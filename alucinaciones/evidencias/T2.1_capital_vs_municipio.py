"""¿La fila 'Capital de municipio' del NGMEP tiene siempre la misma coordenada que la fila 'Municipio'? (todas las 8 132)."""
import csv, io
from collections import Counter
from pathlib import Path
NG = Path(__file__).resolve().parents[2] / "data/raw/BD_Municipios-Entidades"
rows = list(csv.reader(io.StringIO((NG / "ENTIDADES.csv").read_bytes().decode("cp1252"), newline=""), delimiter=";"))
h, E = rows[0], rows[1:]; ix = {c: i for i, c in enumerate(h)}
mun = {r[ix["INEMUNI"]]: r for r in E if r[ix["TIPO"]] == "Municipio"}
cap = {r[ix["INEMUNI"]]: r for r in E if r[ix["TIPO"]] == "Capital de municipio"}
xy = lambda r: (r[ix["LATITUD_ETRS89_REGCAN95"]], r[ix["LONGITUD_ETRS89_REGCAN95"]])
iguales = [k for k in cap if k in mun and xy(cap[k]) == xy(mun[k])]
print(f"Municipios: {len(mun)}; capitales: {len(cap)}; capital con coordenada idéntica (texto) a su fila Municipio: {len(iguales)}")
print("ORIGENCOOR de la fila Municipio:", dict(Counter(r[ix["ORIGENCOOR"]] for r in mun.values()).most_common()))
print("¿ORIGENCOOR capital == ORIGENCOOR municipio?:", dict(Counter(cap[k][ix["ORIGENCOOR"]] == mun[k][ix["ORIGENCOOR"]] for k in iguales)))
