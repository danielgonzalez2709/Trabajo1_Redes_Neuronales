"""Pruebas de aceptación de T3.4: operadores del GA para permutaciones (Spec §7.4 y §7.4.2 [DECIDIDO v1.15]).

Aceptación del PLAN: 10 000 aplicaciones aleatorias de cada operador (OX, inversión, intercambio y la mutación 50/50)
sobre permutaciones aleatorias de tamaños variados (incluidos n = 3 y n = 47) producen siempre permutaciones válidas
de 0..n-1, y los padres no cambian.

Además, casos a mano:
  - OX con cortes fijos: el tramo P1[a..b] se conserva en sus posiciones y las posiciones libres se llenan, de
    izquierda a derecha, con las ciudades que faltan en el orden en que aparecen en P2 (§7.4.2).
  - Inversión del tramo [i..j] e intercambio de dos posiciones con posiciones fijas.
  - Sorteo de dos posiciones distintas a < b (lo usan OX e inversión).
  - Mutación 50/50: frecuencia de cada operador cercana a 0,5.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.part2 import ga

N_OPERACIONES = 10_000
TAMANOS = (3, 4, 5, 8, 13, 47)  # incluye n = 3 (mínimo de la validación de C) y n = 47 (las capitales)


def _es_permutacion(tour, n: int) -> bool:
    tour = np.asarray(tour)
    return tour.shape == (n,) and np.array_equal(np.sort(tour), np.arange(n))


def _permutaciones_aleatorias(semilla: int):
    """N_OPERACIONES pares (n, P1, P2) con n recorriendo TAMANOS y permutaciones uniformes."""
    rng = np.random.default_rng(semilla)
    for k in range(N_OPERACIONES):
        n = TAMANOS[k % len(TAMANOS)]
        yield n, rng.permutation(n), rng.permutation(n)


# ------------------------------------------------------------------------- 10 000 operaciones válidas


def test_ox_10000_operaciones_validas_y_padres_intactos():
    rng = np.random.default_rng(100)
    for n, p1, p2 in _permutaciones_aleatorias(1):
        c1, c2 = p1.copy(), p2.copy()
        hijo = ga._ox(p1, p2, rng)
        assert _es_permutacion(hijo, n)
        assert np.array_equal(p1, c1) and np.array_equal(p2, c2)
        assert hijo is not p1 and hijo is not p2


def test_inversion_10000_operaciones_validas_y_padre_intacto():
    rng = np.random.default_rng(101)
    for n, p, _ in _permutaciones_aleatorias(2):
        copia = p.copy()
        hijo = ga._invertir(p, rng)
        assert _es_permutacion(hijo, n)
        assert np.array_equal(p, copia)
        # posiciones distintas i < j: el tramo invertido tiene al menos 2 ciudades, así que el hijo cambia
        assert not np.array_equal(hijo, p)


def test_intercambio_10000_operaciones_validas_y_padre_intacto():
    rng = np.random.default_rng(102)
    for n, p, _ in _permutaciones_aleatorias(3):
        copia = p.copy()
        hijo = ga._intercambiar(p, rng)
        assert _es_permutacion(hijo, n)
        assert np.array_equal(p, copia)
        assert np.count_nonzero(hijo != p) == 2  # dos posiciones distintas, exactamente


def test_mutacion_10000_operaciones_validas_y_padre_intacto():
    rng = np.random.default_rng(103)
    for n, p, _ in _permutaciones_aleatorias(4):
        copia = p.copy()
        hijo = ga._mutar(p, rng)
        assert _es_permutacion(hijo, n)
        assert np.array_equal(p, copia)
        assert not np.array_equal(hijo, p)


def test_ox_encadenado_sigue_siendo_permutacion():
    """Hijos de hijos (como en generaciones sucesivas): 10 000 cruces encadenados con n = 47."""
    rng = np.random.default_rng(104)
    a, b = rng.permutation(47), rng.permutation(47)
    for _ in range(N_OPERACIONES):
        a, b = ga._ox(a, b, rng), ga._mutar(ga._ox(b, a, rng), rng)
        assert _es_permutacion(a, 47) and _es_permutacion(b, 47)


# ------------------------------------------------------------------------------------- casos a mano


P1 = np.arange(8)
P2 = np.array([7, 5, 3, 1, 6, 4, 2, 0])


def test_ox_a_mano():
    """a = 2, b = 5. OX(P1, P2): tramo P1[2..5] = [2, 3, 4, 5] en las posiciones 2..5. Ciudades que faltan, en el orden
    de P2 = 7, 5, 3, 1, 6, 4, 2, 0 sin {2, 3, 4, 5}: 7, 1, 6, 0. Posiciones libres de izquierda a derecha: 0, 1, 6, 7.
      hijo = [7, 1, 2, 3, 4, 5, 6, 0]
    OX(P2, P1): tramo P2[2..5] = [3, 1, 6, 4]; faltan, en el orden de P1: 0, 2, 5, 7.
      hijo = [0, 2, 3, 1, 6, 4, 5, 7]
    """
    assert ga._ox_tramo(P1, P2, 2, 5).tolist() == [7, 1, 2, 3, 4, 5, 6, 0]
    assert ga._ox_tramo(P2, P1, 2, 5).tolist() == [0, 2, 3, 1, 6, 4, 5, 7]


def test_ox_a_mano_tramos_en_los_extremos():
    """a = 0, b = 2: tramo P1[0..2] = [0, 1, 2]; faltan en el orden de P2: 7, 5, 3, 6, 4 → posiciones 3..7.
    a = 5, b = 7: tramo P2[5..7] = [4, 2, 0]; faltan en el orden de P1: 1, 3, 5, 6, 7 → posiciones 0..4."""
    assert ga._ox_tramo(P1, P2, 0, 2).tolist() == [0, 1, 2, 7, 5, 3, 6, 4]
    assert ga._ox_tramo(P2, P1, 5, 7).tolist() == [1, 3, 5, 6, 7, 4, 2, 0]


def test_ox_conserva_tramo_y_orden_relativo_de_p2():
    """Propiedad de OX sobre cortes aleatorios: el tramo de P1 queda en sus posiciones y las demás ciudades aparecen
    en el mismo orden relativo que en P2."""
    rng = np.random.default_rng(5)
    for _ in range(2_000):
        n = int(rng.integers(3, 30))
        p1, p2 = rng.permutation(n), rng.permutation(n)
        a, b = ga._dos_posiciones(n, rng)
        hijo = ga._ox_tramo(p1, p2, a, b)
        assert np.array_equal(hijo[a : b + 1], p1[a : b + 1])
        fuera = np.r_[0:a, b + 1 : n]
        tramo = set(p1[a : b + 1].tolist())
        assert hijo[fuera].tolist() == [c for c in p2.tolist() if c not in tramo]


def test_inversion_a_mano():
    """[0..7] con i = 2, j = 5: el tramo [2, 3, 4, 5] queda [5, 4, 3, 2]."""
    assert ga._invertir_tramo(P1, 2, 5).tolist() == [0, 1, 5, 4, 3, 2, 6, 7]
    assert ga._invertir_tramo(P2, 0, 7).tolist() == P2[::-1].tolist()
    assert ga._invertir_tramo(P1, 3, 4).tolist() == [0, 1, 2, 4, 3, 5, 6, 7]


def test_intercambio_a_mano():
    """[0..7] con posiciones 1 y 6: [0, 6, 2, 3, 4, 5, 1, 7]."""
    assert ga._intercambiar_posiciones(P1, 1, 6).tolist() == [0, 6, 2, 3, 4, 5, 1, 7]
    assert ga._intercambiar_posiciones(P2, 0, 7).tolist() == [0, 5, 3, 1, 6, 4, 2, 7]


def test_operadores_a_mano_no_modifican_la_entrada():
    p1, p2 = P1.copy(), P2.copy()
    ga._ox_tramo(p1, p2, 2, 5)
    ga._invertir_tramo(p1, 2, 5)
    ga._intercambiar_posiciones(p2, 1, 6)
    assert np.array_equal(p1, P1) and np.array_equal(p2, P2)


def test_dos_posiciones_distintas_ordenadas_y_todas_posibles():
    """a < b, ambas en 0..n-1; con n = 4 salen los 6 pares posibles."""
    rng = np.random.default_rng(6)
    vistos = set()
    for _ in range(N_OPERACIONES):
        a, b = ga._dos_posiciones(4, rng)
        assert type(a) is int and type(b) is int
        assert 0 <= a < b <= 3
        vistos.add((a, b))
    assert vistos == {(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)}


# --------------------------------------------------------------------------------------- mutación 50/50


@pytest.fixture
def espia_operadores(monkeypatch):
    """Envuelve `ga._invertir` y `ga._intercambiar` (que `_mutar` llama por nombre) y anota, por llamada, qué
    operador se aplicó y qué devolvió."""
    llamadas = []
    for nombre in ("_invertir", "_intercambiar"):
        original = getattr(ga, nombre)

        def espia(tour, rng, _nombre=nombre, _original=original):
            hijo = _original(tour, rng)
            llamadas.append((_nombre, hijo))
            return hijo

        monkeypatch.setattr(ga, nombre, espia)
    return llamadas


def test_mutacion_elige_cada_operador_con_probabilidad_un_medio(espia_operadores):
    """Inversión o intercambio, 50/50 (§7.4.2). Tolerancia: 5 desviaciones estándar de una binomial con p = 0.5 y
    k = 20 000 (semilla fija)."""
    k = 20_000
    rng = np.random.default_rng(7)
    tour = np.arange(10)
    for _ in range(k):
        ga._mutar(tour, rng)
    operadores = [nombre for nombre, _ in espia_operadores]
    assert len(operadores) == k
    frecuencia = operadores.count("_invertir") / k
    assert abs(frecuencia - 0.5) < 5 * math.sqrt(0.25 / k)


def test_mutacion_aplica_un_solo_operador_y_devuelve_su_resultado(espia_operadores):
    """Cada mutación llama exactamente a un operador, y el hijo es lo que ese operador devolvió."""
    rng = np.random.default_rng(8)
    tour = rng.permutation(12)
    for k in range(1, 501):
        hijo = ga._mutar(tour, rng)
        assert len(espia_operadores) == k
        assert hijo is espia_operadores[-1][1]
    assert {nombre for nombre, _ in espia_operadores} == {"_invertir", "_intercambiar"}
