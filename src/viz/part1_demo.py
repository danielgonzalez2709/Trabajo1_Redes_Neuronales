"""Figura de trayectoria del demo de la Parte 1 (T1.8, Spec §6.8): una corrida por método en 2D sobre curvas de nivel.

Un PNG por función: cada método de la lista aporta su corrida con frames (Spec §5.4: `result.frames`, cada uno
{iter, positions, best}). Convención común a todos los métodos: marcadores huecos = inicio, rellenos = final, trazo =
camino.

- Método con una posición por frame (GD): el camino une esa posición frame a frame.
- Método con población (EA, PSO, DE): población del primer y del último frame; el camino une el `best` de cada frame.

Solo lee lo que ya está en las corridas: no ejecuta optimizadores ni evalúa f en la trayectoria (el mejor f y
evaluaciones salen de `result.f_best` y `result.eval_equiv`). El fondo, de `part1_gifs._ejes`, sí evalúa f en una malla.

Sin la interfaz de estado global de matplotlib ni cambios en sus parámetros (Figure dentro de `rc_context`), como
src/viz/part1_gifs.py, del que toma el fondo, el mínimo global y el estilo. Mismos datos → mismos bytes.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib import patheffects
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from src.viz import paleta as p
from src.viz import part1_gifs as g
from src.viz.gifs import _num
from src.viz.style import DPI, parametros

DIM = 2  # la única dimensión con frames (Spec §5.4)

# ---- composición: la de los GIF (g.TAMANO, g.EJES), más alta si hay más rótulos o filas de leyenda que en ellos
ROTULOS_BASE = 2  # rótulos que caben sobre los ejes con g.TAMANO
FILAS_LEYENDA_BASE = 2  # filas de leyenda que caben bajo los ejes con g.TAMANO
ALTO_FILA = g.SALTO_ROTULO * g.TAMANO[1]  # pulgadas por rótulo o fila de leyenda añadidos

# ---- estilo
MARCADOR = "o"
ANCHO_BORDE_HUECO = 1.5  # borde, en el color del método, de los marcadores huecos
DECIMALES_EVAL = 1  # evaluaciones equivalentes no enteras (k no entero)

TITULO = "Trayectorias en {func} {dim}D · semilla {semilla}"
ROTULO = "{nombre}: mejor f = {f} · {evals} evaluaciones equivalentes"  # f_best = mejor valor visto
LEYENDA_GD = "{nombre}: camino del punto"
LEYENDA_POBLACION = "{nombre}: camino del mejor punto (población de {n})"
LEYENDA_INICIO = "Inicio (marcadores huecos)"
LEYENDA_FINAL = "Final (marcadores rellenos)"


# ------------------------------------------------------------------------------------------------ validación


def _validar(corridas: list[dict]) -> tuple[str, int]:
    """(func, semilla) comunes a `corridas`; ValueError si no hay corridas, alguna no es 2D o no trae frames, se
    mezclan funciones o semillas, o un método se repite."""
    if len(corridas) == 0:
        raise ValueError("figura de trayectoria: no se recibió ninguna corrida")
    for c in corridas:
        if c["dim"] != DIM:
            raise ValueError(f"figura de trayectoria: solo se dibuja en {DIM}D; la corrida de {c['method']} "
                             f"tiene dim = {c['dim']}")
        if not c["result"].get("frames"):
            raise ValueError(f"figura de trayectoria: la corrida de {c['method']} (semilla {c['seed']}) no trae "
                             "frames (result.frames); solo los guarda la primera semilla en 2D con record_frames")
    funciones = list(dict.fromkeys(c["func"] for c in corridas))
    if len(funciones) > 1:
        raise ValueError(f"figura de trayectoria: todas las corridas deben ser de la misma func; se recibieron "
                         f"{', '.join(funciones)}")
    semillas = list(dict.fromkeys(c["seed"] for c in corridas))
    if len(semillas) > 1:
        raise ValueError(f"figura de trayectoria: todas las corridas deben tener la misma semilla; se recibieron "
                         f"{', '.join(str(s) for s in semillas)}")
    metodos = [c["method"] for c in corridas]
    repetidos = [m for k, m in enumerate(metodos) if m in metodos[:k]]
    if repetidos:
        raise ValueError(f"figura de trayectoria: método repetido: {repetidos[0]}")
    return funciones[0], semillas[0]


# ------------------------------------------------------------------------------------------------ dibujo


def _evaluaciones(v: float) -> str:
    return _num(v, 0) if float(v).is_integer() else _num(v, DECIMALES_EVAL)


def _rotulo(corrida: dict) -> str:
    resultado = corrida["result"]
    return ROTULO.format(nombre=p.NOMBRE_METODO[corrida["method"]], f=g._cifras3(resultado["f_best"]),
                         evals=_evaluaciones(resultado["eval_equiv"]))


def _puntos(ax, xy: np.ndarray, color: str, tamano: float, gid: str, *, hueco: bool) -> None:
    """Marcadores sin línea: huecos (borde en el color del método) o rellenos (borde en tinta). No se recortan en
    el borde de los ejes: un punto sobre la frontera del dominio se ve entero."""
    if hueco:
        estilo = {"markerfacecolor": "none", "markeredgecolor": color, "markeredgewidth": ANCHO_BORDE_HUECO}
    else:
        estilo = {"markerfacecolor": color, "markeredgecolor": p.TINTA, "markeredgewidth": g.ANCHO_BORDE}
    ax.plot(xy[:, 0], xy[:, 1], linestyle="none", marker=MARCADOR, markersize=tamano, zorder=3 if hueco else 4,
            clip_on=False, gid=gid, **estilo)


def _metodo(ax, corrida: dict) -> Line2D:
    """Dibuja el camino, el inicio y el final de una corrida ("camino:{m}", "inicio:{m}", "final:{m}") y devuelve
    su entrada de la leyenda."""
    m, frames = corrida["method"], corrida["result"]["frames"]
    color = p.COLOR_METODO[m]
    es_poblacion = any(len(f["positions"]) > 1 for f in frames)
    if es_poblacion:
        camino = np.asarray([f["best"] for f in frames], dtype=float)
        tamano = g.TAMANO_PARTICULA
        etiqueta = LEYENDA_POBLACION.format(nombre=p.NOMBRE_METODO[m], n=len(frames[0]["positions"]))
    else:
        camino = np.asarray([f["positions"][0] for f in frames], dtype=float)
        tamano = g.TAMANO_MARCA
        etiqueta = LEYENDA_GD.format(nombre=p.NOMBRE_METODO[m])
    halo = [patheffects.Stroke(linewidth=g.ANCHO_HALO, foreground=p.SUPERFICIE), patheffects.Normal()]
    ax.plot(camino[:, 0], camino[:, 1], color=color, linestyle="-", linewidth=g.ANCHO_CAMINO, path_effects=halo,
            zorder=2, gid=f"camino:{m}")
    _puntos(ax, np.asarray(frames[0]["positions"], dtype=float), color, tamano, f"inicio:{m}", hueco=True)
    _puntos(ax, np.asarray(frames[-1]["positions"], dtype=float), color, tamano, f"final:{m}", hueco=False)
    return Line2D([], [], color=color, linestyle="-", linewidth=g.ANCHO_CAMINO, label=etiqueta)


def _entradas_comunes() -> list[Line2D]:
    inicio = Line2D([], [], linestyle="none", marker=MARCADOR, markersize=g.TAMANO_MARCA, markerfacecolor="none",
                    markeredgecolor=p.TINTA, markeredgewidth=ANCHO_BORDE_HUECO, label=LEYENDA_INICIO)
    final = Line2D([], [], linestyle="none", marker=MARCADOR, markersize=g.TAMANO_MARCA,
                   markerfacecolor=p.TINTA_TENUE, markeredgecolor=p.TINTA, markeredgewidth=g.ANCHO_BORDE,
                   label=LEYENDA_FINAL)
    return [inicio, final]


def _componer(fig: Figure, ax, n_rotulos: int, filas_leyenda: int) -> tuple[float, float]:
    """Alarga la figura lo que piden los rótulos y las filas de leyenda de más y recoloca los ejes, que conservan su
    tamaño en pulgadas. Devuelve (alto base, alto final) en pulgadas."""
    ancho, base = g.TAMANO
    arriba = max(0, n_rotulos - ROTULOS_BASE) * ALTO_FILA
    abajo = max(0, filas_leyenda - FILAS_LEYENDA_BASE) * ALTO_FILA
    alto = base + arriba + abajo
    fig.set_size_inches(ancho, alto)
    fig.set_dpi(DPI)
    x0, y0, w, h = g.EJES
    ax.set_position([x0, (y0 * base + abajo) / alto, w, h * base / alto])
    return base, alto


def _textos(fig: Figure, titulo: str, rotulos: list[tuple[str, str]], semilla: int, base: float, alto: float) -> None:
    """Título y rótulos medidos desde el borde superior, y nota desde el inferior, con las distancias de los GIF."""
    fig.text(g.X_TEXTO, 1.0 - (1.0 - g.Y_TITULO) * base / alto, titulo, color=p.TINTA, fontweight="bold", va="top",
             gid="titulo")
    for k, (gid, texto) in enumerate(rotulos):
        # distancia al borde superior en pulgadas (la del GIF más k filas), como fracción del alto final
        y = 1.0 - ((1.0 - g.Y_ROTULO) * base + k * ALTO_FILA) / alto
        fig.text(g.X_TEXTO, y, texto, color=p.TINTA, va="top", gid=gid)
    fig.text(g.X_TEXTO, g.Y_NOTA * base / alto, g.NOTA.format(semilla=semilla), color=p.TINTA_SECUNDARIA,
             fontsize="small", gid="nota")


def construir(corridas: list[dict]) -> Figure:
    """Figura con las `corridas` (dicts de Spec §5.4) de una función en 2D y una misma semilla, en el orden recibido.
    gid de los artistas: "camino:{m}", "inicio:{m}", "final:{m}", "x_star"; de los textos: "titulo", "rotulo:{m}",
    "nota". ValueError si la lista no se puede dibujar (ver `_validar`)."""
    func, semilla = _validar(corridas)
    with mpl.rc_context(parametros()):
        fig, ax = g._ejes(func)
        leyenda = [_metodo(ax, c) for c in corridas]
        leyenda += [*_entradas_comunes(), g._optimo(ax, func)]
        # una columna (las entradas de los métodos son largas): una fila por entrada
        base, alto = _componer(fig, ax, n_rotulos=len(corridas), filas_leyenda=len(leyenda))
        ax.legend(handles=leyenda, loc="upper center", bbox_to_anchor=g.LEYENDA_ANCLA, ncol=1)
        rotulos = [(f"rotulo:{c['method']}", _rotulo(c)) for c in corridas]
        _textos(fig, TITULO.format(func=func.capitalize(), dim=DIM, semilla=semilla), rotulos, semilla, base, alto)
    return fig


# ------------------------------------------------------------------------------------------------ PNG


def figura_trayectoria(corridas: list[dict], ruta: str | Path) -> Path:
    """Escribe en `ruta` el PNG de `construir(corridas)` y devuelve la ruta. Crea la carpeta si falta; si las corridas
    no se pueden dibujar lanza ValueError sin escribir nada."""
    fig = construir(corridas)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    g.imagen(fig).save(ruta, format="PNG")
    return ruta
