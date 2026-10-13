"""Datos del GIF de trayectorias de la Parte 1 en 2D (T4.3).

Este módulo no dibuja: ejecuta cinco corridas en 2D y escribe un JSON que el GIF solo lee
(Spec §4). Corridas: Rosenbrock y Rastrigin con `gdfijo` y `gdarmijo`, y Rastrigin con `pso`;
todas con `base_seed`, `run_id = 0`, k = 2n y `presupuesto_por_dim` de la config.

Conteo: toda evaluación del experimento pasa por `ejecutar_corrida` (`CountedProblem`). Única
excepción: para rotular f en el punto `best` de cada marca se llama a `get_function(func, 2).f`;
esas llamadas no cuentan evaluaciones porque no forman parte del experimento.

Marcas (eje de tiempo = iteración): `indices_submuestreo(n_iter, MARCAS_MAX)`; en GD una lista
común a las dos variantes con el mayor n_iter. En la marca t se usa el fotograma con
`iter = min(t, n_iter)`, de modo que la variante que termina antes se sostiene en su último.

- `fotograma_en`: fotograma de `iter = min(t, n_iter)`, buscado por su campo `iter`.
- `construir_datos`: el diccionario del contrato {"meta", "gd", "pso"}.
- `guardar` / `generar`: escritura del JSON (lo usa `scripts/part1_gif_trayectorias.py`).
"""

from __future__ import annotations

from pathlib import Path

from src.common.config import load_config
from src.common.results import save_json
from src.part1.corrida import ejecutar_corrida
from src.part1.eta_deslizador import indices_submuestreo
from src.part1.functions import get_function

DIM = 2                        # los fotogramas solo existen en 2D (§5.1)
RUN_ID = 0
MARCAS_MAX = 45                # máximo de marcas (fotogramas del GIF) por función
FUNCIONES_GD = ("rosenbrock", "rastrigin")
METODOS_GD = ("gdfijo", "gdarmijo")
FUNC_PSO = "rastrigin"
METODO_PSO = "pso"
NOMBRE_ARCHIVO = "gif_trayectorias.json"


def _punto(p) -> list[float]:
    return [float(c) for c in p]


def fotograma_en(frames: list[dict], t: int) -> dict:
    """Fotograma cuyo campo `iter` es min(t, n_iter), con n_iter = `iter` del último.

    Se busca por el campo `iter`, no por la posición en la lista. ValueError si ese `iter`
    no está o si aparece repetido.
    """
    n_iter = int(frames[-1]["iter"])
    buscado = min(int(t), n_iter)
    encontrados = [frame for frame in frames if int(frame["iter"]) == buscado]
    if len(encontrados) != 1:
        raise ValueError(f"se esperaba un fotograma con iter = {buscado}; hay {len(encontrados)}")
    return encontrados[0]


def _corrida(cfg: dict, func: str, method: str) -> dict:
    return ejecutar_corrida(func, DIM, method, cfg["base_seed"], RUN_ID, cfg,
                            presupuesto_por_dim=cfg["presupuesto_por_dim"], grabar_frames=True)


def _n_iter(corrida: dict) -> int:
    return int(corrida["result"]["frames"][-1]["iter"])


def _resumen(corrida: dict) -> dict:
    resultado = corrida["result"]
    return {"n_iter": _n_iter(corrida), "f_best": float(resultado["f_best"]), "n_f": int(resultado["n_f"])}


def _entrada_gd(func: str, corridas: dict, marcas_max: int) -> dict:
    f = get_function(func, DIM).f
    iteraciones = indices_submuestreo(max(_n_iter(c) for c in corridas.values()), marcas_max)
    metodos = {}
    for method, corrida in corridas.items():
        frames = corrida["result"]["frames"]
        elegidos = [fotograma_en(frames, t) for t in iteraciones]
        metodos[method] = {**_resumen(corrida), "n_grad": int(corrida["result"]["n_grad"]),
                           "x": [_punto(fr["positions"][0]) for fr in elegidos],
                           "f": [float(f(fr["best"])) for fr in elegidos]}
    return {"iteraciones": iteraciones, "metodos": metodos}


def _entrada_pso(corrida: dict, marcas_max: int) -> dict:
    f = get_function(FUNC_PSO, DIM).f
    frames = corrida["result"]["frames"]
    iteraciones = indices_submuestreo(_n_iter(corrida), marcas_max)
    elegidos = [fotograma_en(frames, t) for t in iteraciones]
    return {"iteraciones": iteraciones, **_resumen(corrida),
            "enjambre": [[_punto(p) for p in fr["positions"]] for fr in elegidos],
            "mejor": [_punto(fr["best"]) for fr in elegidos],
            "f_mejor": [float(f(fr["best"])) for fr in elegidos]}


def construir_datos(cfg: dict, ruta_config: str | Path, marcas_max: int = MARCAS_MAX) -> dict:
    """Diccionario {"meta", "gd", "pso"} del GIF; ejecuta exactamente cinco corridas.

    `ruta_config` se guarda en `meta.config` como texto con "/". No modifica `cfg`.
    """
    gd, primera = {}, None
    for func in FUNCIONES_GD:
        corridas = {method: _corrida(cfg, func, method) for method in METODOS_GD}
        primera = primera or corridas[METODOS_GD[0]]
        gd[func] = _entrada_gd(func, corridas, marcas_max)
    pso = {FUNC_PSO: _entrada_pso(_corrida(cfg, FUNC_PSO, METODO_PSO), marcas_max)}
    meta = {"config": str(ruta_config).replace("\\", "/"), "base_seed": int(cfg["base_seed"]),
            "run_id": RUN_ID, "dim": DIM, "k": float(primera["k"]), "budget": float(primera["budget"]),
            "marcas_max": int(marcas_max)}
    return {"meta": meta, "gd": gd, "pso": pso}


def guardar(datos: dict, ruta: str | Path) -> Path:
    """Escribe `datos` como JSON compacto (sin sangría, para el tamaño) y devuelve la ruta."""
    return save_json(ruta, datos, sangria=None)


def generar(ruta_config: str | Path, salida: str | Path | None = None) -> Path:
    """Carga la config, construye los datos y los guarda. `salida` None = `<cfg["salida"]>/gif_trayectorias.json`."""
    cfg = load_config(ruta_config)
    destino = Path(cfg["salida"]) / NOMBRE_ARCHIVO if salida is None else Path(salida)
    return guardar(construir_datos(cfg, ruta_config), destino)
