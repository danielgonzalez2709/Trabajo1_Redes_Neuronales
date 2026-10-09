"""Pruebas de interfaz de los scripts del Bloque 1 (hallazgos S1 y S6 de revisor-calidad). Sin red."""

from __future__ import annotations

import inspect

import caracterizar_bloque1
import descargar_datos


def test_get_recibe_la_url_ya_construida():
    """S1: la URL se construye una sola vez, con _url; _get no recibe parámetros de consulta."""
    assert list(inspect.signature(descargar_datos._get).parameters) == ["url", "timeout"]
    assert descargar_datos._url("https://ejemplo.org/items", {"f": "json", "q": "León"}) == (
        "https://ejemplo.org/items?f=json&q=Le%C3%B3n"
    )


def test_caracterizar_tiene_description_y_help():
    """S6: argparse con description y help, como el resto de scripts."""
    parser = caracterizar_bloque1.construir_parser()
    assert parser.description and "Bloque 1" in parser.description
    fecha = next(a for a in parser._actions if "--fecha" in a.option_strings)
    assert fecha.required and fecha.help
