"""Funciones de prueba de la Parte 1: Rosenbrock y Rastrigin (Spec §5.1 y §6.1).

Las funciones están definidas en todo Rⁿ: el dominio (`bounds`) es información para los
optimizadores, que son quienes proyectan; aquí no se recorta ni se valida que x esté dentro.
"""

from __future__ import annotations  # las anotaciones de tipo se evalúan de forma diferida

import numpy as np  # cálculo vectorial de f y ∇f


class TestFunction:  # interfaz común de las funciones de prueba (§5.1)
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

    name: str  # identificador de la función (el mismo que usa run_filename, §5.4)
    dim_min: int  # dimensión mínima admitida por la función
    limite: float  # semiancho del dominio [-limite, limite]ⁿ
    x_star_valor: float  # valor de cada coordenada de x*
    f_star: float  # valor mínimo global f*

    def __init__(self, dim: int) -> None:  # valida n y construye bounds y x*
        # dim debe ser entero de Python o de numpy; bool se rechaza aunque sea subclase de int
        if isinstance(dim, bool) or not isinstance(dim, (int, np.integer)):
            # tipo inválido para la dimensión
            raise TypeError(f"{self.name}: dim debe ser entero, se recibió {dim!r}")
        if dim < self.dim_min:  # dimensión por debajo del mínimo de la función
            # n demasiado pequeña (Rosenbrock exige n >= 2, Rastrigin n >= 1)
            raise ValueError(f"{self.name}: dim debe ser >= {self.dim_min}, se recibió {dim}")
        self.dim = int(dim)  # guarda n como int de Python (también si llegó como np.int64)
        # bounds: una fila [-limite, limite] por coordenada, forma (n, 2)
        self.bounds = np.tile(np.array([-self.limite, self.limite], dtype=float), (self.dim, 1))
        self.bounds.setflags(write=False)  # solo lectura: evita modificar el dominio por accidente
        # x* = (x_star_valor, ..., x_star_valor), un valor repetido en las dim coordenadas
        self.x_star = np.full(self.dim, self.x_star_valor, dtype=float)
        self.x_star.setflags(write=False)  # solo lectura: x* no se puede modificar

    def _validar(self, x) -> np.ndarray:  # normaliza la entrada antes de calcular f o ∇f
        """Convierte x a arreglo float64 y exige la forma (dim,)."""
        arr = np.asarray(x, dtype=float)  # acepta listas o arreglos; convierte a float64
        if arr.shape != (self.dim,):  # rechaza vectores de otra longitud, matrices o escalares
            raise ValueError(  # forma incorrecta de x
                # el mensaje indica la forma esperada y la recibida
                f"{self.name}: x debe tener forma ({self.dim},), se recibió forma {arr.shape}"
            )
        return arr  # x validado, listo para _f/_grad

    def f(self, x) -> float:  # f(x) pública del contrato §5.1
        """Valor de la función en x, como float de Python."""
        return float(self._f(self._validar(x)))  # valida x, calcula f y devuelve float nativo

    def grad(self, x) -> np.ndarray:  # ∇f(x) pública del contrato §5.1
        """Gradiente analítico en x: arreglo nuevo float64 de forma (dim,); no modifica x."""
        return np.asarray(self._grad(self._validar(x)), dtype=float)  # valida x y calcula ∇f

    def _f(self, x: np.ndarray) -> float:  # cálculo de f que define cada subclase
        raise NotImplementedError  # la clase base no tiene fórmula propia

    def _grad(self, x: np.ndarray) -> np.ndarray:  # cálculo de ∇f que define cada subclase
        raise NotImplementedError  # la clase base no tiene fórmula propia


class Rosenbrock(TestFunction):  # función de Rosenbrock, valle estrecho y mal condicionado
    """Rosenbrock (Spec §6.1), n >= 2, dominio [-2.048, 2.048]ⁿ, x* = (1, ..., 1), f* = 0.

    f(x) = Σ_{i=1}^{n-1} [100 (x_{i+1} - x_i²)² + (1 - x_i)²]

    ∂f/∂x_i = -400 x_i (x_{i+1} - x_i²) - 2 (1 - x_i)   [solo si i < n]
              + 200 (x_i - x_{i-1}²)                     [solo si i > 1]
    """

    name = "rosenbrock"  # identificador de la función
    dim_min = 2  # Rosenbrock necesita al menos dos coordenadas (n >= 2)
    limite = 2.048  # dominio [-2.048, 2.048]ⁿ (§6.1)
    x_star_valor = 1.0  # x* = (1, ..., 1)
    f_star = 0.0  # f* = 0

    def _f(self, x: np.ndarray) -> float:  # f de Rosenbrock (§6.1)
        actual, siguiente = x[:-1], x[1:]  # pares (x_i, x_{i+1}) para i = 1, ..., n-1
        # Σ [100 (x_{i+1} − x_i²)² + (1 − x_i)²]
        return np.sum(100.0 * (siguiente - actual**2) ** 2 + (1.0 - actual) ** 2)

    def _grad(self, x: np.ndarray) -> np.ndarray:  # ∇f de Rosenbrock (§6.1)
        actual, siguiente = x[:-1], x[1:]  # pares (x_i, x_{i+1}) para i = 1, ..., n-1
        g = np.zeros_like(x)  # acumulador de ∂f/∂x_i, misma forma que x
        # término −400 x_i (x_{i+1} − x_i²) − 2 (1 − x_i), solo para i < n
        g[:-1] += -400.0 * actual * (siguiente - actual**2) - 2.0 * (1.0 - actual)
        g[1:] += 200.0 * (siguiente - actual**2)  # término 200 (x_i − x_{i-1}²), solo para i > 1
        return g  # ∇f(x) completo


class Rastrigin(TestFunction):  # función de Rastrigin, multimodal con muchos mínimos locales
    """Rastrigin (Spec §6.1), n >= 1, dominio [-5.12, 5.12]ⁿ, x* = (0, ..., 0), f* = 0.

    f(x) = 10 n + Σ_{i=1}^{n} [x_i² - 10 cos(2π x_i)]

    ∂f/∂x_i = 2 x_i + 20π sin(2π x_i)
    """

    name = "rastrigin"  # identificador de la función
    dim_min = 1  # Rastrigin está definida desde n = 1
    limite = 5.12  # dominio [-5.12, 5.12]ⁿ (§6.1)
    x_star_valor = 0.0  # x* = (0, ..., 0)
    f_star = 0.0  # f* = 0

    def _f(self, x: np.ndarray) -> float:  # f de Rastrigin (§6.1)
        # f(x) = 10n + Σ [x_i² − 10 cos(2π x_i)], con n = self.dim
        return 10.0 * self.dim + np.sum(x**2 - 10.0 * np.cos(2.0 * np.pi * x))

    def _grad(self, x: np.ndarray) -> np.ndarray:  # ∇f de Rastrigin (§6.1)
        return 2.0 * x + 20.0 * np.pi * np.sin(2.0 * np.pi * x)  # ∂f/∂x_i = 2 x_i + 20π sin(2π x_i)


FUNCIONES: dict[str, type[TestFunction]] = {  # registro nombre → clase que usa get_function
    Rosenbrock.name: Rosenbrock,  # "rosenbrock" → Rosenbrock
    Rastrigin.name: Rastrigin,  # "rastrigin" → Rastrigin
}


def get_function(name: str, dim: int) -> TestFunction:  # fábrica: instancia la función por nombre
    """Devuelve la instancia de la función `name` en dimensión `dim`.

    Lanza ValueError si el nombre no está en FUNCIONES (el mensaje lista los válidos).
    """
    if name not in FUNCIONES:  # nombre no registrado
        validos = ", ".join(sorted(FUNCIONES))  # lista ordenada de nombres válidos para el mensaje
        # error que enumera los nombres admitidos
        raise ValueError(f"función desconocida {name!r}; nombres válidos: {validos}")
    return FUNCIONES[name](dim)  # crea la instancia; el constructor valida dim
