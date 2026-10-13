"""Pruebas de T3.4: algoritmo genético para el TSP (Spec §5.2, §7.4 y §7.4.2 [DECIDIDO v1.15]).

Qué se prueba:
  1. Con 8 ciudades, el GA encuentra el óptimo de fuerza bruta (7! permutaciones con la ciudad 0 fija).
  2. Recorridos válidos en varias semillas.
  3. Conteo: n_tour_evals = poblacion + (poblacion − elites) · generaciones, también con poblacion − elites impar
     (el segundo hijo sobrante no se evalúa ni se cuenta).
  4. Población inicial: el vecino más cercano desde la ciudad 0 + poblacion − 1 permutaciones al azar.
  5. Elitismo: el mejor global no empeora; los élites de la generación g pasan sin cambios a la g + 1.
  6. Torneo: con torneo_k = poblacion gana el mejor; con torneo_k = 1 es uniforme; empates: primero del sorteo.
  7. pc = 0 y pm = 0: los hijos son copias de los padres.
  8. `history`: una entrada por generación, best_cost no creciente, último valor = cost, iter desde 0.
  9. `cost` = costo recalculado del recorrido (con el arco de cierre).
 10. Reproducibilidad con `rng`.
 11. Validaciones de C y de cada parámetro de `ga:`.
 12. Bloque `ga:` de `configs/part2/base.yaml`.

Las pruebas que revisan cada generación leen los estados de `ga.iterar` (el generador que consume `solve`).
"""

from __future__ import annotations

import inspect
import itertools
import math
from pathlib import Path

import numpy as np
import pytest

from src.common.config import load_config
from src.part2 import aco, ga, recorridos

ROOT = Path(__file__).resolve().parents[1]
BASE_PART2 = ROOT / "configs" / "part2" / "base.yaml"


# --------------------------------------------------------------------------------------------- auxiliares


def _cfg(poblacion=20, generaciones=30, pc=0.9, pm=0.2, torneo_k=4, elites=2):
    return {
        "ga": {
            "poblacion": poblacion,
            "generaciones": generaciones,
            "pc": pc,
            "pm": pm,
            "torneo_k": torneo_k,
            "elites": elites,
        }
    }


def _euclidea(n: int, semilla: int) -> np.ndarray:
    """Instancia euclídea con coordenadas uniformes en [0, 100]²."""
    xy = np.random.default_rng(semilla).uniform(0, 100, size=(n, 2))
    return np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))


def _costo_a_mano(C: np.ndarray, tour) -> float:
    """Costo del ciclo con el arco de cierre, sumado arco por arco (independiente de ga.py)."""
    return sum(C[tour[k], tour[(k + 1) % len(tour)]] for k in range(len(tour)))


def _fuerza_bruta(C: np.ndarray) -> float:
    n = C.shape[0]
    return min(_costo_a_mano(C, (0, *resto)) for resto in itertools.permutations(range(1, n)))


def _filas(matriz) -> set:
    return {tuple(int(c) for c in fila) for fila in matriz}


def _es_permutacion(tour, n: int) -> bool:
    return sorted(int(c) for c in tour) == list(range(n))


C8 = _euclidea(8, 7)
OPTIMO_8 = _fuerza_bruta(C8)


# ------------------------------------------------------------------------- 1. 8 ciudades = fuerza bruta


def test_instancia_de_8_ciudades_no_es_trivial():
    """El vecino más cercano (individuo inicial) no es óptimo: si lo fuera, la prueba no probaría nada."""
    _, c_nn = recorridos.vecino_mas_cercano(C8)
    assert c_nn > OPTIMO_8 * (1 + 1e-9)


@pytest.mark.parametrize("semilla", [0, 1, 2])
def test_8_ciudades_coincide_con_fuerza_bruta(semilla):
    res = ga.solve(C8, _cfg(poblacion=30, generaciones=60), np.random.default_rng(semilla))
    assert res["cost"] == pytest.approx(OPTIMO_8, rel=1e-12)


def test_8_ciudades_mejora_desde_la_poblacion_inicial():
    """El óptimo no está ya en la población inicial: lo encuentran las generaciones (el operador importa)."""
    cfg = _cfg(poblacion=10, generaciones=60)
    inicial = ga._poblacion_inicial(C8, 10, np.random.default_rng(3))
    assert recorridos.costos_recorridos(C8, inicial).min() > OPTIMO_8 * (1 + 1e-9)
    res = ga.solve(C8, cfg, np.random.default_rng(3))
    assert res["cost"] == pytest.approx(OPTIMO_8, rel=1e-12)


# ------------------------------------------------------------------------------ 2. recorridos válidos


@pytest.mark.parametrize("semilla", range(5))
def test_recorrido_es_permutacion(semilla):
    C = _euclidea(12, 5)
    res = ga.solve(C, _cfg(poblacion=11, generaciones=10, elites=3), np.random.default_rng(semilla))
    assert _es_permutacion(res["tour"], 12)
    assert all(type(c) is int for c in res["tour"])
    assert type(res["cost"]) is float
    for h in res["history"]:
        assert _es_permutacion(h["best_tour"], 12)


def test_toda_la_poblacion_son_permutaciones():
    C = _euclidea(10, 2)
    for estado in ga.iterar(C, _cfg(poblacion=9, generaciones=8, pm=0.7, elites=1), np.random.default_rng(4)):
        assert estado["poblacion"].shape == (9, 10)
        assert (np.sort(estado["poblacion"], axis=1) == np.arange(10)).all()


def test_funciona_con_tres_ciudades():
    C = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]], dtype=float)
    res = ga.solve(C, _cfg(poblacion=4, generaciones=3, torneo_k=2, elites=1), np.random.default_rng(0))
    assert _es_permutacion(res["tour"], 3)
    assert res["cost"] == 6.0  # todo ciclo de 3 ciudades cuesta 1 + 2 + 3


# -------------------------------------------------------------------------------------- 3. conteo


@pytest.mark.parametrize(
    ("poblacion", "elites", "generaciones"),
    [(20, 2, 7), (7, 2, 4), (6, 0, 3), (5, 4, 5), (2, 1, 3)],  # 7 − 2 = 5 y 5 − 4 = 1: número impar de hijos
)
def test_conteo_de_recorridos(poblacion, elites, generaciones, monkeypatch):
    """n_tour_evals sigue la fórmula de §7.4.2 y coincide con los recorridos que de verdad se evalúan (se cuentan las
    filas que recibe la función de costos): el segundo hijo sobrante no se evalúa."""
    evaluados = []
    original = ga._costos_recorridos

    def contar(C, tours):
        evaluados.append(len(tours))
        return original(C, tours)

    monkeypatch.setattr(ga, "_costos_recorridos", contar)
    cfg = _cfg(poblacion=poblacion, generaciones=generaciones, elites=elites, torneo_k=2)
    res = ga.solve(C8, cfg, np.random.default_rng(0))
    esperado = poblacion + (poblacion - elites) * generaciones
    assert res["n_tour_evals"] == esperado
    assert type(res["n_tour_evals"]) is int
    assert sum(evaluados) == esperado


def test_conteo_con_valores_por_defecto():
    """§7.4.2: 150 + 148 · 1 000 = 148 150 (sin correr el GA: misma fórmula con los valores de la base)."""
    bloque = load_config(BASE_PART2)["ga"]
    assert bloque["poblacion"] + (bloque["poblacion"] - bloque["elites"]) * bloque["generaciones"] == 148_150


def test_numero_de_hijos_por_generacion_con_cantidad_impar():
    """poblacion = 7, elites = 2: cada generación tiene 7 individuos (2 élites + 5 hijos)."""
    for estado in ga.iterar(C8, _cfg(poblacion=7, generaciones=4, elites=2, torneo_k=2), np.random.default_rng(1)):
        assert estado["poblacion"].shape == (7, 8)
        assert estado["costos"].shape == (7,)


# ---------------------------------------------------------------------------------- 4. población inicial


def test_poblacion_inicial_contiene_el_vecino_mas_cercano():
    C = _euclidea(15, 3)
    poblacion = ga._poblacion_inicial(C, 25, np.random.default_rng(0))
    tour_nn, _ = recorridos.vecino_mas_cercano(C)
    assert poblacion.shape == (25, 15)
    assert np.array_equal(poblacion[0], tour_nn)
    assert (np.sort(poblacion, axis=1) == np.arange(15)).all()
    assert len(_filas(poblacion[1:])) == 24  # 24 permutaciones al azar (con n = 15 no se repiten en la práctica)
    assert tuple(tour_nn.tolist()) not in _filas(poblacion[1:])


def test_poblacion_inicial_al_azar_es_uniforme():
    """La primera ciudad de las permutaciones al azar es uniforme en 0..n-1 (no fijas en 0 como el vecino)."""
    C = _euclidea(4, 1)
    poblacion = ga._poblacion_inicial(C, 20_001, np.random.default_rng(2))
    primeras = poblacion[1:, 0]
    sd = math.sqrt(0.25 * 0.75 / len(primeras))
    for ciudad in range(4):
        assert abs(np.mean(primeras == ciudad) - 0.25) < 5 * sd


def test_mejor_global_inicial_no_supera_al_vecino_mas_cercano():
    """El GA parte del mismo punto que ACO (§7.4.2): el mejor de la generación 0 cuesta a lo sumo C^nn."""
    C = _euclidea(20, 6)
    _, c_nn = recorridos.vecino_mas_cercano(C)
    res = ga.solve(C, _cfg(poblacion=10, generaciones=5), np.random.default_rng(0))
    assert res["history"][0]["best_cost"] <= c_nn


# ------------------------------------------------------------------------------------- 5. elitismo


def test_elites_pasan_sin_cambios_a_la_siguiente_generacion():
    """Los `elites` de menor costo de la generación g (empates: primer índice) son las primeras filas de la g + 1.
    n = 5 deja solo 12 ciclos distintos, así que hay empates de costo en la población."""
    C = _euclidea(5, 4)
    elites = 3
    cfg = _cfg(poblacion=12, generaciones=25, elites=elites, pm=0.5)
    rng = np.random.default_rng(9)
    estados = list(ga.iterar(C, cfg, rng))
    hubo_empate = False
    for previo, estado in zip(estados, estados[1:]):
        orden = np.argsort(previo["costos"], kind="stable")[:elites]
        assert np.array_equal(estado["poblacion"][:elites], previo["poblacion"][orden])
        assert np.array_equal(estado["costos"][:elites], previo["costos"][orden])
        hubo_empate |= len(np.unique(previo["costos"])) < len(previo["costos"])
    assert hubo_empate, "el caso no ejercita el desempate de los élites"


def test_elites_de_la_poblacion_inicial():
    """Generación 0: sus primeras filas son los élites de la población inicial (misma semilla)."""
    C = _euclidea(9, 2)
    cfg = _cfg(poblacion=10, generaciones=1, elites=4)
    inicial = ga._poblacion_inicial(C, 10, np.random.default_rng(5))
    costos = recorridos.costos_recorridos(C, inicial)
    estado = next(ga.iterar(C, cfg, np.random.default_rng(5)))
    assert np.array_equal(estado["poblacion"][:4], inicial[np.argsort(costos, kind="stable")[:4]])


def test_mejor_global_nunca_empeora_y_es_el_minimo_visto():
    C = _euclidea(14, 8)
    rng = np.random.default_rng(1)
    cfg = _cfg(poblacion=12, generaciones=40, elites=0, pm=0.6)  # sin élites el mejor de la población puede empeorar
    inicial = ga._poblacion_inicial(C, 12, np.random.default_rng(1))
    minimo = float(recorridos.costos_recorridos(C, inicial).min())
    previo = math.inf
    empeoro_la_poblacion = False
    for estado in ga.iterar(C, cfg, rng):
        minimo = min(minimo, float(estado["costos"].min()))
        assert estado["best_cost"] == pytest.approx(minimo, rel=1e-12)
        assert estado["best_cost"] <= previo
        assert estado["best_cost"] == pytest.approx(_costo_a_mano(C, estado["best_tour"]), rel=1e-12)
        empeoro_la_poblacion |= float(estado["costos"].min()) > estado["best_cost"]
        previo = estado["best_cost"]
    assert empeoro_la_poblacion, "el caso no distingue el mejor global del mejor de la generación"


def test_mejor_global_cambia_solo_con_mejora_estricta():
    """Con n = 3 todos los ciclos cuestan lo mismo: el mejor global se queda en el primero de la población inicial
    (el vecino más cercano, índice 0)."""
    C = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]], dtype=float)
    res = ga.solve(C, _cfg(poblacion=6, generaciones=10, torneo_k=2, elites=1, pm=1.0), np.random.default_rng(0))
    tour_nn, _ = recorridos.vecino_mas_cercano(C)
    assert res["tour"] == tour_nn.tolist()
    assert all(h["best_tour"] == tour_nn.tolist() for h in res["history"])


# -------------------------------------------------------------------------------------- 6. torneo


def test_torneo_con_k_igual_a_la_poblacion_gana_el_mejor():
    rng = np.random.default_rng(0)
    for _ in range(500):
        costos = rng.uniform(0, 10, size=9)
        assert ga._torneo(costos, 9, rng) == int(np.argmin(costos))


def test_torneo_con_k_uno_es_uniforme():
    k = 40_000
    rng = np.random.default_rng(1)
    costos = np.array([4.0, 1.0, 3.0, 2.0])
    ganadores = np.array([ga._torneo(costos, 1, rng) for _ in range(k)])
    sd = math.sqrt(0.25 * 0.75 / k)
    for i in range(4):
        assert abs(np.mean(ganadores == i) - 0.25) < 5 * sd


def test_torneo_empates_gana_el_primero_del_sorteo():
    """Costos iguales y k = poblacion: gana el primero del sorteo, que es uniforme (no siempre el índice 0)."""
    k = 20_000
    rng = np.random.default_rng(2)
    ganadores = np.array([ga._torneo(np.ones(4), 4, rng) for _ in range(k)])
    sd = math.sqrt(0.25 * 0.75 / k)
    for i in range(4):
        assert abs(np.mean(ganadores == i) - 0.25) < 5 * sd


def test_torneo_sortea_individuos_distintos():
    """k = 2 entre 3 individuos distintos: el peor (índice 2) nunca gana, porque a su lado siempre hay otro mejor.
    Si el sorteo fuera con reemplazo, podría salir dos veces el peor y ganar."""
    rng = np.random.default_rng(3)
    costos = np.array([1.0, 2.0, 3.0])
    ganadores = {ga._torneo(costos, 2, rng) for _ in range(5_000)}
    assert ganadores == {0, 1}


# --------------------------------------------------------------------------------- 7. pc = 0, pm = 0


def test_sin_cruce_ni_mutacion_los_hijos_son_copias():
    C = _euclidea(10, 3)
    cfg = _cfg(poblacion=12, generaciones=15, pc=0.0, pm=0.0, elites=1, torneo_k=3)
    inicial = ga._poblacion_inicial(C, 12, np.random.default_rng(4))
    previos = _filas(inicial)
    for estado in ga.iterar(C, cfg, np.random.default_rng(4)):
        actuales = _filas(estado["poblacion"])
        assert actuales <= previos
        previos = actuales


def test_con_mutacion_aparecen_individuos_nuevos():
    """Contraste del caso anterior: con pm = 1 (y pc = 0) aparecen individuos que no estaban."""
    C = _euclidea(10, 3)
    cfg = _cfg(poblacion=12, generaciones=1, pc=0.0, pm=1.0, elites=1, torneo_k=3)
    inicial = ga._poblacion_inicial(C, 12, np.random.default_rng(4))
    estado = next(ga.iterar(C, cfg, np.random.default_rng(4)))
    assert not _filas(estado["poblacion"][1:]) & _filas(inicial)  # cada hijo mutó: ninguno es copia exacta


def test_con_cruce_aparecen_individuos_nuevos():
    C = _euclidea(10, 3)
    cfg = _cfg(poblacion=12, generaciones=1, pc=1.0, pm=0.0, elites=1, torneo_k=3)
    inicial = ga._poblacion_inicial(C, 12, np.random.default_rng(4))
    estado = next(ga.iterar(C, cfg, np.random.default_rng(4)))
    assert _filas(estado["poblacion"]) - _filas(inicial)


# ------------------------------------------------------------- generación de hijos con sorteos controlados
# §7.4.2, Generación, punto 2: dos torneos eligen P1 y P2; con cruce nacen OX(P1, P2) y OX(P2, P1); sin cruce, copias
# de P1 y P2, en ese orden. Los torneos y los cortes se fijan con monkeypatch; pc y pm en {0, 1} hacen deterministas
# los sorteos de cruce y mutación.

POB_4 = np.array(
    [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [7, 5, 3, 1, 6, 4, 2, 0],
        [3, 0, 6, 2, 7, 1, 5, 4],
        [5, 2, 7, 0, 4, 6, 1, 3],
    ]
)


def _hijos_controlados(monkeypatch, cantidad, pc, ganadores, cortes):
    """Hijos de `ga._hijos` con los ganadores de torneo y los cortes (a, b) dados, en orden de uso."""
    ganadores, cortes = iter(ganadores), iter(cortes)
    monkeypatch.setattr(ga, "_torneo", lambda costos, k, rng: next(ganadores))
    monkeypatch.setattr(ga, "_dos_posiciones", lambda n, rng: next(cortes))
    params = {"torneo_k": 2, "pc": pc, "pm": 0.0}
    return ga._hijos(POB_4.copy(), np.arange(4.0), cantidad, params, np.random.default_rng(0))


def test_hijos_con_cruce_son_ox_p1_p2_y_ox_p2_p1(monkeypatch):
    """P1 = fila 0, P2 = fila 1, cortes (2, 5) y luego (1, 3):
      hijo 1 = OX(P1, P2) con (2, 5) = [7, 1, 2, 3, 4, 5, 6, 0]   (caso a mano de test_tsp_operators)
      hijo 2 = OX(P2, P1) con (1, 3): tramo P2[1..3] = [5, 3, 1]; faltan en el orden de P1: 0, 2, 4, 6, 7
             = [0, 5, 3, 1, 2, 4, 6, 7]
    (OX(P1, P2) con (1, 3) daría [7, 1, 2, 3, 5, 6, 4, 0]: el orden de los padres importa)."""
    hijos = _hijos_controlados(monkeypatch, 2, pc=1.0, ganadores=[0, 1], cortes=[(2, 5), (1, 3)])
    assert hijos.tolist() == [[7, 1, 2, 3, 4, 5, 6, 0], [0, 5, 3, 1, 2, 4, 6, 7]]
    assert hijos[0].tolist() == ga._ox_tramo(POB_4[0], POB_4[1], 2, 5).tolist()
    assert hijos[1].tolist() == ga._ox_tramo(POB_4[1], POB_4[0], 1, 3).tolist()
    assert ga._ox_tramo(POB_4[0], POB_4[1], 1, 3).tolist() != hijos[1].tolist()


def test_hijos_sin_cruce_ni_mutacion_son_p1_y_p2_en_orden(monkeypatch):
    """Torneos: fila 2 (P1) y fila 3 (P2), luego fila 1 y fila 0. Hijos = [P1, P2, P1', P2']."""
    hijos = _hijos_controlados(monkeypatch, 4, pc=0.0, ganadores=[2, 3, 1, 0], cortes=[])
    assert hijos.tolist() == POB_4[[2, 3, 1, 0]].tolist()


def test_hijos_cantidad_impar_descarta_el_segundo_del_ultimo_par(monkeypatch):
    """cantidad = 3: el par (fila 3, fila 2) aporta solo OX(P1, P2); no se sortean cortes para el segundo."""
    cortes = [(0, 2), (5, 7), (2, 5)]
    hijos = _hijos_controlados(monkeypatch, 3, pc=1.0, ganadores=[0, 1, 3, 2], cortes=cortes)
    assert hijos.tolist() == [
        ga._ox_tramo(POB_4[0], POB_4[1], 0, 2).tolist(),
        ga._ox_tramo(POB_4[1], POB_4[0], 5, 7).tolist(),
        ga._ox_tramo(POB_4[3], POB_4[2], 2, 5).tolist(),
    ]


def test_hijos_no_comparten_memoria_con_la_poblacion():
    poblacion = POB_4.copy()
    params = {"torneo_k": 2, "pc": 0.0, "pm": 0.0}
    hijos = ga._hijos(poblacion, np.arange(4.0), 4, params, np.random.default_rng(0))
    hijos[:] = -1
    assert np.array_equal(poblacion, POB_4)


# ------------------------------------------------------------------------------------ 8. history


def test_history():
    C = _euclidea(15, 9)
    res = ga.solve(C, _cfg(poblacion=20, generaciones=40), np.random.default_rng(1))
    h = res["history"]
    assert [e["iter"] for e in h] == list(range(40))
    costos = [e["best_cost"] for e in h]
    assert all(b <= a for a, b in zip(costos, costos[1:]))
    assert costos[-1] == res["cost"]
    assert h[-1]["best_tour"] == res["tour"]
    for e in h:
        assert e["best_cost"] == pytest.approx(_costo_a_mano(C, e["best_tour"]), rel=1e-12)
        assert type(e["best_cost"]) is float and type(e["iter"]) is int
        assert all(type(c) is int for c in e["best_tour"])
    assert costos[0] > costos[-1], "la instancia debería mejorar con las generaciones"


def test_history_coincide_con_los_estados_de_iterar():
    C = _euclidea(12, 4)
    cfg = _cfg(poblacion=10, generaciones=12)
    estados = list(ga.iterar(C, cfg, np.random.default_rng(2)))
    res = ga.solve(C, cfg, np.random.default_rng(2))
    assert len(estados) == len(res["history"]) == 12
    for estado, h in zip(estados, res["history"]):
        assert h["iter"] == estado["g"]
        assert h["best_cost"] == estado["best_cost"]
        assert h["best_tour"] == estado["best_tour"].tolist()


@pytest.mark.parametrize("clave", ["best_tour", "poblacion", "costos"])
def test_modificar_un_estado_no_afecta_a_los_siguientes(clave):
    """Cada estado cede arreglos propios: si quien consume `iterar` los modifica, las generaciones siguientes no
    cambian. Con poca mejora el mejor global se repite entre estados (el caso lo comprueba)."""
    C = _euclidea(10, 5)
    cfg = _cfg(poblacion=8, generaciones=15)
    limpios = [
        {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in e.items()}
        for e in ga.iterar(C, cfg, np.random.default_rng(3))
    ]
    assert any(np.array_equal(a["best_tour"], b["best_tour"]) for a, b in zip(limpios, limpios[1:]))
    for estado, limpio in zip(ga.iterar(C, cfg, np.random.default_rng(3)), limpios):
        for k in ("best_tour", "poblacion", "costos"):
            assert np.array_equal(estado[k], limpio[k]), (estado["g"], k)
        estado[clave][...] = 0  # el consumidor estropea el estado recibido


# -------------------------------------------------------------------------------------- 9. costo


def test_cost_es_el_costo_del_tour_con_cierre():
    C = _euclidea(11, 10)
    res = ga.solve(C, _cfg(poblacion=10, generaciones=10), np.random.default_rng(0))
    assert res["cost"] == pytest.approx(_costo_a_mano(C, res["tour"]), rel=1e-12)


def test_costos_de_la_poblacion_con_cierre():
    C = _euclidea(9, 1)
    for estado in ga.iterar(C, _cfg(poblacion=8, generaciones=3), np.random.default_rng(0)):
        esperado = [_costo_a_mano(C, fila) for fila in estado["poblacion"]]
        assert np.allclose(estado["costos"], esperado, rtol=1e-12, atol=0)


# ----------------------------------------------------------------------------- 10. reproducibilidad


def test_misma_semilla_mismo_resultado():
    C = _euclidea(20, 1)
    cfg = _cfg(poblacion=15, generaciones=20)
    np.random.seed(123)  # el estado global no debe influir
    a = ga.solve(C, cfg, np.random.default_rng(42))
    np.random.seed(999)
    b = ga.solve(C, cfg, np.random.default_rng(42))
    assert a == b


def test_semillas_distintas_dan_resultados_distintos():
    C = _euclidea(20, 1)
    cfg = _cfg(poblacion=10, generaciones=5)
    historias = {
        tuple(h["best_cost"] for h in ga.solve(C, cfg, np.random.default_rng(s))["history"]) for s in range(5)
    }
    assert len(historias) > 1


def test_solve_no_modifica_entradas():
    C = _euclidea(9, 3)
    copia = C.copy()
    cfg = _cfg(poblacion=6, generaciones=3)
    cfg_copia = {"ga": dict(cfg["ga"])}
    ga.solve(C, cfg, np.random.default_rng(0))
    assert np.array_equal(C, copia)
    assert cfg == cfg_copia


# ------------------------------------------------------------------------------- 11. validaciones


def test_valida_C_no_cuadrada():
    for C in (np.ones((3, 4)), np.ones(9)):
        with pytest.raises(ValueError, match="cuadrada"):
            ga.solve(C, _cfg(), np.random.default_rng(0))


@pytest.mark.parametrize(
    ("C", "patron"),
    [
        (np.ones((2, 2)) - np.eye(2), "n >= 3"),
        (np.where(np.eye(4, dtype=bool), 0.0, np.inf), "finit"),
        (np.where(np.eye(4, dtype=bool), 0.0, np.nan), "finit"),
        (np.array([[0, 1, 2], [1, 0, 3], [2, 3.5, 0]], dtype=float), "simétrica"),
        (np.array([[0, 0, 2], [0, 0, 3], [2, 3, 0]], dtype=float), "> 0"),
        (np.array([[0, -1, 2], [-1, 0, 3], [2, 3, 0]], dtype=float), "> 0"),
        (np.array([["a", "b", "c"]] * 3), "numérica"),
    ],
)
def test_valida_C(C, patron):
    with pytest.raises(ValueError, match=patron):
        ga.solve(C, _cfg(), np.random.default_rng(0))
    with pytest.raises(ValueError, match=patron):
        ga.iterar(C, _cfg(), np.random.default_rng(0))  # en la llamada, sin pedir el primer estado


@pytest.mark.parametrize(
    ("cambios", "error"),
    [
        ({"poblacion": 1, "torneo_k": 1, "elites": 0}, ValueError),  # el resto de claves es válido con poblacion = 1
        ({"poblacion": 20.0}, TypeError),
        ({"poblacion": True}, TypeError),
        ({"generaciones": 0}, ValueError),
        ({"generaciones": "30"}, TypeError),
        ({"torneo_k": 0}, ValueError),
        ({"torneo_k": 21}, ValueError),
        ({"torneo_k": 2.0}, TypeError),
        ({"elites": -1}, ValueError),
        ({"elites": 20}, ValueError),
        ({"elites": 1.5}, TypeError),
        ({"pc": -0.1}, ValueError),
        ({"pc": 1.1}, ValueError),
        ({"pc": float("nan")}, ValueError),
        ({"pc": "0.9"}, TypeError),
        ({"pc": True}, TypeError),
        ({"pm": -0.01}, ValueError),
        ({"pm": 1.5}, ValueError),
        ({"pm": None}, TypeError),
    ],
)
def test_valida_parametros(cambios, error):
    """El error nombra la clave que falla (la primera de `cambios`), no otra que dependa de ella."""
    clave = f"ga.{next(iter(cambios))}"
    with pytest.raises(error, match=clave):
        ga.solve(C8, _cfg(**cambios), np.random.default_rng(0))
    with pytest.raises(error, match=clave):
        ga.iterar(C8, _cfg(**cambios), np.random.default_rng(0))


@pytest.mark.parametrize(
    "cambios",
    [
        {"poblacion": 2, "torneo_k": 1, "elites": 0},
        {"poblacion": 2, "torneo_k": 2, "elites": 1},
        {"torneo_k": 20, "elites": 19},
        {"pc": 0, "pm": 1},
        {"pc": 1.0, "pm": 0.0},
        {"generaciones": 1},
        {"poblacion": np.int64(6), "torneo_k": np.int32(3)},
    ],
)
def test_limites_validos_de_los_parametros(cambios):
    cfg = _cfg(**cambios)
    res = ga.solve(C8, cfg, np.random.default_rng(0))
    p, e, g = (int(cfg["ga"][c]) for c in ("poblacion", "elites", "generaciones"))
    assert res["n_tour_evals"] == p + (p - e) * g


def test_falta_clave_de_configuracion():
    for clave in ("poblacion", "generaciones", "pc", "pm", "torneo_k", "elites"):
        cfg = _cfg()
        del cfg["ga"][clave]
        with pytest.raises(KeyError, match=f"ga.{clave}"):
            ga.solve(C8, cfg, np.random.default_rng(0))
    with pytest.raises(KeyError, match="ga"):
        ga.solve(C8, {}, np.random.default_rng(0))


def test_rng_debe_ser_generator():
    with pytest.raises(TypeError, match="Generator"):
        ga.iterar(C8, _cfg(), 0)
    with pytest.raises(TypeError, match="Generator"):
        ga.solve(C8, _cfg(), 0)


# ---------------------------------------------------------------------- piezas comunes con aco.py


def test_ga_y_aco_comparten_las_piezas_comunes():
    """§7.4.2: validación de C, costo de recorridos y vecino más cercano se reutilizan sin duplicar código."""
    assert aco._validar_matriz is recorridos.validar_matriz
    assert aco._costos is recorridos.costos_recorridos
    assert aco._vecino_mas_cercano is recorridos.vecino_mas_cercano
    assert ga._costos_recorridos is recorridos.costos_recorridos
    assert ga._vecino_mas_cercano is recorridos.vecino_mas_cercano
    assert ga._validar_matriz is recorridos.validar_matriz
    assert "src.part2.aco" not in inspect.getsource(ga)


# ----------------------------------------------------------------------------------- 12. base.yaml


def test_bloque_ga_en_base_yaml():
    """Spec §7.4 y §7.4.2: pop = 150, gen = 1 000, pc = 0.9, pm = 0.2, torneo k = 4, élites = 2."""
    bloque = load_config(BASE_PART2)["ga"]
    assert bloque == {"poblacion": 150, "generaciones": 1000, "pc": 0.9, "pm": 0.2, "torneo_k": 4, "elites": 2}
    for clave in ("poblacion", "generaciones", "torneo_k", "elites"):
        assert type(bloque[clave]) is int
    assert type(bloque["pc"]) is float and type(bloque["pm"]) is float


def test_base_yaml_funciona_con_solve():
    """El bloque de la base es aceptado por solve (con menos generaciones y población para que sea rápido)."""
    cfg = load_config(BASE_PART2)
    cfg["ga"]["poblacion"], cfg["ga"]["generaciones"] = 10, 3
    res = ga.solve(C8, cfg, np.random.default_rng(0))
    assert res["n_tour_evals"] == 10 + 8 * 3


# --------------------------------------------------------------------------------- superficie pública


def test_publicas_solo_solve_e_iterar():
    """§5.2 y §7.4.2: `ga.py` expone `solve` e `iterar`; el resto (operadores, constantes, imports) es privado."""
    assert ga.__all__ == ["solve", "iterar"]
    publicos = {nombre for nombre in vars(ga) if not nombre.startswith("_") and nombre != "annotations"}
    assert publicos == {"np", "validar_entero", "solve", "iterar"}


def test_aco_conserva_n_minimo():
    """Extraer las piezas comunes no cambia la superficie de `aco.py` (T3.3)."""
    assert aco.N_MINIMO == recorridos.N_MINIMO == 3
