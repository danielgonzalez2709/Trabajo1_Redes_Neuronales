"""GIF de la Parte 1 (T4.3, Spec §6.7): trayectorias del GD y enjambre del PSO en 2D sobre curvas de nivel.

Tres GIF, uno por figura de `ARCHIVOS`: el GD de paso fijo y el de Armijo en Rosenbrock 2D y en Rastrigin 2D (las dos
variantes en la misma figura) y el enjambre del PSO en Rastrigin 2D. Solo leen `DATOS` (results/data/part1/
gif_trayectorias.json, de scripts/part1_gif_trayectorias.py): una corrida por variante, un fotograma por marca de
iteración. No ejecutan optimizadores; solo evalúan f en una malla para el fondo.

Sin pyplot ni cambios globales de matplotlib (Figure + FigureCanvasAgg dentro de `rc_context`), como src/viz/gifs.py;
los fotogramas se unen con Pillow. Mismos datos → mismos bytes. El fondo, los límites y la leyenda son iguales en
todos los fotogramas: solo cambian los trazos, los marcadores y los rótulos.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import NamedTuple

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import ListedColormap, to_rgb
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PIL import Image

from src.common.results import load_json
from src.part1.functions import get_function
from src.viz import paleta as p
from src.viz import part1_datos as pd1
from src.viz.gifs import _num
from src.viz.part1_interactivas import CONTORNO_LOG, NIVEL_LINEAL_PASO, NIVEL_LOG_MIN, NIVEL_LOG_PASO, PISO_LOG
from src.viz.style import mapa_secuencial, parametros

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "results" / "data" / "part1" / "gif_trayectorias.json"
SALIDA = RAIZ / "media"
COMANDO = "python scripts/part1_gif_trayectorias.py"  # genera DATOS
ARCHIVOS = {"gd_rosenbrock": "gd_rosenbrock_2d.gif", "gd_rastrigin": "gd_rastrigin_2d.gif",
            "pso_rastrigin": "pso_rastrigin_2d.gif"}

# ---- tiempo y tamaño
MS_FOTOGRAMA = 200
MS_FINAL = 3000  # el último fotograma se sostiene
TAMANO = (6.4, 6.2)  # pulgadas
DPI = 100
COLORES_GIF = 128  # colores de la paleta común a todos los fotogramas del GIF

# ---- colores de las series (= paleta.COLOR_METODO)
COLOR_GDFIJO = p.COLOR_METODO["gdfijo"]
COLOR_GDARMIJO = p.COLOR_METODO["gdarmijo"]
COLOR_PSO = p.COLOR_METODO["pso"]
COLOR_SERIE = {"gdfijo": COLOR_GDFIJO, "gdarmijo": COLOR_GDARMIJO}

# ---- fondo
MALLA_N = 200  # puntos por eje de las curvas de nivel
ALFA_FONDO = 0.55  # peso de la rampa frente a SUPERFICIE: el azul del GD de paso fijo debe verse sobre el fondo
PASOS_MAPA = 256  # colores del mapa aclarado

# ---- estilo de las series
METODOS_GD = ("gdfijo", "gdarmijo")
LINEA_GD = {"gdfijo": "-", "gdarmijo": "--"}
MARCADOR_GD = {"gdfijo": "o", "gdarmijo": "s"}
ANCHO_CAMINO = 2.0
ANCHO_HALO = 4.5  # halo en SUPERFICIE bajo cada camino
TAMANO_MARCA = 9
ANCHO_BORDE = 1.0  # borde en TINTA de los marcadores
TAMANO_X0 = 9
TAMANO_OPTIMO = 15
TAMANO_PARTICULA = 7
TAMANO_MEJOR = 19  # estrella hueca con borde en tinta, mayor que la de x*
ANCHO_BORDE_MEJOR = 1.5

# ---- composición (fracciones de la figura)
EJES = (0.1, 0.2, 0.84, 0.62)
Y_TITULO = 0.975
Y_ROTULO = 0.925
SALTO_ROTULO = 0.037
Y_NOTA = 0.012
X_TEXTO = 0.03
LEYENDA_ANCLA = (0.5, -0.09)

# ---- formato de f
CIFRAS = 3
FIJA_MIN, FIJA_MAX = 1e-2, 1e3  # en [FIJA_MIN, FIJA_MAX) notación fija; fuera, científica

TITULO_GD = "Descenso por gradiente en {func} {dim}D · semilla {semilla} · configuración por defecto"
TITULO_PSO = "PSO en {func} {dim}D · semilla {semilla} · configuración por defecto"
NOTA = "Una sola corrida (semilla {semilla}): ilustra la trayectoria, no el comportamiento medio."


class _Bloque(NamedTuple):
    """Textos del bloque `::: figura` de un GIF (el id sigue el patrón [a-z0-9-]+ del hook del blog)."""

    id: str
    titulo: str
    alt: str  # describe lo que se ve, sin afirmar resultados


FUENTE_BLOG = ("Elaboración propia a partir de results/data/part1/gif_trayectorias.json (python run.py figures). "
               "Corrida con la semilla 0, configuración por defecto.")
BLOQUES = {
    "gd_rosenbrock": _Bloque(
        "gif-gd-rosenbrock",
        "Trayectorias del descenso por gradiente de paso fijo y con Armijo sobre las curvas de nivel de Rosenbrock 2D",
        "Animación de las iteraciones del descenso por gradiente de paso fijo y con búsqueda de Armijo, desde un "
        "mismo punto inicial, sobre las curvas de nivel de la función de Rosenbrock en dos dimensiones"),
    "gd_rastrigin": _Bloque(
        "gif-gd-rastrigin",
        "Trayectorias del descenso por gradiente de paso fijo y con Armijo sobre las curvas de nivel de Rastrigin 2D",
        "Animación de las iteraciones del descenso por gradiente de paso fijo y con búsqueda de Armijo, desde un "
        "mismo punto inicial, sobre las curvas de nivel de la función de Rastrigin en dos dimensiones"),
    "pso_rastrigin": _Bloque(
        "gif-pso-rastrigin",
        "Movimiento del enjambre del PSO sobre las curvas de nivel de Rastrigin 2D",
        "Animación de las iteraciones del PSO: las 30 partículas y la mejor posición del enjambre sobre las curvas "
        "de nivel de la función de Rastrigin en dos dimensiones"),
}


# ------------------------------------------------------------------------------------------------ formato


def _cifras3(v: float) -> str:
    """f con 3 cifras significativas y coma decimal: 0 → "0"; |f| redondeado en [1e-2, 1e3) en notación fija
    ("4,97", "12,3", "0,0188", "5,00"); fuera, científica sin "+" ni ceros en el exponente ("1,88e-3", "1,23e3")."""
    if v == 0:
        return "0"
    cientifica = f"{v:.{CIFRAS - 1}e}"
    r = float(cientifica)  # el rango se decide con el valor ya redondeado (999,7 → 1,00e3)
    if FIJA_MIN <= abs(r) < FIJA_MAX:
        decimales = max(0, CIFRAS - 1 - math.floor(math.log10(abs(r))))
        return f"{r:.{decimales}f}".replace(".", ",")
    mantisa, exponente = cientifica.split("e")
    return f"{mantisa.replace('.', ',')}e{int(exponente)}"


def _semilla(meta: dict) -> int:
    return int(meta["base_seed"]) + int(meta["run_id"])


# ------------------------------------------------------------------------------------------------ dibujo


def _mapa_fondo() -> ListedColormap:
    """mapa_secuencial() mezclado con SUPERFICIE (peso ALFA_FONDO) y opaco: un relleno con alpha deja costuras
    oscuras entre bandas."""
    colores = mapa_secuencial()(np.linspace(0.0, 1.0, PASOS_MAPA))
    colores[:, :3] = ALFA_FONDO * colores[:, :3] + (1.0 - ALFA_FONDO) * np.asarray(to_rgb(p.SUPERFICIE))
    return ListedColormap(colores, name="secuencial_azul_aclarado")


def _ejes(nombre: str) -> tuple[Figure, object]:
    """Figura con los ejes del dominio (1:1) y el fondo de curvas de nivel rellenas de la función 2D."""
    func = get_function(nombre, 2)
    fig = Figure(figsize=TAMANO, dpi=DPI)
    FigureCanvasAgg(fig)
    ax = fig.add_axes(EJES)
    x, y, z = pd1.malla(nombre, MALLA_N)
    if CONTORNO_LOG[nombre]:
        z = np.log10(np.maximum(z, PISO_LOG))  # el piso solo protege de log10(0)
        tope = math.ceil(z.max() / NIVEL_LOG_PASO) * NIVEL_LOG_PASO
        niveles = np.arange(NIVEL_LOG_MIN, tope + NIVEL_LOG_PASO / 2, NIVEL_LOG_PASO)
    else:
        tope = math.ceil(z.max() / NIVEL_LINEAL_PASO) * NIVEL_LINEAL_PASO
        niveles = np.arange(0.0, tope + NIVEL_LINEAL_PASO / 2, NIVEL_LINEAL_PASO)
    ax.contourf(x, y, z, levels=niveles, cmap=_mapa_fondo(), extend="min", antialiased=False, zorder=0)
    (x0, x1), (y0, y1) = func.bounds.tolist()
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1.0, adjustable="box")
    ax.grid(False)
    ax.set_xlabel("x₁")
    ax.set_ylabel("x₂")
    return fig, ax


def _optimo(ax, nombre: str) -> Line2D:
    xs, ys = (float(v) for v in get_function(nombre, 2).x_star)
    (estrella,) = ax.plot([xs], [ys], linestyle="none", marker="*", markersize=TAMANO_OPTIMO,
                          markerfacecolor=p.TINTA, markeredgecolor=p.SUPERFICIE, markeredgewidth=ANCHO_BORDE,
                          zorder=3, gid="x_star", label=f"Mínimo global x* = ({xs:g}, {ys:g})")
    return estrella


def _textos(fig: Figure, titulo: str, rotulos: list[tuple[str, str]], semilla: int) -> None:
    fig.text(X_TEXTO, Y_TITULO, titulo, color=p.TINTA, fontweight="bold", va="top", gid="titulo")
    for k, (gid, texto) in enumerate(rotulos):
        fig.text(X_TEXTO, Y_ROTULO - k * SALTO_ROTULO, texto, color=p.TINTA, va="top", gid=gid)
    fig.text(X_TEXTO, Y_NOTA, NOTA.format(semilla=semilla), color=p.TINTA_SECUNDARIA, fontsize="small", gid="nota")


def _rotulo_gd(m: str, marca: int, variante: dict, j: int) -> str:
    it = min(marca, int(variante["n_iter"]))
    fin = ", terminó" if marca > int(variante["n_iter"]) else ""
    return f"{p.NOMBRE_METODO[m]}: iteración {_num(it, 0)}{fin} · f = {_cifras3(variante['f'][j])}"


def figura_gd(datos: dict, func: str, j: int) -> Figure:
    """Fotograma j del GIF del GD en `func`: camino de cada variante por x[0..j] (incluido x[j]) y marcador en x[j].
    gid de los artistas: "camino:{m}", "marca:{m}", "x0", "x_star"; de los textos: "titulo", "rotulo:{m}", "nota"."""
    meta, bloque = datos["meta"], datos["gd"][func]
    marca = int(bloque["iteraciones"][j])
    with mpl.rc_context(parametros()):
        fig, ax = _ejes(func)
        halo = [patheffects.Stroke(linewidth=ANCHO_HALO, foreground=p.SUPERFICIE), patheffects.Normal()]
        leyenda = []
        for m in METODOS_GD:
            x = np.asarray(bloque["metodos"][m]["x"], dtype=float)
            color = COLOR_SERIE[m]
            ax.plot(x[:j + 1, 0], x[:j + 1, 1], color=color, linestyle=LINEA_GD[m], linewidth=ANCHO_CAMINO,
                    path_effects=halo, zorder=2, gid=f"camino:{m}")
            ax.plot([x[j, 0]], [x[j, 1]], linestyle="none", marker=MARCADOR_GD[m], markersize=TAMANO_MARCA,
                    markerfacecolor=color, markeredgecolor=p.TINTA, markeredgewidth=ANCHO_BORDE, zorder=4,
                    gid=f"marca:{m}")
            leyenda.append(Line2D([], [], color=color, linestyle=LINEA_GD[m], linewidth=ANCHO_CAMINO,
                                  marker=MARCADOR_GD[m], markersize=TAMANO_MARCA, markerfacecolor=color,
                                  markeredgecolor=p.TINTA, markeredgewidth=ANCHO_BORDE, label=p.NOMBRE_METODO[m]))
        x0 = bloque["metodos"][METODOS_GD[0]]["x"][0]
        leyenda.append(ax.plot([x0[0]], [x0[1]], linestyle="none", marker="D", markersize=TAMANO_X0,
                               markerfacecolor=p.TINTA, markeredgecolor=p.SUPERFICIE, markeredgewidth=ANCHO_BORDE,
                               zorder=3, gid="x0", label="Punto inicial")[0])
        leyenda.append(_optimo(ax, func))
        ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=LEYENDA_ANCLA, ncol=2)
        semilla = _semilla(meta)
        rotulos = [(f"rotulo:{m}", _rotulo_gd(m, marca, bloque["metodos"][m], j)) for m in METODOS_GD]
        _textos(fig, TITULO_GD.format(func=func.capitalize(), dim=meta["dim"], semilla=semilla), rotulos, semilla)
    return fig


def figura_pso(datos: dict, j: int) -> Figure:
    """Fotograma j del GIF del PSO en Rastrigin: partículas y mejor del enjambre en la marca j.
    gid de los artistas: "enjambre", "mejor", "x_star"; de los textos: "titulo", "rotulo", "nota"."""
    meta, bloque = datos["meta"], datos["pso"]["rastrigin"]
    with mpl.rc_context(parametros()):
        fig, ax = _ejes("rastrigin")
        pos = np.asarray(bloque["enjambre"][j], dtype=float)
        particulas = ax.plot(pos[:, 0], pos[:, 1], linestyle="none", marker="o", markersize=TAMANO_PARTICULA,
                             markerfacecolor=COLOR_PSO, markeredgecolor=p.TINTA, markeredgewidth=ANCHO_BORDE,
                             zorder=4, gid="enjambre", label=f"Partículas ({len(pos)})")[0]
        estrella = _optimo(ax, "rastrigin")
        mx, my = bloque["mejor"][j]
        mejor = ax.plot([mx], [my], linestyle="none", marker="*", markersize=TAMANO_MEJOR,
                        markerfacecolor="none", markeredgecolor=p.TINTA, markeredgewidth=ANCHO_BORDE_MEJOR,
                        zorder=5, gid="mejor", label="Mejor del enjambre")[0]  # hueca: no tapa a las partículas
        ax.legend(handles=[particulas, mejor, estrella], loc="upper center", bbox_to_anchor=LEYENDA_ANCLA, ncol=2)
        semilla = _semilla(meta)
        rotulo = f"Iteración {_num(int(bloque['iteraciones'][j]), 0)} · mejor f = {_cifras3(bloque['f_mejor'][j])}"
        _textos(fig, TITULO_PSO.format(func="Rastrigin", dim=meta["dim"], semilla=semilla), [("rotulo", rotulo)],
                semilla)
    return fig


# --------------------------------------------------------------------------------------------- GIF


def imagen(fig: Figure) -> Image.Image:
    """Rasteriza la figura (RGB)."""
    with mpl.rc_context(parametros()):
        fig.canvas.draw()
        return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())).convert("RGB")


def paleta_comun(rgb: list[Image.Image]) -> Image.Image:
    """Paleta única del GIF: MEDIANCUT sobre el montaje vertical de TODOS los fotogramas. Con una paleta por
    fotograma, un mismo color (fondo, leyenda, series) cambiaba entre fotogramas."""
    ancho, alto = rgb[0].size
    montaje = Image.new("RGB", (ancho, alto * len(rgb)))
    for k, im in enumerate(rgb):
        montaje.paste(im, (0, k * alto))
    return montaje.quantize(colors=COLORES_GIF, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def guardar_gif(figuras, ruta: str | Path) -> Path:
    """Une las figuras (iterable de Figure) en un GIF: [MS_FOTOGRAMA]·(n−1) + [MS_FINAL] ms, bucle infinito; todos
    los fotogramas con la misma paleta (`paleta_comun`) y sin dithering."""
    rgb = [imagen(f) for f in figuras]
    ref = paleta_comun(rgb)
    imagenes = [im.quantize(palette=ref, dither=Image.Dither.NONE) for im in rgb]
    duraciones = [MS_FOTOGRAMA] * (len(imagenes) - 1) + [MS_FINAL]
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagenes[0].save(ruta, save_all=True, append_images=imagenes[1:], duration=duraciones, loop=0, optimize=False)
    return ruta


def generar_gifs(datos: Path = DATOS, salida: Path | None = None) -> list[Path]:
    """Escribe en `salida` (None = SALIDA) los tres GIF de `ARCHIVOS` desde el JSON `datos` y devuelve sus rutas."""
    d = load_json(datos)
    salida = Path(SALIDA if salida is None else salida)
    rutas = []
    for func in ("rosenbrock", "rastrigin"):
        n = len(d["gd"][func]["iteraciones"])
        rutas.append(guardar_gif((figura_gd(d, func, j) for j in range(n)), salida / ARCHIVOS[f"gd_{func}"]))
    n = len(d["pso"]["rastrigin"]["iteraciones"])
    rutas.append(guardar_gif((figura_pso(d, j) for j in range(n)), salida / ARCHIVOS["pso_rastrigin"]))
    return rutas


# --------------------------------------------------------------------------------------------- blog


def bloques_blog(rutas: list[Path]) -> str:
    """Bloques `::: figura` (formato de blog/README.md) de los GIF de `ARCHIVOS` cuyo archivo está en `rutas`."""
    nombres = {Path(r).name for r in rutas}
    return "\n\n".join(
        f"::: figura {b.id}\nTítulo: {b.titulo}\nFuente: {FUENTE_BLOG}\n![{b.alt}](figures/{ARCHIVOS[clave]})\n:::"
        for clave, b in BLOQUES.items() if ARCHIVOS[clave] in nombres)
