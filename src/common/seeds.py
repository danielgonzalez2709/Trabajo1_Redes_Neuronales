"""Regla única de semillas (Spec §4.1): ``rng = np.random.default_rng(base_seed + run_id)``.

Prohibido ``np.random.seed`` global y el módulo ``random``: cada corrida recibe su propio
``np.random.Generator`` independiente del estado global.

Por diseño solo importa la suma: ``make_rng(0, 5)`` y ``make_rng(5, 0)`` dan la misma secuencia.
Por eso los resultados documentan la semilla efectiva (``seeds_for_runs``).
"""

from __future__ import annotations

import numpy as np


def validar_entero(valor, nombre: str, minimo: int = 0) -> int:
    """Devuelve ``valor`` como ``int`` nativo si es entero (int o entero numpy, no bool) y ``>= minimo``.

    Tipo incorrecto → ``TypeError``; fuera de rango → ``ValueError``.
    """
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, (int, np.integer)):
        raise TypeError(f"{nombre} debe ser un entero; se recibió {valor!r} ({type(valor).__name__})")
    valor = int(valor)
    if valor < minimo:
        raise ValueError(f"{nombre} debe ser un entero >= {minimo}; se recibió {valor}")
    return valor


def make_rng(base_seed: int, run_id: int) -> np.random.Generator:
    """Generador de la corrida ``run_id``: ``np.random.default_rng(base_seed + run_id)``."""
    base = validar_entero(base_seed, "base_seed")
    run = validar_entero(run_id, "run_id")
    return np.random.default_rng(base + run)


def seeds_for_runs(base_seed: int, n_runs: int) -> list[int]:
    """Semillas efectivas ``[base_seed + run_id for run_id in range(n_runs)]`` (para documentarlas en los resultados)."""
    base = validar_entero(base_seed, "base_seed")
    n = validar_entero(n_runs, "n_runs")
    return [base + run_id for run_id in range(n)]
