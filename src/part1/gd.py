"""Descenso por gradiente de la Parte 1 (Spec §5.1, §6.2 y §6.3).

Dos variantes con el mismo bucle (`_descenso`) y distinta regla de paso:
  - "fijo" (T1.2): x_{t+1} = Π(x_t − η ∇f(x_t)), con Π el recorte a `problem.func.bounds`.
  - "armijo" (T1.3): búsqueda de paso con retroceso de Armijo sobre el ensayo proyectado.

Todas las evaluaciones pasan por `CountedProblem` (§6.2): el GD no cuenta nada a mano.
"""

from __future__ import annotations

import math
from numbers import Real

import numpy as np

from src.common.counter import BudgetExhausted, CountedProblem

VARIANTE_FIJO = "fijo"
VARIANTE_ARMIJO = "armijo"
VARIANTES = (VARIANTE_FIJO, VARIANTE_ARMIJO)
CLAVES_ARMIJO = ("eta0", "beta", "c")


def _real(nombre: str, valor) -> float:
    """Devuelve `valor` como float si es un número real (no bool); si no, lanza ValueError."""
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
        raise ValueError(f"{nombre} debe ser un número real (recibido {valor!r})")
    return float(valor)


def _positivo_finito(nombre: str, valor) -> float:
    """Devuelve `valor` como float si es un número real finito y > 0 (no bool).

    Si no, lanza ValueError.
    """
    numero = _real(nombre, valor)
    if not (0 < numero < math.inf):  # también rechaza NaN y ±inf
        raise ValueError(f"{nombre} debe ser finito y > 0 (recibido {valor!r})")
    return numero


def _entre_cero_y_uno(nombre: str, valor) -> float:
    """Devuelve `valor` como float si es un número real (no bool) con 0 < valor < 1."""
    numero = _real(nombre, valor)
    if not (0 < numero < 1):  # también rechaza NaN
        raise ValueError(f"{nombre} debe cumplir 0 < {nombre} < 1 (recibido {valor!r})")
    return numero


def _frame(iteracion: int, x: np.ndarray, problem: CountedProblem) -> dict:
    """Frame de la animación (§5.1): una sola posición y el mejor punto visto hasta ahora."""
    return {"iter": iteracion, "positions": [x.tolist()], "best": problem.best_x.tolist()}


class _PasoFijo:
    """Regla de paso fijo: x' = Π(x − η g), registrado con `observe` (no cuesta; n_f = 0)."""

    def __init__(self, problem: CountedProblem, eta: float):
        self.problem = problem
        self.eta = eta
        self.lo, self.hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]

    def __call__(self, x: np.ndarray, g: np.ndarray) -> np.ndarray:
        x_nuevo = np.clip(x - self.eta * g, self.lo, self.hi)   # proyección Π al dominio
        self.problem.observe(x_nuevo)
        return x_nuevo


class _PasoArmijo:
    """Regla de Armijo con retroceso sobre el ensayo proyectado; guarda fx = f(x actual).

    Cada ensayo se evalúa con `problem.f` (cobrado y registrado en best/history). f(x0) se cobra
    una sola vez, en la primera llamada; después fx es el f del ensayo aceptado.
    """

    def __init__(self, problem: CountedProblem, eta0: float, beta: float, c: float):
        self.problem = problem
        self.eta0, self.beta, self.c = eta0, beta, c
        self.lo, self.hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]
        self.fx: float | None = None              # f en el punto actual (perezoso)

    def __call__(self, x: np.ndarray, g: np.ndarray) -> np.ndarray:
        if self.fx is None:
            self.fx = self.problem.f(x)           # f(x0): cobrada una sola vez
        eta = self.eta0
        while True:                               # sin tope: el presupuesto corta la búsqueda
            x_nuevo = np.clip(x - eta * g, self.lo, self.hi)
            f_nuevo = self.problem.f(x_nuevo)     # 1 evaluación por ensayo
            descenso = float(np.dot(g, x - x_nuevo))   # >= 0; sin recorte vale eta·‖g‖²
            if f_nuevo <= self.fx - self.c * descenso:
                break
            eta *= self.beta
        self.fx = f_nuevo
        return x_nuevo


def _descenso(problem: CountedProblem, siguiente_x, tol_grad: float, grabar: bool,
              rng: np.random.Generator) -> list[dict]:
    """Bucle común a ambas variantes; devuelve los frames (vacío si no se graban).

    `siguiente_x(x, g)` devuelve el nuevo punto aceptado y puede lanzar BudgetExhausted.
    """
    lo, hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]
    x = rng.uniform(lo, hi)                     # única llamada al rng
    problem.observe(x)                          # el punto inicial no cuesta
    frames = [_frame(0, x, problem)] if grabar else []
    iteracion = 0
    try:
        while True:
            g = problem.grad(x)                 # cuesta k evaluaciones equivalentes
            if np.linalg.norm(g) < tol_grad:    # convergió: no se da ese paso
                break
            x = siguiente_x(x, g)
            iteracion += 1
            if grabar:
                frames.append(_frame(iteracion, x, problem))
    except BudgetExhausted:
        pass                                    # presupuesto agotado: se devuelve lo visto
    return frames


def _eta_fijo(problem: CountedProblem, gd_cfg: dict) -> float:
    """eta validado; se elige por el nombre de la función (cfg["gd"]["eta"])."""
    etas = gd_cfg["eta"]
    nombre = problem.func.name
    if not isinstance(etas, dict):
        raise ValueError(f"gd.eta debe ser un mapa {{función: paso}} (recibido {etas!r})")
    if nombre not in etas:
        disponibles = ", ".join(sorted(map(str, etas))) or "(ninguna)"
        raise ValueError(
            f"gd.eta no tiene paso para la función {nombre!r}; funciones disponibles: {disponibles}"
        )
    return _positivo_finito(f"gd.eta.{nombre}", etas[nombre])


def _parametros_armijo(gd_cfg: dict) -> tuple[float, float, float]:
    """(eta0, beta, c) validados desde cfg["gd"]["armijo"]."""
    bloque = gd_cfg.get("armijo")
    if not isinstance(bloque, dict):
        raise ValueError(
            f"gd.armijo debe ser un mapa con claves {', '.join(CLAVES_ARMIJO)} "
            f"(recibido {bloque!r})"
        )
    for clave in CLAVES_ARMIJO:
        if clave not in bloque:
            raise ValueError(f"falta la clave gd.armijo.{clave}")
    eta0 = _positivo_finito("gd.armijo.eta0", bloque["eta0"])
    beta = _entre_cero_y_uno("gd.armijo.beta", bloque["beta"])
    c = _entre_cero_y_uno("gd.armijo.c", bloque["c"])
    return eta0, beta, c


def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Descenso por gradiente con proyección (Spec §6.3); contrato de §5.1.

    `cfg` es la configuración resuelta. Claves: `variante` ("fijo" o "armijo", la fija el runner),
    `gd.tol_grad`, `record_frames` (opcional, por defecto False) y, según la variante,
    `gd.eta` (fijo: mapa función → paso, se elige con `problem.func.name`) o
    `gd.armijo.{eta0, beta, c}` (armijo; `gd.eta` no se lee ni se exige).

    Bucle común, en este orden:
      1. x_0 ~ U(dominio) con UNA sola llamada `rng.uniform(lo, hi)`; el rng no se usa para nada
         más.
      2. `problem.observe(x_0)`: registra x_0 en best/history sin cobrarlo (eval_equiv = 0), para
         que haya un resultado válido aunque el presupuesto no alcance para nada.
      3. Bucle: g = `problem.grad(x)` (cuesta k); si ||g|| < tol_grad se termina sin dar el paso;
         si no, x ← regla de paso(x, g). BudgetExhausted (de grad o de f) termina el bucle y
         nunca sale de esta función.

    Regla "fijo": x ← Π(x − η g), Π = recorte al dominio, y `problem.observe(x)`. Nunca necesita
    el valor de f para decidir: usa `observe` (actualiza las curvas sin contar) y n_f = 0; solo
    paga k por cada ∇f (§5.1).

    Regla "armijo" (backtracking): la primera vez se cobra fx = f(x_0) (perezoso: si el primer
    gradiente ya cumple la tolerancia, n_f = 0). Luego, desde η = eta0, ensayo x' = Π(x − η g) con
    `problem.f(x')` (1 evaluación cobrada por ensayo); se acepta si
        f(x') ≤ fx − c·<g, x − x'>,
    y si no, η ← β·η (producto repetido) sin tope de retrocesos: el presupuesto corta la búsqueda.
    El término <g, x − x'> es el descenso del ensayo proyectado: sin recorte vale η‖g‖² (la
    condición de §6.3); con recorte evita exigir un descenso que la proyección no permite. Tras
    aceptar, x ← x' y fx ← f(x'), que se reutiliza en la siguiente iteración (f(x) no se vuelve a
    evaluar). Así n_f = 1 + (número total de ensayos). Los ensayos ya quedan registrados por
    `problem.f`, por eso los iterados aceptados no se vuelven a observar.

    El resultado es el mejor punto VISTO (problem.best_x), no el último; en Armijo puede ser un
    ensayo rechazado. Con dim == 2 y record_frames, "frames" tiene un frame por punto aceptado
    (iter 0, 1, 2, ...); si no, la clave no existe.
    """
    variante = cfg.get("variante")
    if variante not in VARIANTES:
        raise ValueError(
            f"variante de GD desconocida o ausente: {variante!r}; valores válidos: "
            f"{', '.join(VARIANTES)}"
        )
    gd_cfg = cfg["gd"]
    if variante == VARIANTE_FIJO:
        siguiente_x = _PasoFijo(problem, _eta_fijo(problem, gd_cfg))
    else:
        siguiente_x = _PasoArmijo(problem, *_parametros_armijo(gd_cfg))
    tol_grad = _positivo_finito("gd.tol_grad", gd_cfg["tol_grad"])
    grabar = problem.func.dim == 2 and bool(cfg.get("record_frames", False))
    frames = _descenso(problem, siguiente_x, tol_grad, grabar, rng)

    resultado = {
        "x_best": problem.best_x.tolist(),
        "f_best": float(problem.best_f),
        "n_f": int(problem.n_f),
        "n_grad": int(problem.n_grad),
        "eval_equiv": float(problem.eval_equiv()),
        "history": problem.history,
    }
    if grabar:
        resultado["frames"] = frames
    return resultado
