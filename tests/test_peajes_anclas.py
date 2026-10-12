"""Pruebas de data/processed/peajes_cadenas.csv y peajes_anclas.csv (T2.5; Spec §7.2 Bloque 3). Sin red.

Comprueban el contrato, que todo tramo vigente tiene cadena, que los anclas caen dentro de su cadena y que cada
coordenada es rastreable: los nodos de OSM coinciden con el CSV de nodos del PBF y los centroides se recalculan
desde rutas_pasos_peaje.csv (el dato no se inventa: sale de un archivo versionado).
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

import asignar_peajes as ap

RAIZ = Path(__file__).resolve().parents[1]
PROCESADOS = RAIZ / "data" / "processed"
NODOS_OSM = RAIZ / "data" / "raw" / "peajes_2026-10-12" / "osm_motorway_junction_spain-261001.csv"
COLS_CADENAS = ["id_tramo", "cadena", "orden", "refs_osrm"]
COLS_ANCLAS = ["cadena", "km_cadena", "lon", "lat", "etiqueta", "tipo_coord", "origen_km", "fuente_coord"]
TIPOS = {"nodo_osm", "paso_osrm", "centroide_pasos_osrm"}
# toll=yes de OSM en vías que no son autopista de peaje ni tienen fila en peajes_tramos.csv (se avisan y no se cobran)
REFS_SIN_TRAMO = {"GI-20", "N-622", "PA-34"}


def _leer(nombre: str) -> list[dict]:
    with (PROCESADOS / nombre).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def cadenas_filas():
    return _leer("peajes_cadenas.csv")


@pytest.fixture(scope="module")
def anclas_filas():
    return _leer("peajes_anclas.csv")


@pytest.fixture(scope="module")
def cadenas():
    return ap.leer_cadenas(ap.TRAMOS_CSV, ap.CADENAS_CSV, ap.ANCLAS_CSV, ap.FECHA_CORTE)


def _metros(lon0, lat0, lon1, lat1):
    return math.hypot((lon1 - lon0) * ap.M_POR_GRADO_LON_ECUADOR * math.cos(math.radians(lat0)),
                      (lat1 - lat0) * ap.M_POR_GRADO_LAT)


def test_contrato_de_columnas(cadenas_filas, anclas_filas):
    assert list(cadenas_filas[0]) == COLS_CADENAS
    assert list(anclas_filas[0]) == COLS_ANCLAS


def test_todo_tramo_de_la_tabla_esta_en_una_cadena_salvo_los_posteriores_al_corte(cadenas_filas):
    tramos = {f["id"]: f for f in _leer("peajes_tramos.csv")}
    listados = Counter(f["id_tramo"] for f in cadenas_filas)
    assert max(listados.values()) == 1
    sin_cadena = {i for i in tramos if i not in listados}
    assert sin_cadena == {"AP68-POST-BI", "AP68-POST-VI"}  # vigentes desde el 11-nov-2026
    assert all(tramos[i]["vigente_desde"] > ap.FECHA_CORTE for i in sin_cadena)


def test_el_orden_de_cada_cadena_es_1_a_n_y_une_tramos_de_la_misma_via(cadenas_filas):
    tramos = {f["id"]: f for f in _leer("peajes_tramos.csv")}
    por = defaultdict(list)
    for f in cadenas_filas:
        por[f["cadena"]].append(f)
    for cid, fs in por.items():
        assert sorted(int(f["orden"]) for f in fs) == list(range(1, len(fs) + 1)), cid
        assert len({tramos[f["id_tramo"]]["via"] for f in fs}) == 1, cid
        assert len({f["refs_osrm"] for f in fs}) == 1, cid
        assert all(f["refs_osrm"] for f in fs)


def test_las_dos_ap15_y_las_dos_ap7_son_cadenas_distintas(cadenas):
    """Mismo `ref` en OSRM, distinto lugar: no se pueden unir (hueco de la variante A-15, Alicante frente a Málaga)."""
    assert {"AP15S", "AP15N", "AP7MAL", "AP7ALI", "R2A", "R2B"} <= set(cadenas)
    assert cadenas["AP15S"].refs == cadenas["AP15N"].refs == frozenset({"AP-15"})


def test_el_km_de_cada_ancla_cae_dentro_de_su_cadena(anclas_filas, cadenas):
    for f in anclas_filas:
        assert 0 <= float(f["km_cadena"]) <= cadenas[f["cadena"]].longitud_km + 1e-6, f


def test_cada_ancla_de_extremo_de_tramo_coincide_con_la_suma_de_km_de_la_tabla(anclas_filas, cadenas):
    for f in anclas_filas:
        m = re.fullmatch(r"(inicio|fin) del tramo (\S+)", f["origen_km"])
        if not m:
            assert f["origen_km"], f
            continue
        cad = cadenas[f["cadena"]]
        t = next(t for t in cad.tramos if t.id == m.group(2))
        assert float(f["km_cadena"]) == pytest.approx(t.inicio_km if m.group(1) == "inicio" else t.fin_km, abs=1e-3)


def test_tipos_y_coordenadas_en_espana(anclas_filas):
    for f in anclas_filas:
        assert f["tipo_coord"] in TIPOS and f["fuente_coord"] and f["etiqueta"]
        assert -9.5 <= float(f["lon"]) <= 3.5 and 36.0 <= float(f["lat"]) <= 43.9, f


def test_las_cadenas_que_usan_las_rutas_tienen_al_menos_dos_anclas(cadenas):
    sin_anclas = {c.id for c in cadenas.values() if not c.proyectable}
    assert sin_anclas == {"AP7ALI", "AP41", "AP4"}  # ninguna ruta de T2.3 pasa por ellas (se verifica abajo)


def test_ningun_paso_pide_una_cadena_sin_anclas_ni_una_ref_desconocida(cadenas):
    refs_con_anclas = {r for c in cadenas.values() if c.proyectable for r in c.refs}
    refs_sin_anclas = {r for c in cadenas.values() if not c.proyectable for r in c.refs}
    vistas = {f["ref"] for f in _leer("rutas_pasos_peaje.csv") if f["ref"]}
    assert vistas - refs_con_anclas == REFS_SIN_TRAMO
    # AP-7, AP-41 y AP-4: la única ref compartida con una cadena sin anclas es AP-7, que Alicante no usa
    assert (vistas & refs_sin_anclas) <= {"AP-7"}


def test_los_nodos_de_osm_citados_coinciden_con_el_csv_de_nodos_del_pbf(anclas_filas):
    with NODOS_OSM.open(encoding="utf-8", newline="") as f:
        nodos = {r["osm_id"]: (float(r["lon"]), float(r["lat"])) for r in csv.DictReader(f)}
    comprobados = 0
    for f in anclas_filas:
        if f["tipo_coord"] != "nodo_osm":
            continue
        ident = re.search(r"nodo OSM (\d+)", f["fuente_coord"]).group(1)
        if ident in nodos:  # el CSV solo lleva los motorway_junction; otros nodos salen del crudo de T2.4
            assert _metros(float(f["lon"]), float(f["lat"]), *nodos[ident]) < 0.5, f
            comprobados += 1
    assert comprobados >= 8


def test_los_anclas_de_paso_osrm_estan_a_menos_de_1_5_km_de_un_extremo_de_paso_del_csv(anclas_filas):
    pasos = _leer("rutas_pasos_peaje.csv")
    extremos = [(float(p[a]), float(p[b])) for p in pasos for a, b in (("lon_ini", "lat_ini"), ("lon_fin", "lat_fin"))]
    for f in anclas_filas:
        if f["tipo_coord"] == "paso_osrm":
            d = min(_metros(float(f["lon"]), float(f["lat"]), lo, la) for lo, la in extremos)
            assert d < 1500, (f["etiqueta"], d)  # Noáin (un punto interior del crudo) queda a 1,25 km


def test_los_centroides_se_recalculan_desde_rutas_pasos_peaje_csv(anclas_filas):
    pasos = _leer("rutas_pasos_peaje.csv")
    extremos = [(p["ref"], float(p[a]), float(p[b])) for p in pasos for a, b in (("lon_ini", "lat_ini"), ("lon_fin", "lat_fin"))]
    n_ok = 0
    for f in anclas_filas:
        if f["tipo_coord"] != "centroide_pasos_osrm":
            continue
        m = re.search(r"centro \(media\) de (\d+) extremos .* con ref (.+?) a menos de 700 m", f["fuente_coord"])
        n, refs = int(m.group(1)), set(m.group(2).split("/"))
        cerca = [(lo, la) for ref, lo, la in extremos if ref in refs
                 and _metros(float(f["lon"]), float(f["lat"]), lo, la) <= 700]
        assert len(cerca) >= 0.9 * n, f  # el radio se cuenta desde la semilla, no desde el centroide
        lon = sum(c[0] for c in cerca) / len(cerca)
        lat = sum(c[1] for c in cerca) / len(cerca)
        assert _metros(float(f["lon"]), float(f["lat"]), lon, lat) < 150, f
        n_ok += 1
    assert n_ok >= 50
