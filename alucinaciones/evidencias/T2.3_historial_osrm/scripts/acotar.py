"""Tras arranque limpio: una consulta previa (caso + transformación de URL) y luego los objetivos."""
import gzip
import json
import sys
import urllib.request
from pathlib import Path

crudos = Path(sys.argv[1]) / "data/raw/osrm_2026-10-11/rutas"
caso, modo = sys.argv[2], sys.argv[3]


def url_de(c):
    return json.load(gzip.open(crudos / f"{c}.json.gz", "rt", encoding="utf-8"))["url"]


def pedir(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    rt = d["routes"][0]
    t = sum(1 for leg in rt["legs"] for s in leg["steps"] for i in s["intersections"]
            if "toll" in (i.get("classes") or []))
    return (round(rt["distance"], 1), round(rt["weight"], 1), t)


u = url_de(caso)
if modo == "nodes":
    u += "&annotations=nodes"
elif modo == "full":
    u = u.replace("overview=simplified", "overview=full")
elif modo == "full+nodes":
    u = u.replace("overview=simplified", "overview=full") + "&annotations=nodes"
print("previa", caso, modo, pedir(u))
for obj in ["03_35_rapida", "21_35_rapida", "16_18_sin_peaje", "26_29_rapida"]:
    print("  ", obj, pedir(url_de(obj)))
