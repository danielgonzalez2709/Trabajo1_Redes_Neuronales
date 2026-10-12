"""Tras un arranque limpio: primera consulta = argv[2]; después, 3 veces cada objetivo."""
import gzip
import json
import sys
import urllib.request
from pathlib import Path

crudos = Path(sys.argv[1]) / "data/raw/osrm_2026-10-11/rutas"


def url_de(caso):
    return json.load(gzip.open(crudos / f"{caso}.json.gz", "rt", encoding="utf-8"))["url"]


def pedir(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    rt = d["routes"][0]
    t = sum(1 for leg in rt["legs"] for s in leg["steps"] for i in s["intersections"]
            if "toll" in (i.get("classes") or []))
    return (round(rt["distance"], 1), round(rt["weight"], 1), t)


print("primera", sys.argv[2], pedir(url_de(sys.argv[2])))
for obj in ["03_35_rapida", "21_35_rapida", "26_29_sin_peaje", "16_18_sin_peaje", "26_29_rapida"]:
    print("  ", obj, [pedir(url_de(obj)) for _ in range(3)])
