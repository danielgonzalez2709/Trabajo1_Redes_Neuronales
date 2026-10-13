"""TEMPORAL (T3.3): gráficas rápidas para inspeccionar ACO a ojo antes de aprobar la tarea.

No es parte del entregable: las figuras oficiales son de F4 (T4.x). Borrar cuando existan.

Uso:
    .venv/Scripts/python.exe scripts/ver_aco_temporal.py
    .venv/Scripts/python.exe scripts/ver_aco_temporal.py --semilla 3 --set costo.valor_hora=0 --set aco.iteraciones=1000
    .venv/Scripts/python.exe scripts/ver_aco_temporal.py --guardar figuras_aco   # PNG en esa carpeta, sin ventanas
    .venv/Scripts/python.exe scripts/ver_aco_temporal.py --barrido               # peajes frente a w (~8 s)

Muestra tres figuras:
    1. Convergencia: mejor costo global frente a recorridos evaluados (MMAS y AS), con el vecino más cercano como referencia.
    2. Recorrido final de cada variante sobre lon/lat; en rojo (con su importe) los tramos que pagan peaje.
    3. Evolución del mejor recorrido de MMAS en cuatro momentos de la corrida.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.common.config import apply_overrides, load_config  # noqa: E402
from src.common.seeds import make_rng  # noqa: E402
from src.part2.aco import solve  # noqa: E402
from src.part2.costos import cargar_componentes, matriz_costos  # noqa: E402

PROC = RAIZ / "data" / "processed"
COLOR_CON_PEAJE, COLOR_SIN_PEAJE = "tab:red", "dimgray"
COLOR_VARIANTE = {"mmas": "tab:green", "as": "tab:purple"}


def _leer_ciudades() -> tuple[np.ndarray, np.ndarray, list[str]]:
    with open(PROC / "cities.csv", encoding="utf-8") as f:
        filas = sorted(csv.DictReader(f), key=lambda r: int(r["id"]))
    lon = np.array([float(r["lon"]) for r in filas])
    lat = np.array([float(r["lat"]) for r in filas])
    return lon, lat, [r["capital"] for r in filas]


W_BARRIDO = (0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500, 1000, 2000, 5000)


def _matriz(cfg: dict, valor_hora: float | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve C (€), el peaje (€) de la alternativa elegida y el peaje de la rápida en cada par."""
    vehiculo = yaml.safe_load((PROC / "vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((PROC / "combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    comp = cargar_componentes()
    w = cfg["costo"]["valor_hora"] if valor_hora is None else valor_hora
    C, alt = matriz_costos(comp, w, vehiculo, precio)
    peaje = np.where(alt == "rapida", comp.peaje_eur_rapida, comp.peaje_eur_sin_peaje)
    return C, peaje, comp.peaje_eur_rapida


def _figura_barrido(cfg: dict, semilla: int, plt):
    """Tramos con peaje y peaje total del mejor recorrido MMAS para varios w."""
    iu = np.triu_indices(len(_leer_ciudades()[0]), 1)
    filas = []
    for w in W_BARRIDO:
        C, peaje, peaje_rapida = _matriz(cfg, w)
        res = solve(C, cfg, make_rng(cfg["base_seed"], semilla))
        t = np.asarray(res["tour"])
        u, v = t, np.roll(t, -1)
        con_peaje_rapida = peaje_rapida[iu] > 0
        filas.append({
            "w": w,
            "tramos_pagan": int((peaje[u, v] > 0).sum()),
            "tramos_rapida_con_peaje": int((peaje_rapida[u, v] > 0).sum()),
            "peaje_total": float(peaje[u, v].sum()),
            "pct_pares": 100 * float(((peaje[iu] > 0) & con_peaje_rapida).sum() / con_peaje_rapida.sum()),
        })
        print(f"w = {w:5} €/h: {filas[-1]['tramos_pagan']:2d} tramos con peaje "
              f"(rápida con peaje en {filas[-1]['tramos_rapida_con_peaje']:2d}), "
              f"peaje total {filas[-1]['peaje_total']:6.2f} €, costo {res['cost']:9.2f} €")

    x = [f["w"] for f in filas]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(16, 4.6))
    a1.plot(x, [f["tramos_pagan"] for f in filas], "o-", color="tab:red", label="tramos que pagan peaje")
    a1.plot(x, [f["tramos_rapida_con_peaje"] for f in filas], "s--", color="gray",
            label="tramos cuya ruta rápida tiene peaje")
    a1.set_ylabel("Tramos del recorrido (de 47)")
    a1.set_title("Mejor recorrido MMAS")
    a2.plot(x, [f["peaje_total"] for f in filas], "o-", color="tab:red")
    a2.set_ylabel("Peaje total del recorrido (€)")
    a2.set_title("Peaje pagado en el recorrido")
    a3.plot(x, [f["pct_pares"] for f in filas], "o-", color="tab:blue")
    a3.set_ylabel("% de pares")
    a3.set_ylim(0, 105)
    a3.set_title("Pares (de los 534 con rápida de peaje)\nque eligen pagar")
    for a in (a1, a2, a3):
        a.set_xscale("symlog", linthresh=10)
        a.set_xlim(0, max(x) * 1.3)
        a.set_xlabel("w, valor de la hora (€/h, escala log)")
        a.grid(alpha=0.3)
    a1.legend(fontsize=8)
    fig.suptitle(f"Efecto del valor de la hora (MMAS, semilla {semilla}, {cfg['aco']['iteraciones']} iteraciones)")
    fig.tight_layout()
    return fig


def _costo(C: np.ndarray, tour: list[int]) -> float:
    t = np.asarray(tour)
    return float(C[t, np.roll(t, -1)].sum())


def _vecino_mas_cercano(C: np.ndarray) -> float:
    """Solo para la línea de referencia; el solver calcula el suyo."""
    n = len(C)
    tour, libres = [0], set(range(1, n))
    while libres:
        actual = tour[-1]
        siguiente = min(libres, key=lambda j: C[actual, j])
        tour.append(siguiente)
        libres.remove(siguiente)
    return _costo(C, tour)


def _peaje_total(tour, peaje) -> float:
    t = np.asarray(tour)
    return float(peaje[t, np.roll(t, -1)].sum())


def _dibujar_tour(ax, tour, lon, lat, nombres, peaje, titulo, etiquetas=True):
    ciclo = list(tour) + [tour[0]]
    for i, j in zip(ciclo[:-1], ciclo[1:]):
        paga = peaje[i, j] > 0
        ax.plot([lon[i], lon[j]], [lat[i], lat[j]], color=COLOR_CON_PEAJE if paga else COLOR_SIN_PEAJE,
                lw=2.2 if paga else 1.2)
        if paga and etiquetas:
            ax.annotate(f"{peaje[i, j]:.2f} €", ((lon[i] + lon[j]) / 2, (lat[i] + lat[j]) / 2),
                        fontsize=6, color=COLOR_CON_PEAJE, ha="center")
    ax.scatter(lon, lat, s=14, color="black", zorder=3)
    ax.scatter(lon[tour[0]], lat[tour[0]], s=50, color="red", zorder=4)
    if etiquetas:
        for k, nombre in enumerate(nombres):
            ax.annotate(nombre, (lon[k], lat[k]), fontsize=6, xytext=(2, 2), textcoords="offset points")
    ax.set_title(titulo, fontsize=9)
    ax.set_aspect(1 / np.cos(np.radians(lat.mean())))
    ax.set_xlabel("lon")
    ax.set_ylabel("lat")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(RAIZ / "configs" / "part2" / "base.yaml"))
    p.add_argument("--set", dest="overrides", action="append", default=[], metavar="clave=valor")
    p.add_argument("--semilla", type=int, default=0, help="run_id para make_rng(base_seed, run_id)")
    p.add_argument("--guardar", metavar="CARPETA", help="guarda PNG en la carpeta en vez de abrir ventanas")
    p.add_argument("--barrido", action="store_true", help="solo la figura de peajes frente a w (MMAS)")
    args = p.parse_args()

    if args.guardar:
        import matplotlib

        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = apply_overrides(load_config(args.config), args.overrides)
    if args.barrido:
        fig = _figura_barrido(cfg, args.semilla, plt)
        if args.guardar:
            Path(args.guardar).mkdir(parents=True, exist_ok=True)
            fig.savefig(Path(args.guardar) / "barrido_w.png", dpi=130)
            print(f"Figura guardada en {Path(args.guardar).resolve()}")
        else:
            plt.show()
        return

    C, peaje, _ = _matriz(cfg)
    lon, lat, nombres = _leer_ciudades()
    c_nn = _vecino_mas_cercano(C)
    w = cfg["costo"]["valor_hora"]
    m = cfg["aco"]["hormigas"]

    resultados = {}
    for variante in ("mmas", "as"):
        cfg_v = copy.deepcopy(cfg)
        cfg_v["aco"]["variante"] = variante
        res = solve(C, cfg_v, make_rng(cfg["base_seed"], args.semilla))
        resultados[variante] = res
        print(f"{variante.upper():5s} costo = {res['cost']:.2f} €  |  recorridos evaluados = {res['n_tour_evals']}  "
              f"|  mejora sobre vecino más cercano = {100 * (1 - res['cost'] / c_nn):.2f} %")
    print(f"Vecino más cercano = {c_nn:.2f} €  (w = {w} €/h, semilla {args.semilla})")

    # 1. Convergencia
    fig1, ax = plt.subplots(figsize=(8, 4.5))
    for variante, res in resultados.items():
        x = [1 + m * (h["iter"] + 1) for h in res["history"]]
        y = [h["best_cost"] for h in res["history"]]
        ax.plot(x, y, color=COLOR_VARIANTE[variante], label=f"{variante.upper()} (final {res['cost']:.2f} €)")
    ax.axhline(c_nn, ls="--", color="gray", label=f"Vecino más cercano ({c_nn:.2f} €)")
    ax.set_xlabel("Recorridos evaluados")
    ax.set_ylabel("Mejor costo global (€)")
    ax.set_title(f"Convergencia ACO — w = {w} €/h, semilla {args.semilla}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig1.tight_layout()

    # 2. Recorridos finales
    fig2, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    for ax, (variante, res) in zip(axes, resultados.items()):
        _dibujar_tour(ax, res["tour"], lon, lat, nombres, peaje,
                      f"{variante.upper()}: {res['cost']:.2f} € (peajes {_peaje_total(res['tour'], peaje):.2f} €)")
    fig2.legend(
        handles=[plt.Line2D([], [], color=COLOR_CON_PEAJE, lw=2.2, label="paga peaje (€ del tramo)"),
                 plt.Line2D([], [], color=COLOR_SIN_PEAJE, lw=1.2, label="sin peaje")],
        loc="lower center", ncol=2,
    )
    fig2.suptitle(f"Mejor recorrido final — w = {w} €/h (punto rojo: ciudad inicial del tour)")
    fig2.tight_layout(rect=(0, 0.05, 1, 1))

    # 3. Evolución de MMAS
    hist = resultados["mmas"]["history"]
    indices = sorted({0, len(hist) // 10, len(hist) // 3, len(hist) - 1})
    fig3, axes = plt.subplots(1, len(indices), figsize=(4.5 * len(indices), 4.8))
    for ax, k in zip(np.atleast_1d(axes), indices):
        h = hist[k]
        _dibujar_tour(ax, h["best_tour"], lon, lat, nombres, peaje,
                      f"iter {h['iter']}: {h['best_cost']:.2f} €", etiquetas=False)
    fig3.suptitle("Evolución del mejor recorrido global (MMAS)")
    fig3.tight_layout()

    if args.guardar:
        carpeta = Path(args.guardar)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, fig in (("convergencia", fig1), ("recorridos", fig2), ("evolucion_mmas", fig3)):
            fig.savefig(carpeta / f"{nombre}.png", dpi=130)
        print(f"Figuras guardadas en {carpeta.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
