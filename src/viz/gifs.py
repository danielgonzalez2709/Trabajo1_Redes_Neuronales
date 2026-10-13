"""GIF de la Parte 2 (T4.5, Spec §7.6.5 y enunciado §1.2.4): evolución de la mejor solución sobre el mapa de España.

Un GIF por algoritmo (MMAS y GA) en w = 25 €/h (el de la demo, §7.7), con la mejor de sus 10 corridas del barrido de
T3.6: un fotograma por cada mejora del mejor recorrido (`mejoras` del historial). El contorno de las provincias
peninsulares sale del crudo del IGN de T2.1; los arcos son segmentos rectos entre capitales (no el trazado real).

Sin pyplot ni cambios globales de matplotlib (Figure + FigureCanvasAgg dentro de `rc_context`); los fotogramas se
unen con Pillow. Mismos datos → mismos bytes.
"""

from __future__ import annotations

import gzip
import json
import math
from collections.abc import Callable
from pathlib import Path

import matplotlib as mpl
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image

from src.common.results import load_json
from src.part2 import experiment as ex
from src.viz import paleta as p
from src.viz.part2_figs import ANCHO_PEAJE, ANCHO_SIN_PEAJE, NOTA, TAMANO_CIUDAD
from src.viz.style import parametros

RAIZ = Path(__file__).resolve().parents[2]
RESULTADOS = RAIZ / "results" / "data" / "part2"
DATOS = RAIZ / "data" / "processed"
PROVINCIAS = RAIZ / "data" / "raw" / "ign_provincias_2026-10-07.geojson.gz"  # crudo de T2.1 (IGN)
SALIDA = RAIZ / "media"

W_GIF = 25.0  # €/h, el de la demo (§7.7)
GIFS = {"mmas": "aco", "ga": "ga"}  # variante → familia del historial (history_{familia}_w{w}.json)
CPRO_EXCLUIDAS = {7, 35, 38, 51, 52}  # Illes Balears, Las Palmas, S. C. de Tenerife, Ceuta, Melilla (= T2.1)
PASO_CONTORNO = 40  # se conserva 1 de cada 40 vértices del contorno (solo es fondo)
TAMANO = (7.0, 6.4)  # pulgadas
DPI = 100
MS_FOTOGRAMA = 450
MS_FINAL = 3000  # el último fotograma se sostiene
COLORES = (p.COLOR_RECORRIDO, p.COLOR_PEAJE, p.COLOR_CIUDAD)
TOL_REL = 1e-9


def mejor_corrida(variante: dict) -> dict:
    """La corrida de menor costo final (empate: menor run_id)."""
    return min(variante["corridas"], key=lambda c: (c["cost"], c["run_id"]))


def fotogramas(corrida: dict) -> list[dict]:
    """Un fotograma por mejora: {iter, evaluados, costo, tour}. `evaluados` = recorridos evaluados al terminar la
    iteración (iniciales + por_iter·(iter+1)), el mismo eje que la convergencia de T4.4."""
    ini, por_iter = corrida["recorridos_iniciales"], corrida["recorridos_por_iter"]
    salida = []
    for m in corrida["mejoras"]:
        if salida and m["best_cost"] > salida[-1]["costo"]:
            raise ValueError(f"el mejor costo crece en la iteración {m['iter']} (debe ser no creciente)")
        salida.append({"iter": m["iter"], "evaluados": ini + por_iter * (m["iter"] + 1),
                       "costo": m["best_cost"], "tour": list(m["best_tour"])})
    if not salida or not math.isclose(salida[-1]["costo"], corrida["cost"], rel_tol=TOL_REL):
        raise ValueError(f"el costo final de las mejoras no coincide con el de la corrida ({corrida['cost']})")
    return salida


def contorno_peninsular(ruta: Path = PROVINCIAS, paso: int = PASO_CONTORNO) -> list[tuple[np.ndarray, np.ndarray]]:
    """Anillos exteriores (lon, lat) de las provincias peninsulares, con 1 de cada `paso` vértices y cerrados."""
    with gzip.open(ruta, "rt", encoding="utf-8") as fh:
        features = json.load(fh)["features"]
    anillos = []
    for feat in features:
        codigo = feat["properties"]["nationalcode"]  # 34 + CCAA(2) + CPRO(2) + 00000 (como construir_cities.py)
        cpro = int(codigo[4:6])
        if cpro == 0 or not codigo.endswith("00000") or cpro in CPRO_EXCLUIDAS:
            continue
        geom = feat["geometry"]
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poligono in poligonos:
            anillo = np.asarray(poligono[0], dtype=float)[::paso]
            if len(anillo) < 3:
                continue  # islote: no aporta al fondo
            anillo = np.vstack([anillo, anillo[:1]])
            anillos.append((anillo[:, 0], anillo[:, 1]))
    return anillos


def _num(x: float, decimales: int = 2) -> str:
    """Coma decimal y espacio de miles (convención del reporte en español, como en T4.4)."""
    return f"{x:,.{decimales}f}".replace(",", " ").replace(".", ",")


def _segmentos(lon, lat, u, v) -> tuple[np.ndarray, np.ndarray]:
    nan = np.full(len(u), np.nan)
    return (np.column_stack([lon[u], lon[v], nan]).ravel(), np.column_stack([lat[u], lat[v], nan]).ravel())


def _fotograma(lon, lat, f: dict, con_peaje: np.ndarray, anillos, mejor: float, titulo: str, limites) -> Image.Image:
    t = np.asarray(f["tour"], dtype=int)
    u, v = t, np.roll(t, -1)
    with mpl.rc_context(parametros()):
        fig = Figure(figsize=TAMANO, dpi=DPI)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes((0.09, 0.14, 0.89, 0.72))
        for x, y in anillos:
            ax.fill(x, y, color=p.CUADRICULA, alpha=0.35, linewidth=0, zorder=0)
            ax.plot(x, y, color=p.EJE, linewidth=0.5, zorder=1)
        for peaje, color, ancho, etiqueta in ((False, COLORES[0], ANCHO_SIN_PEAJE, "Tramo sin peaje"),
                                              (True, COLORES[1], ANCHO_PEAJE, "Tramo con peaje")):
            sel = con_peaje == peaje
            xs, ys = _segmentos(lon, lat, u[sel], v[sel])
            ax.plot(xs, ys, color=color, linewidth=ancho, label=f"{etiqueta} ({int(sel.sum())})", zorder=2)
        ax.scatter(lon, lat, s=TAMANO_CIUDAD, color=COLORES[2], zorder=3, label=f"Capital ({lon.size})")
        ax.set_xlim(limites[0])
        ax.set_ylim(limites[1])
        ax.set_aspect(1 / math.cos(math.radians(float(np.mean(lat)))), adjustable="box")
        ax.set_xlabel("Longitud (°)")
        ax.set_ylabel("Latitud (°)")
        ax.legend(loc="lower right")
        gap = 100 * (f["costo"] - mejor) / mejor
        gap = 0.0 if abs(gap) < 5e-3 else gap  # evita "-0,00 %" por redondeo
        fig.text(0.02, 0.965, titulo, fontsize="large", fontweight="bold", va="top")
        fig.text(0.02, 0.915, f"Iter. {f['iter']} · {_num(f['evaluados'], 0)} recorridos · {_num(f['costo'])} € · "
                              f"gap {_num(gap)} % frente al mejor conocido",
                 color=p.TINTA_SECUNDARIA, va="top")
        fig.text(0.02, 0.012, NOTA, color=p.TINTA_TENUE, fontsize="small")
        canvas.draw()
        imagen = Image.fromarray(np.asarray(canvas.buffer_rgba())).convert("RGB")
    return imagen


def gif_evolucion(lon, lat, fots: list[dict], peaje_de: Callable[[list[int]], np.ndarray], anillos, mejor_conocido: float,
                  titulo: str, ruta: str | Path) -> Path:
    """Escribe en `ruta` un GIF con un fotograma por elemento de `fots`; `peaje_de(tour)` → arco paga peaje."""
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    xs = np.concatenate([lon, *[x for x, _ in anillos]]) if anillos else lon
    ys = np.concatenate([lat, *[y for _, y in anillos]]) if anillos else lat
    margen = 0.3
    limites = ((xs.min() - margen, xs.max() + margen), (ys.min() - margen, ys.max() + margen))
    imagenes = [_fotograma(lon, lat, f, np.asarray(peaje_de(f["tour"]), dtype=bool), anillos, mejor_conocido, titulo,
                           limites).quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
                for f in fots]
    duraciones = [MS_FOTOGRAMA] * (len(imagenes) - 1) + [MS_FINAL]
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagenes[0].save(ruta, save_all=True, append_images=imagenes[1:], duration=duraciones, loop=0, optimize=False)
    return ruta


def generar_gifs(resultados: Path = RESULTADOS, datos: Path = DATOS, salida: Path | None = None,
                 w: float = W_GIF) -> list[Path]:
    """Genera media/tsp_{mmas|ga}_w{w}.gif desde los historiales del barrido (T3.6) y devuelve sus rutas."""
    resultados, datos = Path(resultados), Path(datos)
    salida = Path(SALIDA if salida is None else salida)
    d = ex.cargar_datos(datos)
    n = d.comp.tiempo_h_rapida.shape[0]
    lon, lat = ex.cargar_coordenadas(datos / ex.ARCHIVO_CIUDADES, n)
    fila = next(f for f in load_json(resultados / ex.ARCHIVO_SWEEP) if math.isclose(float(f["w"]), w))
    anillos = contorno_peninsular()
    texto_w = ex._texto_num(w)

    def peaje_de(tour):
        return ex.arcos(d, tour, w, d.consumo_l100, d.precio_l)["peajes"] > 0

    rutas = []
    for variante, familia in GIFS.items():
        hist = load_json(resultados / f"history_{familia}_w{texto_w}.json")
        corrida = mejor_corrida(hist["variantes"][variante])
        titulo = f"{p.NOMBRE_SOLVER[variante]} · w = {texto_w} €/h · corrida {corrida['run_id']}"
        rutas.append(gif_evolucion(lon, lat, fotogramas(corrida), peaje_de, anillos, fila["cost"], titulo,
                                   salida / f"tsp_{variante}_w{texto_w}.gif"))
    return rutas
