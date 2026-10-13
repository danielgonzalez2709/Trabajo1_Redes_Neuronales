"""Datos de las figuras de la Parte 1 (T4.2; Spec §6.7). Puro: sin Plotly y sin ejecutar optimizadores.

Lee los JSON de corrida de una carpeta de experimento (`results/data/part1/` o `part1_tuned/`; Spec §5.4) y prepara lo
que dibuja `part1_interactivas`: curvas de convergencia en una rejilla común, f finales, mallas de las funciones y
qué métodos cambiaron de hiperparámetros entre el experimento por defecto y el afinado (T1.10).

f*, x* y los dominios salen siempre de `src.part1.functions.get_function`.
"""

from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.common.results import load_json, run_filename
from src.part1.functions import get_function

ARCHIVO_RESUMEN = "summary.json"
CARPETA_CORRIDAS = "runs"
PUNTOS_REJILLA = 200  # puntos (antes de quitar duplicados) de la rejilla geométrica de evaluaciones equivalentes
CUARTILES = (25, 50, 75)
CAMPOS_COMUNES = ("budget", "k")  # deben coincidir entre por defecto y afinado (además de las semillas)

Clave = tuple[str, int, str]  # (func, dim, method)


class DatosFaltantes(FileNotFoundError):
    """Falta el resumen o alguna corrida de un experimento (las carpetas `runs/` no se versionan)."""


# ------------------------------------------------------------------------------------------------ carga


def cargar_experimento(carpeta: Path) -> dict:
    """{meta, resumen, corridas}: `corridas[(func, dim, method)]` = lista de JSON de corrida en el orden de
    `meta.semillas`; las claves siguen el orden func × dim × methods de `meta` (summary.json).

    Lanza `DatosFaltantes` si no existe `summary.json` o falta alguna de las corridas que `meta` anuncia."""
    carpeta = Path(carpeta)
    ruta_resumen = carpeta / ARCHIVO_RESUMEN
    if not ruta_resumen.is_file():
        raise DatosFaltantes(f"no existe {ruta_resumen}")
    resumen = load_json(ruta_resumen)
    meta = resumen["meta"]
    rutas = {
        (func, dim, method): [carpeta / CARPETA_CORRIDAS / run_filename(func, dim, method, s) for s in meta["semillas"]]
        for func in meta["func"] for dim in meta["dim"] for method in meta["methods"]
    }
    todas = [r for grupo in rutas.values() for r in grupo]
    faltan = [r for r in todas if not r.is_file()]
    if faltan:
        raise DatosFaltantes(f"faltan {len(faltan)} de {len(todas)} corridas en {carpeta / CARPETA_CORRIDAS} "
                             f"(la primera: {faltan[0].name})")
    return {"meta": meta, "resumen": resumen,
            "corridas": {clave: [load_json(r) for r in grupo] for clave, grupo in rutas.items()}}


def celdas(corridas: dict[Clave, list]) -> list[tuple[str, int]]:
    """Pares (func, dim) en el orden en que aparecen en las claves."""
    return list(dict.fromkeys((func, dim) for func, dim, _ in corridas))


def metodos_de(corridas: dict[Clave, list], func: str, dim: int) -> list[str]:
    return [m for f, d, m in corridas if (f, d) == (func, dim)]


# ------------------------------------------------------------------------------------- convergencia


def rejilla(presupuesto: float, n_puntos: int = PUNTOS_REJILLA) -> np.ndarray:
    """Enteros únicos espaciados geométricamente de 1 a `presupuesto` (ambos incluidos)."""
    if not float(presupuesto).is_integer() or presupuesto < 1:
        raise ValueError(f"el presupuesto debe ser un entero >= 1; se recibió {presupuesto!r}")
    tope = int(presupuesto)
    r = np.unique(np.rint(np.geomspace(1, tope, n_puntos)).astype(np.int64))
    r[0], r[-1] = 1, tope  # extremos exactos (rint ya los da; queda explícito)
    return r


def _valor_comun(corridas: list[dict], campo: str, nombre: str):
    valores = {c[campo] for c in corridas}
    if len(valores) != 1:
        raise ValueError(f"las corridas no comparten {nombre}: {sorted(valores)}")
    return valores.pop()


def _escalon(corrida: dict, x: np.ndarray, f_star: float) -> np.ndarray:
    """f_best − f* del último registro de `history` con eval_equiv <= x; NaN si aún no hay ninguno."""
    hist = corrida["result"]["history"]
    evals = np.array([h["eval_equiv"] for h in hist], dtype=float)
    valores = np.array([h["f_best"] for h in hist], dtype=float) - f_star
    idx = np.searchsorted(evals, x, side="right") - 1
    return np.where(idx >= 0, valores[np.maximum(idx, 0)], np.nan)


def curva_convergencia(corridas: list[dict], f_star: float, n_puntos: int = PUNTOS_REJILLA) -> dict:
    """{rejilla, mediana, q25, q75} de f_best − f* entre corridas, en la rejilla de evaluaciones equivalentes.

    Los NaN (corrida sin registros todavía) se ignoran; si ninguna corrida tiene registro, el punto es NaN."""
    x = rejilla(_valor_comun(corridas, "budget", "presupuesto"), n_puntos)
    valores = np.array([_escalon(c, x, f_star) for c in corridas])
    with warnings.catch_warnings():  # columna toda NaN: numpy avisa y devuelve NaN, que es lo que se quiere
        warnings.simplefilter("ignore", RuntimeWarning)
        q25, mediana, q75 = np.nanpercentile(valores, CUARTILES, axis=0)
    return {"rejilla": x, "mediana": mediana, "q25": q25, "q75": q75}


def f_finales(corridas: list[dict], f_star: float) -> list[float]:
    """f_best − f* de cada corrida, en el orden recibido."""
    return [c["result"]["f_best"] - f_star for c in corridas]


# ------------------------------------------------------------------------------------------------ malla


@lru_cache(maxsize=None)  # varias figuras comparten malla; los arreglos devueltos no se escriben
def malla(nombre: str, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x, y, z) de la función 2D en una malla n × n sobre su dominio; z[i, j] = f(x[j], y[i]) (convención de Plotly).
    Los arreglos son de solo lectura (el resultado se guarda en caché)."""
    func = get_function(nombre, 2)
    x = np.linspace(func.bounds[0, 0], func.bounds[0, 1], n)
    y = np.linspace(func.bounds[1, 0], func.bounds[1, 1], n)
    z = np.array([[func.f([xj, yi]) for xj in x] for yi in y])
    for arreglo in (x, y, z):
        arreglo.setflags(write=False)
    return x, y, z


# ------------------------------------------------------------------------------ por defecto vs. afinado


def bloque_hiperparametros(config: dict, func: str, method: str):
    """Parte del `config` guardado que define al método: gdfijo → gd.eta[func]; gdarmijo → gd.armijo; el resto → su
    bloque (`config[method]`)."""
    if method == "gdfijo":
        return config["gd"]["eta"][func]
    if method == "gdarmijo":
        return config["gd"]["armijo"]
    return config[method]


def _bloque_del_grupo(corridas: list[dict], clave: Clave):
    func, _, method = clave
    bloques = [bloque_hiperparametros(c["config"], func, method) for c in corridas]
    if any(b != bloques[0] for b in bloques):
        raise ValueError(f"{clave}: las corridas no comparten hiperparámetros")
    return bloques[0]


def metodos_afinados(corridas_defecto: dict[Clave, list], corridas_afinadas: dict[Clave, list]) -> dict:
    """{(func, dim): [métodos cuyo bloque de hiperparámetros difiere entre ambos experimentos]} (en el orden de las
    claves de `corridas_defecto`; lista vacía si en la celda no cambió ninguno)."""
    cambios: dict[tuple[str, int], list[str]] = {celda: [] for celda in celdas(corridas_defecto)}
    for clave, grupo in corridas_defecto.items():
        func, dim, method = clave
        if _bloque_del_grupo(grupo, clave) != _bloque_del_grupo(corridas_afinadas[clave], clave):
            cambios[(func, dim)].append(method)
    return cambios


def comprobar_comparables(corridas_defecto: dict[Clave, list], corridas_afinadas: dict[Clave, list]) -> None:
    """ValueError si los dos experimentos no tienen las mismas configuraciones, semillas, presupuesto y k."""
    if set(corridas_defecto) != set(corridas_afinadas):
        raise ValueError("por defecto y afinado no tienen las mismas configuraciones (func, dim, method): "
                         f"{sorted(set(corridas_defecto) ^ set(corridas_afinadas))}")
    for clave, grupo in corridas_defecto.items():
        otro = corridas_afinadas[clave]
        if [c["seed"] for c in grupo] != [c["seed"] for c in otro]:
            raise ValueError(f"{clave}: por defecto y afinado no comparten semillas")
        for campo in CAMPOS_COMUNES:
            if {c[campo] for c in grupo} != {c[campo] for c in otro} or len({c[campo] for c in grupo}) != 1:
                raise ValueError(f"{clave}: por defecto y afinado no comparten {campo}")
