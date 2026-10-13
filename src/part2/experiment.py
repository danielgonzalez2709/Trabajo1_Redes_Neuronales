"""Experimento de la Parte 2: barrido de w, umbral por envolvente, gaps y sensibilidad (Spec §7.4, §7.5, §5.4).

Costo de cada par (§7.3): c_ij(w) = mín_a (w·t^a_ij + P^a_ij + d^a_ij·(consumo/100)·precio_l), a ∈ {rapida, sin_peaje}.
Pasos: (1) para cada w de `costo.valor_hora` se corren `runs` corridas de MMAS, AS y GA con `make_rng`; (2) los
recorridos finales, canonicalizados, son los candidatos; (3) la envolvente inferior exacta (`envolvente.py`) da los
umbrales; (4) en cada w, mejor encontrado = mínimo de todos los candidatos, y gap % = 100·(costo − mejor)/mejor.
Con `costo.consumo_l100` o `costo.precio_l` no nulos es una corrida de sensibilidad (salida aparte, unión con la base).
Con `experimento.referencia_gap` no nulo es la demo (§7.7, T3.7): un solo w, gap frente al mejor conocido de ese w en
el `sweep_w.json` indicado ([DECIDIDO v1.17]: no es un óptimo probado), `demo.json` y la figura del recorrido.
Uso: `python run.py part2 --config configs/part2/sweep_w.yaml` (barrido),
`python run.py part2 --config configs/part2/sensibilidad_consumo.yaml [--set costo.consumo_l100=6.2]` y
`python run.py part2 --config configs/part2/demo.yaml` (demo).
"""

from __future__ import annotations

import copy
import csv
import dataclasses
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.common.config import cargar_yaml
from src.common.results import load_json, save_json
from src.common.seeds import make_rng, validar_entero
from src.part2 import aco, ga, recorridos
from src.part2.costos import ARCHIVO_RUTAS, CLAVE_CONSUMO, Componentes, cargar_componentes, matriz_costos
from src.part2.envolvente import Rectas, canonico, costo_envolvente, envolvente, rectas
from src.viz.part2_figs import figura_recorrido

RAIZ = Path(__file__).resolve().parents[2]

SOLVERS = ("mmas", "as", "ga")  # orden fijo: define run_id y el orden de las salidas
FAMILIA = {"mmas": "aco", "as": "aco", "ga": "ga"}
SOLVE = {"mmas": aco.solve, "as": aco.solve, "ga": ga.solve}
ITERAR = {"mmas": aco.iterar, "as": aco.iterar, "ga": ga.iterar}
METODOS = ("aco", "ga", "exacto")  # Spec §4.1
SOLVER_GAP_ACO = "mmas"  # §7.4.1: MMAS es la variante principal de ACO
SOLVER_GAP_GA = "ga"

ARCHIVO_VEHICULO = "vehiculo.yaml"
ARCHIVO_COMBUSTIBLE = "combustible.json"
CLAVE_PRECIO = "precio_medio_eur_l"  # combustible.json (Spec §5.3, v1.6: media peninsular)
ARCHIVO_SWEEP = "sweep_w.json"
ARCHIVO_UMBRALES = "umbrales_w.json"
ARCHIVO_COMPARACION = "comparacion_base.json"
CARPETA_SENSIBILIDAD = "sensibilidad"
ARCHIVO_CIUDADES = "cities.csv"  # §5.3: coordenadas (lon, lat) para la figura de la demo
ARCHIVO_DEMO = "demo.json"
FIGURA_DEMO = "recorrido_w{w}.png"
NOMBRE_SOLVER = {"mmas": "MMAS", "as": "AS", "ga": "GA"}
NOTA_DEMO = (
    "Gap frente al mejor conocido: el mejor costo encontrado en este w por el barrido de T3.6 (sweep_w.json), "
    "no frente a un óptimo probado (Spec §7.7, v1.17)."
)
SANGRIA_HISTORIALES = None  # JSON compacto: decisión de Jose Miguel (12-oct) para reducir el tamaño en results/
NOTA_UMBRAL = (
    "Umbral entre las mejores rutas encontradas en el barrido (todos los w, métodos y corridas), "
    "no umbral del óptimo probado (Spec §7.5)."
)
REGLA_SEMILLAS = (
    f"seed = base_seed + run_id; run_id = (i_w · {len(SOLVERS)} + i_solver) · runs + r, i_solver en SOLVERS"
)

TOL_REL = 1e-9  # comprobaciones internas de consistencia (sumas de los mismos números en otro orden)


# --------------------------------------------------------------------------------------------- datos


@dataclass(frozen=True, eq=False)
class Datos:
    """Componentes de costo, km con peaje por alternativa y valores de los archivos (consumo y precio)."""

    comp: Componentes
    km_peaje_rapida: np.ndarray
    km_peaje_sin_peaje: np.ndarray
    consumo_l100: float  # vehiculo.yaml: consumo_wltp_comb_l100
    precio_l: float  # combustible.json: precio_medio_eur_l


def _cargar_km_peaje(ruta: Path, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Matrices n×n de `km_peaje` (rápida, sin peaje) de rutas.csv, por espejo (cargar_componentes ya validó i < j)."""
    km = {alt: np.zeros((n, n)) for alt in ("rapida", "sin_peaje")}
    with ruta.open(encoding="utf-8", newline="") as f:
        for numero, fila in enumerate(csv.DictReader(f), start=2):
            i, j = int(fila["i"]), int(fila["j"])
            valor = recorridos.validar_real(float(fila["km_peaje"]), f"{ruta}, línea {numero}: km_peaje", 0.0)
            km[fila["alternativa"]][i, j] = km[fila["alternativa"]][j, i] = valor
    return km["rapida"], km["sin_peaje"]


def cargar_datos(path: str | Path = RAIZ / "data" / "processed") -> Datos:
    """Lee rutas.csv (componentes y km con peaje), vehiculo.yaml (consumo) y combustible.json (precio)."""
    path = Path(path)
    comp = cargar_componentes(path)
    km_r, km_s = _cargar_km_peaje(path / ARCHIVO_RUTAS, comp.tiempo_h_rapida.shape[0])
    vehiculo = cargar_yaml((path / ARCHIVO_VEHICULO).read_text(encoding="utf-8"))
    precio = json.loads((path / ARCHIVO_COMBUSTIBLE).read_text(encoding="utf-8"))[CLAVE_PRECIO]
    return Datos(
        comp=comp,
        km_peaje_rapida=km_r,
        km_peaje_sin_peaje=km_s,
        consumo_l100=recorridos.validar_real(vehiculo[CLAVE_CONSUMO], CLAVE_CONSUMO, 0.0, min_abierto=True),
        precio_l=recorridos.validar_real(precio, CLAVE_PRECIO, 0.0, min_abierto=True),
    )


def consumo_y_precio(cfg: dict, datos: Datos) -> tuple[float, float]:
    """(consumo l/100 km, precio €/l) de `costo.consumo_l100` y `costo.precio_l`; `null` = valor de los archivos
    (§7.5)."""
    costo = recorridos.leer_clave(cfg, "costo", "costo", "§7.5")
    valores = []
    for clave, del_archivo in (("consumo_l100", datos.consumo_l100), ("precio_l", datos.precio_l)):
        valor = recorridos.leer_clave(costo, clave, f"costo.{clave}", "§7.5")
        valores.append(
            del_archivo if valor is None
            else recorridos.validar_real(valor, f"costo.{clave}", 0.0, min_abierto=True)
        )
    return valores[0], valores[1]


# ------------------------------------------------------------------------------- desglose y estadísticas


def arcos(datos: Datos, tour, w: float, consumo_l100: float, precio_l: float) -> dict[str, np.ndarray]:
    """Por arco del recorrido cerrado (tour[k] → tour[k+1]; el último cierra el ciclo): {tiempo €, peajes €,
    combustible €, km_peaje} con la alternativa que elige `matriz_costos` (incluido su desempate en `rapida`, §7.3)."""
    comp = datos.comp
    _, alternativa = matriz_costos(comp, w, {CLAVE_CONSUMO: consumo_l100}, precio_l)
    sin_peaje = alternativa == "sin_peaje"
    t = np.asarray(tour)
    u, v = t, np.roll(t, -1)

    def elegido(rapida, sin):
        return np.where(sin_peaje, sin, rapida)[u, v]

    return {
        "tiempo": w * elegido(comp.tiempo_h_rapida, comp.tiempo_h_sin_peaje),
        "peajes": elegido(comp.peaje_eur_rapida, comp.peaje_eur_sin_peaje),
        "combustible": elegido(comp.dist_km_rapida, comp.dist_km_sin_peaje) * (consumo_l100 / 100) * precio_l,
        "km_peaje": elegido(datos.km_peaje_rapida, datos.km_peaje_sin_peaje),
    }


def desglose(datos: Datos, tour, w: float, consumo_l100: float, precio_l: float) -> dict:
    """{tiempo €, peajes €, combustible €, km_peaje} del recorrido en w: suma de `arcos`."""
    return {clave: float(x.sum()) for clave, x in arcos(datos, tour, w, consumo_l100, precio_l).items()}


def gap(costo: float, mejor: float) -> float:
    """Gap % = 100 · (costo − mejor) / mejor (§7.5; "mejor" = mejor encontrado en ese w)."""
    return 100.0 * (costo - mejor) / mejor


def estadisticas(costos, mejor: float) -> dict:
    """{n, mejor, media, desviacion (muestral, n − 1; None si n = 1), gap_mejor, gap_media}."""
    x = np.asarray(costos, dtype=float)
    media = float(x.mean())
    return {
        "n": int(x.size),
        "mejor": float(x.min()),
        "media": media,
        "desviacion": float(x.std(ddof=1)) if x.size > 1 else None,
        "gap_mejor": gap(float(x.min()), mejor),
        "gap_media": gap(media, mejor),
    }


# ------------------------------------------------------------------------------------- validación


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def presupuesto_recorridos(cfg: dict) -> tuple[int, int]:
    """(recorridos de ACO, recorridos del GA): 1 + hormigas·iteraciones (§7.4.1) y
    poblacion + (poblacion − elites)·generaciones (§7.4.2)."""
    bloque_aco = recorridos.leer_clave(cfg, "aco", "aco", "§7.4.1")
    bloque_ga = recorridos.leer_clave(cfg, "ga", "ga", "§7.4.2")

    def entero(bloque, familia, clave, minimo):
        return validar_entero(recorridos.leer_clave(bloque, clave, f"{familia}.{clave}", "§7.4"),
                              f"{familia}.{clave}", minimo)

    n_aco = 1 + entero(bloque_aco, "aco", "hormigas", 1) * entero(bloque_aco, "aco", "iteraciones", 1)
    poblacion = entero(bloque_ga, "ga", "poblacion", 2)
    n_ga = poblacion + (poblacion - entero(bloque_ga, "ga", "elites", 0)) * entero(bloque_ga, "ga", "generaciones", 1)
    return n_aco, n_ga


def comprobar_presupuesto(cfg: dict) -> int:
    """Número común de recorridos evaluados (Spec §7.4 [DECIDIDO v1.16]); ValueError si ACO y GA difieren."""
    n_aco, n_ga = presupuesto_recorridos(cfg)
    if n_aco != n_ga:
        raise ValueError(
            f"presupuesto común (Spec §7.4 v1.16): ACO evalúa {_miles(n_aco)} recorridos (1 + hormigas · "
            f"iteraciones) y el GA {_miles(n_ga)} (poblacion + (poblacion − elites) · generaciones); deben ser iguales"
        )
    return n_aco


def _leer_w(valor) -> list[float]:
    """`costo.valor_hora`: número o lista no vacía, finitos ≥ 0 y estrictamente crecientes."""
    valores = valor if isinstance(valor, list) else [valor]
    if not valores:
        raise ValueError("costo.valor_hora no puede ser una lista vacía")
    w = [recorridos.validar_real(x, "costo.valor_hora", 0.0) for x in valores]
    if any(b <= a for a, b in zip(w, w[1:])):
        raise ValueError(f"costo.valor_hora debe ser estrictamente creciente (sin repetidos); se recibió {valores}")
    return w


def _leer_lista(valor, nombre: str, validos: tuple[str, ...]) -> list[str]:
    if not isinstance(valor, list) or not valor:
        raise ValueError(f"{nombre} debe ser una lista no vacía ⊂ {validos}; se recibió {valor!r}")
    fuera = [x for x in valor if x not in validos]
    if fuera or len(set(valor)) != len(valor):
        raise ValueError(f"{nombre} debe ser una lista sin repetidos ⊂ {validos}; se recibió {valor!r}")
    return valor


def _leer_ruta(valor, nombre: str) -> Path:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nombre} debe ser una ruta (texto no vacío); se recibió {valor!r}")
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else RAIZ / ruta


def _texto_num(x: float) -> str:
    """25.0 → "25", 5.6 → "5.6" (nombres de archivo y carpetas)."""
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def _cfg_solver(cfg: dict, solver: str) -> dict:
    """Copia de la config para un solver; en ACO fija `aco.variante`."""
    copia = copy.deepcopy(cfg)
    if FAMILIA[solver] == "aco":
        copia["aco"]["variante"] = solver
    return copia


def run_id(i_w: int, solver: str, r: int, runs: int) -> int:
    """run_id = (i_w · |SOLVERS| + i_solver) · runs + r: distinto para cada (w, solver, corrida) del barrido."""
    return (i_w * len(SOLVERS) + SOLVERS.index(solver)) * runs + r


@dataclass(frozen=True, eq=False)
class Plan:
    """Config validada y datos cargados, listos para `correr`."""

    cfg: dict
    w: list[float]
    solvers: tuple[str, ...]
    runs: int
    base_seed: int
    datos: Datos
    consumo_l100: float
    precio_l: float
    salida: Path
    base: dict | None  # sensibilidad: {"umbrales": ..., "sweep": ...} del barrido base; None en el barrido base
    referencia: dict | None = None  # demo (§7.7): {archivo, w, cost, tour} del mejor conocido; None si no es demo
    coordenadas: tuple[np.ndarray, np.ndarray] | None = None  # demo: (lon, lat) por id de ciudad, de cities.csv


def _matriz(plan: Plan, w: float) -> np.ndarray:
    """Matriz de costos C en w con el consumo y el precio del plan (§7.3)."""
    C, _ = matriz_costos(plan.datos.comp, w, {CLAVE_CONSUMO: plan.consumo_l100}, plan.precio_l)
    return C


def _leer_base(salida_base: Path) -> dict:
    archivos = {"umbrales": salida_base / ARCHIVO_UMBRALES, "sweep": salida_base / ARCHIVO_SWEEP}
    faltan = [str(p) for p in archivos.values() if not p.is_file()]
    if faltan:
        raise FileNotFoundError(
            f"sensibilidad: no existe el barrido base en {salida_base} (faltan {faltan}); corre primero "
            "run.py part2 --config configs/part2/sweep_w.yaml con la misma experimento.salida"
        )
    return {clave: load_json(p) for clave, p in archivos.items()}


def _ruta_legible(ruta: Path) -> str:
    """Ruta relativa a la raíz del repositorio si está dentro; si no, absoluta."""
    try:
        return ruta.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return str(ruta)


def leer_referencia(ruta: Path, w: float, C: np.ndarray) -> dict:
    """Mejor conocido en w (§7.7 [DECIDIDO v1.17]): la entrada de ese w en un `sweep_w.json` (§5.4). Errores claros si
    falta el archivo o la entrada, si el recorrido no es una permutación o si su costo con la matriz actual `C` no es
    el guardado (datos, consumo o precio distintos): nunca se inventa una referencia."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(
            f"demo: no existe la referencia del gap {ruta} (Spec §7.7); corre primero el barrido "
            "(run.py part2 --config configs/part2/sweep_w.yaml) o ajusta experimento.referencia_gap"
        )
    filas = load_json(ruta)
    if not isinstance(filas, list):
        raise ValueError(f"{ruta}: se esperaba la lista de filas de sweep_w.json (Spec §5.4)")
    entradas = [e for e in filas if isinstance(e, dict) and e.get("w") == w]
    if len(entradas) != 1:
        raise ValueError(f"{ruta}: no tiene una (y solo una) entrada con w = {_texto_num(w)} €/h; no hay mejor "
                         "conocido para la demo (Spec §7.7)")
    e = entradas[0]
    costo = recorridos.validar_real(e.get("cost"), f"{ruta}: cost (w = {_texto_num(w)})", 0.0, min_abierto=True)
    tour, n = e.get("tour"), C.shape[0]
    if not isinstance(tour, list) or sorted(tour) != list(range(n)):
        raise ValueError(f"{ruta}: el tour de w = {_texto_num(w)} no es una permutación de 0..{n - 1}")
    recalculado = float(recorridos.costos_recorridos(C, np.array([tour]))[0])
    if not math.isclose(recalculado, costo, rel_tol=TOL_REL):
        raise ValueError(
            f"{ruta}: la referencia de w = {_texto_num(w)} no corresponde al modelo de costo actual (su recorrido "
            f"cuesta {recalculado:.6f} € y el archivo dice {costo:.6f} €): datos, consumo o precio distintos"
        )
    return {"archivo": _ruta_legible(ruta), "w": w, "cost": costo, "tour": tour}


def cargar_coordenadas(ruta: Path, n: int) -> tuple[np.ndarray, np.ndarray]:
    """(lon, lat) por id de ciudad de cities.csv (§5.3); exige los id 0..n−1, uno por ciudad de la matriz."""
    with Path(ruta).open(encoding="utf-8", newline="") as f:
        filas = sorted(csv.DictReader(f), key=lambda fila: int(fila["id"]))
    if [int(fila["id"]) for fila in filas] != list(range(n)):
        raise ValueError(f"{ruta}: los id deben ser 0..{n - 1} (una fila por ciudad de la matriz)")
    return np.array([float(fila["lon"]) for fila in filas]), np.array([float(fila["lat"]) for fila in filas])


def _validar_solvers(plan: Plan) -> None:
    """Valida C, el bloque de cada solver y el rng con `iterar`, que valida al llamarse: el generador que devuelve
    se descarta sin pedir ninguna iteración (no corre nada ni consume el rng)."""
    C = _matriz(plan, plan.w[0])
    for s in plan.solvers:
        ITERAR[s](C, _cfg_solver(plan.cfg, s), make_rng(plan.base_seed, 0))


def _etiqueta_sensibilidad(costo: dict) -> str | None:
    """Carpeta de la sensibilidad (p. ej. "consumo5.6", "consumo5.6_precio1.9"); None si es el barrido base."""
    partes = [f"{nombre}{_texto_num(costo[clave])}"
              for nombre, clave in (("consumo", "consumo_l100"), ("precio", "precio_l")) if costo[clave] is not None]
    return "_".join(partes) or None


def preparar(cfg: dict) -> Plan:
    """Valida la config completa y carga los datos, sin correr nada ni escribir archivos.

    Errores: ValueError/TypeError/KeyError (config) y FileNotFoundError (datos o barrido base de la sensibilidad).
    """
    methods = _leer_lista(recorridos.leer_clave(cfg, "methods", "methods", "§4.1"), "methods", METODOS)
    if "exacto" in methods:
        raise ValueError("methods: 'exacto' (T3.2) es opcional desde Spec v1.14 y no está implementado; quítalo")
    runs = validar_entero(recorridos.leer_clave(cfg, "runs", "runs", "§7.5"), "runs", minimo=1)
    base_seed = validar_entero(recorridos.leer_clave(cfg, "base_seed", "base_seed", "§4.1"), "base_seed")
    costo = recorridos.leer_clave(cfg, "costo", "costo", "§7.3")
    w = _leer_w(recorridos.leer_clave(costo, "valor_hora", "costo.valor_hora", "§7.5"))
    exp = recorridos.leer_clave(cfg, "experimento", "experimento", "§7.5")
    variantes = _leer_lista(recorridos.leer_clave(exp, "variantes_aco", "experimento.variantes_aco", "§7.5"),
                            "experimento.variantes_aco", aco.VARIANTES)
    datos_dir = _leer_ruta(recorridos.leer_clave(exp, "datos", "experimento.datos", "§7.5"), "experimento.datos")
    salida = _leer_ruta(recorridos.leer_clave(exp, "salida", "experimento.salida", "§5.4"), "experimento.salida")
    referencia_gap = recorridos.leer_clave(exp, "referencia_gap", "experimento.referencia_gap", "§7.7")
    solvers = tuple(s for s in SOLVERS if FAMILIA[s] in methods and (FAMILIA[s] != "aco" or s in variantes))

    datos = cargar_datos(datos_dir)
    consumo, precio = consumo_y_precio(cfg, datos)
    plan = Plan(cfg=cfg, w=w, solvers=solvers, runs=runs, base_seed=base_seed, datos=datos,
                consumo_l100=consumo, precio_l=precio, salida=salida, base=None)
    _validar_solvers(plan)
    if "aco" in methods and "ga" in methods:
        comprobar_presupuesto(cfg)

    if referencia_gap is not None:  # demo (§7.7): sin envolvente ni sensibilidad; la referencia valida el modelo
        if len(w) != 1:
            raise ValueError(f"la demo (experimento.referencia_gap) admite un solo valor de costo.valor_hora; "
                             f"se recibió {w}")
        ruta = _leer_ruta(referencia_gap, "experimento.referencia_gap")
        n = datos.comp.tiempo_h_rapida.shape[0]
        # La referencia se valida con la matriz del plan (consumo y precio efectivos): por eso, p. ej.,
        # `--set costo.consumo_l100=5.6` falla con "no corresponde" frente al barrido base de 4,6 l/100 km.
        return dataclasses.replace(plan, referencia=leer_referencia(ruta, w[0], _matriz(plan, w[0])),
                                   coordenadas=cargar_coordenadas(datos_dir / ARCHIVO_CIUDADES, n))

    etiqueta = _etiqueta_sensibilidad(costo)
    if etiqueta is not None:
        plan = dataclasses.replace(plan, base=_leer_base(salida), salida=salida / CARPETA_SENSIBILIDAD / etiqueta)
    return plan


# ------------------------------------------------------------------------------------------ ejecución


@dataclass(frozen=True, eq=False)
class Corridas:
    """Lo que dejan todas las corridas de un plan."""

    costos: dict[float, dict[str, list[float]]]  # w → solver → costo de cada corrida (recorrido canónico)
    hallazgos: dict[tuple[int, ...], list[dict]]  # recorrido canónico → [{w, metodo, run_id}]
    historiales: dict[tuple[float, str], dict]  # (w, familia) → contenido de history_{familia}_w{w}.json


def _registro_corrida(res: dict, rid: int, seed: int, iniciales: int, por_iter: int) -> dict:
    """Corrida para el historial: curva del mejor costo por iteración y el recorrido solo cuando cambia."""
    mejoras, anterior = [], None
    for h in res["history"]:
        if h["best_tour"] != anterior:
            mejoras.append({"iter": h["iter"], "best_cost": h["best_cost"], "best_tour": h["best_tour"]})
            anterior = h["best_tour"]
    if res["n_tour_evals"] != iniciales + por_iter * len(res["history"]):
        raise RuntimeError(f"conteo inesperado de recorridos en la corrida {rid}: {res['n_tour_evals']}")
    return {
        "run_id": rid, "seed": seed, "cost": res["cost"], "tour": res["tour"], "n_tour_evals": res["n_tour_evals"],
        "recorridos_iniciales": iniciales, "recorridos_por_iter": por_iter,
        "best_cost": [h["best_cost"] for h in res["history"]], "mejoras": mejoras,
    }


def _conteo(cfg: dict, solver: str) -> tuple[int, int]:
    """(recorridos iniciales, recorridos por iteración): ACO 1 y hormigas (§7.4.1); GA poblacion y
    poblacion − elites (§7.4.2)."""
    if FAMILIA[solver] == "aco":
        return 1, cfg["aco"]["hormigas"]
    return cfg["ga"]["poblacion"], cfg["ga"]["poblacion"] - cfg["ga"]["elites"]


def _verificar(valor: float, referencia: float, que: str) -> None:
    if not math.isclose(valor, referencia, rel_tol=TOL_REL):
        raise RuntimeError(f"{que}: {valor!r} ≠ {referencia!r} (tolerancia relativa {TOL_REL})")


def _correr_solvers(plan: Plan, imprimir: bool = True) -> Corridas:
    """Corre todos los (w, solver, corrida) del plan; con `imprimir`, una línea por (w, solver)."""
    corridas = Corridas(costos={}, hallazgos={}, historiales={})
    for i_w, w in enumerate(plan.w):
        C = _matriz(plan, w)
        corridas.costos[w] = {}
        for s in plan.solvers:
            cfg_s = _cfg_solver(plan.cfg, s)
            iniciales, por_iter = _conteo(cfg_s, s)
            registros = []
            for r in range(plan.runs):
                rid = run_id(i_w, s, r, plan.runs)
                res = SOLVE[s](C, cfg_s, make_rng(plan.base_seed, rid))
                tour = canonico(res["tour"])
                costo = float(recorridos.costos_recorridos(C, np.array([tour]))[0])
                _verificar(costo, res["cost"], f"costo del recorrido canónico (w = {w}, {s}, run_id {rid})")
                corridas.costos[w].setdefault(s, []).append(costo)
                corridas.hallazgos.setdefault(tour, []).append({"w": w, "metodo": s, "run_id": rid})
                registros.append(_registro_corrida(res, rid, plan.base_seed + rid, iniciales, por_iter))
            familia = FAMILIA[s]
            hist = corridas.historiales.setdefault((w, familia), {"w": w, "metodo": familia, "variantes": {}})
            hist["variantes"][s] = {"parametros": cfg_s[familia], "corridas": registros}
            est = corridas.costos[w][s]
            if imprimir:
                print(f"  w = {_texto_num(w):>5} €/h  {s:<4}  mejor {min(est):10.2f} €  "
                      f"media {np.mean(est):10.2f} €")
    return corridas


def _fila_sweep(w: float, tour: tuple[int, ...], mejor: float, candidato: int, costos: dict[str, list[float]],
                d: dict, anterior: tuple[int, ...] | None) -> dict:
    """Fila de `sweep_w.json` (§5.4) para un w: el mejor encontrado (`tour`, `mejor`, desglose `d`) y, por solver,
    las estadísticas de `costos`. `gap_aco` y `gap_ga` son el gap de la MEDIA de MMAS y del GA (None si no
    corrieron)."""
    metodos = {s: estadisticas(c, mejor) for s, c in costos.items()}
    return {
        "w": w, "tour": list(tour), "cost": mejor,
        "desglose": {"tiempo": d["tiempo"], "peajes": d["peajes"], "combustible": d["combustible"]},
        "km_peaje": d["km_peaje"],
        "cambio_vs_anterior": None if anterior is None else tour != anterior,
        "gap_aco": metodos[SOLVER_GAP_ACO]["gap_media"] if SOLVER_GAP_ACO in metodos else None,
        "gap_ga": metodos[SOLVER_GAP_GA]["gap_media"] if SOLVER_GAP_GA in metodos else None,
        "candidato": candidato, "metodos": metodos,
    }


def _filas_sweep(plan: Plan, costos: dict, env: dict, rect: Rectas) -> list[dict]:
    """Filas de `sweep_w.json`: en cada w el mejor de TODOS los candidatos, con comprobaciones de consistencia."""
    tours = np.array(env["candidatos"], dtype=np.intp)
    filas, anterior = [], None
    for w in plan.w:
        costos_cand = recorridos.costos_recorridos(_matriz(plan, w), tours)
        k = int(np.argmin(costos_cand))
        mejor = float(costos_cand[k])
        # Consistencia: la envolvente da el mismo mínimo y no supera a ninguna corrida de este w.
        _verificar(costo_envolvente(env, rect, w), mejor, f"envolvente frente a evaluación directa en w = {w}")
        if mejor > min(min(c) for c in costos[w].values()) * (1 + TOL_REL):
            raise RuntimeError(f"el mejor encontrado en w = {w} supera a una corrida de ese w")
        tour = env["candidatos"][k]
        d = desglose(plan.datos, tour, w, plan.consumo_l100, plan.precio_l)
        filas.append(_fila_sweep(w, tour, mejor, k, costos[w], d, anterior))
        anterior = tour
    return filas


def _json_umbrales(plan: Plan, env: dict, hallazgos: dict) -> dict:
    """Contenido de `umbrales_w.json`: candidatos (con dónde se hallaron), intervalos y umbrales de la envolvente."""
    return {
        "nota": NOTA_UMBRAL, "rango_w": [plan.w[0], plan.w[-1]],
        "consumo_l100": plan.consumo_l100, "precio_l": plan.precio_l,
        "candidatos": [{"id": k, "tour": list(t), "hallado_en": hallazgos[t]} for k, t in enumerate(env["candidatos"])],
        "intervalos": env["intervalos"], "umbrales": env["umbrales"],
        "semillas": {"regla": REGLA_SEMILLAS, "base_seed": plan.base_seed, "solvers": list(SOLVERS)},
        "config": plan.cfg,
    }


def correr(plan: Plan) -> Path:
    """Ejecuta el plan y escribe las salidas en `plan.salida`; devuelve esa carpeta."""
    if plan.referencia is not None:
        return _correr_demo(plan)
    corridas = _correr_solvers(plan)
    hallazgos = corridas.hallazgos
    if plan.base is not None:  # sensibilidad: unión con los candidatos del barrido base (§7.5)
        for c in plan.base["umbrales"]["candidatos"]:
            hallazgos.setdefault(tuple(c["tour"]), []).extend({**h, "origen": "base"} for h in c["hallado_en"])

    rect = rectas(plan.datos.comp, plan.consumo_l100, plan.precio_l)
    env = envolvente(rect, list(hallazgos), plan.w[0], plan.w[-1])
    sweep = _filas_sweep(plan, corridas.costos, env, rect)
    umbrales = _json_umbrales(plan, env, hallazgos)

    save_json(plan.salida / ARCHIVO_SWEEP, sweep)
    save_json(plan.salida / ARCHIVO_UMBRALES, umbrales)
    for (w, familia), hist in corridas.historiales.items():
        save_json(plan.salida / f"history_{familia}_w{_texto_num(w)}.json", hist, sangria=SANGRIA_HISTORIALES)
    if plan.base is not None:
        save_json(plan.salida / ARCHIVO_COMPARACION, _comparacion(plan, sweep, umbrales))
    _imprimir_resumen(sweep, umbrales, plan.salida)
    return plan.salida


def _comparacion(plan: Plan, sweep: list[dict], umbrales: dict) -> dict:
    """Sensibilidad frente a la base (§7.5): costo total y de combustible por w, recorrido y umbrales."""
    base_sweep = {e["w"]: e for e in plan.base["sweep"]}
    base_umb = plan.base["umbrales"]

    def resumen(e):
        return {"cost": e["cost"], "combustible": e["desglose"]["combustible"], "tour": e["tour"]}

    def ganadores(u):
        return [u["candidatos"][s["candidato"]]["tour"] for s in u["intervalos"]]

    por_w = []
    for e in sweep:
        b = base_sweep.get(e["w"])
        por_w.append({
            "w": e["w"], "base": None if b is None else resumen(b), "sensibilidad": resumen(e),
            "mismo_recorrido": None if b is None else b["tour"] == e["tour"],
        })
    return {
        "consumo_l100": {"base": base_umb["consumo_l100"], "sensibilidad": plan.consumo_l100},
        "precio_l": {"base": base_umb["precio_l"], "sensibilidad": plan.precio_l},
        "por_w": por_w,
        "umbrales": {
            "base": [u["w"] for u in base_umb["umbrales"]],
            "sensibilidad": [u["w"] for u in umbrales["umbrales"]],
            "mismos_ganadores": ganadores(base_umb) == ganadores(umbrales),
        },
        "nota": NOTA_UMBRAL,
    }


def _imprimir_resumen(sweep: list[dict], umbrales: dict, salida: Path) -> None:
    print("Mejor encontrado por w:")
    for e in sweep:
        print(f"  w = {_texto_num(e['w']):>5} €/h  {e['cost']:10.2f} €  candidato {e['candidato']}")
    lista = ", ".join(f"{u['w']:.6g}" for u in umbrales["umbrales"]) or "ninguno"
    print(f"Umbrales (entre las mejores rutas encontradas): {lista}")
    print(f"Resultados en {salida}")


def _correr_demo(plan: Plan) -> Path:
    """Demo (§7.7): corre los solvers en el único w, guarda `demo.json` y la figura del mejor recorrido y resume en
    consola costo, desglose, gap frente al mejor conocido, recorridos evaluados y tiempo. Solo escribe en
    `plan.salida`."""
    inicio = time.perf_counter()
    res, con_peaje = _resumen_demo(plan, _correr_solvers(plan, imprimir=False))
    lon, lat = plan.coordenadas
    figura_recorrido(
        lon, lat, res["tour"], con_peaje,
        titulo=f"Mejor recorrido de la demo ({_nombres_solvers(res['solvers'])}, w = {_texto_num(res['w'])} €/h)",
        subtitulo=f"{res['cost']:.2f} € · gap frente al mejor conocido {res['gap_mejor_conocido']:+.2f} %",
        ruta=plan.salida / res["figura"],
    )
    save_json(plan.salida / ARCHIVO_DEMO, res)
    _imprimir_demo(res, plan.salida, time.perf_counter() - inicio)
    return plan.salida


def _resumen_demo(plan: Plan, corridas: Corridas) -> tuple[dict, np.ndarray]:
    """Contenido de `demo.json` (§5.4) a partir de las corridas; calcula, no escribe. Devuelve también qué arcos del
    mejor recorrido pagan peaje (los marca la figura)."""
    (w,) = plan.w
    referencia = plan.referencia
    # Las claves de `hallazgos` son los recorridos canónicos de todas las corridas, cada uno una sola vez.
    tours = list(corridas.hallazgos)
    costos = recorridos.costos_recorridos(_matriz(plan, w), np.array(tours, dtype=np.intp))
    i_mejor = int(np.argmin(costos))
    tour, mejor = tours[i_mejor], float(costos[i_mejor])
    por_arco = arcos(plan.datos, tour, w, plan.consumo_l100, plan.precio_l)
    totales = {clave: float(x.sum()) for clave, x in por_arco.items()}
    con_peaje = por_arco["peajes"] > 0
    n_evals = 0
    for hist in corridas.historiales.values():
        for variante in hist["variantes"].values():
            for corrida in variante["corridas"]:
                n_evals += corrida["n_tour_evals"]
    res = {
        "w": w, "solvers": list(plan.solvers), "tour": list(tour), "cost": mejor,
        "desglose": {"tiempo": totales["tiempo"], "peajes": totales["peajes"],
                     "combustible": totales["combustible"]},
        "km_peaje": totales["km_peaje"], "arcos_con_peaje": int(con_peaje.sum()),
        "referencia": referencia, "gap_mejor_conocido": gap(mejor, referencia["cost"]),
        "metodos": {s: estadisticas(c, referencia["cost"]) for s, c in corridas.costos[w].items()},
        "n_tour_evals": n_evals, "figura": FIGURA_DEMO.format(w=_texto_num(w)), "nota": NOTA_DEMO,
        "semillas": {"regla": REGLA_SEMILLAS, "base_seed": plan.base_seed, "solvers": list(SOLVERS)},
        "config": plan.cfg,
    }
    return res, con_peaje


def _nombres_solvers(solvers: list[str]) -> str:
    """Nombres legibles de los solvers, p. ej. "MMAS + GA"."""
    return " + ".join(NOMBRE_SOLVER[s] for s in solvers)


def _imprimir_demo(res: dict, salida: Path, segundos: float) -> None:
    """Resumen en consola de la demo, leído del mismo dict que se guarda en `demo.json`."""
    desglose, referencia = res["desglose"], res["referencia"]
    print(f"Demo Parte 2: {_nombres_solvers(res['solvers'])}, w = {_texto_num(res['w'])} €/h, "
          f"{res['config']['runs']} corrida(s)")
    print(f"  Mejor recorrido:      {res['cost']:10.2f} €")
    print(f"    Tiempo:             {desglose['tiempo']:10.2f} €")
    print(f"    Peajes:             {desglose['peajes']:10.2f} €  ({res['arcos_con_peaje']} tramos con peaje, "
          f"{res['km_peaje']:.1f} km)")
    print(f"    Combustible:        {desglose['combustible']:10.2f} €")
    print(f"  Mejor conocido:       {referencia['cost']:10.2f} €  ({referencia['archivo']}, barrido T3.6)")
    for s, m in res["metodos"].items():
        print(f"  Gap frente al mejor conocido ({NOMBRE_SOLVER[s]}): mejor corrida {m['gap_mejor']:+.2f} %, "
              f"media de {m['n']} corridas {m['gap_media']:+.2f} %")
    print(f"  Recorridos evaluados: {_miles(res['n_tour_evals'])}")
    print(f"  Tiempo de ejecución:  {segundos:.1f} s (corridas y figura)")
    print(f"  Figura:               {_ruta_legible(salida / res['figura'])}")


def ejecutar(cfg: dict) -> Path:
    """`preparar` + `correr`."""
    return correr(preparar(cfg))


def main(cfg: dict | None) -> int:
    """Manejador de `run.py part2` (Spec §4.1): valida antes de correr; error de config → código 2."""
    try:
        plan = preparar(cfg)
    except (ValueError, TypeError, KeyError, FileNotFoundError) as exc:
        print(f"Error en la configuración de part2: {exc}", file=sys.stderr)
        return 2
    correr(plan)
    return 0
