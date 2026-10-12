"""Verificación adversarial de T2.4 (peajes por tramo). Cazador de alucinaciones, 2026-10-12.

Prompt literal del encargo: alucinaciones/evidencias/T2.4_verificacion_prompt.md.
No usa internet. Lee:
  - data/processed/peajes_tramos.csv (la tabla a verificar);
  - data/raw/peajes_2026-10-12/ (crudos oficiales; comprueba antes su SHA-256 contra MANIFEST.txt);
  - alucinaciones/evidencias/T2.4_audasa_calculadora_2026-10-12.json (calculadora oficial de Audasa, consultada
    por el cazador el 2026-10-12; cabeceras en T2.4_audasa_cabeceras.txt).
El Catálogo RCE se lee con un lector .dbf propio, independiente de scripts/construir_peajes.py.
Los PDF se leen con `pdftotext -raw` (poppler/xpdf). Uso (desde la raíz del repositorio):
    .venv/Scripts/python.exe -I alucinaciones/evidencias/T2.4_verificacion.py > alucinaciones/evidencias/T2.4_verificacion.txt
"""
import csv
import hashlib
import html
import json
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
RAW = Path("data/raw/peajes_2026-10-12")
EV = Path("alucinaciones/evidencias")
TABLA = Path("data/processed/peajes_tramos.csv")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pdf(nombre, raw=True):
    args = ["pdftotext"] + (["-raw"] if raw else ["-layout"]) + [str(RAW / nombre), "-"]
    return subprocess.run(args, capture_output=True).stdout.decode("latin-1")


def texto_html(nombre):
    t = (RAW / nombre).read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def cita(texto, patron, antes=150, despues=200):
    m = re.search(patron, texto)
    return "(no aparece)" if not m else texto[max(0, m.start() - antes): m.end() + despues]


def linea(texto, patron):
    return [l.strip() for l in texto.splitlines() if re.search(patron, l)]


def leer_dbf(zip_path):
    z = zipfile.ZipFile(zip_path)
    n = [x for x in z.namelist() if x.lower().endswith(".dbf")][0]
    b = z.read(n)
    nrec, hlen, rlen = struct.unpack("<IHH", b[4:12])
    campos, off = [], 32
    while b[off] != 0x0D:
        campos.append((b[off:off + 11].split(b"\0")[0].decode("ascii"), b[off + 16]))
        off += 32
    filas = []
    for i in range(nrec):
        r = b[hlen + i * rlen: hlen + (i + 1) * rlen]
        if r[:1] == b"*":
            continue
        p, d = 1, {}
        for nombre, lon in campos:
            d[nombre] = r[p:p + lon].decode("utf-8", errors="replace").strip()
            p += lon
        filas.append(d)
    return filas


def km_rce(cat, carretera, a, b):
    return round(sum(float(r["longitud"]) for r in cat if r["carretera"] == carretera
                     and float(r["pk_inicio"]) >= a - 1e-6 and float(r["pk_fin"]) <= b + 1e-6), 3)


print("# T2.4 — verificación del cazador (2026-10-12)\n")

# 0. Integridad de los crudos
print("## 0. SHA-256 de los crudos contra MANIFEST.txt")
ok = bad = 0
for l in (RAW / "MANIFEST.txt").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([0-9a-f]{64})\s+(\S.*)$", l)
    if m:
        if sha(RAW / m.group(2)) == m.group(1):
            ok += 1
        else:
            bad += 1
            print("  DISTINTO:", m.group(2))
print(f"  coinciden {ok}, distintos {bad}\n")

tabla = {r["id"]: r for r in csv.DictReader(TABLA.open(encoding="utf-8"))}
filas = list(tabla.values())
print(f"Tabla: {len(filas)} filas\n")

# 1. Muestras aleatorias
print("## 1. Muestras aleatorias")
rng = np.random.default_rng(20261012)
m1 = [filas[i]["id"] for i in sorted(rng.choice(len(filas), 5, replace=False))]
validacion = {"AP-68", "AP-4", "AP-41", "AP-7", "AP-9"}
pool = [r for r in filas if r["via"] not in validacion and r["tarifa_ligeros_eur"] not in ("", "TODO(dato-faltante)")]
rng2 = np.random.default_rng(20261013)
m2 = [pool[i]["id"] for i in sorted(rng2.choice(len(pool), 5, replace=False))]
print("  semilla 20261012 (toda la tabla):", m1)
print("  semilla 20261013 (vías fuera de los pares de validación):", m2, "\n")

# Comprobaciones tarifa -> línea literal del crudo
ap68 = pdf("mitma_tarifas_2026_ap-68.pdf")
ap9 = pdf("mitma_tarifas_2026_ap-9.pdf")
chk = [
    ("AP68-01", 6.85, ap68, r"^BILBAO ALTUBE "),
    ("AP68-02", 6.00, ap68, r"^ALTUBE AUTOP\.BURGOS "),
    ("AP68-03", 0.90, ap68, r"^AUTOP\.BURGOS ZAMBRANA "),
    ("AP68-04", 1.90, ap68, r"^ZAMBRANA HARO "),
    ("AP68-05", 4.85, ap68, r"^HARO LOGRO.O "),
    ("AP68-06", 9.40, ap68, r"^LOGRO.O AUTOP\.NAVARRA "),
    ("AP68-07", 11.60, ap68, r"^AUTOP\.NAVARRA ZARAGOZA "),
    ("AP9-02", 8.80, ap9, r"^A CORU.A O A BARCALA - SANTIAGO "),
    ("AP9-04", 7.55, ap9, r"^SANTIAGO - PONTEVEDRA "),
    ("AP6-03", 4.65, pdf("mitma_tarifas_2026_ap-6.pdf"), r"^VILLACASTIN ADANERO "),
    ("AP66-01", 5.90, pdf("mitma_tarifas_2026_ap-66.pdf"), r"^CAMPOMANES-OBLANCA "),
    ("AP71-02", 2.50, pdf("mitma_tarifas_2026_ap-71.pdf"), r"Villadangos-Hospital de Orbigo "),
    ("AP53-01", 7.25, pdf("mitma_tarifas_2026_ap-53.pdf"), r"Santiago-Alto de Santo Domingo "),
    ("AP7-AC-02", 2.85, pdf("mitma_tarifas_2026_ap-7_alicante-cartagena.pdf"), r"^TRONCAL DE LA ZENIA "),
    ("C32-02", 5.03, pdf("abertis_26_001-Aucat-C32-Castelldefels-Vendrell-T26.pdf"), r"troncal de Cubelles "),
]
print("## 2. Tarifas de la tabla frente al crudo (pdftotext -raw)")
for ident, esperado, txt, pat in chk:
    t = float(tabla[ident]["tarifa_ligeros_eur"])
    ls = linea(txt, pat)
    print(f"  {ident}: tabla {t:.2f} | esperado {esperado:.2f} | {'OK' if abs(t - esperado) < 1e-9 else 'DIFIERE'} | crudo: {ls[:1]}")
print("  R2-05 (Meco–Cabanillas, efectivo 1,25), AP-41 R5–Toledo (efectivo 5,95), R4 M-50–Ocaña (efectivo 6,25):"
      " verificados a mano en la matriz -layout (la extracción por línea no es fiable en esas matrices).")
print("  Recorrido completo AP-68:", linea(ap68, r"^BILBAO ZARAGOZA ")[:1], "| Bilbao–Logroño:", linea(ap68, r"^BILBAO LOGRO.O ")[:1])
print("  Suma de la cadena AP68-01..07:", round(sum(float(tabla[f'AP68-0{i}']['tarifa_ligeros_eur']) for i in range(1, 8)), 2), "\n")

# 3. AP-9: desfase de la transcripción (la tabla de recurrencia al 50 % fija la alineación)
print("## 3. AP-9, segunda página: tabla general frente a tabla de recurrencia (50 %)")
for patron in [r"^CALDAS DE REIS - CURRO", r"^CALDAS DE REIS - PONTEVEDRA", r"^CURRO - PONTEVEDRA", r"^PONTEVEDRA - VILABOA",
               r"^PONTEVEDRA - MORRAZO", r"^SANTIAGO - SANTIAGO"]:
    print("  ", linea(ap9, patron))
print()

# 4. Calculadora oficial de Audasa
print("## 4. Calculadora oficial de Audasa (JSON guardado por el cazador)")
aud = json.loads((EV / "T2.4_audasa_calculadora_2026-10-12.json").read_text(encoding="utf-8"))["data"]["tarifas"]
T = {(t["origen"], t["destino"]): float(t["ligeros"]) for t in aud}
print(f"  {len(aud)} recorridos; SHA-256 {sha(EV / 'T2.4_audasa_calculadora_2026-10-12.json')}")
for par in [("A Coruña", "Pontevedra"), ("A Coruña", "Santiago"), ("Santiago", "Pontevedra"), ("Santiago", "Santiago"),
            ("Sigüeiro", "Santiago"), ("Santiago", "Padrón"), ("Sigüeiro", "Padrón"), ("Ordes", "Santiago"),
            ("Ordes", "Padrón"), ("Caldas", "Curro"), ("Curro", "Pontevedra"), ("Caldas", "Pontevedra")]:
    print(f"  {par[0]} -> {par[1]}: {T.get(par)}")
suma = sum(float(tabla[i]["tarifa_ligeros_eur"]) for i in ["AP9-01", "AP9-02", "AP9-03", "AP9-04"])
print(f"  Suma de la tabla AP9-01..04 = {suma:.2f}; Audasa A Coruña -> Pontevedra = {T[('A Coruña', 'Pontevedra')]:.2f}")
print(f"  Con 'Santiago-Santiago' sumado: {suma + 4.55:.2f} (no coincide con Audasa)")
print(f"  Aditividad al cruzar Santiago: Sigüeiro->Santiago + Santiago->Padrón = "
      f"{T[('Sigüeiro', 'Santiago')] + T[('Santiago', 'Padrón')]:.2f} = Sigüeiro->Padrón {T[('Sigüeiro', 'Padrón')]:.2f}\n")

# 5. Catálogo RCE
print("## 5. Catálogo RCE 2025 (lector .dbf propio)")
cat = leer_dbf(RAW / "mitma_260306-catalogorce2025.zip")
print(f"  {len(cat)} registros")
for ident, carr, a, b in [("AP68-05", "AP-68", 87, 126.9), ("AP68-06", "AP-68", 126.9, 208.3), ("AP68-07", "AP-68", 208.3, 291.83),
                          ("AP9-01", "AP-9", 2.6, 7.814), ("AP9-02", "AP-9", 7.814, 67), ("AP9-03", "AP-9", 67, 74.7),
                          ("AP9-04", "AP-9", 74.7, 128.8), ("AP4-01", "AP-4", 12.9, 105.36), ("AP41-01", "AP-41", 0, 47.6),
                          ("AP7-AC-01", "AP-7", 724, 758.3), ("AP7-AC-02", "AP-7", 758.3, 799.8), ("M12-01", "M-12", 0, 2.55),
                          ("M12-02", "M-12", 2.55, 10.865)]:
    print(f"  {ident}: tabla {tabla[ident]['km']} | Catálogo {km_rce(cat, carr, a, b)}")
nav = [r for r in cat if r["carretera"] == "AP-68" and r["provincia"] == "Navarra"]
print(f"  AP-68 en Navarra: {len(nav)} tramos, clases {sorted({r['clase'] for r in nav})}, "
      f"{sum(float(r['longitud']) for r in nav):.2f} km")
pv = [r for r in cat if r["carretera"] == "AP-68" and r["provincia"] in ("Bizkaia", "Araba/Álava", "Álava", "Vizcaya")]
print(f"  AP-68 en Bizkaia/Álava: {len(pv)} tramos; p.k. mínimo de la AP-68: "
      f"{min(float(r['pk_inicio']) for r in cat if r['carretera'] == 'AP-68')}")
for r in sorted([r for r in cat if r["carretera"] == "M-12"], key=lambda r: float(r["pk_inicio"])):
    print(f"  M-12 {float(r['pk_inicio']):.3f}-{float(r['pk_fin']):.3f} {r['inicio']} -> {r['fin']} | {r['clase']}")
circ = [r for r in cat if r["carretera"] == "AP-7" and 676 <= float(r["pk_inicio"]) < 706.75]
print(f"  AP-7 p.k. 676,3-706,75 (Circunvalación de Alicante): clases {sorted({r['clase'] for r in circ})}\n")

# 6. AP-68: fuentes oficiales sobre el fin de la concesión
print("## 6. AP-68 tras el 10-nov-2026")
boe = subprocess.run(["pdftotext", str(RAW / "boe_A-2026-19039.pdf"), "-"], capture_output=True).stdout.decode("latin-1")
b1 = re.sub(r"\s+", " ", boe)
print("  BOE-A-2026-19039, título:", cita(b1, r"Real Decreto 730/2026", 0, 230))
for pat in [r"19,60", r"6,65", r"[Ll]igeros", r"[Tt]urismos", r"11 de noviembre", r"libre"]:
    print(f"  ¿'{pat}' en el BOE? {'sí' if re.search(pat, b1) else 'no'}")
print("  Fin de la concesión:", cita(b1, r"hasta el final de la concesi.n, el 10 de noviembre de 2026", 80, 0))
cong = re.sub(r"\s+", " ", subprocess.run(["pdftotext", str(RAW / "congreso_e_0102096_n_000.pdf"), "-"],
                                          capture_output=True).stdout.decode("latin-1"))
print("  Congreso (23-feb-2026):", cita(cong, r"En consecuencia", 0, 260))
biz = texto_html("bizkaia_nota_2026-07-22_bidesaria_ap68.html")
print("  Bizkaia (22-jul-2026):", cita(biz, r"reducci.n media del 20%", 60, 180))
print(f"  Variación real ligeros 6,85 -> 4,20: {100 * (4.20 / 6.85 - 1):.1f} %; P1 12,60 -> 8,65: {100 * (8.65 / 12.60 - 1):.1f} %;"
      f" P2 14,25 -> 9,75: {100 * (9.75 / 14.25 - 1):.1f} %\n")

# 7. M-12 según SEITT
print("## 7. M-12 según la web de SEITT")
m12 = texto_html("seitt_m-12.html")
print("  ", cita(m12, r"Peajes Troncales", 0, 330))
print("  ", cita(m12, r"La longitud de la M-12 es de 8,40 km", 0, 330))
print()

# 8. Encabezados de los PDF de la R-4 (SEITT)
print("## 8. Encabezados de los PDF de tarifas de la R-4 (SEITT)")
for f in ["seitt_tarifas_r4_2026_1.pdf", "seitt_tarifas_r4_2026.pdf", "seitt_tarifas_r4_2025.pdf", "seitt_tarifas_r4_2025_0.pdf"]:
    t = pdf(f, raw=False)
    print(f"  {f}: {linea(t, r'Peaje 20')[:1]} | {re.findall(r'En vigor desde el 1 de enero de \d{4}', t)[:1]}")
print("  Enlazado desde la web de la R-4:", sorted(set(re.findall(r"tarifas_r4_[0-9_]+\.pdf",
                                                              (RAW / "seitt_r-4.html").read_text(encoding="utf-8", errors="replace")))))
bo25 = re.sub(r"\s+", " ", subprocess.run(["pdftotext", str(RAW / "boe_A-2025-25961.pdf"), "-"],
                                          capture_output=True).stdout.decode("latin-1"))
print("  BOE-A-2025-25961 (Circunvalación de Alicante):", cita(bo25, r"Circunvalaci.n de Alicante, que continuar.n siendo de 0 euros", 120, 0))
