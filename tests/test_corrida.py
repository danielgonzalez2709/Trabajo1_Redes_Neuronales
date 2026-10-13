"""Pruebas de `src/part1/corrida.py` (T1.7-A; Spec §5.1, §5.4, §6.2 y §6.3): UNA corrida.

Grupos, de lo más pequeño a lo más grande:

    0. constantes y despachador   -> METODOS, METODOS_GD, obtener_optimizador
    1. forma del diccionario      -> claves de §5.4, semilla efectiva, k y presupuesto
    2. configuración              -> cfg de entrada intacto, `variante` y `record_frames`
    3. reproducibilidad           -> misma entrada, semillas distintas, suma de semillas
    4. conteo por método          -> n_f y n_grad de cada familia, sensibilidad k = 1
    5. frames                     -> solo en 2D y con grabar_frames=True
    6. validaciones               -> tipos y rangos de los argumentos
    7. efectos y serialización    -> no imprime, se guarda y se relee con JSON
    8. higiene                    -> azar global, líneas largas, celdas

Las corridas usan un presupuesto pequeño (`PRESUPUESTO` por dimensión) para que la suite tarde
pocos segundos. La configuración es la real: `configs/part1/base.yaml`.
"""

from __future__ import annotations

import copy
import math
import random
import re
from pathlib import Path

import numpy as np
import pytest

from src.common.config import load_config
from src.common.results import load_json, run_filename, save_json
from src.part1 import corrida, de, ea, gd, pso
from src.part1.corrida import (
    K_SENSIBILIDAD,
    METODOS,
    METODOS_GD,
    METODOS_SIN_GRADIENTE,
    PRESUPUESTO_POR_DIM_DEFECTO,
    ejecutar_corrida,
    obtener_optimizador,
)
from src.part1.functions import FUNCIONES

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_CORRIDA = RAIZ / "src" / "part1" / "corrida.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

PRESUPUESTO = 200                      # evaluaciones equivalentes por dimensión en las pruebas
CLAVES_CORRIDA = {"func", "dim", "method", "seed", "k", "budget", "config", "result"}
CLAVES_RESULTADO = {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history"}
NOMBRES_FUNCIONES = sorted(FUNCIONES)
DIMENSIONES = (2, 3)
TODAS_LAS_COMBINACIONES = [(func, dim, method) for func in NOMBRES_FUNCIONES
                           for dim in DIMENSIONES for method in METODOS]


@pytest.fixture(scope="module")
def cfg_base() -> dict:
    """Configuración real de la Parte 1; las pruebas no la modifican (se comprueba aparte)."""
    return load_config(RUTA_BASE)


def correr(cfg: dict, func: str = "rastrigin", dim: int = 2, method: str = "pso",
           base_seed: int = 0, run_id: int = 0, **opciones) -> dict:
    """`ejecutar_corrida` con el presupuesto pequeño de las pruebas salvo que se pida otro."""
    opciones.setdefault("presupuesto_por_dim", PRESUPUESTO)
    return ejecutar_corrida(func, dim, method, base_seed, run_id, cfg, **opciones)


# ================================================================================================
# 0. Constantes y despachador
# ================================================================================================

def test_constantes_del_spec():
    assert PRESUPUESTO_POR_DIM_DEFECTO == 10_000
    assert K_SENSIBILIDAD == 1
    assert METODOS == ("gdfijo", "gdarmijo", "ea", "pso", "de")
    assert METODOS_SIN_GRADIENTE == ("ea", "pso", "de")
    assert METODOS_GD == {"gdfijo": gd.VARIANTE_FIJO, "gdarmijo": gd.VARIANTE_ARMIJO}
    assert METODOS_GD == {"gdfijo": "fijo", "gdarmijo": "armijo"}


def test_los_metodos_son_los_gd_mas_los_sin_gradiente_y_coinciden_con_base_yaml(cfg_base):
    assert METODOS == tuple(METODOS_GD) + METODOS_SIN_GRADIENTE
    assert list(METODOS) == cfg_base["methods"]


@pytest.mark.parametrize("method, esperado", [
    ("gdfijo", gd.optimize), ("gdarmijo", gd.optimize),
    ("ea", ea.optimize), ("pso", pso.optimize), ("de", de.optimize),
])
def test_el_despachador_devuelve_el_optimize_de_cada_metodo(method, esperado):
    assert obtener_optimizador(method) is esperado


@pytest.mark.parametrize("method", ["gd", "PSO", "gd_fijo", "", None, 3])
def test_el_despachador_rechaza_un_metodo_desconocido_listando_los_validos(method):
    with pytest.raises(ValueError) as error:
        obtener_optimizador(method)
    for valido in METODOS:
        assert valido in str(error.value)


# ================================================================================================
# 1. Forma del diccionario (Spec §5.4)
# ================================================================================================

@pytest.mark.parametrize("func, dim, method", TODAS_LAS_COMBINACIONES)
def test_forma_del_diccionario_y_presupuesto_respetado(cfg_base, func, dim, method):
    salida = correr(cfg_base, func, dim, method, base_seed=3, run_id=4)
    assert set(salida) == CLAVES_CORRIDA
    assert (salida["func"], salida["dim"], salida["method"]) == (func, dim, method)
    assert salida["seed"] == 7
    assert salida["k"] == 2 * dim
    assert salida["budget"] == PRESUPUESTO * dim
    resultado = salida["result"]
    assert set(resultado) - {"frames"} == CLAVES_RESULTADO
    assert resultado["eval_equiv"] <= salida["budget"]
    assert resultado["eval_equiv"] == resultado["n_f"] + salida["k"] * resultado["n_grad"]
    assert len(resultado["x_best"]) == dim
    assert math.isfinite(resultado["f_best"])


def test_tipos_nativos_de_los_campos_de_identificacion(cfg_base):
    salida = correr(cfg_base, dim=np.int64(2), base_seed=np.int64(1), run_id=np.int64(2))
    assert type(salida["dim"]) is int and salida["dim"] == 2
    assert type(salida["seed"]) is int and salida["seed"] == 3
    assert type(salida["k"]) is float
    assert type(salida["budget"]) is float
    assert type(salida["func"]) is str and type(salida["method"]) is str


def test_presupuesto_por_defecto_es_10000_por_dimension(cfg_base, monkeypatch):
    """Sin correr 20 000 evaluaciones: se sustituye el optimizador por uno que no evalúa."""
    visto = {}

    def optimize_falso(problem, cfg, rng):
        visto["k"], visto["budget"] = problem.k, problem.budget
        return {"marcador": True}

    monkeypatch.setattr(corrida, "obtener_optimizador", lambda method: optimize_falso)
    salida = ejecutar_corrida("rastrigin", 3, "pso", 0, 0, cfg_base)
    assert salida["budget"] == 30_000 == visto["budget"]
    assert salida["k"] == 6 == visto["k"]
    assert salida["result"] == {"marcador": True}


def test_el_optimizador_recibe_el_problema_la_copia_de_cfg_y_el_rng_de_la_semilla(
        cfg_base, monkeypatch):
    visto = {}

    def optimize_falso(problem, cfg, rng):
        visto.update(problem=problem, cfg=cfg, sorteo=rng.random(4))
        return {}

    monkeypatch.setattr(corrida, "obtener_optimizador", lambda method: optimize_falso)
    salida = ejecutar_corrida("rosenbrock", 3, "de", 10, 5, cfg_base)
    assert visto["problem"].func.name == "rosenbrock" and visto["problem"].func.dim == 3
    assert visto["cfg"] is salida["config"]
    np.testing.assert_array_equal(visto["sorteo"], np.random.default_rng(15).random(4))


# ================================================================================================
# 2. Configuración
# ================================================================================================

@pytest.mark.parametrize("method", METODOS)
def test_el_cfg_de_entrada_no_cambia_y_config_es_otro_objeto(cfg_base, method):
    cfg = copy.deepcopy(cfg_base)
    antes = copy.deepcopy(cfg)
    salida = correr(cfg, method=method, grabar_frames=not cfg["record_frames"])
    assert cfg == antes
    assert salida["config"] is not cfg
    assert salida["config"]["gd"] is not cfg["gd"]
    assert salida["config"]["gd"]["eta"] is not cfg["gd"]["eta"]


@pytest.mark.parametrize("method, variante", [("gdfijo", "fijo"), ("gdarmijo", "armijo")])
def test_los_gd_fijan_su_variante_en_config(cfg_base, method, variante):
    assert correr(cfg_base, method=method)["config"]["variante"] == variante


def test_un_gd_sobrescribe_la_variante_que_traiga_el_cfg(cfg_base):
    cfg = copy.deepcopy(cfg_base)
    cfg["variante"] = "armijo"
    salida = correr(cfg, method="gdfijo")
    assert salida["config"]["variante"] == "fijo"
    assert salida["result"]["n_f"] == 0
    assert cfg["variante"] == "armijo"


@pytest.mark.parametrize("method", METODOS_SIN_GRADIENTE)
def test_los_metodos_sin_gradiente_no_reciben_variante(cfg_base, method):
    assert "variante" not in correr(cfg_base, method=method)["config"]


@pytest.mark.parametrize("method", METODOS)
@pytest.mark.parametrize("grabar", [True, False])
def test_record_frames_queda_fijado_con_grabar_frames(cfg_base, method, grabar):
    for valor_en_cfg in (True, False):
        cfg = copy.deepcopy(cfg_base)
        cfg["record_frames"] = valor_en_cfg
        assert correr(cfg, method=method, grabar_frames=grabar)["config"]["record_frames"] is grabar


def test_config_conserva_el_resto_de_la_configuracion(cfg_base):
    config = correr(cfg_base, method="ea")["config"]
    esperado = copy.deepcopy(cfg_base)
    esperado["record_frames"] = False
    assert config == esperado


def test_funciona_con_un_cfg_sin_record_frames(cfg_base):
    cfg = {clave: valor for clave, valor in cfg_base.items() if clave != "record_frames"}
    for method in METODOS:
        assert correr(cfg, method=method)["config"]["record_frames"] is False
    assert "record_frames" not in cfg


# ================================================================================================
# 3. Reproducibilidad (Spec §4.1)
# ================================================================================================

@pytest.mark.parametrize("func, dim, method", TODAS_LAS_COMBINACIONES)
def test_misma_entrada_mismo_resultado_bit_a_bit(cfg_base, func, dim, method):
    primera = correr(cfg_base, func, dim, method, base_seed=2, run_id=1, grabar_frames=True)
    segunda = correr(cfg_base, func, dim, method, base_seed=2, run_id=1, grabar_frames=True)
    assert primera == segunda
    assert repr(primera["result"]) == repr(segunda["result"])


@pytest.mark.parametrize("method", METODOS)
def test_semillas_distintas_dan_resultados_distintos(cfg_base, method):
    assert correr(cfg_base, method=method, run_id=0)["result"] != \
        correr(cfg_base, method=method, run_id=1)["result"]


@pytest.mark.parametrize("method", METODOS)
def test_solo_importa_la_suma_base_seed_mas_run_id(cfg_base, method):
    una = correr(cfg_base, method=method, base_seed=0, run_id=5)
    otra = correr(cfg_base, method=method, base_seed=5, run_id=0)
    assert una["seed"] == otra["seed"] == 5
    assert una["result"] == otra["result"]


# ================================================================================================
# 4. Conteo por método (Spec §6.2 y §6.3)
# ================================================================================================

@pytest.mark.parametrize("func", NOMBRES_FUNCIONES)
@pytest.mark.parametrize("dim", DIMENSIONES)
def test_gd_de_paso_fijo_solo_paga_gradientes(cfg_base, func, dim):
    resultado = correr(cfg_base, func, dim, "gdfijo")["result"]
    assert resultado["n_f"] == 0
    assert resultado["n_grad"] > 0


@pytest.mark.parametrize("func", NOMBRES_FUNCIONES)
@pytest.mark.parametrize("dim", DIMENSIONES)
def test_gd_armijo_paga_f_y_gradientes(cfg_base, func, dim):
    resultado = correr(cfg_base, func, dim, "gdarmijo")["result"]
    assert resultado["n_f"] > 0
    assert resultado["n_grad"] > 0


@pytest.mark.parametrize("func", NOMBRES_FUNCIONES)
@pytest.mark.parametrize("dim", DIMENSIONES)
@pytest.mark.parametrize("method", METODOS_SIN_GRADIENTE)
def test_las_metaheuristicas_no_piden_gradientes(cfg_base, func, dim, method):
    resultado = correr(cfg_base, func, dim, method)["result"]
    assert resultado["n_grad"] == 0
    assert resultado["n_f"] > 0


@pytest.mark.parametrize("method", METODOS)
def test_k_explicito_de_sensibilidad_queda_en_el_campo_k(cfg_base, method):
    salida = correr(cfg_base, method=method, k=K_SENSIBILIDAD)
    assert salida["k"] == 1
    assert salida["budget"] == PRESUPUESTO * 2
    resultado = salida["result"]
    assert resultado["eval_equiv"] == resultado["n_f"] + resultado["n_grad"]
    assert resultado["eval_equiv"] <= salida["budget"]


@pytest.mark.parametrize("dim", DIMENSIONES)
def test_con_k_1_el_gd_fijo_da_mas_gradientes_que_con_k_2n(cfg_base, dim):
    """En Rosenbrock, con este presupuesto y la semilla 0, el GD de paso fijo para por
    presupuesto con ambos k (en Rastrigin para antes, por la tolerancia del gradiente)."""
    principal = correr(cfg_base, "rosenbrock", dim, "gdfijo")["result"]
    sensibilidad = correr(cfg_base, "rosenbrock", dim, "gdfijo", k=1)["result"]
    assert principal["n_grad"] == PRESUPUESTO * dim // (2 * dim)
    assert sensibilidad["n_grad"] == PRESUPUESTO * dim
    assert sensibilidad["n_grad"] > principal["n_grad"]


def test_k_none_equivale_a_k_2n_explicito(cfg_base):
    assert correr(cfg_base, dim=3, method="gdarmijo") == \
        correr(cfg_base, dim=3, method="gdarmijo", k=6)


def test_k_no_cambia_a_un_metodo_sin_gradiente(cfg_base):
    assert correr(cfg_base, method="de")["result"] == correr(cfg_base, method="de", k=1)["result"]


def test_un_presupuesto_mayor_permite_mas_evaluaciones(cfg_base):
    corto = correr(cfg_base, method="pso", presupuesto_por_dim=100)
    largo = correr(cfg_base, method="pso", presupuesto_por_dim=300)
    assert (corto["budget"], largo["budget"]) == (200, 600)
    assert corto["result"]["n_f"] < largo["result"]["n_f"] <= 600


# ================================================================================================
# 5. Frames (Spec §5.1)
# ================================================================================================

@pytest.mark.parametrize("func", NOMBRES_FUNCIONES)
@pytest.mark.parametrize("method", METODOS)
def test_frames_en_2d_con_grabar_frames(cfg_base, func, method):
    resultado = correr(cfg_base, func, 2, method, grabar_frames=True)["result"]
    frames = resultado["frames"]
    assert len(frames) >= 1
    assert set(frames[0]) == {"iter", "positions", "best"}
    assert frames[0]["iter"] == 0
    assert all(len(posicion) == 2 for posicion in frames[0]["positions"])


@pytest.mark.parametrize("method", METODOS)
@pytest.mark.parametrize("dim, grabar", [(3, True), (3, False), (2, False)])
def test_sin_frames_en_3d_o_con_grabar_frames_false(cfg_base, method, dim, grabar):
    assert "frames" not in correr(cfg_base, dim=dim, method=method, grabar_frames=grabar)["result"]


def test_por_defecto_no_se_graban_frames_aunque_el_cfg_los_pida(cfg_base):
    assert cfg_base["record_frames"] is True
    salida = ejecutar_corrida("rastrigin", 2, "pso", 0, 0, cfg_base,
                              presupuesto_por_dim=PRESUPUESTO)
    assert "frames" not in salida["result"]
    assert salida["config"]["record_frames"] is False


@pytest.mark.parametrize("method", METODOS)
def test_grabar_frames_no_cambia_el_resto_del_resultado(cfg_base, method):
    con = correr(cfg_base, method=method, grabar_frames=True)["result"]
    sin = correr(cfg_base, method=method, grabar_frames=False)["result"]
    con.pop("frames")
    assert con == sin


# ================================================================================================
# 6. Validaciones
# ================================================================================================

@pytest.mark.parametrize("argumento", ["dim", "run_id", "base_seed"])
@pytest.mark.parametrize("valor", [True, False, 2.0, "2", None, np.float64(2.0), np.True_])
def test_dim_run_id_y_base_seed_deben_ser_enteros(cfg_base, argumento, valor):
    with pytest.raises(TypeError, match=argumento):
        correr(cfg_base, **{argumento: valor})


@pytest.mark.parametrize("argumento", ["run_id", "base_seed"])
def test_run_id_y_base_seed_no_pueden_ser_negativos(cfg_base, argumento):
    with pytest.raises(ValueError, match=argumento):
        correr(cfg_base, **{argumento: -1})


@pytest.mark.parametrize("dim", [0, -2])
def test_dim_debe_ser_al_menos_1(cfg_base, dim):
    with pytest.raises(ValueError, match="dim"):
        correr(cfg_base, dim=dim)


def test_dim_menor_que_el_minimo_de_la_funcion_lo_rechaza_la_funcion(cfg_base):
    with pytest.raises(ValueError, match="rosenbrock"):
        correr(cfg_base, func="rosenbrock", dim=1)


@pytest.mark.parametrize("argumento", ["k", "presupuesto_por_dim"])
@pytest.mark.parametrize("valor", [0, 0.0, -1, -0.5, math.inf, -math.inf, math.nan])
def test_k_y_presupuesto_deben_ser_finitos_y_positivos(cfg_base, argumento, valor):
    with pytest.raises(ValueError, match=argumento):
        correr(cfg_base, **{argumento: valor})


@pytest.mark.parametrize("argumento", ["k", "presupuesto_por_dim"])
@pytest.mark.parametrize("valor", [True, False, "4", [4]])
def test_k_y_presupuesto_no_admiten_bool_ni_texto(cfg_base, argumento, valor):
    with pytest.raises(TypeError, match=argumento):
        correr(cfg_base, **{argumento: valor})


def test_presupuesto_none_no_es_valido(cfg_base):
    with pytest.raises(TypeError, match="presupuesto_por_dim"):
        correr(cfg_base, presupuesto_por_dim=None)


@pytest.mark.parametrize("method", ["gd", "PSO", "gd_fijo", "", None])
def test_metodo_desconocido_lanza_valueerror_con_la_lista(cfg_base, method):
    with pytest.raises(ValueError) as error:
        correr(cfg_base, method=method)
    for valido in METODOS:
        assert valido in str(error.value)


@pytest.mark.parametrize("func", ["esfera", "Rastrigin", ""])
def test_funcion_desconocida_lanza_valueerror(cfg_base, func):
    with pytest.raises(ValueError, match="rastrigin"):
        correr(cfg_base, func=func)


@pytest.mark.parametrize("grabar", [1, 0, "true", None, 1.0])
def test_grabar_frames_debe_ser_bool(cfg_base, grabar):
    with pytest.raises(TypeError, match="grabar_frames"):
        correr(cfg_base, grabar_frames=grabar)


@pytest.mark.parametrize("cfg", [None, [("gd", {})], "configs/part1/base.yaml", 3])
def test_cfg_debe_ser_un_dict(cfg):
    with pytest.raises(TypeError, match="cfg"):
        correr(cfg)


def test_las_validaciones_ocurren_antes_de_correr(cfg_base, monkeypatch):
    """Con cualquier argumento inválido el optimizador no llega a ejecutarse."""
    llamadas = []

    def optimize_espia(problem, cfg, rng):
        llamadas.append(1)
        return {}

    for nombre in ("gd", "ea", "pso", "de"):
        monkeypatch.setattr(getattr(corrida, nombre), "optimize", optimize_espia)
    invalidos = [{"dim": 2.0}, {"run_id": True}, {"base_seed": -1}, {"k": 0},
                 {"presupuesto_por_dim": math.nan}, {"method": "x"}, {"func": "x"},
                 {"grabar_frames": 1}]
    for cambio in invalidos:
        with pytest.raises((TypeError, ValueError)):
            correr(cfg_base, **cambio)
    assert llamadas == []
    correr(cfg_base)
    assert llamadas == [1]


# ================================================================================================
# 7. Efectos y serialización (Spec §5.4)
# ================================================================================================

@pytest.mark.parametrize("method", METODOS)
def test_no_imprime_nada(cfg_base, capsys, method):
    correr(cfg_base, method=method, grabar_frames=True)
    capturado = capsys.readouterr()
    assert capturado.out == ""
    assert capturado.err == ""


def test_no_escribe_archivos(cfg_base, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for method in METODOS:
        correr(cfg_base, method=method, grabar_frames=True)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("func, dim, method", TODAS_LAS_COMBINACIONES)
def test_se_guarda_y_se_relee_con_json(cfg_base, tmp_path, func, dim, method):
    salida = correr(cfg_base, func, dim, method, base_seed=1, run_id=2, grabar_frames=True)
    nombre = run_filename(salida["func"], salida["dim"], salida["method"], salida["seed"])
    assert nombre == f"{func}_{dim}d_{method}_seed3.json"
    ruta = save_json(tmp_path / nombre, salida)
    assert load_json(ruta) == salida


def test_k_fraccionario_tambien_se_guarda(cfg_base, tmp_path):
    salida = correr(cfg_base, method="gdfijo", k=2.5)
    assert salida["k"] == 2.5
    assert load_json(save_json(tmp_path / "corrida.json", salida))["k"] == 2.5


# ================================================================================================
# 8. Higiene
# ================================================================================================

def test_no_usa_azar_global_ni_modifica_su_estado(cfg_base):
    estado_numpy = np.random.get_state()
    estado_random = random.getstate()
    for method in METODOS:
        correr(cfg_base, method=method)
    assert np.random.get_state()[1].tolist() == estado_numpy[1].tolist()
    assert np.random.get_state()[2:] == estado_numpy[2:]
    assert random.getstate() == estado_random


def test_el_codigo_no_importa_random_ni_siembra_global_ni_imprime():
    texto = RUTA_CORRIDA.read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*(import random|from random)", texto)
    assert "np.random.seed" not in texto
    assert not re.search(r"(?m)^\s*print\(", texto)
    assert "open(" not in texto


@pytest.mark.parametrize("ruta", [RUTA_CORRIDA, RUTA_PRUEBAS],
                         ids=["corrida.py", "test_corrida.py"])
def test_lineas_de_hasta_100_caracteres_en_lf(ruta):
    crudo = ruta.read_bytes()
    assert b"\r" not in crudo
    lineas = crudo.decode("utf-8").splitlines()
    largas = [i + 1 for i, linea in enumerate(lineas) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    celda_actual = None
    for numero, linea in enumerate(RUTA_CORRIDA.read_text(encoding="utf-8").splitlines(), start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_markdown_con_los_nombres_publicos():
    texto = RUTA_CORRIDA.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in ("obtener_optimizador", "ejecutar_corrida"):
        assert f"`{nombre}`" in cabecera
