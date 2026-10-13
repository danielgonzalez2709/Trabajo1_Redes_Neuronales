"""Umbrales EXACTOS del valor de la hora: en qué w cambia la ruta óptima (verificación de T3.6 con src/part2/exact.py).

Para cada consumo (base 4,6 y sensibilidad 5,6 y 6,2 l/100 km): resuelve el óptimo exacto en cada w entero de
0 a 100 €/h y, donde la ruta óptima cambia entre w y w + 1, la ubica por bisección con precisión 0,005 €/h.
Compara las rutas con los 215 candidatos de la envolvente de T3.6 (results/data/part2/umbrales_w.json).

No usa internet. Uso (≈ 8 min):   .venv\\Scripts\\python.exe scripts/umbrales_exactos.py
Salida: results/data/part2/umbrales_exactos.json
"""
import json
import sys
import time
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.common.results import save_json  # noqa: E402
from src.part2 import costos as cs  # noqa: E402
from src.part2.exact import resolver_exacto  # noqa: E402

PRECISION = 0.005
CONSUMOS = [4.6, 5.6, 6.2]
SALIDA = RAIZ / "results" / "data" / "part2" / "umbrales_exactos.json"
PR_T36 = {4.6: [10.754, 13.813, 42.186], 5.6: [12.20, 17.69, 43.57], 6.2: [14.49, 18.62, 44.39]}  # umbrales de T3.6


def aristas(tour):
    n = len(tour)
    return frozenset(frozenset((tour[k], tour[(k + 1) % n])) for k in range(n))


def describir(comp, tour, w, vehiculo, precio):
    """Distancia, tiempo, peajes y arcos con peaje de un recorrido en w (alternativa más barata en cada arco)."""
    C, elegida = cs.matriz_costos(comp, w, vehiculo, precio)
    n = len(tour)
    km = horas = peajes = 0.0
    arcos_peaje = 0
    for k in range(n):
        i, j = tour[k], tour[(k + 1) % n]
        alt = elegida[i, j]
        km += getattr(comp, f"dist_km_{alt}")[i, j]
        horas += getattr(comp, f"tiempo_h_{alt}")[i, j]
        peaje = getattr(comp, f"peaje_eur_{alt}")[i, j]
        peajes += peaje
        arcos_peaje += peaje > 0
    costo = sum(C[tour[k], tour[(k + 1) % n]] for k in range(n))
    return {"w": w, "costo": round(costo, 4), "km": round(km, 1), "horas": round(horas, 2),
            "peajes_eur": round(peajes, 2), "arcos_con_peaje": int(arcos_peaje)}


def umbrales_para(comp, vehiculo, precio, candidatos):
    cache = {}

    def optimo(w):
        w = round(w, 6)
        if w not in cache:
            C, _ = cs.matriz_costos(comp, w, vehiculo, precio)
            cache[w] = resolver_exacto(C)[0]
        return cache[w]

    grilla = list(range(0, 101))
    rutas = {w: optimo(w) for w in grilla}
    cortes = []
    for a, b in zip(grilla, grilla[1:]):
        if aristas(rutas[a]) == aristas(rutas[b]):
            continue
        lo, hi = float(a), float(b)
        while hi - lo > PRECISION:
            medio = (lo + hi) / 2
            if aristas(optimo(medio)) == aristas(rutas[a]):
                lo = medio
            else:
                hi = medio
        cortes.append((lo, hi))
    bordes = [0.0] + [round((lo + hi) / 2, 3) for lo, hi in cortes] + [100.0]
    tramos = []
    for desde, hasta in zip(bordes, bordes[1:]):
        w_rep = round((desde + hasta) / 2, 3)
        tour = optimo(w_rep)
        ids = [c["id"] for c in candidatos if aristas(c["tour"]) == aristas(tour)]
        tramos.append({"w_desde": desde, "w_hasta": hasta, "tour": tour,
                       "candidato_t36": ids[0] if ids else None,
                       "en_candidatos_t36": bool(ids), **describir(comp, tour, w_rep, vehiculo, precio)})
    return {"umbrales": bordes[1:-1], "tramos": tramos, "resoluciones_exactas": len(cache)}


def main():
    comp = cs.cargar_componentes(RAIZ / "data" / "processed")
    vehiculo = yaml.safe_load((RAIZ / "data" / "processed" / "vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((RAIZ / "data" / "processed" / "combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    candidatos = json.loads((RAIZ / "results/data/part2/umbrales_w.json").read_text(encoding="utf-8"))["candidatos"]
    resultado = {"nota": "Umbrales del ÓPTIMO EXACTO (PuLP 4 + HiGHS, DFJ con subtours perezosos, gap 0): grilla de w "
                         f"enteros en [0, 100] y bisección hasta {PRECISION} €/h. Comparación con los umbrales de la "
                         "envolvente de T3.6 (mejores rutas encontradas por las heurísticas).",
                 "precio_l": precio, "consumos": {}}
    for consumo in CONSUMOS:
        t0 = time.time()
        r = umbrales_para(comp, {**vehiculo, cs.CLAVE_CONSUMO: consumo}, precio, candidatos)
        r["umbrales_t36"] = PR_T36[consumo]
        resultado["consumos"][str(consumo)] = r
        print(f"consumo {consumo}: umbrales exactos {r['umbrales']} (T3.6: {PR_T36[consumo]}); "
              f"tramos fuera de los candidatos de T3.6: {[t['w_desde'] for t in r['tramos'] if not t['en_candidatos_t36']]}; "
              f"{r['resoluciones_exactas']} resoluciones en {time.time() - t0:.0f} s", flush=True)
    save_json(SALIDA, resultado)
    print(f"guardado en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
