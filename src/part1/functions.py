"""Funciones de prueba de la Parte 1: Rosenbrock y Rastrigin (Spec §5.1 y §6.1).

Las funciones están definidas en todo Rⁿ: el dominio (`bounds`) es información para los
optimizadores, que son quienes proyectan; aquí no se recorta ni se valida que x esté dentro.
"""

from __future__ import annotations

import numpy as np


class TestFunction:
    """Interfaz común (Spec §5.1).

    Atributos públicos:
        name   -- identificador en minúsculas y sin guion bajo (coincide con run_filename, §5.4).
        dim    -- dimensión n (int).
        bounds -- np.ndarray float64 de forma (dim, 2), no escribible: [límite inferior, superior].
        x_star -- np.ndarray float64 de forma (dim,), no escribible: minimizador global.
        f_star -- float: valor mínimo global f(x_star).

    Cada subclase define `name`, `dim_min` (dimensión mínima), `limite` (dominio
    [-limite, limite]ⁿ), `x_star_valor` (x* = (x_star_valor, ..., x_star_valor)), `f_star`,
    y los cálculos `_f(x)` y `_grad(x)` sobre un arreglo ya validado.
    """

    __test__ = False  # evita que pytest intente recolectar esta clase como prueba

    name: str
    dim_min: int
    limite: float
    x_star_valor: float
    f_star: float

    def __init__(self, dim: int) -> None:
        if isinstance(dim, bool) or not isinstance(dim, (int, np.integer)):
            raise TypeError(f"{self.name}: dim debe ser entero, se recibió {dim!r}")
        if dim < self.dim_min:
            raise ValueError(f"{self.name}: dim debe ser >= {self.dim_min}, se recibió {dim}")
        self.dim = int(dim)
        self.bounds = np.tile(np.array([-self.limite, self.limite], dtype=float), (self.dim, 1))
        self.bounds.setflags(write=False)
        self.x_star = np.full(self.dim, self.x_star_valor, dtype=float)
        self.x_star.setflags(write=False)

    def _validar(self, x) -> np.ndarray:
        """Convierte x a arreglo float64 y exige la forma (dim,)."""
        arr = np.asarray(x, dtype=float)
        if arr.shape != (self.dim,):
            raise ValueError(
                f"{self.name}: x debe tener forma ({self.dim},), se recibió forma {arr.shape}"
            )
        return arr

    def f(self, x) -> float:
        """Valor de la función en x, como float de Python."""
        return float(self._f(self._validar(x)))

    def grad(self, x) -> np.ndarray:
        """Gradiente analítico en x: arreglo nuevo float64 de forma (dim,); no modifica x."""
        return np.asarray(self._grad(self._validar(x)), dtype=float)

    def _f(self, x: np.ndarray) -> float:
        raise NotImplementedError

    def _grad(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class Rosenbrock(TestFunction):
    """Rosenbrock (Spec §6.1), n >= 2, dominio [-2.048, 2.048]ⁿ, x* = (1, ..., 1), f* = 0.

    f(x) = Σ_{i=1}^{n-1} [100 (x_{i+1} - x_i²)² + (1 - x_i)²]

    ∂f/∂x_i = -400 x_i (x_{i+1} - x_i²) - 2 (1 - x_i)   [solo si i < n]
              + 200 (x_i - x_{i-1}²)                     [solo si i > 1]
    """

    name = "rosenbrock"
    dim_min = 2
    limite = 2.048
    x_star_valor = 1.0
    f_star = 0.0

    def _f(self, x: np.ndarray) -> float:
        actual, siguiente = x[:-1], x[1:]
        return np.sum(100.0 * (siguiente - actual**2) ** 2 + (1.0 - actual) ** 2)

    def _grad(self, x: np.ndarray) -> np.ndarray:
        actual, siguiente = x[:-1], x[1:]
        g = np.zeros_like(x)
        g[:-1] += -400.0 * actual * (siguiente - actual**2) - 2.0 * (1.0 - actual)
        g[1:] += 200.0 * (siguiente - actual**2)
        return g


class Rastrigin(TestFunction):
    """Rastrigin (Spec §6.1), n >= 1, dominio [-5.12, 5.12]ⁿ, x* = (0, ..., 0), f* = 0.

    f(x) = 10 n + Σ_{i=1}^{n} [x_i² - 10 cos(2π x_i)]

    ∂f/∂x_i = 2 x_i + 20π sin(2π x_i)
    """

    name = "rastrigin"
    dim_min = 1
    limite = 5.12
    x_star_valor = 0.0
    f_star = 0.0

    def _f(self, x: np.ndarray) -> float:
        return 10.0 * self.dim + np.sum(x**2 - 10.0 * np.cos(2.0 * np.pi * x))

    def _grad(self, x: np.ndarray) -> np.ndarray:
        return 2.0 * x + 20.0 * np.pi * np.sin(2.0 * np.pi * x)


FUNCIONES: dict[str, type[TestFunction]] = {
    Rosenbrock.name: Rosenbrock,
    Rastrigin.name: Rastrigin,
}


def get_function(name: str, dim: int) -> TestFunction:
    """Devuelve la instancia de la función `name` en dimensión `dim`.

    Lanza ValueError si el nombre no está en FUNCIONES (el mensaje lista los válidos).
    """
    if name not in FUNCIONES:
        validos = ", ".join(sorted(FUNCIONES))
        raise ValueError(f"función desconocida {name!r}; nombres válidos: {validos}")
    return FUNCIONES[name](dim)
