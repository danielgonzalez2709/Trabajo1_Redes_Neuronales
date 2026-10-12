"""¿Depende la respuesta de OSRM de la consulta anterior? Pide un objetivo precedido por distintas consultas previas."""
import gzip
import json
import sys
import urllib.request
from pathlib import Path

raiz = Path(sys.argv[1])
crudos = raiz / "data/raw/osrm_2026-10-11/rutas"


def url_de(caso):
    return json.load(gzip.open(crudos / f"{caso}.json.gz", "rt", encoding="utf-8"))["url"]


def pedir(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    rt = d["routes"][0]
    t = sum(1 for leg in rt["legs"] for s in leg["steps"] for i in s["intersections"]
            if "toll" in (i.get("classes") or []))
    return (round(rt["distance"], 1), round(rt["weight"], 1), t)


objetivos = ["03_35_rapida", "21_35_rapida", "26_29_sin_peaje", "16_18_sin_peaje", "26_29_rapida"]
previas = [None, "03_35_rapida", "03_35_sin_peaje", "26_29_sin_peaje", "26_29_rapida", "00_01_rapida", "00_01_sin_peaje"]
for obj in objetivos:
    print(obj)
    for prev in previas:
        res = []
        for _ in range(3):
            if prev:
                pedir(url_de(prev))
            res.append(pedir(url_de(obj)))
        print(f"   previa={prev!s:18} -> {res}")
