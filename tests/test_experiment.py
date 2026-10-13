"""Pruebas de `src/part1/experiment.py` (T1.7-C; Spec §4.1, §5.4, §6.2, §6.5 y §6.6).

Grupos:

    1. archivos de corridas      -> cantidad, nombres, claves de §5.4, semillas, k y presupuesto
    2. frames                    -> solo run_id = 0 en 2D y solo con record_frames: true
    3. summary.json              -> forma exacta, orden, relectura
    4. sensibilidad k = 1        -> GD re-ejecutados, poblacionales copiados
    5. paralelismo               -> workers = 1 y workers = 2 dan los mismos bytes
    6. tablas                    -> CSV y texto de consola
    7. validación                -> config inválida: error claro y ningún archivo
    8. efectos                   -> config intacta, avance, nada fuera de salida/tablas
    9. CLI                       -> `run.py part1`, importación perezosa
   10. configs del repo e higiene

El experimento se ejecuta con un presupuesto pequeño (`PRESUPUESTO` por dimensión) y pocas
corridas; las fixtures de módulo lo ejecutan una vez por variante. La configuración parte de la
real: `configs/part1/base.yaml`.
"""

from __future__ import annotations

import copy
import csv
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from src.common import cli
from src.common.config import load_config
from src.common.results import load_json, run_filename, to_jsonable
from src.common.seeds import seeds_for_runs
from src.part1 import experiment
from src.part1.corrida import (
    K_SENSIBILIDAD,
    METODOS,
    METODOS_GD,
    METODOS_SIN_GRADIENTE,
    ejecutar_corrida,
)
from src.part1.experiment import ejecutar_experimento, manejador_part1, validar_config
from src.part1.metricas import UMBRAL_PRINCIPAL, UMBRALES

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_DEMO = RAIZ / "configs" / "part1" / "demo.yaml"
RUTA_EXPERIMENT = RAIZ / "src" / "part1" / "experiment.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

PRESUPUESTO = 200                      # evaluaciones equivalentes por dimensión en las pruebas
RUNS = 2
BASE_SEED = 7                          # distinto de 0: distingue la semilla del run_id
FUNCIONES_CFG = ["rosenbrock", "rastrigin"]
DIMENSIONES = [2, 3]
N_CONFIGURACIONES = len(FUNCIONES_CFG) * len(DIMENSIONES) * len(METODOS)

CLAVES_CORRIDA = {"func", "dim", "method", "seed", "k", "budget", "config", "result"}
CLAVES_RESULTADO = {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history"}
CLAVES_SUMMARY = ["meta", "configuraciones", "sensibilidad_k1", "avisos"]
CLAVES_META = ["runs", "base_seed", "semillas", "presupuesto_por_dim", "umbrales",
               "umbral_principal", "k_regla", "k_sensibilidad", "func", "dim", "methods"]
CLAVES_ENTRADA = ["func", "dim", "method", "k", "n_corridas", "f_final", "n_f_medio",
                  "n_grad_medio", "eval_equiv_medio", "eval_equiv_medio_k2n",
                  "eval_equiv_medio_k1", "tasa_exito", "evals_hasta_exito_medio"]
CLAVES_UMBRAL = ["1e-04", "1e-02", "1e-06"]
CSV_PRINCIPAL = "tabla_principal.csv"
CSV_SENSIBILIDAD = "tabla_sensibilidad_k1.csv"
RUNS_PRINCIPAL = "datos/runs/"         # rutas relativas a la carpeta de cada experimento
RUNS_K1 = "datos/k1/runs/"
RUTA_SUMMARY = "datos/summary.json"


# ================================================================================================
# Auxiliares y fixtures
# ================================================================================================

def config_de_prueba(carpeta: Path, **cambios) -> dict:
    """Config real de la Parte 1 con presupuesto pequeño y salidas dentro de `carpeta`."""
    cfg = load_config(RUTA_BASE)
    cfg.update(runs=RUNS, base_seed=BASE_SEED, presupuesto_por_dim=PRESUPUESTO, workers=1,
               salida=str(carpeta / "datos"), tablas=str(carpeta / "tablas"))
    cfg.update(cambios)
    return cfg


def silencio(_linea: str) -> None:
    """Receptor del avance que no hace nada."""


class Experimento:
    """Un experimento ya ejecutado: su config, el texto devuelto, el avance y sus archivos.

    `bytes` es una foto en memoria de todo lo que quedó escrito al terminar. Los lectores
    (`leer`, `corridas`, `corrida`, `summary`, `filas_csv`) usan esa foto y no el disco: lo
    que devuelven no cambia aunque después se borre o se vuelva a escribir la carpeta.
    """

    def __init__(self, carpeta: Path, **cambios):
        self.cfg = config_de_prueba(carpeta, **cambios)
        self.cfg_original = copy.deepcopy(self.cfg)
        self.avance: list[str] = []
        self.texto = ejecutar_experimento(self.cfg, informar=self.avance.append)
        self.carpeta = carpeta
        self.salida = Path(self.cfg["salida"])
        self.tablas = Path(self.cfg["tablas"])
        self.bytes = {ruta.relative_to(carpeta).as_posix(): ruta.read_bytes()
                      for ruta in sorted(carpeta.rglob("*")) if ruta.is_file()}

    def leer(self, relativa: str):
        """JSON de la foto, por ruta relativa a la carpeta (p. ej. "datos/summary.json")."""
        return json.loads(self.bytes[relativa])

    def corridas(self, prefijo: str = RUNS_PRINCIPAL) -> dict[str, dict]:
        """Corridas de la foto bajo `prefijo`: nombre de archivo -> diccionario."""
        return {relativa[len(prefijo):]: self.leer(relativa) for relativa in self.bytes
                if relativa.startswith(prefijo)}

    def corrida(self, func: str, dim: int, method: str, run_id: int = 0,
                prefijo: str = RUNS_PRINCIPAL) -> dict:
        nombre = run_filename(func, dim, method, self.cfg["base_seed"] + run_id)
        return self.leer(prefijo + nombre)

    def corrida_k1(self, func: str, dim: int, method: str, run_id: int = 0) -> dict:
        return self.corrida(func, dim, method, run_id, prefijo=RUNS_K1)

    def summary(self) -> dict:
        return self.leer(RUTA_SUMMARY)

    def filas_csv(self, nombre: str) -> list[dict]:
        """Filas del CSV `nombre` de la foto, leídas con `csv.DictReader`."""
        texto = self.bytes[f"tablas/{nombre}"].decode("utf-8")
        return list(csv.DictReader(io.StringIO(texto, newline="")))


@pytest.fixture(scope="module")
def exp(tmp_path_factory) -> Experimento:
    """Experimento completo (2 funciones × 2 dimensiones × 5 métodos) en serie."""
    return Experimento(tmp_path_factory.mktemp("serie"))


@pytest.fixture(scope="module")
def exp_paralelo(exp) -> Experimento:
    """El mismo experimento con dos procesos, con las MISMAS rutas que `exp`.

    Usa las mismas rutas para que la config guardada en cada corrida sea comparable byte a
    byte. Antes de correr borra lo que escribió `exp` (que ya está en `exp.bytes`): así la
    foto de esta ejecución solo contiene lo que escribió la ejecución con dos procesos.
    """
    shutil.rmtree(exp.salida)
    shutil.rmtree(exp.tablas)
    assert list(exp.carpeta.iterdir()) == []
    return Experimento(exp.carpeta, workers=2)


def _corrida_con_contadores_alterados(func, dim, method, base_seed, run_id, cfg, **opciones):
    """`ejecutar_corrida` real con un contador cambiado para provocar avisos de tipo (c).

    pso, run_id = 1: n_grad = 1. gdfijo, run_id = 0: n_f = 1 (con cualquier k).
    """
    corrida = ejecutar_corrida(func, dim, method, base_seed, run_id, cfg, **opciones)
    if method == "pso" and run_id == 1:
        corrida["result"]["n_grad"] = 1
    if method == "gdfijo" and run_id == 0:
        corrida["result"]["n_f"] = 1
    return corrida


CAMBIOS_CON_AVISOS = dict(func=["rastrigin"], dim=[2], methods=["pso", "gdfijo"])
AVISO_PSO = (f"rastrigin 2D pso: 1 corrida(s) con n_grad > 0 en un método que no debería "
             f"usarlo (semillas: {BASE_SEED + 1})")
AVISO_GDFIJO = (f"rastrigin 2D gdfijo: 1 corrida(s) con n_f > 0 en un método que no debería "
                f"usarlo (semillas: {BASE_SEED})")


@pytest.fixture(scope="module")
def exp_con_avisos(tmp_path_factory) -> Experimento:
    """Experimento en serie cuyas corridas traen contadores que `metricas.avisos` señala."""
    with pytest.MonkeyPatch.context() as parche:
        parche.setattr(experiment, "ejecutar_corrida", _corrida_con_contadores_alterados)
        return Experimento(tmp_path_factory.mktemp("con_avisos"), **CAMBIOS_CON_AVISOS)


@pytest.fixture(scope="module")
def exp_sin_frames(tmp_path_factory) -> Experimento:
    """Experimento pequeño en 2D con record_frames: false."""
    return Experimento(tmp_path_factory.mktemp("sin_frames"), func=["rastrigin"], dim=[2],
                       methods=["pso", "gdfijo"], record_frames=False)


def combinaciones(cfg: dict) -> list[tuple[str, int, str]]:
    """(func, dim, method) en el orden de la config."""
    return [(func, dim, method) for func in cfg["func"] for dim in cfg["dim"]
            for method in cfg["methods"]]


# ================================================================================================
# 1. Archivos de corridas
# ================================================================================================

def test_se_crea_un_archivo_por_corrida_con_el_nombre_de_run_filename(exp):
    esperados = {run_filename(func, dim, method, BASE_SEED + run_id)
                 for func, dim, method in combinaciones(exp.cfg) for run_id in range(RUNS)}
    assert len(esperados) == N_CONFIGURACIONES * RUNS
    assert set(exp.corridas()) == esperados


def test_cada_json_tiene_las_claves_exactas_del_spec(exp):
    corridas = exp.corridas()
    assert len(corridas) == N_CONFIGURACIONES * RUNS
    for nombre, corrida in corridas.items():
        assert set(corrida) == CLAVES_CORRIDA, nombre
        assert set(corrida["result"]) - {"frames"} == CLAVES_RESULTADO, nombre


def test_el_contenido_coincide_con_el_nombre_del_archivo(exp):
    for func, dim, method in combinaciones(exp.cfg):
        for run_id in range(RUNS):
            corrida = exp.corrida(func, dim, method, run_id)
            assert (corrida["func"], corrida["dim"], corrida["method"]) == (func, dim, method)
            assert corrida["seed"] == BASE_SEED + run_id


def test_las_semillas_son_base_seed_mas_run_id_y_las_mismas_para_todos_los_metodos(exp):
    esperadas = seeds_for_runs(BASE_SEED, RUNS)
    assert esperadas == [7, 8]
    for func, dim, method in combinaciones(exp.cfg):
        prefijo = f"{func}_{dim}d_{method}_seed"
        semillas = sorted(corrida["seed"] for nombre, corrida in exp.corridas().items()
                          if nombre.startswith(prefijo))
        assert semillas == esperadas, (func, dim, method)


def test_la_corrida_guardada_es_la_de_make_rng_con_base_seed_y_run_id(exp):
    """La semilla guardada es la que se usó: se reproduce con ejecutar_corrida."""
    for method in METODOS:
        esperada = ejecutar_corrida("rastrigin", 2, method, BASE_SEED, 1, exp.cfg_original,
                                    presupuesto_por_dim=PRESUPUESTO)
        guardada = exp.corrida("rastrigin", 2, method, run_id=1)
        assert guardada["result"] == to_jsonable(esperada["result"]), method


def test_presupuesto_y_k_comunes_a_todos_los_metodos(exp):
    for func, dim, method in combinaciones(exp.cfg):
        for run_id in range(RUNS):
            corrida = exp.corrida(func, dim, method, run_id)
            assert corrida["budget"] == PRESUPUESTO * dim, (func, dim, method)
            assert corrida["k"] == 2 * dim, (func, dim, method)
            assert corrida["result"]["eval_equiv"] <= corrida["budget"]


def test_la_config_guardada_trae_la_variante_solo_en_los_gd(exp):
    for method, variante in METODOS_GD.items():
        assert exp.corrida("rastrigin", 3, method)["config"]["variante"] == variante
    for method in METODOS_SIN_GRADIENTE:
        assert "variante" not in exp.corrida("rastrigin", 3, method)["config"]


# ================================================================================================
# 2. Frames
# ================================================================================================

def test_solo_la_primera_semilla_de_2d_trae_frames(exp):
    for func, dim, method in combinaciones(exp.cfg):
        for run_id in range(RUNS):
            corrida = exp.corrida(func, dim, method, run_id)
            debe_traer = dim == 2 and run_id == 0
            assert ("frames" in corrida["result"]) == debe_traer, (func, dim, method, run_id)
            assert corrida["config"]["record_frames"] is debe_traer


def test_los_frames_guardados_no_estan_vacios(exp):
    for method in METODOS:
        assert len(exp.corrida("rastrigin", 2, method)["result"]["frames"]) > 0, method


def test_con_record_frames_false_ninguna_corrida_trae_frames(exp_sin_frames):
    corridas = exp_sin_frames.corridas()
    assert len(corridas) == 2 * RUNS
    for nombre, corrida in corridas.items():
        assert "frames" not in corrida["result"], nombre
        assert corrida["config"]["record_frames"] is False


# ================================================================================================
# 3. summary.json
# ================================================================================================

def test_summary_claves_de_nivel_superior(exp):
    assert list(exp.summary()) == CLAVES_SUMMARY


def test_summary_meta(exp):
    meta = exp.summary()["meta"]
    assert list(meta) == CLAVES_META
    assert meta == {
        "runs": RUNS,
        "base_seed": BASE_SEED,
        "semillas": [7, 8],
        "presupuesto_por_dim": PRESUPUESTO,
        "umbrales": [1e-4, 1e-2, 1e-6],
        "umbral_principal": 1e-4,
        "k_regla": "2n",
        "k_sensibilidad": 1,
        "func": FUNCIONES_CFG,
        "dim": DIMENSIONES,
        "methods": list(METODOS),
    }
    assert meta["umbrales"] == list(UMBRALES) and meta["umbral_principal"] == UMBRAL_PRINCIPAL


@pytest.mark.parametrize("tabla", ["configuraciones", "sensibilidad_k1"])
def test_summary_una_entrada_por_configuracion_en_el_orden_de_la_config(exp, tabla):
    entradas = exp.summary()[tabla]
    assert len(entradas) == N_CONFIGURACIONES
    orden = [(entrada["func"], entrada["dim"], entrada["method"]) for entrada in entradas]
    assert orden == combinaciones(exp.cfg)


def test_el_orden_del_summary_sigue_la_config_y_no_el_alfabeto(exp_sin_frames):
    entradas = exp_sin_frames.summary()["configuraciones"]
    assert [entrada["method"] for entrada in entradas] == ["pso", "gdfijo"]


@pytest.mark.parametrize("tabla", ["configuraciones", "sensibilidad_k1"])
def test_summary_claves_de_cada_entrada(exp, tabla):
    for entrada in exp.summary()[tabla]:
        assert list(entrada) == CLAVES_ENTRADA
        assert entrada["n_corridas"] == RUNS
        assert list(entrada["tasa_exito"]) == CLAVES_UMBRAL
        assert list(entrada["evals_hasta_exito_medio"]) == CLAVES_UMBRAL
        assert list(entrada["f_final"]) == ["media", "desv", "mediana", "mejor", "peor"]


def test_la_tabla_principal_usa_k_igual_a_2n(exp):
    for entrada in exp.summary()["configuraciones"]:
        assert entrada["k"] == 2 * entrada["dim"]
        assert entrada["eval_equiv_medio"] == entrada["eval_equiv_medio_k2n"]


def test_las_metricas_del_summary_salen_de_los_archivos_guardados(exp):
    entrada = exp.summary()["configuraciones"][combinaciones(exp.cfg).index(("rastrigin", 3, "de"))]
    corridas = [exp.corrida("rastrigin", 3, "de", run_id) for run_id in range(RUNS)]
    f_finales = [corrida["result"]["f_best"] for corrida in corridas]
    assert entrada["f_final"]["mejor"] == min(f_finales)
    assert entrada["f_final"]["peor"] == max(f_finales)
    assert entrada["f_final"]["media"] == pytest.approx(sum(f_finales) / RUNS, rel=1e-12)
    assert entrada["n_f_medio"] == sum(c["result"]["n_f"] for c in corridas) / RUNS


def test_sin_resultados_sospechosos_los_avisos_son_una_lista_vacia(exp):
    assert exp.summary()["avisos"] == []


def test_los_avisos_de_las_corridas_llegan_al_summary_con_la_etiqueta_de_su_tabla(exp_con_avisos):
    """pso solo corre en la tabla principal; gdfijo se re-ejecuta y avisa en las dos."""
    assert exp_con_avisos.summary()["avisos"] == [
        f"{experiment.ETIQUETA_PRINCIPAL}: {AVISO_PSO}",
        f"{experiment.ETIQUETA_PRINCIPAL}: {AVISO_GDFIJO}",
        f"{experiment.ETIQUETA_SENSIBILIDAD}: {AVISO_GDFIJO}",
    ]


def test_los_contadores_alterados_estan_en_las_corridas_guardadas(exp_con_avisos):
    """Control de la fixture: el aviso sale de lo que se guardó, no de otro sitio."""
    assert exp_con_avisos.corrida("rastrigin", 2, "pso", run_id=1)["result"]["n_grad"] == 1
    assert exp_con_avisos.corrida("rastrigin", 2, "pso", run_id=0)["result"]["n_grad"] == 0
    assert exp_con_avisos.corrida("rastrigin", 2, "gdfijo", run_id=0)["result"]["n_f"] == 1
    assert exp_con_avisos.corrida_k1("rastrigin", 2, "gdfijo", run_id=0)["result"]["n_f"] == 1


def test_los_avisos_son_una_lista_de_textos(exp_con_avisos):
    avisos = exp_con_avisos.summary()["avisos"]
    assert isinstance(avisos, list) and len(avisos) == 3
    assert all(isinstance(aviso, str) and aviso for aviso in avisos)


def test_cada_aviso_dice_de_que_tabla_viene():
    """Un resumen con 100 % de éxito en los tres umbrales produce un aviso de tipo (b)."""
    resumen = {"func": "rastrigin", "dim": 2, "method": "pso", "n_corridas": 3,
               "tasa_exito": {clave: 1.0 for clave in CLAVES_UMBRAL}}
    principal = experiment.avisos_de_tabla(experiment.ETIQUETA_PRINCIPAL, [resumen], [[]])
    sensibilidad = experiment.avisos_de_tabla(experiment.ETIQUETA_SENSIBILIDAD, [resumen], [[]])
    assert len(principal) == 1 and len(sensibilidad) == 1
    assert principal[0].startswith(experiment.ETIQUETA_PRINCIPAL)
    assert sensibilidad[0].startswith(experiment.ETIQUETA_SENSIBILIDAD)
    assert experiment.ETIQUETA_PRINCIPAL != experiment.ETIQUETA_SENSIBILIDAD
    assert "rastrigin 2D pso" in principal[0]
    assert principal[0] != sensibilidad[0]


def test_los_avisos_del_summary_llevan_una_de_las_dos_etiquetas(exp_con_avisos):
    avisos = exp_con_avisos.summary()["avisos"]
    etiquetas = [aviso.split(": ")[0] for aviso in avisos]
    assert etiquetas == [experiment.ETIQUETA_PRINCIPAL, experiment.ETIQUETA_PRINCIPAL,
                         experiment.ETIQUETA_SENSIBILIDAD]


# ================================================================================================
# 4. Sensibilidad k = 1
# ================================================================================================

def test_k1_solo_guarda_las_reejecuciones_de_los_gd(exp):
    esperados = {run_filename(func, dim, method, BASE_SEED + run_id)
                 for func in FUNCIONES_CFG for dim in DIMENSIONES for method in METODOS_GD
                 for run_id in range(RUNS)}
    assert len(esperados) == 2 * len(FUNCIONES_CFG) * len(DIMENSIONES) * RUNS
    nombres = set(exp.corridas(RUNS_K1))
    assert nombres == esperados
    for method in METODOS_SIN_GRADIENTE:
        assert not any(f"_{method}_" in nombre for nombre in nombres)


def test_las_reejecuciones_tienen_k_1_el_mismo_presupuesto_y_no_traen_frames(exp):
    corridas = exp.corridas(RUNS_K1)
    assert len(corridas) == 16
    for nombre, corrida in corridas.items():
        assert set(corrida) == CLAVES_CORRIDA
        assert corrida["k"] == K_SENSIBILIDAD == 1
        assert corrida["budget"] == PRESUPUESTO * corrida["dim"]
        assert "frames" not in corrida["result"], nombre
        assert corrida["config"]["record_frames"] is False
        assert corrida["result"]["eval_equiv"] <= corrida["budget"]


def test_las_reejecuciones_usan_las_mismas_semillas(exp):
    for method in METODOS_GD:
        for run_id in range(RUNS):
            assert exp.corrida_k1("rosenbrock", 2, method, run_id)["seed"] == BASE_SEED + run_id


@pytest.mark.parametrize("method", list(METODOS_GD))
@pytest.mark.parametrize("dim", DIMENSIONES)
def test_la_reejecucion_con_k_1_difiere_de_la_principal_en_rosenbrock(exp, method, dim):
    """En Rosenbrock el GD agota el presupuesto: con k = 1 alcanza para más gradientes."""
    for run_id in range(RUNS):
        principal = exp.corrida("rosenbrock", dim, method, run_id)["result"]
        k1 = exp.corrida_k1("rosenbrock", dim, method, run_id)["result"]
        assert k1["n_grad"] > principal["n_grad"]


@pytest.mark.parametrize("method", list(METODOS_GD))
def test_la_reejecucion_guardada_es_la_de_ejecutar_corrida_con_k_1(exp, method):
    esperada = ejecutar_corrida("rosenbrock", 3, method, BASE_SEED, 1, exp.cfg_original,
                                k=K_SENSIBILIDAD, presupuesto_por_dim=PRESUPUESTO)
    del esperada["config"]["workers"]      # la config de una corrida no guarda `workers`
    assert exp.corrida_k1("rosenbrock", 3, method, run_id=1) == to_jsonable(esperada)


@pytest.mark.parametrize("method", METODOS_SIN_GRADIENTE)
def test_los_poblacionales_reutilizados_coinciden_con_una_reejecucion_real(exp, method):
    """ea/pso/de no dependen de k: la corrida principal es igual a una con k = 1."""
    for func, dim, run_id in [("rosenbrock", 2, 0), ("rastrigin", 3, 1)]:
        real = ejecutar_corrida(func, dim, method, BASE_SEED, run_id, exp.cfg_original,
                                k=K_SENSIBILIDAD, presupuesto_por_dim=PRESUPUESTO)
        principal = exp.corrida(func, dim, method, run_id)["result"]
        principal.pop("frames", None)
        assert principal == to_jsonable(real["result"]), (func, dim, run_id)
        assert real["result"]["n_grad"] == 0


def test_la_entrada_de_sensibilidad_de_un_poblacional_es_copia_de_la_principal(exp):
    summary = exp.summary()
    pares = list(zip(summary["configuraciones"], summary["sensibilidad_k1"]))
    copiadas = [(a, b) for a, b in pares if a["method"] in METODOS_SIN_GRADIENTE]
    assert len(copiadas) == len(FUNCIONES_CFG) * len(DIMENSIONES) * len(METODOS_SIN_GRADIENTE)
    for principal, sensibilidad in copiadas:
        assert sensibilidad == principal


def test_la_entrada_de_sensibilidad_de_un_gd_es_la_reejecucion(exp):
    summary = exp.summary()
    for principal, sensibilidad in zip(summary["configuraciones"], summary["sensibilidad_k1"]):
        if principal["method"] not in METODOS_GD:
            continue
        nombre = (principal["func"], principal["dim"], principal["method"])
        assert sensibilidad["k"] == 1, nombre
        assert sensibilidad["eval_equiv_medio"] == sensibilidad["eval_equiv_medio_k1"], nombre
        corridas = [exp.corrida_k1(*nombre, run_id) for run_id in range(RUNS)]
        n_grad = [corrida["result"]["n_grad"] for corrida in corridas]
        assert sensibilidad["n_grad_medio"] == sum(n_grad) / RUNS, nombre
        if principal["func"] == "rosenbrock":
            assert sensibilidad["n_grad_medio"] > principal["n_grad_medio"], nombre


# ================================================================================================
# 5. Paralelismo
# ================================================================================================

def test_workers_1_y_workers_2_escriben_los_mismos_archivos_byte_a_byte(exp, exp_paralelo):
    assert exp.cfg["workers"] == 1 and exp_paralelo.cfg["workers"] == 2
    assert sorted(exp.bytes) == sorted(exp_paralelo.bytes)
    # 40 corridas + 16 re-ejecuciones con k = 1 + summary.json + 2 CSV
    assert len(exp.bytes) == N_CONFIGURACIONES * RUNS + 16 + 1 + 2
    distintos = [nombre for nombre in exp.bytes if exp.bytes[nombre] != exp_paralelo.bytes[nombre]]
    assert distintos == []


def test_la_comparacion_de_bytes_cubre_runs_k1_summary_y_csv(exp):
    nombres = list(exp.bytes)
    for prefijo in (RUNS_PRINCIPAL, RUNS_K1):
        assert any(nombre.startswith(prefijo) for nombre in nombres)
    for nombre in (RUTA_SUMMARY, f"tablas/{CSV_PRINCIPAL}", f"tablas/{CSV_SENSIBILIDAD}"):
        assert nombre in nombres


def test_la_config_guardada_en_cada_corrida_no_trae_workers(exp):
    """`workers` no cambia el resultado: no forma parte de la config de una corrida."""
    corridas = list(exp.corridas().items()) + list(exp.corridas(RUNS_K1).items())
    assert len(corridas) == N_CONFIGURACIONES * RUNS + 16
    for nombre, corrida in corridas:
        config = corrida["config"]
        assert "workers" not in config, nombre
        assert config["presupuesto_por_dim"] == PRESUPUESTO
        assert config["runs"] == RUNS and config["base_seed"] == BASE_SEED


def test_el_texto_devuelto_no_depende_de_workers(exp, exp_paralelo):
    assert exp.texto == exp_paralelo.texto


def test_la_funcion_que_corre_en_otro_proceso_es_de_nivel_de_modulo():
    """ProcessPoolExecutor con `spawn` (Windows) necesita una función importable por nombre."""
    funcion = experiment._correr_tarea
    assert funcion.__module__ == "src.part1.experiment"
    assert funcion.__qualname__ == funcion.__name__
    assert getattr(experiment, funcion.__name__) is funcion


# ================================================================================================
# 6. Tablas
# ================================================================================================

@pytest.mark.parametrize("nombre", [CSV_PRINCIPAL, CSV_SENSIBILIDAD])
def test_los_csv_tienen_cabecera_y_una_fila_por_configuracion(exp, nombre):
    crudo = exp.bytes[f"tablas/{nombre}"]
    assert b"\r" not in crudo
    assert crudo.endswith(b"\n")
    lineas = crudo.decode("utf-8").splitlines()
    assert len(lineas) == 1 + N_CONFIGURACIONES
    assert lineas[0].startswith("func,dim,method,k,n_corridas,f_final_media,")


def test_el_csv_principal_coincide_con_el_summary(exp):
    filas = exp.filas_csv(CSV_PRINCIPAL)
    entradas = exp.summary()["configuraciones"]
    assert len(filas) == len(entradas) == N_CONFIGURACIONES
    for fila, entrada in zip(filas, entradas):
        assert (fila["func"], int(fila["dim"]), fila["method"]) == (
            entrada["func"], entrada["dim"], entrada["method"])
        assert float(fila["f_final_media"]) == entrada["f_final"]["media"]
        assert float(fila["tasa_exito_1e-04"]) == entrada["tasa_exito"]["1e-04"]
        assert float(fila["n_grad_medio"]) == entrada["n_grad_medio"]


def test_el_csv_de_sensibilidad_trae_k_1_en_los_gd(exp):
    filas_gd = [fila for fila in exp.filas_csv(CSV_SENSIBILIDAD) if fila["method"] in METODOS_GD]
    assert len(filas_gd) == 8
    for fila in filas_gd:
        assert float(fila["k"]) == 1


def test_none_se_escribe_como_celda_vacia(exp):
    """Con presupuesto pequeño hay configuraciones sin éxitos: su media hasta el éxito es None."""
    entradas = exp.summary()["configuraciones"]
    sin_exito = [i for i, entrada in enumerate(entradas)
                 if entrada["evals_hasta_exito_medio"]["1e-06"] is None]
    assert sin_exito, "el caso de prueba ya no tiene configuraciones sin éxito"
    filas = exp.filas_csv(CSV_PRINCIPAL)
    for i in sin_exito:
        assert filas[i]["evals_hasta_exito_medio_1e-06"] == ""
    texto = exp.bytes[f"tablas/{CSV_PRINCIPAL}"].decode("utf-8")
    assert "None" not in texto and "nan" not in texto.lower()


def test_el_texto_devuelto_trae_las_dos_tablas_por_separado(exp):
    assert isinstance(exp.texto, str)
    lineas = exp.texto.splitlines()
    cabeceras = [i for i, linea in enumerate(lineas) if linea.startswith("función")]
    assert len(cabeceras) == 2
    for inicio in cabeceras:
        filas = lineas[inicio + 1:inicio + 1 + N_CONFIGURACIONES]
        assert [fila.split(" | ")[2].strip() for fila in filas] == list(METODOS) * 4
    assert experiment.ETIQUETA_PRINCIPAL in lineas[cabeceras[0] - 1]
    assert experiment.ETIQUETA_SENSIBILIDAD in lineas[cabeceras[1] - 1]


def _titulo_de_sensibilidad(texto: str) -> str:
    lineas = [linea for linea in texto.splitlines()
              if linea.startswith(experiment.ETIQUETA_SENSIBILIDAD)]
    assert len(lineas) == 1
    return lineas[0]


def test_la_nota_de_sensibilidad_nombra_los_metodos_de_la_config(exp, exp_sin_frames):
    assert _titulo_de_sensibilidad(exp.texto) == (
        f"{experiment.ETIQUETA_SENSIBILIDAD} (re-ejecutados con k = 1: gdfijo, gdarmijo; "
        "filas de la tabla principal: ea, pso, de)")
    assert _titulo_de_sensibilidad(exp_sin_frames.texto) == (
        f"{experiment.ETIQUETA_SENSIBILIDAD} (re-ejecutados con k = 1: gdfijo; "
        "filas de la tabla principal: pso)")


@pytest.mark.parametrize("methods, nota", [
    (["de", "ea"], "filas de la tabla principal: de, ea"),
    (["gdarmijo"], "re-ejecutados con k = 1: gdarmijo"),
])
def test_la_nota_de_sensibilidad_omite_el_grupo_que_no_esta_en_la_config(tmp_path, methods,
                                                                        nota):
    cfg = config_de_prueba(tmp_path, func=["rastrigin"], dim=[2], methods=methods, runs=1)
    texto = ejecutar_experimento(cfg, informar=silencio)
    assert _titulo_de_sensibilidad(texto) == f"{experiment.ETIQUETA_SENSIBILIDAD} ({nota})"


# ================================================================================================
# 7. Validación
# ================================================================================================

def test_la_config_base_y_la_del_demo_son_validas():
    validar_config(load_config(RUTA_BASE))
    validar_config(load_config(RUTA_DEMO))


CASOS_INVALIDOS = [
    ("func", [], ValueError, "func"),
    ("dim", [], ValueError, "dim"),
    ("methods", [], ValueError, "methods"),
    ("methods", "pso", TypeError, "methods"),
    ("methods", ["pso", "sgd"], ValueError, "sgd"),
    ("methods", ["pso", "pso"], ValueError, "repetid"),
    ("methods", [["pso"]], (TypeError, ValueError), "methods"),
    ("func", ["rastrigin", "ackley"], ValueError, "ackley"),
    ("func", ["rastrigin", "rastrigin"], ValueError, "repetid"),
    ("dim", [2, 2], ValueError, "repetid"),
    ("dim", [0], ValueError, "dim"),
    ("dim", [2.0], TypeError, "dim"),
    ("dim", [True], TypeError, "dim"),
    ("dim", 2, TypeError, "dim"),
    ("runs", True, TypeError, "runs"),
    ("runs", 0, ValueError, "runs"),
    ("runs", 2.0, TypeError, "runs"),
    ("base_seed", -1, ValueError, "base_seed"),
    ("base_seed", False, TypeError, "base_seed"),
    ("record_frames", 1, TypeError, "record_frames"),
    ("record_frames", "true", TypeError, "record_frames"),
    ("record_frames", None, TypeError, "record_frames"),
    ("presupuesto_por_dim", 0, ValueError, "presupuesto_por_dim"),
    ("presupuesto_por_dim", 1e4, TypeError, "presupuesto_por_dim"),
    ("presupuesto_por_dim", True, TypeError, "presupuesto_por_dim"),
    ("workers", 0, ValueError, "workers"),
    ("workers", True, TypeError, "workers"),
    ("workers", None, TypeError, "workers"),
    ("salida", "", ValueError, "salida"),
    ("salida", "   ", ValueError, "salida"),
    ("salida", None, TypeError, "salida"),
    ("tablas", "", ValueError, "tablas"),
    ("tablas", 3, TypeError, "tablas"),
]


@pytest.mark.parametrize("clave, valor, error, fragmento", CASOS_INVALIDOS,
                         ids=[f"{caso[0]}={caso[1]!r}" for caso in CASOS_INVALIDOS])
def test_validacion_rechaza_y_no_escribe_nada(tmp_path, clave, valor, error, fragmento):
    cfg = config_de_prueba(tmp_path / "x")
    cfg[clave] = valor
    with pytest.raises(error, match=fragmento):
        validar_config(cfg)
    with pytest.raises(error, match=fragmento):
        ejecutar_experimento(cfg, informar=silencio)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("clave", ["func", "dim", "methods", "runs", "base_seed",
                                   "record_frames", "presupuesto_por_dim", "workers",
                                   "salida", "tablas"])
def test_validacion_rechaza_una_clave_que_falta(tmp_path, clave):
    cfg = config_de_prueba(tmp_path / "x")
    del cfg[clave]
    with pytest.raises(ValueError, match=clave):
        ejecutar_experimento(cfg, informar=silencio)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("no_finito", [float("inf"), float("-inf"), float("nan")])
@pytest.mark.parametrize("ruta", ["pso.w", "gd.eta.rastrigin", "de.F", "gd.armijo.c"])
def test_validacion_rechaza_un_float_no_finito_y_dice_donde_esta(tmp_path, ruta, no_finito):
    cfg = config_de_prueba(tmp_path / "x")
    *padres, hoja = ruta.split(".")
    nodo = cfg
    for parte in padres:
        nodo = nodo[parte]
    nodo[hoja] = no_finito
    with pytest.raises(ValueError, match=re.escape(ruta)) as error:
        ejecutar_experimento(cfg, informar=silencio)
    assert "null" in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_validacion_rechaza_un_no_finito_dentro_de_una_lista(tmp_path):
    cfg = config_de_prueba(tmp_path / "x")
    cfg["extra"] = {"valores": [1.0, float("nan")]}
    with pytest.raises(ValueError, match=re.escape("extra.valores[1]")):
        validar_config(cfg)


def test_validacion_acepta_null_como_sin_limite(tmp_path):
    cfg = config_de_prueba(tmp_path / "x")
    assert cfg["pso"]["iteraciones"] is None and cfg["ea"]["generaciones"] is None
    cfg["pso"]["vmax_frac"] = None
    validar_config(cfg)


def test_validacion_rechaza_una_dimension_menor_que_el_minimo_de_la_funcion(tmp_path):
    cfg = config_de_prueba(tmp_path / "x", func=["rastrigin", "rosenbrock"], dim=[1])
    with pytest.raises(ValueError, match="rosenbrock"):
        ejecutar_experimento(cfg, informar=silencio)
    assert list(tmp_path.iterdir()) == []


def test_validacion_rechaza_una_config_que_no_es_un_mapeo():
    with pytest.raises(TypeError, match="config"):
        validar_config(None)
    with pytest.raises(TypeError, match="config"):
        validar_config([("runs", 1)])


def test_validar_config_no_devuelve_nada_y_no_modifica_la_config(tmp_path):
    cfg = config_de_prueba(tmp_path / "x")
    copia = copy.deepcopy(cfg)
    assert validar_config(cfg) is None
    assert cfg == copia
    assert list(tmp_path.iterdir()) == []


# ================================================================================================
# 8. Efectos
# ================================================================================================

def test_la_config_de_entrada_no_se_modifica(exp, exp_paralelo, exp_sin_frames):
    for experimento in (exp, exp_paralelo, exp_sin_frames):
        assert experimento.cfg == experimento.cfg_original


def test_solo_escribe_dentro_de_salida_y_tablas(tmp_path, monkeypatch):
    """Con el directorio de trabajo en una carpeta vacía, esa carpeta sigue vacía al terminar."""
    trabajo = tmp_path / "trabajo"
    trabajo.mkdir()
    monkeypatch.chdir(trabajo)
    destino = tmp_path / "experimento"
    Experimento(destino, func=["rastrigin"], dim=[2], methods=["gdfijo", "de"])
    assert list(trabajo.iterdir()) == []
    assert sorted(ruta.name for ruta in tmp_path.iterdir()) == ["experimento", "trabajo"]
    assert sorted(ruta.name for ruta in destino.iterdir()) == ["datos", "tablas"]
    assert sorted(ruta.name for ruta in (destino / "datos").iterdir()) == [
        "k1", "runs", "summary.json"]
    assert [ruta.name for ruta in (destino / "datos" / "k1").iterdir()] == ["runs"]
    assert sorted(ruta.name for ruta in (destino / "tablas").iterdir()) == [
        CSV_PRINCIPAL, CSV_SENSIBILIDAD]


def test_no_quedan_archivos_temporales(exp):
    assert len(exp.bytes) == N_CONFIGURACIONES * RUNS + 16 + 1 + 2
    assert not [nombre for nombre in exp.bytes if nombre.endswith(".tmp")]


def test_el_avance_tiene_una_linea_por_configuracion_terminada(exp):
    # 20 configuraciones de la tabla principal + 8 re-ejecuciones de GD con k = 1
    assert len(exp.avance) == N_CONFIGURACIONES + 8
    assert all("\n" not in linea for linea in exp.avance)
    for (func, dim, method), linea in zip(combinaciones(exp.cfg), exp.avance):
        assert f"{func} {dim}D {method}" in linea
    assert all("k = 1" in linea for linea in exp.avance[N_CONFIGURACIONES:])
    assert not any("k = 1" in linea for linea in exp.avance[:N_CONFIGURACIONES])


def test_con_informar_propio_no_imprime_nada(tmp_path, capsys):
    cfg = config_de_prueba(tmp_path, func=["rastrigin"], dim=[2], methods=["gdfijo"])
    ejecutar_experimento(cfg, informar=silencio)
    salida = capsys.readouterr()
    assert salida.out == "" and salida.err == ""


def test_por_defecto_el_avance_se_imprime(tmp_path, capsys):
    cfg = config_de_prueba(tmp_path, func=["rastrigin"], dim=[2], methods=["gdfijo"])
    ejecutar_experimento(cfg)
    assert "rastrigin 2D gdfijo" in capsys.readouterr().out


def test_dos_ejecuciones_iguales_escriben_los_mismos_bytes(tmp_path):
    cambios = dict(func=["rastrigin"], dim=[2], methods=["ea", "gdarmijo"])
    primero = Experimento(tmp_path, **cambios).bytes
    segundo = Experimento(tmp_path, **cambios).bytes
    assert primero == segundo


# ================================================================================================
# 9. CLI
# ================================================================================================

def _yaml_de_prueba(tmp_path: Path, **cambios) -> Path:
    """Config en tmp_path que hereda de la base real, con rutas absolutas y poco presupuesto."""
    datos = {"hereda": str(RUTA_BASE), "func": ["rastrigin"], "dim": [2],
             "methods": ["pso", "gdfijo"], "runs": 2, "presupuesto_por_dim": PRESUPUESTO,
             "salida": str(tmp_path / "datos"), "tablas": str(tmp_path / "tablas")}
    datos.update(cambios)
    ruta = tmp_path / "prueba.yaml"
    ruta.write_text(yaml.safe_dump(datos, sort_keys=False), encoding="utf-8")
    return ruta


def test_cli_part1_corre_el_experimento(tmp_path, capsys):
    assert cli.main(["part1", "--config", str(_yaml_de_prueba(tmp_path))]) == 0
    salida = capsys.readouterr().out
    assert "Configuración final resuelta" in salida
    assert "pendiente" not in salida
    assert experiment.ETIQUETA_PRINCIPAL in salida
    assert experiment.ETIQUETA_SENSIBILIDAD in salida
    tabla = [linea for linea in salida.splitlines() if linea.startswith("rastrigin | 2")]
    assert [linea.split(" | ")[2].strip() for linea in tabla] == ["pso", "gdfijo"] * 2
    assert len(list((tmp_path / "datos" / "runs").iterdir())) == 4
    assert len(list((tmp_path / "datos" / "k1" / "runs").iterdir())) == 2
    assert (tmp_path / "datos" / "summary.json").is_file()
    assert (tmp_path / "tablas" / CSV_PRINCIPAL).is_file()
    assert (tmp_path / "tablas" / CSV_SENSIBILIDAD).is_file()


def test_cli_part1_admite_set(tmp_path, capsys):
    ruta = _yaml_de_prueba(tmp_path)
    assert cli.main(["part1", "--config", str(ruta), "--set", "runs=1",
                     "--set", "base_seed=5"]) == 0
    nombres = sorted(archivo.name for archivo in (tmp_path / "datos" / "runs").iterdir())
    assert nombres == ["rastrigin_2d_gdfijo_seed5.json", "rastrigin_2d_pso_seed5.json"]


def _lineas_tras_el_titulo_de_avisos(salida: str) -> list[str]:
    """Líneas impresas después de TITULO_AVISOS (el título debe aparecer una sola vez)."""
    lineas = salida.splitlines()
    assert lineas.count(experiment.TITULO_AVISOS) == 1
    return lineas[lineas.index(experiment.TITULO_AVISOS) + 1:]


def test_el_manejador_imprime_los_avisos_del_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(experiment, "ejecutar_corrida", _corrida_con_contadores_alterados)
    cfg = config_de_prueba(tmp_path, **CAMBIOS_CON_AVISOS)
    assert manejador_part1(cfg) == 0
    salida = capsys.readouterr().out
    avisos = load_json(tmp_path / "datos" / "summary.json")["avisos"]
    assert avisos == [
        f"{experiment.ETIQUETA_PRINCIPAL}: {AVISO_PSO}",
        f"{experiment.ETIQUETA_PRINCIPAL}: {AVISO_GDFIJO}",
        f"{experiment.ETIQUETA_SENSIBILIDAD}: {AVISO_GDFIJO}",
    ]
    assert _lineas_tras_el_titulo_de_avisos(salida) == [f"  - {aviso}" for aviso in avisos]
    assert experiment.TEXTO_SIN_AVISOS not in salida


def test_cli_part1_sin_avisos_lo_dice(tmp_path, capsys):
    """Rastrigin 2D con pso y gdfijo y poco presupuesto no produce avisos."""
    assert cli.main(["part1", "--config", str(_yaml_de_prueba(tmp_path))]) == 0
    salida = capsys.readouterr().out
    assert load_json(tmp_path / "datos" / "summary.json")["avisos"] == []
    assert _lineas_tras_el_titulo_de_avisos(salida) == [f"  - {experiment.TEXTO_SIN_AVISOS}"]


def test_cli_part1_config_invalida_sale_con_codigo_2_y_no_escribe(tmp_path, capsys):
    ruta = _yaml_de_prueba(tmp_path)
    codigo = cli.main(["part1", "--config", str(ruta), "--set", "methods=[pso, sgd]"])
    assert codigo == 2
    error = capsys.readouterr().err
    assert "sgd" in error and "config" in error.lower()
    assert sorted(archivo.name for archivo in tmp_path.iterdir()) == ["prueba.yaml"]


def test_el_manejador_devuelve_2_con_una_config_invalida_y_0_con_una_valida(tmp_path, capsys):
    cfg = config_de_prueba(tmp_path, func=["rastrigin"], dim=[2], methods=["de"], runs=1)
    assert manejador_part1({**cfg, "workers": 0}) == 2
    assert list(tmp_path.iterdir()) == []
    assert "workers" in capsys.readouterr().err
    assert manejador_part1(cfg) == 0
    assert "rastrigin | 2" in capsys.readouterr().out


def test_el_manejador_no_oculta_errores_que_no_son_de_validacion(tmp_path, monkeypatch):
    def falla(*_args, **_kwargs):
        raise ValueError("error interno de prueba")

    monkeypatch.setattr(experiment, "ejecutar_experimento", falla)
    with pytest.raises(ValueError, match="error interno de prueba"):
        manejador_part1(config_de_prueba(tmp_path))


def test_el_manejador_registrado_ya_no_es_el_provisional(capsys):
    sub = cli.SUBCOMANDOS["part1"]
    assert sub.usa_config is True
    assert sub.manejador.__module__ == "src.common.cli"
    assert sub.manejador.__qualname__ == sub.manejador.__name__      # nivel de módulo
    assert sub.manejador({"methods": []}) == 2
    salida = capsys.readouterr()
    assert "pendiente" not in salida.out + salida.err


def test_part2_y_figures_siguen_pendientes(capsys):
    for nombre in ("part2", "figures"):
        assert cli.SUBCOMANDOS[nombre].manejador(None) == 0
        assert "pendiente" in capsys.readouterr().out


def test_importar_el_cli_no_carga_numpy_ni_el_experimento():
    codigo = (
        "import sys\n"
        "import src.common.cli as cli\n"
        "cli.build_parser()\n"
        "cargados = [m for m in ('numpy', 'src.part1.experiment', 'src.part1') "
        "if m in sys.modules]\n"
        "print(cargados)\n"
    )
    res = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True,
                         encoding="utf-8", check=False)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "[]"


def test_la_ayuda_de_run_py_no_carga_numpy():
    codigo = (
        "import sys\n"
        "from src.common.cli import main\n"
        "try:\n"
        "    main(['--help'])\n"
        "except SystemExit:\n"
        "    pass\n"
        "print('NUMPY' if 'numpy' in sys.modules else 'LIMPIO')\n"
    )
    res = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True,
                         encoding="utf-8", check=False)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().endswith("LIMPIO")


# ================================================================================================
# 10. Configs del repo e higiene
# ================================================================================================

def test_el_demo_no_escribe_en_las_carpetas_del_experimento_completo():
    base, demo = load_config(RUTA_BASE), load_config(RUTA_DEMO)
    assert base["salida"] == "results/data/part1"
    assert base["tablas"] == "results/tables/part1"
    for clave in ("salida", "tablas"):
        assert demo[clave] != base[clave]
        assert Path(demo[clave]) not in (Path("results/data/part1"),
                                         Path("results/tables/part1"))
        assert Path(base[clave]) not in Path(demo[clave]).parents


def test_la_base_trae_las_claves_que_lee_el_experimento():
    base = load_config(RUTA_BASE)
    assert base["presupuesto_por_dim"] == 10_000
    assert base["workers"] == 1
    assert base["runs"] == 30 and base["base_seed"] == 0


@pytest.mark.parametrize("ruta", [RUTA_EXPERIMENT, RUTA_PRUEBAS],
                         ids=["experiment.py", "test_experiment.py"])
def test_lineas_de_hasta_100_caracteres_en_lf(ruta):
    crudo = ruta.read_bytes()
    assert b"\r" not in crudo
    lineas = crudo.decode("utf-8").splitlines()
    largas = [i + 1 for i, linea in enumerate(lineas) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    celda_actual = None
    lineas = RUTA_EXPERIMENT.read_text(encoding="utf-8").splitlines()
    for numero, linea in enumerate(lineas, start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_markdown_con_los_nombres_publicos():
    texto = RUTA_EXPERIMENT.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in ("validar_config", "ejecutar_experimento", "manejador_part1"):
        assert f"`{nombre}`" in cabecera


def test_el_experimento_no_usa_azar_global_ni_cuenta_evaluaciones():
    texto = RUTA_EXPERIMENT.read_text(encoding="utf-8")
    for prohibido in ("np.random", "import random", "CountedProblem(", "default_rng"):
        assert prohibido not in texto
