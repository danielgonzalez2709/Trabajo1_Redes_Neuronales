"""T1.5 - verificaciones complementarias del cazador (12-oct-2026). Solo lectura sobre el repo.
Ejecutar desde la raiz:  PYTHONPATH=. .venv/bin/python alucinaciones/evidencias/T1.5_verificacion2.py
"""
import math
import numpy as np
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.common.config import load_config
from src.part1.functions import get_function
from src.part1.pso import optimize, calcular_velocidades

cfg = load_config("configs/part1/base.yaml")
P = cfg["pso"]

print("== A. rho del sistema determinista (v,x) con chi=0.729844 y phi_t en (0, 4.1] ==")
phi = 4.1
chi = 2 / abs(2 - phi - math.sqrt(phi * phi - 4 * phi))
for phit in (0.5, 2.0, 3.9, 4.0, 4.1):
    M = chi * np.array([[1.0, -phit], [1.0, 1.0 - phit]])
    print(f"phi_t={phit}: |lambda| = {np.abs(np.linalg.eigvals(M))}")
print("=> el radio espectral llega a 1 exactamente en phi = 4.1 (derivacion propia, sin fuente)")

print("\n== B. forma constriccion chi*(v + c(p-x)...) con c=2.05  vs  forma inercia w=chi, c'=chi*2.05 ==")
rng = np.random.default_rng(0)
x, v, b = (rng.uniform(-5, 5, (30, 2)) for _ in range(3))
g = rng.uniform(-5, 5, 2); r1, r2 = rng.random((30, 2)), rng.random((30, 2))
constr = chi * (v + 2.05 * r1 * (b - x) + 2.05 * r2 * (g - x))
inerc = calcular_velocidades(x, v, b, g, chi, chi * 2.05, chi * 2.05, r1, r2)
print("max |dif| =", np.abs(constr - inerc).max())
con_c15 = calcular_velocidades(x, v, b, g, 1.0, 1.49618, 1.49618, r1, r2)
print("c1=c2=1.49618 con w=1 (SIN constriccion) vs constriccion C&K, max|dif| =", np.abs(constr - con_c15).max())

print("\n== C. Primera iteracion: termino cognitivo nulo (b = x) -> solo atraccion social ==")
f = get_function("rastrigin", 2)
viol = 0; total = 0
for s in range(30):
    p = CountedProblem(f, k=4, budget=1e6)
    r = optimize(p, {"pso": dict(P, iteraciones=1, vmax_frac=None), "record_frames": True}, make_rng(0, s))
    x0 = np.array(r["frames"][0]["positions"]); g0 = np.array(r["frames"][0]["best"]); x1 = np.array(r["frames"][1]["positions"])
    paso = x1 - x0; hacia = g0 - x0
    # con v=0, b=x: paso = c2*R2*(g-x), R2 en (0,1) -> paso/hacia en [0, c2] (sin recorte de frontera: comparar solo componentes dentro)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(hacia != 0, paso / hacia, 0.0)
    total += ratio.size
    viol += int(((ratio < -1e-12) | (ratio > P["c2"] + 1e-12)).sum())
print(f"componentes con paso/(g-x) fuera de [0, c2={P['c2']}]: {viol} / {total} (0 = paso puramente social)")

print("\n== D. El lider (x0 == g0) permanece quieto mientras g no cambie ==")
casos = 0; ok = 0
for s in range(30):
    p = CountedProblem(f, k=4, budget=1e6)
    r = optimize(p, {"pso": dict(P, iteraciones=40), "record_frames": True}, make_rng(0, s))
    fr = r["frames"]
    g0 = np.array(fr[0]["best"]); x0 = np.array(fr[0]["positions"])
    i = int(np.argmin(np.abs(x0 - g0).sum(axis=1)))
    t_g = next((t for t in range(1, len(fr)) if not np.array_equal(fr[t]["best"], fr[0]["best"])), None)
    t_x = next((t for t in range(1, len(fr)) if not np.array_equal(fr[t]["positions"][i], x0[i])), None)
    casos += 1
    # El lider debe moverse (si lo hace) en una iteracion t_x > t_g - 1 -> primera iteracion despues del cambio de g
    ok += int(t_x is None or (t_g is not None and t_x == t_g + 1) or (t_g is not None and t_x >= t_g))
print(f"{ok}/{casos} corridas: el lider no se mueve antes del primer cambio de g")

print("\n== E. Rosenbrock: exitos (f - f* <= 1e-4) en 30 corridas, budget 10000 n ==")
for dim in (2, 3):
    f = get_function("rosenbrock", dim)
    fs = []
    for s in range(30):
        p = CountedProblem(f, k=2 * dim, budget=10_000 * dim)
        fs.append(optimize(p, {"pso": P, "record_frames": False}, make_rng(0, s))["f_best"])
    print(f"rosenbrock {dim}D: exitos {sum(x <= 1e-4 for x in fs)}/30; max f_best = {max(fs):.3e}")
