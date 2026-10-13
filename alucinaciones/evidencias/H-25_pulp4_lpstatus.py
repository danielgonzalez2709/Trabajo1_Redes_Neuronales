"""Evidencia H-25: la API "clásica" de estado de PuLP (pulp.LpStatus[modelo.status]) no existe en PuLP 4.0.

Primera versión de src/part2/exact.py (13-oct-2026, escrita por Claude) usaba esa forma y fallaba en la primera prueba.
Ejecutar: .venv/Scripts/python.exe alucinaciones/evidencias/H-25_pulp4_lpstatus.py
"""
import pulp

print("PuLP", pulp.__version__)
print("¿existe pulp.LpStatus?", hasattr(pulp, "LpStatus"))
m = pulp.LpProblem("t", pulp.LpMinimize)
x = m.add_variable("x", lowBound=0)
m += x
m += x >= 1
stats = m.solve(pulp.HiGHS(msg=False))
print("¿existe modelo.status?", hasattr(m, "status"))
print("forma de PuLP 4: solve() devuelve", type(stats).__name__, "con status =", repr(stats.status))
