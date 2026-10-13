"""Envolvente inferior exacta de los costos de recorridos fijos en función de w (Spec §7.5 [DECIDIDO v1.16]).

Cada arco cuesta mín(a_rápida + w·t_rápida, a_sinpeaje + w·t_sinpeaje) (§7.3), así que el costo de un recorrido fijo
es lineal a trozos y cóncavo en w. Entre quiebres consecutivos (de todos los arcos de todos los candidatos) todo es
lineal y la envolvente inferior se obtiene con cruces de rectas calculados analíticamente, sin rejilla. Módulo puro:
no lee archivos ni corre solvers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.part2.costos import Componentes

TOL_EMPATE = 1e-12  # empate relativo entre recorridos al elegir el ganador al inicio de un tramo


@dataclass(frozen=True, eq=False)
class Rectas:
    """Costo de cada arco y alternativa como recta en w (Spec §7.3): c^a_ij(w) = a^a_ij + w · t^a_ij, con
    a = peaje + distancia · (consumo / 100) · precio_l y t = tiempo en horas."""

    a_rapida: np.ndarray
    t_rapida: np.ndarray
    a_sin_peaje: np.ndarray
    t_sin_peaje: np.ndarray


def rectas(comp: Componentes, consumo_l100: float, precio_l: float) -> Rectas:
    def fijo(peaje, dist):
        return peaje + dist * (consumo_l100 / 100) * precio_l

    return Rectas(
        a_rapida=fijo(comp.peaje_eur_rapida, comp.dist_km_rapida),
        t_rapida=np.asarray(comp.tiempo_h_rapida, dtype=float),
        a_sin_peaje=fijo(comp.peaje_eur_sin_peaje, comp.dist_km_sin_peaje),
        t_sin_peaje=np.asarray(comp.tiempo_h_sin_peaje, dtype=float),
    )


def canonico(tour) -> tuple[int, ...]:
    """Forma canónica de un ciclo: empieza en la ciudad 0 y va en el sentido cuyo segundo elemento es menor.

    C es simétrica (§7.2), así que las rotaciones y el sentido inverso de un ciclo son el mismo recorrido.
    """
    t = [int(c) for c in tour]
    if 0 not in t:
        raise ValueError(f"el recorrido debe contener la ciudad 0; se recibió {t}")
    k = t.index(0)
    rotado = t[k:] + t[:k]
    inverso = [rotado[0], *rotado[:0:-1]]
    return tuple(inverso if len(t) > 2 and inverso[1] < rotado[1] else rotado)


def _arcos(tours: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return tours, np.roll(tours, -1, axis=-1)


def costo_recorrido(rect: Rectas, tour, w: float) -> float:
    """Costo del recorrido cerrado en w: Σ mín(rápida, sin peaje) por arco (empate → rápida, mismo valor)."""
    u, v = _arcos(np.asarray(tour))
    r = rect.a_rapida[u, v] + w * rect.t_rapida[u, v]
    s = rect.a_sin_peaje[u, v] + w * rect.t_sin_peaje[u, v]
    return float(np.where(s < r, s, r).sum())


def _lineas(rect: Rectas, u: np.ndarray, v: np.ndarray, w: float) -> tuple[np.ndarray, np.ndarray]:
    """(intercepto, pendiente) del costo de cada recorrido en un tramo sin quiebres que contiene a w."""
    usa_s = rect.a_sin_peaje[u, v] + w * rect.t_sin_peaje[u, v] < rect.a_rapida[u, v] + w * rect.t_rapida[u, v]
    alfa = np.where(usa_s, rect.a_sin_peaje[u, v], rect.a_rapida[u, v]).sum(axis=1)
    beta = np.where(usa_s, rect.t_sin_peaje[u, v], rect.t_rapida[u, v]).sum(axis=1)
    return alfa, beta


def _ganador_en(alfa: np.ndarray, beta: np.ndarray, w: float) -> int:
    """Recorrido de menor costo en w; empates: menor pendiente (el que sigue ganando a la derecha), luego menor
    índice."""
    valor = alfa + beta * w
    minimo = valor.min()
    empatados = np.flatnonzero(valor <= minimo + TOL_EMPATE * max(1.0, abs(minimo)))
    # lexsort ordena por la última clave (pendiente) y desempata con la primera (índice).
    return int(empatados[np.lexsort((empatados, beta[empatados]))[0]])


def _envolvente_rectas(alfa: np.ndarray, beta: np.ndarray, L: float, R: float) -> list[tuple[float, float, int]]:
    """Envolvente inferior de rectas α_k + β_k·w en [L, R] como tramos (desde, hasta, k).

    Desde el ganador en L, el siguiente es la recta de menor pendiente que lo corta primero; cada cambio baja la
    pendiente, así que hay a lo sumo tantos cambios como rectas.
    """
    k = _ganador_en(alfa, beta, L)
    actual, tramos = L, []
    while True:
        menores = np.flatnonzero(beta < beta[k])
        if not menores.size:
            break
        # Un cruce "antes" de `actual` solo puede venir del redondeo (esa recta ya estaba debajo): cambia aquí mismo.
        cruces = np.maximum((alfa[menores] - alfa[k]) / (beta[k] - beta[menores]), actual)
        x = cruces.min()
        if x >= R:
            break
        en_x = menores[cruces == x]  # rectas que cortan al ganador en el mismo punto x
        # Tras x gana la de menor pendiente (lexsort: pendiente, luego índice).
        siguiente = int(en_x[np.lexsort((en_x, beta[en_x]))[0]])
        tramos.append((actual, float(x), k))
        actual, k = float(x), siguiente
    tramos.append((actual, R, k))
    return tramos


def envolvente(rect: Rectas, tours, w_min: float, w_max: float) -> dict:
    """Envolvente inferior exacta de los costos de `tours` en [w_min, w_max] (Spec §7.5 [DECIDIDO v1.16]).

    Devuelve {"candidatos": recorridos canónicos sin repetir y ordenados, "intervalos": [{w_desde, w_hasta,
    candidato, costo_desde, costo_hasta}] (cubren el rango sin huecos; ganadores consecutivos distintos),
    "umbrales": [{w, de, a, costo}]} (`candidato`, `de` y `a` son índices de "candidatos").
    """
    candidatos = sorted({canonico(t) for t in tours})
    u, v = _arcos(np.array(candidatos, dtype=np.intp))
    if w_min == w_max:
        tramos = [(w_min, w_max, _ganador_en(*_lineas(rect, u, v, w_min), w_min))]
    else:
        dt = rect.t_rapida[u, v] - rect.t_sin_peaje[u, v]
        con_quiebre = dt != 0
        quiebres = (rect.a_sin_peaje[u, v] - rect.a_rapida[u, v])[con_quiebre] / dt[con_quiebre]
        quiebres = quiebres[(quiebres > w_min) & (quiebres < w_max)]
        puntos = np.unique(np.concatenate([[w_min], quiebres, [w_max]]))
        tramos = []
        for L, R in zip(puntos[:-1].tolist(), puntos[1:].tolist()):
            tramos += _envolvente_rectas(*_lineas(rect, u, v, (L + R) / 2), L, R)
        tramos = [t for t in tramos if t[1] > t[0]]

    unidos: list[list] = []
    for desde, hasta, k in tramos:
        if unidos and unidos[-1][2] == k:
            unidos[-1][1] = hasta
        else:
            unidos.append([desde, hasta, k])

    intervalos = [
        {"w_desde": desde, "w_hasta": hasta, "candidato": k,
         "costo_desde": costo_recorrido(rect, candidatos[k], desde),
         "costo_hasta": costo_recorrido(rect, candidatos[k], hasta)}
        for desde, hasta, k in unidos
    ]
    umbrales = [
        {"w": b["w_desde"], "de": a["candidato"], "a": b["candidato"], "costo": b["costo_desde"]}
        for a, b in zip(intervalos, intervalos[1:])
    ]
    return {"candidatos": candidatos, "intervalos": intervalos, "umbrales": umbrales}


def costo_envolvente(env: dict, rect: Rectas, w: float) -> float:
    """Costo de la envolvente `env` en w (el del ganador del intervalo que contiene a w)."""
    tramo = next(s for s in env["intervalos"] if s["w_desde"] <= w <= s["w_hasta"])
    return costo_recorrido(rect, env["candidatos"][tramo["candidato"]], w)
