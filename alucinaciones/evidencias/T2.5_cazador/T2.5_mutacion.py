"""Cazador T2.5, afirmacion 7: prueba de mutacion en una COPIA fuera del repo (el repo no se toca).
Uso: python -I T2.5_mutacion.py <repo> <carpeta_vacia_de_trabajo>
Copia scripts/, tests/, src/, configs/, data/processed y los 2 crudos que las pruebas leen; ejecuta las 56 pruebas
de T2.5 con cada mutante. Para los mutantes de DATOS (anclas) regenera las salidas (como haria quien edita un ancla)."""
import csv, shutil, subprocess, sys
from pathlib import Path
repo, w = Path(sys.argv[1]), Path(sys.argv[2])
for d in ("scripts", "tests", "src", "configs", "docs"):
    shutil.copytree(repo / d, w / d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "T2.5_cazador"))
shutil.copytree(repo / "data/processed", w / "data/processed", dirs_exist_ok=True)
(w / "data/raw/peajes_2026-10-12").mkdir(parents=True, exist_ok=True)
for f in ("osm_motorway_junction_spain-261001.csv", "medicion_km_osm_2026-10-12.json"):
    shutil.copy(repo / "data/raw/peajes_2026-10-12" / f, w / "data/raw/peajes_2026-10-12" / f)
shutil.copy(repo / "run.py", w / "run.py")
PY = sys.executable
SC = w / "scripts/asignar_peajes.py"; AN = w / "data/processed/peajes_anclas.csv"
orig_sc, orig_an = SC.read_bytes(), AN.read_bytes()

def pruebas():
    r = subprocess.run([PY, "-m", "pytest", "tests/test_asignar_peajes.py", "tests/test_peajes_anclas.py", "-q"],
                       cwd=w, capture_output=True, text=True)
    return r.stdout.strip().splitlines()[-1]

def mutar_codigo(a, b):
    t = orig_sc.decode().replace("\r\n", "\n"); assert t.count(a) == 1, a
    SC.write_text(t.replace(a, b), encoding="utf-8", newline="\n")

def mutar_anclas(cambios, regenerar=True):
    filas = list(csv.reader(orig_an.decode().splitlines())); h = filas[0]
    for r in filas[1:]:
        for (cad, km), nuevo in cambios.items():
            if r[h.index("cadena")] == cad and r[h.index("km_cadena")] == km: r[h.index("km_cadena")] = nuevo
    with AN.open("w", encoding="utf-8", newline="") as f: csv.writer(f, lineterminator="\n").writerows(filas)
    if regenerar: subprocess.run([PY, "scripts/asignar_peajes.py"], cwd=w, capture_output=True)

print("base:", pruebas())
for nombre, a, b in [
    ("M1 recorrido solo del primer paso", "        r.lo, r.hi = min(r.lo, lo), max(r.hi, hi)\n", "        pass\n"),
    ("M2 km_peaje cuenta tramos gratuitos", "            if t.tarifa > 0:\n                res.km_peaje += solape\n",
     "            res.km_peaje += solape\n            if t.tarifa > 0:\n"),
    ("M3 sin prorrata (siempre tarifa completa)", "            importe = t.tarifa * fraccion\n", "            importe = t.tarifa\n"),
]:
    mutar_codigo(a, b); print(nombre, "->", pruebas()); SC.write_bytes(orig_sc)
mutar_anclas({("AP6", "9.580"): "29.230", ("AP6", "29.230"): "9.580"})
print("M4 intercambia km de San Rafael y Villacastin (AP-6), salidas regeneradas ->", pruebas())
AN.write_bytes(orig_an)
mutar_anclas({("AP68", "139.140"): "175.000", ("AP68", "219.740"): "260.000"})
print("M5 dos anclas intermedias de la AP-68 con km +36/+40, salidas regeneradas ->", pruebas())
