"""Pruebas del estilo de las figuras (T4.1): paleta única, tema de Plotly y estilo de matplotlib."""
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import plotly.io as pio  # noqa: E402

from src.viz import paleta as p  # noqa: E402
from src.viz.style import aplicar_estilo, mapa_secuencial  # noqa: E402
from src.viz.theme import NOMBRE_TEMA, aplicar_tema  # noqa: E402

HEX = re.compile(r"#[0-9a-f]{6}")


def test_colores_validos_y_categorica_sin_repetidos():
    for color in p.CATEGORICA + p.SECUENCIAL_AZUL + [p.SUPERFICIE, p.TINTA, p.TINTA_SECUNDARIA, p.CUADRICULA, p.EJE]:
        assert HEX.fullmatch(color), color
    assert len(set(p.CATEGORICA)) == len(p.CATEGORICA)


def test_cada_metodo_del_spec_tiene_color_y_nombre_fijos():
    metodos = {"gdfijo", "gdarmijo", "ea", "pso", "de"}  # identificadores del Spec §5.4
    assert set(p.COLOR_METODO) == metodos == set(p.NOMBRE_METODO)
    assert len(set(p.COLOR_METODO.values())) == len(metodos)  # colores distintos
    assert set(p.COLOR_ALGORITMO) == {"aco", "ga", "exacto"} == set(p.NOMBRE_ALGORITMO)


def test_rampa_secuencial_va_de_claro_a_oscuro():
    def luminancia(h):
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    valores = [luminancia(c) for c in p.SECUENCIAL_AZUL]
    assert valores == sorted(valores, reverse=True)


def test_tema_plotly_registrado_con_la_paleta():
    aplicar_tema()
    assert pio.templates.default == NOMBRE_TEMA
    fig = go.Figure(go.Scatter(x=[0, 1], y=[1, 0]))
    layout = fig.layout.template.layout
    assert list(layout.colorway) == p.CATEGORICA
    assert layout.paper_bgcolor == p.SUPERFICIE
    assert fig.layout.template.data.scatter[0].line.width == p.ANCHO_LINEA


def test_estilo_matplotlib_dibuja_y_guarda(tmp_path):
    aplicar_estilo()
    assert plt.rcParams["lines.linewidth"] == p.ANCHO_LINEA
    assert not plt.rcParams["axes.spines.top"] and not plt.rcParams["axes.spines.right"]
    fig, ax = plt.subplots()
    ax.contourf([[0, 1], [2, 3]], cmap=mapa_secuencial())
    ax.plot([0, 1], [0, 1], color=p.COLOR_METODO["pso"], label=p.NOMBRE_METODO["pso"])
    ax.legend()
    salida = tmp_path / "prueba.png"
    fig.savefig(salida)
    plt.close(fig)
    assert salida.stat().st_size > 0
