"""Pruebas unitarias de las utilidades geográficas y de nombres de scripts/comun_bloque1.py (A5)."""

from __future__ import annotations

import math

import pytest

from comun_bloque1 import R_TIERRA_KM, haversine_km, punto_en_multipoligono, variantes

# Cuadrado 0..10 con un agujero 4..6 (anillo exterior + anillo interior).
CUADRADO_CON_AGUJERO = {
    "type": "Polygon",
    "coordinates": [
        [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
        [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
    ],
}
DOS_ISLAS = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        [[[5, 5], [6, 5], [6, 6], [5, 6], [5, 5]]],
    ],
}


class TestPuntoEnMultipoligono:
    def test_dentro_del_anillo_exterior(self):
        assert punto_en_multipoligono(2, 2, CUADRADO_CON_AGUJERO)

    def test_dentro_del_agujero_queda_fuera(self):
        assert not punto_en_multipoligono(5, 5, CUADRADO_CON_AGUJERO)

    def test_exterior(self):
        assert not punto_en_multipoligono(11, 5, CUADRADO_CON_AGUJERO)
        assert not punto_en_multipoligono(-1, -1, CUADRADO_CON_AGUJERO)

    def test_multipoligono_ambas_partes_y_el_hueco_entre_ellas(self):
        assert punto_en_multipoligono(0.5, 0.5, DOS_ISLAS)
        assert punto_en_multipoligono(5.5, 5.5, DOS_ISLAS)
        assert not punto_en_multipoligono(3, 3, DOS_ISLAS)

    def test_rayo_a_la_altura_de_una_arista_horizontal(self):
        # lat = 10 coincide con la arista superior horizontal; lat = 4 con la del agujero.
        # La regla (yi > lat) != (yj > lat) no cuenta aristas horizontales: no hay división por cero.
        assert not punto_en_multipoligono(-1, 10, CUADRADO_CON_AGUJERO)
        assert punto_en_multipoligono(2, 4, CUADRADO_CON_AGUJERO)

    def test_geometria_no_soportada(self):
        with pytest.raises(ValueError):
            punto_en_multipoligono(0, 0, {"type": "Point", "coordinates": [0, 0]})


class TestVariantes:
    def test_articulo_pospuesto_del_ine(self):
        assert "a coruna" in variantes("Coruña, A")

    def test_nombre_bilingue(self):
        v = variantes("Donostia/San Sebastián")
        assert {"donostia", "san sebastian", "donostia/san sebastian"} <= v

    def test_nombre_simple_sin_tildes(self):
        assert variantes("Castelló de la Plana") == {"castello de la plana"}


class TestHaversine:
    def test_distancia_cero(self):
        assert haversine_km(40.0, -3.0, 40.0, -3.0) == 0.0

    def test_un_grado_de_latitud(self):
        # Referencia calculada (no recordada): un grado de meridiano = 2*pi*R/360 con el R del código.
        esperado = 2 * math.pi * R_TIERRA_KM / 360
        assert haversine_km(40.0, -3.0, 41.0, -3.0) == pytest.approx(esperado, rel=1e-12)

    def test_simetrica(self):
        assert haversine_km(36.5, -6.3, 42.0, 2.8) == pytest.approx(haversine_km(42.0, 2.8, 36.5, -6.3))
