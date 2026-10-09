"""Verificación adversarial independiente de T2.1 (cazador de alucinaciones).

Solo biblioteca estándar; no importa ningún script del pipeline. Lee el crudo NGMEP y el crudo IGR
y lo contrasta con data/processed/cities.csv y con las cifras de data/caracterizacion_bloque1.md.

Uso:  python -I alucinaciones/evidencias/T2.1_verificacion.py > alucinaciones/evidencias/T2.1_verificacion.txt
"""
import csv
import hashlib
import io
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NG = ROOT / "data/raw/BD_Municipios-Entidades"
SEED = 20261008  # semilla documentada para la muestra aleatoria
MANUAL = ["Vitoria-Gasteiz", "A Coruña", "Ourense", "Girona", "Lleida", "Castelló de la Plana",
          "Donostia/San Sebastián", "Pamplona/Iruña", "Córdoba", "León", "Valencia", "Guadalajara"]
EXCLUIDAS_PROV = {"07", "35", "38", "51", "52"}  # Illes Balears, Las Palmas, S. C. Tenerife, Ceuta, Melilla


def leer(nombre):
    raw = (NG / nombre).read_bytes()
    txt = raw.decode("cp1252")
    filas = list(csv.reader(io.StringIO(txt, newline=""), delimiter=";"))
    return raw, filas[0], filas[1:]


def num(s):
    return float(s.replace(",", "."))


def hav(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


print("== 0. SHA-256 de los crudos NGMEP")
for f in sorted(NG.iterdir()):
    print(f"  {f.name}: {hashlib.sha256(f.read_bytes()).hexdigest()}")

print("\n== 1. Forma de los CSV NGMEP (filas de datos, columnas, celdas vacías, CRLF)")
tablas = {}
for n in ["PROVINCIAS.csv", "MUNICIPIOS.csv", "ENTIDADES.csv", "EATIMS.csv", "COMJURIDIC.csv"]:
    raw, h, rows = leer(n)
    tablas[n] = (h, rows)
    anchos = Counter(len(r) for r in rows)
    vacias = Counter(h[i] for r in rows for i, v in enumerate(r) if v.strip() == "")
    crlf = raw.count(b"\r\n"); lf = raw.count(b"\n")
    print(f"  {n}: filas={len(rows)} cols={len(h)} anchos={dict(anchos)} CRLF={crlf}/{lf} vacías={dict(vacias)}")
    print(f"     byte 0x92: {raw.count(bytes([0x92]))} veces")

raw_ent = (NG / "ENTIDADES.csv").read_bytes()
i = raw_ent.find(bytes([0x92]))
if i >= 0:
    frag = raw_ent[max(0, i - 30): i + 10]
    print(f"  Contexto 0x92 en ENTIDADES: cp1252={frag.decode('cp1252')!r}  latin-1={frag.decode('latin-1')!r}")
try:
    raw_ent.decode("utf-8"); print("  ENTIDADES decodifica como UTF-8: sí")
except UnicodeDecodeError as e:
    print(f"  ENTIDADES decodifica como UTF-8: NO ({e.reason} en byte {e.start})")

hE, E = tablas["ENTIDADES.csv"]
ix = {c: k for k, c in enumerate(hE)}
print("\n== 2. Recuentos de ENTIDADES.csv")
print("  TIPO:", dict(Counter(r[ix["TIPO"]] for r in E).most_common()))
print("  ORIGENCOOR:", dict(Counter(r[ix["ORIGENCOOR"]] for r in E).most_common()))
print("  SUPRIMIDA_INE:", dict(Counter(r[ix["SUPRIMIDA_INE"]] for r in E)))
print("  DISCREPANTE_INE:", dict(Counter(r[ix["DISCREPANTE_INE"]] for r in E)))
codigos = [r[ix["CODIGOINE"]] for r in E]
print(f"  CODIGOINE únicos: {len(set(codigos))} de {len(codigos)}")
disc = [r for r in E if r[ix["DISCREPANTE_INE"]] == "VERDADERO"]
print("  Filas DISCREPANTE_INE=VERDADERO (CODIGOINE, NOMBRE, TIPO):")
for r in disc:
    print(f"     {r[ix['CODIGOINE']]} {r[ix['NOMBRE']]} | {r[ix['TIPO']]}")

ent = {r[ix["CODIGOINE"]]: r for r in E}

# Capitales según PROVINCIAS -> MUNICIPIOS -> ENTIDADES
hP, P = tablas["PROVINCIAS.csv"]
hM, M = tablas["MUNICIPIOS.csv"]
im = {c: k for k, c in enumerate(hM)}
print("\n== 3. Lista de capitales desde PROVINCIAS.csv")
print(f"  Provincias/ciudades en PROVINCIAS.csv: {len(P)}")
excl = [(p[0], p[1], p[4]) for p in P if p[0] in EXCLUIDAS_PROV]
print(f"  Excluidas (07, 35, 38, 51, 52): {excl}")
esperadas = {}
for p in P:
    if p[0] in EXCLUIDAS_PROV:
        continue
    cand = [m for m in M if m[im["COD_PROV"]] == p[0] and m[im["NOMBRE_ACTUAL"]] == p[4]]
    assert len(cand) == 1, (p, len(cand))
    m = cand[0]
    ce = m[im["COD_INE_CAPITAL"]]
    e = ent[ce]
    esperadas[p[1]] = dict(capital_prov=p[4], cod_prov=p[0], provincia=p[1], codigo=ce, tipo=e[ix["TIPO"]],
                           nombre_ent=e[ix["NOMBRE"]],
                           lat=num(e[ix["LATITUD_ETRS89_REGCAN95"]]), lon=num(e[ix["LONGITUD_ETRS89_REGCAN95"]]),
                           origen=e[ix["ORIGENCOOR"]], muni=m[im["COD_INE"]],
                           sup=e[ix["SUPRIMIDA_INE"]], dis=e[ix["DISCREPANTE_INE"]])
print(f"  Capitales peninsulares esperadas: {len(esperadas)}")
print("  TIPO de la entidad COD_INE_CAPITAL:", dict(Counter(v["tipo"] for v in esperadas.values())))
print("  SUPRIMIDA/DISCREPANTE en las 47:", dict(Counter((v["sup"], v["dis"]) for v in esperadas.values())))

cities = list(csv.DictReader(open(ROOT / "data/processed/cities.csv", encoding="utf-8", newline="")))
print(f"\n  cities.csv: {len(cities)} filas; columnas={list(cities[0].keys())}")
set_c = {c["capital"] for c in cities}
set_p = {c["provincia"] for c in cities}
print(f"  Provincias en PROVINCIAS (sin excluidas) y no en cities: {sorted(set(esperadas) - set_p)}")
print(f"  Provincias en cities y no en PROVINCIAS: {sorted(set_p - set(esperadas))}")
for c in cities:
    e = esperadas[c["provincia"]]
    if c["capital"] != e["capital_prov"] or c["capital"] != e["nombre_ent"]:
        print(f"  Nombre: cities='{c['capital']}' | PROVINCIAS.CAPITAL='{e['capital_prov']}' | ENTIDADES.NOMBRE='{e['nombre_ent']}'")

print("\n== 4. Comparación coordenadas y CODIGOINE (TODAS las 47; se destacan muestra y lista manual)")
rng = random.Random(SEED)
resto = sorted(set_c - set(MANUAL))
muestra = sorted(rng.sample(resto, 8))
print(f"  Semilla {SEED}; muestra aleatoria (8, fuera de la lista manual): {muestra}")
fallos = 0
for c in cities:
    e = esperadas[c["provincia"]]
    m_cod = re.search(r"CODIGOINE (\d{11})", c["nota"])
    cod = m_cod.group(1) if m_cod else None
    ok_lat = f"{e['lat']:.6f}" == c["lat"]
    ok_lon = f"{e['lon']:.6f}" == c["lon"]
    ok_cod = cod == e["codigo"]
    ok_org = f"ORIGENCOOR NGMEP '{e['origen']}'" in c["nota"]
    ok = ok_lat and ok_lon and ok_cod and ok_org and e["tipo"] == "Capital de municipio"
    fallos += not ok
    marca = "MANUAL " if c["capital"] in MANUAL else ("MUESTRA" if c["capital"] in muestra else "       ")
    if marca.strip() or not ok:
        print(f"  [{marca}] {c['capital']:<24} crudo=({e['lat']:.6f},{e['lon']:.6f}) {e['codigo']} "
              f"csv=({c['lat']},{c['lon']}) {cod} -> {'OK' if ok else 'FALLO'}")
print(f"  Filas con discrepancia (de 47): {fallos}")
print("  ORIGENCOOR en las 47 (crudo):", dict(Counter(v["origen"] for v in esperadas.values()).most_common()))
print(f"  verificado_manual=true: {sorted(c['capital'] for c in cities if c['verificado_manual'] == 'true')}")

print("\n== 5. IGR vs NGMEP y comparación con la fila TIPO=Municipio (todas las 52 provincias)")
igr = {}
for q in json.load(open(ROOT / "data/raw/ign_nuc_capitales_provincia_2026-10-07.json", encoding="utf-8")):
    for f in q["respuesta"]["features"]:
        pr = f["properties"]
        igr[pr["codine"]] = (float(pr["latitud"]), float(pr["longitud"]), pr.get("nombre"), pr.get("capital"))
print(f"  Registros IGR capitales de provincia: {len(igr)}")
difieren = []
for p in P:
    m = [m for m in M if m[im["COD_PROV"]] == p[0] and m[im["NOMBRE_ACTUAL"]] == p[4]][0]
    ce = m[im["COD_INE_CAPITAL"]]
    e = ent[ce]
    lat, lon = num(e[ix["LATITUD_ETRS89_REGCAN95"]]), num(e[ix["LONGITUD_ETRS89_REGCAN95"]])
    mu = ent[m[im["COD_INE"]]]
    assert mu[ix["TIPO"]] == "Municipio"
    igual_muni = (e[ix["LATITUD_ETRS89_REGCAN95"]] == mu[ix["LATITUD_ETRS89_REGCAN95"]]
                  and e[ix["LONGITUD_ETRS89_REGCAN95"]] == mu[ix["LONGITUD_ETRS89_REGCAN95"]])
    if ce in igr:
        d = hav(lat, lon, igr[ce][0], igr[ce][1])
        dtxt = f"{d:.3f} km"
    else:
        d, dtxt = None, "sin IGR"
    marca = "EXCL" if p[0] in EXCLUIDAS_PROV else "    "
    if (d is not None and d > 0.001) or igual_muni or d is None:
        print(f"  [{marca}] {p[0]} {p[4]:<24} dist_IGR={dtxt:<9} capital==municipio(texto exacto): {igual_muni} "
              f"ORIGENCOOR={e[ix['ORIGENCOOR']]}")
    if marca.strip() == "" and d is not None and d > 0.001:
        difieren.append((p[0], p[4], round(d, 3), igual_muni, e[ix["ORIGENCOOR"]]))
print(f"  Peninsulares con dist IGR > 1 m: {len(difieren)} -> {[x[0] for x in difieren]}")
print(f"  ...de ellas con coord. idéntica a la fila Municipio: {sum(x[3] for x in difieren)}")
print(f"  ORIGENCOOR en esas: {dict(Counter(x[4] for x in difieren))}")
iguales_muni_47 = [v["capital_prov"] for k, v in esperadas.items()
                   if ent[v["muni"]][ix["LATITUD_ETRS89_REGCAN95"]] == ent[v["codigo"]][ix["LATITUD_ETRS89_REGCAN95"]]
                   and ent[v["muni"]][ix["LONGITUD_ETRS89_REGCAN95"]] == ent[v["codigo"]][ix["LONGITUD_ETRS89_REGCAN95"]]]
print(f"  De las 47, capital==municipio: {len(iguales_muni_47)} -> {iguales_muni_47}")

print("\n== 6. Rango y distancias de cities.csv")
lats = [(float(c["lat"]), c["capital"]) for c in cities]; lons = [(float(c["lon"]), c["capital"]) for c in cities]
print(f"  lat min {min(lats)} max {max(lats)}; lon min {min(lons)} max {max(lons)}")
pares = [(hav(float(a['lat']), float(a['lon']), float(b['lat']), float(b['lon'])), a['capital'], b['capital'])
         for i, a in enumerate(cities) for b in cities[i + 1:]]
print(f"  par más cercano {min(pares)}; más lejano {max(pares)}")
sys.exit(0)
