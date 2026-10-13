"""Datos sintéticos de 4 ciudades compartidos por test_envolvente.py y test_experiment_part2.py (no es un módulo de
pruebas: pytest no lo recolecta).

Ciudades 0..3: los tres ciclos distintos son A = (0,1,2,3), B = (0,1,3,2) y C = (0,2,1,3).
Arcos de A: 01, 12, 23, 30 · B: 01, 13, 32, 20 · C: 02, 21, 13, 30.
"""

from __future__ import annotations

import numpy as np

from src.part2.costos import Componentes
from src.part2.envolvente import Rectas, rectas

A, B, C = (0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 1, 3)

UNO = (0.0, 1.0)  # peaje 0, 1 h
CARO = (10.0, 0.5)  # peaje 10 €, 0,5 h

# Arco 12 (solo lo usan A y C) a trozos: rápida 6 € + 1 h, sin peaje 0 € + 1,5 h → cambia de alternativa en w = 12.
# A(w) = 3w + mín(6 + w, 1,5w) = 4,5w (w ≤ 12) | 6 + 4w (w ≥ 12)
# B(w) = 20 + 3w
# C(w) = 20 + 2w + mín(6 + w, 1,5w) = 20 + 3,5w (w ≤ 12) | 26 + 3w (w ≥ 12)
RAPIDA_TROZOS = {(0, 1): UNO, (1, 2): (6.0, 1.0), (2, 3): UNO, (0, 3): UNO, (1, 3): CARO, (0, 2): CARO}
SIN_PEAJE_TROZOS = {(1, 2): (0.0, 1.5)}


def comp(rapida: dict, sin_peaje: dict | None = None, n: int = 4) -> Componentes:
    """Componentes sintéticos: {(i, j): (peaje, tiempo)} por alternativa, distancia 0 (sin combustible).

    Si `sin_peaje` es None, la alternativa sin peaje es idéntica a la rápida en todos los arcos.
    """
    sin_peaje = rapida if sin_peaje is None else {**rapida, **sin_peaje}
    mats = {}
    for nombre, arcos in (("rapida", rapida), ("sin_peaje", sin_peaje)):
        p, t = np.zeros((n, n)), np.zeros((n, n))
        for (i, j), (peaje, tiempo) in arcos.items():
            p[i, j] = p[j, i] = peaje
            t[i, j] = t[j, i] = tiempo
        mats[f"peaje_eur_{nombre}"], mats[f"tiempo_h_{nombre}"] = p, t
        mats[f"dist_km_{nombre}"] = np.zeros((n, n))
    return Componentes(**mats)


def comp_trozos(intercambiadas: bool = False) -> Componentes:
    """Los arcos a trozos; con `intercambiadas`, la sin peaje del arco 12 es la rápida (misma función de costo)."""
    if intercambiadas:
        return comp({**RAPIDA_TROZOS, (1, 2): SIN_PEAJE_TROZOS[(1, 2)]}, {(1, 2): RAPIDA_TROZOS[(1, 2)]})
    return comp(RAPIDA_TROZOS, SIN_PEAJE_TROZOS)


def rectas_unitarias(componentes: Componentes) -> Rectas:
    """Rectas con consumo y precio 1 (la distancia es 0, así que no influyen)."""
    return rectas(componentes, consumo_l100=1.0, precio_l=1.0)
