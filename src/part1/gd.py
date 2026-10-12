"""Descenso por gradiente de la Parte 1 (Spec §5.1, §6.2 y §6.3).

Variante "fijo" (T1.2): paso fijo con proyección al dominio, x_{t+1} = Π(x_t - η ∇f(x_t)), donde
Π es el recorte a `problem.func.bounds`. La variante "armijo" llega en T1.3.

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


def _positivo_finito(nombre: str, valor) -> float:
    """Devuelve `valor` como float si es un número real finito y > 0 (no bool).

    Si no, lanza ValueError.
    """
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
        raise ValueError(f"{nombre} debe ser un número real finito y > 0 (recibido {valor!r})")
    if not (0 < valor < math.inf):  # también rechaza NaN y ±inf
        raise ValueError(f"{nombre} debe ser finito y > 0 (recibido {valor!r})")
    return float(valor)


def _leer_parametros(problem: CountedProblem, cfg: dict) -> tuple[float, float]:
    """(eta, tol_grad) validados; eta se elige por el nombre de la función (cfg["gd"]["eta"])."""
    gd_cfg = cfg["gd"]
    etas = gd_cfg["eta"]
    nombre = problem.func.name
    if not isinstance(etas, dict):
        raise ValueError(f"gd.eta debe ser un mapa {{función: paso}} (recibido {etas!r})")
    if nombre not in etas:
        disponibles = ", ".join(sorted(map(str, etas))) or "(ninguna)"
        raise ValueError(
            f"gd.eta no tiene paso para la función {nombre!r}; funciones disponibles: {disponibles}"
        )
    eta = _positivo_finito(f"gd.eta.{nombre}", etas[nombre])
    tol_grad = _positivo_finito("gd.tol_grad", gd_cfg["tol_grad"])
    return eta, tol_grad


def _frame(iteracion: int, x: np.ndarray, problem: CountedProblem) -> dict:
    """Frame de la animación (§5.1): una sola posición y el mejor punto visto hasta ahora."""
    return {"iter": iteracion, "positions": [x.tolist()], "best": problem.best_x.tolist()}


def _descenso_paso_fijo(problem: CountedProblem, eta: float, tol_grad: float, grabar: bool,
                        rng: np.random.Generator) -> list[dict]:
    """Bucle del GD de paso fijo con proyección; devuelve los frames (vacío si no se graban)."""
    lo, hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]
    x = rng.uniform(lo, hi)                     # única llamada al rng
    problem.observe(x)                          # el punto inicial no cuesta
    frames = [_frame(0, x, problem)] if grabar else []
    iteracion = 0
    while True:
        try:
            g = problem.grad(x)                 # cuesta k evaluaciones equivalentes
        except BudgetExhausted:
            break
        if np.linalg.norm(g) < tol_grad:        # convergió: no se da ese paso
            break
        x = np.clip(x - eta * g, lo, hi)        # proyección Π al dominio
        problem.observe(x)
        iteracion += 1
        if grabar:
            frames.append(_frame(iteracion, x, problem))
    return frames


def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Descenso por gradiente con proyección (Spec §6.3); contrato de §5.1.

    `cfg` es la configuración resuelta. Claves: `variante` ("fijo" o "armijo", la fija el runner),
    `gd.eta` (mapa función → paso, se elige con `problem.func.name`), `gd.tol_grad` y
    `record_frames` (opcional, por defecto False).

    Variante "fijo", en este orden:
      1. x_0 ~ U(dominio) con UNA sola llamada `rng.uniform(lo, hi)`; el rng no se usa para nada
         más.
      2. `problem.observe(x_0)`: registra x_0 en best/history sin cobrarlo (eval_equiv = 0).
      3. Bucle: g = `problem.grad(x)` (cuesta k); si el presupuesto no alcanza (BudgetExhausted)
         se termina; si ||g|| < tol_grad se termina sin dar el paso; si no, x ← Π(x − η g) con
         Π = recorte al dominio, y `problem.observe(x)`.
    El GD de paso fijo nunca necesita el valor de f para decidir, por eso usa `observe` (que
    actualiza las curvas de convergencia sin contar) y n_f = 0: solo paga k por cada ∇f (§5.1).
    BudgetExhausted nunca sale de esta función. El resultado es el mejor punto VISTO
    (problem.best_x), no el último. Con dim == 2 y record_frames, "frames" tiene un frame por
    punto visitado (iter 0, 1, 2, ...); si no, la clave no existe.
    """
    variante = cfg.get("variante")
    if variante not in VARIANTES:
        raise ValueError(
            f"variante de GD desconocida o ausente: {variante!r}; valores válidos: "
            f"{', '.join(VARIANTES)}"
        )
    if variante == VARIANTE_ARMIJO:
        raise NotImplementedError("variante 'armijo': se implementa en T1.3")

    eta, tol_grad = _leer_parametros(problem, cfg)
    grabar = problem.func.dim == 2 and bool(cfg.get("record_frames", False))
    frames = _descenso_paso_fijo(problem, eta, tol_grad, grabar, rng)

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
