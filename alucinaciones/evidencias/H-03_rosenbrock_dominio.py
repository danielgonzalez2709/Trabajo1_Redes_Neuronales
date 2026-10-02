import itertools
import numpy as np


def f(x):
    return np.sum(100 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2)


def g(x):
    n = len(x)
    gr = np.zeros(n)
    gr[:-1] += -400 * x[:-1] * (x[1:] - x[:-1] ** 2) - 2 * (1 - x[:-1])
    gr[1:] += 200 * (x[1:] - x[:-1] ** 2)
    return gr


def H(x):
    n = len(x)
    h = np.zeros((n, n))
    for i in range(n):
        if i < n - 1:
            h[i, i] += 1200 * x[i] ** 2 - 400 * x[i + 1] + 2
            h[i, i + 1] += -400 * x[i]
            h[i + 1, i] += -400 * x[i]
        if i > 0:
            h[i, i] += 200
    return h


rng = np.random.default_rng(0)
for n in (2, 3):
    x = rng.uniform(-2, 2, n)
    e = 1e-6
    num = np.array([(f(x + e * np.eye(n)[i]) - f(x - e * np.eye(n)[i])) / (2 * e) for i in range(n)])
    print(f"n={n} error rel. gradiente: {np.max(np.abs(num - g(x)) / np.maximum(1, np.abs(g(x)))):.1e}")
print("lambda_max(H) en x*=(1,1):", round(np.linalg.eigvalsh(H(np.ones(2))).max(), 2))

domains = {"[-2.048,2.048]": (-2.048, 2.048), "[-5,10]": (-5, 10), "[-30,30]": (-30, 30)}
Ls = {}
for n in (2, 3):
    for name, (lo, hi) in domains.items():
        X = rng.uniform(lo, hi, (20000, n))
        L = max(np.linalg.eigvalsh(H(x)).max() for x in X)
        L = max(L, max(np.linalg.eigvalsh(H(np.array(c))).max() for c in itertools.product([lo, hi], repeat=n)))
        Ls[(n, name)] = L
        print(f"n={n} {name:16s} L = max lambda_max(H) ~ {L:12.1f} -> eta <= 1/L = {1 / L:.2e}")


def gd(x0, eta, lo, hi, iters):
    x = x0.copy()
    for _ in range(iters):
        x = np.clip(x - eta * g(x), lo, hi)
    return f(x)


print("\nGD proyectado desde 30 inicios aleatorios, 5000 iteraciones (= presupuesto 10000n con k=2n)")
for n in (2, 3):
    for name, (lo, hi) in domains.items():
        X = rng.uniform(lo, hi, (30, n))
        for label, eta in (("1e-3", 1e-3), ("1/L", 1 / Ls[(n, name)])):
            res = np.array([gd(x0, eta, lo, hi, 5000) for x0 in X])
            print(f"n={n} {name:16s} eta={label:5s}({eta:.1e}): exito f<1e-4 = {np.mean(res < 1e-4):.2f} | "
                  f"mediana f = {np.median(res):.2e} | peor = {np.max(res):.2e}")
