"""Piezas comunes de los solvers del TSP de la Parte 2 (Spec §7.4.1 y §7.4.2).

`aco.py` (T3.3) y `ga.py` (T3.4) comparten la validación de la matriz C, el costo de recorridos cerrados, el
recorrido del vecino más cercano y la validación de parámetros (§7.4.2: "se reutilizan sin duplicar código y sin
cambiar el comportamiento de `aco.py`"). Se extrajeron de `aco.py` sin cambiar su lógica ni sus mensajes de error.
"""

from __future__ import annotations

import math

import numpy as np

N_MINIMO = 3  # con menos de 3 ciudades no hay ciclo hamiltoniano con arcos distintos


# ---------------------------------------------------------------------------------------- validación


def validar_real(valor, nombre: str, minimo: float, maximo: float | None = None, *, min_abierto=False,
                 max_abierto=False) -> float:
    """`valor` como float finito dentro del intervalo; TypeError si no es número, ValueError si está fuera."""
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, (int, float, np.integer, np.floating)):
        raise TypeError(f"{nombre} debe ser un número; se recibió {valor!r} ({type(valor).__name__})")
    x = float(valor)
    fuera = (
        not math.isfinite(x)
        or (x <= minimo if min_abierto else x < minimo)
        or (maximo is not None and (x >= maximo if max_abierto else x > maximo))
    )
    if fuera:
        izq = "(" if min_abierto else "["
        der = ")" if max_abierto else "]"
        rango = f"{izq}{minimo}, {maximo if maximo is not None else '∞'}{der}"
        raise ValueError(f"{nombre} debe estar en {rango}; se recibió {valor!r}")
    return x


def leer_clave(bloque: dict, clave: str, ruta: str, seccion: str):
    """`bloque[clave]`; si falta (o `bloque` no es un mapeo), KeyError que nombra la ruta y la sección del Spec."""
    try:
        return bloque[clave]
    except (KeyError, TypeError):
        raise KeyError(f"falta la clave {ruta} en la configuración (Spec {seccion})") from None


def validar_generador(rng) -> np.random.Generator:
    """El solver recibe su `rng` (Spec §4.1); no crea el suyo ni acepta una semilla."""
    if not isinstance(rng, np.random.Generator):
        raise TypeError(f"rng debe ser un np.random.Generator (Spec §4.1); se recibió {type(rng).__name__}")
    return rng


def validar_matriz(C) -> np.ndarray:
    """C como float64: cuadrada, n ≥ 3, finita, simétrica y con c_ij > 0 fuera de la diagonal (η = 1/c)."""
    C = np.asarray(C)
    if C.dtype.kind not in "iuf":
        raise ValueError(f"C debe ser numérica; se recibió dtype {C.dtype}")
    if C.ndim != 2 or C.shape[0] != C.shape[1]:
        raise ValueError(f"C debe ser una matriz cuadrada; se recibió forma {C.shape}")
    n = C.shape[0]
    if n < N_MINIMO:
        raise ValueError(f"C debe tener n >= {N_MINIMO} ciudades; se recibió n = {n}")
    C = C.astype(float)
    if not np.isfinite(C).all():
        raise ValueError("C debe ser finita (sin NaN ni inf)")
    if not np.array_equal(C, C.T):
        raise ValueError("C debe ser simétrica (TSP simétrico, Spec §7.3)")
    if not (C[~np.eye(n, dtype=bool)] > 0).all():
        raise ValueError("C debe tener costos > 0 fuera de la diagonal (η = 1/c, notas Def. 13)")
    return C


# ----------------------------------------------------------------------------------------- recorridos


def costos_recorridos(C: np.ndarray, tours: np.ndarray) -> np.ndarray:
    """Costo de cada fila de `tours` (k × n), incluido el arco de cierre (última ciudad → primera)."""
    return C[tours, np.roll(tours, -1, axis=1)].sum(axis=1)


def vecino_mas_cercano(C: np.ndarray) -> tuple[np.ndarray, float]:
    """Recorrido del vecino más cercano desde la ciudad 0 y su costo C^nn (notas, Def. 8). Empates: menor índice."""
    n = C.shape[0]
    tour = [0]
    disponible = np.ones(n, dtype=bool)
    disponible[0] = False
    for _ in range(n - 1):
        candidatos = np.where(disponible, C[tour[-1]], np.inf)
        siguiente = int(np.argmin(candidatos))
        tour.append(siguiente)
        disponible[siguiente] = False
    tour = np.array(tour)
    return tour, float(costos_recorridos(C, tour[None, :])[0])
