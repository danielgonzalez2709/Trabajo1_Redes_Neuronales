"""Algoritmo genético para el TSP: torneo + OX + inversión/intercambio + elitismo (Spec §5.2, §7.4 y §7.4.2).

Fuentes:
  - Esquema (Spec §7.4.2 [DECIDIDO v1.15, Jose Miguel, 12-oct]): el clásico de la tabla de §7.4. Individuo =
    permutación de 0..n-1; aptitud = costo del recorrido cerrado sobre la misma matriz C que ACO (se minimiza tal
    cual: torneo y elitismo solo comparan costos).
  - Referencia general (sin copiar código): notebooks del profesor, Ospina y Zapata (2026),
    `data/raw/GA/IRNA202601_prep_Algoritmos_Evolutivos.ipynb` e `IRNA202602_intro_algoritmos_evolutivos.ipynb`.
    Solo se toma el ciclo evaluar → ordenar → élites → cruce → mutación. No se toman:
      · su esquema por fracciones (fracción de élites, de mutantes y de cruce, con padres al azar y sin torneo):
        sin torneo la única presión de selección sería el elitismo;
      · su cruce de un punto y su mutación por coordenada, pensados para codificación real: sobre una permutación
        repiten y pierden ciudades. Por eso aquí se usan OX, inversión e intercambio, que conservan la permutación.

Una generación g (g = 0, 1, …, generaciones − 1), a partir de la población anterior y sus costos:
  1. Élites: los `elites` individuos de menor costo pasan sin cambios (empates: primer índice).
  2. Hasta completar `poblacion − elites` hijos: dos torneos eligen P1 y P2; con probabilidad `pc` nacen
     OX(P1, P2) y OX(P2, P1), y si no, copias de P1 y P2. Si solo falta un hijo, el segundo no se genera.
  3. Mutación: cada hijo, con probabilidad `pm`, recibe un solo operador, inversión o intercambio (50/50).
  4. Se evalúan los hijos (todos a la vez) y se actualiza el mejor global (solo con mejora estricta).

Población inicial (§7.4.2): el recorrido del vecino más cercano desde la ciudad 0 (el mismo C^nn de ACO, §7.4.1) +
`poblacion − 1` permutaciones uniformes al azar.

Conteo (§7.4.2): n_tour_evals = poblacion + (poblacion − elites) · generaciones. Cada hijo cuenta 1 aunque sea una
copia; los élites no se vuelven a evaluar.

Decisiones de implementación (no fijadas por el Spec, reportadas al orquestador):
  - `history[k]["iter"]` = g: la generación 0 es la primera generada; la población inicial no tiene entrada propia
    (su mejor individuo entra como punto de partida del mejor global). Así `history` tiene `generaciones` entradas,
    como ACO tiene `iteraciones`.
  - OX(P1, P2) y OX(P2, P1) sortean cada uno sus propios cortes a < b (§7.4.2 define el sorteo dentro de OX).
  - Los dos torneos son independientes: P1 y P2 pueden ser el mismo individuo.
  - Los élites ocupan las primeras filas de la nueva población; luego van los hijos en el orden en que nacen.
  - Sorteo 50/50 de la mutación: u < 0.5 → inversión; si no, intercambio.
"""

from __future__ import annotations

import numpy as np

from src.common.seeds import validar_entero
from src.part2.recorridos import costos_recorridos as _costos_recorridos
from src.part2.recorridos import leer_clave as _leer_clave
from src.part2.recorridos import validar_generador as _validar_generador
from src.part2.recorridos import validar_matriz as _validar_matriz
from src.part2.recorridos import validar_real as _validar_real
from src.part2.recorridos import vecino_mas_cercano as _vecino_mas_cercano

__all__ = ["solve", "iterar"]  # Spec §5.2 y §7.4.2: el resto del módulo es privado

_SECCION = "§7.4.2"
_PROB_INVERSION = 0.5  # Spec §7.4.2: inversión o intercambio, elegido 50/50


# ---------------------------------------------------------------------------------------- validación


def _leer_parametros(cfg: dict) -> dict:
    """Parámetros validados de `cfg["ga"]` (rangos de §7.4.2)."""
    bloque = _leer_clave(cfg, "ga", "ga", _SECCION)

    def clave(nombre):
        return _leer_clave(bloque, nombre, f"ga.{nombre}", _SECCION)

    poblacion = validar_entero(clave("poblacion"), "ga.poblacion", minimo=2)
    generaciones = validar_entero(clave("generaciones"), "ga.generaciones", minimo=1)
    torneo_k = validar_entero(clave("torneo_k"), "ga.torneo_k", minimo=1)
    if torneo_k > poblacion:
        raise ValueError(f"ga.torneo_k debe estar en [1, poblacion = {poblacion}]; se recibió {torneo_k}")
    elites = validar_entero(clave("elites"), "ga.elites", minimo=0)
    if elites >= poblacion:
        raise ValueError(f"ga.elites debe ser < poblacion = {poblacion}; se recibió {elites}")
    return {
        "poblacion": poblacion,
        "generaciones": generaciones,
        "torneo_k": torneo_k,
        "elites": elites,
        "pc": _validar_real(clave("pc"), "ga.pc", 0.0, 1.0),
        "pm": _validar_real(clave("pm"), "ga.pm", 0.0, 1.0),
    }


# ------------------------------------------------------------------------------------------ operadores
# Todos devuelven un arreglo nuevo: nunca modifican a los padres.


def _dos_posiciones(n: int, rng: np.random.Generator) -> tuple[int, int]:
    """Dos posiciones distintas a < b de 0..n-1, uniformes entre los n(n−1)/2 pares (las usan OX e inversión)."""
    a, b = sorted(rng.choice(n, size=2, replace=False).tolist())
    return a, b


def _ox_tramo(p1: np.ndarray, p2: np.ndarray, a: int, b: int) -> np.ndarray:
    """OX con cortes fijos (§7.4.2): el hijo copia P1[a..b] en las mismas posiciones y llena las libres, de
    izquierda a derecha, con las ciudades que faltan en el orden en que aparecen en P2."""
    n = len(p1)
    hijo = np.empty(n, dtype=p1.dtype)
    hijo[a : b + 1] = p1[a : b + 1]
    en_tramo = np.zeros(n, dtype=bool)
    en_tramo[p1[a : b + 1]] = True
    faltan = p2[~en_tramo[p2]]  # ciudades de P2 fuera del tramo, en su orden
    libres = np.r_[0:a, b + 1 : n]  # posiciones libres, de izquierda a derecha
    hijo[libres] = faltan
    return hijo


def _ox(p1: np.ndarray, p2: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """OX(P1, P2) con cortes a < b al azar."""
    a, b = _dos_posiciones(len(p1), rng)
    return _ox_tramo(p1, p2, a, b)


def _invertir_tramo(tour: np.ndarray, i: int, j: int) -> np.ndarray:
    """Invierte el tramo [i..j] (inclusive)."""
    hijo = tour.copy()
    hijo[i : j + 1] = tour[i : j + 1][::-1]
    return hijo


def _invertir(tour: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Inversión (§7.4.2): dos posiciones distintas i < j al azar; invierte el tramo [i..j]."""
    i, j = _dos_posiciones(len(tour), rng)
    return _invertir_tramo(tour, i, j)


def _intercambiar_posiciones(tour: np.ndarray, i: int, j: int) -> np.ndarray:
    """Intercambia las ciudades de las posiciones i y j."""
    hijo = tour.copy()
    hijo[i], hijo[j] = tour[j], tour[i]
    return hijo


def _intercambiar(tour: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Intercambio (§7.4.2): dos posiciones distintas al azar; intercambia sus ciudades."""
    i, j = _dos_posiciones(len(tour), rng)
    return _intercambiar_posiciones(tour, i, j)


def _mutar(tour: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, str]:
    """Un solo operador, inversión o intercambio, elegido 50/50 (§7.4.2). Devuelve (hijo, nombre del operador)."""
    if rng.random() < _PROB_INVERSION:
        return _invertir(tour, rng), "inversion"
    return _intercambiar(tour, rng), "intercambio"


def _torneo(costos: np.ndarray, k: int, rng: np.random.Generator) -> int:
    """Índice del ganador de un torneo: k individuos distintos al azar, gana el de menor costo (empates: el primero
    del sorteo)."""
    sorteados = rng.choice(len(costos), size=k, replace=False)
    return int(sorteados[np.argmin(costos[sorteados])])


# ---------------------------------------------------------------------------------------- generaciones


def _poblacion_inicial(C: np.ndarray, poblacion: int, rng: np.random.Generator) -> np.ndarray:
    """Matriz poblacion × n: fila 0 = vecino más cercano desde la ciudad 0; el resto, permutaciones uniformes."""
    n = C.shape[0]
    tour_nn, _ = _vecino_mas_cercano(C)
    filas = [tour_nn] + [rng.permutation(n) for _ in range(poblacion - 1)]
    return np.array(filas, dtype=np.intp)


def _hijos(poblacion: np.ndarray, costos: np.ndarray, cantidad: int, params: dict,
           rng: np.random.Generator) -> np.ndarray:
    """`cantidad` hijos (cantidad × n): selección por torneo, cruce OX con probabilidad pc y mutación con pm."""
    hijos = []
    while len(hijos) < cantidad:
        p1 = poblacion[_torneo(costos, params["torneo_k"], rng)]
        p2 = poblacion[_torneo(costos, params["torneo_k"], rng)]
        dos = cantidad - len(hijos) >= 2  # si solo falta uno, el segundo no se genera
        if rng.random() < params["pc"]:
            nuevos = [_ox(p1, p2, rng)] + ([_ox(p2, p1, rng)] if dos else [])
        else:
            nuevos = [p1.copy()] + ([p2.copy()] if dos else [])
        for hijo in nuevos:
            if rng.random() < params["pm"]:
                hijo, _ = _mutar(hijo, rng)
            hijos.append(hijo)
    return np.array(hijos, dtype=np.intp)


def iterar(C: np.ndarray, cfg: dict, rng: np.random.Generator):
    """Generador de estados del GA, uno por generación g, después de evaluar a los hijos (Spec §7.4.2).

    Valida C, `cfg["ga"]` y `rng` en la llamada (no al pedir el primer estado). Cada estado es un dict con:
      - "g": int, la generación (desde 0; la población inicial no tiene estado propio);
      - "poblacion": matriz poblacion × n (élites en las primeras filas, luego los hijos);
      - "costos": costo de cada fila con el arco de cierre;
      - "n_tour_evals": recorridos evaluados hasta g, incluida la población inicial (§7.4.2);
      - "best_tour", "best_cost": mejor global hasta g, incluida la población inicial.
    Los arreglos de cada estado son copias: modificarlos no afecta a las generaciones siguientes.
    `solve` consume este generador; las pruebas lo usan para revisar cada generación.
    """
    params = _leer_parametros(cfg)
    C = _validar_matriz(C)
    _validar_generador(rng)
    return _generar(C, params, rng)


def _generar(C: np.ndarray, params: dict, rng: np.random.Generator):
    """Cuerpo de `iterar` (C, params y rng ya validados)."""
    elites = params["elites"]
    n_hijos = params["poblacion"] - elites

    poblacion = _poblacion_inicial(C, params["poblacion"], rng)
    costos = _costos_recorridos(C, poblacion)
    n_tour_evals = len(costos)
    k = int(np.argmin(costos))  # empates: primer índice
    best_tour, best_cost = poblacion[k].copy(), float(costos[k])

    for g in range(params["generaciones"]):
        orden = np.argsort(costos, kind="stable")[:elites]  # empates: primer índice
        hijos = _hijos(poblacion, costos, n_hijos, params, rng)
        costos_hijos = _costos_recorridos(C, hijos)
        n_tour_evals += len(costos_hijos)
        poblacion = np.vstack([poblacion[orden], hijos])
        costos = np.concatenate([costos[orden], costos_hijos])
        k = int(np.argmin(costos_hijos))
        if costos_hijos[k] < best_cost:  # mejora estricta
            best_tour, best_cost = hijos[k].copy(), float(costos_hijos[k])
        yield {
            "g": g,
            "poblacion": poblacion.copy(),
            "costos": costos.copy(),
            "n_tour_evals": n_tour_evals,
            "best_tour": best_tour.copy(),
            "best_cost": best_cost,
        }


# ------------------------------------------------------------------------------------------- contrato


def solve(C: np.ndarray, cfg: dict, rng: np.random.Generator) -> dict:
    """Resuelve el TSP simétrico de costos C con el GA de `cfg["ga"]` (Spec §5.2 y §7.4.2).

    Retorna {"tour", "cost", "n_tour_evals", "history"}: `tour` es la mejor permutación encontrada (el ciclo se
    cierra implícitamente), `cost` su costo con el arco de cierre, `n_tour_evals` = poblacion + (poblacion − elites)
    · generaciones y `history` una entrada por generación con el mejor global hasta ella.
    """
    history = []
    for estado in iterar(C, cfg, rng):
        history.append(
            {"iter": estado["g"], "best_cost": estado["best_cost"], "best_tour": estado["best_tour"].tolist()}
        )
    return {
        "tour": list(history[-1]["best_tour"]),
        "cost": history[-1]["best_cost"],
        "n_tour_evals": estado["n_tour_evals"],
        "history": history,
    }
