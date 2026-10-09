"""Configuración común de pytest.

- Hace importables el paquete src/ (desde la raíz) y los módulos de scripts/ (p. ej. comun_bloque1).
- Auxiliares de las pruebas del contador (T0.4): la cuadrática `Cuadratica` (fixture `cuadratica`)
  y el bucle poblacional de juguete (fixture `bucle_poblacional`).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for ruta in (SCRIPTS, ROOT):
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))


# ------------------------------------------------------------------------------------------------
# Auxiliares compartidos de las pruebas del contador (T0.4: test_counter.py y test_budget.py).
# No dependen de src/part1/functions.py (llega en T1.1).
# Imports aquí abajo (E402): el bloque de arriba debe modificar sys.path antes de importar de src/.

import numpy as np  # noqa: E402
import pytest  # noqa: E402


class Cuadratica:
    """f(x) = ||x - x_star||², ∇f(x) = 2(x - x_star); mínimo f_star = 0 en x_star (explícito).

    Cumple la interfaz de TestFunction que usa CountedProblem y registra las llamadas reales
    (llamadas_f, llamadas_grad) para verificar que observe/BudgetExhausted no cuentan mal.
    """

    name = "cuadratica"

    def __init__(self, x_star):
        self.x_star = np.array(x_star, dtype=float)
        self.dim = self.x_star.size
        self.bounds = np.array([[-5.0, 5.0]] * self.dim)
        self.f_star = 0.0
        self.llamadas_f = 0
        self.llamadas_grad = 0

    def f(self, x):
        self.llamadas_f += 1
        return float(np.sum((np.asarray(x, dtype=float) - self.x_star) ** 2))

    def grad(self, x):
        self.llamadas_grad += 1
        return 2.0 * (np.asarray(x, dtype=float) - self.x_star)


def correr_bucle_poblacional(problem, N: int, T: int, rng: np.random.Generator) -> None:
    """Optimizador poblacional de juguete: evalúa la población inicial y T generaciones de N
    individuos; captura BudgetExhausted y termina (patrón [DECIDIDO 9-oct, T0.4])."""
    from src.common.counter import BudgetExhausted

    lo, hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]
    x = rng.uniform(lo, hi, size=(N, problem.func.dim))
    try:
        for i in range(N):                       # población inicial (cuenta, §6.2)
            problem.f(x[i])
        for _ in range(T):                       # T generaciones
            x = np.clip(x + rng.normal(0.0, 0.1, size=x.shape), lo, hi)
            for i in range(N):
                problem.f(x[i])
    except BudgetExhausted:
        return


@pytest.fixture
def cuadratica():
    """Fábrica de la cuadrática de prueba: cuadratica(x_star) -> Cuadratica."""
    return Cuadratica


@pytest.fixture
def bucle_poblacional():
    """Auxiliar único del bucle poblacional: bucle_poblacional(problem, N, T, rng)."""
    return correr_bucle_poblacional
