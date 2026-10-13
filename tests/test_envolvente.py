"""Pruebas de `src/part2/envolvente.py` (T3.6, Spec §7.5 [DECIDIDO v1.16]): envolvente inferior exacta.

Qué se prueba:
  1. Envolvente con datos sintéticos calculados a mano: dos rectas que se cruzan, un arco que cambia de alternativa
     dentro del intervalo, tres candidatos con uno que nunca gana y un cruce fino (0,011 €/h) que una rejilla de 0,5
     no ve.
  2. Fuerza bruta con datos reales y candidatos que sí se cruzan.
  3. Casos borde: rango de un solo punto, quiebre justo en w_min/w_max, desempates de `_ganador_en`, recorridos
     distintos con el mismo costo.
  4. Canonicalización: rotaciones y sentido inverso de un ciclo son el mismo candidato.
  5. Costo de un recorrido fijo por rectas == costo con `matriz_costos` (datos reales).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.part2 import envolvente as ev
from src.part2.costos import cargar_componentes, matriz_costos
from src.part2.recorridos import costos_recorridos, vecino_mas_cercano
from tests.sinteticos_part2 import (A, B, C, CARO, RAPIDA_TROZOS, SIN_PEAJE_TROZOS, UNO, comp, comp_trozos,
                                     rectas_unitarias)

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
# Consumo y precio de los archivos (vehiculo.yaml, combustible.json); aquí solo hace falta que sean positivos.
CONSUMO, PRECIO = 4.6, 1.8318

DOS_RECTAS = {(0, 1): UNO, (1, 2): UNO, (2, 3): UNO, (0, 3): UNO, (1, 3): CARO, (0, 2): CARO}


def _ganadores(env: dict) -> list[tuple[int, ...]]:
    return [env["candidatos"][s["candidato"]] for s in env["intervalos"]]


def _umbrales(env: dict) -> list[float]:
    return [u["w"] for u in env["umbrales"]]


@pytest.fixture(scope="module")
def rect_reales():
    return ev.rectas(cargar_componentes(PROC), CONSUMO, PRECIO)


# ------------------------------------------------------------------------------- 1. a mano (sintéticos)


def test_dos_rectas_se_cruzan_en_w_20():
    """A = 4w (cuatro arcos de 1 h, sin peaje); B = 20 + 3w (dos arcos de 1 h y dos de 10 € + 0,5 h).
    A = B en w = 20."""
    env = ev.envolvente(rectas_unitarias(comp(DOS_RECTAS)), [A, B], 0.0, 100.0)
    assert _ganadores(env) == [A, B]
    assert _umbrales(env) == [pytest.approx(20.0, abs=1e-12)]
    assert env["intervalos"][0]["w_desde"] == 0.0 and env["intervalos"][-1]["w_hasta"] == 100.0
    assert env["intervalos"][0]["costo_desde"] == pytest.approx(0.0)
    assert env["intervalos"][-1]["costo_hasta"] == pytest.approx(320.0)


@pytest.mark.parametrize("intercambiadas", [False, True], ids=["sin_peaje_lenta", "sin_peaje_rapida"])
def test_cruce_exacto_con_un_arco_que_cambia_de_alternativa(intercambiadas):
    """A y B se cruzan en w = 14 (6 + 4w = 20 + 3w), no en 13,33 (4,5w = 20 + 3w, la recta de A antes del quiebre).

    Con las alternativas del arco 12 intercambiadas (la sin peaje es la rápida) la función es la misma; ese caso
    exige decidir la alternativa activa dentro del tramo y no en su extremo izquierdo, donde las dos empatan.
    """
    env = ev.envolvente(rectas_unitarias(comp_trozos(intercambiadas)), [A, B], 0.0, 100.0)
    assert _ganadores(env) == [A, B]
    assert _umbrales(env) == [pytest.approx(14.0, abs=1e-12)]


def test_tres_candidatos_uno_nunca_gana():
    """C(w) > mín(A, B) en todo [0, 100]: no aparece en la envolvente y el único umbral sigue en 14."""
    env = ev.envolvente(rectas_unitarias(comp_trozos()), [C, A, B], 0.0, 100.0)
    assert _ganadores(env) == [A, B]
    assert _umbrales(env) == [pytest.approx(14.0, abs=1e-12)]
    assert sorted(env["candidatos"]) == sorted([A, B, C])  # C es candidato aunque no gane


def test_umbral_con_un_trozo_a_cada_lado_del_quiebre():
    """Si el cruce cae antes del quiebre del arco, sale de la recta de antes: con B' = 9 + 3w,
    A = B' en 4,5w = 9 + 3w → w = 6."""
    rapida = {**RAPIDA_TROZOS, (1, 3): (4.5, 0.5), (0, 2): (4.5, 0.5)}
    env = ev.envolvente(rectas_unitarias(comp(rapida, SIN_PEAJE_TROZOS)), [A, B], 0.0, 100.0)
    assert _umbrales(env) == [pytest.approx(6.0, abs=1e-12)]


# Cruce fino: A = 40 + 4w, C = 70 + 3w, B = 100,011 + 2w → A = C en w = 30 y C = B en w = 30,011
# (C gana solo 0,011 €/h).
# Con X = a + c, Y = b + d, Z = e + f (a = 01, b = 12, c = 23, d = 30, e = 13, f = 02): A = X + Y, B = X + Z, C = Y + Z.
# X = (A + B − C)/2 = 35,0055 + 1,5w, Y = (A + C − B)/2 = 4,9945 + 2,5w, Z = (B + C − A)/2 = 65,0055 + 0,5w; cada
# suma se reparte a partes iguales entre sus dos arcos.
FINO = {
    (0, 1): (17.50275, 0.75), (2, 3): (17.50275, 0.75),
    (1, 2): (2.49725, 1.25), (0, 3): (2.49725, 1.25),
    (1, 3): (32.50275, 0.25), (0, 2): (32.50275, 0.25),
}


def test_cruce_fino_que_una_rejilla_de_medio_euro_no_ve():
    rect = rectas_unitarias(comp(FINO))
    env = ev.envolvente(rect, [A, B, C], 0.0, 100.0)
    assert _ganadores(env) == [A, C, B]
    assert _umbrales(env) == [pytest.approx(30.0, abs=1e-9), pytest.approx(30.011, abs=1e-9)]
    # La rejilla de 0,5 €/h nunca elige C: el umbral exacto no sale de evaluar en puntos fijos.
    rejilla = np.arange(0.0, 100.0 + 0.25, 0.5)
    ganadores_rejilla = {min((A, B, C), key=lambda t: ev.costo_recorrido(rect, t, w)) for w in rejilla}
    assert C not in ganadores_rejilla


# ----------------------------------------------------------------------------- 2. fuerza bruta (reales)


def _par_que_se_cruza(rect) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Dos variantes (inversión de un tramo) del vecino más cercano en w = 50 cuyo orden de costo se invierte entre
    w = 0 y w = 100: entre ellas hay al menos un umbral. Búsqueda determinista (semilla 0)."""
    Cw, _ = matriz_costos(cargar_componentes(PROC), 50.0, {"consumo_wltp_comb_l100": CONSUMO}, PRECIO)
    base = vecino_mas_cercano(Cw)[0]
    rng = np.random.default_rng(0)
    variantes = []
    for _ in range(40):
        i, j = sorted(rng.choice(47, 2, replace=False).tolist())
        t = base.copy()
        t[i : j + 1] = t[i : j + 1][::-1]
        variantes.append(tuple(int(c) for c in t))
    c0 = [ev.costo_recorrido(rect, t, 0.0) for t in variantes]
    c100 = [ev.costo_recorrido(rect, t, 100.0) for t in variantes]
    indices = range(len(variantes))
    pares = [(a, b) for a in indices for b in indices if c0[a] < c0[b] and c100[a] > c100[b]]
    assert pares, "precondición: debe haber un par que se cruce"
    a, b = pares[0]
    return variantes[a], variantes[b]


def test_envolvente_coincide_con_fuerza_bruta_en_datos_reales(rect_reales):
    """Un par que se cruza + 10 permutaciones al azar: hay al menos un umbral y, en 401 puntos de [0, 100], el
    ganador de la envolvente tiene el costo mínimo de todos los recorridos."""
    rng = np.random.default_rng(1)
    tours = [*_par_que_se_cruza(rect_reales), *(tuple(rng.permutation(47)) for _ in range(10))]
    env = ev.envolvente(rect_reales, tours, 0.0, 100.0)
    assert len(env["umbrales"]) >= 1
    puntos = np.concatenate([np.linspace(0.0, 100.0, 401), _umbrales(env)])
    for w in puntos:
        minimo = min(ev.costo_recorrido(rect_reales, t, w) for t in tours)
        assert ev.costo_envolvente(env, rect_reales, w) == pytest.approx(minimo, rel=1e-12)
    # Los intervalos cubren [0, 100] sin huecos y cada umbral separa ganadores distintos.
    for s1, s2 in zip(env["intervalos"], env["intervalos"][1:]):
        assert s1["w_hasta"] == s2["w_desde"] and s1["candidato"] != s2["candidato"]
    assert len(env["umbrales"]) == len(env["intervalos"]) - 1


# ------------------------------------------------------------------------------------- 3. casos borde


def test_envolvente_en_un_solo_punto():
    """Rango degenerado (un solo w, p. ej. la demo): un intervalo, sin umbrales."""
    env = ev.envolvente(rectas_unitarias(comp(DOS_RECTAS)), [A, B], 25.0, 25.0)
    assert _ganadores(env) == [B] and env["umbrales"] == []


@pytest.mark.parametrize("intercambiadas", [False, True], ids=["sin_peaje_lenta", "sin_peaje_rapida"])
def test_quiebre_justo_en_los_extremos_del_rango(intercambiadas):
    """El arco 12 cambia de alternativa en w = 12. Con el quiebre en w_max ([0, 12]) gana A todo el rango
    (4,5w < 20 + 3w); con el quiebre en w_min ([12, 100]) A y B se cruzan en 14; en [12, 12], A cuesta 54."""
    rect = rectas_unitarias(comp_trozos(intercambiadas))
    izquierda = ev.envolvente(rect, [A, B], 0.0, 12.0)
    assert _ganadores(izquierda) == [A] and izquierda["umbrales"] == []
    assert izquierda["intervalos"][0]["costo_hasta"] == pytest.approx(54.0)
    derecha = ev.envolvente(rect, [A, B], 12.0, 100.0)
    assert _ganadores(derecha) == [A, B] and _umbrales(derecha) == [pytest.approx(14.0, abs=1e-12)]
    assert derecha["intervalos"][0]["costo_desde"] == pytest.approx(54.0)
    punto = ev.envolvente(rect, [A, B], 12.0, 12.0)
    assert _ganadores(punto) == [A] and punto["intervalos"][0]["costo_desde"] == pytest.approx(54.0)


def test_ganador_en_desempata_por_pendiente_y_luego_por_indice():
    # Rectas idénticas: gana el menor índice.
    assert ev._ganador_en(np.array([5.0, 5.0]), np.array([1.0, 1.0]), 3.0) == 0
    # Empate en w = 10 (20 = 20) con pendientes distintas: gana la de menor pendiente, esté donde esté.
    assert ev._ganador_en(np.array([0.0, 10.0]), np.array([2.0, 1.0]), 10.0) == 1
    assert ev._ganador_en(np.array([10.0, 0.0]), np.array([1.0, 2.0]), 10.0) == 0
    # Sin empate, gana el de menor costo aunque tenga mayor pendiente.
    assert ev._ganador_en(np.array([0.0, 10.0]), np.array([2.0, 1.0]), 9.0) == 0


def test_recorridos_distintos_con_el_mismo_costo_no_producen_umbrales():
    """Todos los arcos iguales: A, B y C cuestan 4w. Gana el primero en orden canónico, sin cambios falsos."""
    todos_uno = {(i, j): UNO for i in range(4) for j in range(i + 1, 4)}
    env = ev.envolvente(rectas_unitarias(comp(todos_uno)), [C, B, A], 0.0, 100.0)
    assert _ganadores(env) == [A] and env["umbrales"] == []


# ------------------------------------------------------------------------------------ 4. canonicalización


def test_rotaciones_y_sentido_inverso_son_el_mismo_ciclo():
    base = (0, 1, 2, 3, 4)
    variantes = [base[k:] + base[:k] for k in range(5)]
    variantes += [tuple(reversed(v)) for v in variantes]
    assert {ev.canonico(v) for v in variantes} == {(0, 1, 2, 3, 4)}
    # [2, 4, 0, 3, 1] rota a (0, 3, 1, 2, 4); al revés sería (0, 4, 2, 1, 3): gana el de menor segundo elemento.
    assert ev.canonico([2, 4, 0, 3, 1]) == (0, 3, 1, 2, 4)
    assert ev.canonico(np.array([3, 0, 4, 1, 2])) != ev.canonico(base)


def test_la_envolvente_no_duplica_candidatos_ni_inventa_cambios():
    """Rotaciones/inversiones del mismo ciclo cuentan como uno solo y no producen umbrales."""
    env = ev.envolvente(rectas_unitarias(comp(DOS_RECTAS)), [A, (2, 3, 0, 1), (3, 2, 1, 0)], 0.0, 100.0)
    assert env["candidatos"] == [A] and env["umbrales"] == []


# ----------------------------------------------------------------- 5. costo por rectas == matriz_costos


@pytest.mark.parametrize("w", [0.0, 7.3, 25.0, 30.011, 100.0])
def test_costo_por_rectas_igual_a_matriz_costos(rect_reales, w):
    Cw, _ = matriz_costos(cargar_componentes(PROC), w, {"consumo_wltp_comb_l100": CONSUMO}, PRECIO)
    rng = np.random.default_rng(1)
    for _ in range(20):
        tour = rng.permutation(47)
        assert ev.costo_recorrido(rect_reales, tour, w) == pytest.approx(costos_recorridos(Cw, tour[None])[0],
                                                                         rel=1e-12)
