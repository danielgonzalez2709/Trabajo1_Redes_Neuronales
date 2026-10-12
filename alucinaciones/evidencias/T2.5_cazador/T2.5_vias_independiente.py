"""Cazador T2.5, afirmacion 1: km por 'ref' de OSRM en los 5 pares (lectura independiente de los crudos gz).
Uso: python -I T2.5_vias_independiente.py <carpeta rutas>"""
import gzip, json, sys, collections
from pathlib import Path
for a, b in [(44, 46), (9, 37), (26, 41), (2, 28), (13, 33)]:
    for alt in ("rapida", "sin_peaje"):
        d = json.load(gzip.open(Path(sys.argv[1]) / f"{a:02d}_{b:02d}_{alt}.json.gz"))["respuesta"]["routes"][0]
        km, tollint = collections.Counter(), collections.Counter()
        for leg in d["legs"]:
            for s in leg["steps"]:
                ref = s.get("ref") or "-"; km[ref] += s["distance"] / 1000
                tollint[ref] += sum("toll" in (i.get("classes") or []) for i in s["intersections"])
        top = ", ".join(f"{r} {k:.1f} km (toll:{tollint[r]})" for r, k in km.most_common(4) if r != "-")
        print(f"{a}-{b} {alt}: total {d['distance']/1000:.1f} km; toll en toda la ruta: {sum(tollint.values())}; {top}")
