"""Pruebas de las utilidades comunes a EA, PSO y DE (T1.6b; Spec §5.1, §6.2 y §6.4).

Un grupo de pruebas por utilidad de `src/part1/_comun.py`:

    1. validar_real                  -> tipo, bool, NaN/inf, mínimo (in/excluido) y máximo
    2. leer_bloque y validar_claves_exactas
    3. validar_limites, validar_poblacion y exigir_forma
    4. generar_poblacion_inicial     (pruebas movidas desde test_ea.py)
    5. evaluar_poblacion             (pruebas movidas desde test_ea.py)
    6. leer_record_frames y construir_frame
    7. construir_resultado           -> retorno del contrato §5.1, con y sin frames
    8. higiene                       -> azar global, líneas largas, celdas, cabecera, imports

Las utilidades se prueban SIN los algoritmos: solo arreglos, `limites`, `rng` y un callable.
Todo el azar de las pruebas sale de `np.random.default_rng(<entero fijo>)`.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest

from src.common.counter import CountedProblem
from src.part1._comun import (
    DIMENSION_CON_FRAMES,
    construir_frame,
    construir_resultado,
    evaluar_poblacion,
    exigir_forma,
    generar_poblacion_inicial,
    leer_bloque,
    leer_record_frames,
    validar_claves_exactas,
    validar_limites,
    validar_poblacion,
    validar_real,
)
from src.part1.functions import get_function

RAIZ = Path(__file__).resolve().parents[1]
RUTA_COMUN = RAIZ / "src" / "part1" / "_comun.py"
RUTA_PRUEBAS = Path(__file__).resolve()
RUTAS_METODOS = {nombre: RAIZ / "src" / "part1" / f"{nombre}.py" for nombre in ("ea", "pso", "de")}
LARGO_MAXIMO = 100
LIMITE_SIN_RECORTE = 100.0
CLAVES_RETORNO = {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history"}
UTILIDADES = (
    "validar_real", "leer_bloque", "validar_claves_exactas", "validar_limites",
    "validar_poblacion", "exigir_forma", "generar_poblacion_inicial", "evaluar_poblacion",
    "leer_record_frames", "construir_frame", "construir_resultado",
)


def limites_cuadrados(dim: int, limite: float = LIMITE_SIN_RECORTE) -> np.ndarray:
    """Dominio [-limite, limite]^dim como arreglo (dim, 2)."""
    return np.tile(np.array([-limite, limite]), (dim, 1))


def poblacion_aleatoria(tamano: int, dim: int, semilla: int = 7, amplitud: float = 2.0):
    """Población de prueba (tamano, dim) con valores en [-amplitud, amplitud]."""
    rng = np.random.default_rng(semilla)
    return rng.uniform(-amplitud, amplitud, size=(tamano, dim))


def problema_evaluado(dim: int, puntos: int = 4) -> CountedProblem:
    """CountedProblem de Rastrigin (k = 2n) con `puntos` evaluaciones de f ya hechas."""
    func = get_function("rastrigin", dim)
    problema = CountedProblem(func, k=2 * dim, budget=1000.0)
    for x in poblacion_aleatoria(puntos, dim, semilla=11):
        problema.f(x)
    return problema


# ================================================================================================
# 1. validar_real
# ================================================================================================

@pytest.mark.parametrize("valor", [0, 0.0, 1, 0.5, np.int64(3), np.float64(0.25), np.float32(2)])
def test_real_valido_devuelve_float_nativo(valor):
    numero = validar_real(valor, "x", minimo=0, minimo_incluido=True)
    assert type(numero) is float
    assert numero == float(valor)


@pytest.mark.parametrize("valor", [True, False, np.True_, "0.5", None, [0.5], {}, 1 + 2j])
def test_real_con_tipo_incorrecto_lanza_typeerror_que_nombra_valor_y_tipo(valor):
    with pytest.raises(TypeError) as info:
        validar_real(valor, "pso.w", minimo=0, minimo_incluido=True)
    assert str(info.value) == (f"pso.w debe ser un número real; se recibió {valor!r} "
                               f"({type(valor).__name__})")


@pytest.mark.parametrize("valor", [math.nan, math.inf, -math.inf, np.float64("nan")])
@pytest.mark.parametrize("minimo_incluido", [True, False])
def test_real_nan_o_infinito_lanza_valueerror(valor, minimo_incluido):
    with pytest.raises(ValueError):
        validar_real(valor, "x", minimo=0, minimo_incluido=minimo_incluido)


def test_real_minimo_incluido_acepta_el_minimo_y_rechaza_lo_menor():
    assert validar_real(0, "x", minimo=0, minimo_incluido=True) == 0.0
    assert validar_real(2.5, "x", minimo=2.5, minimo_incluido=True) == 2.5
    with pytest.raises(ValueError):
        validar_real(-1e-9, "x", minimo=0, minimo_incluido=True)


def test_real_minimo_excluido_rechaza_el_minimo_y_acepta_lo_mayor():
    with pytest.raises(ValueError):
        validar_real(0.0, "x", minimo=0, minimo_incluido=False)
    assert validar_real(5e-324, "x", minimo=0, minimo_incluido=False) == 5e-324


def test_real_maximo_es_inclusivo_y_sin_maximo_no_hay_tope():
    assert validar_real(1, "x", minimo=0.0, minimo_incluido=True, maximo=1.0) == 1.0
    with pytest.raises(ValueError):
        validar_real(1.0000001, "x", minimo=0.0, minimo_incluido=True, maximo=1.0)
    assert validar_real(1e308, "x", minimo=0, minimo_incluido=True) == 1e308


# Los tres módulos conservan su texto de error de antes del refactor: EA y PSO pasan el mínimo
# como entero (se lee "0") y DE como real (se lee "0.0").
CASOS_MENSAJE_DE_RANGO = [
    pytest.param(-0.1, "ea.frac_e", 0, True, None,
                 "ea.frac_e debe ser finito y >= 0; se recibió -0.1", id="ea_fraccion"),
    pytest.param(math.nan, "pso.w", 0, True, None,
                 "pso.w debe ser finito y >= 0; se recibió nan", id="pso_coeficiente_nan"),
    pytest.param(0.0, "pso.vmax_frac", 0, False, None,
                 "pso.vmax_frac debe ser finito y > 0; se recibió 0.0", id="pso_vmax_frac"),
    pytest.param(math.inf, "de.F", 0.0, False, None,
                 "de.F debe ser finito y > 0.0; se recibió inf", id="de_f_inf"),
    pytest.param(2, "de.CR", 0.0, True, 1.0,
                 "de.CR debe ser finito y >= 0.0 y <= 1.0; se recibió 2", id="de_cr_alto"),
    pytest.param(-1, "de.CR", 0.0, True, 1.0,
                 "de.CR debe ser finito y >= 0.0 y <= 1.0; se recibió -1", id="de_cr_bajo"),
]


@pytest.mark.parametrize("valor,nombre,minimo,incluido,maximo,mensaje", CASOS_MENSAJE_DE_RANGO)
def test_real_fuera_de_rango_mensaje_exacto(valor, nombre, minimo, incluido, maximo, mensaje):
    with pytest.raises(ValueError) as info:
        validar_real(valor, nombre, minimo=minimo, minimo_incluido=incluido, maximo=maximo)
    assert str(info.value) == mensaje


# ================================================================================================
# 2. leer_bloque y validar_claves_exactas
# ================================================================================================

def test_leer_bloque_devuelve_el_mismo_objeto_sin_copiarlo():
    bloque = {"N": 30}
    assert leer_bloque({"pso": bloque, "record_frames": True}, "pso") is bloque


@pytest.mark.parametrize("nombre", ["ea", "pso", "de"])
def test_leer_bloque_faltante_lanza_valueerror_con_mensaje_exacto(nombre):
    with pytest.raises(ValueError) as info:
        leer_bloque({"record_frames": True}, nombre)
    assert str(info.value) == (f"falta el bloque '{nombre}' en la configuración (definido en "
                               "configs/part1/base.yaml)")


def test_leer_bloque_no_valida_el_contenido_del_bloque():
    assert leer_bloque({"de": [1, 2]}, "de") == [1, 2]


def test_claves_exactas_correctas_no_lanzan_y_no_importa_el_orden():
    assert validar_claves_exactas({"b": 1, "a": 2}, ("a", "b"), "de") is None


@pytest.mark.parametrize("bloque", [None, [1, 2], "texto", 3, (1, 2)])
def test_claves_exactas_bloque_que_no_es_mapeo_lanza_typeerror(bloque):
    with pytest.raises(TypeError) as info:
        validar_claves_exactas(bloque, ("a", "b"), "pso")
    assert str(info.value) == (f"el bloque 'pso' debe ser un mapeo; se recibió "
                               f"{type(bloque).__name__}")


def test_claves_exactas_faltantes_se_nombran_en_el_orden_de_claves():
    with pytest.raises(ValueError) as info:
        validar_claves_exactas({"b": 1}, ("a", "b", "c"), "ea")
    assert str(info.value) == "faltan claves en el bloque 'ea': a, c"


def test_claves_exactas_sobrantes_se_nombran_junto_con_las_validas():
    with pytest.raises(ValueError) as info:
        validar_claves_exactas({"a": 1, "zz": 2, "b": 3, 7: 4}, ("a", "b"), "de")
    assert str(info.value) == "claves desconocidas en el bloque 'de': zz, 7; válidas: a, b"


def test_claves_exactas_si_faltan_y_sobran_se_reportan_primero_las_faltantes():
    with pytest.raises(ValueError, match="faltan claves en el bloque 'de': a, b"):
        validar_claves_exactas({"zz": 1}, ("a", "b"), "de")


# ================================================================================================
# 3. validar_limites, validar_poblacion y exigir_forma
# ================================================================================================

def test_limites_validos_se_devuelven_como_float_d_por_2():
    limites = validar_limites([[-1, 3], [0, 10], [2, 2]])
    assert limites.shape == (3, 2)
    assert limites.dtype == np.float64
    assert limites.tolist() == [[-1.0, 3.0], [0.0, 10.0], [2.0, 2.0]]


LIMITES_INVALIDOS = [
    pytest.param(np.array([-1.0, 1.0]), r"forma \(d, 2\)", id="forma_1d"),
    pytest.param(np.array([[-1.0, 0.0, 1.0]]), r"forma \(d, 2\)", id="forma_d_por_3"),
    pytest.param(np.empty((0, 2)), r"forma \(d, 2\)", id="sin_dimensiones"),
    pytest.param(np.array([[-1.0, np.nan]]), "finito", id="con_nan"),
    pytest.param(np.array([[-np.inf, 1.0]]), "finito", id="con_inf"),
    pytest.param(np.array([[2.0, -2.0]]), "inferior", id="inferior_mayor_que_superior"),
]


@pytest.mark.parametrize("limites,patron", LIMITES_INVALIDOS)
def test_limites_invalidos_lanzan_valueerror(limites, patron):
    with pytest.raises(ValueError, match=patron):
        validar_limites(limites)


def test_poblacion_valida_se_devuelve_como_float_y_admite_cero_filas():
    poblacion = validar_poblacion([[1, 2, 3], [4, 5, 6]])
    assert poblacion.shape == (2, 3) and poblacion.dtype == np.float64
    assert validar_poblacion(np.empty((0, 2))).shape == (0, 2)


@pytest.mark.parametrize("poblacion", [np.array([1.0, 2.0]), np.zeros((2, 2, 2)), np.empty((3, 0))])
def test_poblacion_con_forma_invalida_lanza_valueerror_con_el_nombre_pedido(poblacion):
    with pytest.raises(ValueError) as info:
        validar_poblacion(poblacion)
    assert str(info.value) == f"poblacion debe tener forma (N, d); se recibió {poblacion.shape}"
    with pytest.raises(ValueError, match="^velocidades debe tener forma"):
        validar_poblacion(poblacion, "velocidades")


def test_exigir_forma_no_copia_un_arreglo_float64_y_convierte_los_demas():
    arreglo = np.zeros((3, 2))
    assert exigir_forma(arreglo, (3, 2), "x") is arreglo
    convertido = exigir_forma([1, 2, 3], (3,), "x")
    assert convertido.dtype == np.float64 and convertido.tolist() == [1.0, 2.0, 3.0]


@pytest.mark.parametrize("arreglo,forma", [
    (np.zeros((3, 2)), (2, 3)), (np.zeros(3), (3, 1)), (np.zeros((3, 2)), (3,)), (5.0, (1,)),
])
def test_exigir_forma_con_otra_forma_lanza_valueerror_con_mensaje_exacto(arreglo, forma):
    with pytest.raises(ValueError) as info:
        exigir_forma(arreglo, forma, "aptitudes")
    assert str(info.value) == (f"aptitudes debe tener forma {forma}; se recibió "
                               f"{np.shape(arreglo)}")


# ================================================================================================
# 4. generar_poblacion_inicial (movidas desde test_ea.py)
# ================================================================================================

@pytest.mark.parametrize("tamano,dim", [(50, 2), (50, 3), (7, 5)])
def test_poblacion_inicial_forma_dtype_y_rango(tamano, dim):
    limites = limites_cuadrados(dim, 2.048)
    poblacion = generar_poblacion_inicial(tamano, limites, np.random.default_rng(1))
    assert poblacion.shape == (tamano, dim)
    assert poblacion.dtype == np.float64
    assert np.all(poblacion >= limites[:, 0]) and np.all(poblacion <= limites[:, 1])


def test_poblacion_inicial_respeta_limites_distintos_por_dimension():
    limites = np.array([[-1.0, 3.0], [0.0, 10.0], [-5.0, -2.0]])
    poblacion = generar_poblacion_inicial(2000, limites, np.random.default_rng(2))
    assert np.all(poblacion >= limites[:, 0]) and np.all(poblacion <= limites[:, 1])
    # y cada columna llena su propio rango (no un rango común)
    assert poblacion[:, 0].max() > 2.5 and poblacion[:, 0].min() < -0.5
    assert poblacion[:, 1].max() > 9.0 and poblacion[:, 1].min() < 1.0
    assert poblacion[:, 2].max() < -2.0 + 1e-12 and poblacion[:, 2].min() < -4.5


def test_poblacion_inicial_misma_semilla_misma_poblacion_y_semillas_distintas_no():
    limites = limites_cuadrados(2, 5.12)
    a = generar_poblacion_inicial(50, limites, np.random.default_rng(3))
    b = generar_poblacion_inicial(50, limites, np.random.default_rng(3))
    c = generar_poblacion_inicial(50, limites, np.random.default_rng(4))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


@pytest.mark.parametrize("limites", [caso.values[0] for caso in LIMITES_INVALIDOS],
                         ids=[caso.id for caso in LIMITES_INVALIDOS])
def test_poblacion_inicial_rechaza_limites_invalidos(limites):
    with pytest.raises(ValueError):
        generar_poblacion_inicial(5, limites, np.random.default_rng(0))


def test_poblacion_inicial_rechaza_tamano_invalido():
    limites = limites_cuadrados(2)
    with pytest.raises(ValueError):
        generar_poblacion_inicial(0, limites, np.random.default_rng(0))
    with pytest.raises(TypeError):
        generar_poblacion_inicial(5.0, limites, np.random.default_rng(0))


def test_poblacion_inicial_consume_una_sola_llamada_uniform():
    """Orden de consumo del rng documentado: rng.uniform(lim_inf, lim_sup, size=(N, d))."""
    limites = np.array([[-1.0, 3.0], [0.0, 10.0]])
    poblacion = generar_poblacion_inicial(10, limites, np.random.default_rng(8))
    esperado = np.random.default_rng(8).uniform(limites[:, 0], limites[:, 1], size=(10, 2))
    assert np.array_equal(poblacion, esperado)


# ================================================================================================
# 5. evaluar_poblacion (movidas desde test_ea.py)
# ================================================================================================

def test_evaluar_llama_una_vez_por_fila_en_orden_y_con_filas_1d():
    poblacion = poblacion_aleatoria(6, 3)
    recibidos = []

    def evaluar(x):
        recibidos.append(np.array(x, copy=True))
        return float(np.sum(x ** 2))

    aptitudes = evaluar_poblacion(poblacion, evaluar)
    assert len(recibidos) == 6
    for i, x in enumerate(recibidos):
        assert x.shape == (3,)
        assert np.array_equal(x, poblacion[i])
    assert aptitudes.dtype == np.float64
    assert aptitudes.shape == (6,)
    assert np.allclose(aptitudes, np.sum(poblacion ** 2, axis=1))


def test_evaluar_no_modifica_la_poblacion():
    poblacion = poblacion_aleatoria(5, 2)
    copia = poblacion.copy()
    evaluar_poblacion(poblacion, lambda x: float(np.sum(x)))
    assert np.array_equal(poblacion, copia)


def test_evaluar_rechaza_poblacion_que_no_es_2d():
    with pytest.raises(ValueError):
        evaluar_poblacion(np.array([1.0, 2.0, 3.0]), lambda x: 0.0)


def test_evaluar_propaga_la_excepcion_del_callable():
    class Corte(Exception):
        pass

    def evaluar(x):
        raise Corte

    with pytest.raises(Corte):
        evaluar_poblacion(poblacion_aleatoria(3, 2), evaluar)


# ================================================================================================
# 6. leer_record_frames y construir_frame
# ================================================================================================

def test_la_dimension_con_frames_es_2():
    assert DIMENSION_CON_FRAMES == 2


@pytest.mark.parametrize("valor", [True, False, np.True_, np.False_])
def test_record_frames_bool_se_devuelve_como_bool_nativo(valor):
    leido = leer_record_frames({"record_frames": valor})
    assert type(leido) is bool and leido == bool(valor)


def test_record_frames_faltante_lanza_valueerror_con_mensaje_exacto():
    with pytest.raises(ValueError) as info:
        leer_record_frames({"pso": {}})
    assert str(info.value) == "falta la clave 'record_frames' en la configuración"


@pytest.mark.parametrize("valor", ["si", 1, 0, None, [True]])
def test_record_frames_que_no_es_bool_lanza_typeerror_con_mensaje_exacto(valor):
    with pytest.raises(TypeError) as info:
        leer_record_frames({"record_frames": valor})
    assert str(info.value) == (f"record_frames debe ser bool; se recibió {valor!r} "
                               f"({type(valor).__name__})")


def test_frame_tiene_las_tres_claves_del_contrato_con_listas_nativas():
    poblacion = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    frame = construir_frame(4, poblacion, np.array([3.0, 4.0]))
    assert frame == {"iter": 4, "positions": [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]],
                     "best": [3.0, 4.0]}
    assert type(frame["positions"]) is list and type(frame["positions"][0]) is list
    assert type(frame["best"]) is list and type(frame["best"][0]) is float


def test_frame_no_comparte_memoria_con_la_poblacion():
    poblacion = np.array([[1.0, 2.0], [3.0, 4.0]])
    frame = construir_frame(0, poblacion, poblacion[0])
    poblacion[0, 0] = 99.0
    assert frame["positions"][0] == [1.0, 2.0]
    assert frame["best"] == [1.0, 2.0]


# ================================================================================================
# 7. construir_resultado (retorno del contrato §5.1)
# ================================================================================================

@pytest.mark.parametrize("dim", [2, 3])
def test_resultado_sin_frames_tiene_exactamente_las_claves_del_contrato(dim):
    problema = problema_evaluado(dim)
    resultado = construir_resultado(problema, [], guardar_frames=False)
    assert set(resultado) == CLAVES_RETORNO
    assert resultado["x_best"] == problema.best_x.tolist()
    assert resultado["f_best"] == problema.best_f
    assert resultado["n_f"] == 4
    assert resultado["n_grad"] == 0
    assert resultado["eval_equiv"] == 4.0
    assert resultado["history"] == problema.history


def test_resultado_usa_tipos_nativos_de_python():
    resultado = construir_resultado(problema_evaluado(2), [], guardar_frames=False)
    assert type(resultado["x_best"]) is list
    assert all(type(valor) is float for valor in resultado["x_best"])
    assert type(resultado["f_best"]) is float
    assert type(resultado["n_f"]) is int
    assert type(resultado["n_grad"]) is int
    assert type(resultado["eval_equiv"]) is float
    assert type(resultado["history"]) is list


def test_resultado_con_frames_agrega_la_clave_frames_con_la_lista_recibida():
    frames = [construir_frame(0, np.zeros((2, 2)), np.zeros(2))]
    resultado = construir_resultado(problema_evaluado(2), frames, guardar_frames=True)
    assert set(resultado) == CLAVES_RETORNO | {"frames"}
    assert resultado["frames"] == frames


def test_resultado_sin_guardar_frames_omite_la_clave_aunque_la_lista_no_este_vacia():
    frames = [construir_frame(0, np.zeros((2, 2)), np.zeros(2))]
    resultado = construir_resultado(problema_evaluado(2), frames, guardar_frames=False)
    assert "frames" not in resultado


def test_resultado_con_guardar_frames_y_lista_vacia_devuelve_frames_vacio():
    resultado = construir_resultado(problema_evaluado(2), [], guardar_frames=True)
    assert resultado["frames"] == []


def test_resultado_copia_el_historial_del_problema():
    problema = problema_evaluado(2)
    resultado = construir_resultado(problema, [], guardar_frames=False)
    assert resultado["history"] is not problema.history
    assert len(resultado["history"]) >= 1
    for copia, original in zip(resultado["history"], problema.history):
        assert copia == original and copia is not original


def test_resultado_cuenta_el_gradiente_en_eval_equiv():
    problema = problema_evaluado(3, puntos=2)
    problema.grad(np.zeros(3))
    resultado = construir_resultado(problema, [], guardar_frames=False)
    assert resultado["n_grad"] == 1
    assert resultado["eval_equiv"] == 2 + 2 * 3     # n_f + k * n_grad, con k = 2n


# ================================================================================================
# 8. Higiene
# ================================================================================================

def test_el_codigo_no_importa_random_ni_siembra_global():
    texto = RUTA_COMUN.read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*(import random|from random)", texto)
    assert "np.random.seed" not in texto


@pytest.mark.parametrize("ruta", [RUTA_COMUN, RUTA_PRUEBAS], ids=["_comun.py", "test_comun.py"])
def test_lineas_de_hasta_100_caracteres(ruta):
    texto = ruta.read_text(encoding="utf-8")
    largas = [i + 1 for i, linea in enumerate(texto.splitlines()) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    """Error B1 de T1.4: ningún def/class/import/from fuera de una celda `# %%` de código."""
    celda_actual = None
    for numero, linea in enumerate(RUTA_COMUN.read_text(encoding="utf-8").splitlines(), start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_con_tabla_de_utilidades():
    texto = RUTA_COMUN.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in UTILIDADES:
        assert f"`{nombre}`" in cabecera
        assert f"def {nombre}(" in texto


def test_comun_no_importa_ningun_modulo_de_algoritmo():
    texto = RUTA_COMUN.read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*(from|import) src\.part1", texto)


@pytest.mark.parametrize("nombre", ["pso", "de"])
def test_pso_y_de_no_importan_nada_de_ea(nombre):
    texto = RUTAS_METODOS[nombre].read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*(from src\.part1\.ea import|import src\.part1\.ea)", texto)
    assert not re.search(r"(?m)^\s*from src\.part1 import .*\bea\b", texto)


@pytest.mark.parametrize("nombre", ["ea", "pso", "de"])
def test_los_metodos_importan_de_comun_y_no_redefinen_sus_utilidades(nombre):
    texto = RUTAS_METODOS[nombre].read_text(encoding="utf-8")
    assert re.search(r"(?m)^from src\.part1\._comun import", texto)
    for utilidad in UTILIDADES:
        assert f"def {utilidad}(" not in texto
        assert f"def _{utilidad}(" not in texto
