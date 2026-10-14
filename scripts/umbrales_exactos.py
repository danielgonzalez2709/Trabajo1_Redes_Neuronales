"""Umbrales EXACTOS del valor de la hora: en qué w cambia la ruta óptima (verificación de T3.6 con src/part2/exact.py).

Para cada consumo (base 4,6 y sensibilidad 5,6 y 6,2 l/100 km):
1. resuelve el óptimo exacto en cada w entero de 0 a 100 €/h y, donde la ruta óptima cambia entre w y w + 1, la ubica
   por bisección con precisión 0,005 €/h;
2. arma la envolvente inferior (src/part2/envolvente.py) de los candidatos de T3.6 MÁS las rutas óptimas que las
   heurísticas no encontraron. Como el costo de cada recorrido es lineal por tramos en w, esa envolvente da los umbrales
   de forma analítica; se comprueba que coinciden con la bisección y que en cada tramo el ganador es el óptimo exacto.
   Los candidatos de T3.6 conservan su id (el de umbrales_w.json y sweep_w.json); las rutas nuevas van al final.

No usa internet. Uso: .venv\\Scripts\\python.exe scripts/umbrales_exactos.py              (≈ 13 min)
                       .venv\\Scripts\\python.exe scripts/umbrales_exactos.py --solo-envolvente
(--solo-envolvente reutiliza las rutas exactas de la salida anterior y solo rehace el paso 2, en segundos).
Salida: results/data/part2/umbrales_exactos.json
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from src.common.results import save_json  # noqa: E402
from src.part2 import costos as cs  # noqa: E402
from src.part2 import envolvente as env  # noqa: E402
from src.part2.exact import resolver_exacto  # noqa: E402

PRECISION = 0.005
TOL_COSTO = 1e-6
PASO_VENTAJA = 0.01  # €/h: rejilla para la ventaja máxima del ganador sobre el 2.º mejor recorrido conocido
CONSUMOS = [4.6, 5.6, 6.2]
SALIDA = RAIZ / "results" / "data" / "part2" / "umbrales_exactos.json"
CANDIDATOS_T36 = {  # envolvente de T3.6 de cada consumo (la base y las dos corridas de sensibilidad)
    4.6: RAIZ / "results/data/part2/umbrales_w.json",
    5.6: RAIZ / "results/data/part2/sensibilidad/consumo5.6/umbrales_w.json",
    6.2: RAIZ / "results/data/part2/sensibilidad/consumo6.2/umbrales_w.json",
}


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


def umbrales_por_biseccion(comp, vehiculo, precio):
    """Óptimo exacto en cada w entero y bisección donde cambia. Devuelve (cortes, rutas por w, resoluciones)."""
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
        tramos.append({"w_desde": desde, "w_hasta": hasta, "tour": optimo(w_rep)})
    return cortes, tramos, len(cache)


def envolvente_exacta(comp, vehiculo, precio, t36, rutas_exactas):
    """Envolvente de los candidatos de T3.6 + las rutas exactas nuevas, con los ids de T3.6 conservados."""
    rect = env.rectas(comp, vehiculo[cs.CLAVE_CONSUMO], precio)
    originales = [env.canonico(c["tour"]) for c in t36["candidatos"]]
    nuevas = sorted({env.canonico(t) for t in rutas_exactas} - set(originales))
    todos = originales + nuevas
    e = env.envolvente(rect, todos, 0.0, 100.0)
    a_id = {t: k for k, t in enumerate(todos)}
    remap = [a_id[tuple(t)] for t in e["candidatos"]]
    candidatos = [{"id": k, "tour": list(t),
                   "hallado_en": t36["candidatos"][k]["hallado_en"] if k < len(originales)
                   else [{"metodo": "exacto (PuLP 4 + HiGHS, DFJ, gap 0)"}],
                   "exacto_nuevo": k >= len(originales)} for k, t in enumerate(todos)]
    intervalos = [{**i, "candidato": remap[i["candidato"]]} for i in e["intervalos"]]
    umbrales = [{**u, "de": remap[u["de"]], "a": remap[u["a"]]} for u in e["umbrales"]]

    # Ventaja máxima del ganador de cada intervalo sobre el 2.º mejor recorrido conocido (rejilla de PASO_VENTAJA).
    tours = np.array(todos, dtype=np.intp)
    for i in intervalos:
        ws = np.arange(i["w_desde"], i["w_hasta"] + 1e-9, PASO_VENTAJA)
        ventaja = 0.0
        for w in ws:
            costos = np.sort([env.costo_recorrido(rect, t, w) for t in tours])
            ventaja = max(ventaja, costos[1] - costos[0])
        i["ventaja_max_2o"] = round(float(ventaja), 4)
    return {"consumo_l100": vehiculo[cs.CLAVE_CONSUMO], "precio_l": precio, "candidatos": candidatos,
            "intervalos": intervalos, "umbrales": umbrales}, rect


def comprobar(e, rect, comp, vehiculo, precio, cortes):
    """Los umbrales analíticos caen dentro de los intervalos de la bisección y cada ganador es el óptimo exacto."""
    ws = [u["w"] for u in e["umbrales"]]
    if len(ws) != len(cortes) or any(not (lo - 1e-9 <= w <= hi + 1e-9) for w, (lo, hi) in zip(ws, cortes)):
        raise SystemExit(f"la envolvente {ws} no coincide con la bisección {cortes}")
    for i in e["intervalos"]:
        w = (i["w_desde"] + i["w_hasta"]) / 2
        C, _ = cs.matriz_costos(comp, w, vehiculo, precio)
        _, optimo, _ = resolver_exacto(C)
        ganador = env.costo_recorrido(rect, e["candidatos"][i["candidato"]]["tour"], w)
        if abs(ganador - optimo) > TOL_COSTO * max(1.0, optimo):
            raise SystemExit(f"w = {w}: el ganador cuesta {ganador} y el óptimo exacto {optimo}")


def main():
    solo_envolvente = "--solo-envolvente" in sys.argv
    comp = cs.cargar_componentes(RAIZ / "data" / "processed")
    vehiculo = yaml.safe_load((RAIZ / "data" / "processed" / "vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((RAIZ / "data" / "processed" / "combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    anterior = json.loads(SALIDA.read_text(encoding="utf-8")) if solo_envolvente else None
    resultado = {"nota": "Umbrales del ÓPTIMO EXACTO (PuLP 4 + HiGHS, DFJ con subtours perezosos, gap 0): óptimo en cada "
                         f"w entero de [0, 100] y bisección hasta {PRECISION} €/h; luego envolvente analítica de los "
                         "candidatos de T3.6 más las rutas exactas que las heurísticas no encontraron (ids de T3.6 "
                         "conservados; las nuevas al final, con exacto_nuevo = true).",
                 "precio_l": precio, "consumos": {}}
    for consumo in CONSUMOS:
        t0 = time.time()
        veh = {**vehiculo, cs.CLAVE_CONSUMO: consumo}
        t36 = json.loads(CANDIDATOS_T36[consumo].read_text(encoding="utf-8"))
        if solo_envolvente:
            previo = anterior["consumos"][str(consumo)]
            cortes = ([tuple(c) for c in previo["cortes_biseccion"]] if "cortes_biseccion" in previo  # salida antigua:
                      else [(u - PRECISION, u + PRECISION) for u in previo["umbrales"]])     # punto medio ± precisión
            tramos = [{k: t[k] for k in ("w_desde", "w_hasta", "tour")} for t in previo["tramos"]]
            resoluciones = previo["resoluciones_exactas"]
        else:
            cortes, tramos, resoluciones = umbrales_por_biseccion(comp, veh, precio)
        e, rect = envolvente_exacta(comp, veh, precio, t36, [t["tour"] for t in tramos])
        comprobar(e, rect, comp, veh, precio, cortes)
        ids_t36 = {env.canonico(c["tour"]): c["id"] for c in t36["candidatos"]}
        for t in tramos:
            t["candidato_t36"] = ids_t36.get(env.canonico(t["tour"]))
            t["en_candidatos_t36"] = t["candidato_t36"] is not None
            t.update(describir(comp, t["tour"], round((t["w_desde"] + t["w_hasta"]) / 2, 3), veh, precio))
        resultado["consumos"][str(consumo)] = {
            "umbrales": [round(u["w"], 3) for u in e["umbrales"]],
            "umbrales_t36": [round(u["w"], 3) for u in t36["umbrales"]],
            "cortes_biseccion": [list(c) for c in cortes],
            "tramos": tramos,
            "resoluciones_exactas": resoluciones,
            "envolvente": e,
        }
        r = resultado["consumos"][str(consumo)]
        print(f"consumo {consumo}: umbrales exactos {r['umbrales']} (T3.6: {r['umbrales_t36']}); rutas nuevas: "
              f"{[c['id'] for c in e['candidatos'] if c['exacto_nuevo']]}; {time.time() - t0:.0f} s", flush=True)
    save_json(SALIDA, resultado)
    print(f"guardado en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
