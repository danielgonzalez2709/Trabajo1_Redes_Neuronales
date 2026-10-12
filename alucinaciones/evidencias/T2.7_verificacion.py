"""Verificación adversarial de T2.7 (vehículo). Cazador de alucinaciones, 2026-10-11.

Prompt literal del encargo: alucinaciones/evidencias/T2.7_verificacion_prompt.md.
No usa internet: lee los crudos de data/raw/vehiculo_2026-10-11/ y la captura de Wayback del 2-oct-2026 guardada aquí.
Uso (desde la raíz del repositorio):
    .venv/Scripts/python.exe -I alucinaciones/evidencias/T2.7_verificacion.py > alucinaciones/evidencias/T2.7_verificacion.txt
El catálogo PDF se lee con `pdftotext` (poppler) si está instalado; si no, esa sección se omite.
"""
import collections
import gzip
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAW = Path("data/raw/vehiculo_2026-10-11")
EV = Path("alucinaciones/evidencias")
WB_0210 = EV / "T2.7_wayback_20261002070925_corolla-sedan_caracteristicas.html.gz"
BS = chr(92)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plain(raw):
    t = html.unescape(html.unescape(raw)).replace(BS + "u0026", "&")
    return t


def section(title):
    print(f"\n## {title}")


section("0. Integridad (SHA256SUMS)")
bad = 0
for line in (RAW / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    h, name = line.split(maxsplit=1)
    name = name.lstrip("*")
    ok = sha(RAW / name) == h
    bad += not ok
    print(f"  {'OK ' if ok else 'MAL'} {name}")
print(f"  archivos con hash distinto: {bad}")
print(f"  captura 2-oct (esta carpeta): {WB_0210.name} SHA-256 {sha(WB_0210)}")
print("  cabeceras de esa captura (Wayback, id_): memento-datetime: Fri, 02 Oct 2026 07:09:25 GMT")

section("1. Acabados y versiones del Corolla Sedan (vigencia en la fecha de corte)")
grades = json.loads((RAW / "texus_corolla_sedan_getGrades.json").read_text(encoding="utf-8"))
print(f"  getGrades (11-oct): {len(grades)} acabado(s): {[g['Name'] for g in grades]}")
full = json.loads((RAW / "texus_corolla_sedan_GetFullConfiguration.json").read_text(encoding="utf-8"))
print(f"  GetFullConfiguration: Car.Name = {full['Car']['Name']!r}")
print(f"  Motor: Name = {full['Motorization']['Engine']['Name']!r}, InternalCode = "
      f"{full['Motorization']['Engine']['InternalCode']!r}")
for k in ["Options", "Packs", "Accessories"]:
    print(f"  {k} elegidos: {len(full[k])}")
for k in ["AvailableInternalOptions", "AvailableExternalOptions", "AvailablePacks",
          "AvailableMotorizationsForGradeBodytype", "AvailableAccessoryWheels", "AvailableAccessories"]:
    print(f"  {k}: {full[k]}")
print(f"  Llanta de serie: {full['Wheel'].get('Description') or full['Wheel'].get('Name')!r}"
      if full["Wheel"].get("Description") else "  Llanta de serie: (ver JSON)")

caps = [
    ("15-sep-2026", (RAW / "wayback_20260915155745_toyota_es_corolla_sedan.html").read_text(encoding="utf-8")),
    ("23-sep-2026", (RAW / "wayback_20260923175050_toyota_es_corolla_sedan.html").read_text(encoding="utf-8")),
    ("02-oct-2026 /caracteristicas", gzip.decompress(WB_0210.read_bytes()).decode("utf-8")),
    ("11-oct-2026 actual", (RAW / "toyota_es_corolla_sedan.html").read_text(encoding="utf-8")),
]
pats = {
    "comb": r"Consumo combinado WLTP \(l/100 km\)[^0-9]{0,80}([0-9][.,][0-9])",
    "comb_max": r"Consumo combinado WLTP - Max \(l/100 km\)[^0-9]{0,80}([0-9][.,][0-9])",
    "co2": r"CO2COMBINEDWLTP[^0-9]{0,200}?([0-9]{3}(?: - [0-9]{3})?)",
    "co2_medio": r"CO2 combinado WLTP – medio \(g/km\)[^0-9]{0,80}([0-9]{3})",
}
for label, raw in caps:
    t = plain(raw)
    vers = collections.Counter(m.split(".")[0] for m in re.findall("Corolla SD - [^\"<" + BS + BS + "]{0,60}", t))
    print(f"  [{label}] versiones 'Corolla SD': {dict(vers)}")
    print("     " + ", ".join(f"{k}={sorted(set(re.findall(p, t)))}" for k, p in pats.items()))

section("2. WLTP de la ficha actual (GetTechnicalSpecifications)")
spec = json.loads((RAW / "texus_corolla_sedan_GetTechnicalSpecifications.json").read_text(encoding="utf-8"))
vals = {}


def walk(o):
    if isinstance(o, dict):
        if "InternalCode" in o and "Value" in o:
            vals[o["InternalCode"]] = (o["Value"], o.get("Unit"), o.get("Name"))
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(spec)
for k in ["FUELCOMBINEDWLTP", "FUELCOMBINEDWLTPMAX", "CO2COMBINEDWLTP", "CO2COMBINEDWLTPMAX", "KERBWGHT",
          "BORESTROKE", "COMPRATIO", "DINHP", "HYBATCAP"]:
    print(f"  {k}: {vals.get(k)}")

section("2b. km77 (respaldo)")
for f in ["km77_corolla_sedan_140h_style_plus.html", "km77_corolla_sedan_140h_eco.html"]:
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", (RAW / f).read_text(encoding="utf-8"))))
    m = re.search(r"Consumo WLTP Combinado ([0-9],[0-9]) l/100 km Emisiones de CO₂ WLTP ([0-9]+) gr/km", t)
    title = re.search(r"Toyota Corolla Sedan [^|]{0,50}", t).group(0).strip()
    print(f"  {f}: {title!r} -> consumo {m.group(1)}, CO2 {m.group(2)}")

section("3. Fase WLTP extra alta: ¿aparece en las fichas actuales de Toyota y km77?")
for f in sorted(RAW.glob("*.html")) + sorted(RAW.glob("*.json")):
    n = len(re.findall(r"(?i)extra.?alt|extra.?high|EXTRAHIGH", f.read_text(encoding="utf-8", errors="replace")))
    print(f"  {f.name}: {n}")

section("4. Catálogo 09/2023 (pdftotext)")
pdf = RAW / "14764_CORS_48_ES_WEB_S.pdf"
if shutil.which("pdftotext"):
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True).stdout.decode("utf-8")
    pages = [p for p in txt.split("\f") if p.strip()]
    print(f"  páginas con texto: {len(pages)}")
    for kw in ["Gasolina de 95 o más octanos", "2ZR-FXE", "Ritmo extra alto (l/100km)", "5,6-6,2", "4,3–4,8",
               "98–110", "4,4-4,8", "99-109", "80,5 x 88,3", "13,048:1", "4,08", "09/23/CORSEDAN/ES/0000",
               "© 2023 Toyota España S.L.U."]:
        where = [i for i, p in enumerate(txt.split("\f"), 1) if kw in p]
        print(f"  {kw!r}: págs. PDF {where}")
    print(f"  menciones de RON / E10 / E5 (palabra completa): {len(re.findall(r'(?<![A-Za-z0-9])(RON|E10|E5)(?![A-Za-z0-9])', txt))}")
    m = re.search(r"Los niveles de consumo.{0,700}?emisiones de CO₂\.", re.sub(r"\s+", " ", txt))
    print(f"  nota de la pág. 17: {m.group(0) if m else None}")
else:
    print("  pdftotext no disponible: sección omitida")
