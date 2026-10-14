"""Pruebas del óptimo exacto (T3.2, src/part2/exact.py): coincide con la fuerza bruta y con el barrido de T3.6."""
import itertools
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.part2 import costos as cs
from src.part2.exact import resolver_exacto, solve

RAIZ = Path(__file__).resolve().parents[1]


def _simetrica(n, semilla):
    rng = np.random.default_rng(semilla)
    puntos = rng.uniform(0, 100, size=(n, 2))
    C = np.linalg.norm(puntos[:, None, :] - puntos[None, :, :], axis=2)
    return C


def _fuerza_bruta(C):
    n = len(C)
    return min(sum(C[p[k], p[(k + 1) % n]] for k in range(n)) for p in itertools.permutations(range(n)) if p[0] == 0)


@pytest.mark.parametrize("n, semilla", [(5, 0), (6, 1), (7, 2), (8, 3), (8, 4)])
def test_coincide_con_la_fuerza_bruta(n, semilla):
    C = _simetrica(n, semilla)
    tour, costo, _ = resolver_exacto(C)
    assert sorted(tour) == list(range(n)) and tour[0] == 0
    assert costo == pytest.approx(sum(C[tour[k], tour[(k + 1) % n]] for k in range(n)))
    assert costo == pytest.approx(_fuerza_bruta(C), abs=1e-9)


def test_agrega_restricciones_de_subtour_cuando_hacen_falta():
    # Dos grupos lejanos: la relajación de grado 2 forma dos triángulos y obliga a cortar subtours.
    puntos = np.array([[0, 0], [1, 0], [0, 1], [100, 100], [101, 100], [100, 101]], dtype=float)
    C = np.linalg.norm(puntos[:, None, :] - puntos[None, :, :], axis=2)
    tour, costo, resoluciones = resolver_exacto(C)
    assert resoluciones >= 2
    assert costo == pytest.approx(_fuerza_bruta(C))


def test_solve_respeta_el_contrato_de_la_parte2():
    r = solve(_simetrica(6, 7), {}, None)
    assert set(r) == {"tour", "cost", "n_tour_evals", "history"}
    assert r["n_tour_evals"] == 0 and r["history"][0]["best_cost"] == r["cost"]


def test_menos_de_tres_ciudades_falla():
    with pytest.raises(ValueError):
        resolver_exacto(np.zeros((2, 2)))


def test_optimo_con_los_datos_reales_coincide_con_el_barrido_en_w25():
    """En w = 25 €/h el mejor costo del barrido de T3.6 es el óptimo (verificación del 13-oct)."""
    comp = cs.cargar_componentes(RAIZ / "data" / "processed")
    vehiculo = yaml.safe_load((RAIZ / "data/processed/vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((RAIZ / "data/processed/combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    barrido = json.loads((RAIZ / "results/data/part2/sweep_w.json").read_text(encoding="utf-8"))
    mejor_w25 = next(e["cost"] for e in barrido if e["w"] == 25)
    C, _ = cs.matriz_costos(comp, 25, vehiculo, precio)
    assert resolver_exacto(C)[1] == pytest.approx(mejor_w25, abs=1e-6)


# --- umbrales exactos (scripts/umbrales_exactos.py -> results/data/part2/umbrales_exactos.json) ---------------------

EXACTOS = RAIZ / "results" / "data" / "part2" / "umbrales_exactos.json"


def _exactos():
    if not EXACTOS.exists():
        pytest.skip("falta results/data/part2/umbrales_exactos.json (python scripts/umbrales_exactos.py)")
    return json.loads(EXACTOS.read_text(encoding="utf-8"))


def test_envolvente_exacta_conserva_los_ids_de_t36_y_cubre_el_rango():
    base = json.loads((RAIZ / "results/data/part2/umbrales_w.json").read_text(encoding="utf-8"))
    e = _exactos()["consumos"]["4.6"]["envolvente"]
    n = len(base["candidatos"])
    assert [c["tour"] for c in e["candidatos"][:n]] == [c["tour"] for c in base["candidatos"]]
    assert all(not c["exacto_nuevo"] for c in e["candidatos"][:n]) and all(c["exacto_nuevo"] for c in e["candidatos"][n:])
    iv = e["intervalos"]
    assert iv[0]["w_desde"] == 0.0 and iv[-1]["w_hasta"] == 100.0
    assert all(a["w_hasta"] == b["w_desde"] and a["candidato"] != b["candidato"] for a, b in zip(iv, iv[1:]))
    assert [round(u["w"], 2) for u in e["umbrales"]] == [10.02, 14.53, 42.19]


def test_en_cada_tramo_el_ganador_de_la_envolvente_exacta_es_el_optimo():
    comp = cs.cargar_componentes(RAIZ / "data" / "processed")
    vehiculo = yaml.safe_load((RAIZ / "data/processed/vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((RAIZ / "data/processed/combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    e = _exactos()["consumos"]["4.6"]["envolvente"]
    for i in e["intervalos"]:
        w = (i["w_desde"] + i["w_hasta"]) / 2
        C, _ = cs.matriz_costos(comp, w, vehiculo, precio)
        tour = e["candidatos"][i["candidato"]]["tour"]
        assert sum(C[tour[k], tour[(k + 1) % len(tour)]] for k in range(len(tour))) == pytest.approx(
            resolver_exacto(C)[1], rel=1e-9)


def test_el_mapa_usa_la_envolvente_exacta():
    from src.viz import part2_interactivas as pi

    _exactos()
    entradas = pi.cargar_entradas()
    assert [round(u["w"], 2) for u in entradas["umbrales"]["umbrales"]] == [10.02, 14.53, 42.19]
    pasos = pi.pasos_mapa(entradas)
    assert any(p["exacto_nuevo"] for p in pasos) and not any(p["exacto_nuevo"] for p in pasos if p["en_barrido"])


def test_el_mejor_costo_del_barrido_es_el_optimo_en_los_11_w():
    """El gap de T3.6 se mide contra el mejor costo conocido; aquí se comprueba que es el óptimo en cada w."""
    comp = cs.cargar_componentes(RAIZ / "data" / "processed")
    vehiculo = yaml.safe_load((RAIZ / "data/processed/vehiculo.yaml").read_text(encoding="utf-8"))
    precio = json.loads((RAIZ / "data/processed/combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"]
    barrido = json.loads((RAIZ / "results/data/part2/sweep_w.json").read_text(encoding="utf-8"))
    assert len(barrido) == 11
    for fila in barrido:
        C, _ = cs.matriz_costos(comp, fila["w"], vehiculo, precio)
        assert resolver_exacto(C)[1] == pytest.approx(fila["cost"], abs=1e-6), fila["w"]
