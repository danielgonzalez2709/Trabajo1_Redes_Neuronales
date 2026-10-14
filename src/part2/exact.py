"""T3.2 — Óptimo exacto del TSP simétrico (Spec §7.4): formulación de Dantzig, Fulkerson y Johnson (1954) con PuLP 4 +
HiGHS y eliminación perezosa de subtours.

Modelo: una variable binaria x_ij por arista (i < j); cada ciudad tiene grado 2; se resuelve, se buscan los ciclos de la
solución y, si hay más de uno, se agrega para cada ciclo S la restricción Σ_{i<j ∈ S} x_ij ≤ |S| − 1 y se vuelve a
resolver. Termina cuando la solución es un único ciclo de n ciudades: ese ciclo es óptimo (las restricciones agregadas
son válidas para todo recorrido y el problema relajado ya no tiene subtours).

Se usa gap 0 (gapRel = gapAbs = 0): con la tolerancia por defecto de HiGHS (0,01 % relativo) el solver puede devolver
una ruta a unos céntimos del óptimo, insuficiente para ubicar umbrales donde las rutas difieren por menos de 1 €.
"""
from __future__ import annotations

import numpy as np
import pulp


def _ciclos(n: int, aristas: list[tuple[int, int]]) -> list[list[int]]:
    """Componentes conexas (ciclos) del grafo de grado 2 formado por las aristas elegidas."""
    vecinos = {i: [] for i in range(n)}
    for i, j in aristas:
        vecinos[i].append(j)
        vecinos[j].append(i)
    vistos, ciclos = set(), []
    for inicio in range(n):
        if inicio in vistos:
            continue
        pila, ciclo = [inicio], []
        while pila:
            u = pila.pop()
            if u in vistos:
                continue
            vistos.add(u)
            ciclo.append(u)
            pila.extend(vecinos[u])
        ciclos.append(ciclo)
    return ciclos


def _recorrido(n: int, aristas: list[tuple[int, int]]) -> list[int]:
    """Ordena las aristas de un único ciclo como permutación que empieza en la ciudad 0."""
    vecinos = {i: [] for i in range(n)}
    for i, j in aristas:
        vecinos[i].append(j)
        vecinos[j].append(i)
    tour, previo, actual = [0], None, 0
    while len(tour) < n:
        siguiente = vecinos[actual][0] if vecinos[actual][0] != previo else vecinos[actual][1]
        tour.append(siguiente)
        previo, actual = actual, siguiente
    return tour


def resolver_exacto(C) -> tuple[list[int], float, int]:
    """Recorrido óptimo de la matriz simétrica C. Devuelve (tour, costo, número de resoluciones del modelo)."""
    C = np.asarray(C, dtype=float)
    n = len(C)
    if n < 3:
        raise ValueError("el TSP exacto necesita al menos 3 ciudades")
    modelo = pulp.LpProblem("tsp_dfj", pulp.LpMinimize)
    x = {(i, j): modelo.add_variable(f"x_{i}_{j}", cat="Binary") for i in range(n) for j in range(i + 1, n)}
    modelo += pulp.lpSum(C[i, j] * var for (i, j), var in x.items())
    for i in range(n):
        modelo += pulp.lpSum(x[min(i, j), max(i, j)] for j in range(n) if j != i) == 2
    resoluciones = 0
    while True:
        # PuLP 4: solve() devuelve las estadísticas (con el estado); ya no existen pulp.LpStatus ni modelo.status.
        stats = modelo.solve(pulp.HiGHS(msg=False, gapRel=0.0, gapAbs=0.0))
        resoluciones += 1
        if stats.status != pulp.LpSolveStatus.Optimal:
            raise RuntimeError(f"HiGHS no encontró el óptimo: {stats.status!r}")
        aristas = [arista for arista, var in x.items() if var.value() > 0.5]
        ciclos = _ciclos(n, aristas)
        if len(ciclos) == 1:
            tour = _recorrido(n, aristas)
            costo = float(sum(C[tour[k], tour[(k + 1) % n]] for k in range(n)))
            return tour, costo, resoluciones
        for ciclo in ciclos:  # Dantzig, Fulkerson y Johnson: elimina cada subtour encontrado
            miembros = set(ciclo)
            modelo += pulp.lpSum(var for (i, j), var in x.items() if i in miembros and j in miembros) <= len(ciclo) - 1


def solve(C, cfg: dict | None = None, rng=None) -> dict:
    """Contrato de los solvers de la Parte 2 (Spec §5.2). `cfg` y `rng` no se usan: el método es determinista.

    `n_tour_evals` es 0 porque el exacto no evalúa recorridos completos (no es comparable con ACO/GA); `history`
    contiene una sola entrada con el óptimo.
    """
    tour, costo, _ = resolver_exacto(C)
    return {"tour": tour, "cost": costo, "n_tour_evals": 0,
            "history": [{"iter": 0, "best_cost": costo, "best_tour": tour}]}
