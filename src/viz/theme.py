"""Tema de Plotly para las figuras interactivas del blog (T4.1). Uso:

    from src.viz.theme import aplicar_tema
    aplicar_tema()          # registra "trabajo1" y lo deja como plantilla por defecto
"""
import plotly.graph_objects as go
import plotly.io as pio

from src.viz import paleta as p

NOMBRE_TEMA = "trabajo1"


def construir_tema() -> go.layout.Template:
    """Plantilla con la paleta, la tipografía y la anatomía (líneas finas, cuadrícula tenue) del Design System."""
    eje = dict(
        showgrid=True, gridcolor=p.CUADRICULA, gridwidth=1, zeroline=False,
        showline=True, linecolor=p.EJE, linewidth=1, ticks="outside", tickcolor=p.EJE,
        tickfont=dict(color=p.TINTA_TENUE), title=dict(font=dict(color=p.TINTA_SECUNDARIA)),
    )
    return go.layout.Template(
        layout=dict(
            font=dict(family=", ".join(p.FUENTES), color=p.TINTA, size=14),
            paper_bgcolor=p.SUPERFICIE,
            plot_bgcolor=p.SUPERFICIE,
            colorway=p.CATEGORICA,
            xaxis=eje,
            yaxis=eje,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(color=p.TINTA_SECUNDARIA)),
            hoverlabel=dict(bgcolor=p.SUPERFICIE, bordercolor=p.EJE, font=dict(color=p.TINTA)),
            hovermode="x unified",
            colorscale=dict(sequential=[[i / (len(p.SECUENCIAL_AZUL) - 1), c]
                                        for i, c in enumerate(p.SECUENCIAL_AZUL)]),
            margin=dict(l=60, r=24, t=48, b=56),
        ),
        data=dict(
            scatter=[go.Scatter(line=dict(width=p.ANCHO_LINEA), marker=dict(size=p.TAMANO_MARCADOR))],
        ),
    )


def aplicar_tema() -> None:
    pio.templates[NOMBRE_TEMA] = construir_tema()
    pio.templates.default = NOMBRE_TEMA
