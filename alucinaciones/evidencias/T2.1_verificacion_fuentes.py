"""Verificación independiente de las cifras de IGR, Nominatim, límites provinciales e INE en
data/caracterizacion_bloque1.md (T2.1). Solo stdlib + openpyxl (si está). Sin red.

Uso:  python -I alucinaciones/evidencias/T2.1_verificacion_fuentes.py > alucinaciones/evidencias/T2.1_verificacion_fuentes.txt
"""
import csv
import gzip
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"


def hav(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


print("== IGR nuc")
q = json.load(open(RAW / "ign_nuc_capitales_provincia_2026-10-07.json", encoding="utf-8"))
print(f"  consultas: {len(q)}; con registros: {sum(1 for x in q if x['respuesta']['features'])}")
feats = [f for x in q for f in x["respuesta"]["features"]]
print(f"  registros: {len(feats)}; cpro distintos: {len({f['properties']['cpro'] for f in feats})}")
print("  por capital:", dict(Counter(f["properties"]["capital"] for f in feats)))
print("  tipo:", dict(Counter(f["properties"]["tipo"] for f in feats)))
cols = Counter(len(f["properties"]) for f in feats)
print(f"  nº de propiedades por registro: {dict(cols)}; nulos/vacíos: "
      f"{sum(1 for f in feats for v in f['properties'].values() if v in (None, ''))}")
fechas = sorted(str(f["properties"]["fecha"])[:10] for f in feats)
print(f"  fecha: {fechas[0]} .. {fechas[-1]}")
cad = [f["properties"] for f in feats if f["properties"]["nombre"] == "Cádiz"][0]
print(f"  Cádiz: codine={cad['codine']} lat={cad['latitud']} lon={cad['longitud']} capital={cad['capital']}")
for n in ("Vitoria-Gasteiz", "Madrid", "Murcia"):
    p = [f["properties"] for f in feats if f["properties"]["nombre"] == n][0]
    print(f"  {n}: capital={p['capital']} tipo={p['tipo']}")
print(f"  códigos consultados: {sorted(x['url'].rsplit('=', 1)[1] for x in q)}")

print("\n== Nominatim")
nom = json.load(open(RAW / "nominatim_capitales_2026-10-07.json", encoding="utf-8"))
es = [x for x in nom if x["modo"] == "es"]; glob = [x for x in nom if x["modo"] != "es"]
print(f"  consultas: {len(nom)} (es={len(es)}, otras={len(glob)}: {[x['consulta'] for x in glob]})")
print("  nº de resultados por consulta:", dict(Counter(len(x["respuesta"]) for x in nom)))
print("  addresstype del 1.er resultado (es):", dict(Counter(x["respuesta"][0]["addresstype"] for x in es)))
for x in glob:
    r = x["respuesta"][0]
    print(f"  sin filtro '{x['consulta']}': {r['display_name']} ({r['lat']}, {r['lon']})")
print("  claves de resultado:", sorted({k for x in nom for r in x["respuesta"] for k in r}))
cities = {c["capital"]: c for c in csv.DictReader(open(ROOT / "data/processed/cities.csv", encoding="utf-8"))}
ver = {c["capital"]: c for c in csv.DictReader(open(ROOT / "data/processed/cities_verificacion.csv", encoding="utf-8"))}
d = sorted((float(v["dist_osm_km"]), k) for k, v in ver.items())
print(f"  dist OSM -> cities (según cities_verificacion): mediana {(d[23][0])} máx {d[-1]}")
alm = ver["Almería"]
print(f"  Almería recalculada: {hav(float(cities['Almería']['lat']), float(cities['Almería']['lon']), float(alm['osm_lat']), float(alm['osm_lon'])):.2f} km")

print("\n== Límites provinciales")
g = json.load(gzip.open(RAW / "ign_provincias_2026-10-07.geojson.gz", "rt", encoding="utf-8"))
F = g["features"]
print(f"  features: {len(F)}; timeStamp: {g.get('timeStamp')}; bytes gz: {(RAW / 'ign_provincias_2026-10-07.geojson.gz').stat().st_size}")
print(f"  nombres no provincia: {[f['properties']['nameunit'] for f in F if f['properties']['nameunit'] in ('Ceuta','Melilla') or 'Territorio' in f['properties']['nameunit']]}")
print(f"  propiedades: {len(F[0]['properties'])} {sorted(F[0]['properties'])}")
print("  vacíos por columna:", dict(Counter(k for f in F for k, v in f["properties"].items() if v in (None, ""))))
def nv(geom):
    return sum(len(r) for poly in geom["coordinates"] for r in poly)
print(f"  tipos geom: {dict(Counter(f['geometry']['type'] for f in F))}; vértices: {sum(nv(f['geometry']) for f in F)}")

print("\n== INE 26codmun")
try:
    import openpyxl
    wb = openpyxl.load_workbook(RAW / "ine_26codmun_2026-10-07.xlsx", read_only=True)
    print(f"  hojas: {len(wb.sheetnames)}")
    tot = 0
    for ws in wb.worksheets:
        rows = [r for r in ws.iter_rows(values_only=True) if any(v is not None for v in r)]
        hdr = next(i for i, r in enumerate(rows) if r and r[0] == "CPRO")
        tot += len(rows) - hdr - 1
    print(f"  filas de municipio: {tot}")
except ImportError:
    print("  openpyxl no disponible en este intérprete")
