"""cities.csv proviene del NGMEP 202603 (fuente principal, decisión del equipo 2026-10-08) y se contrasta
con IGR Poblaciones (sin red).

La entidad NGMEP de cada capital se identifica con el criterio de la Memoria NGMEP 2026:
PROVINCIAS.CAPITAL -> MUNICIPIOS (mismo COD_PROV, NOMBRE_ACTUAL) -> COD_INE_CAPITAL -> ENTIDADES
(TIPO = "Capital de municipio").

Umbral X = 2,5 km para el contraste IGR -> NGMEP. Justificación con los datos (2026-10-07):
  * la mayor distancia observada IGR Poblaciones vs. NGMEP es 2,350 km (Barcelona); 38 de 47 son idénticas;
  * la menor distancia entre dos capitales es 43,05 km con coordenadas NGMEP (42,91 km con IGR; ambas
    Palencia-Valladolid), así que X queda por debajo
    del 10 % de esa separación: confundir una capital con otra ciudad no puede pasar esta prueba.
"""

from __future__ import annotations

import csv
import itertools
import json

import pytest

from comun_bloque1 import (FECHA_DESCARGA_NGMEP, PROCESSED, RAW, UMBRAL_IGR_KM, haversine_km, leer_ngmep, num,
                           ruta_unica)

CITIES = PROCESSED / "cities.csv"
VERIFICACION = PROCESSED / "cities_verificacion.csv"
UMBRAL_KM = UMBRAL_IGR_KM  # X = 2,5 km (justificación en el docstring del módulo)


# ORÁCULO INDEPENDIENTE. Esta fixture reimplementa a propósito el criterio de la Memoria NGMEP en lugar de
# importar comun_bloque1.entidades_capital_ngmep, que es la función que usa construir_cities.py. Si ambas
# compartieran el código de selección, un error en ese código produciría cities.csv incorrecto y la prueba lo
# daría por bueno. Solo comparte la lectura del CSV (leer_ngmep: cp1252, ';'), que tiene su propia prueba.
@pytest.fixture(scope="module")
def capitales_ngmep() -> dict[str, dict[str, str]]:
    """Entidad 'Capital de municipio' de la capital de cada provincia, por COD_PROV."""
    provincias = leer_ngmep("PROVINCIAS.csv")
    municipios = leer_ngmep("MUNICIPIOS.csv")
    entidades = {e["CODIGOINE"]: e for e in leer_ngmep("ENTIDADES.csv")}
    out = {}
    for p in provincias:
        muni = [m for m in municipios if m["COD_PROV"] == p["COD_PROV"] and m["NOMBRE_ACTUAL"] == p["CAPITAL"]]
        assert len(muni) == 1, p
        out[p["COD_PROV"]] = entidades[muni[0]["COD_INE_CAPITAL"]]
    return out


@pytest.fixture(scope="module")
def igr_por_codine() -> dict[str, dict]:
    consultas = json.loads(ruta_unica(RAW, "ign_nuc_capitales_provincia_*.json").read_text(encoding="utf-8"))
    return {f["properties"]["codine"]: f["properties"] for c in consultas for f in c["respuesta"]["features"]}


@pytest.fixture(scope="module")
def cities() -> list[dict[str, str]]:
    with CITIES.open(encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    with VERIFICACION.open(encoding="utf-8", newline="") as fh:
        codigo = {r["id"]: r["codigoine"] for r in csv.DictReader(fh)}
    for f in filas:
        f["codigoine"] = codigo[f["id"]]
    return filas


def test_ngmep_tiene_52_capitalidades_de_provincia(capitales_ngmep):
    assert len(capitales_ngmep) == 52  # 50 provincias + Ceuta + Melilla (Memoria NGMEP)


def test_codigo_ine_es_el_de_la_capital_ngmep(cities, capitales_ngmep):
    for f in cities:
        e = capitales_ngmep[f["codigoine"][:2]]
        assert e["CODIGOINE"] == f["codigoine"], (f["capital"], e["CODIGOINE"], f["codigoine"])
        assert e["TIPO"] == "Capital de municipio", (f["capital"], e["TIPO"])
        assert f"CODIGOINE {e['CODIGOINE']}" in f["nota"], f["capital"]


def test_coordenadas_iguales_a_ngmep(cities, capitales_ngmep):
    for f in cities:
        e = capitales_ngmep[f["codigoine"][:2]]
        assert f["lat"] == f"{num(e['LATITUD_ETRS89_REGCAN95']):.6f}", f["capital"]
        assert f["lon"] == f"{num(e['LONGITUD_ETRS89_REGCAN95']):.6f}", f["capital"]


def test_fuente_y_fecha_ngmep(cities):
    for f in cities:
        assert "NGMEP 202603" in f["fuente"], f["capital"]
        assert f["fecha_consulta"] == FECHA_DESCARGA_NGMEP, f["capital"]


def test_nombre_y_provincia_coinciden(cities, capitales_ngmep):
    provincias = {p["COD_PROV"]: p["PROVINCIA"] for p in leer_ngmep("PROVINCIAS.csv")}
    for f in cities:
        cod = f["codigoine"][:2]
        assert capitales_ngmep[cod]["NOMBRE"] == f["capital"]
        assert provincias[cod] == f["provincia"]


def test_contraste_igr_a_ngmep(cities, igr_por_codine):
    for f in cities:
        igr = igr_por_codine[f["codigoine"]]  # mismo código INE en IGR Poblaciones
        d = haversine_km(float(igr["latitud"]), float(igr["longitud"]), float(f["lat"]), float(f["lon"]))
        assert d <= UMBRAL_KM, (f["capital"], round(d, 3))


def test_umbral_menor_que_10_por_ciento_de_la_separacion_minima(cities):
    minima = min(
        haversine_km(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
        for a, b in itertools.combinations(cities, 2)
    )
    assert UMBRAL_KM < 0.1 * minima, minima
