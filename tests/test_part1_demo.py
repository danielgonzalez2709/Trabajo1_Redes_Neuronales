"""Pruebas de T1.8 (Spec §6.8): figura de trayectoria del demo de la Parte 1 (`src/viz/part1_demo.py`).

Corridas sintéticas con la forma del Spec §5.4 (tests/sinteticos_part1.py); todo lo que se escribe va a tmp_path.
"""

import io
from pathlib import Path

import numpy as np
import pytest
from matplotlib.contour import ContourSet
from matplotlib.figure import Figure
from PIL import Image

from src.part1.functions import get_function
from src.viz import paleta as p
from src.viz import part1_demo as d
from src.viz import part1_gifs as g
from src.viz import style
from tests.sinteticos_part1 import corrida

SEMILLA = 7  # distinta de 0: distingue la semilla de un valor fijo
RUTA_MODULO = Path(d.__file__)

# GD: una posición por frame; `best` (mejor punto visto) se aparta de la posición en el frame 2.
CAMINO_GD = [[3.0, -3.5], [2.5, -1.0], [2.8, -2.0], [-2.0, -3.0]]
MEJOR_GD = [[3.0, -3.5], [2.5, -1.0], [2.5, -1.0], [-2.0, -3.0]]
# Población de 3 puntos en 4 frames (cantidades distintas); `best` no coincide con positions[0].
POBLACION = [
    [[4.0, 4.0], [-4.0, 4.0], [0.5, -4.5]],
    [[2.0, 2.5], [-2.0, 1.5], [0.5, -2.0]],
    [[1.5, 1.8], [-1.0, 1.0], [0.4, -1.2]],
    [[1.0, 1.2], [-0.5, 0.8], [0.25, -0.75]],
]
MEJOR_POBLACION = [[0.5, -4.5], [-2.0, 1.5], [-2.0, 1.5], [0.25, -0.75]]


def _frames_gd():
    return [{"iter": t, "positions": [x], "best": b} for t, (x, b) in enumerate(zip(CAMINO_GD, MEJOR_GD))]


def _frames_poblacion():
    return [{"iter": t, "positions": pos, "best": b} for t, (pos, b) in enumerate(zip(POBLACION, MEJOR_POBLACION))]


def _gd(method="gdfijo", func="rastrigin", seed=SEMILLA, **cambios):
    return corrida(func, 2, method, seed, history=((0, 40.0), (76, 4.97479)), frames=_frames_gd(), **cambios)


def _poblacion(method="pso", func="rastrigin", seed=SEMILLA, **cambios):
    return corrida(func, 2, method, seed, history=((30, 12.0), (20000, 0.00188)), frames=_frames_poblacion(),
                   **cambios)


def _corridas():
    return [_poblacion(), _gd()]


def _por_gid(fig, gid):
    return [a for ax in fig.axes for a in [*ax.lines, *ax.collections] if a.get_gid() == gid]


def _unico(fig, gid):
    artistas = _por_gid(fig, gid)
    assert len(artistas) == 1, (gid, artistas)
    return artistas[0]


def _xy(fig, gid) -> list[list[float]]:
    return np.column_stack(_unico(fig, gid).get_data()).tolist()


def _textos(fig):
    return {t.get_gid(): t.get_text() for t in fig.texts}


def _hueco(linea) -> bool:
    """Marcador sin relleno de color: cara "none" o del color de la superficie."""
    cara = linea.get_markerfacecolor()
    return cara == "none" or cara == p.SUPERFICIE


# ------------------------------------------------------------------------------------------------ figura


def test_construir_devuelve_una_figure_con_el_fondo_de_curvas_de_nivel():
    fig = d.construir(_corridas())
    assert isinstance(fig, Figure)
    assert len(fig.axes) == 1
    assert [c for c in fig.axes[0].collections if isinstance(c, ContourSet)]
    func = get_function("rastrigin", 2)
    assert fig.axes[0].get_xlim() == tuple(func.bounds[0]) and fig.axes[0].get_ylim() == tuple(func.bounds[1])


def test_el_camino_del_gd_son_las_posiciones_de_cada_frame():
    fig = d.construir(_corridas())
    assert _xy(fig, "camino:gdfijo") == CAMINO_GD
    assert _xy(fig, "camino:gdfijo") != MEJOR_GD
    assert _xy(fig, "inicio:gdfijo") == [CAMINO_GD[0]]
    assert _xy(fig, "final:gdfijo") == [CAMINO_GD[-1]]


def test_el_camino_de_la_poblacion_es_el_mejor_de_cada_frame():
    fig = d.construir(_corridas())
    assert _xy(fig, "camino:pso") == MEJOR_POBLACION
    assert _xy(fig, "inicio:pso") == POBLACION[0]
    assert _xy(fig, "final:pso") == POBLACION[-1]


@pytest.mark.parametrize("metodo", ["pso", "gdfijo"])
def test_el_inicio_va_hueco_y_el_final_relleno_con_el_color_del_metodo(metodo):
    fig = d.construir(_corridas())
    inicio, final, camino = (_unico(fig, f"{parte}:{metodo}") for parte in ("inicio", "final", "camino"))
    color = p.COLOR_METODO[metodo]
    assert _hueco(inicio) and inicio.get_markeredgecolor() == color
    assert final.get_markerfacecolor() == color
    assert camino.get_color() == color
    assert inicio.get_linestyle() == "None" and final.get_linestyle() == "None"
    assert camino.get_marker() in ("None", "none", "", None)


def test_el_minimo_global_se_marca_una_vez():
    fig = d.construir(_corridas())
    assert _xy(fig, "x_star") == [get_function("rastrigin", 2).x_star.tolist()]


def test_titulo_nota_y_rotulos():
    textos = _textos(d.construir(_corridas()))
    assert set(textos) == {"titulo", "nota", "rotulo:pso", "rotulo:gdfijo"}
    assert "Rastrigin 2D" in textos["titulo"] and f"semilla {SEMILLA}" in textos["titulo"]
    assert textos["nota"] == (f"Una sola corrida (semilla {SEMILLA}): ilustra la trayectoria, no el "
                              "comportamiento medio.")
    assert textos["rotulo:pso"] == "PSO: mejor f = 1,88e-3 · 20 000 evaluaciones equivalentes"
    assert textos["rotulo:gdfijo"] == "GD (paso fijo): mejor f = 4,97 · 76 evaluaciones equivalentes"


def test_el_rotulo_lee_f_best_y_eval_equiv_del_resultado_y_no_del_historial():
    gd = _gd()
    gd["result"]["f_best"], gd["result"]["eval_equiv"] = 12.3, 1234.5
    textos = _textos(d.construir([gd]))
    assert textos["rotulo:gdfijo"] == "GD (paso fijo): mejor f = 12,3 · 1 234,5 evaluaciones equivalentes"


def test_los_rotulos_siguen_el_orden_de_las_corridas_y_no_se_pisan():
    fig = d.construir([_gd(), _poblacion("de"), _poblacion("ea"), _poblacion("pso"), _gd("gdarmijo")])
    alturas = {t.get_gid(): t.get_position()[1] for t in fig.texts}
    orden = ["titulo", "rotulo:gdfijo", "rotulo:de", "rotulo:ea", "rotulo:pso", "rotulo:gdarmijo"]
    assert [alturas[gid] for gid in orden] == sorted((alturas[gid] for gid in orden), reverse=True)
    techo_de_los_ejes = fig.axes[0].get_position().y1
    assert alturas["rotulo:gdarmijo"] > techo_de_los_ejes > alturas["nota"]
    for metodo in ("gdfijo", "de", "ea", "pso", "gdarmijo"):
        assert len(_por_gid(fig, f"camino:{metodo}")) == 1


def test_la_leyenda_nombra_cada_metodo_el_inicio_el_final_y_el_minimo():
    fig = d.construir(_corridas())
    etiquetas = [t.get_text() for t in fig.axes[0].get_legend().get_texts()]
    assert len(POBLACION[0]) != len(POBLACION)  # el número de la leyenda son los puntos, no los frames
    assert etiquetas == ["PSO: camino del mejor punto (población de 3)", "GD (paso fijo): camino del punto",
                         "Inicio (marcadores huecos)", "Final (marcadores rellenos)", "Mínimo global x* = (0, 0)"]


def test_la_figura_se_alarga_por_la_leyenda_y_los_ejes_conservan_su_tamano():
    """2 métodos: 5 filas de leyenda frente a las 2 de los GIF; todo lo demás, a las distancias de los GIF."""
    fig = d.construir(_corridas())
    ancho, base = g.TAMANO
    fila = g.SALTO_ROTULO * base
    alto = base + 3 * fila
    assert fig.get_size_inches().tolist() == pytest.approx([ancho, alto])
    caja = fig.axes[0].get_position(original=True)
    assert caja.height * alto == pytest.approx(g.EJES[3] * base)
    assert caja.y0 * alto == pytest.approx(g.EJES[1] * base + 3 * fila)
    assert (caja.x0, caja.width) == pytest.approx((g.EJES[0], g.EJES[2]))
    y = {t.get_gid(): t.get_position()[1] for t in fig.texts}
    assert y["nota"] * alto == pytest.approx(g.Y_NOTA * base)  # misma distancia al borde inferior
    assert (1 - y["titulo"]) * alto == pytest.approx((1 - g.Y_TITULO) * base)  # y al superior
    assert (1 - y["rotulo:gdfijo"]) * alto == pytest.approx((1 - g.Y_ROTULO) * base + fila)
    g.imagen(fig)  # dibuja: las cajas de abajo son las del PNG
    nota = next(t for t in fig.texts if t.get_gid() == "nota")
    leyenda = fig.axes[0].get_legend().get_window_extent()
    assert leyenda.y0 > nota.get_window_extent().y1 > 0
    assert leyenda.x0 > 0 and leyenda.x1 < fig.bbox.width


def test_cinco_metodos_alargan_la_figura_arriba_y_abajo():
    fig = d.construir([_gd(), _poblacion("de"), _poblacion("ea"), _poblacion("pso"), _gd("gdarmijo")])
    base = g.TAMANO[1]
    fila = g.SALTO_ROTULO * base
    alto = base + 3 * fila + 6 * fila  # 3 rótulos y 6 filas de leyenda más que en los GIF
    assert fig.get_size_inches()[1] == pytest.approx(alto)
    assert fig.axes[0].get_position(original=True).y0 * alto == pytest.approx(g.EJES[1] * base + 6 * fila)
    g.imagen(fig)
    nota = next(t for t in fig.texts if t.get_gid() == "nota")
    assert fig.axes[0].get_legend().get_window_extent().y0 > nota.get_window_extent().y1


@pytest.mark.parametrize("metodo", ["pso", "gdfijo"])
def test_los_marcadores_no_se_recortan_en_el_borde_de_los_ejes(metodo):
    fig = d.construir(_corridas())
    for parte in ("inicio", "final"):
        assert _unico(fig, f"{parte}:{metodo}").get_clip_on() is False
    assert _unico(fig, f"camino:{metodo}").get_clip_on() is True


def test_puntos_pide_hueco_por_palabra_clave():
    import inspect

    assert inspect.signature(d._puntos).parameters["hueco"].kind is inspect.Parameter.KEYWORD_ONLY


def test_una_sola_corrida_basta():
    fig = d.construir([_poblacion("de", func="rosenbrock")])
    assert _xy(fig, "camino:de") == MEJOR_POBLACION
    assert "Rosenbrock 2D" in _textos(fig)["titulo"]
    assert _xy(fig, "x_star") == [[1.0, 1.0]]


def test_construir_no_modifica_las_corridas():
    import copy

    corridas = _corridas()
    copia = copy.deepcopy(corridas)
    d.construir(corridas)
    assert corridas == copia


# ------------------------------------------------------------------------------------------------ PNG


def test_figura_trayectoria_escribe_un_png_valido_y_devuelve_su_ruta(tmp_path):
    ruta = tmp_path / "sub" / "trayectoria.png"
    assert d.figura_trayectoria(_corridas(), ruta) == ruta
    with Image.open(ruta) as imagen:
        imagen.verify()
        assert imagen.format == "PNG"
    with Image.open(ruta) as imagen:
        ancho, alto = imagen.size
        assert ancho == round(g.TAMANO[0] * style.DPI) and alto >= round(g.TAMANO[1] * style.DPI)
        assert len(imagen.convert("RGB").getcolors(maxcolors=1 << 24)) > 50  # no es un lienzo vacío
    assert sorted(x.name for x in tmp_path.rglob("*")) == ["sub", "trayectoria.png"]


def test_el_png_es_la_figura_de_construir(tmp_path):
    ruta = d.figura_trayectoria(_corridas(), tmp_path / "a.png")
    esperado = io.BytesIO()
    g.imagen(d.construir(_corridas())).save(esperado, format="PNG")
    assert ruta.read_bytes() == esperado.getvalue()


def test_acepta_la_ruta_como_texto(tmp_path):
    ruta = d.figura_trayectoria(_corridas(), str(tmp_path / "a.png"))
    assert isinstance(ruta, Path) and ruta.is_file()


def test_mismos_datos_mismos_bytes_y_datos_distintos_otros_bytes(tmp_path):
    a = d.figura_trayectoria(_corridas(), tmp_path / "a.png").read_bytes()
    b = d.figura_trayectoria(_corridas(), tmp_path / "b.png").read_bytes()
    assert a == b
    otra = _corridas()
    otra[1]["result"]["frames"][-1]["positions"] = [[4.0, 4.0]]
    assert d.figura_trayectoria(otra, tmp_path / "c.png").read_bytes() != a


# ------------------------------------------------------------------------------------------------ errores


def _sin_frames():
    c = _gd()
    del c["result"]["frames"]
    return [_poblacion(), c]


def _frames_vacios():
    c = _gd()
    c["result"]["frames"] = []
    return [c]


def _en_3d():
    c = _poblacion()
    c["dim"] = 3
    return [c, _gd()]


CASOS_DE_ERROR = [
    ("lista vacía", lambda: [], "ninguna corrida"),
    ("sin frames", _sin_frames, "gdfijo.*frames"),
    ("frames vacíos", _frames_vacios, "gdfijo.*frames"),
    ("no es 2D", _en_3d, "2D"),
    ("mezcla funciones", lambda: [_poblacion(), _gd(func="rosenbrock")], "func"),
    ("mezcla semillas", lambda: [_poblacion(), _gd(seed=SEMILLA + 1)], "semilla"),
    ("método repetido", lambda: [_gd(), _gd()], "repetid"),
]


@pytest.mark.parametrize("corridas, fragmento", [(caso[1], caso[2]) for caso in CASOS_DE_ERROR],
                         ids=[caso[0] for caso in CASOS_DE_ERROR])
def test_errores_de_entrada_con_mensaje_claro_y_sin_archivo(tmp_path, corridas, fragmento):
    with pytest.raises(ValueError, match=fragmento):
        d.construir(corridas())
    with pytest.raises(ValueError, match=fragmento):
        d.figura_trayectoria(corridas(), tmp_path / "a.png")
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------------------------------------------ higiene


def test_el_modulo_no_evalua_la_funcion_ni_usa_pyplot():
    """Los puntos de la trayectoria se leen de la corrida; solo el fondo (`_ejes`) evalúa f en una malla."""
    texto = RUTA_MODULO.read_text(encoding="utf-8")
    for prohibido in ("pyplot", "get_function", "CountedProblem", "np.random", ".f("):
        assert prohibido not in texto, prohibido


def test_lineas_de_hasta_120_caracteres_en_lf():
    for ruta in (RUTA_MODULO, Path(__file__)):
        crudo = ruta.read_bytes()
        assert b"\r" not in crudo
        assert [i + 1 for i, linea in enumerate(crudo.decode("utf-8").splitlines()) if len(linea) > 120] == []
