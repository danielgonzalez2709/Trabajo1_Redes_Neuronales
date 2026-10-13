"""Colonia de hormigas para el TSP: Ant System (AS) y MAX–MIN Ant System (MMAS) (Spec §5.2, §7.4 y §7.4.1).

Fuentes:
  - Fórmulas (fuente principal, Spec §7.4.1): notas del profesor, Ospina y Zapata (2026-01),
    `data/raw/ACO/notas_aco.html`. De ellas sale todo el algoritmo:
      · regla de transición p_ij ∝ τ_ij^α · η_ij^β con η_ij = 1/c_ij y selección por ruleta (§4.1);
      · C^nn = costo del vecino más cercano (Def. 8);
      · AS: τ₀ = m/C^nn, evaporación en todos los arcos y depósito Δτ = 1/L_k de las m hormigas, simétrico (§4.2);
      · MMAS: una sola hormiga deposita, τ ← [(1−ρ)τ + Δτ^best] recortada a [τ_min, τ_max], inicio en τ_max (§6);
        τ_max = 1/(ρ L^bs) (§6.1 y corolario de la Prop. 1); τ_min con p_best y ā = n/2 (§7.2, Prop. 2).
  - Estructura (sin copiar código): Berroa, J., *AntColonyOptimizer.py*,
    https://github.com/johnberroa/Ant-Colony-Optimization (sin licencia; consultado el 12-oct-2026). Solo se toman
    dos ideas: calcular τ^α·η^β una vez por iteración (τ cambia solo al final de la iteración) y cerrar el recorrido
    al volver a la ciudad de partida. Su algoritmo (depósito fijo, τ₀ = 1, arcos dirigidos, regla tipo ACS) no es el
    de este módulo.

Una iteración t (t = 0, 1, …):
  1. W = τ^α · η^β (una vez).
  2. Las m hormigas construyen su recorrido a la vez (vectorizado por hormiga, un paso por ciudad).
  3. Se actualiza la mejor global T^bs (y, en MMAS, τ_max y τ_min si mejoró).
  4. Se actualiza la feromona: AS deposita las m hormigas; MMAS deposita T^ib si t es par y T^bs si t es impar
     (§7.4.1).

Conteo (§7.4.1): n_tour_evals = 1 + m · iteraciones (el recorrido del vecino más cercano + los de las hormigas).

Puntos fijados por el Spec §7.4.1 [DECIDIDO v1.14, Jose Miguel, 12-oct]:
  - Recorrido inicial: T^bs empieza en el recorrido del vecino más cercano (ambas variantes; "al inicio L^bs = C^nn").
    Si ninguna hormiga lo mejora, `solve` devuelve ese recorrido. Empates: T^ib es la primera hormiga de costo mínimo
    y T^bs cambia solo con mejora estricta.
  - Orden dentro de cada iteración: construir → evaluar → actualizar T^ib, T^bs y (en MMAS) τ_max/τ_min → evaporar y
    depositar. En t impar deposita la mejor global incluida la iteración actual, y tras cada actualización
    τ ∈ [τ_min, τ_max]. (El esqueleto de las notas, §3, actualiza s^bs después; §7.4.1 explica por qué aquí va antes.)
  - Si la Prop. 2 da τ_min ≥ τ_max (con p_best = 0.05 ocurre para n ≤ 4), MMAS lanza `ValueError`.

Decisiones de implementación (no fijadas por el Spec):
  - `history[k]["iter"]` = t, desde 0 (como en las notas y en la regla de alternancia).
  - C debe ser exactamente simétrica (la feromona y el costo del recorrido no dependen del sentido).
"""

from __future__ import annotations

import numpy as np

from src.common.seeds import validar_entero
from src.part2.recorridos import costos_recorridos as _costos
from src.part2.recorridos import N_MINIMO  # noqa: F401  (superficie pública de T3.3)
from src.part2.recorridos import leer_clave, validar_generador
from src.part2.recorridos import validar_matriz as _validar_matriz
from src.part2.recorridos import validar_real as _real
from src.part2.recorridos import vecino_mas_cercano as _vecino_mas_cercano

VARIANTES = ("mmas", "as")  # Spec §7.4.1: MMAS principal, AS comparación


# ---------------------------------------------------------------------------------------- validación
# Validación de C, costo de recorridos, vecino más cercano y `_real` viven en `recorridos.py` (compartidos con
# `ga.py`, Spec §7.4.2); se importan con sus nombres de T3.3 para no cambiar el comportamiento ni las pruebas.


def _clave(bloque: dict, clave: str, ruta: str):
    return leer_clave(bloque, clave, ruta, "§7.4.1")


def _leer_parametros(cfg: dict) -> dict:
    """Parámetros validados de `cfg["aco"]` (todo el bloque, aunque una variante no use el ρ de la otra)."""
    bloque = _clave(cfg, "aco", "aco")
    variante = _clave(bloque, "variante", "aco.variante")
    if variante not in VARIANTES:
        raise ValueError(f"aco.variante debe ser una de {VARIANTES}; se recibió {variante!r}")
    sub_as = _clave(bloque, "as", "aco.as")
    sub_mmas = _clave(bloque, "mmas", "aco.mmas")
    return {
        "variante": variante,
        "hormigas": validar_entero(_clave(bloque, "hormigas", "aco.hormigas"), "aco.hormigas", minimo=1),
        "iteraciones": validar_entero(_clave(bloque, "iteraciones", "aco.iteraciones"), "aco.iteraciones", minimo=1),
        "alpha": _real(_clave(bloque, "alpha", "aco.alpha"), "aco.alpha", 0.0),
        "beta": _real(_clave(bloque, "beta", "aco.beta"), "aco.beta", 0.0),
        # 0 < ρ ≤ 1 (notas §4.2); 0 < p_best < 1 (notas Prop. 2)
        "rho_as": _real(_clave(sub_as, "rho", "aco.as.rho"), "aco.as.rho", 0.0, 1.0, min_abierto=True),
        "rho_mmas": _real(_clave(sub_mmas, "rho", "aco.mmas.rho"), "aco.mmas.rho", 0.0, 1.0, min_abierto=True),
        "p_best": _real(
            _clave(sub_mmas, "p_best", "aco.mmas.p_best"),
            "aco.mmas.p_best",
            0.0,
            1.0,
            min_abierto=True,
            max_abierto=True,
        ),
    }


# ----------------------------------------------------------------------------------- piezas del algoritmo


def _limites_mmas(L_bs: float, rho: float, n: int, p_best: float) -> tuple[float, float]:
    """(τ_min, τ_max) de MMAS: τ_max = 1/(ρ L^bs) (notas §6.1) y la Prop. 2 de las notas (§7.2) con ā = n/2:

    τ_min = τ_max · (1 − p_best^(1/n)) / ((ā − 1) · p_best^(1/n)).
    """
    tau_max = 1.0 / (rho * L_bs)
    raiz = p_best ** (1.0 / n)
    a_barra = n / 2
    tau_min = tau_max * (1.0 - raiz) / ((a_barra - 1.0) * raiz)
    if not tau_min < tau_max:
        raise ValueError(
            f"MMAS: la Prop. 2 da τ_min = {tau_min:.6g} ≥ τ_max = {tau_max:.6g} con n = {n} y p_best = {p_best}; "
            "las notas no definen este caso (usa más ciudades, otro p_best o la variante 'as')"
        )
    return tau_min, tau_max


def _pesos(tau: np.ndarray, eta_beta: np.ndarray, alpha: float) -> np.ndarray:
    """W_ij = τ_ij^α · η_ij^β (notas §4.1). Se calcula una vez por iteración."""
    return tau**alpha * eta_beta


def _ruleta(pesos: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Una elección por fila de `pesos` (k × n), con probabilidad pesos_j / Σ_l pesos_l (ruleta, notas §4.1).

    Se sortea u ~ U[0, total) y se toma la primera columna cuya suma acumulada supera u; las columnas de peso 0
    nunca se eligen. Si el redondeo diera u == total, se toma la última columna con peso positivo (nunca una
    ciudad visitada).
    """
    acumulado = np.cumsum(pesos, axis=1)
    total = acumulado[:, -1]
    if not (np.isfinite(total) & (total > 0)).all():
        raise FloatingPointError(
            "ruleta sin pesos válidos (τ^α·η^β dio 0, inf o NaN en todas las ciudades no visitadas); "
            "revisa la escala de C o los valores de α, β e iteraciones"
        )
    u = rng.random(pesos.shape[0]) * total
    elegido = (acumulado <= u[:, None]).sum(axis=1)  # índice de la primera suma acumulada > u
    n = pesos.shape[1]
    ultimo_positivo = n - 1 - np.argmax(pesos[:, ::-1] > 0, axis=1)
    return np.where(elegido < n, elegido, ultimo_positivo)


def _construir_recorridos(W: np.ndarray, m: int, rng: np.random.Generator) -> np.ndarray:
    """Recorridos (m × n) de las m hormigas a la vez.

    Cada hormiga arranca en una ciudad uniforme al azar y, en cada paso, elige la siguiente entre las no visitadas
    por ruleta sobre la fila de W de su ciudad actual; las visitadas tienen peso 0.
    """
    n = W.shape[0]
    hormigas = np.arange(m)
    tours = np.empty((m, n), dtype=np.intp)
    actual = rng.integers(n, size=m)
    tours[:, 0] = actual
    disponible = np.ones((m, n), dtype=bool)
    disponible[hormigas, actual] = False
    for paso in range(1, n):
        actual = _ruleta(W[actual] * disponible, rng)
        tours[:, paso] = actual
        disponible[hormigas, actual] = False
    return tours


def _deposito(n: int, tours: np.ndarray, costos: np.ndarray) -> np.ndarray:
    """Δτ simétrica: cada recorrido k suma 1/L_k (Q = 1) en τ_ij y τ_ji de cada arco suyo, con el de cierre."""
    desde = tours.ravel()
    hacia = np.roll(tours, -1, axis=1).ravel()
    delta = np.zeros((n, n))
    np.add.at(delta, (desde, hacia), np.repeat(1.0 / costos, n))
    return delta + delta.T  # en un recorrido cada arco no dirigido aparece una sola vez (n ≥ 3)


def _actualizar_as(tau: np.ndarray, tours: np.ndarray, costos: np.ndarray, rho: float) -> np.ndarray:
    """AS (notas §4.2): τ ← (1 − ρ)τ + Σ_k Δτ^k, con las m hormigas. Devuelve una matriz nueva."""
    return (1.0 - rho) * tau + _deposito(tau.shape[0], tours, costos)


def _actualizar_mmas(
    tau: np.ndarray, tour: np.ndarray, costo: float, rho: float, tau_min: float, tau_max: float
) -> np.ndarray:
    """MMAS (notas §6): τ ← [(1 − ρ)τ + Δτ^best] recortada a [τ_min, τ_max]. Devuelve una matriz nueva."""
    delta = _deposito(tau.shape[0], tour[None, :], np.array([costo]))
    return np.clip((1.0 - rho) * tau + delta, tau_min, tau_max)


def iterar(C: np.ndarray, cfg: dict, rng: np.random.Generator):
    """Generador de estados de ACO, uno por iteración t, después de actualizar la feromona (Spec §7.4.1).

    Valida C, `cfg["aco"]` y `rng` en la llamada (no al pedir el primer estado). Cada estado es un dict con:
      - "t": int, la iteración (desde 0);
      - "W": matriz n × n de pesos τ^α·η^β con la que se construyeron los recorridos de esta iteración;
      - "tours": recorridos de las m hormigas (m × n) y "costos": su costo con el arco de cierre (m);
      - "tau": feromona n × n después de la actualización (matriz nueva en cada iteración);
      - "tau_min", "tau_max": límites con que se recortó en MMAS (None en AS);
      - "best_tour", "best_cost": mejor global hasta t, incluido el vecino más cercano.
    `solve` consume este generador; las pruebas lo usan para revisar cada actualización.
    """
    params = _leer_parametros(cfg)
    C = _validar_matriz(C)
    validar_generador(rng)
    vecino = _vecino_mas_cercano(C)  # T^bs inicial: L^bs = C^nn (Spec §7.4.1)
    if params["variante"] == "mmas":
        _limites_mmas(vecino[1], params["rho_mmas"], C.shape[0], params["p_best"])  # τ_min ≥ τ_max → ValueError aquí
    return _generar(C, params, rng, vecino)


def _generar(C: np.ndarray, params: dict, rng: np.random.Generator, vecino: tuple[np.ndarray, float]):
    """Cuerpo de `iterar` (C, params y rng ya validados; `vecino` = recorrido del vecino más cercano y C^nn)."""
    n = C.shape[0]
    m = params["hormigas"]
    alpha = params["alpha"]
    p_best = params["p_best"]
    es_mmas = params["variante"] == "mmas"

    fuera_diagonal = ~np.eye(n, dtype=bool)
    eta = np.zeros_like(C)
    eta[fuera_diagonal] = 1.0 / C[fuera_diagonal]
    eta_beta = eta ** params["beta"]  # no cambia entre iteraciones

    best_tour, best_cost = vecino
    if es_mmas:
        rho = params["rho_mmas"]
        tau_min, tau_max = _limites_mmas(best_cost, rho, n, p_best)
        tau = np.full((n, n), tau_max)  # inicialización en τ_max (notas §6)
    else:
        rho = params["rho_as"]
        tau_min = tau_max = None
        tau = np.full((n, n), m / best_cost)  # τ₀ = m/C^nn (notas §4.2)

    for t in range(params["iteraciones"]):
        W = _pesos(tau, eta_beta, alpha)
        tours = _construir_recorridos(W, m, rng)
        costos = _costos(C, tours)
        # Orden de §7.4.1: T^ib, T^bs y límites antes de evaporar y depositar.
        k_ib = int(np.argmin(costos))
        ib_tour, ib_cost = tours[k_ib], float(costos[k_ib])
        mejora = ib_cost < best_cost
        if mejora:
            best_tour, best_cost = ib_tour.copy(), ib_cost
        if es_mmas:
            if mejora:
                tau_min, tau_max = _limites_mmas(best_cost, rho, n, p_best)
            dep_tour, dep_cost = (ib_tour, ib_cost) if t % 2 == 0 else (best_tour, best_cost)
            tau = _actualizar_mmas(tau, dep_tour, dep_cost, rho, tau_min, tau_max)
        else:
            tau = _actualizar_as(tau, tours, costos, rho)
        yield {
            "t": t,
            "W": W,
            "tours": tours,
            "costos": costos,
            "tau": tau,
            "tau_min": tau_min,
            "tau_max": tau_max,
            "best_tour": best_tour,
            "best_cost": best_cost,
        }


# ------------------------------------------------------------------------------------------- contrato


def solve(C: np.ndarray, cfg: dict, rng: np.random.Generator) -> dict:
    """Resuelve el TSP simétrico de costos C con AS o MMAS según `cfg["aco"]` (Spec §5.2 y §7.4.1).

    Retorna {"tour", "cost", "n_tour_evals", "history"}: `tour` es la mejor permutación encontrada (el ciclo se
    cierra implícitamente), `cost` su costo con el arco de cierre, `n_tour_evals` = 1 + m · iteraciones y `history`
    una entrada por iteración con el mejor global hasta ella.
    """
    history = []
    n_tour_evals = 1  # recorrido del vecino más cercano (C^nn)
    for estado in iterar(C, cfg, rng):
        n_tour_evals += len(estado["costos"])
        history.append(
            {"iter": estado["t"], "best_cost": estado["best_cost"], "best_tour": estado["best_tour"].tolist()}
        )
    return {
        "tour": list(history[-1]["best_tour"]),
        "cost": history[-1]["best_cost"],
        "n_tour_evals": n_tour_evals,
        "history": history,
    }
