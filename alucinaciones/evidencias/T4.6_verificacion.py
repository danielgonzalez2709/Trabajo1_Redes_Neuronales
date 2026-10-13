import copy, math, sys
sys.path.insert(0, ".")
import numpy as np
from src.common.config import load_config
from src.common.counter import CountedProblem, BudgetExhausted
from src.common.seeds import make_rng
from src.part1 import ea, pso, de
from src.part1.functions import get_function

cfg = load_config("configs/part1/base.yaml")
print("== bloques", cfg["ea"], cfg["pso"], cfg["de"], sep="\n")
p = ea.ParametrosEA.desde_config(cfg["ea"])
print("EA n_e,n_m,n_c:", p.n_elite, p.n_mutantes, p.n_cruzantes, "| 50*0.15 =", repr(50*0.15), "50*0.10 =", repr(50*0.10), "50*0.75 =", repr(50*0.75))

# constriccion
phi = 4.1
chi = 2/abs(2-phi-math.sqrt(phi*phi-4*phi))
print("chi =", chi, " chi*phi/2 =", chi*phi/2)

# --- 3: conteo con contadores de generaciones completas
def contar(mod, nombre):
    orig = getattr(mod, nombre); c = {"n": 0}
    def w(*a, **k):
        r = orig(*a, **k); c["n"] += 1; return r
    setattr(mod, nombre, w); return c, orig
print("== conteo (semilla 0 y 7)")
for fn in ("rosenbrock", "rastrigin"):
    for dim in (2, 3):
        for mod, nombre, m in ((ea, "_evaluar_generacion", "ea"), (pso, "actualizar_memoria_personal", "pso"), (de, "seleccionar_codiciosa", "de")):
            for seed in (0, 7):
                c, orig = contar(mod, nombre)
                prob = CountedProblem(get_function(fn, dim), 2*dim, 10000*dim)
                r = mod.optimize(prob, copy.deepcopy(cfg), make_rng(0, seed))
                setattr(mod, nombre, orig)
                T = c["n"]
                if m == "ea": base = 50 + 42*T
                else: base = 30*(T+1)
                fr = len(r["frames"]) if "frames" in r else None
                print(f"{fn:10s} {dim}D {m:3s} seed={seed} n_f={r['n_f']} n_grad={r['n_grad']} T={T} r={r['n_f']-base} frames={fr}")

# --- 5a: cruce en 2D
rng = np.random.default_rng(1)
pob = rng.uniform(-2, 2, size=(50, 2))
res = ea.cruzar_individuos(pob, 38, rng)
ok = True
for k in range(19):
    P = pob[res.indices_padre[k]]; Q = pob[res.indices_madre[k]]
    ok &= np.array_equal(res.hijos[2*k], [P[0], Q[1]]) and np.array_equal(res.hijos[2*k+1], [Q[0], P[1]])
print("== EA 2D: hijos = (p1,q2),(q1,p2) en las 19 parejas:", ok, "cortes:", set(res.puntos_corte.tolist()))
# pareja k = (cruzante k, cruzante k+m)
rng2 = np.random.default_rng(1); rng2.uniform(-2, 2, size=(50, 2)); idx = rng2.choice(50, size=38, replace=False)
print("pareja k = (cruzante_k, cruzante_{k+m}):", np.array_equal(idx[:19], res.indices_padre) and np.array_equal(idx[19:], res.indices_madre))
# 3D: cortes en {1,2}; valores de coordenada de hijos ya existen en la misma columna
pob3 = rng.uniform(-2, 2, size=(50, 3)); r3 = ea.cruzar_individuos(pob3, 38, rng)
print("3D cortes:", set(r3.puntos_corte.tolist()), "| valores hijos ya en la columna:", all(np.isin(r3.hijos[:, j], pob3[:, j]).all() for j in range(3)))

# --- 5b: sigma_j = 0
lim = np.array([[-5.12, 5.12]]*2)
for val in (0.1, 1/3, 0.995, 2.7182818, -4.52299366):
    pob = np.random.default_rng(3).uniform(-5, 5, size=(50, 2)); pob[:, 1] = val
    s = pob.std(axis=0, ddof=0)[1]
    cambios = 0; maxd = 0.0
    rg = np.random.default_rng(5)
    for _ in range(2000):
        m = ea.mutar_individuos(pob, 5, lim, rg)
        d = np.abs(m.mutantes[:, 1] - val).max(); maxd = max(maxd, d); cambios += int(d > 0)
        c = ea.cruzar_individuos(pob, 38, rg)
        assert (c.hijos[:, 1] == val).all()
    print(f"col constante {val!r}: std numpy = {s!r}; llamadas de mutación que cambian la columna: {cambios}/2000, max|delta| = {maxd!r}")

# --- 5c: PSO lider
print("== PSO lider / primer movimiento (rastrigin y rosenbrock 2D, 30 semillas)")
P = pso.ParametrosPSO.desde_config(cfg["pso"])
for fn in ("rastrigin", "rosenbrock"):
    f = get_function(fn, 2); lim = np.asarray(f.bounds, float)
    vmax = pso.calcular_velocidad_maxima(lim, P.fraccion_vmax)
    quieto1 = 0; quieto_hasta = 0; comp_total = 0; comp_social = 0; comp_clip = 0; comp_front = 0
    for seed in range(30):
        rng = make_rng(0, seed)
        e = pso.generar_enjambre_inicial(P.tamano_enjambre, lim, rng); x, v = e.posiciones, e.velocidades
        fx = np.array([f.f(xi) for xi in x]); b = x.copy(); fb = fx.copy()
        g = pso.actualizar_mejor_global(b, fb); lider = g.indice; x_lider0 = x[lider].copy()
        fiel = True
        for it in range(1, 300):
            R1 = rng.random(x.shape); R2 = rng.random(x.shape)
            vs = pso.calcular_velocidades(x, v, b, g.posicion, P.inercia, P.coef_cognitivo, P.coef_social, R1, R2)
            vl = pso.limitar_velocidades(vs, vmax)
            fr = pso.aplicar_frontera(x + vl, vl, lim)
            if it == 1:
                social = P.coef_social * R2 * (g.posicion - x)
                comp_total += x.size
                comp_social += int(np.sum(np.isclose(fr.posiciones - x, social, rtol=0, atol=1e-12)))
                comp_clip += int(np.sum(vs != vl)); comp_front += int(fr.salieron.sum())
                assert np.array_equal(vs, social) or np.allclose(vs, social, rtol=0, atol=0)
                if np.array_equal(fr.posiciones[lider], x_lider0): quieto1 += 1
            x, v = fr.posiciones, fr.velocidades
            fx = np.array([f.f(xi) for xi in x])
            m = pso.actualizar_memoria_personal(x, fx, b, fb); b, fb = m.mejores_personales, m.aptitudes_personales
            g2 = pso.actualizar_mejor_global(b, fb)
            if g2.indice != lider or not np.array_equal(g2.posicion, x_lider0):
                break
            g = g2
            if not np.array_equal(x[lider], x_lider0): fiel = False
        quieto_hasta += int(fiel)
    print(f"{fn}: lider quieto en iter 1: {quieto1}/30; quieto hasta que g cambia: {quieto_hasta}/30; iter 1: desplazamiento == c2*R2*(g-x) en {comp_social}/{comp_total} componentes; recortadas por v_max: {comp_clip}; por frontera: {comp_front}")

# --- DE: hijos dentro del dominio, consumo del rng, sincronía
print("== DE")
f = get_function("rastrigin", 2); lim = np.asarray(f.bounds, float)
rng = np.random.default_rng(0); pob = rng.uniform(lim[:, 0], lim[:, 1], size=(30, 2))
fuera = 0; nre = 0
for _ in range(2000):
    ip = de.sortear_padres(30, rng)
    assert all(len({i, *ip[i]}) == 4 for i in range(30))
    mu = de.mutar_diferencial(pob, ip, 0.7)
    re = de.reiniciar_fuera_de_dominio(mu, lim, rng); nre += int(re.reiniciadas.sum())
    cr = de.cruzar_binomial(pob, re.mutantes, 0.9, rng)
    fuera += int(((cr.hijos < lim[:, 0]) | (cr.hijos > lim[:, 1])).sum())
    assert cr.de_mutante.any(axis=1).all()
print("componentes de hijos fuera del dominio:", fuera, "| reiniciadas:", nre)
# limite exacto se conserva
mu = np.array([[lim[0, 0], lim[1, 1]], [lim[0, 0]-1e-9, 0.0]])
print("valor igual al limite se conserva:", de.reiniciar_fuera_de_dominio(mu, lim, np.random.default_rng(0)).reiniciadas.tolist())
# consumo independiente de datos
a = np.random.default_rng(9); bq = np.random.default_rng(9)
de.reiniciar_fuera_de_dominio(np.zeros((30, 2)), lim, a); de.reiniciar_fuera_de_dominio(np.full((30, 2), 99.0), lim, bq)
print("consumo del rng del reinicio independiente de los datos:", a.random() == bq.random())
# poblacion colapsada: mutante == x_r1
col = np.tile([0.995, 0.0], (30, 1)); ip = de.sortear_padres(30, a)
print("poblacion colapsada: mutante == x_r1:", np.array_equal(de.mutar_diferencial(col, ip, 0.7), col[ip[:, 0]]))
