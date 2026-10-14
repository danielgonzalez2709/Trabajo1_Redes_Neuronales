"""Figuras interactivas de la Parte 1 (T4.2; Spec §6.7, puntos 1, 2, 3 y 5) con Plotly.

Las figuras NO ejecutan optimizadores (Spec §4): leen los JSON de `results/data/part1/` (por defecto) y
`results/data/part1_tuned/` (afinado, T1.10) con `part1_datos`. Solo se evalúa f en una malla para dibujar curvas de
nivel y la superficie, y en las posiciones guardadas del enjambre para su altura (z = f(posición)).

Las ocho figuras (id, archivo, título y fuente en `FIGURAS`, única fuente de esos textos):
- contornos de Rosenbrock (niveles logarítmicos: se dibuja log10 f) y de Rastrigin;
- convergencia (mediana + banda intercuartílica de f − f* contra evaluaciones equivalentes, ejes log) y cajas de
  f final − f*, con selector de celda función × dimensión;
- las mismas dos comparando por defecto (trazo continuo / caja rellena) contra afinado (discontinuo / caja hueca),
  solo para los métodos cuyo bloque de hiperparámetros cambió (`part1_datos.metodos_afinados`);
- deslizador de η del GD de paso fijo en Rosenbrock 2D (lee `eta_deslizador.json`, de scripts/part1_eta_deslizador.py);
- superficie de Rastrigin 2D con el enjambre del PSO y deslizador de iteración.

Eje log con ceros: DE y PSO llegan a f − f* = 0 exacto; esos valores se dibujan en `PISO_LOG`. Es una decisión de
dibujo, no un dato, y se declara en el título del eje y en la fuente de la figura (`TEXTO_PISO`).

Los HTML son fragmentos (sin <html>) para el `incluir:` del blog y cargan plotly.js desde su CDN, como los de la
Parte 2. Si faltan corridas (las carpetas `runs/` no se versionan) se avisa con el comando que las genera y no se
lanza excepción. Uso: `python run.py figures`.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import NamedTuple

import numpy as np
import plotly.graph_objects as go

from src.common.results import load_json
from src.part1.functions import get_function
from src.part1.metricas import UMBRAL_PRINCIPAL
from src.viz import paleta as p
from src.viz import part1_datos as pd1
from src.viz.theme import aplicar_tema

RAIZ = Path(__file__).resolve().parents[2]
RES_DEFECTO = RAIZ / "results" / "data" / "part1"
RES_AFINADO = RAIZ / "results" / "data" / "part1_tuned"
SALIDA = RAIZ / "blog" / "docs" / "figures"
ARCHIVO_ETA = "eta_deslizador.json"  # dentro de la carpeta del experimento por defecto
COMANDO = {
    "defecto": "python run.py part1 --config configs/part1/base.yaml",
    "afinado": "python run.py part1 --config configs/part1/tuned.yaml",
    "eta": "python scripts/part1_eta_deslizador.py",
}

PISO_LOG = 1e-16  # los valores menores (incluido el 0 exacto) se dibujan aquí: un eje log no admite ceros
TEXTO_PISO = f"los valores menores que {PISO_LOG:g} (incluido el 0 exacto) se dibujan en {PISO_LOG:g}"


class Figura(NamedTuple):
    id: str  # id del bloque `::: figura <id>` del blog (patrón [a-z0-9-]+)
    archivo: str
    titulo: str
    fuente: str


_FUENTE_DEFECTO = "Elaboración propia a partir de las corridas de results/data/part1/runs/"
_FUENTE_AFINADO = ("Elaboración propia a partir de las corridas de results/data/part1/runs/ (por defecto) y "
                   "results/data/part1_tuned/runs/ (afinado)")
_FUENTE_FUNCION = "Elaboración propia a partir de la definición de la función (src/part1/functions.py)."

FIGURAS: dict[str, Figura] = {
    "contorno_rosenbrock": Figura(
        "contorno-rosenbrock", "part1_contorno_rosenbrock.html",
        "Curvas de nivel de la función de Rosenbrock en dos dimensiones (niveles en escala logarítmica)",
        _FUENTE_FUNCION),
    "contorno_rastrigin": Figura(
        "contorno-rastrigin", "part1_contorno_rastrigin.html",
        "Curvas de nivel de la función de Rastrigin en dos dimensiones", _FUENTE_FUNCION),
    "convergencia": Figura(
        "convergencia-part1", "part1_convergencia.html",
        "Convergencia de los métodos con la configuración por defecto: mediana y rango intercuartílico de "
        "f − f* frente a las evaluaciones equivalentes",
        f"{_FUENTE_DEFECTO}; en el eje logarítmico {TEXTO_PISO}."),
    "cajas": Figura(
        "cajas-part1", "part1_cajas.html",
        "Distribución de f final − f* por método con la configuración por defecto",
        f"{_FUENTE_DEFECTO}; en el eje logarítmico {TEXTO_PISO}."),
    "convergencia_afinado": Figura(
        "convergencia-afinado-part1", "part1_convergencia_afinado.html",
        "Convergencia por defecto (trazo continuo) frente a afinada (trazo discontinuo) de los métodos cuyos "
        "hiperparámetros cambiaron con el ajuste",
        f"{_FUENTE_AFINADO}; en el eje logarítmico {TEXTO_PISO}."),
    "cajas_afinado": Figura(
        "cajas-afinado-part1", "part1_cajas_afinado.html",
        "Distribución de f final − f* por defecto (caja rellena) y afinada (caja hueca) de los métodos cuyos "
        "hiperparámetros cambiaron con el ajuste",
        f"{_FUENTE_AFINADO}; en el eje logarítmico {TEXTO_PISO}."),
    "eta": Figura(
        "eta-rosenbrock", "part1_eta_rosenbrock.html",
        "Trayectoria del descenso de gradiente de paso fijo en Rosenbrock 2D según el tamaño de paso η",
        "Elaboración propia a partir de results/data/part1/eta_deslizador.json."),
    "enjambre": Figura(
        "enjambre-rastrigin", "part1_enjambre_rastrigin.html",
        "Enjambre del PSO sobre la superficie de Rastrigin 2D a lo largo de las iteraciones",
        f"{_FUENTE_DEFECTO} (PSO en Rastrigin 2D, primera semilla)."),
}
NECESITAN_DEFECTO = ("convergencia", "cajas", "enjambre")
NECESITAN_AFINADO = ("convergencia_afinado", "cajas_afinado")

# ---- constantes de dibujo
MALLA = {"rosenbrock": 151, "rastrigin": 201}  # puntos por eje de las curvas de nivel
# (Rastrigin: 200 intervalos en un dominio de 10,24 períodos por eje ≈ 19,5 intervalos por período)
MALLA_SUPERFICIE = 121  # puntos por eje de la superficie 3D
CONTORNO_LOG = {"rosenbrock": True, "rastrigin": False}  # Rosenbrock varía varios órdenes de magnitud: log10 f
NIVEL_LOG_MIN = -2.0  # primer nivel de log10 f de Rosenbrock
NIVEL_LOG_PASO = 0.5
NIVEL_LINEAL_PASO = 10.0  # separación entre niveles de f en Rastrigin
CIFRAS = 6  # cifras significativas de las curvas en el HTML
CIFRAS_MALLA = 4  # cifras significativas de z en mallas y superficie
DECIMALES_POSICION = 5  # decimales de las coordenadas de trayectorias y partículas
ALFA_BANDA = 0.15
ALFA_CAJA = 0.45
OPACIDAD_SUPERFICIE = 0.85
DISPERSION_PUNTOS = 0.5  # `jitter` de los puntos de las cajas
PASOS_ENJAMBRE = 30  # pasos (como máximo) del deslizador de iteración
ENJAMBRE = ("rastrigin", 2, "pso")  # configuración cuya primera semilla trae los frames que se dibujan
NOMBRE_VARIANTE = {"defecto": "por defecto", "afinado": "afinado"}
DASH_VARIANTE = {"defecto": "solid", "afinado": "dash"}
SIMBOLO_VARIANTE = {"defecto": "circle", "afinado": "circle-open"}
# Etiqueta del paso marcado del deslizador de η; "afinado" baja una línea más para no pisar a "por defecto" (pasos
# vecinos).
ETIQUETA_MARCA = {"defecto": "<br>por defecto", "afinado": "<br><br>afinado"}
TAMANO_OPTIMO = 14
TAMANO_TRAYECTORIA = 4
TAMANO_PARTICULA = 4
FUENTE_DESLIZADOR = 10
MARGEN_EJE_Y = 110  # margen izquierdo de los ejes log: caben los rótulos anchos (10^−15) y el título del eje
SEPARACION_EJE_Y = 14  # `standoff` entre los rótulos y el título del eje y
PLOTLY_JS = "cdn"
CONFIG_PLOTLY = {"responsive": True, "displaylogo": False}
SEPARADORES = ", "  # coma decimal y espacio de miles
ALTO = {"contorno_rosenbrock": 620, "contorno_rastrigin": 620, "convergencia": 600, "cajas": 560,
        "convergencia_afinado": 600, "cajas_afinado": 560, "eta": 800, "enjambre": 760}
TAMANO_MAX = 500_000  # bytes por HTML


# ------------------------------------------------------------------------------------------------ formato


def _cient(x: float, cifras: int = 3) -> str:
    """1.494e-3 → "1,49e-3"; 0.001 → "1e-3"; 0 → "0" (coma decimal, exponente sin ceros)."""
    if x == 0:
        return "0"
    mantisa, exponente = f"{x:.{cifras - 1}e}".split("e")
    mantisa = mantisa.rstrip("0").rstrip(".") if "." in mantisa else mantisa
    return f"{mantisa.replace('.', ',')}e{int(exponente)}"


def _rgba(hex_color: str, alfa: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def _sig(valores, cifras: int) -> list:
    """Lista con `cifras` significativas; NaN → None (hueco en la curva)."""
    return [None if math.isnan(v) else float(f"{v:.{cifras}g}") for v in np.asarray(valores, dtype=float).ravel()]


def _matriz(z: np.ndarray) -> list[list]:
    return [_sig(fila, CIFRAS_MALLA) for fila in z]


def _pos(valores) -> list[float]:
    return [round(float(v), DECIMALES_POSICION) for v in valores]


def _con_piso(valores) -> np.ndarray:
    """Recorta a PISO_LOG para el eje log (NaN se conserva)."""
    return np.maximum(np.asarray(valores, dtype=float), PISO_LOG)


def _celda(func: str, dim: int) -> str:
    return f"{func.capitalize()} {dim}D"


def muestreo(n: int, maximo: int) -> np.ndarray:
    """Hasta `maximo` índices de 0..n−1 espaciados geométricamente (todos si n <= maximo); incluye el primero y el
    último."""
    if n <= maximo:
        return np.arange(n)
    return np.unique(np.rint(np.geomspace(1, n, maximo)).astype(int)) - 1


_ESCALA_AZUL = [[i / (len(p.SECUENCIAL_AZUL) - 1), c] for i, c in enumerate(p.SECUENCIAL_AZUL)]


def _marca_optimo(func) -> go.Scatter:
    x, y = (float(v) for v in func.x_star)
    return go.Scatter(x=[x], y=[y], mode="markers", meta="x_star", name=f"Mínimo global x* = ({x:g}, {y:g})",
                      marker=dict(symbol="star", size=TAMANO_OPTIMO, color=p.TINTA,
                                  line=dict(color=p.SUPERFICIE, width=1)),
                      hovertemplate=f"x* = ({x:g}, {y:g}), f* = {func.f_star:g}<extra></extra>")


def _ejes_dominio(func) -> dict:
    (x0, x1), (y0, y1) = func.bounds.tolist()
    return dict(xaxis=dict(title=dict(text="x₁"), range=[x0, x1], constrain="domain"),
                yaxis=dict(title=dict(text="x₂"), range=[y0, y1], scaleanchor="x", constrain="domain"))


# ---------------------------------------------------------------------------------------- curvas de nivel


def _contorno(nombre: str, solo_lineas: bool = False) -> go.Contour:
    """Curvas de nivel de la función 2D. Rosenbrock: z = log10 f (niveles logarítmicos). `solo_lineas`: sin relleno
    y en gris, como fondo de una trayectoria."""
    x, y, z = pd1.malla(nombre, MALLA[nombre])
    if CONTORNO_LOG[nombre]:
        z = np.log10(np.maximum(z, PISO_LOG))  # el piso solo protege de log10(0) si la malla cae en x*
        tope = float(np.ceil(z.max() / NIVEL_LOG_PASO) * NIVEL_LOG_PASO)
        exponentes = list(range(int(NIVEL_LOG_MIN), int(math.floor(z.max())) + 1))
        extra = dict(
            autocontour=False, contours=dict(start=NIVEL_LOG_MIN, end=tope, size=NIVEL_LOG_PASO),
            colorbar=dict(title=dict(text="f (escala log)"), tickvals=exponentes,
                          ticktext=[f"10<sup>{e}</sup>" for e in exponentes]),
            hovertemplate="x₁ = %{x:.3f}<br>x₂ = %{y:.3f}<br>log₁₀ f = %{z:.2f}<extra></extra>",
        )
    else:
        tope = float(np.floor(z.max() / NIVEL_LINEAL_PASO) * NIVEL_LINEAL_PASO)
        extra = dict(autocontour=False, contours=dict(start=NIVEL_LINEAL_PASO, end=tope, size=NIVEL_LINEAL_PASO),
                     colorbar=dict(title=dict(text="f")),
                     hovertemplate="x₁ = %{x:.3f}<br>x₂ = %{y:.3f}<br>f = %{z:.2f}<extra></extra>")
    if solo_lineas:
        extra.pop("colorbar")
        extra["contours"] = {**extra.get("contours", {}), "coloring": "lines"}
        extra.update(colorscale=[[0, p.EJE], [1, p.EJE]], showscale=False, hoverinfo="skip", hovertemplate=None)
    else:
        extra.update(colorscale=_ESCALA_AZUL, line=dict(width=0.5, color=p.SUPERFICIE))
    return go.Contour(x=_sig(x, CIFRAS), y=_sig(y, CIFRAS), z=_matriz(z), meta="contorno", showlegend=False, **extra)


def figura_contorno(nombre: str) -> go.Figure:
    """Curvas de nivel de la función en su dominio, con la marca del mínimo global."""
    aplicar_tema()
    func = get_function(nombre, 2)
    fig = go.Figure([_contorno(nombre), _marca_optimo(func)])
    paso = f"{NIVEL_LOG_PASO:g}".replace(".", ",") if CONTORNO_LOG[nombre] else f"{NIVEL_LINEAL_PASO:g}"
    niveles = (f"Niveles logarítmicos: de una curva a la siguiente, f se multiplica por 10^{paso}"
               if CONTORNO_LOG[nombre] else f"Una curva de nivel cada {paso} unidades de f")
    fig.update_layout(
        title=dict(text=f"Curvas de nivel de {nombre.capitalize()} 2D", subtitle=dict(text=niveles), x=0,
                   xanchor="left"),
        hovermode="closest", separators=SEPARADORES, legend=dict(y=-0.15, yanchor="top"),
        margin=dict(t=84, b=100), **_ejes_dominio(func),
    )
    return fig


# ----------------------------------------------------------------- series por defecto / afinado y selector


def _series(defecto: dict, afinado: dict | None, metodos: dict | None) -> list[tuple]:
    """[(func, dim, method, variante, corridas)] en orden de celda, método y variante. Sin `afinado`: todos los
    métodos, solo por defecto. Con `afinado`: solo `metodos[(func, dim)]`, las dos variantes."""
    series = []
    for func, dim in pd1.celdas(defecto):
        elegidos = pd1.metodos_de(defecto, func, dim) if afinado is None else metodos.get((func, dim), [])
        for method in elegidos:
            series.append((func, dim, method, "defecto", defecto[(func, dim, method)]))
            if afinado is not None:
                series.append((func, dim, method, "afinado", afinado[(func, dim, method)]))
    return series


def _nombre_serie(method: str, variante: str, comparacion: bool) -> str:
    return f"{p.NOMBRE_METODO[method]} · {NOMBRE_VARIANTE[variante]}" if comparacion else p.NOMBRE_METODO[method]


def _selector(fig: go.Figure, grupos: list[tuple], titulos: dict) -> None:
    """Menú con una opción por celda (func, dim): muestra solo sus trazas y cambia el título. Deja visible la
    primera celda."""
    celdas = list(titulos)
    for traza, grupo in zip(fig.data, grupos):
        traza.visible = grupo == celdas[0]
    botones = [dict(method="update", label=_celda(*c),
                    args=[{"visible": [g == c for g in grupos]}, {"title.text": titulos[c]}]) for c in celdas]
    fig.update_layout(
        title=dict(text=titulos[celdas[0]], x=0, xanchor="left"),
        updatemenus=[dict(buttons=botones, active=0, direction="down", x=1, xanchor="right", y=1.03,
                          yanchor="bottom")],
    )


def _eje_y_log(texto: str) -> dict:
    """Eje y logarítmico; el título declara el piso de dibujo (el detalle, `TEXTO_PISO`, va en el subtítulo)."""
    return dict(type="log", exponentformat="power",
                title=dict(text=f"{texto} (escala log, piso de dibujo en {PISO_LOG:g})", standoff=SEPARACION_EJE_Y))


# -------------------------------------------------------------------------------------------- convergencia


def figura_convergencia(defecto: dict, afinado: dict | None = None, metodos: dict | None = None) -> go.Figure:
    """Mediana y banda intercuartílica de f − f* contra evaluaciones equivalentes (ejes log), por celda.

    `defecto` y `afinado`: {(func, dim, method): [corridas]}. Con `afinado`, solo los métodos de `metodos[(func, dim)]`
    y dos curvas por método (continua = por defecto, discontinua = afinado). `meta` de cada traza:
    "{mediana|q25|q75}:{func}:{dim}:{method}:{variante}"."""
    aplicar_tema()
    comparacion = afinado is not None
    fig = go.Figure()
    grupos, titulos = [], {}
    for func, dim, method, variante, corridas in _series(defecto, afinado, metodos):
        curva = pd1.curva_convergencia(corridas, get_function(func, dim).f_star)
        x = curva["rejilla"].tolist()
        color, nombre = p.COLOR_METODO[method], _nombre_serie(method, variante, comparacion)
        clave = f"{func}:{dim}:{method}:{variante}"
        fig.add_trace(go.Scatter(x=x, y=_sig(_con_piso(curva["q25"]), CIFRAS), mode="lines", line=dict(width=0),
                                 meta=f"q25:{clave}", showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=_sig(_con_piso(curva["q75"]), CIFRAS), mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=_rgba(color, ALFA_BANDA), meta=f"q75:{clave}",
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=x, y=_sig(_con_piso(curva["mediana"]), CIFRAS), mode="lines", meta=f"mediana:{clave}", name=nombre,
            line=dict(color=color, dash=DASH_VARIANTE[variante]),
            hovertemplate=f"{nombre}: %{{y:.3e}} (mediana)<extra></extra>",
        ))
        grupos += [(func, dim)] * 3
        titulos[(func, dim)] = (f"Convergencia en {_celda(func, dim)} (mediana y rango intercuartílico de "
                                f"{len(corridas)} corridas)")
    _selector(fig, grupos, titulos)
    fig.add_shape(type="line", xref="paper", x0=0, x1=1, y0=UMBRAL_PRINCIPAL, y1=UMBRAL_PRINCIPAL,
                  line=dict(color=p.TINTA_SECUNDARIA, width=1, dash="dot"))
    # En un eje log las anotaciones se colocan con log10 del valor (las formas, con el valor).
    fig.add_annotation(xref="paper", x=1, xanchor="right", y=math.log10(UMBRAL_PRINCIPAL), yanchor="bottom",
                       showarrow=False, font=dict(color=p.TINTA_SECUNDARIA, size=12),
                       text=f"Umbral de éxito: f − f* ≤ {_cient(UMBRAL_PRINCIPAL)}")
    variantes = " · continua: por defecto; discontinua: afinado" if comparacion else ""
    fig.update_layout(
        title=dict(subtitle=dict(text=f"k = 2n evaluaciones equivalentes por gradiente{variantes}"
                                      f"<br>Piso de dibujo: {TEXTO_PISO}")),
        xaxis=dict(type="log", title=dict(text="Evaluaciones equivalentes (escala log)")),
        yaxis=_eje_y_log("f − f*"),
        height=ALTO["convergencia"], separators=SEPARADORES,
        legend=dict(y=-0.2, yanchor="top", traceorder="normal"), margin=dict(l=MARGEN_EJE_Y, t=130, b=130),
    )
    return fig


# --------------------------------------------------------------------------------------------------- cajas


def figura_cajas(defecto: dict, afinado: dict | None = None, metodos: dict | None = None) -> go.Figure:
    """Cajas de f final − f* por método (eje y log), con los puntos de todas las corridas, por celda.

    Con `afinado`: por método, la caja por defecto (rellena, puntos llenos) junto a la afinada (hueca, puntos huecos),
    solo para `metodos[(func, dim)]`. `meta` de cada traza: "caja:{func}:{dim}:{method}:{variante}"."""
    aplicar_tema()
    comparacion = afinado is not None
    fig = go.Figure()
    grupos, titulos = [], {}
    for func, dim, method, variante, corridas in _series(defecto, afinado, metodos):
        y = _con_piso(pd1.f_finales(corridas, get_function(func, dim).f_star)).tolist()
        color = p.COLOR_METODO[method]
        etiqueta = (f"{p.NOMBRE_METODO[method]}<br>{NOMBRE_VARIANTE[variante]}" if comparacion
                    else p.NOMBRE_METODO[method])
        fig.add_trace(go.Box(
            x=[etiqueta] * len(y), y=y, name=_nombre_serie(method, variante, comparacion), showlegend=False,
            meta=f"caja:{func}:{dim}:{method}:{variante}", boxpoints="all", jitter=DISPERSION_PUNTOS, pointpos=0,
            line=dict(color=color, width=p.ANCHO_LINEA),
            fillcolor=_rgba(color, ALFA_CAJA) if variante == "defecto" else p.SUPERFICIE,
            marker=dict(color=color, symbol=SIMBOLO_VARIANTE[variante], size=p.TAMANO_MARCADOR - 2),
            hovertemplate="%{y:.3e}<extra>" + _nombre_serie(method, variante, comparacion) + "</extra>",
        ))
        grupos.append((func, dim))
        titulos[(func, dim)] = f"f final − f* en {_celda(func, dim)} ({len(corridas)} corridas por caja)"
    _selector(fig, grupos, titulos)
    variantes = "Caja rellena: por defecto · caja hueca: afinado · " if comparacion else ""
    fig.update_layout(
        title=dict(subtitle=dict(text=f"{variantes}Cada punto es una corrida<br>Piso de dibujo: {TEXTO_PISO}")),
        xaxis=dict(title=dict(text="Método"), showgrid=False), yaxis=_eje_y_log("f final − f*"),
        height=ALTO["cajas"], separators=SEPARADORES, hovermode="closest", margin=dict(l=MARGEN_EJE_Y, t=130, b=90),
    )
    return fig


# ------------------------------------------------------------------------------------------ deslizador de η


def _textos_eta(entrada: dict, f_star: float, resumen: str) -> tuple[str, str]:
    marca = f" ({NOMBRE_VARIANTE[entrada['marca']]})" if entrada["marca"] else ""
    titulo = f"GD de paso fijo en Rosenbrock 2D · η = {_cient(entrada['eta'])}{marca}"
    # `f_best` es el mejor punto visto (Spec §5.1), no la f del último iterado: con η grande pueden diferir.
    subtitulo = (f"Mejor f − f* visto = {_cient(entrada['f_best'] - f_star)} · {entrada['n_iter']} iteraciones "
                 f"({entrada['n_grad']} gradientes)<br>{resumen}")
    return titulo, subtitulo


def figura_eta(datos: dict) -> go.Figure:
    """Curvas de nivel de Rosenbrock y la trayectoria del GD de paso fijo; un paso del deslizador por entrada de
    `datos["etas"]` (contrato de `eta_deslizador.json`). Arranca en el η marcado "defecto" (si no hay, en el primero).
    `meta`: "contorno", "eta:{k}", "x0", "x_star"."""
    aplicar_tema()
    meta, etas = datos["meta"], datos["etas"]
    func = get_function(meta["func"], meta["dim"])
    color = p.COLOR_METODO[meta["method"]]
    activo = next((k for k, e in enumerate(etas) if e["marca"] == "defecto"), 0)
    marcados = [f"{NOMBRE_VARIANTE[e['marca']].capitalize()}: η = {_cient(e['eta'])}" for e in etas if e["marca"]]
    resumen = " · ".join(marcados + [f"semilla {meta['seed']}, mismo punto inicial para todos los η"])
    resumen += "<br>El deslizador cambia el tamaño de paso η"

    fig = go.Figure([_contorno(meta["func"], solo_lineas=True)])
    for k, e in enumerate(etas):
        xs, ys = zip(*e["puntos"])
        fig.add_trace(go.Scatter(
            x=_pos(xs), y=_pos(ys), customdata=list(e["iteraciones"]), mode="lines+markers", meta=f"eta:{k}",
            name="Trayectoria del GD (iterados submuestreados)", visible=k == activo,
            line=dict(color=color, width=1), marker=dict(color=color, size=TAMANO_TRAYECTORIA),
            hovertemplate="iteración %{customdata}<br>x = (%{x:.4f}; %{y:.4f})<extra></extra>",
        ))
    x0 = [float(v) for v in meta["x0"]]
    fig.add_trace(go.Scatter(
        x=[x0[0]], y=[x0[1]], mode="markers", meta="x0", name="Punto inicial x₀",
        marker=dict(symbol="diamond", size=TAMANO_OPTIMO - 2, color=p.TINTA, line=dict(color=p.SUPERFICIE, width=1)),
        hovertemplate="x₀ = (%{x:.4f}; %{y:.4f})<extra></extra>",
    ))
    fig.add_trace(_marca_optimo(func))

    n_fijas_antes, n = 1, len(etas)  # contorno antes de las trayectorias; x0 y x* después
    steps, textos = [], []
    for k, e in enumerate(etas):
        titulo, subtitulo = _textos_eta(e, func.f_star, resumen)
        textos.append((titulo, subtitulo))
        visible = [True] * n_fijas_antes + [i == k for i in range(n)] + [True, True]
        steps.append(dict(method="update", label=_cient(e["eta"]) + ETIQUETA_MARCA.get(e["marca"], ""),
                          args=[{"visible": visible}, {"title.text": titulo, "title.subtitle.text": subtitulo}]))
    fig.update_layout(
        title=dict(text=textos[activo][0], subtitle=dict(text=textos[activo][1]), x=0, xanchor="left"),
        sliders=[dict(active=activo, steps=steps, currentvalue=dict(visible=False), transition=dict(duration=0),
                      font=dict(size=FUENTE_DESLIZADOR), pad=dict(t=80))],
        hovermode="closest", height=ALTO["eta"], separators=SEPARADORES,
        legend=dict(y=-0.5, yanchor="top"), margin=dict(t=150, b=230), **_ejes_dominio(func),
    )
    return fig


# ------------------------------------------------------------------------------------------------ enjambre


def figura_enjambre(corrida: dict) -> go.Figure:
    """Superficie de la función 2D de la corrida y las partículas de sus `frames` (z = f(posición)), con un
    deslizador de iteración de hasta PASOS_ENJAMBRE pasos geométricos. `meta`: "superficie", "enjambre:{iter}",
    "x_star"."""
    aplicar_tema()
    func = get_function(corrida["func"], corrida["dim"])
    method, frames = corrida["method"], corrida["result"]["frames"]
    color = p.COLOR_METODO[method]
    elegidos = [frames[i] for i in muestreo(len(frames), PASOS_ENJAMBRE)]
    x, y, z = pd1.malla(corrida["func"], MALLA_SUPERFICIE)
    fig = go.Figure([go.Surface(
        x=_sig(x, CIFRAS), y=_sig(y, CIFRAS), z=_matriz(z), meta="superficie", colorscale=_ESCALA_AZUL,
        opacity=OPACIDAD_SUPERFICIE, showscale=False, hoverinfo="skip", showlegend=False,
        contours=dict(x=dict(highlight=False), y=dict(highlight=False), z=dict(highlight=False)),
    )])
    for k, frame in enumerate(elegidos):
        pos = np.asarray(frame["positions"], dtype=float)
        fig.add_trace(go.Scatter3d(
            x=_pos(pos[:, 0]), y=_pos(pos[:, 1]), z=_sig([func.f(q) for q in pos], CIFRAS), mode="markers",
            meta=f"enjambre:{frame['iter']}", name=f"Partículas ({len(pos)})", visible=k == 0,
            marker=dict(color=color, size=TAMANO_PARTICULA, line=dict(color=p.TINTA, width=1)),
            hovertemplate="x = (%{x:.3f}; %{y:.3f})<br>f = %{z:.3e}<extra></extra>",
        ))
    xs, ys = (float(v) for v in func.x_star)
    fig.add_trace(go.Scatter3d(
        x=[xs], y=[ys], z=[func.f_star], mode="markers", meta="x_star", name=f"Mínimo global x* = ({xs:g}, {ys:g})",
        marker=dict(color=p.TINTA, size=TAMANO_PARTICULA + 1, symbol="diamond"),
        hovertemplate=f"x* = ({xs:g}, {ys:g}), f* = {func.f_star:g}<extra></extra>",
    ))

    ultima = frames[-1]["iter"]
    subtitulo_fijo = f"{p.NOMBRE_METODO[method]}, semilla {corrida['seed']} · altura de cada partícula: z = f(posición)"
    steps, textos = [], []
    for k, frame in enumerate(elegidos):
        titulo = f"{p.NOMBRE_METODO[method]} en {_celda(corrida['func'], corrida['dim'])} · iteración {frame['iter']} de {ultima}"
        subtitulo = (f"Mejor posición vista por el enjambre (g): f − f* = {_cient(func.f(frame['best']) - func.f_star)}"
                     f"<br>{subtitulo_fijo}")
        textos.append((titulo, subtitulo))
        visible = [True] + [i == k for i in range(len(elegidos))] + [True]
        steps.append(dict(method="update", label=str(frame["iter"]),
                          args=[{"visible": visible}, {"title.text": titulo, "title.subtitle.text": subtitulo}]))
    eje = dict(backgroundcolor=p.SUPERFICIE, gridcolor=p.CUADRICULA, color=p.TINTA_TENUE)
    fig.update_layout(
        title=dict(text=textos[0][0], subtitle=dict(text=textos[0][1]), x=0, xanchor="left"),
        sliders=[dict(active=0, steps=steps, currentvalue=dict(prefix="Iteración "), transition=dict(duration=0),
                      font=dict(size=FUENTE_DESLIZADOR), pad=dict(t=24))],
        scene=dict(xaxis=dict(title=dict(text="x₁"), **eje), yaxis=dict(title=dict(text="x₂"), **eje),
                   zaxis=dict(title=dict(text="f"), **eje), uirevision="enjambre"),
        height=ALTO["enjambre"], separators=SEPARADORES, hovermode="closest",
        legend=dict(y=-0.2, yanchor="top"), margin=dict(l=0, r=0, t=110, b=130),
    )
    return fig


# --------------------------------------------------------------------------------------------- generación


def bloque_blog(figura: Figura) -> str:
    """Bloque `::: figura` listo para pegar en blog/secciones/ (formato de blog/README.md y blog/hooks/reporte.py)."""
    return (f"::: figura {figura.id}\nTítulo: {figura.titulo}\nFuente: {figura.fuente}\n"
            f"incluir: figures/{figura.archivo}\n:::")


def bloques_blog(rutas: list[Path]) -> str:
    """Bloques de las figuras de `FIGURAS` cuyo archivo está en `rutas`, en el orden de `FIGURAS`."""
    nombres = {Path(r).name for r in rutas}
    return "\n\n".join(bloque_blog(f) for f in FIGURAS.values() if f.archivo in nombres)


def _avisar(motivo: str, claves: tuple[str, ...], comando: str) -> None:
    archivos = ", ".join(FIGURAS[c].archivo for c in claves)
    print(f"AVISO Parte 1: {motivo}. No se genera: {archivos}. Para generarlo: {comando}")


def _cargar(carpeta: Path, claves: tuple[str, ...], comando: str) -> dict | None:
    try:
        return pd1.cargar_experimento(carpeta)
    except pd1.DatosFaltantes as error:
        _avisar(str(error), claves, comando)
        return None


def _escribir(fig: go.Figure, salida: Path, clave: str) -> Path:
    figura = FIGURAS[clave]
    html = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_JS, div_id=f"fig-part1-{figura.id}",
                       config=CONFIG_PLOTLY, default_height=f"{ALTO[clave]}px")
    ruta = salida / figura.archivo
    ruta.write_text(html + "\n", encoding="utf-8")
    return ruta


def generar_part1(defecto: Path | None = None, afinado: Path | None = None, eta: Path | None = None,
                  salida: Path | None = None) -> list[Path]:
    """Genera en `salida` (por defecto SALIDA) las figuras de la Parte 1 que los datos permiten y devuelve sus rutas
    en el orden de `FIGURAS`. `defecto` y `afinado`: carpetas de experimento; `eta`: JSON del deslizador (por defecto
    `<defecto>/eta_deslizador.json`). Lo que falte se avisa por la salida estándar con el comando que lo genera; no
    lanza excepción por datos ausentes. Sí lanza ValueError si por defecto y afinado no son comparables."""
    defecto = Path(RES_DEFECTO if defecto is None else defecto)
    afinado = Path(RES_AFINADO if afinado is None else afinado)
    eta = defecto / ARCHIVO_ETA if eta is None else Path(eta)
    salida = Path(SALIDA if salida is None else salida)
    salida.mkdir(parents=True, exist_ok=True)

    figuras = {clave: figura_contorno(clave.removeprefix("contorno_"))
               for clave in ("contorno_rosenbrock", "contorno_rastrigin")}
    exp_d = _cargar(defecto, NECESITAN_DEFECTO + NECESITAN_AFINADO, COMANDO["defecto"])
    if exp_d is not None:
        corridas = exp_d["corridas"]
        figuras["convergencia"] = figura_convergencia(corridas)
        figuras["cajas"] = figura_cajas(corridas)
        con_frames = [c for c in corridas.get(ENJAMBRE, []) if c["result"].get("frames")]
        if con_frames:
            figuras["enjambre"] = figura_enjambre(con_frames[0])
        else:
            _avisar(f"ninguna corrida de {ENJAMBRE} trae frames", ("enjambre",), COMANDO["defecto"])
        exp_a = _cargar(afinado, NECESITAN_AFINADO, COMANDO["afinado"])
        if exp_a is not None:
            pd1.comprobar_comparables(corridas, exp_a["corridas"])
            metodos = pd1.metodos_afinados(corridas, exp_a["corridas"])
            if any(metodos.values()):
                figuras["convergencia_afinado"] = figura_convergencia(corridas, exp_a["corridas"], metodos)
                figuras["cajas_afinado"] = figura_cajas(corridas, exp_a["corridas"], metodos)
            else:
                _avisar("ningún método cambió de hiperparámetros entre por defecto y afinado", NECESITAN_AFINADO,
                        COMANDO["afinado"])
    if eta.is_file():
        figuras["eta"] = figura_eta(load_json(eta))
    else:
        _avisar(f"no existe {eta}", ("eta",), COMANDO["eta"])
    return [_escribir(figuras[clave], salida, clave) for clave in FIGURAS if clave in figuras]
