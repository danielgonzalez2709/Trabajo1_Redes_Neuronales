"""Corridas sintéticas de la Parte 1 con la forma del Spec §5.4, para las pruebas de las figuras (T4.2).

Ninguna prueba de las figuras depende de `results/data/part1/runs/` (ignorada por git).
"""
import copy

from src.common.results import run_filename, save_json

CONFIG = {
    "gd": {"eta": {"rosenbrock": 1e-3, "rastrigin": 2e-3}, "armijo": {"eta0": 1.0, "beta": 0.5, "c": 1e-4},
           "tol_grad": 1e-8},
    "ea": {"N": 50}, "pso": {"N": 30, "w": 0.7}, "de": {"NP": 30},
}
METODOS = ("gdfijo", "gdarmijo", "ea", "pso", "de")
FUNCIONES = ("rosenbrock", "rastrigin")
DIMENSIONES = (2, 3)
SEMILLAS = (0, 1, 2)
PRESUPUESTO = 100.0


def corrida(func="rosenbrock", dim=2, method="pso", seed=0, history=((1, 8.0),), budget=PRESUPUESTO, k=4.0,
            config=None, frames=None) -> dict:
    hist = [{"eval_equiv": float(e), "f_best": float(f)} for e, f in history]
    result = {"x_best": [0.0] * dim, "f_best": hist[-1]["f_best"], "n_f": 0, "n_grad": 0,
              "eval_equiv": hist[-1]["eval_equiv"], "history": hist}
    if frames is not None:
        result["frames"] = frames
    return {"func": func, "dim": dim, "method": method, "seed": seed, "k": k, "budget": budget,
            "config": copy.deepcopy(CONFIG if config is None else config), "result": result}


def _frames(n_iter=6, n_particulas=4) -> list[dict]:
    """Enjambre que se contrae hacia el origen."""
    frames = []
    for t in range(n_iter):
        r = 3.0 / (t + 1)
        pos = [[r * (-1) ** i, r * (i - 1.5) / 2] for i in range(n_particulas)]
        frames.append({"iter": t, "positions": pos, "best": pos[0]})
    return frames


def experimento(config=None, escala=1.0, semillas=SEMILLAS) -> dict:
    """{(func, dim, method): [corridas]}: el final de la corrida s del método i vale escala·(i + 1)·10^−s; `de` llega
    a 0 exacto. Frames solo en la primera semilla de dim 2 (como el experimento real)."""
    corridas = {}
    for func in FUNCIONES:
        for dim in DIMENSIONES:
            for i, method in enumerate(METODOS):
                grupo = []
                for s in semillas:
                    final = 0.0 if method == "de" else escala * (i + 1) * 10.0 ** (-s)
                    inicio = 0 if method.startswith("gd") else 1
                    hist = [(inicio, 50.0 + s), (10 + s, 5.0), (40, final)]
                    frames = _frames() if (dim == 2 and s == semillas[0]) else None
                    grupo.append(corrida(func, dim, method, s, hist, config=config, frames=frames))
                corridas[(func, dim, method)] = grupo
    return corridas


def config_afinada() -> dict:
    """Cambian gd.eta.rosenbrock (gdfijo solo en Rosenbrock) y el bloque `ea`; gdarmijo, pso y de quedan igual."""
    cfg = copy.deepcopy(CONFIG)
    cfg["gd"]["eta"]["rosenbrock"] = 1.5e-3
    cfg["ea"]["N"] = 117
    return cfg


def escribir_experimento(carpeta, corridas: dict, semillas=SEMILLAS, omitir=None):
    """Escribe summary.json (meta + medianas) y runs/*.json en `carpeta`. `omitir` = clave (func, dim, method, seed)."""
    import numpy as np

    meta = {"semillas": list(semillas), "func": list(dict.fromkeys(c[0] for c in corridas)),
            "dim": list(dict.fromkeys(c[1] for c in corridas)), "methods": list(dict.fromkeys(c[2] for c in corridas))}
    configuraciones = [{"func": f, "dim": d, "method": m,
                        "f_final": {"mediana": float(np.median([c["result"]["f_best"] for c in grupo]))}}
                       for (f, d, m), grupo in corridas.items()]
    save_json(carpeta / "summary.json", {"meta": meta, "configuraciones": configuraciones})
    for (f, d, m), grupo in corridas.items():
        for c in grupo:
            if (f, d, m, c["seed"]) != omitir:
                save_json(carpeta / "runs" / run_filename(f, d, m, c["seed"]), c)


def eta_json() -> dict:
    """JSON del deslizador de η con la forma del contrato de T4.2-A."""
    x0 = [-1.2, 1.0]

    def entrada(eta, marca, n_iter):
        its = sorted({0, n_iter // 2, n_iter})
        puntos = [x0] + [[x0[0] + 0.1 * j, x0[1] - 0.05 * j] for j in range(1, len(its))]
        return {"eta": eta, "marca": marca, "f_best": 2.0 * eta, "n_grad": n_iter + 1, "n_iter": n_iter,
                "iteraciones": its, "puntos": puntos}

    return {"meta": {"func": "rosenbrock", "dim": 2, "method": "gdfijo", "seed": 0, "k": 4.0, "budget": 20000.0,
                     "x0": x0, "puntos_max": 150},
            "etas": [entrada(1e-5, None, 10), entrada(1e-3, "defecto", 40), entrada(1.5e-3, "afinado", 30),
                     entrada(1e-2, None, 20)]}
