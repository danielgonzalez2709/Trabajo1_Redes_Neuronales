"""Pruebas de T3.3: Ant System y MMAS para el TSP (Spec §5.2, §7.4 y §7.4.1 [DECIDIDO v1.14]).

Fuente de las fórmulas: notas del profesor, `data/raw/ACO/notas_aco.html` (§4.1, §4.2, §6, §6.1, §7.2 Prop. 2, §9).

Qué se prueba:
  1. Con 8 ciudades, MMAS y AS encuentran el óptimo de fuerza bruta (7! permutaciones con la ciudad 0 fija; notas §9).
  2. Recorridos válidos (permutaciones de 0..n-1); ruleta con p_ij ∝ W_ij y W = τ^α · η^β con la τ previa.
  3. MMAS: tras cada actualización toda τ fuera de la diagonal está en [τ_min, τ_max]; τ_max = 1/(ρ·L^bs) y
     τ_min sigue la Prop. 2 (cifras a mano).
  4. Conteo: n_tour_evals = 1 + m · iteraciones.
  5. `history`: una entrada por iteración, best_cost no creciente, mejor global y su último valor = cost.
  6. `cost` = costo recalculado del recorrido (con el arco de cierre).
  7. Reproducibilidad con `rng`.
  8. AS: depósito Δτ = Σ 1/L_k (a mano) y τ simétrica; τ₀ = m/C^nn.
  9. MMAS: en t par deposita la mejor de la iteración y en t impar la mejor global (desde τ = τ_max(C^nn)).
 10. Validaciones de C, de la variante y de los parámetros.
 11. Bloque `aco:` de `configs/part2/base.yaml`.

Las pruebas que revisan cada actualización leen los estados de `aco.iterar` (el generador que consume `solve`).
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

import numpy as np
import pytest

from src.common.config import load_config
from src.part2 import aco

ROOT = Path(__file__).resolve().parents[1]
BASE_PART2 = ROOT / "configs" / "part2" / "base.yaml"


# --------------------------------------------------------------------------------------------- auxiliares


def _cfg(variante="mmas", hormigas=8, iteraciones=60, alpha=1, beta=3, rho_as=0.5, rho_mmas=0.02, p_best=0.05):
    return {
        "aco": {
            "variante": variante,
            "hormigas": hormigas,
            "alpha": alpha,
            "beta": beta,
            "iteraciones": iteraciones,
            "as": {"rho": rho_as},
            "mmas": {"rho": rho_mmas, "p_best": p_best},
        }
    }


def _euclidea(n: int, semilla: int) -> np.ndarray:
    """Instancia euclídea con coordenadas uniformes en [0, 100]² (como en las notas, §9)."""
    xy = np.random.default_rng(semilla).uniform(0, 100, size=(n, 2))
    return np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2))


def _costo_a_mano(C: np.ndarray, tour) -> float:
    """Costo del ciclo con el arco de cierre, sumado arco por arco (independiente de aco.py)."""
    return sum(C[tour[k], tour[(k + 1) % len(tour)]] for k in range(len(tour)))


def _fuerza_bruta(C: np.ndarray) -> float:
    n = C.shape[0]
    return min(_costo_a_mano(C, (0, *resto)) for resto in itertools.permutations(range(1, n)))


def _deposito_a_mano(n: int, tours, costos) -> np.ndarray:
    """Δτ_ij = Σ_k 1/L_k sobre los arcos (no dirigidos) de cada recorrido, con el arco de cierre."""
    delta = np.zeros((n, n))
    for tour, L in zip(tours, costos):
        for k in range(n):
            a, b = tour[k], tour[(k + 1) % n]
            delta[a, b] += 1.0 / L
            delta[b, a] += 1.0 / L
    return delta


# Matriz de 4 ciudades para las cuentas a mano. Vecino más cercano desde 0: 0→1 (1), 1→2 (3), 2→3 (4), 3→0 (2):
# C^nn = 10. Recorrido 0-2-1-3: 10 + 3 + 20 + 2 = 35.
C4 = np.array([[0, 1, 10, 2], [1, 0, 3, 20], [10, 3, 0, 4], [2, 20, 4, 0]], dtype=float)

FUERA_DIAG_8 = ~np.eye(8, dtype=bool)
C8 = _euclidea(8, 7)
OPTIMO_8 = _fuerza_bruta(C8)


# ------------------------------------------------------------------------- 1. 8 ciudades = fuerza bruta


def test_instancia_de_8_ciudades_no_es_trivial():
    """El vecino más cercano no es óptimo: si lo fuera, la prueba de fuerza bruta no probaría nada."""
    _, c_nn = aco._vecino_mas_cercano(C8)
    assert c_nn > OPTIMO_8 * (1 + 1e-9)


@pytest.mark.parametrize("variante", ["mmas", "as"])
@pytest.mark.parametrize("semilla", [0, 1])
def test_8_ciudades_coincide_con_fuerza_bruta(variante, semilla):
    # Con 8 ciudades pasa aun sin actualizar la feromona (β = 3 basta); el aprendizaje lo vigilan las pruebas de
    # depósito, alternancia, τ₀ y recorte.
    res = aco.solve(C8, _cfg(variante=variante, hormigas=8, iteraciones=100), np.random.default_rng(semilla))
    assert res["cost"] == pytest.approx(OPTIMO_8, rel=1e-12)


# ---------------------------------------------------------------- 2. recorridos válidos, ruleta y pesos


@pytest.mark.parametrize("variante", ["mmas", "as"])
def test_recorrido_es_permutacion(variante):
    C = _euclidea(12, 5)
    res = aco.solve(C, _cfg(variante=variante, hormigas=6, iteraciones=15), np.random.default_rng(0))
    assert sorted(res["tour"]) == list(range(12))
    assert all(type(c) is int for c in res["tour"])
    assert type(res["cost"]) is float
    for h in res["history"]:
        assert sorted(h["best_tour"]) == list(range(12))


def test_recorridos_de_todas_las_hormigas_son_permutaciones():
    C = _euclidea(10, 2)
    for estado in aco.iterar(C, _cfg(variante="as", hormigas=9, iteraciones=5), np.random.default_rng(4)):
        assert estado["tours"].shape == (9, 10)
        assert (np.sort(estado["tours"], axis=1) == np.arange(10)).all()


def test_ruleta_respeta_las_probabilidades():
    """p_j = pesos_j / Σ pesos (notas §4.1); las columnas de peso 0 nunca salen."""
    k = 40_000
    rng = np.random.default_rng(0)
    elegidos = aco._ruleta(np.tile([1.0, 0.0, 3.0, 0.0], (k, 1)), rng)  # P(0) = 1/4, P(2) = 3/4
    assert set(np.unique(elegidos)) == {0, 2}
    assert abs(np.mean(elegidos == 2) - 0.75) < 5 * math.sqrt(0.75 * 0.25 / k)
    elegidos = aco._ruleta(np.tile([0.0, 1.0, 0.0, 1.0], (k, 1)), rng)  # P(1) = P(3) = 1/2 (incluye la última)
    assert set(np.unique(elegidos)) == {1, 3}
    assert abs(np.mean(elegidos == 3) - 0.5) < 5 * math.sqrt(0.25 / k)


def test_ciudad_inicial_uniforme():
    """Cada hormiga arranca en una ciudad uniforme al azar (Spec §7.4.1)."""
    m = 30_000
    tours = aco._construir_recorridos(np.ones((3, 3)), m, np.random.default_rng(0))
    sd = math.sqrt((1 / 3) * (2 / 3) / m)
    for ciudad in range(3):
        assert abs(np.mean(tours[:, 0] == ciudad) - 1 / 3) < 5 * sd


def test_ruleta_usa_alpha_de_la_config_a_mano():
    """AS con α = 2, β = 1, m = 5 sobre C4: τ₀ = m/C^nn = 5/10 = 0.5, así que en t = 0 W_ij = 0.5² · (1/c_ij)¹:
      W_01 = 0.25 / 1  = 0.25
      W_02 = 0.25 / 10 = 0.025
      W_03 = 0.25 / 2  = 0.125
      W_13 = 0.25 / 20 = 0.0125
    (con α = 1 saldría 0.5, 0.05, 0.25, 0.025)."""
    cfg = _cfg(variante="as", hormigas=5, iteraciones=1, alpha=2, beta=1)
    estado = next(aco.iterar(C4, cfg, np.random.default_rng(0)))
    W = estado["W"]
    assert W[0, 1] == pytest.approx(0.25, rel=1e-12)
    assert W[0, 2] == pytest.approx(0.025, rel=1e-12)
    assert W[0, 3] == pytest.approx(0.125, rel=1e-12)
    assert W[1, 3] == pytest.approx(0.0125, rel=1e-12)
    assert np.array_equal(W, W.T)


@pytest.mark.parametrize("variante", ["mmas", "as"])
def test_pesos_de_cada_iteracion_salen_de_tau_previa(variante):
    """En cada iteración t ≥ 1, W = τ^α · η^β con la τ que dejó la iteración anterior (α = 2, β = 1.5)."""
    alpha, beta = 2, 1.5
    cfg = _cfg(variante=variante, hormigas=6, iteraciones=8, alpha=alpha, beta=beta)
    estados = list(aco.iterar(C8, cfg, np.random.default_rng(1)))
    eta_beta = np.where(FUERA_DIAG_8, 1.0 / np.where(FUERA_DIAG_8, C8, 1.0), 0.0) ** beta
    for previo, estado in zip(estados, estados[1:]):
        esperado = previo["tau"] ** alpha * eta_beta
        assert np.allclose(estado["W"][FUERA_DIAG_8], esperado[FUERA_DIAG_8], rtol=1e-12, atol=0), estado["t"]


# ------------------------------------------------------------------------------- 3. límites MMAS


def test_limites_mmas_a_mano():
    """L^bs = 100, ρ = 0.02, n = 8, p_best = 0.05.

    τ_max = 1/(0.02 · 100) = 0.5.
    p_best^(1/8) = exp(ln 0.05 / 8) = exp(−2.99573227 / 8) = exp(−0.37446653) = 0.68765602
    ā = n/2 = 4 → ā − 1 = 3
    τ_min = 0.5 · (1 − 0.68765602) / (3 · 0.68765602) = 0.5 · 0.31234398 / 2.06296807 = 0.5 · 0.15140514 = 0.07570257
    """
    tau_min, tau_max = aco._limites_mmas(L_bs=100.0, rho=0.02, n=8, p_best=0.05)
    assert tau_max == pytest.approx(0.5, rel=1e-12)
    assert tau_min == pytest.approx(0.07570257, rel=1e-7)


def test_limites_mmas_a_mano_otro_caso():
    """L^bs = 40, ρ = 0.5, n = 10, p_best = 0.5.

    τ_max = 1/(0.5 · 40) = 0.05.
    p_best^(1/10) = 0.5^0.1 = 0.93303299; ā − 1 = 4
    τ_min = 0.05 · 0.06696701 / (4 · 0.93303299) = 0.05 · 0.06696701 / 3.73213197 = 0.05 · 0.01794337 = 0.00089717
    """
    tau_min, tau_max = aco._limites_mmas(L_bs=40.0, rho=0.5, n=10, p_best=0.5)
    assert tau_max == pytest.approx(0.05, rel=1e-12)
    assert tau_min == pytest.approx(0.00089717, rel=1e-5)


def test_solve_usa_p_best_de_la_config():
    """MMAS, n = 8, p_best = 0.2: límites con que se recorta cada iteración (estados de `iterar`, que consume `solve`).

    p_best^(1/8) = exp(ln 0.2 / 8) = exp(−1.60943791 / 8) = exp(−0.20117974) = 0.81776543; ā − 1 = 3
    τ_min / τ_max = (1 − 0.81776543) / (3 · 0.81776543) = 0.18223457 / 2.45329630 = 0.07428151
    (con p_best = 0.05 la razón sería 0.15140514). Además τ_max = 1/(ρ · L^bs) con el costo final de `solve`.
    """
    rho = 0.1
    cfg = _cfg(variante="mmas", hormigas=8, iteraciones=10, rho_mmas=rho, p_best=0.2)
    estados = list(aco.iterar(C8, cfg, np.random.default_rng(0)))
    res = aco.solve(C8, cfg, np.random.default_rng(0))
    assert len(estados) == 10
    for estado in estados:
        assert estado["tau_min"] / estado["tau_max"] == pytest.approx(0.07428151, rel=1e-7)
    assert estados[-1]["tau_max"] == pytest.approx(1.0 / (rho * res["cost"]), rel=1e-12)
    assert estados[-1]["tau_min"] == pytest.approx(0.07428151 / (rho * res["cost"]), rel=1e-7)


def test_mmas_feromona_dentro_de_los_limites_tras_cada_actualizacion():
    rho, p_best = 0.1, 0.05  # ρ alto para que el recorte inferior se active en pocas iteraciones
    cfg = _cfg(variante="mmas", hormigas=8, iteraciones=80, rho_mmas=rho, p_best=p_best)
    toco_min = False
    for estado in aco.iterar(C8, cfg, np.random.default_rng(3)):
        tau, tmin, tmax = estado["tau"], estado["tau_min"], estado["tau_max"]
        assert tmax == pytest.approx(1.0 / (rho * estado["best_cost"]), rel=1e-12)
        esperado_min, _ = aco._limites_mmas(estado["best_cost"], rho, 8, p_best)
        assert tmin == pytest.approx(esperado_min, rel=1e-12)
        fuera = tau[FUERA_DIAG_8]
        assert (fuera >= tmin).all() and (fuera <= tmax).all()
        assert np.array_equal(tau, tau.T)
        toco_min |= bool((fuera == tmin).any())
    assert toco_min, "el recorte inferior nunca se activó: la prueba no ejercita τ_min"


def test_mmas_rechaza_limites_invertidos():
    """Con n = 4 y p_best = 0.05, la Prop. 2 da τ_min > τ_max (p^(1/4) = 0.4729; razón 1.115): ValueError (§7.4.1)
    en la llamada a `iterar`, sin esperar al primer estado. AS sí funciona con n = 4."""
    cfg = _cfg(variante="mmas", hormigas=4, iteraciones=2)
    with pytest.raises(ValueError, match="τ_min"):
        aco.iterar(C4, cfg, np.random.default_rng(0))
    with pytest.raises(ValueError, match="τ_min"):
        aco.solve(C4, cfg, np.random.default_rng(0))
    aco.solve(C4, _cfg(variante="as", hormigas=4, iteraciones=2), np.random.default_rng(0))


# -------------------------------------------------------------------------------------- 4. conteo


@pytest.mark.parametrize(("variante", "m", "iteraciones"), [("mmas", 5, 7), ("as", 3, 12)])
def test_conteo_de_recorridos(variante, m, iteraciones):
    res = aco.solve(C8, _cfg(variante=variante, hormigas=m, iteraciones=iteraciones), np.random.default_rng(0))
    assert res["n_tour_evals"] == 1 + m * iteraciones
    assert type(res["n_tour_evals"]) is int


# ------------------------------------------------------------------------------------ 5. history


@pytest.mark.parametrize("variante", ["mmas", "as"])
def test_history(variante):
    C = _euclidea(15, 9)
    res = aco.solve(C, _cfg(variante=variante, hormigas=10, iteraciones=40), np.random.default_rng(1))
    h = res["history"]
    assert [e["iter"] for e in h] == list(range(40))
    costos = [e["best_cost"] for e in h]
    assert all(b <= a for a, b in zip(costos, costos[1:]))
    assert costos[-1] == res["cost"]
    assert h[-1]["best_tour"] == res["tour"]
    for e in h:
        assert e["best_cost"] == pytest.approx(_costo_a_mano(C, e["best_tour"]), rel=1e-12)
        assert type(e["best_cost"]) is float and type(e["iter"]) is int
    assert costos[0] > costos[-1], "la instancia debería mejorar con las iteraciones"


def test_history_registra_el_mejor_global_de_cada_iteracion():
    C = _euclidea(12, 4)
    cfg = _cfg(variante="as", hormigas=6, iteraciones=20)
    estados = list(aco.iterar(C, cfg, np.random.default_rng(2)))
    res = aco.solve(C, cfg, np.random.default_rng(2))
    _, mejor = aco._vecino_mas_cercano(C)
    for estado, h in zip(estados, res["history"]):
        mejor = min(mejor, float(np.min(estado["costos"])))
        assert h["best_cost"] == pytest.approx(mejor, rel=1e-12)


# -------------------------------------------------------------------------------------- 6. costo


def test_costos_incluyen_el_arco_de_cierre():
    tours = np.array([[0, 1, 2, 3], [0, 2, 1, 3]])
    # 0-1-2-3-0: 1 + 3 + 4 + 2 = 10; 0-2-1-3-0: 10 + 3 + 20 + 2 = 35
    assert aco._costos(C4, tours).tolist() == [10.0, 35.0]


def test_vecino_mas_cercano_a_mano():
    """Desde 0: el más cercano es 1 (1), desde 1 es 2 (3), desde 2 queda 3 (4), cierre 3→0 (2): C^nn = 10."""
    tour, c_nn = aco._vecino_mas_cercano(C4)
    assert list(tour) == [0, 1, 2, 3]
    assert c_nn == 10.0


def test_vecino_mas_cercano_no_toma_el_minimo_global():
    """Desde 0 va a 2 (1); desde 2 el más cercano no visitado es 3 (2); luego 1; cierre 1→0 (9). C^nn = 1+2+5+9 = 17."""
    C = np.array([[0, 9, 1, 8], [9, 0, 6, 5], [1, 6, 0, 2], [8, 5, 2, 0]], dtype=float)
    tour, c_nn = aco._vecino_mas_cercano(C)
    assert list(tour) == [0, 2, 3, 1]
    assert c_nn == 17.0


# ----------------------------------------------------------------------------- 7. reproducibilidad


def test_misma_semilla_mismo_resultado():
    C = _euclidea(20, 1)
    for variante in ["mmas", "as"]:
        cfg = _cfg(variante=variante, hormigas=10, iteraciones=15)
        np.random.seed(123)  # el estado global no debe influir
        a = aco.solve(C, cfg, np.random.default_rng(42))
        np.random.seed(999)
        b = aco.solve(C, cfg, np.random.default_rng(42))
        assert a == b, variante


def test_semillas_distintas_dan_resultados_distintos():
    C = _euclidea(20, 1)
    cfg = _cfg(variante="mmas", hormigas=10, iteraciones=5)
    historias = {
        tuple(h["best_cost"] for h in aco.solve(C, cfg, np.random.default_rng(s))["history"]) for s in range(5)
    }
    assert len(historias) > 1


def test_solve_no_modifica_entradas():
    C = _euclidea(9, 3)
    copia = C.copy()
    cfg = _cfg(variante="mmas", hormigas=5, iteraciones=3)
    cfg_copia = {"aco": {**cfg["aco"], "as": dict(cfg["aco"]["as"]), "mmas": dict(cfg["aco"]["mmas"])}}
    aco.solve(C, cfg, np.random.default_rng(0))
    assert np.array_equal(C, copia)
    assert cfg == cfg_copia


# ------------------------------------------------------------------------------- 8. depósito de AS


def test_deposito_as_a_mano():
    """τ = 1 en todos los arcos, ρ = 0.5; T¹ = 0-1-2-3 (L = 10), T² = 0-2-1-3 (L = 20).

    Evaporación: 1 → 0.5. Depósitos 1/10 = 0.1 y 1/20 = 0.05:
      {0,1}: T¹         → 0.5 + 0.1        = 0.60
      {1,2}: T¹ y T²    → 0.5 + 0.1 + 0.05 = 0.65
      {2,3}: T¹         → 0.60
      {3,0}: T¹ y T²    → 0.65
      {0,2}: T²         → 0.55
      {1,3}: T²         → 0.55
      diagonal          → 0.50 (solo evapora)
    """
    tau = np.ones((4, 4))
    tours = np.array([[0, 1, 2, 3], [0, 2, 1, 3]])
    nuevo = aco._actualizar_as(tau, tours, np.array([10.0, 20.0]), rho=0.5)
    esperado = np.array(
        [
            [0.50, 0.60, 0.55, 0.65],
            [0.60, 0.50, 0.65, 0.55],
            [0.55, 0.65, 0.50, 0.60],
            [0.65, 0.55, 0.60, 0.50],
        ]
    )
    assert np.allclose(nuevo, esperado, rtol=0, atol=1e-15)
    assert np.array_equal(nuevo, nuevo.T)
    assert np.array_equal(tau, np.ones((4, 4)))  # no modifica la entrada


def test_actualizacion_mmas_a_mano():
    """τ = 0.5, ρ = 0.1, T = 0-1-2-3 con L = 4 (Δ = 0.25), límites [0.3, 0.6].

    Arcos de T: 0.9 · 0.5 + 0.25 = 0.70 → recorte a 0.6. Resto: 0.45 → sin recorte. Con τ = 0.32 fuera de T:
    0.9 · 0.32 = 0.288 → recorte a 0.3.
    """
    tau = np.full((4, 4), 0.5)
    tau[0, 2] = tau[2, 0] = 0.32
    nuevo = aco._actualizar_mmas(tau, np.array([0, 1, 2, 3]), 4.0, rho=0.1, tau_min=0.3, tau_max=0.6)
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
        assert nuevo[a, b] == nuevo[b, a] == 0.6
    assert nuevo[1, 3] == nuevo[3, 1] == pytest.approx(0.45)
    assert nuevo[0, 2] == nuevo[2, 0] == 0.3


def test_as_iteracion_completa_tau0_y_deposito_de_todas_las_hormigas():
    """τ₀ = m/C^nn; cada iteración τ ← (1 − ρ)τ + Σ_k 1/L_k en τ_ij y τ_ji (notas §4.2)."""
    m, rho = 6, 0.5
    C = _euclidea(9, 8)
    _, c_nn = aco._vecino_mas_cercano(C)
    previo = np.full((9, 9), m / c_nn)
    fuera = ~np.eye(9, dtype=bool)
    for estado in aco.iterar(C, _cfg(variante="as", hormigas=m, iteraciones=6, rho_as=rho), np.random.default_rng(7)):
        esperado = (1 - rho) * previo + _deposito_a_mano(9, estado["tours"], estado["costos"])
        assert np.allclose(estado["tau"][fuera], esperado[fuera], rtol=1e-12, atol=0)
        assert np.array_equal(estado["tau"], estado["tau"].T)
        assert estado["tau_min"] is None and estado["tau_max"] is None
        previo = estado["tau"]


# ---------------------------------------------------------------------------- 9. alternancia MMAS


def test_mmas_alterna_mejor_de_la_iteracion_y_mejor_global():
    """Desde τ = τ_max(C^nn) = 1/(ρ C^nn) (inicialización, notas §6), cada iteración recorta
    (1 − ρ)τ + Δτ con T^ib si t es par y T^bs si t es impar."""
    rho = 0.05
    C = _euclidea(10, 3)
    cfg = _cfg(variante="mmas", hormigas=5, iteraciones=40, rho_mmas=rho)
    _, c_nn = aco._vecino_mas_cercano(C)
    previo = np.full((10, 10), 1.0 / (rho * c_nn))
    fuera = ~np.eye(10, dtype=bool)
    discrimina = {0: 0, 1: 0}  # iteraciones (por paridad) en las que T^ib y T^bs dejan τ distintas
    for estado in aco.iterar(C, cfg, np.random.default_rng(0)):
        t = estado["t"]
        k = int(np.argmin(estado["costos"]))
        ib = (estado["tours"][k], estado["costos"][k])
        bs = (estado["best_tour"], estado["best_cost"])
        candidatos = {}
        for nombre, (tour, L) in (("ib", ib), ("bs", bs)):
            x = (1 - rho) * previo + _deposito_a_mano(10, [tour], [L])
            candidatos[nombre] = np.clip(x, estado["tau_min"], estado["tau_max"])
        elegido = "ib" if t % 2 == 0 else "bs"
        otro = "bs" if elegido == "ib" else "ib"
        assert np.allclose(estado["tau"][fuera], candidatos[elegido][fuera], rtol=1e-12, atol=0), t
        if not np.allclose(candidatos[otro][fuera], candidatos[elegido][fuera], rtol=1e-9, atol=0):
            discrimina[t % 2] += 1
        previo = estado["tau"]
    assert discrimina[0] > 0 and discrimina[1] > 0, f"el caso no distingue T^ib de T^bs: {discrimina}"


# ------------------------------------------------------------------------------- 10. validaciones


def test_valida_C_no_cuadrada():
    for C in (np.ones((3, 4)), np.ones(9)):
        with pytest.raises(ValueError, match="cuadrada"):
            aco.solve(C, _cfg(), np.random.default_rng(0))


@pytest.mark.parametrize(
    ("C", "patron"),
    [
        (np.ones((2, 2)) - np.eye(2), "n >= 3"),
        (np.where(np.eye(4, dtype=bool), 0.0, np.inf), "finit"),
        (np.where(np.eye(4, dtype=bool), 0.0, np.nan), "finit"),
        (np.array([[0, 1, 2], [1, 0, 3], [2, 3.5, 0]], dtype=float), "simétrica"),
        (np.array([[0, 0, 2], [0, 0, 3], [2, 3, 0]], dtype=float), "> 0"),
        (np.array([[0, -1, 2], [-1, 0, 3], [2, 3, 0]], dtype=float), "> 0"),
    ],
)
def test_valida_C(C, patron):
    with pytest.raises(ValueError, match=patron):
        aco.solve(C, _cfg(), np.random.default_rng(0))


def test_valida_C_no_numerica():
    with pytest.raises(ValueError, match="numérica"):
        aco.solve(np.array([["a", "b", "c"]] * 3), _cfg(), np.random.default_rng(0))


def test_valida_variante():
    with pytest.raises(ValueError, match="variante"):
        aco.solve(C8, _cfg(variante="acs"), np.random.default_rng(0))


@pytest.mark.parametrize(
    ("cambios", "error"),
    [
        ({"hormigas": 0}, ValueError),
        ({"hormigas": 2.5}, TypeError),
        ({"iteraciones": 0}, ValueError),
        ({"alpha": -1}, ValueError),
        ({"beta": float("nan")}, ValueError),
        ({"beta": "3"}, TypeError),
        ({"rho_mmas": 0.0}, ValueError),
        ({"rho_mmas": 1.5}, ValueError),
        ({"rho_as": 0.0}, ValueError),
        ({"p_best": 0.0}, ValueError),
        ({"p_best": 1.0}, ValueError),
    ],
)
def test_valida_parametros(cambios, error):
    with pytest.raises(error):
        aco.solve(C8, _cfg(**cambios), np.random.default_rng(0))


@pytest.mark.parametrize("variante", ["mmas", "as"])
def test_rho_igual_a_uno_es_valido(variante):
    """0 < ρ ≤ 1 (notas §4.2): ρ = 1 se acepta. Con m = 1 AS no puede quedarse sin pesos: τ solo es > 0 en los arcos
    del recorrido anterior, que forman un ciclo hamiltoniano, y la hormiga siempre puede seguirlo."""
    res = aco.solve(C8, _cfg(variante=variante, hormigas=1, iteraciones=5, rho_as=1.0, rho_mmas=1.0),
                    np.random.default_rng(0))
    assert res["n_tour_evals"] == 1 + 1 * 5


def test_ruleta_con_pesos_nulos_falla_con_error_claro():
    """Una fila con peso 0 en todas las columnas (p_j = 0/0, sin definir) → FloatingPointError, no un índice
    inválido."""
    pesos = np.array([[0.0, 1.0, 0.0, 2.0], [0.0, 0.0, 0.0, 0.0]])
    with pytest.raises(FloatingPointError, match="ruleta"):
        aco._ruleta(pesos, np.random.default_rng(0))


def test_falta_clave_de_configuracion():
    cfg = _cfg()
    del cfg["aco"]["mmas"]["p_best"]
    with pytest.raises(KeyError, match="aco.mmas.p_best"):
        aco.solve(C8, cfg, np.random.default_rng(0))
    with pytest.raises(KeyError, match="aco"):
        aco.solve(C8, {}, np.random.default_rng(0))


def test_rng_debe_ser_generator():
    with pytest.raises(TypeError, match="Generator"):
        aco.iterar(C8, _cfg(), 0)  # error en la llamada, sin pedir el primer estado
    with pytest.raises(TypeError, match="Generator"):
        aco.solve(C8, _cfg(), 0)


# ----------------------------------------------------------------------------------- 11. base.yaml


def test_bloque_aco_en_base_yaml():
    """Spec §7.4 y §7.4.1 [DECIDIDO]: MMAS principal; m = 47, α = 1, β = 3; ρ AS 0.5 y MMAS 0.02; p_best 0.05.
    `iteraciones` es provisional (§7.4: T3.6 fija el presupuesto común): solo se exige entero positivo."""
    bloque = load_config(BASE_PART2)["aco"]
    assert set(bloque) == {"variante", "hormigas", "alpha", "beta", "iteraciones", "as", "mmas"}
    assert bloque["variante"] == "mmas"
    assert bloque["hormigas"] == 47
    assert bloque["alpha"] == 1 and bloque["beta"] == 3
    assert bloque["as"] == {"rho": 0.5}
    assert bloque["mmas"] == {"rho": 0.02, "p_best": 0.05}
    assert type(bloque["iteraciones"]) is int and bloque["iteraciones"] > 0


def test_base_yaml_funciona_con_solve():
    """El bloque de la base es aceptado por solve (con menos iteraciones para que sea rápido)."""
    cfg = load_config(BASE_PART2)
    cfg["aco"]["hormigas"], cfg["aco"]["iteraciones"] = 8, 3
    res = aco.solve(C8, cfg, np.random.default_rng(0))
    assert res["n_tour_evals"] == 1 + 8 * 3
