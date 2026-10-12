"""Repite N veces la URL de T2.3 (tomada del crudo del 11-oct) y una variante con nodos; cuenta respuestas distintas."""
import collections
import gzip
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

raiz = Path(sys.argv[1])
N = int(sys.argv[2])
casos = ["26_29_sin_peaje", "16_18_sin_peaje", "03_35_rapida", "21_35_rapida"]


def pedir(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def ntoll(ruta):
    return sum(1 for leg in ruta["legs"] for s in leg["steps"] for i in s["intersections"]
               if "toll" in (i.get("classes") or []))


resultado = {}
for caso in casos:
    f = raiz / "data/raw/osrm_2026-10-11/rutas" / f"{caso}.json.gz"
    if not f.exists():
        f = raiz / "data/raw/osrm_2026-10-11/rutas" / f"{caso.lstrip('0')}.json.gz"
    url = json.load(gzip.open(f, "rt", encoding="utf-8"))["url"]
    url_nodos = url.replace("overview=simplified", "overview=full") + "&annotations=nodes"
    firmas = collections.Counter()
    firmas_nodos = collections.Counter()
    detalle = {}
    for _ in range(N):
        d = pedir(url)
        r = d["routes"][0]
        h = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:12]
        firmas[h] += 1
        detalle[h] = (round(r["distance"], 1), round(r["weight"], 1), round(r["duration"], 1), ntoll(r), d.get("data_version"))
        dn = pedir(url_nodos)
        nodos = [n for leg in dn["routes"][0]["legs"] for n in leg["annotation"]["nodes"]]
        firmas_nodos[hashlib.sha256(json.dumps(nodos).encode()).hexdigest()[:12]] += 1
    resultado[caso] = {"url": url, "respuestas_distintas": len(firmas), "conteos": dict(firmas),
                       "detalle(dist_m,weight,dur_s,intersecciones_toll,data_version)": detalle,
                       "nodos_distintos": len(firmas_nodos), "conteos_nodos": dict(firmas_nodos)}
    print(caso, "| ruta:", dict(firmas), detalle, "| nodos:", dict(firmas_nodos))
json.dump(resultado, open(Path(sys.argv[3]), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
