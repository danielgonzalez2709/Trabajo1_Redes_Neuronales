"""Envía solo las URL de UNA alternativa (argv[3]) a un servidor (argv[4]) en orden argv[5]; guarda dist, weight y
número de intersecciones toll por crudo en argv[6]."""
import gzip
import json
import sys
import urllib.request
from pathlib import Path

raiz, fecha, alt, servidor, orden, salida = Path(sys.argv[1]), *sys.argv[2:7]
base = raiz / f"data/raw/osrm_{fecha}"
res = json.load(open(raiz / "data/processed/rutas_resumen.json", encoding="utf-8"))
archivos = sorted((base / "rutas").glob(f"*_{alt}.json.gz"))
archivos += [base / "simetria" / f"{j:02d}_{i:02d}_{alt}.json.gz" for i, j in res["simetria"]["pares"]]
if orden == "inverso":
    archivos = archivos[::-1]


def toll(rt):
    return sum(1 for leg in rt["legs"] for s in leg["steps"] for i in s["intersections"]
               if "toll" in (i.get("classes") or []))


out = {}
for f in archivos:
    url = json.load(gzip.open(f, "rt", encoding="utf-8"))["url"].replace("http://127.0.0.1:5001", servidor)
    with urllib.request.urlopen(url, timeout=60) as r:
        rt = json.load(r)["routes"][0]
    out[f"{f.parent.name}/{f.name}"] = [rt["distance"], rt["weight"], toll(rt)]
json.dump(out, open(salida, "w", encoding="utf-8"))
print(alt, orden, servidor, "rutas:", len(out), "con toll:", sum(1 for v in out.values() if v[2] > 0))
