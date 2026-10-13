"""Figuras de la Parte 2 con matplotlib (Spec §7.6, §7.7 y §8).

`figura_recorrido` dibuja un recorrido sobre las 47 capitales (lon, lat de `data/processed/cities.csv`) con el estilo
del proyecto (`style.parametros`) y los colores de `paleta`: tramos con peaje en COLOR_PEAJE, el resto en
COLOR_RECORRIDO. Los arcos son segmentos rectos entre capitales (no el trazado de la carretera).

No usa pyplot ni cambia el backend ni los rcParams globales: crea la figura con `Figure` + `FigureCanvasAgg`
(no interactivo) dentro de un `rc_context`.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from src.viz import paleta as p
from src.viz.style import parametros

TAMANO = (7.0, 6.0)  # pulgadas
ANCHO_SIN_PEAJE = p.ANCHO_LINEA
ANCHO_PEAJE = p.ANCHO_LINEA * 1.5  # el tramo con peaje se distingue también por grosor (no solo por color)
TAMANO_CIUDAD = 14  # área del marcador (pt²)
NOTA = "Segmentos rectos entre capitales (no es el trazado de la carretera)."


def figura_recorrido(lon, lat, tour, con_peaje, titulo: str, subtitulo: str, ruta: str | Path) -> Path:
    """Guarda en `ruta` (PNG) el recorrido cerrado `tour`; `con_peaje[k]` indica si el arco tour[k] → tour[k+1]
    (el último cierra el ciclo) paga peaje. Devuelve la ruta."""
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    t = np.asarray(tour, dtype=int)
    con_peaje = np.asarray(con_peaje, dtype=bool)
    if con_peaje.shape != t.shape:
        raise ValueError(f"con_peaje debe tener un valor por arco ({t.size}); se recibió forma {con_peaje.shape}")
    u, v = t, np.roll(t, -1)

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with mpl.rc_context(parametros()):
        fig = Figure(figsize=TAMANO)
        FigureCanvasAgg(fig)
        ax = fig.add_subplot()
        for peaje, color, ancho, etiqueta in ((False, p.COLOR_RECORRIDO, ANCHO_SIN_PEAJE, "Tramo sin peaje"),
                                              (True, p.COLOR_PEAJE, ANCHO_PEAJE, "Tramo con peaje")):
            sel = con_peaje == peaje
            xs = np.column_stack([lon[u[sel]], lon[v[sel]], np.full(sel.sum(), np.nan)]).ravel()
            ys = np.column_stack([lat[u[sel]], lat[v[sel]], np.full(sel.sum(), np.nan)]).ravel()
            ax.plot(xs, ys, color=color, linewidth=ancho, label=f"{etiqueta} ({int(sel.sum())})", zorder=2)
        ax.scatter(lon, lat, s=TAMANO_CIUDAD, color=p.COLOR_CIUDAD, zorder=3, label=f"Capital ({lon.size})")
        ax.set_aspect(1 / math.cos(math.radians(float(np.mean(lat)))))  # grados de longitud más cortos al norte
        ax.set_xlabel("Longitud (°)")
        ax.set_ylabel("Latitud (°)")
        ax.set_title(f"{titulo}\n{subtitulo}", loc="left")
        ax.legend(loc="lower right")
        fig.text(0.01, 0.0, NOTA, color=p.TINTA_TENUE, fontsize="small")
        fig.savefig(ruta, format="png")
    return ruta
