"""T2.5: vías y clase `toll` de los crudos OSRM de los 5 pares de validación (Spec §7.2 Bloque 3). Sin red.

Los crudos data/raw/osrm_2026-10-12/rutas/ no se versionan (Spec v1.5): este script solo se puede repetir en la máquina
que ejecutó T2.3. Salida: T2.5_vias_5_pares.json (versionado, para el cazador).

    .venv/Scripts/python.exe -I alucinaciones/evidencias/T2.5_vias_5_pares.py
"""

import collections
import gzip
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PARES = {"Bilbao-Zaragoza": (44, 46), "Sevilla-Cadiz": (9, 37), "Madrid-Toledo": (26, 41), "Alicante-Murcia": (2, 28),
         "A Coruna-Pontevedra": (13, 33)}
salida = {}
for nombre, (i, j) in PARES.items():
    for alt in ("rapida", "sin_peaje"):
        ruta = RAIZ / "data" / "raw" / "osrm_2026-10-12" / "rutas" / f"{i:02d}_{j:02d}_{alt}.json.gz"
        crudo = json.load(gzip.open(ruta, "rt", encoding="utf-8"))
        r = crudo["respuesta"]["routes"][0]
        km_por_via, n_toll = collections.Counter(), 0
        for tramo in r["legs"]:
            for paso in tramo["steps"]:
                km_por_via[paso.get("ref") or paso.get("name") or "-"] += paso["distance"] / 1000
                n_toll += sum("toll" in (it.get("classes") or []) for it in paso["intersections"])
        salida[f"{nombre} {alt}"] = {
            "crudo": f"data/raw/osrm_2026-10-12/rutas/{i:02d}_{j:02d}_{alt}.json.gz", "url": crudo["url"],
            "dist_km": round(r["distance"] / 1000, 3), "intersecciones_con_clase_toll": n_toll,
            "km_por_via_top6": {k: round(v, 1) for k, v in km_por_via.most_common(6)}}
destino = Path(__file__).with_suffix(".json")
destino.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(destino)
