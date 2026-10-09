"""Pruebas de integridad del Bloque 1 (T2.1): data/processed/cities.csv.

Contrato (Spec §5.3):
    id, capital, provincia, lat, lon, fuente, fecha_consulta, verificado_manual (bool), nota
"""

from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path

import pytest

from comun_bloque1 import RAW, punto_en_multipoligono, ruta_unica

RAIZ = Path(__file__).resolve().parents[1]
CITIES = RAIZ / "data" / "processed" / "cities.csv"
MAPA = RAIZ / "data" / "processed" / "cities_mapa_control.png"

COLUMNAS = [
    "id",
    "capital",
    "provincia",
    "lat",
    "lon",
    "fuente",
    "fecha_consulta",
    "verificado_manual",
    "nota",
]

# Caja envolvente de la España peninsular (holgada). Excluye Canarias (lat ~28),
# Ceuta (lat ~35.9) y Melilla (lat ~35.3). Baleares queda dentro de la caja,
# por eso además se comprueba por nombre y provincia.
LAT_MIN, LAT_MAX = 36.0, 43.9
LON_MIN, LON_MAX = -9.4, 3.4

CAPITALES_EXCLUIDAS = {"palma", "las palmas de gran canaria", "santa cruz de tenerife", "ceuta", "melilla"}
PROVINCIAS_EXCLUIDAS = {"illes balears", "las palmas", "santa cruz de tenerife", "ceuta", "melilla"}

# Lista de verificación manual del Spec §7.2 que SÍ son capitales de provincia.
# (Mérida aparece en la lista del Spec pero es capital autonómica, no provincial.)
VERIFICACION_MANUAL = {
    "Vitoria-Gasteiz",
    "A Coruña",
    "Ourense",
    "Girona",
    "Lleida",
    "Castelló de la Plana",
    "Donostia/San Sebastián",
    "Pamplona/Iruña",
    "Córdoba",
    "León",
    "València",
    "Guadalajara",
}


@pytest.fixture(scope="module")
def filas() -> list[dict[str, str]]:
    assert CITIES.exists(), f"No existe {CITIES}"
    with CITIES.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_columnas_exactas_del_contrato():
    with CITIES.open(encoding="utf-8", newline="") as fh:
        cabecera = next(csv.reader(fh))
    assert cabecera == COLUMNAS


def test_47_filas(filas):
    assert len(filas) == 47


def test_ids_unicos_y_consecutivos(filas):
    ids = [int(f["id"]) for f in filas]
    assert len(set(ids)) == 47
    assert sorted(ids) == list(range(47))


def test_capitales_y_provincias_unicas(filas):
    assert len({f["capital"] for f in filas}) == 47
    assert len({f["provincia"] for f in filas}) == 47


def test_coordenadas_en_peninsula(filas):
    for f in filas:
        lat, lon = float(f["lat"]), float(f["lon"])
        assert LAT_MIN <= lat <= LAT_MAX, (f["capital"], lat)
        assert LON_MIN <= lon <= LON_MAX, (f["capital"], lon)


def test_sin_capitales_excluidas(filas):
    for f in filas:
        assert f["capital"].strip().lower() not in CAPITALES_EXCLUIDAS, f["capital"]
        assert f["provincia"].strip().lower() not in PROVINCIAS_EXCLUIDAS, f["provincia"]


def test_verificado_manual_sin_nulos_y_booleano(filas):
    for f in filas:
        assert f["verificado_manual"] in {"true", "false"}, (f["capital"], f["verificado_manual"])


def test_lista_de_verificacion_manual_presente_y_marcada(filas):
    por_nombre = {f["capital"]: f for f in filas}
    faltan = VERIFICACION_MANUAL - por_nombre.keys()
    assert not faltan, f"Faltan capitales de la lista de verificación: {faltan}"
    for nombre in VERIFICACION_MANUAL:
        fila = por_nombre[nombre]
        assert fila["verificado_manual"] == "true", nombre
        assert fila["nota"].strip(), f"{nombre}: la nota debe documentar la verificación"


def test_fuente_y_fecha_presentes(filas):
    for f in filas:
        assert f["fuente"].strip(), f["capital"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["fecha_consulta"]), f["capital"]
        assert "TODO" not in f["lat"] + f["lon"], f["capital"]


def test_cada_punto_dentro_de_su_provincia(filas):
    """Punto-en-provincia recalculado aquí con los polígonos oficiales crudos del IGN (no lee resultados intermedios).

    La provincia de cada fila se localiza por nombre (`provincia` = `nameunit` del IGN).
    """
    with gzip.open(ruta_unica(RAW, "ign_provincias_*.geojson.gz"), "rt", encoding="utf-8") as fh:
        geometrias = {f["properties"]["nameunit"]: f["geometry"] for f in json.load(fh)["features"]}
    fuera = [f["capital"] for f in filas
             if not punto_en_multipoligono(float(f["lon"]), float(f["lat"]), geometrias[f["provincia"]])]
    assert not fuera, f"Capitales fuera de su provincia: {fuera}"


def test_existe_el_mapa_de_control():
    assert MAPA.exists() and MAPA.stat().st_size > 0, f"No existe {MAPA}"
    assert MAPA.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", "El mapa de control no es un PNG"


def test_verificado_manual_exactamente_en_las_12_de_la_lista(filas):
    marcadas = {f["capital"] for f in filas if f["verificado_manual"] == "true"}
    assert marcadas == VERIFICACION_MANUAL
    assert len(marcadas) == 12
