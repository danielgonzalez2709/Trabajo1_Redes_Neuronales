"""Figuras interactivas de la Parte 2 (T4.4; Spec §7.6, figuras 2, 3 y 4) con Plotly.

- Fig. 2 `figura_mapa`: recorrido de menor costo conocido para cada w, con deslizador; tramos con peaje en
  COLOR_PEAJE y más gruesos. Pasos del deslizador (`pasos_deslizador`): los 11 w del barrido MÁS el punto medio de
  cada intervalo de la envolvente (§7.5, `umbrales_w.json`) que no contiene ningún w del barrido. Así hay un paso a
  cada lado de cada umbral y se ve cada cambio de ruta (el recorrido 139, ganador solo en 10,75–13,81 €/h, no aparece
  en la rejilla del barrido). En cada paso el recorrido es el `candidato` de la envolvente en ese w.
- Fig. 3 `figura_desglose`: barras apiladas tiempo / peajes / combustible de `sweep_w.json` por w, con los umbrales.
- Fig. 4 `figura_convergencia`: gap (%) del mejor recorrido hasta el momento frente al mejor conocido en ese w (el
  `cost` de `sweep_w.json`, §7.5 y §7.7: no es un óptimo probado) contra recorridos evaluados; media y banda mín–máx de
  las corridas de MMAS, AS y GA; selector de w (inicial: 25 €/h, el de la demo).

Los arcos del mapa son segmentos rectos entre capitales (no hay geometría de carretera versionada): se declara en la
figura (`part2_figs.NOTA`). El costo, el desglose y los arcos con peaje salen de `experiment.arcos` (misma lógica que
el barrido y la demo); `pasos_mapa` comprueba que coinciden con `sweep_w.json` y con la envolvente y, si no, falla.

Los HTML son fragmentos (sin <html>) para el `incluir: figures/<archivo>.html` del blog (blog/hooks/reporte.py los
inserta en la página) y cargan plotly.js desde su CDN: incrustarlo (~4,6 MB) en cada fragmento triplicaría la página.
Uso: `python run.py figures` (escribe en blog/docs/figures/; sin internet).
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from src.common.results import load_json
from src.part2 import experiment as ex
from src.part2.costos import CLAVE_CONSUMO, matriz_costos
from src.part2.recorridos import costos_recorridos
from src.viz import paleta as p
from src.viz.part2_figs import ANCHO_PEAJE, ANCHO_SIN_PEAJE, NOTA
from src.viz.theme import aplicar_tema

RAIZ = Path(__file__).resolve().parents[2]
RESULTADOS = RAIZ / "results" / "data" / "part2"
DATOS = RAIZ / "data" / "processed"
SALIDA = RAIZ / "blog" / "docs" / "figures"
ARCHIVOS = {
    "mapa": "part2_mapa_w.html",
    "desglose": "part2_desglose_w.html",
    "convergencia": "part2_convergencia.html",
}
FAMILIAS = ("aco", "ga")  # history_{familia}_w{w}.json
SOLVERS = ex.SOLVERS  # mmas, as, ga (orden fijo de las salidas)
COMPONENTES = ("tiempo", "peajes", "combustible")  # Spec §5.4: desglose
W_CONVERGENCIA = 25.0  # w inicial del selector de la fig. 4: el de la demo (§7.7)
PUNTOS_CURVA = 200  # puntos por curva de convergencia (muestreo geométrico, eje x logarítmico)
TOL_REL = 1e-9  # mismas sumas en otro orden (como experiment.TOL_REL)
ANCHO_BARRA = 3.0  # €/h: el paso mínimo del barrido es 5 €/h
ALFA_BANDA = 0.15
PLOTLY_JS = "cdn"
ALTO = {"mapa": 760, "desglose": 520, "convergencia": 560}
CONFIG_PLOTLY = {"responsive": True, "displaylogo": False}
SEPARADORES = ", "  # coma decimal y espacio de miles (convención del reporte en español)
DASH_SOLVER = {"mmas": "solid", "as": "dash", "ga": "dot"}  # el trazo distingue también a las variantes


# ------------------------------------------------------------------------------------------------ formato


def _num(x: float, decimales: int = 2) -> str:
    """1234.5 → "1 234,50" (coma decimal, espacio de miles)."""
    return f"{x:,.{decimales}f}".replace(",", " ").replace(".", ",")


def _w(x: float) -> str:
    """Valor de w para etiquetas: entero sin decimales, si no con 2."""
    return _num(x, 0) if float(x).is_integer() else _num(x, 2)


def _rgba(hex_color: str, alfa: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa})"


def _cerca(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=TOL_REL, abs_tol=TOL_REL)


# ------------------------------------------------------------------------------------------ pasos del mapa


def _candidatos_en(intervalos: list[dict], w: float) -> set[int]:
    """Candidatos de la envolvente cuyo intervalo contiene w (dos si w cae justo en un umbral)."""
    return {i["candidato"] for i in intervalos if i["w_desde"] <= w <= i["w_hasta"]}


def pasos_deslizador(sweep: list[dict], intervalos: list[dict]) -> list[dict]:
    """Pasos del deslizador, ordenados por w: [{w, candidato, en_barrido}].

    Los w del barrido (candidato = el de `sweep_w.json`, que debe coincidir con la envolvente) y, por cada intervalo de
    la envolvente cuyo candidato no muestra ningún w del barrido, su punto medio (candidato = el del intervalo)."""
    pasos = []
    for fila in sweep:
        w = float(fila["w"])
        if fila["candidato"] not in _candidatos_en(intervalos, w):
            raise ValueError(f"w = {w}: el candidato {fila['candidato']} de sweep_w.json no es el de la envolvente "
                             f"({sorted(_candidatos_en(intervalos, w))})")
        pasos.append({"w": w, "candidato": fila["candidato"], "en_barrido": True})
    barrido = list(pasos)
    for i in intervalos:  # un intervalo "tiene muestra" si un w del barrido (bordes incluidos) muestra su candidato
        if not any(i["w_desde"] <= x["w"] <= i["w_hasta"] and x["candidato"] == i["candidato"] for x in barrido):
            pasos.append({"w": (i["w_desde"] + i["w_hasta"]) / 2, "candidato": i["candidato"], "en_barrido": False})
    return sorted(pasos, key=lambda x: x["w"])


def detalle_paso(datos: ex.Datos, tour, w: float) -> dict:
    """{costo, desglose{tiempo, peajes, combustible}, km_peaje, con_peaje} del recorrido en w con `experiment.arcos`
    (consumo y precio de `datos`). `con_peaje[k]`: el arco tour[k] → tour[k+1] (el último cierra) paga peaje."""
    por_arco = ex.arcos(datos, tour, w, datos.consumo_l100, datos.precio_l)
    desglose = {k: float(por_arco[k].sum()) for k in COMPONENTES}
    return {
        "costo": sum(desglose.values()),
        "desglose": desglose,
        "km_peaje": float(por_arco["km_peaje"].sum()),
        "con_peaje": por_arco["peajes"] > 0,
    }


def _comprobar_paso(paso: dict, fila: dict | None, costo_min: float) -> None:
    """El paso coincide con sweep_w.json (si es un w del barrido) y su recorrido es el de menor costo conocido."""
    w = paso["w"]
    if not _cerca(paso["costo"], costo_min):
        raise ValueError(f"w = {w}: el recorrido de la envolvente cuesta {paso['costo']!r} € pero el mejor candidato "
                         f"cuesta {costo_min!r} €")
    if fila is None:
        return
    if list(fila["tour"]) != list(paso["tour"]):
        raise ValueError(f"w = {w}: el recorrido de sweep_w.json no es el candidato {paso['candidato']}")
    esperado = {"costo": fila["cost"], "km_peaje": fila["km_peaje"], **fila["desglose"]}
    obtenido = {"costo": paso["costo"], "km_peaje": paso["km_peaje"], **paso["desglose"]}
    for clave, valor in esperado.items():
        if not _cerca(obtenido[clave], valor):
            raise ValueError(f"w = {w}: {clave} recalculado {obtenido[clave]!r} ≠ sweep_w.json {valor!r}")


def pasos_mapa(entradas: dict) -> list[dict]:
    """Pasos completos del deslizador: {w, candidato, en_barrido, tour, costo, desglose, km_peaje, con_peaje}.

    Comprueba que, en cada paso, el recorrido mostrado es el de menor costo entre TODOS los candidatos de
    `umbrales_w.json` y que en los w del barrido coincide con `sweep_w.json` (recorrido, costo, desglose, km)."""
    datos, sweep, umbrales = entradas["datos"], entradas["sweep"], entradas["umbrales"]
    tours = np.array([c["tour"] for c in umbrales["candidatos"]], dtype=np.intp)
    por_w = {float(f["w"]): f for f in sweep}
    pasos = []
    for x in pasos_deslizador(sweep, umbrales["intervalos"]):
        tour = umbrales["candidatos"][x["candidato"]]["tour"]
        paso = {**x, "tour": list(tour), **detalle_paso(datos, tour, x["w"])}
        C, _ = matriz_costos(datos.comp, x["w"], {CLAVE_CONSUMO: datos.consumo_l100}, datos.precio_l)
        _comprobar_paso(paso, por_w.get(x["w"]) if x["en_barrido"] else None,
                        float(costos_recorridos(C, tours).min()))
        pasos.append(paso)
    return pasos


# --------------------------------------------------------------------------------------------- figura 2


def _lineas(lon, lat, tour, mascara) -> tuple[list, list]:
    """Coordenadas de los arcos seleccionados por `mascara`, separados por None (una sola traza)."""
    t = np.asarray(tour, dtype=int)
    u, v = t[mascara], np.roll(t, -1)[mascara]
    xs, ys = [], []
    for a, b in zip(u, v):
        xs += [float(lon[a]), float(lon[b]), None]
        ys += [float(lat[a]), float(lat[b]), None]
    return xs, ys


def _umbrales_entre(umbrales: list[dict], w0: float, w1: float) -> list[dict]:
    return [u for u in umbrales if w0 < u["w"] < w1]


def _textos_paso(paso: dict, anterior: dict | None, umbrales: list[dict]) -> tuple[str, str]:
    d = paso["desglose"]
    n_peaje = int(np.sum(paso["con_peaje"]))
    titulo = f"Recorrido de menor costo conocido · w = {_num(paso['w'])} €/h"
    tramos = "tramo" if n_peaje == 1 else "tramos"
    lineas = [
        f"Costo total {_num(paso['costo'])} € = tiempo {_num(d['tiempo'])} € + peajes {_num(d['peajes'])} € + "
        f"combustible {_num(d['combustible'])} €",
        f"{n_peaje} {tramos} con peaje ({_num(paso['km_peaje'], 1)} km) · recorrido candidato #{paso['candidato']} "
        + ("(w del barrido)" if paso["en_barrido"]
           else "(punto medio de su intervalo de la envolvente, fuera del barrido)"),
    ]
    if anterior is not None:
        for u in _umbrales_entre(umbrales, anterior["w"], paso["w"]):
            lineas.append(f"Desde el paso anterior: umbral en w = {_num(u['w'])} €/h, el recorrido cambia del "
                          f"candidato #{u['de']} al #{u['a']}")
    lineas.append(NOTA)
    return titulo, "<br>".join(lineas)


def figura_mapa(lon, lat, nombres, pasos: list[dict], umbrales: list[dict]) -> go.Figure:
    """Mapa con deslizador: por paso, dos trazas (tramos sin peaje / con peaje) que se muestran solo en ese paso; las
    capitales (con su nombre al pasar el cursor) siempre visibles. `meta` identifica cada traza."""
    aplicar_tema()
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    fig = go.Figure()
    for k, paso in enumerate(pasos):
        con = np.asarray(paso["con_peaje"], dtype=bool)
        for clave, mascara, color, ancho, nombre in (
            ("sin_peaje", ~con, p.COLOR_RECORRIDO, ANCHO_SIN_PEAJE, "Tramo sin peaje"),
            ("con_peaje", con, p.COLOR_PEAJE, ANCHO_PEAJE, "Tramo con peaje"),
        ):
            xs, ys = _lineas(lon, lat, paso["tour"], mascara)
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", line=dict(color=color, width=ancho), meta=clave,
                name=f"{nombre} ({int(mascara.sum())})", hoverinfo="skip", visible=k == 0,
            ))
    fig.add_trace(go.Scatter(
        x=lon, y=lat, mode="markers", text=list(nombres), meta="ciudades", name=f"Capital ({lon.size})",
        marker=dict(color=p.COLOR_CIUDAD, size=p.TAMANO_MARCADOR), hovertemplate="%{text}<extra></extra>",
    ))

    n_lineas = 2 * len(pasos)
    steps, textos = [], []
    for k, paso in enumerate(pasos):
        titulo, subtitulo = _textos_paso(paso, pasos[k - 1] if k else None, umbrales)
        textos.append((titulo, subtitulo))
        visible = [k == i // 2 for i in range(n_lineas)] + [True]
        steps.append(dict(method="update", label=_w(paso["w"]),
                          args=[{"visible": visible}, {"title.text": titulo, "title.subtitle.text": subtitulo}]))
    fig.update_layout(
        title=dict(text=textos[0][0], subtitle=dict(text=textos[0][1]), x=0, xanchor="left"),
        sliders=[dict(active=0, steps=steps, currentvalue=dict(prefix="w = ", suffix=" €/h"),
                      transition=dict(duration=0), pad=dict(t=56))],
        xaxis=dict(title=dict(text="Longitud (°)")),
        # Grados de longitud más cortos al norte: misma corrección que part2_figs.figura_recorrido.
        yaxis=dict(title=dict(text="Latitud (°)"), scaleanchor="x",
                   scaleratio=1 / math.cos(math.radians(float(np.mean(lat))))),
        hovermode="closest", height=ALTO["mapa"], separators=SEPARADORES,
        legend=dict(y=-0.42, yanchor="top"), margin=dict(t=160, b=190),
    )
    return fig


# --------------------------------------------------------------------------------------------- figura 3


def figura_desglose(sweep: list[dict], umbrales: list[dict]) -> go.Figure:
    """Barras apiladas del desglose del mejor recorrido conocido por w; línea punteada en cada umbral."""
    aplicar_tema()
    for f in sweep:
        if not _cerca(sum(f["desglose"][k] for k in COMPONENTES), f["cost"]):
            raise ValueError(f"w = {f['w']}: el desglose no suma el costo ({f['cost']!r} €)")
    w = [float(f["w"]) for f in sweep]
    total = [f["cost"] for f in sweep]
    fig = go.Figure()
    for k in COMPONENTES:
        fig.add_trace(go.Bar(
            x=w, y=[f["desglose"][k] for f in sweep], name=p.NOMBRE_COMPONENTE[k], meta=k, width=ANCHO_BARRA,
            marker=dict(color=p.COLOR_COMPONENTE[k], line=dict(width=0)), customdata=total,
            hovertemplate=f"{p.NOMBRE_COMPONENTE[k]}: %{{y:,.2f}} € (total %{{customdata:,.2f}} €)<extra></extra>",
        ))
    for u in umbrales:
        fig.add_shape(type="line", x0=u["w"], x1=u["w"], yref="paper", y0=0, y1=1,
                      line=dict(color=p.TINTA_SECUNDARIA, width=1, dash="dot"))
    lista = "; ".join(_num(u["w"]) for u in umbrales)
    fig.update_layout(
        barmode="stack", height=ALTO["desglose"], separators=SEPARADORES,
        title=dict(text="Costo del recorrido de menor costo conocido, desglosado, según w", x=0, xanchor="left",
                   subtitle=dict(text=f"Líneas punteadas: umbrales de cambio de ruta en w = {lista} €/h")),
        xaxis=dict(title=dict(text="Valor del tiempo w (€/h)")),
        yaxis=dict(title=dict(text="Costo (€)")),
        legend=dict(y=-0.22, yanchor="top"), margin=dict(t=96, b=120),
    )
    return fig


# --------------------------------------------------------------------------------------------- figura 4


def curvas_convergencia(variante: dict, mejor: float) -> tuple[np.ndarray, np.ndarray]:
    """(x, gaps): x[k] = recorridos evaluados al terminar la iteración k (desde 0) = iniciales + por_iter·(k + 1)
    (ACO: 1 + hormigas·(k + 1), §7.4.1; GA: poblacion + (poblacion − elites)·(k + 1), §7.4.2) y gaps[r, k] = 100·(best_cost − mejor)/mejor de la
    corrida r. Exige que todas las corridas compartan el conteo y que el último x sea su `n_tour_evals`."""
    corridas = variante["corridas"]
    c0 = corridas[0]
    n = len(c0["best_cost"])
    x = c0["recorridos_iniciales"] + c0["recorridos_por_iter"] * np.arange(1, n + 1)
    for c in corridas:
        if (c["recorridos_iniciales"], c["recorridos_por_iter"], len(c["best_cost"])) != (
                c0["recorridos_iniciales"], c0["recorridos_por_iter"], n) or c["n_tour_evals"] != x[-1]:
            raise ValueError(f"n_tour_evals = {c['n_tour_evals']} no coincide con el conteo del historial ({x[-1]})")
    costos = np.array([c["best_cost"] for c in corridas], dtype=float)
    return x, ex.gap(costos, mejor)


def _muestreo(n: int) -> np.ndarray:
    """Índices 0..n−1 espaciados geométricamente (eje x logarítmico); incluye el primero y el último."""
    return np.unique(np.rint(np.geomspace(1, n, min(n, PUNTOS_CURVA))).astype(int)) - 1


def _titulo_convergencia(w: float, n_corridas: int) -> str:
    return f"Convergencia en w = {_w(w)} €/h (media y banda mín–máx de {n_corridas} corridas)"


def figura_convergencia(historias: dict[float, dict[str, dict]], mejores: dict[float, float],
                        w_inicial: float = W_CONVERGENCIA) -> go.Figure:
    """`historias[w][solver]` = variante de history_{aco|ga}_w{w}.json; `mejores[w]` = mejor costo conocido en w
    (sweep_w.json). Por (w, solver): banda mín–máx (trazas min y max) y la media; un menú elige el w."""
    aplicar_tema()
    ws = sorted(historias)
    fig = go.Figure()
    grupos, n_corridas = [], {}
    for w in ws:
        for s in (s for s in SOLVERS if s in historias[w]):
            x, gaps = curvas_convergencia(historias[w][s], mejores[w])
            n_corridas[w] = gaps.shape[0]
            idx = _muestreo(x.size)
            x = x[idx].tolist()
            visible = w == w_inicial
            color, clave = p.COLOR_SOLVER[s], f"{s}:{ex._texto_num(w)}"
            fig.add_trace(go.Scatter(x=x, y=gaps.min(axis=0)[idx].tolist(), mode="lines", line=dict(width=0),
                                     meta=f"min:{clave}", showlegend=False, hoverinfo="skip", visible=visible))
            fig.add_trace(go.Scatter(x=x, y=gaps.max(axis=0)[idx].tolist(), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor=_rgba(color, ALFA_BANDA), meta=f"max:{clave}",
                                     showlegend=False, hoverinfo="skip", visible=visible))
            fig.add_trace(go.Scatter(
                x=x, y=gaps.mean(axis=0)[idx].tolist(), mode="lines", meta=f"media:{clave}", visible=visible,
                name=p.NOMBRE_SOLVER[s], line=dict(color=color, dash=DASH_SOLVER[s]),
                hovertemplate=f"{p.NOMBRE_SOLVER[s]}: %{{y:.2f}} % (media)<extra></extra>",
            ))
            grupos += [w] * 3
    botones = [dict(method="update", label=f"w = {_w(w)} €/h",
                    args=[{"visible": [g == w for g in grupos]},
                          {"title.text": _titulo_convergencia(w, n_corridas[w])}])
               for w in ws]
    fig.update_layout(
        title=dict(text=_titulo_convergencia(w_inicial, n_corridas[w_inicial]), x=0, xanchor="left",
                   subtitle=dict(text="Gap = 100 · (mejor costo hasta el momento − mejor conocido) / mejor conocido"
                                      "<br>Mejor conocido = mejor costo encontrado en ese w por todo el barrido "
                                      "(sweep_w.json), no un óptimo probado")),
        updatemenus=[dict(buttons=botones, active=ws.index(w_inicial), direction="down", x=1, xanchor="right",
                          y=1.03, yanchor="bottom")],
        xaxis=dict(type="log", title=dict(text="Recorridos evaluados (escala logarítmica)")),
        yaxis=dict(title=dict(text="Gap frente al mejor conocido (%)"), rangemode="tozero"),
        height=ALTO["convergencia"], separators=SEPARADORES,
        legend=dict(y=-0.2, yanchor="top"), margin=dict(t=130, b=120),
    )
    return fig


# ------------------------------------------------------------------------------------------- generación


def _nombres(ruta: Path, n: int) -> list[str]:
    with Path(ruta).open(encoding="utf-8", newline="") as f:
        filas = sorted(csv.DictReader(f), key=lambda fila: int(fila["id"]))
    if [int(fila["id"]) for fila in filas] != list(range(n)):
        raise ValueError(f"{ruta}: los id deben ser 0..{n - 1}")
    return [fila["capital"] for fila in filas]


def cargar_entradas(resultados: Path = RESULTADOS, datos: Path = DATOS) -> dict:
    """Lee sweep_w.json, umbrales_w.json, los historiales de cada w, los datos de costo y cities.csv."""
    resultados, datos = Path(resultados), Path(datos)
    sweep = load_json(resultados / ex.ARCHIVO_SWEEP)
    umbrales = load_json(resultados / ex.ARCHIVO_UMBRALES)
    d = ex.cargar_datos(datos)
    if not (_cerca(umbrales["consumo_l100"], d.consumo_l100) and _cerca(umbrales["precio_l"], d.precio_l)):
        raise ValueError(f"umbrales_w.json usa consumo {umbrales['consumo_l100']} y precio {umbrales['precio_l']}, "
                         f"distintos de data/processed ({d.consumo_l100}, {d.precio_l})")
    n = d.comp.tiempo_h_rapida.shape[0]
    lon, lat = ex.cargar_coordenadas(datos / ex.ARCHIVO_CIUDADES, n)
    historias = {}
    for fila in sweep:
        w = float(fila["w"])
        historias[w] = {}
        for familia in FAMILIAS:
            hist = load_json(resultados / f"history_{familia}_w{ex._texto_num(w)}.json")
            historias[w].update(hist["variantes"])
    return {"sweep": sweep, "umbrales": umbrales, "datos": d, "lon": lon, "lat": lat,
            "nombres": _nombres(datos / ex.ARCHIVO_CIUDADES, n), "historias": historias}


def _escribir(fig: go.Figure, ruta: Path, clave: str) -> Path:
    html = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_JS, div_id=f"fig-part2-{clave}",
                       config=CONFIG_PLOTLY, default_height=f"{ALTO[clave]}px")
    ruta.write_text(html + "\n", encoding="utf-8")
    return ruta


def generar_part2(resultados: Path = RESULTADOS, datos: Path = DATOS, salida: Path | None = None) -> list[Path]:
    """Genera las figuras 2, 3 y 4 de la Parte 2 en `salida` (por defecto SALIDA) y devuelve sus rutas."""
    salida = Path(SALIDA if salida is None else salida)
    salida.mkdir(parents=True, exist_ok=True)
    e = cargar_entradas(resultados, datos)
    umbrales = e["umbrales"]["umbrales"]
    figuras = {
        "mapa": figura_mapa(e["lon"], e["lat"], e["nombres"], pasos_mapa(e), umbrales),
        "desglose": figura_desglose(e["sweep"], umbrales),
        "convergencia": figura_convergencia(e["historias"], {float(f["w"]): f["cost"] for f in e["sweep"]}),
    }
    return [_escribir(fig, salida / ARCHIVOS[k], k) for k, fig in figuras.items()]
