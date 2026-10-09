"""Pruebas del criterio único ante datos faltantes (B1) y de las utilidades de lectura (B2, A6)."""

from __future__ import annotations

import pytest

import construir_cities
from comun_bloque1 import DatoFaltanteError, coordenadas_osm, num, ruta_unica


def test_construir_exige_resultado_osm_de_nivel_ciudad():
    """La falta de OSM es un error explícito al construir (OSM es control obligatorio)."""
    with pytest.raises(DatoFaltanteError, match="Valladolid"):
        construir_cities.exigir_resultado_osm({"Valladolid": None}, "Valladolid")
    with pytest.raises(DatoFaltanteError, match="Teruel"):
        construir_cities.exigir_resultado_osm({}, "Teruel")


def test_construir_devuelve_el_resultado_osm_si_existe():
    resultado = {"lat": "41.6", "lon": "-4.7", "addresstype": "city"}
    assert construir_cities.exigir_resultado_osm({"Valladolid": resultado}, "Valladolid") is resultado


def test_validar_y_caracterizar_usan_el_mismo_criterio():
    """coordenadas_osm (usada por validar_cities_ngmep y caracterizar_bloque1) falla con un mensaje claro."""
    with pytest.raises(DatoFaltanteError, match="Lugo"):
        coordenadas_osm({"capital": "Lugo", "osm_lat": "", "osm_lon": ""})
    assert coordenadas_osm({"capital": "Lugo", "osm_lat": "43.0", "osm_lon": "-7.5"}) == (43.0, -7.5)


def test_num_coma_decimal():
    assert num("-2,512507724") == -2.512507724
    assert num("42,84045247") == 42.84045247


def test_ruta_unica(tmp_path):
    with pytest.raises(FileNotFoundError):
        ruta_unica(tmp_path, "ign_nuc_*.json")
    (tmp_path / "ign_nuc_a.json").write_text("{}")
    assert ruta_unica(tmp_path, "ign_nuc_*.json").name == "ign_nuc_a.json"
    (tmp_path / "ign_nuc_b.json").write_text("{}")
    with pytest.raises(FileNotFoundError):
        ruta_unica(tmp_path, "ign_nuc_*.json")


def test_leer_ngmep_decodifica_cp1252_y_separador_punto_y_coma():
    from comun_bloque1 import leer_ngmep

    provincias = leer_ngmep("PROVINCIAS.csv")
    assert len(provincias) == 52
    assert list(provincias[0]) == ["COD_PROV", "PROVINCIA", "COD_CA", "COMUNIDAD_AUTONOMA", "CAPITAL"]
    assert provincias[0]["PROVINCIA"] == "Araba/Álava"
