"""Verificación independiente de las cifras del blog de la Parte 1 (T4.6, cazador de alucinaciones).

Uso, desde la raíz del repositorio (solo lee; no escribe nada en el repositorio):

    .venv/bin/python alucinaciones/evidencias/T4.6-parte1_verificacion.py > alucinaciones/evidencias/T4.6-parte1_verificacion.txt

Recalcula desde las fuentes primarias (JSON por corrida, summary.json, seleccion.json, ensayos_*.json,
gif_trayectorias.json, eta_deslizador.json, base.yaml, tuned.yaml) y compara con las tablas del blog.
No lee alucinaciones/evidencias/T4.6-parte1_cifras.txt.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
D = RAIZ / "results" / "data"
FUNCS, DIMS, METODOS = ["rosenbrock", "rastrigin"], [2, 3], ["gdfijo", "gdarmijo", "ea", "pso", "de"]
UMBRALES = [1e-2, 1e-4, 1e-6]
problemas = []  # discrepancias encontradas


def titulo(t):
    print("\n" + "=" * 100 + "\n" + t + "\n" + "=" * 100)


def cargar_runs(carpeta):
    runs = {}
    for ruta in glob.glob(str(carpeta / "*.json")):
        r = json.load(open(ruta))
        runs.setdefault((r["func"], r["dim"], r["method"]), []).append(r)
    for v in runs.values():
        v.sort(key=lambda r: r["seed"])
    return runs


def evals_exito(r, umbral):
    """Primer eval_equiv del historial con f_best <= umbral (f* = 0); None si no hay."""
    for h in r["result"]["history"]:
        if h["f_best"] <= umbral:
            return h["eval_equiv"]
    return None


def resumen(rs):
    f = [r["result"]["f_best"] for r in rs]
    out = {"n": len(rs), "media": st.fmean(f), "desv": st.stdev(f), "mediana": st.median(f),
           "mejor": min(f), "peor": max(f),
           "n_f": st.fmean(r["result"]["n_f"] for r in rs),
           "n_grad": st.fmean(r["result"]["n_grad"] for r in rs),
           "eval": st.fmean(r["result"]["eval_equiv"] for r in rs)}
    for u in UMBRALES:
        ex = [evals_exito(r, u) for r in rs if r["result"]["f_best"] <= u]
        out[f"ok{u:g}"] = len(ex)
        out[f"ev{u:g}"] = st.fmean(ex) if ex else None
    return out


def e(x):
    return "—" if x is None else f"{x:.3e}"


def ent(x):
    """Entero con las mitades hacia arriba (984.5 -> 985), que es el redondeo que usa el blog."""
    return "—" if x is None else str(math.floor(x + 0.5))


def pct(n, tot=30, con_frac=True):
    return f"{100 * n / tot:.1f} % ({n}/{tot})" if con_frac else f"{100 * n / tot:.1f} %"


def tablas_blog(ruta):
    """{id: [filas (lista de celdas)]} de los bloques '::: tabla id' de una sección."""
    tablas, actual = {}, None
    for linea in open(ruta, encoding="utf-8"):
        m = re.match(r"::: tabla (\S+)", linea)
        if m:
            actual = m.group(1)
            tablas[actual] = []
        elif linea.startswith(":::"):
            actual = None
        elif actual and linea.startswith("|") and not linea.startswith("|---"):
            tablas[actual].append([c.strip() for c in linea.strip().strip("|").split("|")])
    return {k: v[1:] for k, v in tablas.items()}  # sin encabezado


def comparar(nombre, esperado, blog):
    ok = esperado == blog
    if not ok:
        problemas.append((nombre, esperado, blog))
    print(("OK   " if ok else "DIF  ") + nombre + ("" if ok else f"\n     calculado: {esperado}\n     blog:      {blog}"))


# ---------------------------------------------------------------------------------------------
titulo("1. Estadísticas recalculadas desde los JSON por corrida y contraste con summary.json")
conjuntos = {"defecto": D / "part1" / "runs", "defecto_k1": D / "part1" / "k1" / "runs",
             "afinado": D / "part1_tuned" / "runs", "afinado_k1": D / "part1_tuned" / "k1" / "runs"}
R = {n: cargar_runs(c) for n, c in conjuntos.items()}
S = {n: {k: resumen(v) for k, v in rs.items()} for n, rs in R.items()}
for n, rs in R.items():
    print(n, "configuraciones:", len(rs), "corridas:", sum(len(v) for v in rs.values()),
          "semillas distintas por config:", sorted({tuple(r["seed"] for r in v) == tuple(range(30)) for v in rs.values()}))

summ = {"defecto": json.load(open(D / "part1" / "summary.json")),
        "afinado": json.load(open(D / "part1_tuned" / "summary.json")),
        "eta_1l": json.load(open(D / "part1_eta_1l" / "summary.json"))}
maxdif = 0.0
difs = []  # campos en los que los JSON por corrida de este equipo no reproducen summary.json
for nombre, bloque, conj in [("defecto", "configuraciones", "defecto"), ("defecto", "sensibilidad_k1", "defecto_k1"),
                             ("afinado", "configuraciones", "afinado"), ("afinado", "sensibilidad_k1", "afinado_k1")]:
    for c in summ[nombre][bloque]:
        clave = (c["func"], c["dim"], c["method"])
        if clave not in S[conj]:
            continue  # ea/pso/de en sensibilidad_k1: reutilizan la fila principal
        mio = S[conj][clave]
        for campo in ["media", "desv", "mediana", "mejor", "peor"]:
            a, b = mio[campo], c["f_final"][campo]
            d = abs(a - b) / max(abs(b), 1e-300) if b else abs(a)
            maxdif = max(maxdif, d)
            if d > 1e-9:
                difs.append((conj, clave, "f_final." + campo, a, b))
        for u in UMBRALES:
            ku = f"{u:.0e}"
            if abs(mio[f"ok{u:g}"] / 30 - c["tasa_exito"][ku]) > 1e-12:
                difs.append((conj, clave, "tasa " + ku, mio[f"ok{u:g}"] / 30, c["tasa_exito"][ku]))
            a, b = mio[f"ev{u:g}"], c["evals_hasta_exito_medio"][ku]
            if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-6):
                difs.append((conj, clave, "evals_hasta_exito " + ku, a, b))
        for campo, cs in [("n_grad", "n_grad_medio"), ("n_f", "n_f_medio"), ("eval", "eval_equiv_medio")]:
            if abs(mio[campo] - c[cs]) > 1e-9:
                difs.append((conj, clave, cs, mio[campo], c[cs]))
print("campos de summary.json que NO se reproducen con los JSON por corrida de este equipo:", len(difs))
for dfi in difs:
    print("   ", dfi[0], dfi[1], dfi[2], "corridas locales =", dfi[3], "| summary.json =", dfi[4])
print("dif. relativa máx. en las estadísticas de f_final (defecto y afinado; principal y k1):", f"{maxdif:.2e}")
print("desviación: st.stdev (divisor n-1), igual que summary.json")

# ---------------------------------------------------------------------------------------------
titulo("2. Tablas de la sección 04 frente al recálculo")
T04 = tablas_blog(RAIZ / "blog/secciones/04-parte1-resultados.md")
T03 = tablas_blog(RAIZ / "blog/secciones/03-parte1-metodologia.md")
for func in FUNCS:
    filas = []
    for dim in DIMS:
        for m in METODOS:
            s = S["defecto"][(func, dim, m)]
            filas.append([f"{dim}D", m, e(s["media"]), e(s["desv"]), e(s["mediana"]), e(s["mejor"]), e(s["peor"]),
                          pct(s["ok0.0001"]), ent(s["ev0.0001"])])
    for mio, blog in zip(filas, T04[f"resultados-{func}"], strict=True):
        comparar(f"resultados-{func} {mio[0]} {mio[1]}", mio, blog)
filas = []
for func in FUNCS:
    for dim in DIMS:
        for m in METODOS:
            s = S["defecto"][(func, dim, m)]
            filas.append([func.capitalize(), f"{dim}D", m] + [pct(s[f"ok{u:g}"]) for u in UMBRALES])
for mio, blog in zip(filas, T04["exito-umbrales"], strict=True):
    comparar("exito-umbrales " + " ".join(mio[:3]), mio, blog)
filas = []
for func in FUNCS:
    for dim in DIMS:
        for m in ["gdfijo", "gdarmijo"]:
            a, b = S["defecto"][(func, dim, m)], S["defecto_k1"][(func, dim, m)]
            filas.append([func.capitalize(), f"{dim}D", m, f"{e(a['mediana'])} → {e(b['mediana'])}",
                          f"{pct(a['ok0.0001'])} → {pct(b['ok0.0001'])}", f"{a['n_grad']:.1f} → {b['n_grad']:.1f}",
                          f"{ent(a['ev0.0001'])} → {ent(b['ev0.0001'])}"])
for mio, blog in zip(filas, T04["sensibilidad-k1"], strict=True):
    comparar("sensibilidad-k1 " + " ".join(mio[:3]), mio, blog)
for func in FUNCS:
    filas = []
    for dim in DIMS:
        for m in METODOS:
            a, b = S["defecto"][(func, dim, m)], S["afinado"][(func, dim, m)]
            filas.append([f"{dim}D", m, f"{e(a['mediana'])} → {e(b['mediana'])}",
                          f"{pct(a['ok0.0001'], con_frac=False)} → {pct(b['ok0.0001'], con_frac=False)}",
                          f"{ent(a['ev0.0001'])} → {ent(b['ev0.0001'])}"])
    for mio, blog in zip(filas, T04[f"hpo-{func}"], strict=True):
        comparar(f"hpo-{func} {mio[0]} {mio[1]}", mio, blog)
print("\nRedondeos .5 en 'evaluaciones hasta el éxito' (valor exacto):")
for conj in ["defecto", "defecto_k1", "afinado"]:
    for k, s in sorted(S[conj].items()):
        if s["ev0.0001"] is not None:
            print(f"  {conj:11s} {k}: {s['ev0.0001']:.4f}  (n exitosas {s['ok0.0001']})")

titulo("2b. Tabla sensibilidad-eta (03) frente a summary.json de part1 y part1_eta_1l")
filas = []
for dim in DIMS:
    for eta, src in [("`1e-3`", summ["defecto"]), ("`1.5e-4`", summ["eta_1l"])]:
        c = next(c for c in src["configuraciones"] if (c["func"], c["dim"], c["method"]) == ("rosenbrock", dim, "gdfijo"))
        filas.append([f"{dim}D", eta, e(c["f_final"]["media"]), e(c["f_final"]["mediana"]),
                      f"{100 * c['tasa_exito']['1e-02']:.1f} %", f"{100 * c['tasa_exito']['1e-04']:.1f} %"])
        print("   ", dim, eta, "mediana", c["f_final"]["mediana"], "n_grad medio", c["n_grad_medio"],
              "éxito 1e-2", c["tasa_exito"]["1e-02"] * 30, "éxito 1e-4", c["tasa_exito"]["1e-04"] * 30)
for mio, blog in zip(filas, T03["sensibilidad-eta"], strict=True):
    comparar("sensibilidad-eta " + " ".join(mio[:2]), mio, blog)
print("config de part1_eta_1l:", summ["eta_1l"]["meta"])

# ---------------------------------------------------------------------------------------------
titulo("3. Motivo de parada de los GD (defecto, k = 2n y k = 1)")


def motivo(r):
    """'tolerancia' si quedaba presupuesto para otro gradiente al terminar; si no, 'presupuesto'.

    Paso fijo: n_f = 0, así que quedan budget − k·n_grad; si eso es >= k la corrida no paró por presupuesto.
    Armijo: si queda >= max(k, 1) no pudo ser rechazo del contador (un ensayo cuesta 1, un gradiente k).
    """
    resto = r["budget"] - r["result"]["eval_equiv"]
    return "tolerancia" if resto >= max(r["k"], 1.0) else "presupuesto"


for conj in ["defecto", "defecto_k1", "afinado", "afinado_k1"]:
    for func in FUNCS:
        for dim in DIMS:
            for m in ["gdfijo", "gdarmijo"]:
                rs = R[conj][(func, dim, m)]
                c = Counter(motivo(r) for r in rs)
                ng = [r["result"]["n_grad"] for r in rs]
                print(f"{conj:11s} {func:10s} {dim}D {m:9s} {dict(c)}  n_grad min/media/máx = {min(ng)}/{st.fmean(ng):.2f}/{max(ng)}"
                      f"  eval_equiv media = {st.fmean(r['result']['eval_equiv'] for r in rs):.2f}")

titulo("3b. Paso fijo en Rastrigin: reejecución en memoria, norma del gradiente en el punto de parada")
from src.common.config import load_config  # noqa: E402
from src.common.counter import CountedProblem  # noqa: E402
from src.common.seeds import make_rng  # noqa: E402
from src.part1.corrida import ejecutar_corrida  # noqa: E402
from src.part1.functions import get_function  # noqa: E402

cfg = load_config(str(RAIZ / "configs/part1/base.yaml"))
for dim in DIMS:
    normas, iguales, dist_min = [], 0, []
    for seed in range(30):
        f = get_function("rastrigin", dim)
        lo, hi = f.bounds[:, 0], f.bounds[:, 1]
        x = make_rng(0, seed).uniform(lo, hi)
        p = CountedProblem(f, 2 * dim, 10000 * dim)
        n = 0
        while True:  # reimplementación directa de la iteración de paso fijo (sin usar gd.py)
            g = p.grad(x)
            n += 1
            if np.linalg.norm(g) < cfg["gd"]["tol_grad"]:
                break
            x = np.clip(x - cfg["gd"]["eta"]["rastrigin"] * g, lo, hi)
        normas.append(float(np.linalg.norm(g)))
        guardado = R["defecto"][("rastrigin", dim, "gdfijo")][seed]["result"]
        iguales += int(n == guardado["n_grad"])
        # ¿el punto final es un mínimo local de la rejilla? distancia al entero más cercano por coordenada
        dist_min.append(float(np.max(np.abs(x - np.round(x)))))
    print(f"rastrigin {dim}D gdfijo: ||grad|| final máx = {max(normas):.2e} (< tol 1e-8 en {sum(v < 1e-8 for v in normas)}/30);"
          f" n_grad igual al JSON guardado en {iguales}/30; |x - round(x)| máx = {max(dist_min):.4f}")
r0 = ejecutar_corrida("rastrigin", 2, "gdfijo", 0, 0, cfg)["result"]
print("ejecutar_corrida(rastrigin, 2D, gdfijo, semilla 0): n_grad", r0["n_grad"], "f_best", r0["f_best"], "eval_equiv", r0["eval_equiv"])

titulo("3c. Niveles de f final en Rastrigin (paso fijo): valores distintos y múltiplos de 0.995")
for conj in ["defecto"]:
    for m in ["gdfijo", "gdarmijo", "ea", "pso", "de"]:
        for dim in DIMS:
            fs = [r["result"]["f_best"] for r in R[conj][("rastrigin", dim, m)]]
            for nd in (3, 4, 6):
                pass
            d3 = sorted({round(v, 3) for v in fs})
            d6 = sorted({round(v, 6) for v in fs})
            coc = [v / 0.995 for v in d3]
            desv = max(abs(c - round(c)) for c in coc) if d3 else 0
            print(f"rastrigin {dim}D {m:9s}: distintos (3 dec.) = {len(d3)}, (6 dec.) = {len(d6)}, exactos = {len(set(fs))};"
                  f" min = {min(fs):.4f}, máx = {max(fs):.4f}; máx |v/0.995 − entero| = {desv:.4f}")
            if m == "gdfijo":
                print("    valores (3 dec.):", d3)
                print("    v/0.995:", [round(c, 3) for c in coc])
                # f en mínimos locales exactos: suma de f1d(m_i) con m_i el mínimo local 1D cercano al entero i
            if m in ("ea", "pso", "de"):
                print("    fallidas (f > 1e-4):", sorted(round(v, 4) for v in fs if v > 1e-4))
# mínimos locales 1D de Rastrigin (Newton sobre g(x) = 2x + 20π sin(2πx)) y su valor de f
print("mínimos locales 1D de Rastrigin: i, x_i, f1d(x_i), f1d/0.995, f1d/i²")
for i in range(1, 6):
    x = float(i)
    for _ in range(50):
        x -= (2 * x + 20 * math.pi * math.sin(2 * math.pi * x)) / (2 + 40 * math.pi ** 2 * math.cos(2 * math.pi * x))
    f1 = x * x + 10 - 10 * math.cos(2 * math.pi * x)
    print(f"   {i}  {x:.6f}  {f1:.6f}  {f1 / 0.995:.4f}  {f1 / i ** 2:.6f}")

# ---------------------------------------------------------------------------------------------
titulo("4. Armijo en Rastrigin: corridas que agotan el presupuesto y última mejora")
for conj in ["defecto", "defecto_k1"]:
    for dim in DIMS:
        rs = R[conj][("rastrigin", dim, "gdarmijo")]
        agota = sum(motivo(r) == "presupuesto" for r in rs)
        ult = [r["result"]["history"][-1]["eval_equiv"] for r in rs]
        ult_ag = [r["result"]["history"][-1]["eval_equiv"] for r in rs if motivo(r) == "presupuesto"]
        print(f"{conj} rastrigin {dim}D gdarmijo: agotan presupuesto {agota}/30; última mejora (eval_equiv del último punto de history):"
              f" mediana = {st.median(ult)}, máx = {max(ult)}; mediana solo entre las que agotan = {st.median(ult_ag)};"
              f" f=0 exacto en {sum(r['result']['f_best'] == 0 for r in rs)} corridas")
print("history solo registra mejoras estrictas de f_best:",
      all(a["f_best"] > b["f_best"] for rs in R["defecto"].values() for r in rs
          for a, b in zip(r["result"]["history"], r["result"]["history"][1:])))

titulo("4b. Armijo en Rosenbrock: reparto del presupuesto (n_f frente a k·n_grad)")
for conj in ["defecto", "defecto_k1"]:
    for dim in DIMS:
        s = S[conj][("rosenbrock", dim, "gdarmijo")]
        k = 2 * dim if conj == "defecto" else 1
        print(f"{conj} rosenbrock {dim}D gdarmijo: n_f medio {s['n_f']:.1f}, n_grad medio {s['n_grad']:.1f}, k·n_grad = {k * s['n_grad']:.1f},"
              f" fracción en f = {s['n_f'] / s['eval']:.3f}")

# ---------------------------------------------------------------------------------------------
titulo("5. gif_trayectorias.json (una corrida, semilla 0, 2D)")
gif = json.load(open(D / "part1" / "gif_trayectorias.json"))
print("meta:", gif["meta"])
for func in FUNCS:
    b = gif["gd"][func]
    print(func, "fotogramas:", len(b["iteraciones"]))
    for m, v in b["metodos"].items():
        print(f"   {m}: n_iter {v['n_iter']}, n_grad {v['n_grad']}, n_f {v['n_f']}, x0 {np.round(v['x'][0], 4).tolist()}, f0 {v['f'][0]:.4f},"
              f" x_fin {np.round(v['x'][-1], 4).tolist()}, f_fin {v['f'][-1]:.4e}, f_best {v['f_best']:.4e}")
        guard = R["defecto"][(func, 2, m)][0]["result"]
        print(f"      JSON de la corrida semilla 0: n_grad {guard['n_grad']}, n_f {guard['n_f']}, f_best {guard['f_best']:.4e},"
              f" eval_equiv {guard['eval_equiv']}")
p = gif["pso"]["rastrigin"]
print("pso rastrigin: n_iter", p["n_iter"], "n_f", p["n_f"], "f_best", p["f_best"], "fotogramas", len(p["iteraciones"]),
      "partículas", len(p["enjambre"][0]))
print("   f_mejor[0], [1]:", p["f_mejor"][0], p["f_mejor"][1], "iteraciones[0:3]:", p["iteraciones"][:3])
i = next(j for j, v in enumerate(p["f_mejor"]) if v <= 1e-4)
print("   primer fotograma con f_mejor <= 1e-4: índice", i, "iteración", p["iteraciones"][i], "valor", p["f_mejor"][i],
      "| anterior: iteración", p["iteraciones"][i - 1], "valor", p["f_mejor"][i - 1])
gp = R["defecto"][("rastrigin", 2, "pso")][0]["result"]
print("   corrida guardada semilla 0: n_f", gp["n_f"], "f_best", gp["f_best"], "frames", len(gp["frames"]),
      "evals hasta 1e-4:", evals_exito(R["defecto"][("rastrigin", 2, "pso")][0], 1e-4))
pos0 = np.array(gp["frames"][0]["positions"])
print("   posiciones iniciales: min", pos0.min().round(3), "máx", pos0.max().round(3), "(dominio ±5.12)")

titulo("6. eta_deslizador.json")
es = json.load(open(D / "part1" / "eta_deslizador.json"))
print("meta:", es["meta"])
f = get_function("rosenbrock", 2)
_x0 = es["meta"]["x0"]
print("f(x0) =", 100 * (_x0[1] - _x0[0] ** 2) ** 2 + (1 - _x0[0]) ** 2)
for x in es["etas"]:
    ult = np.array(x["puntos"][-1])
    f_ult = 100 * (ult[1] - ult[0] ** 2) ** 2 + (1 - ult[0]) ** 2
    print(f"   eta {x['eta']:.4e} marca {str(x['marca']):8s} f_best {x['f_best']:.4e} n_grad {x['n_grad']} f(último punto) {f_ult:.4e}")
print("n.º de valores de eta:", len(es["etas"]), "| 2/lambda_max en x* =", 2 / 1001.6)
print("eta por encima de 1e-3 con f_best < 1e-3:", [f"{x['eta']:.4e}" for x in es["etas"] if x["eta"] > 1e-3 and x["f_best"] < 1e-3])

# ---------------------------------------------------------------------------------------------
titulo("7. HPO: selección, puntajes, rangos y valores afinados")
sel = json.load(open(D / "part1_hpo" / "seleccion.json"))
sel1 = json.load(open(D / "part1_hpo" / "regla_v1" / "seleccion.json"))
print("meta:", sel["meta"])
base = yaml.safe_load(open(RAIZ / "configs/part1/base.yaml"))
tuned = yaml.safe_load(open(RAIZ / "configs/part1/tuned.yaml"))
print("tuned.yaml:", tuned)
ens = {}
for u, u1 in zip(sel["unidades"], sel1["unidades"]):
    d = json.load(open(D / "part1_hpo" / f"ensayos_{u['unidad']}.json"))
    ens[u["unidad"]] = d
    # recálculo independiente de la regla R6: mediana recortada, rangos promedio, puntaje
    celdas = list(d["ensayos"][0]["por_celda"])
    med = {c: [st.median(max(v, 1e-6) for v in t["por_celda"][c]["f_best"]) for t in d["ensayos"]] for c in celdas}

    def rangos(vals):
        orden = sorted(vals)
        return [(orden.index(v) + 1 + len(vals) - orden[::-1].index(v)) / 2 for v in vals]

    rg = {c: rangos(med[c]) for c in celdas}
    punt = [st.fmean(rg[c][i] for c in celdas) for i in range(len(d["ensayos"]))]
    mejor = min(punt)
    cand = [i for i, v in enumerate(punt) if v == mejor]
    gan = 0 if punt[0] <= mejor else None
    print(f"\n{u['unidad']}: ensayos {len(d['ensayos'])}, semillas {len(d['ensayos'][0]['por_celda'][celdas[0]]['f_best'])}, celdas {celdas}")
    print(f"   ganador seleccion.json = {u['ganador']} (regla_v1: {u1['ganador']}); puntaje defecto = {punt[0]} | mejor puntaje = {mejor} en ensayos {cand}"
          f" | recálculo: {'gana el defecto' if gan == 0 else 'retadores ' + str(cand)}")
    print("   guardado: puntaje_defecto", u["puntaje_defecto"]["rango_medio"], "puntaje_ganador", u["puntaje_ganador"]["rango_medio"])
    assert abs(punt[0] - u["puntaje_defecto"]["rango_medio"]) < 1e-12
    assert abs(punt[u["ganador"]] - u["puntaje_ganador"]["rango_medio"]) < 1e-12
    for i in sorted({0, u["ganador"], u1["ganador"]}):
        t = d["ensayos"][i]
        ex = sum(t["puntaje"]["exitos_1e-06_por_celda"].values())
        tot = sum(t["puntaje"]["semillas_por_celda"].values())
        print(f"   ensayo {i}: rangos {[rg[c][i] for c in celdas]} medianas rec. {[float(f'{med[c][i]:.4g}') for c in celdas]}"
              f" puntaje {punt[i]} éxitos 1e-6 {ex}/{tot}")
        print(f"      parámetros: { {k: float(f'{v:.4g}') for k, v in t['parametros'].items()} }")
    print("   elegido:", u["elegido"])
print("\ncorridas de ajuste:", {u["unidad"]: u["corridas_de_ajuste"] for u in sel["unidades"]}, "total", sel["meta"]["corridas_de_ajuste_total"])

titulo("7b. Medianas de ajuste del GD con Armijo (5 semillas) citadas en la 08")
d = ens["gdarmijo"]
for i in (0, 10):
    print(f"   ensayo {i}:", {c: st.median(d["ensayos"][i]["por_celda"][c]["f_best"]) for c in d["ensayos"][i]["por_celda"]})

titulo("7c. Regla v1: tasas con las semillas de reporte (regla_v1/comparacion.csv)")
for fila in csv.DictReader(open(D / "part1_hpo" / "regla_v1" / "comparacion.csv")):
    if fila["method"] in ("pso", "de"):
        print(f"   {fila['func']} {fila['dim']}D {fila['method']}: 1e-4 {float(fila['tasa_exito_1e-04_defecto']) * 100:.1f} → "
              f"{float(fila['tasa_exito_1e-04_afinado']) * 100:.1f} %; 1e-6 {float(fila['tasa_exito_1e-06_defecto']) * 100:.1f} → "
              f"{float(fila['tasa_exito_1e-06_afinado']) * 100:.1f} %")

titulo("7d. Valores afinados en el borde de los intervalos (R7)")
for metodo, esp in base["hpo"]["espacios"].items():
    for nombre, e_ in esp.items():
        for u in sel["unidades"]:
            for ruta, v in u["elegido"].items():
                if ruta == e_["ruta"] and u["metodo"] == metodo:
                    print(f"   {u['unidad']} {ruta}: {v:.4g} en [{e_['min']}, {e_['max']}] defecto {u['defecto'][ruta]}")

# ---------------------------------------------------------------------------------------------
titulo("8. EA: tamaños de grupo y conteos; PSO y DE: conteos")


def par(n):
    return n + n % 2


for N, fe, fm, fc in [(50, 0.15, 0.10, 0.75), (tuned["ea"]["N"], tuned["ea"]["frac_e"], tuned["ea"]["frac_m"], tuned["ea"]["frac_c"])]:
    ne, nm = round(N * fe), int(N * fm)
    nc = max(par(int(N * fc)), par(N - ne - nm))
    print(f"N={N}: n_e={ne} n_m={nm} floor(N f_c)={int(N * fc)} par={par(int(N * fc))} relleno={par(N - ne - nm)} n_c={nc}"
          f" fracción efectiva={nc / N:.3f} suma={ne + nm + nc} evals/gen={N - ne}")
    for presupuesto in (20000, 30000):
        T, r = divmod(presupuesto - N, N - ne)
        print(f"     presupuesto {presupuesto}: T={T} r={r}")
from src.part1 import ea as _ea  # noqa: E402
print("funciones de ea.py con 'tam' o 'grupo':", [n for n in dir(_ea) if "tama" in n.lower() or "grupo" in n.lower()])
for presupuesto in (20000, 30000):
    T, r = divmod(presupuesto - 30, 30)
    print(f"PSO/DE N=30 presupuesto {presupuesto}: T={T} r={r}")
for clave in [("rosenbrock", 2, "ea"), ("rosenbrock", 3, "ea"), ("rosenbrock", 2, "pso"), ("rosenbrock", 3, "pso"), ("rosenbrock", 2, "de"), ("rosenbrock", 3, "de")]:
    rs = R["defecto"][clave]
    print("   ", clave, "n_f:", sorted({r["result"]["n_f"] for r in rs}), "frames:", sorted({len(r["result"].get("frames", [])) for r in rs}))
for clave in [("rosenbrock", 2, "ea"), ("rosenbrock", 3, "ea")]:
    print("   afinado", clave, "n_f:", sorted({r["result"]["n_f"] for r in R["afinado"][clave]}))

# ---------------------------------------------------------------------------------------------
titulo("9. Constantes: L, Hessianas, 1/L, constricción")
print("Rastrigin L = 2 + 40π² =", 2 + 40 * math.pi ** 2, "1/L =", 1 / (2 + 40 * math.pi ** 2))
H = np.array([[802.0, -400.0], [-400.0, 200.0]])
lam = np.linalg.eigvalsh(H)
print("Rosenbrock, Hessiana en (1,1): valores propios", lam, "2/λmax =", 2 / lam[-1], "condición =", lam[-1] / lam[0])


def hess_ros(x):
    n = len(x)
    Hm = np.zeros((n, n))
    for i in range(n - 1):
        Hm[i, i] += 1200 * x[i] ** 2 - 400 * x[i + 1] + 2
        Hm[i, i + 1] += -400 * x[i]
        Hm[i + 1, i] += -400 * x[i]
        Hm[i + 1, i + 1] += 200
    return Hm


for n in (2, 3):
    g = np.linspace(-2.048, 2.048, 65 if n == 2 else 33)
    mejor = 0
    for pt in np.array(np.meshgrid(*[g] * n)).reshape(n, -1).T:
        mejor = max(mejor, np.abs(np.linalg.eigvalsh(hess_ros(pt))).max())
    print(f"Rosenbrock {n}D: L (máx |λ| en rejilla que incluye las esquinas) = {mejor:.2f}; 1/L = {1 / mejor:.4e}; 1.5e-4 / (1/L) − 1 = {1.5e-4 * mejor - 1:+.4f}")
phi = 4.1
chi = 2 / abs(2 - phi - math.sqrt(phi * phi - 4 * phi))
print("constricción φ=4.1: χ =", chi, "χφ/2 =", chi * phi / 2)
print("resolución 10nε (n=2):", 20 * 2.22e-16, " sqrt(2λ·10nε) con λ=396.8:", math.sqrt(2 * 396.8 * 20 * 2.22e-16))
print("base.yaml gd:", base["gd"], "| ea:", base["ea"], "| pso:", base["pso"], "| de:", base["de"])
print("base.yaml hpo (sin espacios):", {k: v for k, v in base["hpo"].items() if k != "espacios"})

# ---------------------------------------------------------------------------------------------
titulo("10. Sensibilidad k = 1 de la versión afinada")
for func in FUNCS:
    for dim in DIMS:
        for m in ["gdfijo", "gdarmijo"]:
            a, b = S["afinado"][(func, dim, m)], S["afinado_k1"][(func, dim, m)]
            print(f"   {func} {dim}D {m}: éxito 1e-4 {a['ok0.0001']} → {b['ok0.0001']}; mediana {e(a['mediana'])} → {e(b['mediana'])};"
                  f" mejor {e(a['mejor'])} → {e(b['mejor'])}; media {e(a['media'])} → {e(b['media'])}; peor {e(a['peor'])} → {e(b['peor'])};"
                  f" n_grad {a['n_grad']:.1f} → {b['n_grad']:.1f}")
rs = R["afinado_k1"][("rosenbrock", 3, "gdfijo")]
print("   gdfijo afinado Rosenbrock 3D k=1: f del historial al final (últimos 3 puntos de la corrida 0):", rs[0]["result"]["history"][-3:])
print("   eval_equiv de la última mejora (mín/mediana/máx):", min(r["result"]["history"][-1]["eval_equiv"] for r in rs),
      st.median(r["result"]["history"][-1]["eval_equiv"] for r in rs), max(r["result"]["history"][-1]["eval_equiv"] for r in rs))

# ---------------------------------------------------------------------------------------------
titulo("11. Cajas en el piso 1e-16 (peor valor < 1e-16) con la configuración por defecto")
for k, s in sorted(S["defecto"].items()):
    if s["peor"] < 1e-16:
        print("   caja entera en el piso:", k, "peor =", s["peor"])
    elif s["mediana"] < 1e-16:
        print("   mediana en el piso pero no la caja entera:", k, "peor =", s["peor"])
print("avisos de summary.json:")
for a in summ["defecto"]["avisos"]:
    print("   ", a)

# ---------------------------------------------------------------------------------------------
titulo("12. Registro de la cacería: conteos")
reg = open(RAIZ / "alucinaciones/registro.md", encoding="utf-8").read()
ids = re.findall(r"^### (H-\d+) ", reg, flags=re.M)
print("entradas '### H-NN':", len(ids), "de", ids[0], "a", ids[-1], "| duplicadas:", [i for i, c in Counter(ids).items() if c > 1])
for linea in reg.splitlines():
    if re.match(r"\| (Matemáticas|Código|Datos del mundo real|Bibliografía|Conceptos) ", linea):
        print("   ", linea[:200])

titulo("13. Archivos de prompts enlazados en la 09 y claves de cita")
s09 = open(RAIZ / "blog/secciones/09-uso-ia.md", encoding="utf-8").read()
for arch in sorted(set(re.findall(r"alucinaciones/prompts/([\w.\-]+\.md)", s09))):
    print("   ", arch, "existe" if (RAIZ / "alucinaciones/prompts" / arch).is_file() else "NO EXISTE")
bib = open(RAIZ / "blog/references.bib", encoding="utf-8").read()
claves_bib = set(re.findall(r"@\w+\{([^,]+),", bib))
for sec in ["02-fundamentacion", "03-parte1-metodologia", "04-parte1-resultados", "08-discusion", "09-uso-ia", "11-reproducibilidad"]:
    txt = open(RAIZ / f"blog/secciones/{sec}.md", encoding="utf-8").read()
    citas = set(re.findall(r"@([a-z]+\d{4}[a-z]?)", txt))
    print(f"   {sec}: citas {sorted(citas)} | faltan en references.bib: {sorted(citas - claves_bib)} | TODO(cita): {txt.count('TODO(cita)')}")

# ---------------------------------------------------------------------------------------------
titulo("14. k = 2n frente a k = 1 con la configuración por defecto: ¿cambia f_final corrida a corrida?")
for func in FUNCS:
    for dim in DIMS:
        for m in ["gdfijo", "gdarmijo"]:
            a = [r["result"]["f_best"] for r in R["defecto"][(func, dim, m)]]
            b = [r["result"]["f_best"] for r in R["defecto_k1"][(func, dim, m)]]
            sa, sb = S["defecto"][(func, dim, m)], S["defecto_k1"][(func, dim, m)]
            print(f"   {func} {dim}D {m}: corridas con f_best idéntico {sum(x == y for x, y in zip(a, b))}/30; dif. máx. {max(abs(x - y) for x, y in zip(a, b)):.3e};"
                  f" media {e(sa['media'])} → {e(sb['media'])}; desv {e(sa['desv'])} → {e(sb['desv'])}; mejor {e(sa['mejor'])} → {e(sb['mejor'])}; peor {e(sa['peor'])} → {e(sb['peor'])}")
print("   versión afinada:")
for dim in DIMS:
    for m in ["gdfijo", "gdarmijo"]:
        a = [r["result"]["f_best"] for r in R["afinado"][("rastrigin", dim, m)]]
        b = [r["result"]["f_best"] for r in R["afinado_k1"][("rastrigin", dim, m)]]
        print(f"   rastrigin {dim}D {m} afinado: f_best idéntico {sum(x == y for x, y in zip(a, b))}/30; dif. máx. {max(abs(x - y) for x, y in zip(a, b)):.3e}")

titulo("15. Paso fijo en Rosenbrock: barrido fino de eta en memoria (semilla 0, 2D, 5000 gradientes) y estabilidad local")


def gd_fijo_ros(x0, eta, n_grad, lo=-2.048, hi=2.048):
    """Reimplementación directa: mejor f visto y f del último iterado tras n_grad gradientes (el último no da paso)."""
    x = np.array(x0, dtype=float)
    n = len(x)

    def fr(v):
        return float(np.sum(100 * (v[1:] - v[:-1] ** 2) ** 2 + (1 - v[:-1]) ** 2))

    def gr(v):
        g = np.zeros(n)
        g[:-1] += -400 * v[:-1] * (v[1:] - v[:-1] ** 2) - 2 * (1 - v[:-1])
        g[1:] += 200 * (v[1:] - v[:-1] ** 2)
        return g

    mejor = fr(x)
    for _ in range(n_grad):
        x = np.clip(x - eta * gr(x), lo, hi)
        mejor = min(mejor, fr(x))
    return mejor, fr(x)


x0 = es["meta"]["x0"]
for x in es["etas"]:
    if x["marca"]:
        mio, _ = gd_fijo_ros(x0, x["eta"], 5000)
        print(f"   control: eta {x['eta']:.4e} ({x['marca']}): reimplementación {mio:.6e} | eta_deslizador.json {x['f_best']:.6e}")
print("   barrido fino (no está en el blog; sirve para ver dónde deja de converger en esta semilla):")
for eta in [1.5e-3, 1.7e-3, 1.778279410038923e-3, 1.85e-3, 1.9e-3, 1.95e-3, 1.99e-3, 2.0e-3, 2.05e-3, 2.1e-3, 2.2e-3, 2.5e-3, 3.0e-3, 3.1622776601683795e-3]:
    mejor, ultimo = gd_fijo_ros(x0, eta, 5000)
    print(f"      eta {eta:.4e}: mejor f visto {mejor:.4e}; f del último iterado {ultimo:.4e}")
H3 = np.array([[802.0, -400.0, 0.0], [-400.0, 1002.0, -400.0], [0.0, -400.0, 200.0]])
l3 = np.linalg.eigvalsh(H3)
print("   Hessiana de Rosenbrock 3D en (1,1,1): valores propios", l3, "| 2/λmax =", 2 / l3[-1],
      "| eta afinado 1.4941e-3", "SUPERA" if tuned["gd"]["eta"]["rosenbrock"] > 2 / l3[-1] else "no supera", "ese límite local")
print("   Hessiana 2D en (1,1): 2/λmax =", 2 / lam[-1], "| eta afinado", "supera" if tuned["gd"]["eta"]["rosenbrock"] > 2 / lam[-1] else "no supera", "ese límite")

titulo("16. Paso fijo en Rastrigin: ¿la corrida termina en la cuenca en la que empieza?")
for dim in DIMS:
    misma = 0
    for r in R["defecto"][("rastrigin", dim, "gdfijo")]:
        f_ = get_function("rastrigin", dim)
        x0r = make_rng(0, r["seed"]).uniform(f_.bounds[:, 0], f_.bounds[:, 1])
        misma += int(np.array_equal(np.round(x0r), np.round(r["result"]["x_best"])))
    print(f"   rastrigin {dim}D gdfijo: x_best en la misma celda entera que x0 en {misma}/30 corridas")
for dim in DIMS:
    misma = 0
    for r in R["defecto"][("rastrigin", dim, "gdarmijo")]:
        f_ = get_function("rastrigin", dim)
        x0r = make_rng(0, r["seed"]).uniform(f_.bounds[:, 0], f_.bounds[:, 1])
        misma += int(np.array_equal(np.round(x0r), np.round(r["result"]["x_best"])))
    print(f"   rastrigin {dim}D gdarmijo: x_best en la misma celda entera que x0 en {misma}/30 corridas")

titulo("17. Sensibilidad eta = 1.5e-4: reejecución en memoria frente a part1_eta_1l/summary.json")
import copy  # noqa: E402
cfg15 = copy.deepcopy(cfg)
cfg15["gd"]["eta"]["rosenbrock"] = 1.5e-4
for dim in DIMS:
    fs = [ejecutar_corrida("rosenbrock", dim, "gdfijo", 0, s_, cfg15)["result"]["f_best"] for s_ in range(30)]
    c = next(c for c in summ["eta_1l"]["configuraciones"] if (c["dim"], c["method"]) == (dim, "gdfijo"))
    print(f"   {dim}D: mediana reejecutada {st.median(fs):.6e} | summary {c['f_final']['mediana']:.6e}; media {st.fmean(fs):.6e} | {c['f_final']['media']:.6e};"
          f" <=1e-2: {sum(v <= 1e-2 for v in fs)}/30; <=1e-4: {sum(v <= 1e-4 for v in fs)}/30")

titulo("RESUMEN DE DISCREPANCIAS DE TABLAS")
print(len(problemas), "filas de tabla no coinciden con el recálculo")
for pr in problemas:
    print("   ", pr)
