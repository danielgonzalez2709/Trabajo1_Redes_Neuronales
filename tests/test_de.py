"""Pruebas de la evolución diferencial de la Parte 1 (T1.6; Spec §6.2 y §6.4): DE/rand/1/bin.

Un grupo de pruebas por componente de `src/part1/de.py`, de lo más pequeño a lo más grande:

    0. ParametrosDE                  -> validación del bloque `de:` y defaults de base.yaml
    1. sortear_padres                -> tres índices distintos entre sí y distintos de i
    2. mutar_diferencial             -> v = x_r1 + F (x_r2 - x_r3), oráculo con bucles
    3. reiniciar_fuera_de_dominio    -> reinicio uniforme solo de las componentes que salen
    4. cruzar_binomial               -> U <= CR o j == j_rand
    5. seleccionar_codiciosa         -> el hijo gana en empate
    6. optimize                      -> integración con CountedProblem, conteo y reproducibilidad
    7. higiene                       -> azar global, líneas largas, celdas, cabecera

Los componentes (1-5) se prueban SIN CountedProblem: solo arreglos, `limites` y `rng`.
Todo el azar de las pruebas sale de `np.random.default_rng(<entero fijo>)`.
"""

from __future__ import annotations

import dataclasses
import json
import random
import re
from pathlib import Path

import numpy as np
import pytest

from src.common.config import apply_overrides, load_config
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.part1.de import (
    ParametrosDE,
    ResultadoCruce,
    ResultadoReinicio,
    ResultadoSeleccion,
    cruzar_binomial,
    mutar_diferencial,
    optimize,
    reiniciar_fuera_de_dominio,
    seleccionar_codiciosa,
    sortear_padres,
)
from src.part1.functions import get_function

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_DE = RAIZ / "src" / "part1" / "de.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

# Valores por defecto del Spec §6.4 (se repiten a propósito: la prueba de base.yaml los compara).
CFG_DE_SPEC = {"NP": 30, "F": 0.7, "CR": 0.9, "generaciones": None}


def cfg_de(**cambios) -> dict:
    """Bloque `de:` con los valores del Spec y los cambios pedidos."""
    bloque = dict(CFG_DE_SPEC)
    bloque.update(cambios)
    return bloque


def cfg_completo(record_frames: bool = True, **cambios) -> dict:
    """Configuración mínima que recibe optimize: bloque `de` y `record_frames`."""
    return {"de": cfg_de(**cambios), "record_frames": record_frames}


def nuevo_problema(func, presupuesto: float) -> CountedProblem:
    """CountedProblem con k = 2n (Spec §6.2, principal)."""
    return CountedProblem(func, k=2 * func.dim, budget=presupuesto)


class FuncionRegistradora:
    """Envuelve una TestFunction y guarda una copia de CADA punto que recibe `f` y su valor."""

    def __init__(self, func):
        self.name = func.name
        self.dim = func.dim
        self.bounds = func.bounds
        self.x_star = func.x_star
        self.f_star = func.f_star
        self._func = func
        self.puntos_evaluados: list[np.ndarray] = []
        self.valores: list[float] = []

    def f(self, x):
        self.puntos_evaluados.append(np.array(x, dtype=float, copy=True))
        valor = self._func.f(x)
        self.valores.append(valor)
        return valor

    def grad(self, x):
        return self._func.grad(x)


class Esfera:
    """f(x) = sum(x^2) en [-5.12, 5.12]^dim, con la interfaz de TestFunction."""

    name = "esfera"

    def __init__(self, dim: int):
        self.dim = dim
        self.bounds = np.tile(np.array([-5.12, 5.12]), (dim, 1))
        self.x_star = np.zeros(dim)
        self.f_star = 0.0

    def f(self, x):
        return float(np.sum(np.asarray(x, dtype=float) ** 2))

    def grad(self, x):
        return 2.0 * np.asarray(x, dtype=float)


def _correr(func, presupuesto: float, semilla: int = 0, record_frames: bool = True, **cambios):
    """Corre optimize con k = 2n; devuelve (problema, resultado)."""
    problema = nuevo_problema(func, presupuesto)
    resultado = optimize(problema, cfg_completo(record_frames, **cambios), make_rng(semilla, 0))
    return problema, resultado


class RngContador:
    """Generador que delega en uno real y cuenta cuántas veces se le pide azar."""

    def __init__(self, semilla: int):
        self._rng = np.random.default_rng(semilla)
        self.llamadas = 0

    def __getattr__(self, nombre):
        atributo = getattr(self._rng, nombre)
        if not callable(atributo):
            return atributo

        def envuelto(*args, **kwargs):
            self.llamadas += 1
            return atributo(*args, **kwargs)

        return envuelto


# ================================================================================================
# 0. ParametrosDE
# ================================================================================================

def test_parametros_con_los_defaults_del_spec():
    p = ParametrosDE.desde_config(cfg_de())
    assert p.tamano_poblacion == 30
    assert p.factor_f == 0.7
    assert p.prob_cruce == 0.9
    assert p.generaciones is None


def test_base_yaml_coincide_con_el_spec():
    cfg = load_config(RUTA_BASE)
    assert cfg["de"] == CFG_DE_SPEC
    p = ParametrosDE.desde_config(cfg["de"])
    assert (p.tamano_poblacion, p.factor_f, p.prob_cruce, p.generaciones) == (30, 0.7, 0.9, None)


def test_parametros_tienen_tipos_nativos():
    p = ParametrosDE.desde_config(cfg_de(NP=np.int64(10), F=np.float64(0.5), CR=1, generaciones=3))
    assert type(p.tamano_poblacion) is int
    assert type(p.factor_f) is float
    assert type(p.prob_cruce) is float
    assert type(p.generaciones) is int


@pytest.mark.parametrize("clave", list(CFG_DE_SPEC))
def test_falta_una_clave(clave):
    bloque = cfg_de()
    del bloque[clave]
    with pytest.raises(ValueError, match=clave):
        ParametrosDE.desde_config(bloque)


def test_clave_desconocida_se_nombra():
    with pytest.raises(ValueError, match="strategy"):
        ParametrosDE.desde_config(cfg_de(strategy="best1"))


def test_esquema_que_no_es_mapeo():
    with pytest.raises(TypeError):
        ParametrosDE.desde_config([30, 0.7, 0.9, None])


@pytest.mark.parametrize("valor", [0.0, -0.5, float("nan"), float("inf"), -float("inf")])
def test_f_invalido_valueerror(valor):
    with pytest.raises(ValueError, match="de.F"):
        ParametrosDE.desde_config(cfg_de(F=valor))


@pytest.mark.parametrize("valor", [True, "0.7", None, [0.7]])
def test_f_tipo_invalido_typeerror(valor):
    with pytest.raises(TypeError, match="de.F"):
        ParametrosDE.desde_config(cfg_de(F=valor))


@pytest.mark.parametrize("valor", [-0.1, 1.0000001, 2.0, float("nan"), float("inf")])
def test_cr_fuera_de_rango_valueerror(valor):
    with pytest.raises(ValueError, match="de.CR"):
        ParametrosDE.desde_config(cfg_de(CR=valor))


@pytest.mark.parametrize("valor", [True, "0.9", None])
def test_cr_tipo_invalido_typeerror(valor):
    with pytest.raises(TypeError, match="de.CR"):
        ParametrosDE.desde_config(cfg_de(CR=valor))


@pytest.mark.parametrize("valor", [0, 0.0, 1, 1.0, 0.5])
def test_cr_en_los_extremos_es_valido(valor):
    assert ParametrosDE.desde_config(cfg_de(CR=valor)).prob_cruce == float(valor)


@pytest.mark.parametrize("valor", [3, 0, -1])
def test_np_menor_que_4(valor):
    with pytest.raises(ValueError, match="de.NP"):
        ParametrosDE.desde_config(cfg_de(NP=valor))


@pytest.mark.parametrize("valor", [True, 4.0, "30", None])
def test_np_tipo_invalido(valor):
    with pytest.raises(TypeError, match="de.NP"):
        ParametrosDE.desde_config(cfg_de(NP=valor))


def test_np_igual_a_4_es_valido():
    assert ParametrosDE.desde_config(cfg_de(NP=4)).tamano_poblacion == 4


@pytest.mark.parametrize("valor", [True, 3.0, "10"])
def test_generaciones_tipo_invalido(valor):
    with pytest.raises(TypeError, match="de.generaciones"):
        ParametrosDE.desde_config(cfg_de(generaciones=valor))


def test_generaciones_negativo_y_cero():
    with pytest.raises(ValueError, match="de.generaciones"):
        ParametrosDE.desde_config(cfg_de(generaciones=-1))
    assert ParametrosDE.desde_config(cfg_de(generaciones=0)).generaciones == 0


def test_parametros_son_una_dataclass_congelada():
    p = ParametrosDE.desde_config(cfg_de())
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.factor_f = 1.0


# ================================================================================================
# 1. sortear_padres
# ================================================================================================

@pytest.mark.parametrize("tamano", [4, 5, 30])
def test_padres_son_distintos_entre_si_y_de_i(tamano):
    for semilla in range(200):
        padres = sortear_padres(tamano, np.random.default_rng(semilla))
        assert padres.shape == (tamano, 3)
        assert np.issubdtype(padres.dtype, np.integer)
        assert padres.min() >= 0 and padres.max() < tamano
        i = np.arange(tamano)
        r1, r2, r3 = padres[:, 0], padres[:, 1], padres[:, 2]
        assert np.all(r1 != i) and np.all(r2 != i) and np.all(r3 != i)
        assert np.all(r1 != r2) and np.all(r1 != r3) and np.all(r2 != r3)


def test_padres_con_np_4_son_los_tres_otros():
    for semilla in range(50):
        padres = sortear_padres(4, np.random.default_rng(semilla))
        for i in range(4):
            assert sorted(padres[i].tolist()) == [j for j in range(4) if j != i]


def test_padres_todos_los_indices_aparecen_en_cada_columna():
    vistos = [set(), set(), set()]
    for semilla in range(100):
        padres = sortear_padres(10, np.random.default_rng(semilla))
        for columna in range(3):
            vistos[columna].update(padres[:, columna].tolist())
    for columna in range(3):
        assert vistos[columna] == set(range(10))


def test_padres_sin_sesgo_evidente_en_frecuencias():
    cuenta = np.zeros(10)
    for semilla in range(300):
        padres = sortear_padres(10, np.random.default_rng(semilla))
        cuenta += np.bincount(padres[:, 0], minlength=10)
    # r1 es uniforme sobre los otros 9 índices: cada índice se espera 300 * 10 / 10 = 300 veces.
    assert np.all(np.abs(cuenta - 300) < 80)


def test_padres_hace_una_sola_llamada_al_rng():
    rng = RngContador(3)
    sortear_padres(30, rng)
    assert rng.llamadas == 1


def test_padres_consumen_un_random_np_np():
    rng = np.random.default_rng(9)
    sortear_padres(7, rng)
    esperado = np.random.default_rng(9)
    esperado.random((7, 7))
    assert rng.bit_generator.state == esperado.bit_generator.state


@pytest.mark.parametrize("tamano", [3, 2, 1, 0])
def test_padres_con_menos_de_4_individuos(tamano):
    with pytest.raises(ValueError):
        sortear_padres(tamano, np.random.default_rng(0))


def test_padres_es_reproducible():
    a = sortear_padres(12, np.random.default_rng(5))
    b = sortear_padres(12, np.random.default_rng(5))
    c = sortear_padres(12, np.random.default_rng(6))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


# ================================================================================================
# 2. mutar_diferencial
# ================================================================================================

def test_mutacion_a_mano_con_valores_concretos():
    poblacion = np.array([[0.0, 0.0], [1.0, 2.0], [3.0, -1.0], [-2.0, 4.0]])
    padres = np.array([[1, 2, 3], [0, 2, 3], [0, 1, 3], [0, 1, 2]])
    mutantes = mutar_diferencial(poblacion, padres, 0.5)
    # v_0 = x_1 + 0.5 (x_2 - x_3) = [1, 2] + 0.5 ([3, -1] - [-2, 4]) = [3.5, -0.5]
    assert np.allclose(mutantes[0], [3.5, -0.5])
    # v_1 = x_0 + 0.5 (x_2 - x_3) = [0, 0] + [2.5, -2.5]
    assert np.allclose(mutantes[1], [2.5, -2.5])
    # v_2 = x_0 + 0.5 (x_1 - x_3) = [0, 0] + 0.5 ([1, 2] - [-2, 4]) = [1.5, -1.0]
    assert np.allclose(mutantes[2], [1.5, -1.0])
    # v_3 = x_0 + 0.5 (x_1 - x_2) = [0, 0] + 0.5 ([1, 2] - [3, -1]) = [-1.0, 1.5]
    assert np.allclose(mutantes[3], [-1.0, 1.5])


@pytest.mark.parametrize("dimension", [2, 3, 5])
def test_mutacion_coincide_con_el_oraculo_de_bucles(dimension):
    rng = np.random.default_rng(10 + dimension)
    poblacion = rng.uniform(-3, 3, size=(8, dimension))
    padres = sortear_padres(8, rng)
    factor = 0.83
    mutantes = mutar_diferencial(poblacion, padres, factor)
    esperado = np.empty_like(poblacion)
    for i in range(8):
        r1, r2, r3 = padres[i]
        for j in range(dimension):
            esperado[i, j] = poblacion[r1, j] + factor * (poblacion[r2, j] - poblacion[r3, j])
    assert np.allclose(mutantes, esperado, rtol=0.0, atol=1e-12)
    assert mutantes.shape == poblacion.shape


def test_mutacion_no_modifica_las_entradas():
    rng = np.random.default_rng(1)
    poblacion = rng.uniform(-3, 3, size=(6, 2))
    padres = sortear_padres(6, rng)
    copia_poblacion, copia_padres = poblacion.copy(), padres.copy()
    mutantes = mutar_diferencial(poblacion, padres, 0.7)
    assert np.array_equal(poblacion, copia_poblacion)
    assert np.array_equal(padres, copia_padres)
    assert not np.shares_memory(mutantes, poblacion)


def test_mutacion_no_recorta_al_dominio():
    poblacion = np.array([[2.0, 0.0], [-2.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    padres = np.array([[0, 0, 2], [0, 0, 1], [0, 0, 1], [0, 0, 1]])
    salidos = mutar_diferencial(poblacion, padres, 1.0)
    # v_0 = x_0 + (x_0 - x_2) = 2 + 2 = 4: queda fuera del dominio, sin recortar
    assert salidos[0, 0] == 4.0
    # v_1 = x_0 + (x_0 - x_1) = 2 + 4 = 6
    assert salidos[1, 0] == 6.0


def test_mutacion_con_f_cero_copia_a_r1_y_f_pequeno_se_le_parece():
    rng = np.random.default_rng(2)
    poblacion = rng.uniform(-3, 3, size=(6, 3))
    padres = sortear_padres(6, rng)
    assert np.array_equal(mutar_diferencial(poblacion, padres, 0.0), poblacion[padres[:, 0]])
    pequeno = mutar_diferencial(poblacion, padres, 1e-9)
    assert np.allclose(pequeno, poblacion[padres[:, 0]], atol=1e-7)


# ================================================================================================
# 3. reiniciar_fuera_de_dominio
# ================================================================================================

LIMITES_DESIGUALES = np.array([[-2.0, 2.0], [-10.0, 30.0]])


def test_reinicio_solo_cambia_las_componentes_fuera():
    mutantes = np.array([[3.0, 0.0],      # j=0 fuera
                         [0.0, 31.0],     # j=1 fuera
                         [-3.0, -11.0],   # ambas fuera
                         [1.0, 5.0]])     # ninguna
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(0))
    assert isinstance(r, ResultadoReinicio)
    esperada = np.array([[True, False], [False, True], [True, True], [False, False]])
    assert np.array_equal(r.reiniciadas, esperada)
    # las de dentro, intactas
    assert np.array_equal(r.mutantes[~esperada], mutantes[~esperada])
    # las reiniciadas, dentro del dominio de SU dimensión
    lb, ub = LIMITES_DESIGUALES[:, 0], LIMITES_DESIGUALES[:, 1]
    assert np.all(r.mutantes >= lb) and np.all(r.mutantes <= ub)
    # y distintas del valor que tenían
    assert np.all(r.mutantes[esperada] != mutantes[esperada])


def test_reinicio_usa_el_sorteo_completo_en_la_posicion_correspondiente():
    mutantes = np.array([[3.0, 0.0], [0.0, 31.0], [1.0, 1.0]])
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(4))
    sorteo = np.random.default_rng(4).uniform(
        LIMITES_DESIGUALES[:, 0], LIMITES_DESIGUALES[:, 1], size=(3, 2))
    assert r.mutantes[0, 0] == sorteo[0, 0]
    assert r.mutantes[1, 1] == sorteo[1, 1]
    assert r.mutantes[0, 1] == 0.0 and r.mutantes[2, 0] == 1.0


def test_reinicio_valor_igual_al_limite_no_se_reinicia():
    mutantes = np.array([[2.0, -10.0], [-2.0, 30.0]])
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(0))
    assert not r.reiniciadas.any()
    assert np.array_equal(r.mutantes, mutantes)


def test_reinicio_consume_el_mismo_rng_haya_o_no_componentes_fuera():
    dentro = np.zeros((5, 2))
    fuera = np.full((5, 2), 100.0)
    rng_a, rng_b = np.random.default_rng(8), np.random.default_rng(8)
    reiniciar_fuera_de_dominio(dentro, LIMITES_DESIGUALES, rng_a)
    reiniciar_fuera_de_dominio(fuera, LIMITES_DESIGUALES, rng_b)
    assert rng_a.bit_generator.state == rng_b.bit_generator.state
    referencia = np.random.default_rng(8)
    referencia.uniform(LIMITES_DESIGUALES[:, 0], LIMITES_DESIGUALES[:, 1], size=(5, 2))
    assert rng_a.bit_generator.state == referencia.bit_generator.state


def test_reinicio_no_modifica_las_entradas_y_devuelve_copia():
    mutantes = np.array([[3.0, 0.0], [0.0, 1.0]])
    copia, limites = mutantes.copy(), LIMITES_DESIGUALES.copy()
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(0))
    assert np.array_equal(mutantes, copia)
    assert np.array_equal(LIMITES_DESIGUALES, limites)
    assert not np.shares_memory(r.mutantes, mutantes)


def test_reinicio_sin_componentes_fuera_devuelve_copia_igual():
    mutantes = np.array([[1.0, 1.0], [0.0, 0.0]])
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(0))
    assert np.array_equal(r.mutantes, mutantes)
    assert not np.shares_memory(r.mutantes, mutantes)


def test_reinicio_no_recorta_se_reinicia_con_valores_interiores():
    mutantes = np.full((200, 2), 1e9)
    r = reiniciar_fuera_de_dominio(mutantes, LIMITES_DESIGUALES, np.random.default_rng(3))
    assert r.reiniciadas.all()
    # uniforme: no se acumulan en la frontera (un recorte daría exactamente ub)
    assert not np.any(r.mutantes[:, 0] == 2.0)
    assert np.std(r.mutantes[:, 0]) > 0.5


# ================================================================================================
# 4. cruzar_binomial
# ================================================================================================

def _poblacion_y_mutantes(tamano: int, dimension: int, semilla: int = 0):
    rng = np.random.default_rng(semilla)
    poblacion = rng.uniform(-1, 1, size=(tamano, dimension))
    mutantes = rng.uniform(5, 6, size=(tamano, dimension))  # disjuntos de la población
    return poblacion, mutantes


def test_cruce_con_cr_cero_toma_exactamente_un_gen_del_mutante():
    poblacion, mutantes = _poblacion_y_mutantes(20, 5)
    r = cruzar_binomial(poblacion, mutantes, 0.0, np.random.default_rng(1))
    assert isinstance(r, ResultadoCruce)
    assert np.all(r.de_mutante.sum(axis=1) == 1)
    j_rand = np.random.default_rng(1)
    j_rand.random((20, 5))
    esperado = j_rand.integers(0, 5, size=20)
    assert np.array_equal(np.argmax(r.de_mutante, axis=1), esperado)


def test_cruce_con_cr_uno_es_el_mutante():
    poblacion, mutantes = _poblacion_y_mutantes(20, 4)
    r = cruzar_binomial(poblacion, mutantes, 1.0, np.random.default_rng(1))
    assert np.array_equal(r.hijos, mutantes)
    assert r.de_mutante.all()


@pytest.mark.parametrize("prob_cruce", [0.0, 0.1, 0.5, 0.9, 1.0])
def test_cruce_siempre_al_menos_un_gen_del_mutante(prob_cruce):
    poblacion, mutantes = _poblacion_y_mutantes(10, 3)
    for semilla in range(100):
        r = cruzar_binomial(poblacion, mutantes, prob_cruce, np.random.default_rng(semilla))
        assert np.all(r.de_mutante.sum(axis=1) >= 1)
        # el hijo realmente contiene ese gen del mutante (los rangos son disjuntos)
        assert np.all((r.hijos >= 5).sum(axis=1) >= 1)


def test_cruce_reconstruido_a_mano_con_replica_del_rng():
    poblacion, mutantes = _poblacion_y_mutantes(6, 4, semilla=2)
    r = cruzar_binomial(poblacion, mutantes, 0.4, np.random.default_rng(21))
    replica = np.random.default_rng(21)
    u = replica.random((6, 4))
    j_rand = replica.integers(0, 4, size=6)
    for i in range(6):
        for j in range(4):
            del_mutante = u[i, j] <= 0.4 or j == j_rand[i]
            assert r.de_mutante[i, j] == del_mutante
            esperado = mutantes[i, j] if del_mutante else poblacion[i, j]
            assert r.hijos[i, j] == esperado


def test_cruce_j_rand_en_el_rango_y_cubre_todas_las_columnas():
    poblacion, mutantes = _poblacion_y_mutantes(500, 3)
    r = cruzar_binomial(poblacion, mutantes, 0.0, np.random.default_rng(5))
    columnas = np.argmax(r.de_mutante, axis=1)
    assert columnas.min() >= 0 and columnas.max() <= 2
    assert set(columnas.tolist()) == {0, 1, 2}


def test_cruce_en_dimension_2():
    poblacion, mutantes = _poblacion_y_mutantes(8, 2)
    r = cruzar_binomial(poblacion, mutantes, 0.0, np.random.default_rng(0))
    assert r.hijos.shape == (8, 2)
    assert np.all(r.de_mutante.sum(axis=1) == 1)


def test_cruce_no_modifica_entradas_y_devuelve_copias():
    poblacion, mutantes = _poblacion_y_mutantes(6, 3)
    copia_p, copia_m = poblacion.copy(), mutantes.copy()
    r = cruzar_binomial(poblacion, mutantes, 1.0, np.random.default_rng(0))
    assert np.array_equal(poblacion, copia_p) and np.array_equal(mutantes, copia_m)
    assert not np.shares_memory(r.hijos, mutantes)
    assert not np.shares_memory(r.hijos, poblacion)


def test_cruce_consume_el_rng_en_el_orden_u_luego_j_rand():
    poblacion, mutantes = _poblacion_y_mutantes(5, 3)
    rng = np.random.default_rng(7)
    cruzar_binomial(poblacion, mutantes, 0.5, rng)
    esperado = np.random.default_rng(7)
    esperado.random((5, 3))
    esperado.integers(0, 3, size=5)
    assert rng.bit_generator.state == esperado.bit_generator.state


def test_cruce_proporcion_de_genes_del_mutante_se_parece_a_cr():
    poblacion, mutantes = _poblacion_y_mutantes(2000, 10)
    r = cruzar_binomial(poblacion, mutantes, 0.3, np.random.default_rng(11))
    # P(gen del mutante) = CR + (1 - CR)/d = 0.3 + 0.07 = 0.37
    assert abs(r.de_mutante.mean() - 0.37) < 0.02


# ================================================================================================
# 5. seleccionar_codiciosa
# ================================================================================================

def test_seleccion_empate_gana_el_hijo():
    poblacion = np.array([[0.0, 0.0]])
    hijos = np.array([[1.0, 1.0]])
    r = seleccionar_codiciosa(poblacion, np.array([2.0]), hijos, np.array([2.0]))
    assert isinstance(r, ResultadoSeleccion)
    assert np.array_equal(r.poblacion, hijos)
    assert r.reemplazaron.tolist() == [True]


def test_seleccion_mejora_estricta_y_peor_conserva_al_padre():
    poblacion = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    hijos = np.array([[9.0, 9.0], [8.0, 8.0], [7.0, 7.0]])
    aptitudes = np.array([5.0, 5.0, 5.0])
    aptitudes_hijos = np.array([4.0, 6.0, 5.0])
    r = seleccionar_codiciosa(poblacion, aptitudes, hijos, aptitudes_hijos)
    assert r.reemplazaron.tolist() == [True, False, True]
    assert np.array_equal(r.poblacion, np.array([[9.0, 9.0], [1.0, 1.0], [7.0, 7.0]]))
    assert r.aptitudes.tolist() == [4.0, 5.0, 5.0]


def test_seleccion_la_aptitud_nunca_empeora():
    rng = np.random.default_rng(0)
    for _ in range(100):
        aptitudes = rng.uniform(0, 10, size=12)
        aptitudes_hijos = rng.uniform(0, 10, size=12)
        r = seleccionar_codiciosa(rng.random((12, 2)), aptitudes, rng.random((12, 2)),
                                  aptitudes_hijos)
        assert np.all(r.aptitudes <= aptitudes)
        assert np.array_equal(r.aptitudes, np.minimum(aptitudes, aptitudes_hijos))


def test_seleccion_devuelve_copias_sin_alias():
    poblacion = np.array([[0.0, 0.0], [1.0, 1.0]])
    hijos = np.array([[5.0, 5.0], [6.0, 6.0]])
    aptitudes, aptitudes_hijos = np.array([1.0, 1.0]), np.array([0.0, 2.0])
    copias = [a.copy() for a in (poblacion, hijos, aptitudes, aptitudes_hijos)]
    r = seleccionar_codiciosa(poblacion, aptitudes, hijos, aptitudes_hijos)
    for original, copia in zip((poblacion, hijos, aptitudes, aptitudes_hijos), copias):
        assert np.array_equal(original, copia)
    for devuelto in (r.poblacion, r.aptitudes):
        for entrada in (poblacion, hijos, aptitudes, aptitudes_hijos):
            assert not np.shares_memory(devuelto, entrada)
    r.poblacion[0, 0] = -99.0
    assert hijos[0, 0] == 5.0 and poblacion[0, 0] == 0.0


def test_seleccion_formas_incoherentes():
    with pytest.raises(ValueError):
        seleccionar_codiciosa(np.zeros((3, 2)), np.zeros(2), np.zeros((3, 2)), np.zeros(3))
    with pytest.raises(ValueError):
        seleccionar_codiciosa(np.zeros((3, 2)), np.zeros(3), np.zeros((3, 3)), np.zeros(3))


# ================================================================================================
# 6. optimize
# ================================================================================================

@pytest.mark.parametrize("nombre", ["rosenbrock", "rastrigin"])
@pytest.mark.parametrize("dim", [2, 3])
def test_ningun_punto_evaluado_sale_del_dominio(nombre, dim):
    for semilla in range(5):
        func = FuncionRegistradora(get_function(nombre, dim))
        _correr(func, 1_500.0, semilla=semilla)
        puntos = np.array(func.puntos_evaluados)
        assert np.all(puntos >= func.bounds[:, 0]) and np.all(puntos <= func.bounds[:, 1])


def test_history_es_monotono_y_estrictamente_decreciente_en_f():
    _, r = _correr(get_function("rastrigin", 2), 3_000.0)
    f_hist = [p["f_best"] for p in r["history"]]
    assert all(b < a for a, b in zip(f_hist, f_hist[1:]))
    equiv = [p["eval_equiv"] for p in r["history"]]
    assert all(b >= a for a, b in zip(equiv, equiv[1:]))
    assert r["f_best"] == f_hist[-1]


def test_conteo_con_generaciones_fijas():
    _, r = _correr(get_function("rosenbrock", 2), 1e6, generaciones=10)
    assert r["n_f"] == 30 * (10 + 1) == 330
    assert r["n_grad"] == 0
    assert r["eval_equiv"] == r["n_f"]
    assert [fr["iter"] for fr in r["frames"]] == list(range(11))


def test_generaciones_cero_solo_evalua_la_poblacion_inicial():
    _, r = _correr(get_function("rosenbrock", 2), 1e6, generaciones=0)
    assert r["n_f"] == 30
    assert [fr["iter"] for fr in r["frames"]] == [0]


def test_truncado_2d_presupuesto_20000():
    _, r = _correr(get_function("rosenbrock", 2), 20_000.0)
    assert r["n_f"] == 20_000
    assert len(r["frames"]) == 666
    assert r["frames"][-1]["iter"] == 665
    assert r["n_grad"] == 0 and r["eval_equiv"] == 20_000.0


def test_truncado_3d_presupuesto_30000_sin_frames():
    _, r = _correr(get_function("rastrigin", 3), 30_000.0)
    assert r["n_f"] == 30_000
    assert "frames" not in r


def test_presupuesto_menor_que_np_devuelve_el_mejor_visto():
    func = FuncionRegistradora(get_function("rastrigin", 2))
    _, r = _correr(func, 10.0)
    assert r["n_f"] == 10
    assert r["frames"] == []
    assert r["f_best"] == min(func.valores)
    assert len(func.valores) == 10


def test_presupuesto_que_no_alcanza_para_una_evaluacion_es_valueerror():
    func = get_function("rastrigin", 2)
    with pytest.raises(ValueError, match="presupuesto"):
        optimize(nuevo_problema(func, 0.5), cfg_completo(), make_rng(0, 0))


def test_misma_semilla_mismo_resultado_semilla_distinta_difiere():
    func = get_function("rastrigin", 2)
    _, a = _correr(func, 2_000.0, semilla=3)
    _, b = _correr(func, 2_000.0, semilla=3)
    _, c = _correr(func, 2_000.0, semilla=4)
    assert a == b
    assert a["x_best"] != c["x_best"]


def test_orden_del_rng_reproduce_la_primera_generacion_a_mano():
    func = get_function("rastrigin", 2)
    tamano, factor, prob = 6, 0.6, 0.7
    _, r = _correr(func, 1e6, semilla=13, generaciones=1, NP=tamano, F=factor, CR=prob)

    rng = np.random.default_rng(13)                       # make_rng(13, 0)
    lb, ub = func.bounds[:, 0], func.bounds[:, 1]
    poblacion = rng.uniform(lb, ub, size=(tamano, 2))                       # (1)
    aptitudes = np.array([func.f(x) for x in poblacion])
    sorteo = rng.random((tamano, tamano))                                   # (2)
    np.fill_diagonal(sorteo, np.inf)
    padres = np.argsort(sorteo, axis=1)[:, :3]
    mutantes = poblacion[padres[:, 0]] + factor * (poblacion[padres[:, 1]]
                                                   - poblacion[padres[:, 2]])
    reinicio = rng.uniform(lb, ub, size=(tamano, 2))                        # (3)
    fuera = (mutantes < lb) | (mutantes > ub)
    mutantes = np.where(fuera, reinicio, mutantes)
    u = rng.random((tamano, 2))                                             # (4)
    j_rand = rng.integers(0, 2, size=tamano)                                # (5)
    de_mutante = (u <= prob) | (np.arange(2)[None, :] == j_rand[:, None])
    hijos = np.where(de_mutante, mutantes, poblacion)
    aptitudes_hijos = np.array([func.f(x) for x in hijos])
    gana = aptitudes_hijos <= aptitudes
    esperada = np.where(gana[:, None], hijos, poblacion)

    assert np.array_equal(np.array(r["frames"][0]["positions"]), poblacion)
    assert np.array_equal(np.array(r["frames"][1]["positions"]), esperada)


def test_frames_forma_mejor_y_sin_alias():
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 1e6, generaciones=5)
    for frame in r["frames"]:
        assert set(frame) == {"iter", "positions", "best"}
        posiciones = np.array(frame["positions"])
        assert posiciones.shape == (30, 2)
        valores = np.array([func.f(x) for x in posiciones])
        assert frame["best"] == posiciones[np.argmin(valores)].tolist()
    # las listas de frames distintos no comparten memoria
    assert r["frames"][0]["positions"] is not r["frames"][1]["positions"]
    assert r["frames"][0]["positions"][0] is not r["frames"][1]["positions"][0]
    r["frames"][0]["positions"][0][0] = 1e9
    assert r["frames"][1]["positions"][0][0] != 1e9


def test_sin_frames_con_record_frames_falso_o_dim_3():
    _, sin = _correr(get_function("rastrigin", 2), 1_000.0, record_frames=False)
    assert "frames" not in sin
    _, tres = _correr(get_function("rastrigin", 3), 1_000.0, record_frames=True)
    assert "frames" not in tres


def test_retorno_del_contrato_con_tipos_nativos():
    _, r = _correr(get_function("rosenbrock", 2), 2_000.0)
    assert {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history", "frames"} <= set(r)
    assert type(r["x_best"]) is list and all(type(v) is float for v in r["x_best"])
    assert type(r["f_best"]) is float
    assert type(r["n_f"]) is int and type(r["n_grad"]) is int
    assert type(r["eval_equiv"]) is float
    json.dumps(r)


def test_history_es_una_copia_de_la_del_problema():
    problema, r = _correr(get_function("rosenbrock", 2), 1_000.0)
    assert r["history"] == problema.history
    assert r["history"] is not problema.history
    r["history"][0]["f_best"] = -1.0
    assert problema.history[0]["f_best"] != -1.0


def test_optimize_no_cuenta_a_mano_sale_de_problem():
    func = FuncionRegistradora(get_function("rosenbrock", 3))
    problema, r = _correr(func, 2_500.0)
    assert r["n_f"] == problema.n_f == len(func.puntos_evaluados)
    assert r["eval_equiv"] == problema.eval_equiv()
    assert r["x_best"] == problema.best_x.tolist()


def test_humo_con_base_yaml_en_las_cuatro_combinaciones():
    cfg = load_config(RUTA_BASE)
    # func y dim son listas en la base: se construye el problema aparte y solo se pasa `de`
    cfg_optimizador = {"de": cfg["de"], "record_frames": cfg["record_frames"]}
    for nombre in cfg["func"]:
        for dim in cfg["dim"]:
            func = get_function(nombre, dim)
            problema = CountedProblem(func, k=2 * dim, budget=10_000 * dim)
            r = optimize(problema, cfg_optimizador, make_rng(cfg["base_seed"], 0))
            assert r["n_f"] == 10_000 * dim
            assert r["n_grad"] == 0
            assert ("frames" in r) == (dim == 2)
            # La corrida debe MEJORAR a la mejor de la población inicial (las NP primeras
            # evaluaciones); `f_best >= f*` sería casi tautológico (f >= 0 en ambas funciones).
            tamano = cfg["de"]["NP"]
            mejor_inicial = min(p["f_best"] for p in r["history"] if p["eval_equiv"] <= tamano)
            assert r["f_best"] < mejor_inicial


def test_overrides_de_la_config_llegan_al_algoritmo():
    cfg = load_config(RUTA_BASE)
    func = get_function("rastrigin", 2)
    cfg_np12 = apply_overrides(cfg, ["de.NP=12", "de.generaciones=4", "de.F=0.5"])
    assert cfg_np12["de"]["F"] == 0.5
    r = optimize(nuevo_problema(func, 1e6), cfg_np12, make_rng(0, 0))
    assert r["n_f"] == 12 * 5
    assert len(r["frames"][0]["positions"]) == 12


def test_optimize_sin_bloque_de_o_sin_record_frames_falla_con_mensaje_claro():
    func = get_function("rastrigin", 2)
    with pytest.raises(ValueError, match="de"):
        optimize(nuevo_problema(func, 1000.0), {"record_frames": True}, make_rng(0, 0))
    with pytest.raises(ValueError, match="record_frames"):
        optimize(nuevo_problema(func, 1000.0), {"de": cfg_de()}, make_rng(0, 0))
    with pytest.raises(TypeError):
        optimize(nuevo_problema(func, 1000.0), {"de": cfg_de(), "record_frames": "si"},
                 make_rng(0, 0))
    with pytest.raises(ValueError):
        optimize(nuevo_problema(func, 1000.0), {"de": cfg_de(NP=3), "record_frames": True},
                 make_rng(0, 0))


def test_optimize_con_np_4_funciona():
    func = FuncionRegistradora(get_function("rastrigin", 2))
    _, r = _correr(func, 200.0, NP=4)
    assert r["n_f"] == 200
    puntos = np.array(func.puntos_evaluados)
    assert np.all(np.abs(puntos) <= 5.12)


def test_sanidad_de_convergencia_en_esfera_2d_con_20000_evaluaciones():
    """Umbral fijado con lo MEDIDO (30 semillas, 20 000 evaluaciones): f_best máximo = 6.1e-116."""
    for semilla in range(30):
        _, r = _correr(Esfera(2), 20_000.0, semilla=semilla, record_frames=False)
        assert r["f_best"] < 1e-10, f"semilla {semilla}: f_best = {r['f_best']}"


def test_sanidad_de_convergencia_en_rastrigin_2d_con_20000_evaluaciones():
    """Medido: las 30 semillas (0-29) llegan a f_best = 0.0 con 20 000 evaluaciones."""
    for semilla in range(30):
        _, r = _correr(get_function("rastrigin", 2), 20_000.0, semilla=semilla,
                       record_frames=False)
        assert r["f_best"] <= 1e-4, f"semilla {semilla}: f_best = {r['f_best']}"


# ================================================================================================
# 7. Higiene
# ================================================================================================

def test_no_usa_azar_global_ni_modifica_su_estado():
    estado_numpy = np.random.get_state()
    estado_random = random.getstate()
    _correr(get_function("rastrigin", 2), 2_000.0)
    assert np.random.get_state()[1].tolist() == estado_numpy[1].tolist()
    assert np.random.get_state()[2:] == estado_numpy[2:]
    assert random.getstate() == estado_random


def test_el_codigo_no_importa_random_ni_siembra_global():
    texto = RUTA_DE.read_text(encoding="utf-8")
    assert not re.search(r"(?m)^\s*(import random|from random)", texto)
    assert "np.random.seed" not in texto


@pytest.mark.parametrize("ruta", [RUTA_DE, RUTA_PRUEBAS], ids=["de.py", "test_de.py"])
def test_lineas_de_hasta_100_caracteres(ruta):
    texto = ruta.read_text(encoding="utf-8")
    largas = [i + 1 for i, linea in enumerate(texto.splitlines()) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    """Error B1 de T1.4: ningún def/class/import/from fuera de una celda `# %%` de código."""
    celda_actual = None
    for numero, linea in enumerate(RUTA_DE.read_text(encoding="utf-8").splitlines(), start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_con_tabla_de_componentes_y_latex():
    texto = RUTA_DE.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in ("ParametrosDE", "sortear_padres", "mutar_diferencial",
                   "reiniciar_fuera_de_dominio", "cruzar_binomial", "seleccionar_codiciosa",
                   "optimize"):
        assert f"`{nombre}`" in cabecera
    celdas = re.split(r"(?m)^# %%.*\n", texto)
    for funcion, latex in (("def mutar_diferencial(", "r_3"),
                           ("def cruzar_binomial(", "j_{\\text{rand}}"),
                           ("def seleccionar_codiciosa(", "\\le")):
        indice = next(i for i, celda in enumerate(celdas) if funcion in celda)
        assert latex in celdas[indice - 1]
