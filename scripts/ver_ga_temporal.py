"""TEMPORAL (T3.4): gráficas rápidas para inspeccionar a ojo la evolución del GA.

No es parte del entregable: las figuras oficiales son de F4 (T4.x). Borrar cuando existan.

Uso:
    .venv/Scripts/python.exe scripts/ver_ga_temporal.py
    .venv/Scripts/python.exe scripts/ver_ga_temporal.py --semilla 3 --set costo.valor_hora=0 --set ga.generaciones=200
    .venv/Scripts/python.exe scripts/ver_ga_temporal.py --guardar figuras_ga   # PNG en esa carpeta, sin ventanas

Muestra cuatro figuras:
    1. Convergencia (eje x log): mejor, media y peor de la población frente a recorridos evaluados; referencias:
       MMAS (configuración por defecto) y vecino más cercano.
    2. Diversidad por generación: recorridos distintos (forma canónica) y fracción media de aristas compartidas con el mejor.
    3. Recorrido final del GA sobre lon/lat; en rojo (con su importe) los tramos que pagan peaje.
    4. Evolución del mejor recorrido del GA en cuatro momentos de la corrida.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.common.config import apply_overrides, load_config  # noqa: E402
from src.common.seeds import make_rng  # noqa: E402
from src.part2 import aco  # noqa: E402
from src.part2.ga import iterar  # noqa: E402

from ver_aco_temporal import (  # noqa: E402
    COLOR_CON_PEAJE,
    COLOR_SIN_PEAJE,
    _dibujar_tour,
    _leer_ciudades,
    _matriz,
    _peaje_total,
    _vecino_mas_cercano,
)

COLOR_GA = "tab:blue"


def _canonico(tour: np.ndarray) -> tuple:
    """Rota para empezar en la ciudad 0 y elige el sentido con el segundo elemento menor (TSP simétrico)."""
    t = np.roll(tour, -int(np.where(tour == 0)[0][0]))
    if len(t) > 2 and t[-1] < t[1]:
        t = np.concatenate(([t[0]], t[:0:-1]))
    return tuple(int(x) for x in t)


def _aristas(poblacion: np.ndarray) -> np.ndarray:
    """Clave entera de cada arista no dirigida, por individuo: (pop, n)."""
    n = poblacion.shape[1]
    a, b = poblacion, np.roll(poblacion, -1, axis=1)
    return np.minimum(a, b) * n + np.maximum(a, b)


def _diversidad(poblacion: np.ndarray, mejor: np.ndarray) -> tuple[int, float]:
    distintos = len({_canonico(t) for t in poblacion})
    n = poblacion.shape[1]
    clave_mejor = set(_aristas(mejor[None, :])[0].tolist())
    comparte = [len(clave_mejor.intersection(fila.tolist())) / n for fila in _aristas(poblacion)]
    return distintos, float(np.mean(comparte))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(RAIZ / "configs" / "part2" / "base.yaml"))
    p.add_argument("--set", dest="overrides", action="append", default=[], metavar="clave=valor")
    p.add_argument("--semilla", type=int, default=0, help="run_id para make_rng(base_seed, run_id)")
    p.add_argument("--guardar", metavar="CARPETA", help="guarda PNG en la carpeta en vez de abrir ventanas")
    args = p.parse_args()

    if args.guardar:
        import matplotlib

        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cfg = apply_overrides(load_config(args.config), args.overrides)
    C, peaje, _ = _matriz(cfg)
    lon, lat, nombres = _leer_ciudades()
    c_nn = _vecino_mas_cercano(C)
    w = cfg["costo"]["valor_hora"]

    # Corrida del GA: una sola pasada con iterar (la población de cada generación).
    gens, evals, mejor, media, peor, distintos, compartidas, tours = [], [], [], [], [], [], [], []
    for est in iterar(C, cfg, make_rng(cfg["base_seed"], args.semilla)):
        costos = np.asarray(est["costos"])
        d, comp = _diversidad(np.asarray(est["poblacion"]), np.asarray(est["best_tour"]))
        gens.append(est["g"])
        evals.append(est["n_tour_evals"])
        mejor.append(est["best_cost"])
        media.append(float(costos.mean()))
        peor.append(float(costos.max()))
        distintos.append(d)
        compartidas.append(comp)
        tours.append(list(est["best_tour"]))
    gens = np.asarray(gens)
    tamano = cfg["ga"]["poblacion"]
    print(f"GA   costo = {mejor[-1]:.2f} €  |  recorridos evaluados = {evals[-1]}  "
          f"|  mejora sobre vecino más cercano = {100 * (1 - mejor[-1] / c_nn):.2f} %")

    res_aco = aco.solve(C, cfg, make_rng(cfg["base_seed"], args.semilla))
    m = cfg["aco"]["hormigas"]
    print(f"{cfg['aco']['variante'].upper():4s} costo = {res_aco['cost']:.2f} €  |  recorridos evaluados = "
          f"{res_aco['n_tour_evals']}")
    print(f"Vecino más cercano = {c_nn:.2f} €  (w = {w} €/h, semilla {args.semilla})")

    # 1. Convergencia
    fig1, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(evals, peor, color="tab:orange", lw=0.8, alpha=0.8, label="GA peor de la población")
    ax.plot(evals, media, color="tab:cyan", lw=1, label="GA media de la población")
    ax.plot(evals, mejor, color=COLOR_GA, lw=1.8, label=f"GA mejor global (final {mejor[-1]:.2f} €)")
    ax.plot([1 + m * (h["iter"] + 1) for h in res_aco["history"]], [h["best_cost"] for h in res_aco["history"]],
            color="tab:green", label=f"{cfg['aco']['variante'].upper()} mejor global (final {res_aco['cost']:.2f} €)")
    ax.axhline(c_nn, ls="--", color="gray", label=f"Vecino más cercano ({c_nn:.2f} €)")
    ax.set_xscale("log")
    ax.set_xlabel("Recorridos evaluados (escala log)")
    ax.set_ylabel("Costo (€)")
    ax.set_title(f"Convergencia GA — w = {w} €/h, semilla {args.semilla}, eje x logarítmico")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    fig1.tight_layout()

    # 2. Diversidad
    fig2, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.5))
    a1.plot(gens, distintos, color=COLOR_GA)
    a1.set_ylim(0, tamano * 1.05)
    a1.axhline(tamano, ls=":", color="gray", label=f"población ({tamano})")
    a1.set_xlabel("Generación")
    a1.set_ylabel("Recorridos distintos (forma canónica)")
    a1.set_title("Recorridos distintos en la población")
    a1.legend(fontsize=8)
    a2.plot(gens, compartidas, color="tab:purple")
    a2.set_ylim(0, 1.02)
    a2.set_xlabel("Generación")
    a2.set_ylabel("Fracción de aristas compartida con el mejor")
    a2.set_title("Aristas que cada individuo comparte con el mejor (media)")
    for a in (a1, a2):
        a.grid(alpha=0.3)
    fig2.suptitle(f"Diversidad del GA — semilla {args.semilla}")
    fig2.tight_layout()

    # 3. Recorrido final
    fig3, ax = plt.subplots(figsize=(8, 7))
    _dibujar_tour(ax, tours[-1], lon, lat, nombres, peaje,
                  f"GA final (gen {gens[-1]}): {mejor[-1]:.2f} € (peajes {_peaje_total(tours[-1], peaje):.2f} €)")
    fig3.legend(
        handles=[plt.Line2D([], [], color=COLOR_CON_PEAJE, lw=2.2, label="paga peaje (€ del tramo)"),
                 plt.Line2D([], [], color=COLOR_SIN_PEAJE, lw=1.2, label="sin peaje")],
        loc="lower center", ncol=2,
    )
    fig3.tight_layout(rect=(0, 0.05, 1, 1))

    # 4. Evolución del mejor recorrido
    ultimo = len(gens) - 1
    indices = sorted({0, ultimo // 10, ultimo // 2, ultimo})
    fig4, axes = plt.subplots(1, len(indices), figsize=(4.5 * len(indices), 4.8))
    for ax, k in zip(np.atleast_1d(axes), indices):
        _dibujar_tour(ax, tours[k], lon, lat, nombres, peaje,
                      f"generación {gens[k]}: {mejor[k]:.2f} €", etiquetas=False)
    fig4.suptitle("Evolución del mejor recorrido global (GA)")
    fig4.tight_layout()

    # Números de la figura 2 en generaciones de interés
    for g in sorted({0, 100, 500, int(gens[-1])}):
        if g <= gens[-1]:
            k = int(np.where(gens == g)[0][0])
            print(f"Diversidad gen {g:4d}: distintos = {distintos[k]:3d}/{tamano}, "
                  f"aristas compartidas con el mejor = {compartidas[k]:.3f}, mejor = {mejor[k]:.2f} €")

    if args.guardar:
        carpeta = Path(args.guardar)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, fig in (("convergencia", fig1), ("diversidad", fig2), ("recorrido_final", fig3),
                            ("evolucion_ga", fig4)):
            fig.savefig(carpeta / f"{nombre}.png", dpi=130)
        print(f"Figuras guardadas en {carpeta.resolve()}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
