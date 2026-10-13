"""Pruebas de las figuras de la Parte 2 (T4.4; Spec §7.6, figuras 2, 3 y 4).

Datos sintéticos de 4 ciudades (tests/sinteticos_part2.py) para el detalle por arco, y entradas pequeñas
de barrido / envolvente / historial para las figuras. Una prueba de humo genera los HTML reales en tmp_path.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from sinteticos_part2 import RAPIDA_TROZOS, SIN_PEAJE_TROZOS, comp
from src.common import cli
from src.part2.costos import matriz_costos
from src.part2.experiment import Datos
from src.part2.recorridos import costos_recorridos
from src.viz import paleta as p
from src.viz import part2_interactivas as pi

A, B, C = (0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 1, 3)


def _datos() -> Datos:
    n = 4
    km = np.zeros((n, n))
    for (i, j) in ((1, 2), (1, 3), (0, 2)):  # arcos con peaje en la rápida
        km[i, j] = km[j, i] = 5.0
    return Datos(comp=comp(RAPIDA_TROZOS, SIN_PEAJE_TROZOS), km_peaje_rapida=km,
                 km_peaje_sin_peaje=np.zeros((n, n)), consumo_l100=1.0, precio_l=1.0)


# Envolvente sintética: A en [0, 5), B en [5, 8), C en [8, 20]; el barrido solo tiene w = 0, 10 y 20.
INTERVALOS = [
    {"w_desde": 0.0, "w_hasta": 5.0, "candidato": 0},
    {"w_desde": 5.0, "w_hasta": 8.0, "candidato": 1},
    {"w_desde": 8.0, "w_hasta": 20.0, "candidato": 2},
]
UMBRALES = [{"w": 5.0, "de": 0, "a": 1, "costo": 0.0}, {"w": 8.0, "de": 1, "a": 2, "costo": 0.0}]
SWEEP = [{"w": 0.0, "candidato": 0}, {"w": 10.0, "candidato": 2}, {"w": 20.0, "candidato": 2}]


# ------------------------------------------------------------------------------------------- deslizador


def test_pasos_incluyen_el_barrido_y_un_punto_en_cada_intervalo_sin_muestras():
    pasos = pi.pasos_deslizador(SWEEP, INTERVALOS)
    assert [x["w"] for x in pasos] == [0.0, 6.5, 10.0, 20.0]
    assert [x["candidato"] for x in pasos] == [0, 1, 2, 2]
    assert [x["en_barrido"] for x in pasos] == [True, False, True, True]


def test_a_ambos_lados_de_cada_umbral_hay_un_paso_con_el_candidato_de_y_el_a():
    pasos = pi.pasos_deslizador(SWEEP, INTERVALOS)
    for u in UMBRALES:
        antes = max((x for x in pasos if x["w"] < u["w"]), key=lambda x: x["w"])
        despues = min((x for x in pasos if x["w"] > u["w"]), key=lambda x: x["w"])
        assert (antes["candidato"], despues["candidato"]) == (u["de"], u["a"])


def test_candidato_del_barrido_distinto_al_de_la_envolvente_es_error():
    with pytest.raises(ValueError, match="envolvente"):
        pi.pasos_deslizador([{"w": 10.0, "candidato": 1}], INTERVALOS)


# ------------------------------------------------------------------------------------- detalle por arco


@pytest.mark.parametrize("w, esperado", [(20.0, [False, True, False, False]), (4.0, [False] * 4)])
def test_arcos_con_peaje_segun_la_alternativa_elegida(w, esperado):
    # Arco 1-2: rápida 6 € + 1 h, sin peaje 0 € + 1,5 h → con peaje solo si 6 + w < 1,5 w (w > 12).
    det = pi.detalle_paso(_datos(), A, w)
    assert det["con_peaje"].tolist() == esperado
    assert det["km_peaje"] == pytest.approx(5.0 * sum(esperado))


@pytest.mark.parametrize("tour", [A, B, C])
@pytest.mark.parametrize("w", [0.0, 4.0, 12.0, 20.0])
def test_desglose_suma_el_costo_del_recorrido(tour, w):
    datos = _datos()
    det = pi.detalle_paso(datos, tour, w)
    Cm, _ = matriz_costos(datos.comp, w, {"consumo_wltp_comb_l100": 1.0}, 1.0)
    costo = float(costos_recorridos(Cm, np.array([tour]))[0])
    assert sum(det["desglose"].values()) == pytest.approx(costo)
    assert det["costo"] == pytest.approx(costo)


# ------------------------------------------------------------------------------------------- figura 2


LON = np.array([0.0, 1.0, 1.0, 0.0])
LAT = np.array([40.0, 40.0, 41.0, 41.0])
NOMBRES = ["c0", "c1", "c2", "c3"]


def _segmentos(traza) -> set[frozenset]:
    """Arcos (pares de puntos) de una traza de líneas separadas por None."""
    xs, ys = list(traza.x), list(traza.y)
    segs = set()
    for k in range(0, len(xs), 3):
        segs.add(frozenset({(xs[k], ys[k]), (xs[k + 1], ys[k + 1])}))
    return segs


def _arcos_tour(tour, mascara) -> set[frozenset]:
    t = list(tour)
    return {frozenset({(LON[a], LAT[a]), (LON[b], LAT[b])})
            for (a, b), m in zip(zip(t, t[1:] + t[:1]), mascara) if m}


def _pasos_figura():
    datos = _datos()
    tours = {0: A, 1: B, 2: C}
    pasos = []
    for x in pi.pasos_deslizador(SWEEP, INTERVALOS):
        pasos.append({**x, "tour": tours[x["candidato"]], **pi.detalle_paso(datos, tours[x["candidato"]], x["w"])})
    return pasos


def test_mapa_un_paso_del_deslizador_por_w_y_recorrido_correcto_en_cada_paso():
    pasos = _pasos_figura()
    fig = pi.figura_mapa(LON, LAT, NOMBRES, pasos, UMBRALES)
    (slider,) = fig.layout.sliders
    assert len(slider.steps) == len(pasos)
    for paso, step in zip(pasos, slider.steps):
        visibles = [tr for tr, v in zip(fig.data, step.args[0]["visible"]) if v]
        lineas = {tr.meta: tr for tr in visibles if tr.meta in ("sin_peaje", "con_peaje")}
        assert set(lineas) == {"sin_peaje", "con_peaje"}
        con = paso["con_peaje"]
        assert _segmentos(lineas["con_peaje"]) == (_arcos_tour(paso["tour"], con) if con.any() else set())
        assert _segmentos(lineas["sin_peaje"]) == _arcos_tour(paso["tour"], ~con)
        assert f"{paso['w']:.2f}".replace(".", ",") in step.args[1]["title.text"]


def test_mapa_peaje_distinto_por_color_y_grosor_y_ciudades_con_nombre():
    fig = pi.figura_mapa(LON, LAT, NOMBRES, _pasos_figura(), UMBRALES)
    con = [tr for tr in fig.data if tr.meta == "con_peaje"]
    sin = [tr for tr in fig.data if tr.meta == "sin_peaje"]
    assert all(tr.line.color == p.COLOR_PEAJE for tr in con)
    assert all(tr.line.color == p.COLOR_RECORRIDO for tr in sin)
    assert all(tr.line.width > s.line.width for tr in con for s in sin)
    (ciudades,) = [tr for tr in fig.data if tr.meta == "ciudades"]
    assert list(ciudades.text) == NOMBRES and ciudades.marker.color == p.COLOR_CIUDAD


# ------------------------------------------------------------------------------------------- figura 3


def _fila(w, t, pe, co):
    return {"w": w, "cost": t + pe + co, "desglose": {"tiempo": t, "peajes": pe, "combustible": co}}


def test_desglose_barras_apiladas_con_los_tres_componentes_y_los_umbrales():
    sweep = [_fila(0.0, 0.0, 0.0, 5.0), _fila(10.0, 30.0, 6.0, 5.0)]
    fig = pi.figura_desglose(sweep, UMBRALES)
    barras = {tr.meta: tr for tr in fig.data if tr.type == "bar"}
    assert set(barras) == {"tiempo", "peajes", "combustible"}
    for k, comp_ in barras.items():
        assert list(barras[k].y) == [f["desglose"][k] for f in sweep]
        assert comp_.marker.color == p.COLOR_COMPONENTE[k]
    assert fig.layout.barmode == "stack"
    lineas = [s for s in fig.layout.shapes if s.type == "line"]
    assert sorted(s.x0 for s in lineas) == [u["w"] for u in UMBRALES]


def test_desglose_que_no_suma_el_costo_es_error():
    fila = _fila(10.0, 30.0, 6.0, 5.0)
    fila["cost"] += 1.0
    with pytest.raises(ValueError, match="desglose"):
        pi.figura_desglose([fila], UMBRALES)


# ------------------------------------------------------------------------------------------- figura 4


def _variante(curvas, iniciales=1, por_iter=3):
    return {"corridas": [
        {"best_cost": c, "recorridos_iniciales": iniciales, "recorridos_por_iter": por_iter,
         "n_tour_evals": iniciales + por_iter * len(c)} for c in curvas]}


def test_curvas_de_convergencia_en_recorridos_evaluados_y_gap_frente_al_mejor():
    x, gaps = pi.curvas_convergencia(_variante([[12.0, 11.0, 10.0], [14.0, 12.0, 12.0]]), mejor=10.0)
    assert x.tolist() == [4, 7, 10]  # iniciales + por_iter · (k + 1)
    assert gaps.tolist() == [[20.0, 10.0, 0.0], [40.0, 20.0, 20.0]]


def test_curvas_con_conteo_inconsistente_es_error():
    v = _variante([[12.0, 11.0]])
    v["corridas"][0]["n_tour_evals"] = 99
    with pytest.raises(ValueError, match="n_tour_evals"):
        pi.curvas_convergencia(v, mejor=10.0)


def test_figura_convergencia_selector_de_w_eje_en_recorridos_y_colores_de_paleta():
    historias = {
        5.0: {"mmas": _variante([[12.0, 10.0]]), "ga": _variante([[13.0, 11.0]], iniciales=4, por_iter=2)},
        25.0: {"mmas": _variante([[22.0, 20.0]]), "ga": _variante([[23.0, 21.0]], iniciales=4, por_iter=2)},
    }
    fig = pi.figura_convergencia(historias, {5.0: 10.0, 25.0: 20.0}, w_inicial=25.0)
    (menu,) = fig.layout.updatemenus
    assert len(menu.buttons) == 2 and menu.active == 1
    medias = [tr for tr in fig.data if tr.meta and tr.meta.startswith("media")]
    for tr in medias:
        solver = tr.meta.split(":")[1]
        assert tr.line.color == p.COLOR_SOLVER[solver]
    ga25 = next(tr for tr in medias if tr.meta == "media:ga:25")
    assert list(ga25.x) == [6, 8] and list(ga25.y) == pytest.approx([15.0, 5.0])
    assert ga25.visible is True
    assert next(tr for tr in medias if tr.meta == "media:ga:5").visible is False
    assert "recorridos evaluados" in fig.layout.xaxis.title.text.lower()
    assert "mejor conocido" in fig.layout.yaxis.title.text.lower()


# ------------------------------------------------------------------------------------------- humo


@pytest.fixture(scope="module")
def generadas(tmp_path_factory):
    salida = tmp_path_factory.mktemp("figuras")
    return salida, pi.generar_part2(salida=salida)


def test_humo_genera_los_html_reales(generadas):
    salida, rutas = generadas
    assert {r.name for r in rutas} == set(pi.ARCHIVOS.values())
    for r in rutas:
        texto = r.read_text(encoding="utf-8")
        assert r.parent == salida and "Plotly.newPlot" in texto
        assert "<html" not in texto  # fragmento para `incluir:` del blog, no un documento completo


def test_humo_el_deslizador_real_cruza_cada_umbral():
    datos_reales = pi.cargar_entradas()
    pasos = pi.pasos_mapa(datos_reales)
    for u in datos_reales["umbrales"]["umbrales"]:
        antes = max((x for x in pasos if x["w"] < u["w"]), key=lambda x: x["w"])
        despues = min((x for x in pasos if x["w"] > u["w"]), key=lambda x: x["w"])
        assert (antes["candidato"], despues["candidato"]) == (u["de"], u["a"])
        assert antes["tour"] != despues["tour"]
    for x in pasos:
        assert math.isclose(sum(x["desglose"].values()), x["costo"], rel_tol=1e-9)


def test_run_py_figures_genera_la_parte_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pi, "SALIDA", tmp_path)
    assert cli.main(["figures"]) == 0
    assert {r.name for r in tmp_path.iterdir()} == set(pi.ARCHIVOS.values())
    assert "Parte 1" in capsys.readouterr().out
