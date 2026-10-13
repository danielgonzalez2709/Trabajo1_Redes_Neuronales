"""Pruebas de `src/part1/hpo_experimento.py` (T1.10-B; Spec §4.1, §5.4, §6.2, §6.5 y §6.6).

Grupos:

    1. tarea elemental           -> registro compacto, éxito a 1e-6, nivel de módulo
    2. corridas de ajuste        -> R1 (conteo exacto), R2 (semillas >= 30), k = 2n, presupuesto
    3. archivos de la HPO        -> ensayos_*.json, seleccion.json, sin history/frames, tamaño
    4. tuned.yaml                -> cabecera, hereda relativo, relectura, solo lo que cambió
    5. experimento final         -> valores afinados, semillas 0..runs−1, comparacion.csv, R8
    6. paralelismo               -> workers = 1 y workers = 2 dan los mismos bytes
    7. reanudar                  -> reutiliza con meta igual; re-corre con aviso si cambió
    8. validación                -> config inválida: error, código 2 y ningún archivo nuevo
    9. demo                      -> carpetas propias y demo de punta a punta reducido
   10. comparar_resumenes        -> dos summary.json sintéticos hechos a mano
   11. CLI                       -> `run.py hpo` recibe la ruta de --config y los --set
   12. higiene

Casi todas las pruebas corren con un directorio temporal como cwd, rutas RELATIVAS en la config
y una copia de `configs/part1/base.yaml` en `<cwd>/configs/part1/`. El presupuesto es pequeño
(`presupuesto_por_dim = 200`), con 2 o 3 ensayos, 2 semillas y 2 corridas de reporte.
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

from src.common import cli
from src.common.config import apply_overrides, cargar_yaml, load_config
from src.common.results import run_filename, save_json
from src.part1 import hpo_experimento
from src.part1.corrida import ejecutar_corrida
from src.part1.experiment import ejecutar_experimento
from src.part1.functions import get_function
from src.part1.hpo import config_afinada, construir_unidades, elegir_ganador, puntuar_ensayos
from src.part1.hpo_experimento import (
    COLUMNAS_COMPARACION,
    comparar_resumenes,
    ejecutar_hpo,
    manejador_hpo,
    validar_ejecucion,
)
from src.part1.metricas import evals_hasta_exito

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_DEMO_HPO = RAIZ / "configs" / "part1" / "hpo_demo.yaml"
RUTA_MODULO = RAIZ / "src" / "part1" / "hpo_experimento.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

RUTA_CONFIG = "configs/part1/base.yaml"          # relativa al cwd temporal de cada prueba
RUTA_CONFIG_DEMO = "configs/part1/hpo_demo.yaml"
PRESUPUESTO = 200
RUNS = 2
ENSAYOS = 3
SEMILLAS = 2
BASE_SEED_AJUSTE = 1000                          # hpo.base_seed de base.yaml
SUFIJO = "1e-06"
CAMPOS_REGISTRO = ["f_best", "n_f", "n_grad", "eval_equiv", f"evals_hasta_exito_{SUFIJO}"]
CLAVES_META = ["unidad", "metodo", "func", "indice", "celdas", "ensayos", "semillas",
               "semillas_de_ajuste", "presupuesto_por_dim", "k_regla", "espacio", "bloque_base",
               "semilla_busqueda"]
PENALIZACION = 1.0                               # f_best + 1 > f* + 1e-6: el defecto no tiene éxito

# Experimento principal: dos funciones en 2D, gdfijo (una unidad por función) y pso.
OVERRIDES = ["presupuesto_por_dim=200", "runs=2", "func=[rosenbrock, rastrigin]", "dim=[2]",
             "methods=[gdfijo, pso]", "hpo.ensayos=3", "hpo.semillas=2"]
UNIDADES = ["gdfijo_rosenbrock", "gdfijo_rastrigin", "pso"]
CELDAS = {"gdfijo_rosenbrock": ["rosenbrock_2d"], "gdfijo_rastrigin": ["rastrigin_2d"],
          "pso": ["rosenbrock_2d", "rastrigin_2d"]}
# Experimento pequeño: una función, 2 ensayos.
OVERRIDES_PEQUENOS = ["presupuesto_por_dim=200", "runs=2", "func=[rastrigin]", "dim=[2]",
                      "methods=[gdfijo, pso]", "hpo.ensayos=2", "hpo.semillas=2"]

CARPETA_HPO = "results/data/part1_hpo/"
CARPETA_AFINADA = "results/data/part1_tuned/"
TABLAS_AFINADAS = "results/tables/part1_tuned/"
CONFIG_AFINADA = "configs/part1/tuned.yaml"
CARPETAS_POR_DEFECTO = ("results/data/part1/", "results/tables/part1/")
W_DEFECTO = load_config(RUTA_BASE)["pso"]["w"]
ETA_RASTRIGIN_DEFECTO = load_config(RUTA_BASE)["gd"]["eta"]["rastrigin"]
PENALIZACION_GD = 1000.0


# ================================================================================================
# Auxiliares y fixtures
# ================================================================================================

def silencio(_linea: str) -> None:
    """Receptor del avance que no hace nada."""


def preparar_carpeta(carpeta: Path, *extra: Path) -> Path:
    """Copia base.yaml (y `extra`) a `<carpeta>/configs/part1/` y devuelve `carpeta`."""
    destino = carpeta / "configs" / "part1"
    destino.mkdir(parents=True, exist_ok=True)
    for origen in (RUTA_BASE, *extra):
        shutil.copyfile(origen, destino / origen.name)
    return carpeta


def cfg_de(ruta: str, overrides) -> dict:
    """La config que entrega el CLI: --config + --set."""
    return apply_overrides(load_config(ruta), list(overrides))


def foto(carpeta: Path) -> dict:
    """Árbol bajo `carpeta`: ruta relativa -> bytes (archivo) o None (carpeta)."""
    return {ruta.relative_to(carpeta).as_posix(): (ruta.read_bytes() if ruta.is_file() else None)
            for ruta in sorted(carpeta.rglob("*"))}


class Espia:
    """Sustituto de `hpo_experimento.ejecutar_corrida` que anota cada llamada y llama al real.

    Con `forzar`:
    - pso: el ensayo con la inercia por defecto queda sin éxito (f_best + PENALIZACION) y
      cualquier otro llega a f* en la evaluación 1: gana el ensayo 1 (el primero de los
      empatados);
    - gdfijo en rastrigin: todo ensayo con un η distinto del defecto suma PENALIZACION_GD, más
      que el máximo de Rastrigin 2D en su dominio (≈ 80.7): gana el ensayo 0.
    """

    def __init__(self, forzar: bool = False):
        self.forzar = forzar
        self.llamadas: list[dict] = []

    def __call__(self, func, dim, method, base_seed, run_id, cfg, **opciones):
        self.llamadas.append({"func": func, "dim": dim, "method": method,
                              "base_seed": base_seed, "run_id": run_id,
                              "cfg": copy.deepcopy(cfg), **opciones})
        corrida = ejecutar_corrida(func, dim, method, base_seed, run_id, cfg, **opciones)
        if (self.forzar and method == "gdfijo" and func == "rastrigin"
                and cfg["gd"]["eta"]["rastrigin"] != ETA_RASTRIGIN_DEFECTO):
            corrida["result"]["f_best"] = corrida["result"]["f_best"] + PENALIZACION_GD
        if self.forzar and method == "pso":
            f_star = get_function(func, dim).f_star
            resultado = corrida["result"]
            if cfg["pso"]["w"] == W_DEFECTO:
                resultado["f_best"] = resultado["f_best"] + PENALIZACION
            else:
                resultado["f_best"] = f_star
                resultado["history"] = [{"eval_equiv": 1.0, "f_best": f_star}]
        return corrida


class Ejecucion:
    """Una HPO ya ejecutada en `carpeta` (cwd temporal), con su foto de archivos.

    Antes de la HPO corre el experimento por defecto (`con_defecto`), que deja
    `<salida>/summary.json`; `antes` es la foto tomada justo antes de llamar a `ejecutar_hpo`.
    """

    def __init__(self, carpeta: Path, overrides, espia=None, ruta: str = RUTA_CONFIG,
                 con_defecto: bool = True):
        self.carpeta = carpeta
        self.overrides = list(overrides)
        self.avance: list[str] = []
        with pytest.MonkeyPatch.context() as parche:
            parche.chdir(carpeta)
            if espia is not None:
                parche.setattr(hpo_experimento, "ejecutar_corrida", espia)
            self.cfg = cfg_de(ruta, self.overrides)
            self.cfg_original = copy.deepcopy(self.cfg)
            if con_defecto:
                ejecutar_experimento(self.cfg, informar=silencio)
            self.antes = foto(carpeta)
            self.texto = ejecutar_hpo(self.cfg, informar=self.avance.append, ruta_config=ruta,
                                      overrides=self.overrides)
        self.bytes = foto(carpeta)

    def leer(self, relativa: str):
        return json.loads(self.bytes[relativa])

    def texto_de(self, relativa: str) -> str:
        return self.bytes[relativa].decode("utf-8")

    def seleccion(self) -> dict:
        return self.leer(CARPETA_HPO + "seleccion.json")

    def ensayos(self, unidad: str) -> dict:
        return self.leer(f"{CARPETA_HPO}ensayos_{unidad}.json")

    def unidad(self, nombre: str) -> dict:
        return next(u for u in self.seleccion()["unidades"] if u["unidad"] == nombre)


@pytest.fixture(scope="module")
def espia() -> Espia:
    return Espia(forzar=True)


@pytest.fixture(scope="module")
def hpo(tmp_path_factory, espia) -> Ejecucion:
    """HPO principal: rosenbrock y rastrigin en 2D, gdfijo y pso, 3 ensayos, 2 semillas."""
    carpeta = preparar_carpeta(tmp_path_factory.mktemp("hpo"))
    return Ejecucion(carpeta, OVERRIDES, espia=espia)


def ajuste_de(espia: Espia, unidad: str) -> list[dict]:
    """Llamadas del espía que pertenecen a `unidad`."""
    if unidad.startswith("gdfijo_"):
        func = unidad.split("_", 1)[1]
        return [ll for ll in espia.llamadas if ll["method"] == "gdfijo" and ll["func"] == func]
    return [ll for ll in espia.llamadas if ll["method"] == unidad]


def huella_de_ensayo(llamada: dict) -> tuple:
    """Valores de los hiperparámetros de la unidad de la llamada (identifican el ensayo)."""
    cfg = llamada["cfg"]
    if llamada["method"] == "gdfijo":
        return (cfg["gd"]["eta"][llamada["func"]],)
    bloque = cfg["pso"]
    return (bloque["N"], bloque["w"], bloque["c1"], bloque["c2"], bloque["vmax_frac"])


# ================================================================================================
# 1. Tarea elemental
# ================================================================================================

def _tarea(cfg: dict, metodo="pso", func="rastrigin", dim=2, n_semillas=3) -> tuple:
    return (metodo, cfg, func, dim, BASE_SEED_AJUSTE, n_semillas, PRESUPUESTO)


def test_la_tarea_devuelve_solo_el_registro_compacto():
    cfg = load_config(RUTA_BASE)
    del cfg["workers"]
    registro = hpo_experimento._correr_tarea_hpo(_tarea(cfg))
    assert list(registro) == CAMPOS_REGISTRO
    assert all(len(registro[campo]) == 3 for campo in CAMPOS_REGISTRO)
    assert all(type(valor) is float for valor in registro["f_best"])
    assert all(type(valor) is int for valor in registro["n_f"] + registro["n_grad"])
    assert all(type(valor) is float for valor in registro["eval_equiv"])
    assert "history" not in json.dumps(registro) and "frames" not in json.dumps(registro)


def test_la_tarea_coincide_con_ejecutar_corrida_semilla_a_semilla():
    cfg = load_config(RUTA_BASE)
    del cfg["workers"]
    registro = hpo_experimento._correr_tarea_hpo(_tarea(cfg, metodo="gdfijo"))
    for run_id in range(3):
        corrida = ejecutar_corrida("rastrigin", 2, "gdfijo", BASE_SEED_AJUSTE, run_id, cfg,
                                   k=4, presupuesto_por_dim=PRESUPUESTO)
        assert registro["f_best"][run_id] == corrida["result"]["f_best"]
        assert registro["n_grad"][run_id] == corrida["result"]["n_grad"]
        assert registro["eval_equiv"][run_id] == corrida["result"]["eval_equiv"]


def test_la_tarea_da_evaluaciones_solo_a_las_semillas_con_exito(monkeypatch):
    """Semilla 1 forzada a f*: evals = eval_equiv del primer punto con éxito; las demás None."""
    def corrida_forzada(func, dim, method, base_seed, run_id, cfg, **opciones):
        corrida = ejecutar_corrida(func, dim, method, base_seed, run_id, cfg, **opciones)
        if run_id == 1:
            corrida["result"]["f_best"] = 0.0
            corrida["result"]["history"] = [{"eval_equiv": 9.0, "f_best": 5e-7},
                                            {"eval_equiv": 12.0, "f_best": 0.0}]
        return corrida

    monkeypatch.setattr(hpo_experimento, "ejecutar_corrida", corrida_forzada)
    cfg = load_config(RUTA_BASE)
    del cfg["workers"]
    registro = hpo_experimento._correr_tarea_hpo(_tarea(cfg))
    evals = registro[f"evals_hasta_exito_{SUFIJO}"]
    assert evals[1] == 9.0
    for semilla in (0, 2):
        assert (evals[semilla] is None) == (registro["f_best"][semilla] > 1e-6)


def test_las_evaluaciones_de_la_tarea_son_las_de_metricas():
    corrida = {"func": "rastrigin", "dim": 2, "method": "pso", "seed": 0,
               "result": {"history": [{"eval_equiv": 3.0, "f_best": 2.0},
                                      {"eval_equiv": 7.0, "f_best": 1e-7}]}}
    assert evals_hasta_exito(corrida, 0.0, 1e-6) == 7.0


def test_la_funcion_que_corre_en_otro_proceso_es_de_nivel_de_modulo():
    funcion = hpo_experimento._correr_tarea_hpo
    assert funcion.__module__ == "src.part1.hpo_experimento"
    assert funcion.__qualname__ == funcion.__name__
    assert getattr(hpo_experimento, funcion.__name__) is funcion


def test_ejecutar_corrida_esta_en_el_espacio_de_nombres_del_modulo():
    assert hpo_experimento.ejecutar_corrida is ejecutar_corrida


# ================================================================================================
# 2. Corridas de ajuste (R1, R2)
# ================================================================================================

@pytest.mark.parametrize("unidad", UNIDADES)
def test_r1_cada_unidad_corre_ensayos_por_semillas_por_celdas(hpo, espia, unidad):
    llamadas = ajuste_de(espia, unidad)
    n_celdas = len(CELDAS[unidad])
    assert len(llamadas) == ENSAYOS * SEMILLAS * n_celdas
    assert len({huella_de_ensayo(ll) for ll in llamadas}) == ENSAYOS
    por_ensayo_y_celda: dict = {}
    for ll in llamadas:
        clave = (huella_de_ensayo(ll), ll["func"], ll["dim"])
        por_ensayo_y_celda.setdefault(clave, []).append(ll["run_id"])
    assert len(por_ensayo_y_celda) == ENSAYOS * n_celdas
    assert all(sorted(ids) == list(range(SEMILLAS)) for ids in por_ensayo_y_celda.values())
    assert hpo.unidad(unidad)["corridas_de_ajuste"] == len(llamadas)
    assert hpo.unidad(unidad)["ensayos"] == ENSAYOS


def test_r1_el_total_de_seleccion_es_el_que_vio_el_espia(hpo, espia):
    total = sum(ENSAYOS * SEMILLAS * len(celdas) for celdas in CELDAS.values())
    assert total == 24
    assert len(espia.llamadas) == total
    assert hpo.seleccion()["meta"]["corridas_de_ajuste_total"] == total


def test_r2_las_semillas_de_ajuste_son_mayores_o_iguales_que_30(hpo, espia):
    semillas = {ll["base_seed"] + ll["run_id"] for ll in espia.llamadas}
    assert semillas == {BASE_SEED_AJUSTE, BASE_SEED_AJUSTE + 1}     # 1000 y 1001: >= 30


def test_r2_el_experimento_final_usa_las_semillas_de_reporte(hpo):
    nombres = [r for r in hpo.bytes if r.startswith(CARPETA_AFINADA + "runs/")]
    semillas = {int(re.search(r"seed(\d+)\.json$", nombre).group(1)) for nombre in nombres}
    assert semillas == set(range(RUNS))
    assert len(nombres) == 2 * 2 * RUNS          # 2 funciones × 2 métodos × RUNS


def test_las_corridas_de_ajuste_usan_k_2n_el_presupuesto_y_no_graban_frames(hpo, espia):
    for ll in espia.llamadas:
        assert ll["k"] == 2 * ll["dim"]
        assert ll["presupuesto_por_dim"] == PRESUPUESTO
        assert ll["grabar_frames"] is False
        assert "workers" not in ll["cfg"]


def test_el_avance_tiene_una_linea_por_unidad(hpo):
    lineas = [linea for linea in hpo.avance if linea.startswith(hpo_experimento.PREFIJO_AVANCE)]
    assert len(lineas) == len(UNIDADES)
    for numero, (nombre, linea) in enumerate(zip(UNIDADES, lineas), start=1):
        assert f"[{numero}/{len(UNIDADES)}] {nombre}" in linea


# ================================================================================================
# 3. Archivos de la HPO
# ================================================================================================

def test_existen_los_archivos_de_la_hpo(hpo):
    esperados = {f"{CARPETA_HPO}ensayos_{u}.json" for u in UNIDADES} | {
        CARPETA_HPO + "seleccion.json"}
    escritos = {r for r, contenido in hpo.bytes.items()
                if r.startswith(CARPETA_HPO) and contenido is not None}
    assert escritos == esperados


def test_los_archivos_de_la_hpo_no_traen_history_ni_frames_y_pesan_poco(hpo):
    for relativa, contenido in hpo.bytes.items():
        if relativa.startswith(CARPETA_HPO) and contenido is not None:
            texto = contenido.decode("utf-8")
            assert '"history"' not in texto and '"frames"' not in texto, relativa
            assert len(contenido) < 200_000, relativa


def test_el_meta_de_cada_unidad(hpo):
    base = hpo.cfg_original
    for indice, nombre in enumerate(UNIDADES):
        meta = hpo.ensayos(nombre)["meta"]
        assert list(meta) == CLAVES_META
        metodo = "pso" if nombre == "pso" else "gdfijo"
        assert meta["unidad"] == nombre and meta["metodo"] == metodo and meta["indice"] == indice
        assert meta["func"] == (None if nombre == "pso" else nombre.split("_", 1)[1])
        assert meta["celdas"] == [[c.split("_")[0], 2] for c in CELDAS[nombre]]
        assert meta["ensayos"] == ENSAYOS and meta["semillas"] == SEMILLAS
        assert meta["semillas_de_ajuste"] == [BASE_SEED_AJUSTE, BASE_SEED_AJUSTE + 1]
        assert meta["presupuesto_por_dim"] == PRESUPUESTO and meta["k_regla"] == "2n"
        assert meta["espacio"] == base["hpo"]["espacios"][metodo]
        assert meta["bloque_base"] == base["gd" if metodo == "gdfijo" else "pso"]
        assert meta["semilla_busqueda"] == base["hpo"]["semilla_busqueda"]


def test_cada_ensayo_trae_parametros_registros_y_puntaje(hpo):
    for nombre in UNIDADES:
        datos = hpo.ensayos(nombre)
        assert [e["indice"] for e in datos["ensayos"]] == list(range(ENSAYOS))
        for ensayo in datos["ensayos"]:
            assert list(ensayo) == ["indice", "parametros", "por_celda", "puntaje"]
            assert list(ensayo["por_celda"]) == CELDAS[nombre]
            for registro in ensayo["por_celda"].values():
                assert list(registro) == CAMPOS_REGISTRO
                assert all(len(registro[campo]) == SEMILLAS for campo in CAMPOS_REGISTRO)
        rutas = list(datos["ensayos"][0]["parametros"])
        esperadas = (["gd.eta.{func}"] if nombre != "pso"
                     else ["pso.N", "pso.w", "pso.c1", "pso.c2", "pso.vmax_frac"])
        assert rutas == esperadas


def test_el_puntaje_guardado_es_el_de_puntuar_ensayos(hpo):
    for nombre in UNIDADES:
        ensayos = hpo.ensayos(nombre)["ensayos"]
        f_star = {celda: 0.0 for celda in CELDAS[nombre]}
        recalculado = puntuar_ensayos([e["por_celda"] for e in ensayos], f_star)
        assert [e["puntaje"] for e in ensayos] == json.loads(json.dumps(recalculado))
        assert hpo.unidad(nombre)["ganador"] == elegir_ganador(recalculado)


def test_seleccion_por_unidad(hpo):
    seleccion = hpo.seleccion()
    assert list(seleccion["meta"]) == ["ensayos", "semillas", "semillas_de_ajuste",
                                       "presupuesto_por_dim", "semilla_busqueda",
                                       "corridas_de_ajuste_total"]
    assert [u["unidad"] for u in seleccion["unidades"]] == UNIDADES
    for unidad in seleccion["unidades"]:
        assert list(unidad) == ["unidad", "metodo", "func", "celdas", "ensayos", "ganador",
                                "defecto", "elegido", "puntaje_defecto", "puntaje_ganador",
                                "corridas_de_ajuste"]
        ensayos = hpo.ensayos(unidad["unidad"])["ensayos"]
        assert unidad["defecto"] == ensayos[0]["parametros"]
        assert unidad["elegido"] == ensayos[unidad["ganador"]]["parametros"]
        assert unidad["puntaje_defecto"] == ensayos[0]["puntaje"]
        assert unidad["puntaje_ganador"] == ensayos[unidad["ganador"]]["puntaje"]


def test_el_ensayo_0_es_el_defecto_de_la_config(hpo):
    base = hpo.cfg_original
    assert hpo.unidad("pso")["defecto"] == {f"pso.{c}": base["pso"][c]
                                            for c in ("N", "w", "c1", "c2", "vmax_frac")}
    for func in ("rosenbrock", "rastrigin"):
        defecto = hpo.unidad(f"gdfijo_{func}")["defecto"]
        assert defecto == {"gd.eta.{func}": base["gd"]["eta"][func]}


def test_el_ganador_forzado_de_pso_es_el_ensayo_1(hpo):
    # R6: los ensayos 1 y 2 empatan con un puntaje principal estrictamente menor que el del
    # defecto (sin esto el 0 no se desplaza); entre ellos gana el menor índice.
    pso = hpo.unidad("pso")
    assert pso["ganador"] == 1
    assert pso["elegido"]["pso.w"] != W_DEFECTO
    assert pso["puntaje_ganador"]["rango_medio"] < pso["puntaje_defecto"]["rango_medio"]
    puntajes = [e["puntaje"] for e in hpo.ensayos("pso")["ensayos"]]
    assert puntajes[1]["rango_medio"] == puntajes[2]["rango_medio"]


# ================================================================================================
# 4. tuned.yaml
# ================================================================================================

def test_tuned_yaml_tiene_cabecera_y_esta_en_lf(hpo):
    crudo = hpo.bytes[CONFIG_AFINADA]
    assert b"\r" not in crudo and crudo.endswith(b"\n")
    lineas = crudo.decode("utf-8").splitlines()
    cabecera = [linea for linea in lineas if linea.startswith("#")]
    assert lineas[0].startswith("#") and len(cabecera) >= 3
    texto = "\n".join(cabecera)
    assert hpo_experimento.comando_hpo(RUTA_CONFIG, OVERRIDES) in texto
    for override in OVERRIDES:
        assert override in texto
    assert "a mano" in texto
    assert CARPETA_HPO + "seleccion.json" in texto


def test_el_comando_de_la_cabecera_omite_workers_y_reanudar_y_cita_lo_que_lleva_espacios():
    comando = hpo_experimento.comando_hpo(
        "configs/part1/base.yaml", ["runs=2", "workers=4", " workers = 2", "func=[a, b]",
                                    "hpo.reanudar=true", "hpo . reanudar=false"])
    assert hpo_experimento.CLAVES_SIN_EFECTO == ("workers", "hpo.reanudar")
    assert comando == ('python run.py hpo --config configs/part1/base.yaml --set runs=2 '
                       '--set "func=[a, b]"')


def test_tuned_yaml_hereda_de_la_base_con_ruta_relativa(hpo):
    datos = cargar_yaml(hpo.texto_de(CONFIG_AFINADA))
    assert list(datos)[:3] == ["hereda", "salida", "tablas"]
    assert datos["hereda"] == "base.yaml"
    assert datos["salida"] == CARPETA_AFINADA.rstrip("/")
    assert datos["tablas"] == TABLAS_AFINADAS.rstrip("/")


def test_tuned_yaml_es_config_afinada_de_los_ganadores(hpo):
    unidades = construir_unidades(hpo.cfg_original)
    ganadores = [(u, hpo.unidad(u.nombre)["elegido"]) for u in unidades]
    esperado = config_afinada(hpo.cfg_original, ganadores, hereda="base.yaml")
    assert cargar_yaml(hpo.texto_de(CONFIG_AFINADA)) == esperado
    assert esperado["pso"] == {ruta.split(".")[1]: valor
                               for ruta, valor in hpo.unidad("pso")["elegido"].items()
                               if valor != hpo.unidad("pso")["defecto"][ruta]}


def test_tuned_yaml_solo_trae_lo_que_cambio(hpo):
    """gdfijo_rastrigin gana con el ensayo 0 (forzado): su η no aparece en tuned.yaml."""
    assert hpo.unidad("gdfijo_rastrigin")["ganador"] == 0
    datos = cargar_yaml(hpo.texto_de(CONFIG_AFINADA))
    assert "rastrigin" not in datos.get("gd", {}).get("eta", {})
    base = hpo.cfg_original
    for bloque in set(datos) - {"hereda", "salida", "tablas"}:
        pendientes = [(datos[bloque], base[bloque])]
        while pendientes:
            afinado, defecto = pendientes.pop()
            for clave, valor in afinado.items():
                if isinstance(valor, dict):
                    pendientes.append((valor, defecto[clave]))
                else:
                    assert valor != defecto[clave], (bloque, clave)


def test_tuned_yaml_releido_con_load_config(hpo):
    afinada = load_config(hpo.carpeta / CONFIG_AFINADA)
    for clave in ("N", "w", "c1", "c2", "vmax_frac"):
        assert afinada["pso"][clave] == hpo.unidad("pso")["elegido"][f"pso.{clave}"]
    for func in ("rosenbrock", "rastrigin"):
        elegido = hpo.unidad(f"gdfijo_{func}")["elegido"]["gd.eta.{func}"]
        assert afinada["gd"]["eta"][func] == elegido
    assert afinada["runs"] == load_config(RUTA_BASE)["runs"]      # el resto viene de la base


@pytest.mark.parametrize("origen, destino, esperado", [
    ("configs/part1/base.yaml", "configs/part1/tuned.yaml", "base.yaml"),
    ("configs/part1/hpo_demo.yaml", "results/data/part1_hpo_demo/tuned.yaml",
     "../../../configs/part1/hpo_demo.yaml"),
    ("a/b/c.yaml", "a/d.yaml", "b/c.yaml"),
])
def test_hereda_relativo_sin_correr_nada(tmp_path, monkeypatch, origen, destino, esperado):
    monkeypatch.chdir(tmp_path)
    assert hpo_experimento.hereda_relativo(origen, destino) == esperado
    assert list(tmp_path.iterdir()) == []


# ================================================================================================
# 5. Experimento final y comparación
# ================================================================================================

def test_el_experimento_final_usa_los_valores_afinados(hpo):
    elegido = hpo.unidad("pso")["elegido"]
    for func in ("rosenbrock", "rastrigin"):
        nombre = run_filename(func, 2, "pso", 0)
        afinada = hpo.leer(CARPETA_AFINADA + "runs/" + nombre)["config"]
        defecto = hpo.leer("results/data/part1/runs/" + nombre)["config"]
        for ruta, valor in elegido.items():
            assert afinada["pso"][ruta.split(".")[1]] == valor
        assert defecto["pso"]["w"] == W_DEFECTO != afinada["pso"]["w"]
        eta = hpo.unidad(f"gdfijo_{func}")["elegido"]["gd.eta.{func}"]
        gd = hpo.leer(CARPETA_AFINADA + "runs/" + run_filename(func, 2, "gdfijo", 0))["config"]
        assert gd["gd"]["eta"][func] == eta


def test_el_experimento_final_escribe_su_summary_y_sus_tablas(hpo):
    for relativa in (CARPETA_AFINADA + "summary.json", TABLAS_AFINADAS + "tabla_principal.csv",
                     TABLAS_AFINADAS + "tabla_sensibilidad_k1.csv"):
        assert relativa in hpo.bytes


def _filas(contenido: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(contenido.decode("utf-8"), newline="")))


def test_comparacion_csv_una_fila_por_configuracion_en_orden(hpo):
    crudo = hpo.bytes[TABLAS_AFINADAS + "comparacion.csv"]
    assert b"\r" not in crudo and b"None" not in crudo
    assert crudo.decode("utf-8").splitlines()[0] == ",".join(COLUMNAS_COMPARACION)
    filas = _filas(crudo)
    orden = [(f["func"], int(f["dim"]), f["method"]) for f in filas]
    assert orden == [("rosenbrock", 2, "gdfijo"), ("rosenbrock", 2, "pso"),
                     ("rastrigin", 2, "gdfijo"), ("rastrigin", 2, "pso")]


def test_comparacion_csv_coincide_con_comparar_resumenes(hpo):
    esperadas = comparar_resumenes(hpo.leer("results/data/part1/summary.json"),
                                   hpo.leer(CARPETA_AFINADA + "summary.json"))
    filas = _filas(hpo.bytes[TABLAS_AFINADAS + "comparacion.csv"])
    assert len(filas) == len(esperadas) == 4
    for fila, esperada in zip(filas, esperadas):
        for columna in COLUMNAS_COMPARACION:
            valor = esperada[columna]
            assert fila[columna] == ("" if valor is None else str(valor)), columna


def test_el_texto_devuelto_es_la_tabla_sin_juicios(hpo):
    texto = hpo.texto
    for metodo in ("gdfijo", "pso"):
        assert metodo in texto
    for juicio in ("mejora", "empeora", "mejor", "peor"):
        assert juicio not in texto.lower()
    lineas = [linea for linea in texto.splitlines() if " | " in linea]
    assert len(lineas) == 1 + 4
    assert len({len(linea) for linea in lineas}) == 1          # columnas alineadas


def test_r8_no_toca_los_resultados_por_defecto(hpo):
    for relativa, contenido in hpo.antes.items():
        if relativa.startswith(CARPETAS_POR_DEFECTO):
            assert hpo.bytes[relativa] == contenido, relativa
    nuevos = [r for r in hpo.bytes if r not in hpo.antes]
    assert not [r for r in nuevos if r.startswith(CARPETAS_POR_DEFECTO)]


def test_solo_escribe_en_las_carpetas_de_la_hpo(hpo):
    permitidas = (CARPETA_HPO, CARPETA_AFINADA, TABLAS_AFINADAS, CONFIG_AFINADA)
    nuevos = [r for r, c in hpo.bytes.items() if r not in hpo.antes and c is not None]
    assert nuevos
    assert [r for r in nuevos if not r.startswith(permitidas)] == []
    cambiados = [r for r, c in hpo.antes.items() if c is not None and hpo.bytes.get(r) != c]
    assert cambiados == []
    assert not [r for r in hpo.bytes if r.endswith(".tmp")]


def test_la_config_de_entrada_no_se_modifica(hpo):
    assert hpo.cfg == hpo.cfg_original


# ================================================================================================
# 6. Paralelismo
# ================================================================================================

@pytest.fixture(scope="module")
def dos_ejecuciones(tmp_path_factory) -> tuple[Ejecucion, Ejecucion]:
    serie = preparar_carpeta(tmp_path_factory.mktemp("w1"))
    paralelo = preparar_carpeta(tmp_path_factory.mktemp("w2"))
    return (Ejecucion(serie, OVERRIDES_PEQUENOS + ["workers=1"]),
            Ejecucion(paralelo, OVERRIDES_PEQUENOS + ["workers=2"]))


def test_workers_1_y_2_dan_los_mismos_bytes(dos_ejecuciones):
    serie, paralelo = dos_ejecuciones
    assert serie.cfg["workers"] == 1 and paralelo.cfg["workers"] == 2
    for relativa in [r for r in serie.bytes if r.startswith(CARPETA_HPO)] + [CONFIG_AFINADA]:
        assert serie.bytes[relativa] == paralelo.bytes[relativa], relativa
    assert sorted(serie.bytes) == sorted(paralelo.bytes)
    distintos = [r for r in serie.bytes if serie.bytes[r] != paralelo.bytes[r]]
    assert distintos == []
    assert serie.texto == paralelo.texto


# ================================================================================================
# 7. Reanudar
# ================================================================================================

def _correr(carpeta: Path, overrides) -> tuple[Ejecucion, Espia]:
    espia = Espia()
    return Ejecucion(carpeta, overrides, espia=espia, con_defecto=False), espia


def test_reanudar_reutiliza_las_unidades_con_meta_igual_y_recorre_las_que_cambiaron(
        tmp_path_factory):
    carpeta = preparar_carpeta(tmp_path_factory.mktemp("reanudar"))
    with pytest.MonkeyPatch.context() as parche:
        parche.chdir(carpeta)
        ejecutar_experimento(cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS), informar=silencio)

    primera, espia_1 = _correr(carpeta, OVERRIDES_PEQUENOS)
    assert len(espia_1.llamadas) == 2 * SEMILLAS * 2          # gdfijo_rastrigin y pso

    # Sin cambios y con reanudar: no corre nada de la HPO y escribe lo mismo.
    segunda, espia_2 = _correr(carpeta, OVERRIDES_PEQUENOS + ["hpo.reanudar=true"])
    assert espia_2.llamadas == []
    for relativa in (CARPETA_HPO + "seleccion.json", CARPETA_HPO + "ensayos_pso.json",
                     CONFIG_AFINADA):
        assert segunda.bytes[relativa] == primera.bytes[relativa]
    # La cabecera de tuned.yaml no cita hpo.reanudar: reanudada es idéntica a la limpia.
    assert "reanudar=" not in segunda.texto_de(CONFIG_AFINADA)
    reutilizadas = [linea for linea in segunda.avance if "reutiliza" in linea]
    assert len(reutilizadas) == 2

    # Cambia el espacio de pso: solo pso se vuelve a correr, con aviso.
    tercera, espia_3 = _correr(carpeta, OVERRIDES_PEQUENOS + [
        "hpo.reanudar=true", "hpo.espacios.pso.w.max=0.9"])
    assert {ll["method"] for ll in espia_3.llamadas} == {"pso"}
    assert len(espia_3.llamadas) == 2 * SEMILLAS
    avisos = [linea for linea in tercera.avance if "aviso" in linea]
    assert len(avisos) == 1 and "pso" in avisos[0] and "meta" in avisos[0]
    assert tercera.ensayos("pso")["meta"]["espacio"]["w"]["max"] == 0.9
    assert (tercera.bytes[CARPETA_HPO + "ensayos_gdfijo_rastrigin.json"]
            == primera.bytes[CARPETA_HPO + "ensayos_gdfijo_rastrigin.json"])

    # Sin reanudar: vuelve a correr todo aunque los archivos existan.
    _, espia_4 = _correr(carpeta, OVERRIDES_PEQUENOS)
    assert len(espia_4.llamadas) == len(espia_1.llamadas)


def test_reanudar_con_un_archivo_ilegible_lo_vuelve_a_correr(tmp_path_factory):
    carpeta = preparar_carpeta(tmp_path_factory.mktemp("ilegible"))
    with pytest.MonkeyPatch.context() as parche:
        parche.chdir(carpeta)
        ejecutar_experimento(cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS), informar=silencio)
    ruta = carpeta / CARPETA_HPO / "ensayos_pso.json"
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{roto", encoding="utf-8")
    ejecucion, espia = _correr(carpeta, OVERRIDES_PEQUENOS + ["hpo.reanudar=true"])
    assert len(espia.llamadas) == 2 * 2 * SEMILLAS
    assert any("aviso" in linea and "pso" in linea for linea in ejecucion.avance)
    assert ejecucion.ensayos("pso")["meta"]["unidad"] == "pso"


def test_reanudar_con_puntajes_de_otro_formato_los_recalcula_sin_correr(tmp_path_factory):
    """Los registros mandan: un puntaje viejo o alterado se recalcula y se reescribe."""
    carpeta = preparar_carpeta(tmp_path_factory.mktemp("puntajes_viejos"))
    with pytest.MonkeyPatch.context() as parche:
        parche.chdir(carpeta)
        ejecutar_experimento(cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS), informar=silencio)
    primera, _ = _correr(carpeta, OVERRIDES_PEQUENOS)
    relativa = CARPETA_HPO + "ensayos_pso.json"
    datos = primera.ensayos("pso")
    for ensayo in datos["ensayos"]:
        ensayo["puntaje"] = {"indice": ensayo["indice"], "rango_medio": 1.0}   # formato viejo
    save_json(carpeta / relativa, datos)

    segunda, espia = _correr(carpeta, OVERRIDES_PEQUENOS + ["hpo.reanudar=true"])
    assert espia.llamadas == []
    assert segunda.bytes[relativa] == primera.bytes[relativa]
    assert segunda.bytes[CARPETA_HPO + "seleccion.json"] == (
        primera.bytes[CARPETA_HPO + "seleccion.json"])
    notas = [linea for linea in segunda.avance if linea.startswith("nota")]
    assert len(notas) == 1 and "ensayos_pso.json" in notas[0] and "sin correr" in notas[0]


def _datos_y_unidad(hpo: Ejecucion, nombre: str = "pso"):
    unidad = next(u for u in construir_unidades(hpo.cfg_original) if u.nombre == nombre)
    datos = hpo.ensayos(nombre)
    return datos, datos["meta"], unidad


def _sin_parametros(datos):
    del datos["ensayos"][1]["parametros"]


def _ensayo_de_menos(datos):
    datos["ensayos"].pop()


def _celda_renombrada(datos):
    por_celda = datos["ensayos"][0]["por_celda"]
    por_celda["otra_2d"] = por_celda.pop("rastrigin_2d")


def _semilla_de_menos(datos):
    datos["ensayos"][0]["por_celda"]["rastrigin_2d"]["n_f"].pop()


def _evals_sin_exito(datos):
    registro = datos["ensayos"][0]["por_celda"]["rastrigin_2d"]
    registro["f_best"][0] = 5.0                    # sin éxito, pero con evaluaciones
    registro[f"evals_hasta_exito_{SUFIJO}"][0] = 10.0


def _ensayos_no_lista(datos):
    datos["ensayos"] = 5


def _puntaje_viejo(datos):
    for ensayo in datos["ensayos"]:
        ensayo["puntaje"] = {}


@pytest.mark.parametrize("alterar, fragmento", [
    (None, None),
    (_puntaje_viejo, None),
    (_ensayo_de_menos, "no concuerdan con su meta"),
    (_celda_renombrada, "no concuerdan con su meta"),
    (_semilla_de_menos, "no concuerdan con su meta"),
    (_sin_parametros, "mal formado"),
    (_ensayos_no_lista, "mal formado"),
    (_evals_sin_exito, "no se pueden puntuar"),
], ids=["intacto", "puntaje-viejo", "ensayo-de-menos", "celda-renombrada", "semilla-de-menos",
        "sin-parametros", "ensayos-no-lista", "evals-sin-exito"])
def test_motivo_para_no_reutilizar_cada_rama(hpo, alterar, fragmento):
    datos, meta, unidad = _datos_y_unidad(hpo)
    if alterar is not None:
        alterar(datos)
    motivo = hpo_experimento._motivo_para_no_reutilizar(datos, meta, unidad)
    if fragmento is None:
        assert motivo is None
    else:
        assert fragmento in motivo


def test_motivo_para_no_reutilizar_con_meta_distinto_o_sin_mapeo(hpo):
    datos, meta, unidad = _datos_y_unidad(hpo)
    otro = dict(meta, semillas=meta["semillas"] + 1)
    assert "meta" in hpo_experimento._motivo_para_no_reutilizar(datos, otro, unidad)
    assert "meta" in hpo_experimento._motivo_para_no_reutilizar([1], meta, unidad)


# ================================================================================================
# 8. Validación
# ================================================================================================

CASOS_INVALIDOS = [
    ("semillas_cero", ["hpo.semillas=0"], ValueError, "hpo.semillas"),
    ("solape_r2", ["hpo.base_seed=1"], ValueError, "solapan"),
    ("set_salida", ["salida=otra"], ValueError, "salida"),
    ("set_tablas", ["tablas=otra"], ValueError, "tablas"),
    ("set_ruta_afinada", ["pso.w=0.5"], ValueError, "pso.w"),
    ("set_ruta_afinada_func", ["gd.eta.rastrigin=0.001"], ValueError, "gd.eta.rastrigin"),
    ("config_salida_igual", ["hpo.config_salida=configs/part1/base.yaml"], ValueError,
     "config_salida"),
    ("salida_afinada_dentro_de_salida", ["hpo.salida_afinada=results/data/part1/afinado"],
     ValueError, "R8"),
]


def _comprobar_rechazo(carpeta: Path, cfg, ruta, overrides, error, fragmento, capsys) -> None:
    """ejecutar_hpo y manejador_hpo rechazan sin crear ni cambiar nada en `carpeta`."""
    antes = foto(carpeta)
    with pytest.raises(error, match=fragmento):
        ejecutar_hpo(cfg, informar=silencio, ruta_config=ruta, overrides=overrides)
    assert foto(carpeta) == antes
    capsys.readouterr()
    assert manejador_hpo(cfg, ruta, overrides) == 2
    salida = capsys.readouterr()
    assert "run.py hpo: error: configuración inválida" in salida.err
    assert re.search(fragmento, salida.err)
    assert salida.out == ""
    assert foto(carpeta) == antes


@pytest.mark.parametrize("cambios, error, fragmento", [c[1:] for c in CASOS_INVALIDOS],
                         ids=[c[0] for c in CASOS_INVALIDOS])
def test_config_invalida_no_escribe_nada(tmp_path, monkeypatch, capsys, cambios, error,
                                         fragmento):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    overrides = OVERRIDES_PEQUENOS + cambios
    _comprobar_rechazo(tmp_path, cfg_de(RUTA_CONFIG, overrides), RUTA_CONFIG, overrides, error,
                       fragmento, capsys)


def test_config_que_no_coincide_con_config_y_set(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS)
    cfg["runs"] = 3
    _comprobar_rechazo(tmp_path, cfg, RUTA_CONFIG, OVERRIDES_PEQUENOS, ValueError,
                       "no coincide con --config", capsys)


def test_ruta_de_config_inexistente(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS)
    _comprobar_rechazo(tmp_path, cfg, "configs/part1/no_existe.yaml", OVERRIDES_PEQUENOS,
                       FileNotFoundError, "no_existe.yaml", capsys)


def test_sin_summary_por_defecto_pide_correr_part1(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS)
    _comprobar_rechazo(tmp_path, cfg, RUTA_CONFIG, OVERRIDES_PEQUENOS, FileNotFoundError,
                       re.escape("python run.py part1 --config configs/part1/base.yaml"), capsys)


def test_summary_por_defecto_con_otro_meta(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS)
    save_json(tmp_path / "results/data/part1/summary.json",
              {"meta": {"semillas": [0, 1, 2], "presupuesto_por_dim": PRESUPUESTO,
                        "func": ["rastrigin"], "dim": [2], "methods": ["gdfijo", "pso"]}})
    _comprobar_rechazo(tmp_path, cfg, RUTA_CONFIG, OVERRIDES_PEQUENOS, ValueError, "semillas",
                       capsys)


def test_config_salida_en_la_cadena_de_herencia(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "configs/part1/prueba.yaml").write_text("hereda: base.yaml\nruns: 2\n",
                                                         encoding="utf-8")
    overrides = OVERRIDES_PEQUENOS + ["hpo.config_salida=configs/part1/base.yaml"]
    cfg = cfg_de("configs/part1/prueba.yaml", overrides)
    _comprobar_rechazo(tmp_path, cfg, "configs/part1/prueba.yaml", overrides, ValueError,
                       "hereda", capsys)


def test_overrides_debe_ser_una_lista_de_textos(tmp_path, monkeypatch):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, ["runs=2"])
    with pytest.raises(TypeError, match="overrides"):
        validar_ejecucion(cfg, RUTA_CONFIG, "runs=2")
    with pytest.raises(TypeError, match="overrides"):
        validar_ejecucion(cfg, RUTA_CONFIG, [2])


def test_validar_ejecucion_acepta_una_config_valida_y_no_escribe(tmp_path, monkeypatch):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    cfg = cfg_de(RUTA_CONFIG, OVERRIDES_PEQUENOS)
    ejecutar_experimento(cfg, informar=silencio)
    antes = foto(tmp_path)
    assert validar_ejecucion(cfg, RUTA_CONFIG, OVERRIDES_PEQUENOS) is None
    assert foto(tmp_path) == antes


# ================================================================================================
# 9. Demo
# ================================================================================================

PROHIBIDAS = ("results/data/part1", "results/tables/part1", "results/data/part1_tuned",
              "results/tables/part1_tuned")


def test_el_demo_tiene_carpetas_propias():
    demo = load_config(RUTA_DEMO_HPO)
    assert demo["func"] == ["rastrigin"] and demo["dim"] == [2]
    assert demo["methods"] == ["pso", "gdfijo"] and demo["runs"] == 5
    hpo = demo["hpo"]
    assert hpo["ensayos"] == 6 and hpo["semillas"] == 3
    assert Path(hpo["config_salida"]) != Path("configs/part1/tuned.yaml")
    carpetas = [demo["salida"], demo["tablas"], hpo["salida"], hpo["salida_afinada"],
                hpo["tablas_afinada"], hpo["config_salida"]]
    for carpeta in carpetas:
        ruta = Path(carpeta)
        for prohibida in map(Path, PROHIBIDAS):
            assert ruta != prohibida and prohibida not in ruta.parents, carpeta


def test_el_demo_pasa_la_validacion(tmp_path, monkeypatch):
    """En una copia (cwd temporal sin resultados): el demo no exige su resumen por defecto."""
    preparar_carpeta(tmp_path, RUTA_DEMO_HPO)
    monkeypatch.chdir(tmp_path)
    cfg = load_config(RUTA_CONFIG_DEMO)
    assert cfg == load_config(RUTA_DEMO_HPO)
    assert validar_ejecucion(cfg, RUTA_CONFIG_DEMO, []) is None
    assert hpo_experimento.hereda_relativo(RUTA_CONFIG_DEMO, cfg["hpo"]["config_salida"]) == (
        "../../../configs/part1/hpo_demo.yaml")


def test_el_demo_con_un_resumen_por_defecto_de_otro_meta_dice_como_regenerarlo(tmp_path,
                                                                               monkeypatch):
    preparar_carpeta(tmp_path, RUTA_DEMO_HPO)
    monkeypatch.chdir(tmp_path)
    cfg = load_config(RUTA_CONFIG_DEMO)
    summary = Path(cfg["salida"]) / "summary.json"
    save_json(summary, {"meta": {"semillas": [0, 1], "presupuesto_por_dim": 10000,
                                 "func": ["rastrigin"], "dim": [2],
                                 "methods": ["pso", "gdfijo"]}})
    with pytest.raises(ValueError, match="borra") as error:
        validar_ejecucion(cfg, RUTA_CONFIG_DEMO, [])
    assert "semillas" in str(error.value)


def test_el_archivo_del_demo_en_lf_hereda_de_la_base():
    crudo = RUTA_DEMO_HPO.read_bytes()
    assert b"\r" not in crudo
    texto = crudo.decode("utf-8")
    assert texto.startswith("#")
    assert cargar_yaml(texto)["hereda"] == "base.yaml"
    assert all(len(linea) <= LARGO_MAXIMO for linea in texto.splitlines())


def _huella_del_repo() -> dict:
    rutas = [RAIZ / CONFIG_AFINADA]
    for carpeta in PROHIBIDAS:
        rutas.append(RAIZ / carpeta)
        rutas.extend(sorted((RAIZ / carpeta).rglob("*")))
    return {str(r): (r.stat().st_mtime_ns if r.exists() else None) for r in rutas}


def test_demo_de_punta_a_punta_reducido(tmp_path_factory):
    huella = _huella_del_repo()
    carpeta = preparar_carpeta(tmp_path_factory.mktemp("demo"), RUTA_DEMO_HPO)
    overrides = ["presupuesto_por_dim=200", "hpo.ensayos=2", "hpo.semillas=2", "runs=2"]
    demo = Ejecucion(carpeta, overrides, ruta=RUTA_CONFIG_DEMO, con_defecto=False)
    assert _huella_del_repo() == huella
    assert any("resumen por defecto" in linea for linea in demo.avance)
    for relativa in ("results/data/part1_hpo_demo/experimento/summary.json",
                     "results/data/part1_hpo_demo/afinado/summary.json",
                     "results/data/part1_hpo_demo/seleccion.json",
                     "results/data/part1_hpo_demo/ensayos_pso.json",
                     "results/data/part1_hpo_demo/ensayos_gdfijo_rastrigin.json",
                     "results/tables/part1_hpo_demo/afinado/comparacion.csv"):
        assert relativa in demo.bytes, relativa
    tuned = cargar_yaml(demo.texto_de("results/data/part1_hpo_demo/tuned.yaml"))
    assert tuned["hereda"] == "../../../configs/part1/hpo_demo.yaml"
    assert CONFIG_AFINADA not in demo.bytes
    for relativa in map(Path, demo.bytes):
        for prohibida in map(Path, PROHIBIDAS):
            assert relativa != prohibida and prohibida not in relativa.parents, relativa
    filas = _filas(demo.bytes["results/tables/part1_hpo_demo/afinado/comparacion.csv"])
    assert [(f["func"], f["method"]) for f in filas] == [("rastrigin", "pso"),
                                                         ("rastrigin", "gdfijo")]
    afinado = demo.leer("results/data/part1_hpo_demo/afinado/summary.json")
    assert afinado["meta"]["runs"] == 2 and afinado["meta"]["methods"] == ["pso", "gdfijo"]


def test_carpeta_de_demo_detectada_por_un_padre():
    assert hpo_experimento.es_demo({"salida": "results/data/part1_hpo_demo/experimento"})
    assert not hpo_experimento.es_demo({"salida": "results/data/part1"})
    assert not hpo_experimento.es_demo({"salida": "results/data/part1_demo"})


# ================================================================================================
# 10. comparar_resumenes con datos hechos a mano
# ================================================================================================

META = {"runs": 5, "base_seed": 0, "semillas": [0, 1, 2, 3, 4], "presupuesto_por_dim": 10000,
        "func": ["rastrigin"], "dim": [2], "methods": ["pso", "gdfijo"]}


def _entrada(method, mediana, media, tasa_4, tasa_6, evals_4):
    return {"func": "rastrigin", "dim": 2, "method": method,
            "f_final": {"media": media, "desv": 0.1, "mediana": mediana, "mejor": 0.0,
                        "peor": 3.0},
            "tasa_exito": {"1e-04": tasa_4, "1e-02": 1.0, "1e-06": tasa_6},
            "evals_hasta_exito_medio": {"1e-04": evals_4, "1e-02": 10.0, "1e-06": None}}


def _resumenes():
    defecto = {"meta": copy.deepcopy(META), "configuraciones": [
        _entrada("pso", 0.5, 0.7, 0.4, 0.2, 1500.0),
        _entrada("gdfijo", 1.0, 1.2, 0.0, 0.0, None)]}
    # El orden de las configuraciones del afinado está invertido: se emparejan por clave.
    afinado = {"meta": copy.deepcopy(META), "configuraciones": [
        _entrada("gdfijo", 0.75, 1.5, 0.2, 0.0, 2000.0),
        _entrada("pso", 0.25, 0.3, 0.8, 0.6, 900.0)]}
    return defecto, afinado


def test_comparar_resumenes_a_mano():
    defecto, afinado = _resumenes()
    filas = comparar_resumenes(defecto, afinado)
    # Cambio de tasa = afinado − defecto: pso 0.8 − 0.4 = 0.4; gdfijo 0.2 − 0.0 = 0.2.
    assert filas == [
        {"func": "rastrigin", "dim": 2, "method": "pso",
         "f_final_mediana_defecto": 0.5, "f_final_mediana_afinado": 0.25,
         "f_final_media_defecto": 0.7, "f_final_media_afinado": 0.3,
         "tasa_exito_1e-04_defecto": 0.4, "tasa_exito_1e-04_afinado": 0.8,
         "tasa_exito_1e-06_defecto": 0.2, "tasa_exito_1e-06_afinado": 0.6,
         "evals_hasta_exito_1e-04_defecto": 1500.0, "evals_hasta_exito_1e-04_afinado": 900.0,
         "cambio_tasa_exito_1e-04": 0.4},
        {"func": "rastrigin", "dim": 2, "method": "gdfijo",
         "f_final_mediana_defecto": 1.0, "f_final_mediana_afinado": 0.75,
         "f_final_media_defecto": 1.2, "f_final_media_afinado": 1.5,
         "tasa_exito_1e-04_defecto": 0.0, "tasa_exito_1e-04_afinado": 0.2,
         "tasa_exito_1e-06_defecto": 0.0, "tasa_exito_1e-06_afinado": 0.0,
         "evals_hasta_exito_1e-04_defecto": None, "evals_hasta_exito_1e-04_afinado": 2000.0,
         "cambio_tasa_exito_1e-04": 0.2},
    ]
    for fila in filas:
        assert list(fila) == COLUMNAS_COMPARACION


def test_las_columnas_de_la_comparacion():
    assert COLUMNAS_COMPARACION == [
        "func", "dim", "method", "f_final_mediana_defecto", "f_final_mediana_afinado",
        "f_final_media_defecto", "f_final_media_afinado", "tasa_exito_1e-04_defecto",
        "tasa_exito_1e-04_afinado", "tasa_exito_1e-06_defecto", "tasa_exito_1e-06_afinado",
        "evals_hasta_exito_1e-04_defecto", "evals_hasta_exito_1e-04_afinado",
        "cambio_tasa_exito_1e-04"]


@pytest.mark.parametrize("clave, valor", [
    ("semillas", [0, 1, 2, 3, 5]), ("presupuesto_por_dim", 200), ("func", ["rosenbrock"]),
    ("dim", [3]), ("methods", ["pso"])])
def test_metas_que_no_coinciden_dan_error(clave, valor):
    defecto, afinado = _resumenes()
    afinado["meta"][clave] = valor
    with pytest.raises(ValueError, match=clave):
        comparar_resumenes(defecto, afinado)


def test_una_configuracion_que_falta_en_el_afinado_da_error():
    defecto, afinado = _resumenes()
    afinado["configuraciones"].pop()
    with pytest.raises(ValueError, match="pso"):
        comparar_resumenes(defecto, afinado)


def test_comparar_resumenes_no_modifica_las_entradas():
    defecto, afinado = _resumenes()
    copias = copy.deepcopy((defecto, afinado))
    comparar_resumenes(defecto, afinado)
    assert (defecto, afinado) == copias


# ================================================================================================
# 11. CLI
# ================================================================================================

def test_registro_del_subcomando_hpo():
    sub = cli.SUBCOMANDOS["hpo"]
    assert sub.usa_config is True and sub.con_origen is True
    assert sub.manejador.__module__ == "src.common.cli"
    assert sub.manejador.__qualname__ == sub.manejador.__name__
    for nombre in ("part1", "part2", "figures"):
        assert cli.SUBCOMANDOS[nombre].con_origen is False


def test_cli_hpo_entrega_config_ruta_y_sets(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    recibido = {}

    def falso(cfg, ruta, overrides):
        recibido.update(cfg=cfg, ruta=ruta, overrides=overrides)
        return 0

    monkeypatch.setitem(cli.SUBCOMANDOS, "hpo", cli.SUBCOMANDOS["hpo"]._replace(manejador=falso))
    sets = ["runs=2", "hpo.ensayos=4"]
    argv = ["hpo", "--config", RUTA_CONFIG]
    for valor in sets:
        argv += ["--set", valor]
    assert cli.main(argv) == 0
    assert recibido["ruta"] == RUTA_CONFIG and recibido["overrides"] == sets
    assert recibido["cfg"] == cfg_de(RUTA_CONFIG, sets)
    assert "Configuración final resuelta" in capsys.readouterr().out


def test_cli_un_subcomando_sin_origen_recibe_solo_la_config(tmp_path, monkeypatch):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    recibido = []

    def falso(cfg):
        recibido.append(cfg)
        return 0

    monkeypatch.setitem(cli.SUBCOMANDOS, "part1",
                        cli.SUBCOMANDOS["part1"]._replace(manejador=falso))
    assert cli.main(["part1", "--config", RUTA_CONFIG, "--set", "runs=3"]) == 0
    assert recibido[0]["runs"] == 3


def test_cli_hpo_de_punta_a_punta(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    sets = ["presupuesto_por_dim=200", "runs=2", "func=[rastrigin]", "dim=[2]",
            "methods=[gdfijo]", "hpo.ensayos=2", "hpo.semillas=2"]
    ejecutar_experimento(cfg_de(RUTA_CONFIG, sets), informar=silencio)
    argv = ["hpo", "--config", RUTA_CONFIG]
    for valor in sets:
        argv += ["--set", valor]
    assert cli.main(argv) == 0
    salida = capsys.readouterr().out
    assert hpo_experimento.TITULO_COMPARACION in salida
    assert (tmp_path / TABLAS_AFINADAS / "comparacion.csv").is_file()
    assert cargar_yaml((tmp_path / CONFIG_AFINADA).read_text(encoding="utf-8"))["hereda"] == (
        "base.yaml")


def test_cli_hpo_invalida_sale_con_codigo_2(tmp_path, monkeypatch, capsys):
    preparar_carpeta(tmp_path)
    monkeypatch.chdir(tmp_path)
    antes = foto(tmp_path)
    argv = ["hpo", "--config", RUTA_CONFIG, "--set", "hpo.semillas=0"]
    assert cli.main(argv) == 2
    assert "hpo.semillas" in capsys.readouterr().err
    assert foto(tmp_path) == antes


def test_la_ayuda_lista_hpo(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    salida = capsys.readouterr().out
    assert "hpo" in salida and "hiperparámetros" in salida


def test_la_cabecera_del_cli_documenta_hpo():
    assert "python run.py hpo --config configs/part1/base.yaml" in cli.__doc__


def test_importar_el_cli_no_carga_numpy_ni_la_hpo():
    codigo = (
        "import sys\n"
        "import src.common.cli as cli\n"
        "cli.build_parser()\n"
        "cargados = [m for m in ('numpy', 'src.part1.hpo_experimento', 'src.part1.hpo', "
        "'src.part1') if m in sys.modules]\n"
        "print(cargados)\n"
    )
    res = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True,
                         encoding="utf-8", check=False)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == "[]"


def test_la_ayuda_de_hpo_no_carga_numpy():
    codigo = (
        "import sys\n"
        "from src.common.cli import main\n"
        "try:\n"
        "    main(['hpo', '--help'])\n"
        "except SystemExit:\n"
        "    pass\n"
        "print('NUMPY' if 'numpy' in sys.modules else 'LIMPIO')\n"
    )
    res = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True,
                         encoding="utf-8", check=False)
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().endswith("LIMPIO")


# ================================================================================================
# 12. Higiene
# ================================================================================================

@pytest.mark.parametrize("ruta", [RUTA_MODULO, RUTA_PRUEBAS],
                         ids=["hpo_experimento.py", "test_hpo_experimento.py"])
def test_lineas_de_hasta_100_caracteres_en_lf(ruta):
    crudo = ruta.read_bytes()
    assert b"\r" not in crudo
    lineas = crudo.decode("utf-8").splitlines()
    largas = [i + 1 for i, linea in enumerate(lineas) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    celda_actual = None
    lineas = RUTA_MODULO.read_text(encoding="utf-8").splitlines()
    for numero, linea in enumerate(lineas, start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_markdown_con_los_nombres_publicos():
    texto = RUTA_MODULO.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in ("validar_ejecucion", "ejecutar_hpo", "comparar_resumenes", "manejador_hpo",
                   "hereda_relativo", "es_demo", "Archivos que escribe"):
        assert nombre in cabecera, nombre


def test_el_modulo_no_usa_azar_global_ni_cuenta_evaluaciones():
    texto = RUTA_MODULO.read_text(encoding="utf-8")
    for prohibido in ("np.random", "import random", "CountedProblem(", "default_rng"):
        assert prohibido not in texto
