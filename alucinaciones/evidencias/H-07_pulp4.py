"""Evidencia H-07: PuLP 4.0 ya no incluye CBC y cambió la API de variables.

Ejecutar con el entorno del proyecto (requirements.txt):  python alucinaciones/evidencias/H-07_pulp4.py
"""
import itertools
import random

import pulp

print("PuLP", pulp.__version__)
print("Solvers disponibles:", pulp.listSolvers(onlyAvailable=True))
print("¿Existe PULP_CBC_CMD (API de versiones anteriores)?", hasattr(pulp, "PULP_CBC_CMD"))

try:
    pulp.LpVariable("x", 0, 1, cat="Binary")  # forma clásica que reproducen las IA
    print("LpVariable(..., cat=...) funciona")
except TypeError as exc:
    print("LpVariable(..., cat=...) falla:", exc)

# Forma correcta en PuLP 4.0: problema.add_variable(...) + solver instalado con el extra pulp[highs]
random.seed(0)
n = 6
C = [[0 if i == j else random.randint(1, 20) for j in range(n)] for i in range(n)]
m = pulp.LpProblem("tsp", pulp.LpMinimize)
x = {(i, j): m.add_variable(f"x{i}_{j}", cat="Binary") for i in range(n) for j in range(n) if i != j}
m += pulp.lpSum(C[i][j] * x[i, j] for i, j in x)
for i in range(n):
    m += pulp.lpSum(x[i, j] for j in range(n) if j != i) == 1
    m += pulp.lpSum(x[j, i] for j in range(n) if j != i) == 1
for k in range(2, n):
    for S in itertools.combinations(range(n), k):
        m += pulp.lpSum(x[i, j] for i in S for j in S if i != j) <= k - 1
m.solve(pulp.HiGHS(msg=False))
fuerza_bruta = min(sum(C[p[i]][p[(i + 1) % n]] for i in range(n))
                   for p in itertools.permutations(range(n)) if p[0] == 0)
print("Óptimo DFJ con HiGHS:", pulp.value(m.objective), "| fuerza bruta:", fuerza_bruta)
