"""Pruebas de T4.5 (Spec §7.6.5): GIF de la evolución de la mejor ruta sobre el mapa de España.

Funciones puras con historiales sintéticos (4 ciudades) y una prueba de humo que genera los GIF reales en tmp_path.
"""

import gzip
import json

import numpy as np
import pytest
from PIL import Image

from src.viz import gifs
from src.viz import paleta as p


def _corrida(run_id, cost, mejoras, iniciales=1, por_iter=4):
    return {"run_id": run_id, "cost": cost, "recorridos_iniciales": iniciales, "recorridos_por_iter": por_iter,
            "mejoras": mejoras}


MEJORAS = [
    {"iter": 0, "best_cost": 10.0, "best_tour": [0, 1, 2, 3]},
    {"iter": 3, "best_cost": 8.0, "best_tour": [0, 2, 1, 3]},
    {"iter": 9, "best_cost": 7.5, "best_tour": [0, 2, 3, 1]},
]


def test_mejor_corrida_elige_el_menor_costo_y_desempata_por_run_id():
    variante = {"corridas": [_corrida(5, 7.0, MEJORAS), _corrida(2, 7.0, MEJORAS), _corrida(1, 9.0, MEJORAS)]}
    assert gifs.mejor_corrida(variante)["run_id"] == 2


def test_fotogramas_cuentan_recorridos_evaluados_como_la_convergencia():
    fot = gifs.fotogramas(_corrida(0, 7.5, MEJORAS, iniciales=150, por_iter=148))
    assert [f["iter"] for f in fot] == [0, 3, 9]
    assert [f["evaluados"] for f in fot] == [150 + 148 * 1, 150 + 148 * 4, 150 + 148 * 10]
    assert [f["costo"] for f in fot] == [10.0, 8.0, 7.5]
    assert fot[1]["tour"] == [0, 2, 1, 3]


def test_fotogramas_exige_costo_no_creciente_y_final_igual_al_de_la_corrida():
    with pytest.raises(ValueError, match="no decreciente|crece"):
        gifs.fotogramas(_corrida(0, 7.5, [MEJORAS[1], MEJORAS[0]]))
    with pytest.raises(ValueError, match="final"):
        gifs.fotogramas(_corrida(0, 6.0, MEJORAS))


def test_contorno_excluye_islas_y_ciudades_autonomas_y_reduce_vertices(tmp_path):
    cuadrado = [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]
    anillo_largo = [[[np.cos(t), np.sin(t)] for t in np.linspace(0, 2 * np.pi, 1001)]]
    feats = [
        {"properties": {"nationalcode": "34010400000"}, "geometry": {"type": "MultiPolygon", "coordinates": [anillo_largo]}},
        {"properties": {"nationalcode": "34040700000"}, "geometry": {"type": "MultiPolygon", "coordinates": [cuadrado]}},
        {"properties": {"nationalcode": "34185100000"}, "geometry": {"type": "Polygon", "coordinates": cuadrado}},
        {"properties": {"nationalcode": "34010000000"}, "geometry": {"type": "Polygon", "coordinates": cuadrado}},
    ]
    ruta = tmp_path / "prov.geojson.gz"
    with gzip.open(ruta, "wt", encoding="utf-8") as fh:
        json.dump({"features": feats}, fh)
    anillos = gifs.contorno_peninsular(ruta, paso=10)
    assert len(anillos) == 1  # solo Almería (04); Baleares (07), Ceuta (51) y la fila de CCAA (00) fuera
    x, y = anillos[0]
    assert len(x) < 1001 / 5 and (x[0], y[0]) == (x[-1], y[-1])  # reducido y cerrado


def test_gif_tiene_un_fotograma_por_mejora_y_usa_la_paleta(tmp_path):
    lon, lat = np.array([0.0, 1.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0, 1.0])
    fot = gifs.fotogramas(_corrida(0, 7.5, MEJORAS))
    peaje = lambda tour: np.array([True, False, False, False])  # noqa: E731
    ruta = gifs.gif_evolucion(lon, lat, fot, peaje, [], mejor_conocido=7.5, titulo="Prueba",
                              ruta=tmp_path / "t.gif")
    with Image.open(ruta) as im:
        assert im.n_frames == len(fot)
        duraciones = []
        for k in range(im.n_frames):
            im.seek(k)
            duraciones.append(im.info["duration"])
    assert duraciones[-1] > duraciones[0]  # el fotograma final se sostiene
    assert gifs.COLORES == (p.COLOR_RECORRIDO, p.COLOR_PEAJE, p.COLOR_CIUDAD)


def test_generar_gifs_reales(tmp_path):
    rutas = gifs.generar_gifs(salida=tmp_path)
    assert sorted(r.name for r in rutas) == ["tsp_ga_w25.gif", "tsp_mmas_w25.gif"]
    for r in rutas:
        with Image.open(r) as im:
            assert im.n_frames >= 2
    # determinista: regenerar da los mismos bytes
    otra = gifs.generar_gifs(salida=tmp_path / "b")
    assert {r.name: r.read_bytes() for r in rutas} == {r.name: r.read_bytes() for r in otra}


def test_run_figures_copia_los_gif_al_blog(tmp_path, monkeypatch):
    # El blog (MkDocs) solo publica lo que está en blog/docs/: los GIF de media/ se copian a blog/docs/figures/.
    from src.viz import figuras

    origen = tmp_path / "media" / "tsp_mmas_w25.gif"
    origen.parent.mkdir()
    origen.write_bytes(b"GIF89a-prueba")
    monkeypatch.setattr(gifs, "generar_gifs", lambda: [origen])
    monkeypatch.setattr(figuras, "FIGURAS_BLOG", tmp_path / "blog")
    rutas = figuras._gif_parte2()
    copia = tmp_path / "blog" / "tsp_mmas_w25.gif"
    assert rutas == [origen, copia]
    assert copia.read_bytes() == origen.read_bytes()
