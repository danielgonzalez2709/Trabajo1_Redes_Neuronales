"""Pruebas del PSO de la Parte 1 (T1.5; Spec §6.2 y §6.4, v1.4): gbest con inercia.

Un grupo de pruebas por componente de `src/part1/pso.py`, de lo más pequeño a lo más grande:

    0. ParametrosPSO                 -> validación del bloque `pso:` y defaults de base.yaml
    1. generar_enjambre_inicial
    2. calcular_velocidad_maxima
    3. actualizar_memoria_personal
    4. actualizar_mejor_global
    5. calcular_velocidades          -> ecuación a mano, oráculo con bucles y casos límite
    6. limitar_velocidades
    7. aplicar_frontera
    8. optimize                      -> integración con CountedProblem, conteo y reproducibilidad

Los componentes (1-7) se prueban SIN CountedProblem: solo arreglos, `limites`, `rng` y un callable.
Todo el azar de las pruebas sale de `np.random.default_rng(<entero fijo>)`.
"""

from __future__ import annotations

import dataclasses
import json
import math
import random
import re
import warnings
from pathlib import Path

import numpy as np
import pytest

from src.common.config import apply_overrides, load_config
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.part1.functions import get_function
from src.part1.pso import (
    EnjambreInicial,
    MejorGlobal,
    ParametrosPSO,
    ResultadoFrontera,
    ResultadoMemoria,
    actualizar_mejor_global,
    actualizar_memoria_personal,
    aplicar_frontera,
    calcular_velocidad_maxima,
    calcular_velocidades,
    generar_enjambre_inicial,
    limitar_velocidades,
    optimize,
)

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_PSO = RAIZ / "src" / "part1" / "pso.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

# Valores por defecto del Spec §6.4 (se repiten a propósito: la prueba de base.yaml los compara).
CFG_PSO_SPEC = {
    "N": 30,
    "w": 0.7298,
    "c1": 1.49618,
    "c2": 1.49618,
    "vmax_frac": 0.2,
    "iteraciones": None,
}
LIMITE_ENORME = 1e6  # dominio que nunca se toca


def cfg_pso(**cambios) -> dict:
    """Bloque `pso:` con los valores del Spec y los cambios pedidos."""
    bloque = dict(CFG_PSO_SPEC)
    bloque.update(cambios)
    return bloque


def cfg_completo(record_frames: bool = True, **cambios) -> dict:
    """Configuración mínima que recibe optimize: bloque `pso` y `record_frames`."""
    return {"pso": cfg_pso(**cambios), "record_frames": record_frames}


def limites_cuadrados(dim: int, limite: float = LIMITE_ENORME) -> np.ndarray:
    """Dominio [-limite, limite]^dim como arreglo (dim, 2)."""
    return np.tile(np.array([-limite, limite]), (dim, 1))


def nuevo_problema(func, presupuesto: float) -> CountedProblem:
    """CountedProblem con k = 2n (Spec §6.2, principal)."""
    return CountedProblem(func, k=2 * func.dim, budget=presupuesto)


def esfera(x) -> float:
    """f(x) = x_1^2 + x_2^2 (función de los ejemplos a mano)."""
    x = np.asarray(x, dtype=float)
    return float(np.sum(x ** 2))


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


def _correr(func, presupuesto: float, semilla: int = 0, record_frames: bool = True, **cambios):
    """Corre optimize con k = 2n; devuelve (problema, resultado)."""
    problema = nuevo_problema(func, presupuesto)
    resultado = optimize(problema, cfg_completo(record_frames, **cambios), make_rng(semilla, 0))
    return problema, resultado


# ================================================================================================
# 0. ParametrosPSO
# ================================================================================================

def test_parametros_con_los_defaults_del_spec():
    p = ParametrosPSO.desde_config(cfg_pso())
    assert p.tamano_enjambre == 30
    assert p.inercia == 0.7298
    assert p.coef_cognitivo == 1.49618
    assert p.coef_social == 1.49618
    assert p.fraccion_vmax == 0.2
    assert p.iteraciones is None


def test_base_yaml_contiene_el_bloque_pso_con_los_defaults_del_spec():
    cfg = load_config(RUTA_BASE)
    assert cfg["pso"] == CFG_PSO_SPEC
    assert isinstance(cfg["pso"]["N"], int) and not isinstance(cfg["pso"]["N"], bool)
    assert type(cfg["pso"]["w"]) is float
    p = ParametrosPSO.desde_config(cfg["pso"])
    assert p.tamano_enjambre == 30


def test_w_y_c_son_consistentes_con_el_coeficiente_de_constriccion_phi_4_1():
    # chi = 2 / |2 - phi - sqrt(phi^2 - 4 phi)|, w = chi, c = chi * phi / 2 (calculado aquí)
    phi = 4.1
    chi = 2.0 / abs(2.0 - phi - math.sqrt(phi ** 2 - 4.0 * phi))
    p = ParametrosPSO.desde_config(cfg_pso())
    assert p.inercia == pytest.approx(chi, abs=5e-5)
    assert p.coef_cognitivo == pytest.approx(chi * phi / 2.0, abs=5e-6)
    assert p.coef_social == pytest.approx(chi * phi / 2.0, abs=5e-6)


def test_parametros_es_una_dataclass_congelada():
    p = ParametrosPSO.desde_config(cfg_pso())
    assert dataclasses.is_dataclass(p)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.inercia = 0.5


def test_clave_faltante_falla_nombrandola():
    bloque = cfg_pso()
    del bloque["c2"]
    del bloque["vmax_frac"]
    with pytest.raises(ValueError) as info:
        ParametrosPSO.desde_config(bloque)
    mensaje = str(info.value)
    assert "c2" in mensaje and "vmax_frac" in mensaje
    assert "c1" not in mensaje  # solo las que faltan


def test_clave_desconocida_falla_nombrandola():
    with pytest.raises(ValueError, match="vmax"):
        ParametrosPSO.desde_config(cfg_pso(vmax=0.2))


def test_bloque_que_no_es_mapeo_lanza_typeerror():
    with pytest.raises(TypeError):
        ParametrosPSO.desde_config([30, 0.7298])


@pytest.mark.parametrize("clave", ["w", "c1", "c2"])
@pytest.mark.parametrize("valor", [True, False, "0.5", None, [0.5]])
def test_coeficientes_con_tipo_incorrecto_lanzan_typeerror(clave, valor):
    with pytest.raises(TypeError):
        ParametrosPSO.desde_config(cfg_pso(**{clave: valor}))


@pytest.mark.parametrize("clave", ["w", "c1", "c2"])
@pytest.mark.parametrize("valor", [float("nan"), float("inf"), -float("inf"), -0.1, -1])
def test_coeficientes_nan_inf_o_negativos_lanzan_valueerror(clave, valor):
    with pytest.raises(ValueError):
        ParametrosPSO.desde_config(cfg_pso(**{clave: valor}))


@pytest.mark.parametrize("clave", ["w", "c1", "c2"])
def test_coeficiente_cero_es_valido(clave):
    p = ParametrosPSO.desde_config(cfg_pso(**{clave: 0}))
    assert 0.0 in (p.inercia, p.coef_cognitivo, p.coef_social)


@pytest.mark.parametrize("valor", [1, 0, -5])
def test_n_menor_que_2_falla(valor):
    with pytest.raises(ValueError):
        ParametrosPSO.desde_config(cfg_pso(N=valor))


@pytest.mark.parametrize("valor", [True, 30.0, "30", None])
def test_n_con_tipo_incorrecto_lanza_typeerror(valor):
    with pytest.raises(TypeError):
        ParametrosPSO.desde_config(cfg_pso(N=valor))


def test_n_minimo_2_es_valido():
    assert ParametrosPSO.desde_config(cfg_pso(N=2)).tamano_enjambre == 2


@pytest.mark.parametrize("valor", [0.0, -0.2, float("nan"), float("inf")])
def test_vmax_frac_no_positivo_o_no_finito_falla(valor):
    with pytest.raises(ValueError):
        ParametrosPSO.desde_config(cfg_pso(vmax_frac=valor))


@pytest.mark.parametrize("valor", [True, "0.2", [0.2]])
def test_vmax_frac_con_tipo_incorrecto_lanza_typeerror(valor):
    with pytest.raises(TypeError):
        ParametrosPSO.desde_config(cfg_pso(vmax_frac=valor))


def test_vmax_frac_none_es_valido_y_significa_sin_limite():
    assert ParametrosPSO.desde_config(cfg_pso(vmax_frac=None)).fraccion_vmax is None


@pytest.mark.parametrize("valor", [True, False, 5.0, "5"])
def test_iteraciones_con_tipo_incorrecto_lanza_typeerror(valor):
    with pytest.raises(TypeError):
        ParametrosPSO.desde_config(cfg_pso(iteraciones=valor))


def test_iteraciones_negativas_fallan():
    with pytest.raises(ValueError):
        ParametrosPSO.desde_config(cfg_pso(iteraciones=-1))


@pytest.mark.parametrize("valor", [0, 7, np.int64(3)])
def test_iteraciones_enteras_validas(valor):
    p = ParametrosPSO.desde_config(cfg_pso(iteraciones=valor))
    assert p.iteraciones == int(valor) and type(p.iteraciones) is int


@pytest.mark.parametrize("w", [1.0, 1.2])
def test_w_mayor_o_igual_que_1_avisa_sin_rechazar(w):
    with pytest.warns(UserWarning, match="w"):
        p = ParametrosPSO.desde_config(cfg_pso(w=w))
    assert p.inercia == w


def test_el_aviso_de_w_apunta_al_llamador_de_desde_config():
    """El aviso debe señalar a quien llamó a `desde_config`, no al helper interno de pso.py."""
    with pytest.warns(UserWarning, match="w") as registro:
        ParametrosPSO.desde_config(cfg_pso(w=1.2))
    assert registro[0].filename == str(RUTA_PRUEBAS)


def test_el_default_w_no_emite_ningun_aviso():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ParametrosPSO.desde_config(cfg_pso())


def test_no_hay_umbral_sobre_c1_mas_c2():
    # Sin fuente verificada: c1 + c2 grande es aceptado.
    p = ParametrosPSO.desde_config(cfg_pso(c1=10.0, c2=10.0))
    assert p.coef_cognitivo == 10.0


# ================================================================================================
# 1. generar_enjambre_inicial
# ================================================================================================

@pytest.mark.parametrize("tamano,dim", [(30, 2), (30, 3), (7, 5)])
def test_enjambre_inicial_forma_dtype_y_rango(tamano, dim):
    limites = limites_cuadrados(dim, 2.048)
    enjambre = generar_enjambre_inicial(tamano, limites, np.random.default_rng(1))
    assert isinstance(enjambre, EnjambreInicial)
    assert enjambre.posiciones.shape == (tamano, dim)
    assert enjambre.velocidades.shape == (tamano, dim)
    assert enjambre.posiciones.dtype == np.float64
    assert np.all(enjambre.posiciones >= limites[:, 0])
    assert np.all(enjambre.posiciones <= limites[:, 1])


def test_enjambre_inicial_respeta_limites_distintos_por_dimension():
    limites = np.array([[-1.0, 3.0], [0.0, 10.0], [-5.0, -2.0]])
    enjambre = generar_enjambre_inicial(2000, limites, np.random.default_rng(2))
    x = enjambre.posiciones
    assert np.all(x >= limites[:, 0]) and np.all(x <= limites[:, 1])
    assert x[:, 0].max() > 2.5 and x[:, 0].min() < -0.5
    assert x[:, 1].max() > 9.0 and x[:, 1].min() < 1.0
    assert x[:, 2].max() < -2.0 + 1e-12 and x[:, 2].min() < -4.5


def test_enjambre_inicial_arranca_con_velocidad_cero():
    enjambre = generar_enjambre_inicial(30, limites_cuadrados(3, 5.12), np.random.default_rng(3))
    assert np.all(enjambre.velocidades == 0.0)


def test_enjambre_inicial_posiciones_y_velocidades_no_comparten_memoria():
    enjambre = generar_enjambre_inicial(5, limites_cuadrados(2, 5.12), np.random.default_rng(3))
    assert not np.shares_memory(enjambre.posiciones, enjambre.velocidades)


def test_enjambre_inicial_misma_semilla_igual_y_distinta_no():
    limites = limites_cuadrados(2, 5.12)
    a = generar_enjambre_inicial(30, limites, np.random.default_rng(3))
    b = generar_enjambre_inicial(30, limites, np.random.default_rng(3))
    c = generar_enjambre_inicial(30, limites, np.random.default_rng(4))
    assert np.array_equal(a.posiciones, b.posiciones)
    assert not np.array_equal(a.posiciones, c.posiciones)


class RngEspia:
    """Delega en un Generator real y cuenta cuántas veces se llama a cada método de azar."""

    def __init__(self, semilla: int):
        self._rng = np.random.default_rng(semilla)
        self.llamadas: list[str] = []

    def __getattr__(self, nombre):
        atributo = getattr(self._rng, nombre)
        if not callable(atributo):
            return atributo

        def envoltura(*args, **kwargs):
            self.llamadas.append(nombre)
            return atributo(*args, **kwargs)
        return envoltura


def test_enjambre_inicial_hace_una_sola_llamada_uniform_y_nada_mas():
    espia = RngEspia(5)
    generar_enjambre_inicial(30, limites_cuadrados(2, 5.12), espia)
    assert espia.llamadas == ["uniform"]


def test_enjambre_inicial_consume_el_rng_como_uniform_n_d():
    limites = np.array([[-2.0, 2.0], [-10.0, 30.0]])
    enjambre = generar_enjambre_inicial(10, limites, np.random.default_rng(8))
    esperado = np.random.default_rng(8).uniform(limites[:, 0], limites[:, 1], size=(10, 2))
    assert np.array_equal(enjambre.posiciones, esperado)


@pytest.mark.parametrize("tamano", [0, -3])
def test_enjambre_inicial_rechaza_tamano_invalido(tamano):
    with pytest.raises(ValueError):
        generar_enjambre_inicial(tamano, limites_cuadrados(2), np.random.default_rng(0))


# ================================================================================================
# 2. calcular_velocidad_maxima
# ================================================================================================

def test_velocidad_maxima_a_mano():
    # 0.2 * (2.048 - (-2.048)) = 0.8192 en cada dimensión
    vmax = calcular_velocidad_maxima(limites_cuadrados(2, 2.048), 0.2)
    assert vmax.shape == (2,)
    assert vmax == pytest.approx([0.8192, 0.8192])


def test_velocidad_maxima_por_dimension_con_limites_distintos():
    limites = np.array([[-2.0, 2.0], [-10.0, 30.0]])
    vmax = calcular_velocidad_maxima(limites, 0.2)
    assert vmax == pytest.approx([0.8, 8.0])


def test_velocidad_maxima_none_si_no_hay_fraccion():
    assert calcular_velocidad_maxima(limites_cuadrados(3, 5.12), None) is None


def test_velocidad_maxima_rechaza_limites_invalidos():
    with pytest.raises(ValueError):
        calcular_velocidad_maxima(np.array([[2.0, -2.0]]), 0.2)


# ================================================================================================
# 3. actualizar_memoria_personal
# ================================================================================================

def test_memoria_personal_cambia_solo_con_mejora_estricta():
    x = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    b = np.array([[9.0, 9.0], [8.0, 8.0], [7.0, 7.0]])
    f_x = np.array([1.0, 5.0, 4.0])
    f_b = np.array([2.0, 5.0, 3.0])        # mejora, EMPATE, empeora
    r = actualizar_memoria_personal(x, f_x, b, f_b)
    assert isinstance(r, ResultadoMemoria)
    assert r.mejoraron.tolist() == [True, False, False]
    assert r.mejores_personales.tolist() == [[1.0, 1.0], [8.0, 8.0], [7.0, 7.0]]
    assert r.aptitudes_personales.tolist() == [1.0, 5.0, 3.0]
    assert r.mejoraron.dtype == bool and r.mejoraron.shape == (3,)


def test_memoria_personal_no_modifica_entradas_ni_devuelve_alias():
    x = np.array([[1.0, 1.0], [2.0, 2.0]])
    b = np.array([[9.0, 9.0], [8.0, 8.0]])
    f_x = np.array([1.0, 9.0])
    f_b = np.array([2.0, 3.0])
    copias = [a.copy() for a in (x, b, f_x, f_b)]
    r = actualizar_memoria_personal(x, f_x, b, f_b)
    for original, copia in zip((x, b, f_x, f_b), copias, strict=True):
        assert np.array_equal(original, copia)
    for devuelto in (r.mejores_personales, r.aptitudes_personales):
        for entrada in (x, b, f_x, f_b):
            assert not np.shares_memory(devuelto, entrada)


def test_memoria_personal_sin_mejoras_devuelve_copias_iguales():
    b = np.array([[1.0, 1.0], [2.0, 2.0]])
    f_b = np.array([1.0, 2.0])
    r = actualizar_memoria_personal(b + 1.0, f_b + 5.0, b, f_b)
    assert not r.mejoraron.any()
    assert np.array_equal(r.mejores_personales, b)
    assert not np.shares_memory(r.mejores_personales, b)
    assert not np.shares_memory(r.aptitudes_personales, f_b)


def test_aptitud_personal_nunca_empeora_en_una_secuencia_aleatoria():
    rng = np.random.default_rng(11)
    b = rng.uniform(-3, 3, size=(20, 2))
    f_b = np.array([esfera(fila) for fila in b])
    for _ in range(50):
        x = rng.uniform(-3, 3, size=(20, 2))
        f_x = np.array([esfera(fila) for fila in x])
        r = actualizar_memoria_personal(x, f_x, b, f_b)
        assert np.all(r.aptitudes_personales <= f_b)
        # cada fila de b es el punto cuya aptitud se guarda
        assert np.allclose([esfera(fila) for fila in r.mejores_personales],
                           r.aptitudes_personales)
        b, f_b = r.mejores_personales, r.aptitudes_personales


def test_memoria_personal_rechaza_formas_incoherentes():
    with pytest.raises(ValueError):
        actualizar_memoria_personal(np.zeros((3, 2)), np.zeros(2), np.zeros((3, 2)), np.zeros(3))


# ================================================================================================
# 4. actualizar_mejor_global
# ================================================================================================

def test_mejor_global_es_el_argmin_de_las_memorias_personales():
    b = np.array([[1.0, 1.0], [0.5, 0.0], [3.0, 3.0]])
    f_b = np.array([2.0, 0.25, 18.0])
    g = actualizar_mejor_global(b, f_b)
    assert isinstance(g, MejorGlobal)
    assert g.indice == 1 and type(g.indice) is int
    assert g.aptitud == 0.25 and type(g.aptitud) is float
    assert g.posicion.tolist() == [0.5, 0.0]


def test_mejor_global_mira_las_memorias_y_no_las_posiciones_actuales():
    # La memoria de la partícula 0 es la mejor; una posición actual "mejor" no interviene:
    # actualizar_mejor_global solo recibe b y f(b).
    b = np.array([[0.0, 0.0], [5.0, 5.0]])
    f_b = np.array([0.0, 50.0])
    assert actualizar_mejor_global(b, f_b).indice == 0


def test_mejor_global_desempata_con_el_indice_menor():
    b = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
    f_b = np.array([3.0, 1.0, 1.0])
    g = actualizar_mejor_global(b, f_b)
    assert g.indice == 1
    assert g.posicion.tolist() == [0.0, 1.0]


def test_mejor_global_devuelve_copia():
    b = np.array([[1.0, 0.0], [0.0, 1.0]])
    f_b = np.array([1.0, 0.0])
    g = actualizar_mejor_global(b, f_b)
    g.posicion[:] = 99.0
    assert b.tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert not np.shares_memory(g.posicion, b)


def test_mejor_global_rechaza_formas_incoherentes():
    with pytest.raises(ValueError):
        actualizar_mejor_global(np.zeros((3, 2)), np.zeros(2))


# ================================================================================================
# 5. calcular_velocidades
# ================================================================================================

X0 = np.array([[4.0, 2.0], [-1.0, 2.0], [2.0, -3.0]])
V0 = np.array([[-1.0, 0.0], [1.0, -1.0], [0.0, 1.0]])
G0 = np.array([-1.0, 2.0])
LIMITES_AMPLIOS = limites_cuadrados(2, 100.0)


def test_ejemplo_a_mano_de_la_esfera_dos_iteraciones_con_los_componentes():
    """f = x^2 + y^2, w = 0.5, c1 = c2 = 1, R1 = R2 = 0.5 (calculado a mano en la solicitud)."""
    n, d = X0.shape
    f_x0 = np.array([esfera(fila) for fila in X0])
    assert f_x0.tolist() == [20.0, 5.0, 13.0]
    b0, f_b0 = X0.copy(), f_x0.copy()
    g0 = actualizar_mejor_global(b0, f_b0)
    assert g0.posicion.tolist() == [-1.0, 2.0]

    r = np.full((n, d), 0.5)
    v1 = calcular_velocidades(X0, V0, b0, g0.posicion, 0.5, 1.0, 1.0, r, r)
    assert v1.tolist() == [[-3.0, 0.0], [0.5, -0.5], [-1.5, 3.0]]

    v1_limitada = limitar_velocidades(v1, None)
    x1_tentativa = X0 + v1_limitada
    frontera = aplicar_frontera(x1_tentativa, v1_limitada, LIMITES_AMPLIOS)
    assert frontera.posiciones.tolist() == [[1.0, 2.0], [-0.5, 1.5], [0.5, 0.0]]
    assert not frontera.salieron.any()

    f_x1 = np.array([esfera(fila) for fila in frontera.posiciones])
    assert f_x1.tolist() == [5.0, 2.5, 0.25]
    memoria = actualizar_memoria_personal(frontera.posiciones, f_x1, b0, f_b0)
    assert memoria.mejoraron.tolist() == [True, True, True]
    g1 = actualizar_mejor_global(memoria.mejores_personales, memoria.aptitudes_personales)
    assert g1.posicion.tolist() == [0.5, 0.0]
    assert g1.aptitud == 0.25


def _oraculo_con_bucles(x, v, b, g, w, c1, c2, r1, r2):
    """v_ij <- w v_ij + c1 r1_ij (b_ij - x_ij) + c2 r2_ij (g_j - x_ij), con bucles explícitos."""
    n, d = x.shape
    nueva = np.empty((n, d))
    for i in range(n):
        for j in range(d):
            nueva[i, j] = (w * v[i, j] + c1 * r1[i, j] * (b[i, j] - x[i, j])
                           + c2 * r2[i, j] * (g[j] - x[i, j]))
    return nueva


def test_velocidades_reconstruidas_a_mano_con_r1_distinto_de_r2():
    x = np.array([[1.0, 2.0], [3.0, -1.0]])
    v = np.array([[0.5, -0.5], [1.0, 2.0]])
    b = np.array([[0.0, 1.0], [2.0, 2.0]])
    g = np.array([-1.0, 0.0])
    r1 = np.array([[0.25, 0.5], [0.75, 1.0]])
    r2 = np.array([[1.0, 0.0], [0.5, 0.25]])
    resultado = calcular_velocidades(x, v, b, g, 0.5, 2.0, 1.0, r1, r2)
    # partícula 0, dim 0: 0.5*0.5 + 2*0.25*(0-1) + 1*1*(-1-1) = 0.25 - 0.5 - 2 = -2.25
    # partícula 0, dim 1: 0.5*(-0.5) + 2*0.5*(1-2) + 0 = -0.25 - 1 = -1.25
    # partícula 1, dim 0: 0.5*1 + 2*0.75*(2-3) + 0.5*(-1-3) = 0.5 - 1.5 - 2 = -3.0
    # partícula 1, dim 1: 0.5*2 + 2*1*(2+1) + 0.25*(0+1) = 1 + 6 + 0.25 = 7.25
    assert resultado.tolist() == [[-2.25, -1.25], [-3.0, 7.25]]


@pytest.mark.parametrize("semilla,n,d", [(1, 30, 2), (2, 30, 3), (3, 5, 4)])
def test_velocidades_igualan_al_oraculo_con_bucles(semilla, n, d):
    rng = np.random.default_rng(semilla)
    x, v, b = (rng.uniform(-5, 5, size=(n, d)) for _ in range(3))
    g = rng.uniform(-5, 5, size=d)
    r1, r2 = rng.random((n, d)), rng.random((n, d))
    obtenido = calcular_velocidades(x, v, b, g, 0.7298, 1.49618, 1.49618, r1, r2)
    esperado = _oraculo_con_bucles(x, v, b, g, 0.7298, 1.49618, 1.49618, r1, r2)
    assert obtenido.shape == (n, d)
    assert np.allclose(obtenido, esperado, rtol=1e-12, atol=1e-12)


def test_velocidades_w_cero_anula_la_inercia():
    rng = np.random.default_rng(4)
    x, v, b = (rng.uniform(-5, 5, size=(6, 2)) for _ in range(3))
    g, r1, r2 = rng.uniform(-5, 5, size=2), rng.random((6, 2)), rng.random((6, 2))
    sin_inercia = calcular_velocidades(x, v, b, g, 0.0, 1.0, 1.0, r1, r2)
    con_v_cero = calcular_velocidades(x, np.zeros_like(v), b, g, 0.9, 1.0, 1.0, r1, r2)
    assert np.allclose(sin_inercia, con_v_cero)


def test_velocidades_c1_cero_anula_el_termino_cognitivo():
    rng = np.random.default_rng(5)
    x, v, b = (rng.uniform(-5, 5, size=(6, 2)) for _ in range(3))
    g, r1, r2 = rng.uniform(-5, 5, size=2), rng.random((6, 2)), rng.random((6, 2))
    sin_cognitivo = calcular_velocidades(x, v, b, g, 0.5, 0.0, 1.0, r1, r2)
    otro_b = calcular_velocidades(x, v, b + 100.0, g, 0.5, 0.0, 1.0, r1, r2)
    assert np.allclose(sin_cognitivo, 0.5 * v + 1.0 * r2 * (g - x))
    assert np.allclose(sin_cognitivo, otro_b)


def test_velocidades_c2_cero_anula_el_termino_social():
    rng = np.random.default_rng(6)
    x, v, b = (rng.uniform(-5, 5, size=(6, 2)) for _ in range(3))
    g, r1, r2 = rng.uniform(-5, 5, size=2), rng.random((6, 2)), rng.random((6, 2))
    sin_social = calcular_velocidades(x, v, b, g, 0.5, 1.0, 0.0, r1, r2)
    otro_g = calcular_velocidades(x, v, b, g + 100.0, 0.5, 1.0, 0.0, r1, r2)
    assert np.allclose(sin_social, 0.5 * v + 1.0 * r1 * (b - x))
    assert np.allclose(sin_social, otro_g)


def test_la_particula_que_es_g_y_esta_en_su_memoria_solo_se_mueve_por_inercia():
    rng = np.random.default_rng(7)
    x = rng.uniform(-5, 5, size=(5, 2))
    v = rng.uniform(-1, 1, size=(5, 2))
    b = rng.uniform(-5, 5, size=(5, 2))
    b[2] = x[2]                      # la partícula 2 está en su mejor personal...
    g = x[2].copy()                  # ... y es el mejor global
    r1, r2 = rng.random((5, 2)), rng.random((5, 2))
    # con ambos términos de atracción en cero, su velocidad es w·v
    nueva = calcular_velocidades(x, v, b, g, 0.7298, 1.49618, 1.49618, r1, r2)
    assert np.allclose(nueva[2], 0.7298 * v[2])


def test_velocidades_no_modifica_entradas_y_devuelve_arreglo_nuevo():
    rng = np.random.default_rng(8)
    x, v, b = (rng.uniform(-5, 5, size=(4, 3)) for _ in range(3))
    g, r1, r2 = rng.uniform(-5, 5, size=3), rng.random((4, 3)), rng.random((4, 3))
    entradas = [x, v, b, g, r1, r2]
    copias = [a.copy() for a in entradas]
    resultado = calcular_velocidades(x, v, b, g, 0.7, 1.4, 1.4, r1, r2)
    for original, copia in zip(entradas, copias, strict=True):
        assert np.array_equal(original, copia)
        assert not np.shares_memory(resultado, original)


def test_velocidades_no_limita_ni_recorta():
    x = np.array([[100.0, 100.0]])
    resultado = calcular_velocidades(x, np.zeros((1, 2)), x, np.array([-100.0, -100.0]),
                                     0.0, 0.0, 1.0, np.ones((1, 2)), np.ones((1, 2)))
    assert resultado.tolist() == [[-200.0, -200.0]]


def test_velocidades_rechaza_formas_incoherentes():
    x = np.zeros((3, 2))
    with pytest.raises(ValueError):                      # mejor_global de largo distinto de d
        calcular_velocidades(x, x, x, np.zeros(3), 0.5, 1.0, 1.0, x, x)
    with pytest.raises(ValueError):                      # aleatorios de otra forma
        calcular_velocidades(x, x, x, np.zeros(2), 0.5, 1.0, 1.0, np.zeros((2, 2)), x)


# ================================================================================================
# 6. limitar_velocidades
# ================================================================================================

@pytest.mark.parametrize("semilla", [0, 1, 2, 3, 4])
def test_limitar_respeta_mas_menos_vmax_con_entradas_grandes(semilla):
    rng = np.random.default_rng(semilla)
    v = rng.uniform(-1000, 1000, size=(30, 3))
    vmax = np.array([0.5, 2.0, 8.0])
    limitada = limitar_velocidades(v, vmax)
    assert limitada.shape == (30, 3)
    assert np.all(np.abs(limitada) <= vmax)
    # lo que ya estaba dentro no cambia; lo que excedía queda en ±vmax conservando signo
    dentro = np.abs(v) <= vmax
    assert np.array_equal(limitada[dentro], v[dentro])
    assert np.array_equal(limitada[~dentro], (np.sign(v) * vmax)[~dentro])


def test_limitar_a_mano():
    v = np.array([[3.0, -9.0], [0.1, 0.2]])
    assert limitar_velocidades(v, np.array([1.0, 4.0])).tolist() == [[1.0, -4.0], [0.1, 0.2]]


def test_limitar_none_devuelve_copia_sin_cambio():
    v = np.array([[300.0, -900.0], [0.1, 0.2]])
    resultado = limitar_velocidades(v, None)
    assert np.array_equal(resultado, v)
    assert not np.shares_memory(resultado, v)


def test_limitar_no_modifica_la_entrada():
    v = np.array([[300.0, -900.0]])
    copia = v.copy()
    limitar_velocidades(v, np.array([1.0, 1.0]))
    assert np.array_equal(v, copia)


def test_limitar_es_por_dimension():
    v = np.full((4, 2), 10.0)
    resultado = limitar_velocidades(v, np.array([1.0, 5.0]))
    assert resultado[:, 0].tolist() == [1.0] * 4
    assert resultado[:, 1].tolist() == [5.0] * 4


def test_limitar_rechaza_vmax_de_largo_incoherente():
    with pytest.raises(ValueError):
        limitar_velocidades(np.zeros((3, 2)), np.array([1.0, 1.0, 1.0]))


# ================================================================================================
# 7. aplicar_frontera
# ================================================================================================

LIMITES_FRONTERA = np.array([[-2.0, 2.0], [-5.0, 5.0]])


def test_frontera_recorta_y_pone_v_cero_solo_en_la_componente_que_salio():
    tentativas = np.array([[3.0, 0.5], [0.0, -9.0], [1.0, 1.0]])
    v = np.array([[1.0, 1.0], [2.0, -2.0], [0.5, 0.5]])
    r = aplicar_frontera(tentativas, v, LIMITES_FRONTERA)
    assert isinstance(r, ResultadoFrontera)
    assert r.posiciones.tolist() == [[2.0, 0.5], [0.0, -5.0], [1.0, 1.0]]
    assert r.velocidades.tolist() == [[0.0, 1.0], [2.0, 0.0], [0.5, 0.5]]
    assert r.salieron.tolist() == [[True, False], [False, True], [False, False]]
    assert r.salieron.dtype == bool


def test_frontera_ambas_componentes_fuera_ponen_ambas_velocidades_en_cero():
    r = aplicar_frontera(np.array([[-3.0, 6.0]]), np.array([[-1.0, 2.0]]), LIMITES_FRONTERA)
    assert r.posiciones.tolist() == [[-2.0, 5.0]]
    assert r.velocidades.tolist() == [[0.0, 0.0]]


def test_frontera_dentro_del_dominio_no_cambia_nada():
    tentativas = np.array([[2.0, -5.0], [-2.0, 5.0], [0.0, 0.0]])   # incluye el borde exacto
    v = np.array([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    r = aplicar_frontera(tentativas, v, LIMITES_FRONTERA)
    assert np.array_equal(r.posiciones, tentativas)
    assert np.array_equal(r.velocidades, v)
    assert not r.salieron.any()


def test_frontera_no_modifica_las_entradas_ni_devuelve_alias():
    tentativas = np.array([[3.0, 0.5]])
    v = np.array([[1.0, 1.0]])
    t_copia, v_copia = tentativas.copy(), v.copy()
    r = aplicar_frontera(tentativas, v, LIMITES_FRONTERA)
    assert np.array_equal(tentativas, t_copia) and np.array_equal(v, v_copia)
    assert not np.shares_memory(r.posiciones, tentativas)
    assert not np.shares_memory(r.velocidades, v)


def test_frontera_con_enjambre_aleatorio_deja_todo_dentro_del_dominio():
    rng = np.random.default_rng(21)
    tentativas = rng.uniform(-20, 20, size=(200, 2))
    v = rng.uniform(-3, 3, size=(200, 2))
    r = aplicar_frontera(tentativas, v, LIMITES_FRONTERA)
    assert np.all(r.posiciones >= LIMITES_FRONTERA[:, 0])
    assert np.all(r.posiciones <= LIMITES_FRONTERA[:, 1])
    assert np.all(r.velocidades[r.salieron] == 0.0)
    assert np.array_equal(r.velocidades[~r.salieron], v[~r.salieron])


def test_frontera_rechaza_limites_con_otra_dimension():
    with pytest.raises(ValueError):
        aplicar_frontera(np.zeros((2, 3)), np.zeros((2, 3)), LIMITES_FRONTERA)


# ================================================================================================
# 8. optimize
# ================================================================================================

CASOS_DOMINIO = [
    pytest.param(nombre, dim, limite, id=f"{nombre}_{dim}d")
    for nombre, limite in (("rosenbrock", 2.048), ("rastrigin", 5.12))
    for dim in (2, 3)
]


@pytest.mark.parametrize("nombre,dim,limite", CASOS_DOMINIO)
def test_ningun_punto_evaluado_sale_del_dominio(nombre, dim, limite):
    for semilla in range(5):
        func = FuncionRegistradora(get_function(nombre, dim))
        problema, r = _correr(func, 3_000.0, semilla=semilla)
        puntos = np.array(func.puntos_evaluados)
        assert puntos.shape == (r["n_f"], dim)        # cada evaluación contada llegó a f
        assert np.all(np.abs(puntos) <= limite)
        assert np.all(np.abs(r["x_best"]) <= limite)


@pytest.mark.parametrize("nombre,dim,limite", CASOS_DOMINIO)
def test_history_es_monotono_y_f_de_g_nunca_crece(nombre, dim, limite):
    func = FuncionRegistradora(get_function(nombre, dim))
    problema, r = _correr(func, 3_000.0, semilla=2)
    f_hist = [p["f_best"] for p in r["history"]]
    eq_hist = [p["eval_equiv"] for p in r["history"]]
    assert all(b < a for a, b in zip(f_hist, f_hist[1:]))
    assert all(b > a for a, b in zip(eq_hist, eq_hist[1:]))
    assert r["f_best"] == f_hist[-1]
    if dim == 2:
        # Se comprueba el frame t: f(best) (con la función SIN registradora, para no contaminar
        # func.valores) = mínimo de todo lo evaluado hasta completar el enjambre t (g al día).
        sin_registro = get_function(nombre, dim)
        n = cfg_pso()["N"]
        valores = np.array(func.valores)
        assert len(r["frames"]) > 10
        for t, frame in enumerate(r["frames"]):
            esperado = valores[:n * (t + 1)].min()
            assert sin_registro.f(np.array(frame["best"])) == esperado


def test_conteo_exacto_con_iteraciones_fijas():
    func = get_function("rastrigin", 2)
    problema, r = _correr(func, 1e6, iteraciones=10)
    assert r["n_f"] == 30 * (10 + 1) == 330
    assert r["n_grad"] == 0
    assert r["eval_equiv"] == 330.0
    assert len(r["frames"]) == 11
    assert [f["iter"] for f in r["frames"]] == list(range(11))


def test_iteraciones_cero_solo_evalua_el_enjambre_inicial():
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 1e6, iteraciones=0)
    assert r["n_f"] == 30
    assert len(r["frames"]) == 1 and r["frames"][0]["iter"] == 0


def test_conteo_con_n_distinto_y_3d():
    func = get_function("rastrigin", 3)
    _, r = _correr(func, 1e6, N=12, iteraciones=7)
    assert r["n_f"] == 12 * 8
    assert "frames" not in r


def test_truncado_en_2d_con_presupuesto_20000():
    func = get_function("rastrigin", 2)
    problema, r = _correr(func, 20_000.0)
    assert r["n_f"] == 20_000                      # 30*666 = 19980 + 20 de la iteración truncada
    assert r["n_grad"] == 0 and r["eval_equiv"] == 20_000.0
    assert len(r["frames"]) == 666
    assert r["frames"][-1]["iter"] == 665


def test_truncado_en_3d_con_presupuesto_30000_es_exacto_y_sin_frames():
    func = get_function("rosenbrock", 3)
    _, r = _correr(func, 30_000.0)
    assert r["n_f"] == 30_000                      # 30 * 1000 exactos
    assert "frames" not in r


def test_presupuesto_menor_que_el_enjambre_devuelve_el_mejor_visto_sin_frames():
    func = FuncionRegistradora(get_function("rastrigin", 2))
    problema, r = _correr(func, 10.0)
    assert r["n_f"] == 10
    assert r.get("frames", []) == []
    assert r["f_best"] == min(func.valores)
    assert r["x_best"] == func.puntos_evaluados[int(np.argmin(func.valores))].tolist()


def test_presupuesto_que_no_alcanza_para_una_evaluacion_falla():
    func = get_function("rastrigin", 2)
    with pytest.raises(ValueError, match="presupuesto"):
        optimize(nuevo_problema(func, 0.5), cfg_completo(), make_rng(0, 0))
    with pytest.raises(ValueError):                 # CountedProblem ya rechaza presupuesto 0
        optimize(nuevo_problema(func, 0.0), cfg_completo(), make_rng(0, 0))


def test_misma_semilla_mismo_resultado_y_semilla_distinta_no():
    func = get_function("rastrigin", 2)
    _, a = _correr(func, 3_000.0, semilla=5)
    _, b = _correr(func, 3_000.0, semilla=5)
    _, c = _correr(func, 3_000.0, semilla=6)
    assert a == b
    assert a["x_best"] != c["x_best"] or a["history"] != c["history"]


def _oraculo_pso(func, semilla, iteraciones, vmax_frac, n=30):
    """Reimplementa con bucles el PSO completo y devuelve (posiciones de los frames 0..T, recortes).

    Es el oráculo independiente de `optimize`: consume el rng en el orden del Spec (uniform de
    las posiciones; luego R1 y R2 en cada iteración, antes de mover), recorta con
    np.clip(v, -vmax, vmax) si `vmax_frac` no es None y arrastra la velocidad RECORTADA (0 en
    las componentes que salieron del dominio). `recortes[t]` cuenta las componentes que el
    recorte de v_max toca en la iteración t + 1 (siempre 0 si `vmax_frac` es None).
    """
    w, c1, c2 = CFG_PSO_SPEC["w"], CFG_PSO_SPEC["c1"], CFG_PSO_SPEC["c2"]
    d = func.dim
    lo, hi = func.bounds[:, 0], func.bounds[:, 1]
    vmax = None if vmax_frac is None else vmax_frac * (hi - lo)
    rng = np.random.default_rng(semilla)
    x = rng.uniform(lo, hi, size=(n, d))                    # (1) posiciones iniciales
    v = np.zeros((n, d))
    b = x.copy()
    f_b = np.array([func.f(fila) for fila in x])
    posiciones, recortes = [x], []
    for _ in range(iteraciones):
        g = b[int(np.argmin(f_b))]
        r1, r2 = rng.random((n, d)), rng.random((n, d))     # (2) R1 y luego (3) R2
        v = _oraculo_con_bucles(x, v, b, g, w, c1, c2, r1, r2)
        if vmax is None:
            recortes.append(0)
        else:
            recortes.append(int(np.sum(np.abs(v) > vmax)))  # componentes que el recorte toca
            v = np.clip(v, -vmax, vmax)
        x_tent = x + v
        salieron = (x_tent < lo) | (x_tent > hi)
        x = np.clip(x_tent, lo, hi)
        v = np.where(salieron, 0.0, v)                      # arrastra la velocidad RECORTADA
        f_x = np.array([func.f(fila) for fila in x])
        mejora = f_x < f_b
        b = np.where(mejora[:, None], x, b)
        f_b = np.where(mejora, f_x, f_b)
        posiciones.append(x)
    return posiciones, recortes


def test_orden_del_rng_uniform_luego_r1_y_r2_por_iteracion():
    """Frames 0 y 1 de `optimize` = oráculo que sortea uniform, luego R1 y R2 (con v_max)."""
    func = get_function("rosenbrock", 2)
    semilla = 17
    _, r = _correr(func, 1e6, semilla=semilla, iteraciones=2)
    posiciones, _ = _oraculo_pso(func, semilla, 2, CFG_PSO_SPEC["vmax_frac"])
    assert np.array_equal(np.array(r["frames"][0]["positions"]), posiciones[0])
    assert np.array_equal(np.array(r["frames"][1]["positions"]), posiciones[1])


def test_segunda_iteracion_usa_velocidad_cero_en_componentes_que_salieron():
    """Sin v_max y con el dominio ajustado, una componente que sale reinicia su velocidad."""
    func = get_function("rastrigin", 2)
    semilla, iteraciones = 3, 3
    _, r = _correr(func, 1e6, semilla=semilla, iteraciones=iteraciones, vmax_frac=None)
    posiciones, recortes = _oraculo_pso(func, semilla, iteraciones, None)
    assert recortes == [0] * iteraciones                    # sin v_max el recorte no existe
    for t, esperado in enumerate(posiciones):
        assert np.array_equal(np.array(r["frames"][t]["positions"]), esperado)


# vmax_frac = 0.05 (menor que el default 0.2): con el default el recorte casi no actúa tras la
# 1.ª iteración y el escenario no distinguiría arrastrar la velocidad recortada o la sin recortar.
@pytest.mark.parametrize("nombre,semilla", [("rosenbrock", 4), ("rastrigin", 11)])
@pytest.mark.parametrize("vmax_frac", [0.05, 0.2])
def test_vmax_activo_varias_iteraciones_arrastra_la_velocidad_recortada(nombre, semilla,
                                                                       vmax_frac):
    func = get_function(nombre, 2)
    iteraciones = 6
    _, r = _correr(func, 1e6, semilla=semilla, iteraciones=iteraciones, vmax_frac=vmax_frac)
    posiciones, recortes = _oraculo_pso(func, semilla, iteraciones, vmax_frac)
    assert len(r["frames"]) == iteraciones + 1
    # el recorte debe actuar en alguna iteración >= 2 (índice >= 1), si no la prueba no vale
    assert sum(recortes[1:]) > 0
    for t, esperado in enumerate(posiciones):
        assert np.array_equal(np.array(r["frames"][t]["positions"]), esperado)


def test_frames_forma_best_es_g_y_copias_sin_alias():
    func = FuncionRegistradora(get_function("rastrigin", 2))
    problema, r = _correr(func, 3_000.0, semilla=1)
    frames = r["frames"]
    assert len(frames) > 50
    valores = np.array(func.valores)
    for t, frame in enumerate(frames):
        assert set(frame) == {"iter", "positions", "best"}
        assert frame["iter"] == t
        posiciones = np.array(frame["positions"])
        assert posiciones.shape == (30, 2)
        assert len(frame["best"]) == 2
        # best = mejor GLOBAL: su f es el mínimo de todo lo evaluado hasta completar el enjambre t
        minimo = valores[:30 * (t + 1)].min()
        assert func.f(np.array(frame["best"])) == minimo
    ids = {id(frame["positions"]) for frame in frames}
    assert len(ids) == len(frames)
    frames[0]["positions"][0][0] = 1e9               # modificar un frame no altera otro
    assert frames[1]["positions"][0][0] != 1e9


def test_best_del_frame_es_el_mejor_global_hasta_ese_frame_y_no_empeora():
    func = get_function("rosenbrock", 2)
    _, r = _correr(func, 6_000.0, semilla=9)
    f_best = [func.f(np.array(f["best"])) for f in r["frames"]]
    assert all(b <= a for a, b in zip(f_best, f_best[1:]))
    assert f_best[-1] == r["f_best"]


@pytest.mark.parametrize("nombre,limite", [("rosenbrock", 2.048), ("rastrigin", 5.12)])
def test_ningun_frame_sale_del_dominio(nombre, limite):
    func = get_function(nombre, 2)
    _, r = _correr(func, 6_000.0)
    for frame in r["frames"]:
        assert np.all(np.abs(np.array(frame["positions"])) <= limite)
        assert np.all(np.abs(frame["best"]) <= limite)


def test_sin_frames_con_record_frames_falso_o_en_3d():
    f2 = get_function("rastrigin", 2)
    f3 = get_function("rastrigin", 3)
    _, r2_sin = _correr(f2, 1_000.0, record_frames=False)
    _, r3_con = _correr(f3, 1_000.0, record_frames=True)
    _, r2_con = _correr(f2, 1_000.0, record_frames=True)
    assert "frames" not in r2_sin
    assert "frames" not in r3_con
    assert "frames" in r2_con


def test_retorno_contrato_5_1_claves_y_tipos_nativos():
    func = get_function("rastrigin", 2)
    problema, r = _correr(func, 2_000.0)
    assert set(r) == {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history", "frames"}
    assert type(r["x_best"]) is list and all(type(v) is float for v in r["x_best"])
    assert type(r["f_best"]) is float
    assert type(r["n_f"]) is int and type(r["n_grad"]) is int and r["n_grad"] == 0
    assert type(r["eval_equiv"]) is float
    assert type(r["history"]) is list
    json.dumps(r)                                    # serializable sin conversiones
    r["history"].append({"basura": 1})               # history es copia
    assert len(problema.history) == len(r["history"]) - 1
    assert r["x_best"] == problema.best_x.tolist()


def test_optimize_no_cuenta_a_mano_sale_de_problem():
    func = FuncionRegistradora(get_function("rosenbrock", 3))
    problema, r = _correr(func, 2_500.0)
    assert r["n_f"] == problema.n_f == len(func.puntos_evaluados)
    assert r["eval_equiv"] == problema.eval_equiv()


def test_optimize_converge_en_rosenbrock_2d_con_base_yaml():
    cfg = load_config(RUTA_BASE)
    func = get_function("rosenbrock", 2)
    problema = CountedProblem(func, k=2 * func.dim, budget=10_000 * func.dim)
    r = optimize(problema, cfg, make_rng(0, 0))
    assert r["n_f"] == 20_000
    assert len(r["frames"]) == 666
    assert r["f_best"] < 1.0


def test_humo_con_base_yaml_en_las_cuatro_combinaciones():
    cfg = load_config(RUTA_BASE)
    # func y dim son listas en la base: se construye el problema aparte y solo se pasa `pso`
    cfg_optimizador = {"pso": cfg["pso"], "record_frames": cfg["record_frames"]}
    for nombre in cfg["func"]:
        for dim in cfg["dim"]:
            func = get_function(nombre, dim)
            problema = CountedProblem(func, k=2 * dim, budget=10_000 * dim)
            r = optimize(problema, cfg_optimizador, make_rng(cfg["base_seed"], 0))
            assert r["n_f"] == 10_000 * dim
            assert r["n_grad"] == 0
            assert ("frames" in r) == (dim == 2)
            assert r["f_best"] >= func.f_star


def test_overrides_de_la_config_llegan_al_algoritmo():
    cfg = load_config(RUTA_BASE)
    func = get_function("rastrigin", 2)
    cfg_n12 = apply_overrides(cfg, ["pso.N=12", "pso.iteraciones=4"])
    r = optimize(nuevo_problema(func, 1e6), cfg_n12, make_rng(0, 0))
    assert r["n_f"] == 12 * 5
    assert len(r["frames"][0]["positions"]) == 12


def test_optimize_sin_bloque_pso_o_sin_record_frames_falla_con_mensaje_claro():
    func = get_function("rastrigin", 2)
    with pytest.raises(ValueError, match="pso"):
        optimize(nuevo_problema(func, 1000.0), {"record_frames": True}, make_rng(0, 0))
    with pytest.raises(ValueError, match="record_frames"):
        optimize(nuevo_problema(func, 1000.0), {"pso": cfg_pso()}, make_rng(0, 0))
    with pytest.raises(TypeError):
        optimize(nuevo_problema(func, 1000.0), {"pso": cfg_pso(), "record_frames": "si"},
                 make_rng(0, 0))
    bloque = cfg_pso(N=1)
    with pytest.raises(ValueError):
        optimize(nuevo_problema(func, 1000.0), {"pso": bloque, "record_frames": True},
                 make_rng(0, 0))


def test_optimize_sin_limite_de_velocidad_tambien_respeta_el_dominio():
    func = FuncionRegistradora(get_function("rastrigin", 3))
    _correr(func, 3_000.0, vmax_frac=None)
    assert np.all(np.abs(np.array(func.puntos_evaluados)) <= 5.12)


def test_no_usa_azar_global_ni_modifica_su_estado():
    estado_numpy = np.random.get_state()
    estado_random = random.getstate()
    _correr(get_function("rastrigin", 2), 2_000.0)
    assert np.random.get_state()[1].tolist() == estado_numpy[1].tolist()
    assert np.random.get_state()[2:] == estado_numpy[2:]
    assert random.getstate() == estado_random


@pytest.mark.parametrize("ruta", [RUTA_PSO, RUTA_PRUEBAS], ids=["pso.py", "test_pso.py"])
def test_lineas_de_hasta_100_caracteres(ruta):
    texto = ruta.read_text(encoding="utf-8")
    largas = [i + 1 for i, linea in enumerate(texto.splitlines()) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    """Error B1 de T1.4: ningún def/class/import/from fuera de una celda `# %%` de código."""
    celda_actual = None
    for numero, linea in enumerate(RUTA_PSO.read_text(encoding="utf-8").splitlines(), start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_con_tabla_de_componentes_y_latex():
    texto = RUTA_PSO.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    for nombre in ("ParametrosPSO", "generar_enjambre_inicial", "calcular_velocidad_maxima",
                   "actualizar_memoria_personal", "actualizar_mejor_global",
                   "calcular_velocidades", "limitar_velocidades", "aplicar_frontera",
                   "optimize"):
        assert f"`{nombre}`" in texto.split("# %%\n")[0]
    assert "v_{\\max}" in texto
    # Prueba ESTÁTICA a propósito: el requisito de documentación del autor es que la ecuación
    # de velocidad se lea en LaTeX (con \odot) en la celda markdown justo antes del código.
    celdas = re.split(r"(?m)^# %%.*\n", texto)
    indice_codigo = next(i for i, celda in enumerate(celdas)
                         if "def calcular_velocidades(" in celda)
    assert "\\odot" in celdas[indice_codigo - 1]


# ================================================================================================
# 9. Casos límite pedagógicos (preguntas típicas de la sustentación)
# ================================================================================================

def test_vmax_tendiendo_a_cero_congela_el_enjambre():
    """Sustentación: "¿qué pasa si v_max -> 0?". Las partículas dejan de moverse.

    Con v_max = 1e-12 * anchura cada paso mide ~1e-11 como máximo: el enjambre se queda en su
    posición inicial (no explora) aunque siga gastando presupuesto, N * (T + 1) evaluaciones.
    """
    vmax_frac, iteraciones, n = 1e-12, 5, 30
    func = get_function("rastrigin", 2)
    _, r = _correr(func, 1e6, iteraciones=iteraciones, vmax_frac=vmax_frac)
    assert len(r["frames"]) == iteraciones + 1
    inicial = np.array(r["frames"][0]["positions"])
    for frame in r["frames"]:
        assert np.allclose(np.array(frame["positions"]), inicial, rtol=0.0, atol=1e-9)
    assert r["n_f"] == n * (iteraciones + 1)

    # A nivel de componente: aunque la ecuación de velocidad dé valores enormes, sale ~0.
    vmax = calcular_velocidad_maxima(func.bounds, vmax_frac)
    grandes = np.full((n, 2), 1e6)
    assert np.allclose(limitar_velocidades(grandes, vmax), 0.0, rtol=0.0, atol=1e-10)


def test_enjambre_de_dos_con_presupuesto_dos_solo_evalua_el_enjambre_inicial():
    """Sustentación: "¿y si el presupuesto solo alcanza para el enjambre inicial?".

    N = 2 y presupuesto 2: se evalúa el enjambre inicial, la iteración 1 se trunca en su primera
    evaluación (BudgetExhausted, capturada) y queda un único frame (iter 0), sin excepción.
    """
    func = FuncionRegistradora(get_function("rastrigin", 2))
    _, r = _correr(func, 2.0, N=2)
    assert r["n_f"] == 2
    assert [frame["iter"] for frame in r["frames"]] == [0]
    assert r["f_best"] == min(func.valores)
    assert len(func.valores) == 2
