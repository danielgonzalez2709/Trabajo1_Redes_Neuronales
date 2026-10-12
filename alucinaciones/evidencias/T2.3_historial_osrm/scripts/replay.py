"""Repite las 2 202 URL de data/raw/osrm_<fecha> (orden de descargar_datos.py, o inverso) y compara cada ruta con
el crudo guardado: distancia, weight y geometría. Sin escribir nada en el repositorio."""
import gzip
import json
import sys
import urllib.request
from pathlib import Path

raiz, fecha, orden, salida = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
base = raiz / f"data/raw/osrm_{fecha}"
res = json.load(open(raiz / "data/processed/rutas_resumen.json", encoding="utf-8"))
archivos = sorted((base / "rutas").glob("*.json.gz"))  # = orden de pares(n) x ALTERNATIVAS
archivos += [base / "simetria" / f"{j:02d}_{i:02d}_{a}.json.gz" for i, j in res["simetria"]["pares"]
             for a in ("rapida", "sin_peaje")]
assert len(archivos) == 2202, len(archivos)
if orden == "inverso":
    archivos = archivos[::-1]


def toll(rt):
    return sum(1 for leg in rt["legs"] for s in leg["steps"] for i in s["intersections"]
               if "toll" in (i.get("classes") or []))


dif = []
for f in archivos:
    c = json.load(gzip.open(f, "rt", encoding="utf-8"))
    with urllib.request.urlopen(c["url"], timeout=60) as r:
        n = json.load(r)
    a, b = c["respuesta"]["routes"][0], n["routes"][0]
    if (a["distance"], a["weight"], a["geometry"]) != (b["distance"], b["weight"], b["geometry"]):
        dif.append({"crudo": f"{f.parent.name}/{f.name}", "guardado": [a["distance"], a["weight"], toll(a)],
                    "replay": [b["distance"], b["weight"], toll(b)]})
print(f"orden={orden}: rutas distintas del crudo {fecha}: {len(dif)} de {len(archivos)}")
for d in dif:
    print("  ", d["crudo"], "guardado(dist,weight,toll)=", d["guardado"], "replay=", d["replay"])
json.dump(dif, open(salida, "w", encoding="utf-8"), indent=1)
