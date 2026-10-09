"""Pruebas de presupuesto de CountedProblem (T0.4; Spec §5.1 [DECIDIDO 9-oct] y §6.2).

BudgetExhausted se lanza ANTES de la evaluación tras la cual eval_equiv() > budget: después de
cualquier llamada aceptada, eval_equiv() <= budget. Usa la cuadrática compartida de conftest.py
con x_star = 0 (f(1, 1) = 2, f(0, 0) = 0).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.common.counter import BudgetExhausted, CountedProblem

CERO2 = [0.0, 0.0]


def test_budget_exhausted_es_excepcion():
    assert issubclass(BudgetExhausted, Exception)


def test_f_se_detiene_exactamente_en_el_presupuesto(cuadratica):
    func = cuadratica(CERO2)
    p = CountedProblem(func, k=4, budget=10)
    for _ in range(10):
        p.f(np.ones(2))
    assert p.eval_equiv() == 10
    assert p.budget_exhausted()
    with pytest.raises(BudgetExhausted):
        p.f(np.zeros(2))
    # no evaluó ni contó, ni actualizó best (f(0) = 0 habría mejorado)
    assert p.n_f == 10
    assert func.llamadas_f == 10
    assert p.best_f == 2.0
    assert len(p.history) == 1


def test_budget_exhausted_antes_y_despues(cuadratica):
    p = CountedProblem(cuadratica(CERO2), k=4, budget=3)
    assert not p.budget_exhausted()
    p.f(np.ones(2))
    p.f(np.ones(2))
    assert not p.budget_exhausted()   # queda espacio para 1 evaluación
    p.f(np.ones(2))
    assert p.budget_exhausted()


def test_presupuesto_menor_que_una_f(cuadratica):
    """budget = 0.5 es válido (> 0 y finito) pero no cabe ni una f: agotado desde el inicio."""
    func = cuadratica(CERO2)
    p = CountedProblem(func, k=4, budget=0.5)
    assert p.budget_exhausted()
    with pytest.raises(BudgetExhausted):
        p.f(np.ones(2))
    with pytest.raises(BudgetExhausted):
        p.grad(np.ones(2))
    assert p.n_f == 0 and p.n_grad == 0
    assert func.llamadas_f == 0 and func.llamadas_grad == 0


def test_grad_con_costo_k_no_excede_el_presupuesto(cuadratica):
    """budget = 10, k = 4: caben 2 gradientes (8); el tercero (12) lanza; aún caben 2 f (10)."""
    func = cuadratica(CERO2)
    p = CountedProblem(func, k=4, budget=10)
    p.grad(np.ones(2))
    p.grad(np.ones(2))
    assert p.eval_equiv() == 8
    assert not p.budget_exhausted()
    with pytest.raises(BudgetExhausted):
        p.grad(np.ones(2))
    assert p.n_grad == 2
    assert func.llamadas_grad == 2
    assert p.eval_equiv() == 8
    p.f(np.ones(2))
    p.f(np.ones(2))
    assert p.eval_equiv() == 10
    with pytest.raises(BudgetExhausted):
        p.f(np.ones(2))
    assert p.eval_equiv() == 10


def test_grad_cabe_justo(cuadratica):
    p = CountedProblem(cuadratica(CERO2), k=4, budget=4)
    p.grad(np.ones(2))
    assert p.eval_equiv() == 4
    with pytest.raises(BudgetExhausted):
        p.grad(np.ones(2))
    with pytest.raises(BudgetExhausted):
        p.f(np.ones(2))


@pytest.mark.parametrize("k", [1, 4, 6, 2.5])
def test_contador_nunca_supera_presupuesto_con_mezcla_aleatoria(cuadratica, k):
    """Mezcla aleatoria de f y grad hasta agotar: eval_equiv nunca supera el presupuesto."""
    rng = np.random.default_rng(123)
    budget = 97
    p = CountedProblem(cuadratica(CERO2), k=k, budget=budget)
    lanzamientos = 0
    for _ in range(500):
        try:
            if rng.random() < 0.3:
                p.grad(rng.uniform(-5, 5, size=2))
            else:
                p.f(rng.uniform(-5, 5, size=2))
        except BudgetExhausted:
            lanzamientos += 1
        assert p.eval_equiv() <= budget
    assert lanzamientos > 0
    assert p.budget_exhausted()


def test_ultima_generacion_truncada_con_presupuesto_no_multiplo(cuadratica, bucle_poblacional):
    """N = 30, budget = 100 (no múltiplo de 30): 3 generaciones completas (90) + 10 individuos de
    la cuarta, que queda truncada (§6.2)."""
    N, T = 30, 50
    func = cuadratica(CERO2)
    p = CountedProblem(func, k=4, budget=100)
    bucle_poblacional(p, N, T, np.random.default_rng(0))
    assert p.n_f == 100
    assert p.eval_equiv() == 100
    assert func.llamadas_f == 100
    assert p.n_f % N == 10
    assert p.budget_exhausted()


def test_presupuesto_no_entero(cuadratica):
    """budget en evaluaciones equivalentes puede ser float: 5.5 deja hacer 5 f."""
    p = CountedProblem(cuadratica(CERO2), k=4, budget=5.5)
    for _ in range(5):
        p.f(np.ones(2))
    assert p.budget_exhausted()
    with pytest.raises(BudgetExhausted):
        p.f(np.ones(2))
    assert p.eval_equiv() == 5


# ------------------------------------- redondeo en coma flotante (ronda 2, verificador-matematico)

def test_redondeo_k_un_tercio_rechaza_el_grad_que_dejaria_eval_equiv_sobre_budget(cuadratica):
    """k = 1/3: 18 + (1/3)·5 = 19.666666666666668 > budget en coma flotante, así que el quinto
    grad se rechaza (con la comprobación vieja eval_equiv() + k se aceptaba y quedaba > budget)."""
    budget = 19.666666666666664
    p = CountedProblem(cuadratica(CERO2), k=1 / 3, budget=budget)
    for _ in range(18):
        p.f(np.ones(2))
    for _ in range(4):
        p.grad(np.ones(2))
    with pytest.raises(BudgetExhausted):
        p.grad(np.ones(2))
    assert p.n_grad == 4
    assert p.eval_equiv() <= budget


def test_redondeo_k_pi_acepta_grad_que_cabe_exactamente(cuadratica):
    """k = π: 10 + 14π ≤ budget en coma flotante, así que el grad número 14 DEBE aceptarse."""
    budget = 53.982297150257104
    p = CountedProblem(cuadratica(CERO2), k=math.pi, budget=budget)
    for _ in range(10):
        p.f(np.ones(2))
    for _ in range(13):
        p.grad(np.ones(2))
    p.grad(np.ones(2))                       # no debe lanzar
    assert p.n_grad == 14
    assert p.eval_equiv() == 10 + math.pi * 14
    assert p.eval_equiv() <= budget


@pytest.mark.parametrize("k", [1 / 3, 0.1, math.pi, 2 / 7, 1.1])
@pytest.mark.parametrize("semilla", range(5))
def test_busqueda_aleatoria_k_no_representable(cuadratica, k, semilla):
    """Con k no representable en binario, eval_equiv() <= budget después de toda llamada.

    Los presupuestos se eligen en las fronteras: valores alcanzables a + k·b y sus vecinos
    inmediatos en coma flotante, que es donde un error de redondeo en la comprobación previa se
    manifestaría.
    """
    rng = np.random.default_rng(semilla)
    for _ in range(40):
        a, b = int(rng.integers(0, 30)), int(rng.integers(1, 30))
        frontera = a + k * b
        vecinos = [frontera, np.nextafter(frontera, -np.inf), np.nextafter(frontera, np.inf)]
        budget = float(rng.choice(vecinos))
        p = CountedProblem(cuadratica(CERO2), k=k, budget=budget)
        for _ in range(400):
            antes = (p.n_f, p.n_grad)
            try:
                if rng.random() < 0.4:
                    p.grad(np.ones(2))
                else:
                    p.f(np.ones(2))
            except BudgetExhausted:
                assert (p.n_f, p.n_grad) == antes   # rechazo sin contar
            assert p.eval_equiv() <= budget
        assert p.budget_exhausted()


def test_k_float32_no_excede_el_presupuesto_y_se_normaliza(cuadratica):
    """Con k = np.float32 la comparación se haría en float32 (NEP 50) y podría exceder el
    presupuesto por < 1 ulp; el constructor normaliza k y budget a float de Python."""
    k = np.float32(0.1)
    budget = math.nextafter(float(np.float32(1) + k), 0)
    p = CountedProblem(cuadratica(CERO2), k=k, budget=budget)
    assert type(p.k) is float
    assert type(p.budget) is float
    p.f(np.ones(2))
    try:
        p.grad(np.ones(2))
    except BudgetExhausted:
        assert p.n_grad == 0
    assert p.eval_equiv() <= budget
