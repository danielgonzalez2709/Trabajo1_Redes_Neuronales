"""Pruebas del algoritmo evolutivo de la Parte 1 (T1.4; Spec §6.2 y §6.4, v1.4).

Un grupo de pruebas por componente de `src/part1/ea.py`, de lo más pequeño a lo más grande:

    0. ParametrosEA        -> tamaños de los grupos y validación de la configuración
    1-2. generar_poblacion_inicial y evaluar_poblacion: comunes a EA, PSO y DE; sus pruebas
         están en tests/test_comun.py (T1.6b)
    3. seleccionar_elite
    4. mutar_individuos    -> se reconstruye el ruido con una copia del rng (misma semilla)
    5. cruzar_individuos   -> se deducen los padres de cada hijo
    6. ensamblar_nueva_generacion
    7. optimize            -> integración con CountedProblem, conteo y reproducibilidad

Los componentes (1-6) se prueban SIN CountedProblem: solo arreglos, `limites`, `rng` y un callable.
Todo el azar de las pruebas sale de `np.random.default_rng(<entero fijo>)`.
"""

from __future__ import annotations

import dataclasses
import inspect
import math
import random
import re
from pathlib import Path

import numpy as np
import pytest

from src.common.config import apply_overrides, load_config
from src.common.counter import CountedProblem
from src.common.results import load_json, save_json
from src.common.seeds import make_rng
from src.part1 import ea as ea_mod
from src.part1.ea import (
    ParametrosEA,
    ResultadoCruce,
    ResultadoMutacion,
    cruzar_individuos,
    ensamblar_nueva_generacion,
    mutar_individuos,
    optimize,
    seleccionar_elite,
)
from src.part1.functions import get_function

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_EA = RAIZ / "src" / "part1" / "ea.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

# Valores por defecto del Spec §6.4 (se repiten a propósito: la prueba de base.yaml los compara).
CFG_EA_SPEC = {
    "esquema": "clase",
    "N": 50,
    "frac_e": 0.15,
    "frac_m": 0.10,
    "frac_c": 0.75,
    "reevaluar_elite": False,
    "generaciones": None,
}
LIMITE_SIN_RECORTE = 100.0  # dominio enorme: la mutación nunca llega al borde


def cfg_ea(**cambios) -> dict:
    """Bloque `ea:` con los valores del Spec y los cambios pedidos."""
    bloque = dict(CFG_EA_SPEC)
    bloque.update(cambios)
    return bloque


def cfg_completo(record_frames: bool = True, **cambios) -> dict:
    """Configuración mínima que recibe optimize: bloque `ea` y `record_frames`."""
    return {"ea": cfg_ea(**cambios), "record_frames": record_frames}


def limites_cuadrados(dim: int, limite: float = LIMITE_SIN_RECORTE) -> np.ndarray:
    """Dominio [-limite, limite]^dim como arreglo (dim, 2)."""
    return np.tile(np.array([-limite, limite]), (dim, 1))


def poblacion_aleatoria(tamano: int, dim: int, semilla: int = 7, amplitud: float = 2.0):
    """Población de prueba (tamano, dim) con valores en [-amplitud, amplitud]."""
    rng = np.random.default_rng(semilla)
    return rng.uniform(-amplitud, amplitud, size=(tamano, dim))


def nuevo_problema(func, presupuesto: float) -> CountedProblem:
    """CountedProblem con k = 2n (Spec §6.2, principal)."""
    return CountedProblem(func, k=2 * func.dim, budget=presupuesto)


# ================================================================================================
# 0. ParametrosEA
# ================================================================================================

# (N, frac_e, frac_m, frac_c, n_elite, n_mutantes, n_cruzantes): valores CALCULADOS A MANO.
#   n_elite = round(N*frac_e) (round de Python: mitades al par), n_mutantes = int(N*frac_m),
#   n_cruzantes = max(par_arriba(int(N*frac_c)), par_arriba(N - n_elite - n_mutantes)).
CASOS_TAMANOS = [
    # 7.5 -> 8; 5; 37 -> 38; suma 51 (se recorta 1 hijo)
    pytest.param(50, 0.15, 0.10, 0.75, 8, 5, 38, id="defecto_N50"),
    # 4.5 -> 4; 3; 22; relleno 23 -> 24
    pytest.param(30, 0.15, 0.10, 0.75, 4, 3, 24, id="N30_relleno"),
    # 4.2 -> 4; 2.1 -> 2; 10; relleno 15 -> 16
    pytest.param(21, 0.20, 0.10, 0.50, 4, 2, 16, id="N_impar"),
    # int(0) = 0; relleno 20
    pytest.param(40, 0.25, 0.25, 0.00, 10, 10, 20, id="frac_c_cero_relleno"),
    # élite + mutantes = N: no hace falta cruce
    pytest.param(10, 0.50, 0.50, 0.00, 5, 5, 0, id="sin_cruce"),
    # 9 -> 10; relleno 8
    pytest.param(10, 0.10, 0.10, 0.90, 1, 1, 10, id="cruce_alto"),
    # 1; 0; 1 -> 2
    pytest.param(2, 0.50, 0.00, 0.50, 1, 0, 2, id="N_minimo"),
    # 7.5 -> 8; 3; 15 -> 16; relleno 19 -> 20
    pytest.param(30, 0.25, 0.10, 0.50, 8, 3, 20, id="mitad_al_par_arriba"),
    # 3.5 -> 4; 0; 7 -> 8; relleno 10
    pytest.param(14, 0.25, 0.00, 0.50, 4, 0, 10, id="redondeo_3.5_a_4"),
]


@pytest.mark.parametrize("N,frac_e,frac_m,frac_c,n_elite,n_mutantes,n_cruzantes", CASOS_TAMANOS)
def test_tamanos_de_grupos_calculados_a_mano(N, frac_e, frac_m, frac_c, n_elite, n_mutantes,
                                             n_cruzantes):
    p = ParametrosEA.desde_config(cfg_ea(N=N, frac_e=frac_e, frac_m=frac_m, frac_c=frac_c))
    assert p.n_elite == n_elite
    assert p.n_mutantes == n_mutantes
    assert p.n_cruzantes == n_cruzantes
    assert p.n_cruzantes % 2 == 0, "n_cruzantes siempre par (parejas)"
    # la nueva generación siempre se puede completar hasta N (luego se recortan hijos)
    assert p.n_elite + p.n_mutantes + p.n_cruzantes >= N


def test_parametros_conserva_los_valores_de_la_config():
    p = ParametrosEA.desde_config(cfg_ea(N=30, reevaluar_elite=True, generaciones=7))
    assert p.tamano_poblacion == 30
    assert p.fraccion_elite == 0.15
    assert p.fraccion_mutantes == 0.10
    assert p.fraccion_cruce == 0.75
    assert p.reevaluar_elite is True
    assert p.generaciones == 7


def test_parametros_es_dataclass_congelada():
    p = ParametrosEA.desde_config(cfg_ea())
    assert dataclasses.is_dataclass(p)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.tamano_poblacion = 99


def test_parametros_acepta_enteros_numpy_y_generaciones_none_o_entero():
    ParametrosEA.desde_config(cfg_ea(N=np.int64(30), generaciones=np.int64(4)))
    assert ParametrosEA.desde_config(cfg_ea(generaciones=None)).generaciones is None
    assert ParametrosEA.desde_config(cfg_ea(generaciones=0)).generaciones == 0
    assert ParametrosEA.desde_config(cfg_ea(frac_c=0)).n_cruzantes == 38  # fracción entera 0 válida


CASOS_TIPO_INVALIDO = [
    ("N", True), ("N", 50.0), ("N", "50"), ("N", None),
    ("frac_e", True), ("frac_m", "0.1"), ("frac_c", None), ("frac_e", [0.1]),
    ("reevaluar_elite", 1), ("reevaluar_elite", "false"), ("reevaluar_elite", None),
    ("generaciones", True), ("generaciones", 3.0), ("generaciones", "5"),
]


@pytest.mark.parametrize("clave,valor", CASOS_TIPO_INVALIDO)
def test_validacion_tipo_incorrecto_lanza_typeerror(clave, valor):
    with pytest.raises(TypeError):
        ParametrosEA.desde_config(cfg_ea(**{clave: valor}))


CASOS_VALOR_INVALIDO = [
    ("N", 1), ("N", 0), ("N", -5),
    ("frac_e", -0.1), ("frac_m", -1e-9), ("frac_c", -0.75),
    ("frac_e", math.nan), ("frac_m", math.inf), ("frac_c", -math.inf),
    ("generaciones", -1),
]


@pytest.mark.parametrize("clave,valor", CASOS_VALOR_INVALIDO)
def test_validacion_valor_fuera_de_rango_lanza_valueerror(clave, valor):
    with pytest.raises(ValueError):
        ParametrosEA.desde_config(cfg_ea(**{clave: valor}))


def test_validacion_elite_mas_mutantes_mayor_que_N():
    with pytest.raises(ValueError, match="elite|élite"):
        ParametrosEA.desde_config(cfg_ea(N=50, frac_e=0.6, frac_m=0.5))


def test_validacion_n_cruzantes_mayor_que_N():
    # N impar y sin élite ni mutantes: el relleno (par hacia arriba de 5) es 6 > N = 5
    with pytest.raises(ValueError, match="cruz"):
        ParametrosEA.desde_config(cfg_ea(N=5, frac_e=0.0, frac_m=0.0, frac_c=0.0))
    # frac_c = 1 con N impar: par hacia arriba de 5 = 6 > 5
    with pytest.raises(ValueError, match="cruz"):
        ParametrosEA.desde_config(cfg_ea(N=5, frac_e=0.0, frac_m=0.0, frac_c=1.0))


def test_validacion_poblacion_congelada_sin_evaluaciones():
    """Toda la población es élite y no se reevalúa: ninguna generación evaluaría nada."""
    with pytest.raises(ValueError, match="reevaluar_elite"):
        ParametrosEA.desde_config(cfg_ea(frac_e=1.0, frac_m=0.0, frac_c=0.0))
    # con reevaluación sí tiene sentido
    p = ParametrosEA.desde_config(
        cfg_ea(frac_e=1.0, frac_m=0.0, frac_c=0.0, reevaluar_elite=True))
    assert p.n_elite == 50


@pytest.mark.parametrize("esquema", ["spec", "torneo", "Clase", "", 3])
def test_esquema_distinto_de_clase_falla_con_mensaje_claro(esquema):
    with pytest.raises(ValueError) as info:
        ParametrosEA.desde_config(cfg_ea(esquema=esquema))
    mensaje = str(info.value)
    assert repr(esquema) in mensaje or str(esquema) in mensaje
    assert "clase" in mensaje


def test_falta_de_claves_nombra_las_claves_faltantes():
    bloque = cfg_ea()
    del bloque["frac_m"]
    del bloque["N"]
    with pytest.raises(ValueError) as info:
        ParametrosEA.desde_config(bloque)
    mensaje = str(info.value)
    assert "frac_m" in mensaje and "N" in mensaje
    assert "frac_e" not in mensaje  # solo las que faltan


def test_clave_desconocida_en_el_bloque_falla():
    with pytest.raises(ValueError, match="frac_x"):
        ParametrosEA.desde_config(cfg_ea(frac_x=0.1))


def test_bloque_que_no_es_mapeo_lanza_typeerror():
    with pytest.raises(TypeError):
        ParametrosEA.desde_config([50, 0.15])


def test_base_yaml_contiene_el_bloque_ea_con_los_defaults_del_spec():
    cfg = load_config(RUTA_BASE)
    assert cfg["ea"] == CFG_EA_SPEC
    assert isinstance(cfg["ea"]["N"], int) and not isinstance(cfg["ea"]["N"], bool)
    assert type(cfg["ea"]["frac_e"]) is float
    p = ParametrosEA.desde_config(cfg["ea"])
    assert (p.n_elite, p.n_mutantes, p.n_cruzantes) == (8, 5, 38)


def test_base_yaml_no_cambio_el_bloque_ea():
    cfg = load_config(RUTA_BASE)
    assert cfg["ea"]["N"] == 50 and cfg["ea"]["esquema"] == "clase"


# ================================================================================================
# 3. seleccionar_elite
# ================================================================================================

def test_elite_son_los_de_menor_aptitud_y_salen_ordenados_de_mejor_a_peor():
    poblacion = np.array([[0.0, 0], [1, 1], [2, 2], [3, 3], [4, 4]])
    aptitudes = np.array([5.0, 1.0, 3.0, 0.5, 9.0])
    elite, aptitudes_elite = seleccionar_elite(poblacion, aptitudes, 3)
    # a mano: de menor a mayor aptitud -> filas 3 (0.5), 1 (1.0), 2 (3.0)
    assert np.array_equal(elite, np.array([[3.0, 3], [1, 1], [2, 2]]))
    assert np.array_equal(aptitudes_elite, np.array([0.5, 1.0, 3.0]))


def test_elite_empates_el_indice_menor_primero():
    poblacion = np.array([[0.0], [1], [2], [3], [4]])
    aptitudes = np.array([5.0, 1.0, 3.0, 1.0, 1.0])
    elite, aptitudes_elite = seleccionar_elite(poblacion, aptitudes, 2)
    assert np.array_equal(elite, np.array([[1.0], [3.0]]))  # filas 1 y 3, no 4
    assert np.array_equal(aptitudes_elite, np.array([1.0, 1.0]))


def test_elite_devuelve_copias_y_aptitudes_alineadas():
    poblacion = poblacion_aleatoria(10, 2, semilla=11)
    aptitudes = np.sum(poblacion ** 2, axis=1)
    original = poblacion.copy()
    elite, aptitudes_elite = seleccionar_elite(poblacion, aptitudes, 4)
    assert np.allclose(np.sum(elite ** 2, axis=1), aptitudes_elite)
    elite[:] = 123.0
    aptitudes_elite[:] = 123.0
    assert np.array_equal(poblacion, original)
    assert np.allclose(aptitudes, np.sum(original ** 2, axis=1))


def test_elite_cero_individuos_devuelve_arreglos_vacios_con_forma():
    poblacion = poblacion_aleatoria(10, 3)
    elite, aptitudes_elite = seleccionar_elite(poblacion, np.arange(10.0), 0)
    assert elite.shape == (0, 3)
    assert aptitudes_elite.shape == (0,)


def test_elite_toda_la_poblacion_sale_ordenada():
    poblacion = poblacion_aleatoria(8, 2, semilla=5)
    aptitudes = np.array([4.0, 2.0, 8.0, 1.0, 7.0, 3.0, 6.0, 5.0])
    elite, aptitudes_elite = seleccionar_elite(poblacion, aptitudes, 8)
    assert np.array_equal(aptitudes_elite, np.sort(aptitudes))
    assert np.array_equal(elite[0], poblacion[3])


def test_elite_no_depende_del_orden_de_las_filas_de_la_poblacion():
    """Con aptitudes distintas, permutar las filas no cambia ni la élite ni su orden."""
    poblacion = poblacion_aleatoria(12, 3, semilla=21)
    aptitudes = np.sum(poblacion ** 2, axis=1)
    permutacion = np.random.default_rng(22).permutation(12)
    elite_a, aptitudes_a = seleccionar_elite(poblacion, aptitudes, 5)
    elite_b, aptitudes_b = seleccionar_elite(poblacion[permutacion], aptitudes[permutacion], 5)
    assert np.array_equal(elite_a, elite_b)
    assert np.array_equal(aptitudes_a, aptitudes_b)


def test_elite_validaciones():
    poblacion = poblacion_aleatoria(5, 2)
    with pytest.raises(ValueError):
        seleccionar_elite(poblacion, np.arange(5.0), 6)       # más élite que individuos
    with pytest.raises(ValueError):
        seleccionar_elite(poblacion, np.arange(4.0), 2)       # aptitudes de otra longitud
    with pytest.raises(ValueError):
        seleccionar_elite(poblacion, np.arange(5.0), -1)
    with pytest.raises(TypeError):
        seleccionar_elite(poblacion, np.arange(5.0), 2.0)


# ================================================================================================
# 4. mutar_individuos
# ================================================================================================

def _reconstruir_azar_de_mutacion(semilla: int, N: int, dim: int, n_mutantes: int):
    """Misma secuencia del rng que documenta mutar_individuos.

    choice -> integers -> standard_normal. Devuelve también el rng de referencia para comparar
    el estado final (que no se consuma azar de más).
    """
    rng = np.random.default_rng(semilla)
    indices_origen = rng.choice(N, size=n_mutantes, replace=False)
    genes_mutados = rng.integers(0, dim, size=n_mutantes)
    ruido_estandar = rng.standard_normal(size=n_mutantes)
    return indices_origen, genes_mutados, ruido_estandar, rng


@pytest.mark.parametrize("dim", [2, 3, 5])
def test_mutacion_forma_indices_y_genes_validos(dim):
    N, n_mutantes = 40, 9
    poblacion = poblacion_aleatoria(N, dim)
    r = mutar_individuos(poblacion, n_mutantes, limites_cuadrados(dim), np.random.default_rng(1))
    assert isinstance(r, ResultadoMutacion)
    assert r.mutantes.shape == (n_mutantes, dim)
    assert r.indices_origen.shape == (n_mutantes,)
    assert r.genes_mutados.shape == (n_mutantes,)
    assert len(set(r.indices_origen.tolist())) == n_mutantes, "indices_origen sin repetir"
    assert np.all((r.indices_origen >= 0) & (r.indices_origen < N))
    assert np.all((r.genes_mutados >= 0) & (r.genes_mutados < dim))


@pytest.mark.parametrize("semilla", [0, 1, 2, 3, 4])
def test_mutacion_individuos_sin_repeticion_aun_con_casi_toda_la_poblacion(semilla):
    N = 20
    poblacion = poblacion_aleatoria(N, 2)
    r = mutar_individuos(poblacion, 18, limites_cuadrados(2), np.random.default_rng(semilla))
    assert len(set(r.indices_origen.tolist())) == 18


@pytest.mark.parametrize("dim,semilla", [(2, 0), (3, 1), (4, 2)])
def test_mutacion_cada_mutante_difiere_de_su_origen_solo_en_un_gen_con_ruido_esperado(dim,
                                                                                       semilla):
    N, n_mutantes = 30, 12
    poblacion = poblacion_aleatoria(N, dim, semilla=20 + semilla)
    rng = np.random.default_rng(semilla)
    r = mutar_individuos(poblacion, n_mutantes, limites_cuadrados(dim), rng)

    indices, genes, ruido, rng_referencia = _reconstruir_azar_de_mutacion(
        semilla, N, dim, n_mutantes)
    assert rng.random() == rng_referencia.random(), "orden y cantidad de sorteos documentados"
    sigma_por_gen = poblacion.std(axis=0, ddof=0)  # desviación poblacional (ddof=0)
    assert np.array_equal(r.indices_origen, indices)
    assert np.array_equal(r.genes_mutados, genes)
    for k in range(n_mutantes):
        origen = poblacion[indices[k]]
        gen = genes[k]
        otras_columnas = np.arange(dim) != gen
        assert np.array_equal(r.mutantes[k][otras_columnas], origen[otras_columnas])
        esperado = origen[gen] + ruido[k] * sigma_por_gen[gen]
        assert r.mutantes[k, gen] == pytest.approx(esperado, rel=1e-12, abs=1e-12)
        assert r.mutantes[k, gen] != origen[gen]


def test_mutacion_sigma_es_poblacional_y_por_gen():
    """Dos genes con escalas muy distintas: cada ruido se escala con SU sigma (ddof=0)."""
    rng_datos = np.random.default_rng(31)
    poblacion = np.column_stack([
        rng_datos.normal(0.0, 0.01, 10),
        rng_datos.normal(0.0, 10.0, 10),
    ])
    r = mutar_individuos(poblacion, 10, limites_cuadrados(2, 1e6), np.random.default_rng(6))
    indices, genes, ruido, _ = _reconstruir_azar_de_mutacion(6, 10, 2, 10)
    sigma_ddof0 = poblacion.std(axis=0, ddof=0)
    sigma_ddof1 = poblacion.std(axis=0, ddof=1)
    for k in range(10):
        cambio = r.mutantes[k, genes[k]] - poblacion[indices[k], genes[k]]
        assert cambio == pytest.approx(ruido[k] * sigma_ddof0[genes[k]], rel=1e-9, abs=1e-15)
        assert cambio != pytest.approx(ruido[k] * sigma_ddof1[genes[k]], rel=1e-9, abs=1e-15)


def test_mutacion_recorta_al_dominio():
    """Población pegada a los bordes: sin recorte, el ruido (sigma = 1) saca a casi todos."""
    limites = limites_cuadrados(2, 1.0)
    N = 40
    poblacion = np.where(np.arange(N)[:, None] % 2 == 0, -1.0, 1.0) * np.ones((N, 2))
    assert poblacion.std(axis=0, ddof=0)[0] == pytest.approx(1.0)
    r = mutar_individuos(poblacion, N, limites, np.random.default_rng(9))
    assert np.all(r.mutantes >= -1.0) and np.all(r.mutantes <= 1.0)
    # la prueba es significativa: sin recorte alguien habría salido del dominio
    indices, genes, ruido, _ = _reconstruir_azar_de_mutacion(9, N, 2, N)
    sin_recorte = poblacion[indices, genes] + ruido * 1.0
    assert np.any(np.abs(sin_recorte) > 1.0)


def test_mutacion_recorta_con_el_limite_de_cada_gen():
    limites = np.array([[0.0, 0.1], [-50.0, 50.0]])
    poblacion = np.column_stack([np.linspace(0.0, 0.1, 30), np.linspace(-40.0, 40.0, 30)])
    r = mutar_individuos(poblacion, 30, limites, np.random.default_rng(10))
    assert np.all(r.mutantes[:, 0] >= 0.0) and np.all(r.mutantes[:, 0] <= 0.1)
    assert np.all(np.abs(r.mutantes[:, 1]) <= 50.0)


def test_mutacion_no_modifica_la_poblacion_de_entrada():
    poblacion = poblacion_aleatoria(20, 3)
    copia = poblacion.copy()
    mutar_individuos(poblacion, 20, limites_cuadrados(3), np.random.default_rng(12))
    assert np.array_equal(poblacion, copia)


def test_mutacion_cero_mutantes_forma_y_no_consume_azar():
    poblacion = poblacion_aleatoria(10, 3)
    rng = np.random.default_rng(13)
    r = mutar_individuos(poblacion, 0, limites_cuadrados(3), rng)
    assert r.mutantes.shape == (0, 3)
    assert r.indices_origen.shape == (0,)
    assert r.genes_mutados.shape == (0,)
    siguiente = rng.random()
    assert siguiente == np.random.default_rng(13).random()  # el rng quedó intacto


def test_mutacion_misma_semilla_mismo_resultado():
    poblacion = poblacion_aleatoria(25, 2)
    a = mutar_individuos(poblacion, 6, limites_cuadrados(2), np.random.default_rng(14))
    b = mutar_individuos(poblacion, 6, limites_cuadrados(2), np.random.default_rng(14))
    c = mutar_individuos(poblacion, 6, limites_cuadrados(2), np.random.default_rng(15))
    assert np.array_equal(a.mutantes, b.mutantes)
    assert np.array_equal(a.indices_origen, b.indices_origen)
    assert not np.array_equal(a.mutantes, c.mutantes)


def test_mutacion_con_poblacion_colapsada_no_cambia_nada_y_no_produce_nan():
    """sigma = 0 (todos iguales): el ruido se anula y cada mutante es idéntico a su origen."""
    poblacion = np.full((10, 3), 0.5)
    r = mutar_individuos(poblacion, 4, limites_cuadrados(3), np.random.default_rng(17))
    assert not np.any(np.isnan(r.mutantes))
    assert np.array_equal(r.mutantes, poblacion[r.indices_origen])


def test_mutacion_validaciones():
    poblacion = poblacion_aleatoria(10, 2)
    with pytest.raises(ValueError):
        mutar_individuos(poblacion, 11, limites_cuadrados(2), np.random.default_rng(0))
    with pytest.raises(ValueError):
        mutar_individuos(poblacion, -1, limites_cuadrados(2), np.random.default_rng(0))
    with pytest.raises(TypeError):
        mutar_individuos(poblacion, 2.0, limites_cuadrados(2), np.random.default_rng(0))
    with pytest.raises(ValueError):
        mutar_individuos(poblacion, 2, limites_cuadrados(3), np.random.default_rng(0))


# ================================================================================================
# 5. cruzar_individuos
# ================================================================================================

def _reconstruir_azar_de_cruce(semilla: int, N: int, dim: int, n_cruzantes: int):
    """Misma secuencia del rng que documenta cruzar_individuos: choice -> integers."""
    rng = np.random.default_rng(semilla)
    cruzantes = rng.choice(N, size=n_cruzantes, replace=False)
    cortes = rng.integers(1, dim, size=n_cruzantes // 2)
    return cruzantes, cortes


@pytest.mark.parametrize("dim,n_cruzantes", [(2, 10), (3, 12), (5, 20)])
def test_cruce_formas_y_dos_hijos_por_pareja(dim, n_cruzantes):
    N = 30
    poblacion = poblacion_aleatoria(N, dim)
    r = cruzar_individuos(poblacion, n_cruzantes, np.random.default_rng(1))
    mitad = n_cruzantes // 2
    assert isinstance(r, ResultadoCruce)
    assert r.hijos.shape == (n_cruzantes, dim)
    assert r.indices_padre.shape == (mitad,)
    assert r.indices_madre.shape == (mitad,)
    assert r.puntos_corte.shape == (mitad,)


@pytest.mark.parametrize("dim,semilla", [(2, 0), (3, 1), (5, 2), (4, 3)])
def test_cruce_pareja_k_es_cruzante_k_con_cruzante_k_mas_mitad_y_sin_repetir(dim, semilla):
    N, n_cruzantes = 30, 14
    mitad = n_cruzantes // 2
    poblacion = poblacion_aleatoria(N, dim)
    r = cruzar_individuos(poblacion, n_cruzantes, np.random.default_rng(semilla))
    cruzantes, cortes = _reconstruir_azar_de_cruce(semilla, N, dim, n_cruzantes)
    assert np.array_equal(r.indices_padre, cruzantes[:mitad])
    assert np.array_equal(r.indices_madre, cruzantes[mitad:])
    assert np.array_equal(r.puntos_corte, cortes)
    todos = np.concatenate([r.indices_padre, r.indices_madre])
    assert len(set(todos.tolist())) == n_cruzantes, "los cruzantes se eligen sin repetir"


@pytest.mark.parametrize("semilla", range(8))
def test_cruce_punto_de_corte_nunca_es_0_ni_d(semilla):
    for dim in (2, 3, 6):
        poblacion = poblacion_aleatoria(30, dim)
        r = cruzar_individuos(poblacion, 20, np.random.default_rng(semilla))
        assert np.all(r.puntos_corte >= 1)
        assert np.all(r.puntos_corte <= dim - 1)


@pytest.mark.parametrize("dim,semilla", [(2, 4), (3, 5), (6, 6)])
def test_cruce_los_hijos_se_deducen_de_los_padres(dim, semilla):
    """hijo1 = padre[:p] + madre[p:] (fila 2k); hijo2 = madre[:p] + padre[p:] (fila 2k+1)."""
    poblacion = poblacion_aleatoria(30, dim)
    r = cruzar_individuos(poblacion, 16, np.random.default_rng(semilla))
    for k in range(8):
        padre = poblacion[r.indices_padre[k]]
        madre = poblacion[r.indices_madre[k]]
        p = r.puntos_corte[k]
        esperado_1 = np.concatenate([padre[:p], madre[p:]])
        esperado_2 = np.concatenate([madre[:p], padre[p:]])
        assert np.array_equal(r.hijos[2 * k], esperado_1)
        assert np.array_equal(r.hijos[2 * k + 1], esperado_2)
        # y los hijos no son copias de los padres (los padres de la prueba son distintos)
        assert not np.array_equal(r.hijos[2 * k], padre)
        assert not np.array_equal(r.hijos[2 * k], madre)


def test_cruce_en_2d_el_unico_corte_es_1_y_solo_se_intercambian_coordenadas():
    poblacion = poblacion_aleatoria(20, 2)
    r = cruzar_individuos(poblacion, 20, np.random.default_rng(7))
    assert np.all(r.puntos_corte == 1)
    for k in range(10):
        padre = poblacion[r.indices_padre[k]]
        madre = poblacion[r.indices_madre[k]]
        assert np.array_equal(r.hijos[2 * k], np.array([padre[0], madre[1]]))
        assert np.array_equal(r.hijos[2 * k + 1], np.array([madre[0], padre[1]]))


def test_cruce_no_modifica_la_poblacion():
    poblacion = poblacion_aleatoria(20, 3)
    copia = poblacion.copy()
    cruzar_individuos(poblacion, 20, np.random.default_rng(8))
    assert np.array_equal(poblacion, copia)


def test_cruce_cero_cruzantes_forma_y_no_consume_azar():
    poblacion = poblacion_aleatoria(10, 3)
    rng = np.random.default_rng(9)
    r = cruzar_individuos(poblacion, 0, rng)
    assert r.hijos.shape == (0, 3)
    assert r.indices_padre.shape == (0,)
    assert r.indices_madre.shape == (0,)
    assert r.puntos_corte.shape == (0,)
    assert rng.random() == np.random.default_rng(9).random()


def test_cruce_misma_semilla_mismo_resultado():
    poblacion = poblacion_aleatoria(25, 3)
    a = cruzar_individuos(poblacion, 10, np.random.default_rng(10))
    b = cruzar_individuos(poblacion, 10, np.random.default_rng(10))
    c = cruzar_individuos(poblacion, 10, np.random.default_rng(11))
    assert np.array_equal(a.hijos, b.hijos)
    assert np.array_equal(a.puntos_corte, b.puntos_corte)
    assert not np.array_equal(a.hijos, c.hijos)


def test_cruce_consume_el_rng_en_el_orden_documentado():
    poblacion = poblacion_aleatoria(25, 4)
    rng = np.random.default_rng(12)
    cruzar_individuos(poblacion, 10, rng)
    referencia = np.random.default_rng(12)
    referencia.choice(25, size=10, replace=False)
    referencia.integers(1, 4, size=5)
    assert rng.random() == referencia.random()


def test_cruce_validaciones():
    poblacion = poblacion_aleatoria(10, 3)
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="par"):
        cruzar_individuos(poblacion, 5, rng)                       # impar
    with pytest.raises(ValueError):
        cruzar_individuos(poblacion_aleatoria(10, 1), 4, rng)      # d < 2: no hay corte posible
    with pytest.raises(ValueError):
        cruzar_individuos(poblacion, 12, rng)                      # más cruzantes que individuos
    with pytest.raises(ValueError):
        cruzar_individuos(poblacion, -2, rng)
    with pytest.raises(TypeError):
        cruzar_individuos(poblacion, 4.0, rng)


# ================================================================================================
# 6. ensamblar_nueva_generacion
# ================================================================================================

def _grupos(n_elite: int, n_mutantes: int, n_hijos: int, dim: int = 2):
    """Filas identificables: la élite vale 1000+i, los mutantes 2000+i y los hijos 3000+i."""
    elite = (1000.0 + np.arange(n_elite))[:, None] * np.ones((1, dim))
    mutantes = (2000.0 + np.arange(n_mutantes))[:, None] * np.ones((1, dim))
    hijos = (3000.0 + np.arange(n_hijos))[:, None] * np.ones((1, dim))
    return elite, mutantes, hijos


def test_ensamblar_orden_elite_mutantes_hijos_con_tamano_exacto():
    elite, mutantes, hijos = _grupos(2, 3, 5)
    nueva = ensamblar_nueva_generacion(elite, mutantes, hijos, 10)
    assert nueva.shape == (10, 2)
    assert np.array_equal(nueva[:, 0], np.array([1000, 1001, 2000, 2001, 2002,
                                                 3000, 3001, 3002, 3003, 3004.0]))


def test_ensamblar_si_sobran_filas_quita_las_ultimas_de_hijos():
    elite, mutantes, hijos = _grupos(8, 5, 38)        # 51 filas, tamano 50 (caso por defecto)
    nueva = ensamblar_nueva_generacion(elite, mutantes, hijos, 50)
    assert nueva.shape == (50, 2)
    assert np.array_equal(nueva[:8], elite)
    assert np.array_equal(nueva[8:13], mutantes)
    assert np.array_equal(nueva[13:], hijos[:37])      # falta justo el último hijo


def test_ensamblar_nunca_quita_elite_ni_mutantes_si_basta_con_quitar_hijos():
    elite, mutantes, hijos = _grupos(3, 4, 20)
    nueva = ensamblar_nueva_generacion(elite, mutantes, hijos, 7)   # quedan 0 hijos
    assert np.array_equal(nueva, np.vstack([elite, mutantes]))


def test_ensamblar_sin_hijos_o_sin_mutantes_con_arreglos_vacios():
    elite, mutantes, hijos = _grupos(4, 0, 6, dim=3)
    nueva = ensamblar_nueva_generacion(elite, mutantes, hijos, 10)
    assert nueva.shape == (10, 3)
    assert np.array_equal(nueva[:4], elite) and np.array_equal(nueva[4:], hijos)


def test_ensamblar_si_faltan_filas_lanza_valueerror():
    elite, mutantes, hijos = _grupos(2, 2, 2)
    with pytest.raises(ValueError, match="faltan|falta"):
        ensamblar_nueva_generacion(elite, mutantes, hijos, 10)


def test_ensamblar_si_elite_mas_mutantes_superan_el_tamano_lanza_valueerror():
    elite, mutantes, hijos = _grupos(5, 6, 4)
    with pytest.raises(ValueError):
        ensamblar_nueva_generacion(elite, mutantes, hijos, 10)


def test_ensamblar_no_modifica_las_entradas_ni_comparte_memoria():
    elite, mutantes, hijos = _grupos(2, 2, 6)
    copias = [elite.copy(), mutantes.copy(), hijos.copy()]
    nueva = ensamblar_nueva_generacion(elite, mutantes, hijos, 8)
    nueva[:] = -1.0
    for original, copia in zip((elite, mutantes, hijos), copias):
        assert np.array_equal(original, copia)


def test_ensamblar_dimensiones_incompatibles():
    elite, mutantes, _ = _grupos(2, 2, 0, dim=2)
    hijos = np.zeros((6, 3))
    with pytest.raises(ValueError):
        ensamblar_nueva_generacion(elite, mutantes, hijos, 8)


# ================================================================================================
# 7. optimize (orquestador) — integración con CountedProblem
# ================================================================================================

CLAVES_RETORNO = {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history"}


def _correr(func, presupuesto, semilla=0, record_frames=True, **cambios):
    problema = nuevo_problema(func, presupuesto)
    resultado = optimize(problema, cfg_completo(record_frames, **cambios), make_rng(semilla, 0))
    return problema, resultado


def test_retorno_tiene_las_claves_del_contrato_y_tipos_nativos(tmp_path):
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 2000.0)
    assert CLAVES_RETORNO <= set(r) <= CLAVES_RETORNO | {"frames"}
    assert isinstance(r["x_best"], list) and len(r["x_best"]) == 2
    assert all(type(v) is float for v in r["x_best"])
    assert type(r["f_best"]) is float
    assert type(r["n_f"]) is int and type(r["n_grad"]) is int
    assert type(r["eval_equiv"]) is float
    assert isinstance(r["history"], list)
    for h in r["history"]:
        assert set(h) == {"eval_equiv", "f_best"}
        assert type(h["eval_equiv"]) is float and type(h["f_best"]) is float
    # JSON-serializable con el guardado del proyecto (sin NaN/inf, claves de texto)
    ruta = save_json(tmp_path / "ea.json", {"result": r})
    assert load_json(ruta)["result"]["x_best"] == r["x_best"]


@pytest.mark.parametrize("T", [0, 1, 3, 10])
def test_conteo_con_elite_en_cache_es_N_mas_T_por_N_menos_elite(T):
    func = get_function("rastrigin", 2)
    problema, r = _correr(func, 1e6, generaciones=T)
    assert r["n_f"] == 50 + T * (50 - 8)     # 50 + 42 T
    assert r["n_grad"] == 0
    assert r["eval_equiv"] == float(r["n_f"])
    assert problema.n_f == r["n_f"]


@pytest.mark.parametrize("T", [0, 1, 4])
def test_conteo_reevaluando_la_elite_es_N_por_T_mas_1(T):
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 1e6, generaciones=T, reevaluar_elite=True)
    assert r["n_f"] == 50 * (T + 1)
    assert r["n_grad"] == 0
    assert r["eval_equiv"] == float(r["n_f"])


def test_el_contador_coincide_con_las_llamadas_reales_de_la_funcion(cuadratica):
    func = cuadratica([1.0, -1.0])
    problema = nuevo_problema(func, 1e6)
    r = optimize(problema, cfg_completo(generaciones=6), make_rng(0, 0))
    assert func.llamadas_f == r["n_f"] == problema.n_f == 50 + 6 * 42
    assert func.llamadas_grad == 0


def test_presupuesto_2d_exacto_y_476_frames():
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 20_000.0)
    assert r["n_f"] == 20_000                  # 50 + 42*475, sin truncar
    assert r["eval_equiv"] <= 20_000.0
    assert len(r["frames"]) == 476             # iter 0..475
    assert [f["iter"] for f in r["frames"]] == list(range(476))


def test_presupuesto_no_multiplo_trunca_la_ultima_generacion_sin_frame():
    func = get_function("rosenbrock", 2)
    # 50 + 42*713 = 29 996; sobran 4 evaluaciones de la generación 714 (truncada)
    problema, r = _correr(func, 30_000.0)
    assert r["n_f"] == 30_000
    assert r["eval_equiv"] <= 30_000.0
    assert len(r["frames"]) == 714             # iter 0..713; la truncada NO registra frame
    assert r["frames"][-1]["iter"] == 713
    assert problema.n_f == 30_000


def test_presupuesto_3d_30000_cuenta_exacto_y_no_hay_frames():
    func = get_function("rosenbrock", 3)
    _, r = _correr(func, 30_000.0)
    assert r["n_f"] == 30_000                  # 713 generaciones + 4 evaluaciones truncadas
    assert r["eval_equiv"] <= 30_000.0
    assert "frames" not in r                   # frames solo en 2D (§5.1)


def test_presupuesto_pequeno_trunca_la_poblacion_inicial_y_devuelve_el_mejor_visto():
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 10.0, semilla=5)
    assert r["n_f"] == 10
    # el mejor de las 10 primeras filas de la población inicial (misma semilla, mismo orden)
    inicial = make_rng(5, 0).uniform(func.bounds[:, 0], func.bounds[:, 1], size=(50, 2))
    valores = np.array([func.f(x) for x in inicial[:10]])
    mejor = int(np.argmin(valores))
    assert r["f_best"] == valores[mejor]
    assert r["x_best"] == inicial[mejor].tolist()
    assert r["frames"] == []                   # ni la población inicial se completó: sin frames


def test_presupuesto_menor_que_uno_lanza_valueerror_claro():
    func = get_function("rastrigin", 2)
    problema = nuevo_problema(func, 0.5)
    with pytest.raises(ValueError, match="presupuesto"):
        optimize(problema, cfg_completo(), make_rng(0, 0))


def test_generaciones_cero_solo_evalua_la_poblacion_inicial():
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 1e6, generaciones=0)
    assert r["n_f"] == 50
    assert len(r["frames"]) == 1
    assert r["frames"][0]["iter"] == 0


@pytest.mark.parametrize("nombre,dim", [("rosenbrock", 2), ("rastrigin", 2), ("rastrigin", 3)])
def test_historial_no_empeora_y_f_best_es_la_f_de_x_best(nombre, dim):
    func = get_function(nombre, dim)
    _, r = _correr(func, 5_000.0 * dim)
    valores = [h["f_best"] for h in r["history"]]
    assert valores == sorted(valores, reverse=True)
    equivalentes = [h["eval_equiv"] for h in r["history"]]
    assert equivalentes == sorted(equivalentes)
    assert r["f_best"] == func.f(np.array(r["x_best"]))
    assert r["history"][-1]["f_best"] == r["f_best"]


def test_history_es_copia_del_historial_del_problema():
    func = get_function("rosenbrock", 2)
    problema, r = _correr(func, 1_000.0)
    assert r["history"] == problema.history
    assert r["history"] is not problema.history
    r["history"][0]["f_best"] = -1.0
    assert problema.history[0]["f_best"] != -1.0


def test_misma_semilla_mismo_resultado_y_semillas_distintas_no():
    func = get_function("rastrigin", 2)
    _, a = _correr(func, 3_000.0, semilla=3)
    _, b = _correr(func, 3_000.0, semilla=3)
    _, c = _correr(func, 3_000.0, semilla=4)
    assert a == b
    assert a["x_best"] != c["x_best"] or a["history"] != c["history"]


def test_no_usa_azar_global_ni_modifica_su_estado():
    estado_numpy = np.random.get_state()
    estado_random = random.getstate()
    func = get_function("rastrigin", 2)
    _correr(func, 2_000.0)
    assert np.random.get_state()[1].tolist() == estado_numpy[1].tolist()
    assert np.random.get_state()[2:] == estado_numpy[2:]
    assert random.getstate() == estado_random


def test_ea_no_importa_random_ni_siembra_numpy_global():
    texto = RUTA_EA.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import random|from random)", texto, re.M)
    assert "np.random.seed" not in texto


@pytest.mark.parametrize("ruta", [RUTA_EA, RUTA_PRUEBAS], ids=["ea.py", "test_ea.py"])
def test_lineas_de_hasta_100_caracteres(ruta):
    texto = ruta.read_text(encoding="utf-8")
    largas = [i + 1 for i, linea in enumerate(texto.splitlines()) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


@pytest.mark.parametrize("nombre,limite", [("rosenbrock", 2.048), ("rastrigin", 5.12)])
def test_ningun_frame_sale_del_dominio(nombre, limite):
    func = get_function(nombre, 2)
    _, r = _correr(func, 6_000.0)
    assert len(r["frames"]) > 100
    for frame in r["frames"]:
        posiciones = np.array(frame["positions"])
        assert posiciones.shape == (50, 2)
        assert np.all(np.abs(posiciones) <= limite)
        assert np.all(np.abs(frame["best"]) <= limite)
    assert np.all(np.abs(r["x_best"]) <= limite)


def test_forma_de_los_frames_y_best_es_el_mejor_global_hasta_ese_frame():
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 8_000.0, semilla=2)
    frames = r["frames"]
    inicial = make_rng(2, 0).uniform(func.bounds[:, 0], func.bounds[:, 1], size=(50, 2))
    assert frames[0]["iter"] == 0
    assert frames[0]["positions"] == inicial.tolist()      # iter 0 = población inicial
    mejor_hasta_ahora = math.inf
    for t, frame in enumerate(frames):
        assert set(frame) == {"iter", "positions", "best"}
        assert frame["iter"] == t
        assert len(frame["positions"]) == 50
        assert all(len(par) == 2 for par in frame["positions"])
        assert len(frame["best"]) == 2
        valores = [func.f(np.array(par)) for par in frame["positions"]]
        mejor_hasta_ahora = min(mejor_hasta_ahora, min(valores))
        # best = mejor GLOBAL: su f es el mínimo de todo lo evaluado hasta este frame
        assert func.f(np.array(frame["best"])) == mejor_hasta_ahora
    assert frames[-1]["best"] == r["x_best"]


def test_best_del_frame_es_global_aun_cuando_la_generacion_empeora():
    """Sin élite (frac_e=0) la mejor fila de una generación puede ser peor que la global."""
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 8_000.0, semilla=1, frac_e=0.0, frac_m=0.10, frac_c=0.75)
    valores_best = [func.f(np.array(frame["best"])) for frame in r["frames"]]
    assert valores_best == sorted(valores_best, reverse=True)
    mejor_de_cada_poblacion = [
        min(func.f(np.array(par)) for par in frame["positions"]) for frame in r["frames"]
    ]
    # la prueba es significativa: alguna generación sí tuvo un mejor peor que el global previo
    assert any(
        mejor_de_cada_poblacion[t] > valores_best[t] for t in range(1, len(r["frames"]))
    )
    assert r["frames"][-1]["best"] == r["x_best"]


def test_presupuesto_igual_a_N_exacto_evalua_la_poblacion_inicial_y_nada_mas():
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 50.0)
    assert r["n_f"] == 50
    assert r["eval_equiv"] == 50.0
    assert [f["iter"] for f in r["frames"]] == [0]       # un frame: la población inicial


def test_optimize_con_poblacion_minima_N_2_de_extremo_a_extremo():
    """N = 2: n_elite = 1, sin mutantes, 1 pareja que produce 2 hijos (se recorta 1)."""
    func = get_function("rastrigin", 2)
    parametros = dict(N=2, frac_e=0.5, frac_m=0.0, frac_c=0.5)
    problema, r = _correr(func, 52.0, **parametros)
    assert r["n_f"] == 52                      # 2 + 50 generaciones de (N - n_elite) = 1
    assert len(r["frames"]) == 51              # iter 0..50
    assert all(len(frame["positions"]) == 2 for frame in r["frames"])
    assert r["f_best"] == func.f(np.array(r["x_best"]))
    assert np.all(np.abs(r["x_best"]) <= 5.12)


class FuncionRegistradora:
    """Envuelve una TestFunction y guarda una copia de CADA punto que recibe `f`."""

    def __init__(self, func):
        self.name = func.name
        self.dim = func.dim
        self.bounds = func.bounds
        self.x_star = func.x_star
        self.f_star = func.f_star
        self._func = func
        self.puntos_evaluados: list[np.ndarray] = []

    def f(self, x):
        self.puntos_evaluados.append(np.array(x, dtype=float, copy=True))
        return self._func.f(x)

    def grad(self, x):
        return self._func.grad(x)


@pytest.mark.parametrize("nombre,limite", [("rosenbrock", 2.048), ("rastrigin", 5.12)])
def test_todo_punto_evaluado_en_3d_esta_dentro_del_dominio(nombre, limite):
    func = FuncionRegistradora(get_function(nombre, 3))
    problema = nuevo_problema(func, 6_000.0)
    r = optimize(problema, cfg_completo(), make_rng(4, 0))
    puntos = np.array(func.puntos_evaluados)
    assert puntos.shape == (r["n_f"], 3)       # cada evaluación contada llegó a la función
    assert np.all(np.abs(puntos) <= limite)
    assert "frames" not in r


def test_frame_de_generacion_truncada_no_se_registra_en_2d():
    func = get_function("rastrigin", 2)
    # 50 + 42*22 = 974; sobran 26 evaluaciones de la generación 23 (truncada)
    _, r = _correr(func, 1_000.0)
    assert r["n_f"] == 1_000
    assert [f["iter"] for f in r["frames"]] == list(range(23))


def test_frames_solo_si_dim_2_y_record_frames():
    f2 = get_function("rastrigin", 2)
    f3 = get_function("rastrigin", 3)
    assert "frames" not in _correr(f2, 1_000.0, record_frames=False)[1]
    assert "frames" not in _correr(f3, 1_000.0, record_frames=True)[1]
    assert "frames" in _correr(f2, 1_000.0, record_frames=True)[1]


def test_el_mejor_global_no_se_pierde_y_cuadratica_2d_converge(cuadratica):
    func = cuadratica([1.0, -1.0])
    _, r = _correr(func, 20_000.0)
    assert r["f_best"] <= 1e-4
    assert np.allclose(r["x_best"], [1.0, -1.0], atol=1e-1)


# ------------------------------------------------- contrato entre componentes (espías)

def _espiar(monkeypatch, nombre: str, bitacora: list) -> list:
    """Envuelve ea.<nombre>: guarda {parametro: valor} de cada llamada (copias de los arreglos)
    y anota el orden de las llamadas. Enlaza por NOMBRE de parámetro, no por posición."""
    original = getattr(ea_mod, nombre)
    firma = inspect.signature(original)
    llamadas: list = []

    def envoltura(*args, **kwargs):
        ligados = firma.bind(*args, **kwargs).arguments
        llamadas.append({
            clave: valor.copy() if isinstance(valor, np.ndarray) else valor
            for clave, valor in ligados.items()
        })
        bitacora.append(nombre)
        return original(*args, **kwargs)

    monkeypatch.setattr(ea_mod, nombre, envoltura)
    return llamadas


@pytest.mark.parametrize("reevaluar", [False, True])
def test_la_elite_se_selecciona_con_las_aptitudes_de_la_poblacion_actual(monkeypatch, reevaluar):
    func = get_function("rosenbrock", 2)
    bitacora: list = []
    llamadas = _espiar(monkeypatch, "seleccionar_elite", bitacora)
    _correr(func, 1e6, generaciones=4, reevaluar_elite=reevaluar)
    assert len(llamadas) == 4
    for llamada in llamadas:
        esperadas = np.array([func.f(x) for x in llamada["poblacion"]])
        assert np.array_equal(llamada["aptitudes"], esperadas), (
            "la élite debe usar las aptitudes de la población actual, no las de la inicial "
            "(el cuaderno de clase ordenaba con las iniciales; CAMBIO-EA.md §8)"
        )
        assert llamada["n_elite"] == 8


def test_mutacion_y_cruce_reciben_la_poblacion_completa_y_el_mismo_rng(monkeypatch):
    func = get_function("rastrigin", 2)
    bitacora: list = []
    elite = _espiar(monkeypatch, "seleccionar_elite", bitacora)
    mutar = _espiar(monkeypatch, "mutar_individuos", bitacora)
    cruzar = _espiar(monkeypatch, "cruzar_individuos", bitacora)
    ensamblar = _espiar(monkeypatch, "ensamblar_nueva_generacion", bitacora)
    rng = make_rng(0, 0)
    optimize(nuevo_problema(func, 1e6), cfg_completo(generaciones=3), rng)
    assert len(elite) == len(mutar) == len(cruzar) == len(ensamblar) == 3
    for t in range(3):
        poblacion_t = elite[t]["poblacion"]
        assert poblacion_t.shape == (50, 2)
        assert np.array_equal(mutar[t]["poblacion"], poblacion_t)    # completa y sin ordenar
        assert np.array_equal(cruzar[t]["poblacion"], poblacion_t)
        assert (mutar[t]["n_mutantes"], cruzar[t]["n_cruzantes"]) == (5, 38)
        assert np.array_equal(mutar[t]["limites"], func.bounds)
        assert mutar[t]["rng"] is rng and cruzar[t]["rng"] is rng    # un solo rng, inyectado
        assert ensamblar[t]["tamano"] == 50
        assert ensamblar[t]["elite"].shape == (8, 2)
    # orden fijo por generación: élite -> mutar -> cruzar -> ensamblar
    assert bitacora == ["seleccionar_elite", "mutar_individuos", "cruzar_individuos",
                        "ensamblar_nueva_generacion"] * 3


# ------------------------------------------------- humo con la configuración real y overrides

def test_humo_con_base_yaml_rosenbrock_2d():
    cfg = load_config(RUTA_BASE)
    func = get_function("rosenbrock", 2)
    problema = CountedProblem(func, k=2 * func.dim, budget=10_000 * func.dim)
    r = optimize(problema, cfg, make_rng(0, 0))
    assert r["n_f"] == 20_000
    assert r["n_grad"] == 0
    assert len(r["frames"]) == 476
    assert r["f_best"] < 1.0


def test_overrides_de_la_config_llegan_al_algoritmo():
    cfg = load_config(RUTA_BASE)
    func = get_function("rastrigin", 2)

    cfg_n30 = apply_overrides(cfg, ["ea.N=30"])
    r30 = optimize(nuevo_problema(func, 1e6), {**cfg_n30, "ea": {**cfg_n30["ea"],
                                                                    "generaciones": 2}},
                   make_rng(0, 0))
    assert r30["n_f"] == 30 + 2 * (30 - 4)                # N=30 -> n_elite = 4
    assert len(r30["frames"][0]["positions"]) == 30

    cfg_g5 = apply_overrides(cfg, ["ea.generaciones=5"])
    r5 = optimize(nuevo_problema(func, 1e6), cfg_g5, make_rng(0, 0))
    assert r5["n_f"] == 50 + 5 * 42

    cfg_spec = apply_overrides(cfg, ["ea.esquema=spec"])
    with pytest.raises(ValueError) as info:
        optimize(nuevo_problema(func, 1e6), cfg_spec, make_rng(0, 0))
    assert "spec" in str(info.value) and "clase" in str(info.value)


def test_optimize_sin_bloque_ea_o_sin_record_frames_falla_con_mensaje_claro():
    func = get_function("rastrigin", 2)
    with pytest.raises(ValueError, match="ea"):
        optimize(nuevo_problema(func, 1000.0), {"record_frames": True}, make_rng(0, 0))
    with pytest.raises(ValueError, match="record_frames"):
        optimize(nuevo_problema(func, 1000.0), {"ea": cfg_ea()}, make_rng(0, 0))
    with pytest.raises(TypeError):
        optimize(nuevo_problema(func, 1000.0), {"ea": cfg_ea(), "record_frames": "si"},
                 make_rng(0, 0))
    bloque = cfg_ea()
    del bloque["frac_e"]
    with pytest.raises(ValueError, match="frac_e"):
        optimize(nuevo_problema(func, 1000.0), {"ea": bloque, "record_frames": True},
                 make_rng(0, 0))


def test_optimize_no_modifica_la_config():
    cfg = cfg_completo(generaciones=2)
    copia = {"ea": dict(cfg["ea"]), "record_frames": cfg["record_frames"]}
    optimize(nuevo_problema(get_function("rastrigin", 2), 1e6), cfg, make_rng(0, 0))
    assert cfg == copia
