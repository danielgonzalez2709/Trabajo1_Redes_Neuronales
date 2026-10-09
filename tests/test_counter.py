"""Pruebas de conteo de CountedProblem (T0.4; Spec §5.1 y §6.2).

Usa la cuadrática compartida de conftest.py: f(x) = ||x - x_star||², con x_star explícito en cada
prueba (no depende de functions.py, que llega en T1.1).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.common.counter import CountedProblem

UNOS2 = [1.0, 1.0]  # x_star de las pruebas en 2D: f([3, 1]) = 4, f([1, 2]) = 1, f([2, 1]) = 1


# ---------------------------------------------------------------- conteos básicos

def test_estado_inicial(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=100)
    assert p.n_f == 0 and p.n_grad == 0
    assert p.best_x is None
    assert p.best_f == math.inf
    assert p.history == []
    assert p.eval_equiv() == 0
    assert isinstance(p.eval_equiv(), float)


def test_conteo_f_y_grad_por_separado(cuadratica):
    func = cuadratica(np.ones(3))
    p = CountedProblem(func, k=6, budget=1000)
    for _ in range(5):
        p.f(np.zeros(3))
    for _ in range(3):
        p.grad(np.zeros(3))
    assert p.n_f == 5
    assert p.n_grad == 3
    assert func.llamadas_f == 5 and func.llamadas_grad == 3


def test_f_y_grad_devuelven_valores_de_la_funcion(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=100)
    x = np.array([3.0, -1.0])
    valor = p.f(x)
    assert isinstance(valor, float)
    assert valor == pytest.approx(4.0 + 4.0)
    np.testing.assert_allclose(p.grad(x), [4.0, -4.0])


@pytest.mark.parametrize("dim", [2, 3])
def test_eval_equiv_con_k_2n_y_k_1(cuadratica, dim):
    k = 2 * dim
    p = CountedProblem(cuadratica(np.ones(dim)), k=k, budget=10_000 * dim)
    for _ in range(7):
        p.f(np.zeros(dim))
    for _ in range(4):
        p.grad(np.zeros(dim))
    assert p.eval_equiv() == 7 + k * 4          # k por defecto = el del constructor (2n)
    assert p.eval_equiv(k=1) == 7 + 4            # sensibilidad k = 1 (§6.2)
    assert isinstance(p.eval_equiv(k=1), float)
    assert p.eval_equiv() == 7 + k * 4          # eval_equiv(k) no altera el k del constructor


def test_bucle_poblacional_cuenta_N_por_T_mas_1(cuadratica, bucle_poblacional):
    """Población inicial + T generaciones de N individuos → exactamente N·(T+1) evaluaciones de f
    (§6.2), con presupuesto suficiente (10 000·n)."""
    N, T, dim = 30, 50, 2
    p = CountedProblem(cuadratica(np.zeros(dim)), k=2 * dim, budget=10_000 * dim)
    bucle_poblacional(p, N, T, np.random.default_rng(0))
    assert p.n_f == N * (T + 1)
    assert p.n_grad == 0
    assert p.eval_equiv() == N * (T + 1)
    assert not p.budget_exhausted()


# ---------------------------------------------------------------- best / history / observe

def test_best_se_actualiza_con_f(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=100)
    p.f(np.array([3.0, 1.0]))   # 4
    p.f(np.array([1.0, 2.0]))   # 1
    p.f(np.array([4.0, 4.0]))   # 18 (peor)
    assert p.best_f == pytest.approx(1.0)
    np.testing.assert_allclose(p.best_x, [1.0, 2.0])


def test_history_solo_crece_al_mejorar_estrictamente(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=100)
    p.f(np.array([3.0, 1.0]))     # 4 → mejora (eval_equiv 1)
    p.f(np.array([3.0, 1.0]))     # 4 → igual, no mejora
    p.f(np.array([5.0, 5.0]))     # 32 → peor
    p.grad(np.array([0.0, 0.0]))  # gradiente: no evalúa f ni toca history (eval_equiv pasa a 7)
    p.f(np.array([1.0, 2.0]))     # 1 → mejora (eval_equiv 8)
    assert p.history == [
        {"eval_equiv": 1.0, "f_best": 4.0},
        {"eval_equiv": 8.0, "f_best": 1.0},
    ]
    for registro in p.history:
        assert isinstance(registro["eval_equiv"], float)
        assert isinstance(registro["f_best"], float)


def test_f_nan_se_cuenta_pero_nunca_es_best(cuadratica):
    func = cuadratica(UNOS2)
    p = CountedProblem(func, k=4, budget=100)
    nan_x = np.array([np.nan, 0.0])
    valor = p.f(nan_x)                         # sin best previo (best_f = inf)
    assert math.isnan(valor)
    assert p.n_f == 1
    assert p.best_x is None and p.best_f == math.inf and p.history == []
    p.f(np.array([3.0, 1.0]))                  # 4 → primer best
    p.f(nan_x)                                 # NaN después de tener best: tampoco lo reemplaza
    p.observe(nan_x)                           # ni observado
    assert p.n_f == 3
    assert p.best_f == 4.0
    np.testing.assert_allclose(p.best_x, [3.0, 1.0])
    assert p.history == [{"eval_equiv": 2.0, "f_best": 4.0}]


def test_observe_no_cuenta_y_no_devuelve_valor(cuadratica):
    func = cuadratica(UNOS2)
    p = CountedProblem(func, k=4, budget=100)
    p.grad(np.array([0.0, 0.0]))                  # eval_equiv = 4
    resultado = p.observe(np.array([2.0, 1.0]))   # f = 1
    assert resultado is None
    assert p.n_f == 0
    assert p.n_grad == 1
    assert p.eval_equiv() == 4
    assert func.llamadas_f == 1                   # sí evaluó la función (sin contar)
    assert p.best_f == pytest.approx(1.0)
    np.testing.assert_allclose(p.best_x, [2.0, 1.0])
    # en observe, eval_equiv del registro = valor actual del contador
    assert p.history == [{"eval_equiv": 4.0, "f_best": 1.0}]
    # observar algo igual o peor no agrega registro
    p.observe(np.array([2.0, 1.0]))
    p.observe(np.array([5.0, 5.0]))
    assert len(p.history) == 1
    # observar algo mejor sí
    p.observe(np.array([1.0, 1.0]))
    assert p.history[-1] == {"eval_equiv": 4.0, "f_best": 0.0}


def test_observe_funciona_con_presupuesto_agotado(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=4)
    p.grad(np.zeros(2))
    assert p.budget_exhausted()
    assert p.observe(np.array([1.0, 1.0])) is None
    assert p.best_f == 0.0
    assert p.eval_equiv() == 4


def test_best_x_es_copia_defensiva(cuadratica):
    p = CountedProblem(cuadratica(UNOS2), k=4, budget=100)
    x = np.array([2.0, 2.0])
    p.f(x)
    x[0] = 99.0                               # mutación posterior del arreglo del algoritmo
    np.testing.assert_allclose(p.best_x, [2.0, 2.0])
    y = np.array([1.0, 1.5])
    p.observe(y)
    y[:] = -7.0
    np.testing.assert_allclose(p.best_x, [1.0, 1.5])


# ---------------------------------------------------------------- validaciones

@pytest.mark.parametrize("k", [0, -1, -0.5, float("nan"), float("inf"), -float("inf")])
def test_k_invalido(cuadratica, k):
    with pytest.raises(ValueError):
        CountedProblem(cuadratica(UNOS2), k=k, budget=100)


@pytest.mark.parametrize("budget", [0, -10, float("nan"), float("inf"), -float("inf")])
def test_budget_invalido(cuadratica, budget):
    with pytest.raises(ValueError):
        CountedProblem(cuadratica(UNOS2), k=4, budget=budget)


@pytest.mark.parametrize("valor", [True, False, np.bool_(True), np.bool_(False)])
def test_bool_rechazado_en_k_y_budget(cuadratica, valor):
    with pytest.raises(TypeError):
        CountedProblem(cuadratica(UNOS2), k=valor, budget=100)
    with pytest.raises(TypeError):
        CountedProblem(cuadratica(UNOS2), k=4, budget=valor)


def test_atributos_publicos_func_k_budget(cuadratica):
    func = cuadratica(UNOS2)
    p = CountedProblem(func, k=4, budget=100)
    assert p.func is func and p.k == 4 and p.budget == 100
