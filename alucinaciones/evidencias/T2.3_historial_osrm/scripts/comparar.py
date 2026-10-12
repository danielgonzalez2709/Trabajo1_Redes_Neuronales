"""Compara las salidas de T2.3 del 11-oct (copia en scratchpad) con las del 12-oct, y los crudos del 12-oct con el
replay de 1 hilo del diagnóstico."""
import csv
import gzip
import json
import sys
from pathlib import Path

raiz, viejo = Path(sys.argv[1]), Path(sys.argv[2])


def filas(p):
    return {(r["i"], r["j"], r["alternativa"]): r for r in csv.DictReader(open(p, encoding="utf-8"))}


a, b = filas(viejo / "rutas.csv"), filas(raiz / "data/processed/rutas.csv")
cambian = [k for k in a if (a[k]["dist_km"], a[k]["tiempo_h"]) != (b[k]["dist_km"], b[k]["tiempo_h"])]
print("filas rutas.csv que cambian (dist_km o tiempo_h):", len(cambian), "de", len(a))
print("  por alternativa:", {alt: sum(1 for k in cambian if k[2] == alt) for alt in ("rapida", "sin_peaje")})
for k in sorted(cambian, key=lambda k: (int(k[0]), int(k[1]), k[2])):
    print("  ", ",".join(k), a[k]["dist_km"], a[k]["tiempo_h"], "->", b[k]["dist_km"], b[k]["tiempo_h"])

ra = json.load(open(viejo / "rutas_resumen.json", encoding="utf-8"))
rb = json.load(open(raiz / "data/processed/rutas_resumen.json", encoding="utf-8"))
pa = {tuple(p) for p in ra["pares_sin_peaje"]["pares"]}
pb = {tuple(p) for p in rb["pares_sin_peaje"]["pares"]}
print("pares sin peaje: 11-oct", len(pa), "| 12-oct", len(pb))
print("  salen:", sorted(pa - pb), " entran:", sorted(pb - pa))
for p in [(3, 35), (21, 35), (6, 26), (44, 46), (13, 33)]:
    print("  ", list(p), "sin peaje 11-oct:", p in pa, "| 12-oct:", p in pb)
for nombre, r in (("11-oct", ra), ("12-oct", rb)):
    print(nombre, "avisos:", {k: v["n"] for k, v in r["avisos"].items()}, "| control_pasos:",
          {k: v for k, v in r["control_pasos"].items() if k != "nota"})
print("sin_peaje con toll 12-oct:", rb["avisos"]["sin_peaje_con_clase_toll"]["pares"])
print("fecha_consulta_utc 12-oct:", rb["fecha_consulta_utc"])

# Crudos 12-oct frente al replay de 1 hilo del diagnóstico (distancia y weight por petición)
diag = {(r["i"], r["j"], r["alternativa"]): r for r in
        csv.DictReader(open(raiz / "alucinaciones/evidencias/T2.3_toll_diagnostico/replay_1081_threads1_2026-10-11.csv"))}
dif = []
for (i, j, alt), r in diag.items():
    d = json.load(gzip.open(raiz / f"data/raw/osrm_2026-10-12/rutas/{int(i):02d}_{int(j):02d}_{alt}.json.gz", "rt",
                            encoding="utf-8"))["respuesta"]["routes"][0]
    if (round(d["distance"], 1), round(d["weight"], 1)) != (float(r["dist_threads1"]), float(r["weight_threads1"])):
        dif.append((i, j, alt, r["dist_threads1"], r["weight_threads1"], round(d["distance"], 1), round(d["weight"], 1)))
print("crudos 12-oct distintos del replay 1 hilo del diagnóstico (dist, weight):", len(dif), "de", len(diag))
for x in dif:
    print("  ", x)
