"""T1.5 - verificacion independiente del cazador (12-oct-2026). Solo lectura sobre el repo.
Ejecutar desde la raiz:  .venv/bin/python alucinaciones/evidencias/T1.5_verificacion.py
"""
import math, time, warnings
from decimal import Decimal as D, getcontext
import numpy as np
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.common.config import load_config
from src.part1.functions import get_function
from src.part1.pso import optimize, ParametrosPSO, generar_enjambre_inicial

print("== 1. chi y c con precision de 40 digitos (phi = 4.1) ==")
getcontext().prec = 40
phi = D("4.1")
chi = 2 / abs(2 - phi - (phi * phi - 4 * phi).sqrt())
c = chi * phi / 2
print("chi      =", chi)
print("chi*phi/2=", c)
print("chi - 0.7298   =", float(chi - D("0.7298")))
print("c   - 1.49618  =", float(c - D("1.49618")))
print("phi/2 (c de la forma 'constriccion sobre todo el lado derecho') =", phi / 2)
print("0.7298*2.05 =", 0.7298 * 2.05, " ; 0.729844*2.05 =", float(chi) * 2.05)

print("\n== 2. conteo y truncado (N=30, k=2n, budget=10000 n) ==")
cfg = load_config("configs/part1/base.yaml")
cfgo = {"pso": cfg["pso"], "record_frames": True}
for nombre in ("rosenbrock", "rastrigin"):
    for dim in (2, 3):
        f = get_function(nombre, dim)
        B = 10_000 * dim
        N = 30
        T_completas, resto = divmod(B, N)
        # Derivacion propia: n_f = N (T+1) con T iteraciones completas
        T = B // N - 1
        p = CountedProblem(f, k=2 * dim, budget=B)
        t0 = time.perf_counter()
        r = optimize(p, cfgo, make_rng(0, 0))
        dt = time.perf_counter() - t0
        nf = r["n_f"]
        fr = len(r["frames"]) if "frames" in r else None
        last = r["frames"][-1]["iter"] if "frames" in r else None
        print(f"{nombre} {dim}D B={B}: enjambres completos={B//N} (T={T}), truncadas={B%N}; "
              f"n_f={nf} frames={fr} ultimo_iter={last} n_grad={r['n_grad']} "
              f"f_best={r['f_best']:.3e} t={dt:.2f}s")

print("\n== 3. v_max por dimension ==")
for nombre in ("rosenbrock", "rastrigin"):
    f = get_function(nombre, 2)
    b = np.asarray(f.bounds, float)
    print(nombre, "ancho", b[:, 1] - b[:, 0], "-> 0.2*ancho", 0.2 * (b[:, 1] - b[:, 0]))

print("\n== 4. Lider con v=0 inicial: se mueve en la iteracion 1? ==")
f = get_function("rastrigin", 2)
n_quieto = 0
for s in range(30):
    cfgo2 = {"pso": dict(cfg["pso"], iteraciones=3), "record_frames": True}
    p = CountedProblem(f, k=4, budget=1e6)
    r = optimize(p, cfgo2, make_rng(0, s))
    fr = r["frames"]
    g0 = np.array(fr[0]["best"]); x0 = np.array(fr[0]["positions"]); x1 = np.array(fr[1]["positions"])
    # lider = particula cuya x(0) == g(0)
    i = int(np.argmin(np.abs(x0 - g0).sum(axis=1)))
    n_quieto += bool(np.array_equal(x0[i], x1[i]))
print("lideres que NO se mueven en la iteracion 1:", n_quieto, "/ 30")

print("\n== 5. 'PSO garantiza el optimo global': Rastrigin 2D/3D, 30 corridas ==")
for dim in (2, 3):
    f = get_function("rastrigin", dim)
    exitos = 0; fs = []
    for s in range(30):
        p = CountedProblem(f, k=2 * dim, budget=10_000 * dim)
        r = optimize(p, cfgo, make_rng(0, s))
        fs.append(r["f_best"]); exitos += (r["f_best"] - f.f_star <= 1e-4)
    print(f"rastrigin {dim}D: exitos {exitos}/30 ; f_best mediana={np.median(fs):.3f} max={max(fs):.3f}")

print("\n== 6. no derivable: |x| (no diferenciable en 0) ==")
class Abs:
    name = "abs"; dim = 2; bounds = np.array([[-5.0, 5.0]] * 2); f_star = 0.0
    x_star = np.zeros(2)
    def f(self, x): return float(np.abs(x).sum())
    __call__ = f
    def grad(self, x): raise RuntimeError("no se usa")
try:
    a = Abs()
    p = CountedProblem(a, k=4, budget=3000)
    r = optimize(p, {"pso": cfg["pso"], "record_frames": False}, make_rng(0, 0))
    print("f_best sobre sum|x| =", r["f_best"])
except Exception as e:
    print("no se pudo (interfaz de CountedProblem):", type(e).__name__, e)

print("\n== 7. inercia alta vs baja (Rastrigin 2D, c1=c2 fijos, 30 corridas, budget 20000) ==")
f = get_function("rastrigin", 2)
for w in (0.4, 0.7298, 0.9):
    b = dict(cfg["pso"], w=w)
    fs = []
    for s in range(30):
        p = CountedProblem(f, k=4, budget=20_000)
        r = optimize(p, {"pso": b, "record_frames": False}, make_rng(0, s))
        fs.append(r["f_best"])
    print(f"w={w}: f_best mediana={np.median(fs):.3f} media={np.mean(fs):.3f} exitos={sum(x<=1e-4 for x in fs)}/30")
