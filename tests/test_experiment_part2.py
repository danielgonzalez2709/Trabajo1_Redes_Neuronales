"""Pruebas de T3.6: experimento de la Parte 2 (Spec §7.4 "Comparación justa", §7.5 y §5.3/§5.4).

La envolvente, la canonicalización y el costo por rectas se prueban en tests/test_envolvente.py.

Qué se prueba:
  1. Desglose del mejor recorrido (desempate en `rapida`; alternativa `sin_peaje` elegida).
  4. Gap y estadísticas con valores a mano; fila de `sweep_w.json` (gap de la media) con costos dados.
  5. Presupuesto común: con `base.yaml` ACO y GA dan 51 654 recorridos; una config desigual es un error.
  6. Claves `costo.consumo_l100` y `costo.precio_l`: null = archivos; override proporcional; inválidas → error.
  7. Extremo a extremo con config diminuta y datos reales: JSON de §5.3/§5.4, reproducibles, y la sensibilidad no
     sobrescribe la salida base (también con otra rejilla de w); etiqueta de la carpeta de sensibilidad.
  8. `run.py part2` con config inválida falla antes de correr (no escribe nada); la CLI importa el experimento
     solo al usar part2.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from src.common import cli
from src.common.config import apply_overrides, load_config
from src.common.results import load_json, save_json
from src.part2 import experiment as ex
from src.part2.costos import Componentes, matriz_costos
from src.part2.envolvente import canonico, costo_recorrido
from src.part2.recorridos import costos_recorridos
from tests.sinteticos_part2 import A, B, UNO, comp, comp_trozos, rectas_unitarias

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
BASE_PART2 = ROOT / "configs" / "part2" / "base.yaml"
SWEEP = ROOT / "configs" / "part2" / "sweep_w.yaml"
DEMO = ROOT / "configs" / "part2" / "demo.yaml"
SENSIBILIDAD = ROOT / "configs" / "part2" / "sensibilidad_consumo.yaml"

CLAVES_CONTRATO = {"w", "tour", "cost", "desglose", "km_peaje", "cambio_vs_anterior", "gap_aco", "gap_ga"}


@pytest.fixture(scope="module")
def datos():
    return ex.cargar_datos(PROC)


# --------------------------------------------------------------------------------------------- 1. desglose


def test_desglose_suma_el_costo_y_respeta_el_desempate():
    """Arco 12 empata en w = 8 (rápida 8 € + 1 h = 16; sin peaje 0 € + 2 h = 16): se elige `rapida` (§7.3), así que
    el desglose lleva 8 € de peaje y 8 € de tiempo en ese arco, no 0 € y 16 €."""
    componentes = comp({(0, 1): UNO, (1, 2): (8.0, 1.0), (2, 3): UNO, (0, 3): UNO}, {(1, 2): (0.0, 2.0)})
    km = np.zeros((4, 4))
    km[1, 2] = km[2, 1] = 30.0  # km con peaje solo en la rápida del arco 12
    datos_sint = ex.Datos(comp=componentes, km_peaje_rapida=km, km_peaje_sin_peaje=np.zeros((4, 4)),
                          consumo_l100=4.6, precio_l=1.8)
    d = ex.desglose(datos_sint, A, 8.0, 4.6, 1.8)
    assert d["peajes"] == 8.0 and d["tiempo"] == 8.0 * 4 and d["combustible"] == 0.0
    assert d["km_peaje"] == 30.0
    assert d["tiempo"] + d["peajes"] + d["combustible"] == costo_recorrido(rectas_unitarias(componentes), A, 8.0)


def test_desglose_toma_km_peaje_y_peaje_de_la_alternativa_sin_peaje_cuando_se_elige():
    """Arco 12 en w = 4: rápida 8 € + 1 h = 12, sin peaje 3 € + 1,5 h = 9 → se elige `sin_peaje` (como en los 26 pares
    cuya sin peaje también paga, §7.2 Bloque 2). Su peaje (3 €) y sus km con peaje (5) son los que cuentan, no los de
    la rápida (8 € y 30 km)."""
    componentes = comp({(0, 1): UNO, (1, 2): (8.0, 1.0), (2, 3): UNO, (0, 3): UNO}, {(1, 2): (3.0, 1.5)})
    km_r, km_s = np.zeros((4, 4)), np.zeros((4, 4))
    km_r[1, 2] = km_r[2, 1] = 30.0
    km_s[1, 2] = km_s[2, 1] = 5.0
    datos_sint = ex.Datos(comp=componentes, km_peaje_rapida=km_r, km_peaje_sin_peaje=km_s, consumo_l100=4.6,
                          precio_l=1.8)
    d = ex.desglose(datos_sint, A, 4.0, 4.6, 1.8)
    assert d["km_peaje"] == 5.0
    assert d["peajes"] == 3.0 and d["tiempo"] == 4.0 * 4.5


# --------------------------------------------------------------------------------- 4. gap y estadísticas


def test_gap_y_estadisticas_a_mano():
    assert ex.gap(12.0, 10.0) == pytest.approx(20.0)
    assert ex.gap(10.0, 10.0) == 0.0
    est = ex.estadisticas([14.0, 10.0, 12.0], mejor=8.0)
    assert est["n"] == 3
    assert est["mejor"] == 10.0 and est["media"] == 12.0
    assert est["desviacion"] == pytest.approx(2.0)  # n − 1: sqrt(((2² + 2² + 0²) / 2)) = 2 (con n sería 1,633)
    assert est["gap_mejor"] == pytest.approx(25.0) and est["gap_media"] == pytest.approx(50.0)


def test_estadisticas_con_una_corrida_no_tienen_desviacion():
    est = ex.estadisticas([10.0], mejor=10.0)
    assert est["desviacion"] is None and est["gap_mejor"] == 0.0


D_FILA = {"tiempo": 1.0, "peajes": 2.0, "combustible": 1.5, "km_peaje": 7.0}


def test_fila_sweep_gap_aco_y_gap_ga_son_el_gap_de_la_media():
    """Mejor encontrado 4,5. MMAS: 4,5 y 23,5 (media 14); GA: 4,5 y 23 (media 13,75). gap_aco = 100·(14 − 4,5)/4,5 y
    gap_ga = 100·(13,75 − 4,5)/4,5; el gap del mejor (0) va en `metodos`. AS no entra en gap_aco."""
    costos = {"mmas": [4.5, 23.5], "as": [10.0, 12.0], "ga": [4.5, 23.0]}
    fila = ex._fila_sweep(1.0, A, 4.5, 3, costos, D_FILA, anterior=B)
    assert fila["gap_aco"] == pytest.approx(100 * (14.0 - 4.5) / 4.5)
    assert fila["gap_ga"] == pytest.approx(100 * (13.75 - 4.5) / 4.5)
    assert fila["metodos"]["mmas"]["gap_mejor"] == 0.0 and fila["metodos"]["ga"]["gap_mejor"] == 0.0
    assert list(fila["metodos"]) == ["mmas", "as", "ga"]
    assert fila["tour"] == list(A) and fila["cost"] == 4.5 and fila["candidato"] == 3
    assert fila["desglose"] == {"tiempo": 1.0, "peajes": 2.0, "combustible": 1.5} and fila["km_peaje"] == 7.0
    assert fila["cambio_vs_anterior"] is True


def test_fila_sweep_sin_mmas_ni_ga_y_cambio_vs_anterior():
    fila = ex._fila_sweep(1.0, A, 4.5, 0, {"as": [4.5, 5.0]}, D_FILA, anterior=None)
    assert fila["gap_aco"] is None and fila["gap_ga"] is None and fila["cambio_vs_anterior"] is None
    assert ex._fila_sweep(1.0, A, 4.5, 0, {"as": [4.5]}, D_FILA, anterior=A)["cambio_vs_anterior"] is False


# -------------------------------------------------------------------------------------- 5. presupuesto


def test_presupuesto_comun_de_la_base():
    """Spec §7.4 [DECIDIDO v1.16]: 51 654 = 1 + 47 · 1 099 = 150 + 148 · 348."""
    base = load_config(BASE_PART2)
    assert base["aco"]["iteraciones"] == 1099 and base["ga"]["generaciones"] == 348
    assert ex.presupuesto_recorridos(base) == (51_654, 51_654)
    assert ex.comprobar_presupuesto(base) == 51_654


def test_presupuesto_desigual_es_error():
    cfg = apply_overrides(load_config(BASE_PART2), ["aco.iteraciones=1000"])
    with pytest.raises(ValueError, match=r"47 001.*51 654|presupuesto"):
        ex.comprobar_presupuesto(cfg)


# ---------------------------------------------------------------------------- 6. consumo_l100 y precio_l


def test_consumo_y_precio_null_son_los_de_los_archivos(datos):
    base = load_config(BASE_PART2)
    assert base["costo"]["consumo_l100"] is None and base["costo"]["precio_l"] is None
    assert ex.consumo_y_precio(base, datos) == (4.6, 1.8318)  # vehiculo.yaml y combustible.json (T2.6, T2.7)


def test_override_de_consumo_y_precio(datos):
    cfg = apply_overrides(load_config(BASE_PART2), ["costo.consumo_l100=5.6", "costo.precio_l=1.9"])
    assert ex.consumo_y_precio(cfg, datos) == (5.6, 1.9)


def test_el_combustible_es_proporcional_al_consumo():
    """Una sola alternativa por arco (sin cambios de elección): el combustible escala con consumo × precio."""
    componentes = comp({(0, 1): UNO, (1, 2): UNO, (2, 3): UNO, (0, 3): UNO})
    componentes = Componentes(**{**componentes.__dict__, "dist_km_rapida": np.full((4, 4), 100.0),
                          "dist_km_sin_peaje": np.full((4, 4), 100.0)})
    datos_sint = ex.Datos(comp=componentes, km_peaje_rapida=np.zeros((4, 4)), km_peaje_sin_peaje=np.zeros((4, 4)),
                          consumo_l100=4.6, precio_l=2.0)
    base = ex.desglose(datos_sint, A, 25.0, 4.6, 2.0)["combustible"]
    assert base == pytest.approx(4 * 100 * 0.046 * 2.0)
    assert ex.desglose(datos_sint, A, 25.0, 5.6, 2.0)["combustible"] == pytest.approx(base * 5.6 / 4.6)
    assert ex.desglose(datos_sint, A, 25.0, 4.6, 3.0)["combustible"] == pytest.approx(base * 1.5)


@pytest.mark.parametrize("clave", ["consumo_l100", "precio_l"])
@pytest.mark.parametrize("valor", ["0", "-1", "abc", ".inf", "true"])
def test_consumo_o_precio_invalidos_son_error(datos, clave, valor):
    cfg = apply_overrides(load_config(BASE_PART2), [f"costo.{clave}={valor}"])
    with pytest.raises((ValueError, TypeError), match=clave):
        ex.consumo_y_precio(cfg, datos)


# ------------------------------------------------------------------------------- semillas (run_id)


def test_run_id_unico_por_w_solver_y_corrida():
    ids = [ex.run_id(i_w, s, r, runs=10) for i_w in range(11) for s in ex.SOLVERS for r in range(10)]
    assert len(set(ids)) == len(ids) == 330
    assert min(ids) == 0 and max(ids) == 329


# ------------------------------------------------------------------------------- 7. extremo a extremo

DIMINUTA = [
    "costo.valor_hora=[0, 25]", "runs=2",
    "aco.hormigas=4", "aco.iteraciones=5",  # 1 + 4 · 5 = 21
    "ga.poblacion=5", "ga.elites=1", "ga.generaciones=4",  # 5 + 4 · 4 = 21
]


def _cfg_diminuta(salida: Path, extra: list[str] | None = None) -> dict:
    return apply_overrides(load_config(SWEEP), [*DIMINUTA, f"experimento.salida={salida.as_posix()}", *(extra or [])])


def _leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def corrida_base(tmp_path_factory):
    salida = tmp_path_factory.mktemp("base")
    ex.ejecutar(_cfg_diminuta(salida))
    return salida


def test_e2e_escribe_los_archivos_del_contrato(corrida_base):
    nombres = {p.name for p in corrida_base.iterdir()}
    assert nombres == {"sweep_w.json", "umbrales_w.json", "history_aco_w0.json", "history_aco_w25.json",
                       "history_ga_w0.json", "history_ga_w25.json"}


def test_e2e_historiales_compactos_y_el_resto_con_sangria(corrida_base):
    """Decisión de Jose Miguel (12-oct): los historiales van sin sangría (una línea) y cargan igual con load_json;
    sweep_w.json y umbrales_w.json siguen con indent=2."""
    for nombre in ("history_aco_w0.json", "history_aco_w25.json", "history_ga_w0.json", "history_ga_w25.json"):
        texto = (corrida_base / nombre).read_bytes().decode("utf-8")
        assert texto.count("\n") == 1 and texto.endswith("\n") and ", " not in texto
        assert load_json(corrida_base / nombre) == json.loads(texto)
    for nombre in ("sweep_w.json", "umbrales_w.json"):
        assert "\n  " in (corrida_base / nombre).read_bytes().decode("utf-8")


def test_e2e_sweep_w_con_la_forma_de_5_4(corrida_base):
    sweep = _leer(corrida_base / "sweep_w.json")
    assert [e["w"] for e in sweep] == [0, 25]
    for k, e in enumerate(sweep):
        assert CLAVES_CONTRATO <= set(e)
        assert sorted(e["tour"]) == list(range(47)) and e["tour"][0] == 0
        assert set(e["desglose"]) == {"tiempo", "peajes", "combustible"}
        assert sum(e["desglose"].values()) == pytest.approx(e["cost"], rel=1e-12)
        assert e["km_peaje"] >= 0
        assert e["cambio_vs_anterior"] is None if k == 0 else isinstance(e["cambio_vs_anterior"], bool)
        # El mejor encontrado es <= que toda corrida en ese w; gap >= 0 y gap_aco es el de MMAS.
        for metodo in ("mmas", "as", "ga"):
            m = e["metodos"][metodo]
            assert m["n"] == 2 and m["mejor"] >= e["cost"] - 1e-9 and m["gap_mejor"] >= 0
        assert e["gap_aco"] == e["metodos"]["mmas"]["gap_media"]
        assert e["gap_ga"] == e["metodos"]["ga"]["gap_media"]
    assert sweep[0]["desglose"]["tiempo"] == 0.0  # w = 0
    assert sweep[1]["cambio_vs_anterior"] == (sweep[1]["tour"] != sweep[0]["tour"])


def test_e2e_mejor_encontrado_es_el_minimo_de_todos_los_candidatos(corrida_base, datos):
    """En cada w, `cost` es el mínimo de TODOS los candidatos (de cualquier w), no solo de las corridas de ese w."""
    sweep = _leer(corrida_base / "sweep_w.json")
    tours = np.array([c["tour"] for c in _leer(corrida_base / "umbrales_w.json")["candidatos"]])
    for e in sweep:
        Cw, _ = matriz_costos(datos.comp, e["w"], {"consumo_wltp_comb_l100": datos.consumo_l100}, datos.precio_l)
        costos = costos_recorridos(Cw, tours)
        assert e["cost"] == costos.min() and tuple(e["tour"]) == tuple(tours[costos.argmin()])


def test_e2e_umbrales_e_historiales(corrida_base):
    umb = _leer(corrida_base / "umbrales_w.json")
    assert umb["rango_w"] == [0, 25]
    assert {"candidatos", "intervalos", "umbrales", "consumo_l100", "precio_l", "nota"} <= set(umb)
    assert umb["intervalos"][0]["w_desde"] == 0 and umb["intervalos"][-1]["w_hasta"] == 25
    tours = [tuple(c["tour"]) for c in umb["candidatos"]]
    assert len(set(tours)) == len(tours) and all(t == canonico(t) for t in tours)
    # 2 w × 3 métodos × 2 corridas = 12 hallazgos repartidos entre los candidatos
    assert sum(len(c["hallado_en"]) for c in umb["candidatos"]) == 12

    hist = _leer(corrida_base / "history_aco_w25.json")
    assert hist["w"] == 25 and set(hist["variantes"]) == {"mmas", "as"}
    corridas = hist["variantes"]["mmas"]["corridas"]
    assert len(corridas) == 2
    for c in corridas:
        assert {"run_id", "seed", "cost", "tour", "n_tour_evals", "best_cost", "mejoras",
                "recorridos_iniciales", "recorridos_por_iter"} <= set(c)
        assert c["n_tour_evals"] == 21 and len(c["best_cost"]) == 5
        assert c["mejoras"][0]["iter"] == 0 and c["mejoras"][-1]["best_tour"] == c["tour"]
        assert all(a["best_tour"] != b["best_tour"] for a, b in zip(c["mejoras"], c["mejoras"][1:]))
        assert [m["best_cost"] for m in c["mejoras"]] == [c["best_cost"][m["iter"]] for m in c["mejoras"]]
    ga_hist = _leer(corrida_base / "history_ga_w0.json")
    assert set(ga_hist["variantes"]) == {"ga"}
    assert ga_hist["variantes"]["ga"]["corridas"][0]["n_tour_evals"] == 21
    semillas = [c["seed"] for v in (hist, ga_hist) for var in v["variantes"].values() for c in var["corridas"]]
    assert len(set(semillas)) == len(semillas)


def test_e2e_cada_corrida_se_reproduce_con_su_semilla_y_su_variante(corrida_base, datos):
    """Primera corrida de cada solver en w = 25: `solve` con la semilla registrada y la variante del solver da el
    mismo recorrido y costo (MMAS y AS no se confunden)."""
    from src.part2 import aco, ga

    cfg = _cfg_diminuta(corrida_base)
    Cw, _ = matriz_costos(datos.comp, 25.0, {"consumo_wltp_comb_l100": datos.consumo_l100}, datos.precio_l)
    for familia, solver, solve in (("aco", "mmas", aco.solve), ("aco", "as", aco.solve), ("ga", "ga", ga.solve)):
        corrida = _leer(corrida_base / f"history_{familia}_w25.json")["variantes"][solver]["corridas"][0]
        cfg_s = apply_overrides(cfg, [f"aco.variante={solver}"] if familia == "aco" else [])
        res = solve(Cw, cfg_s, np.random.default_rng(corrida["seed"]))
        assert (res["tour"], res["cost"]) == (corrida["tour"], corrida["cost"])


def test_correr_con_datos_sinteticos_y_umbral_conocido(tmp_path):
    """Plan con los arcos a trozos de arriba (4 ciudades): A gana en w = 1 y B en w = 100; el umbral es 14 y la fila
    de w = 100 marca el cambio de recorrido. (w = 0 no se usa porque C tendría costos 0 fuera de la diagonal.)"""
    ceros = np.zeros((4, 4))
    datos_sint = ex.Datos(comp=comp_trozos(), km_peaje_rapida=ceros, km_peaje_sin_peaje=ceros, consumo_l100=1.0,
                          precio_l=1.0)
    cfg = apply_overrides(load_config(BASE_PART2), ["aco.hormigas=4", "aco.iteraciones=5", "ga.poblacion=5",
                                                    "ga.elites=1", "ga.generaciones=4"])
    plan = ex.Plan(cfg=cfg, w=[1.0, 100.0], solvers=("as", "ga"), runs=1, base_seed=0, datos=datos_sint,
                   consumo_l100=1.0, precio_l=1.0, salida=tmp_path, base=None)
    ex.correr(plan)
    sweep = _leer(tmp_path / "sweep_w.json")
    assert [tuple(e["tour"]) for e in sweep] == [A, B]
    assert [e["cost"] for e in sweep] == [pytest.approx(4.5), pytest.approx(320.0)]
    assert [e["cambio_vs_anterior"] for e in sweep] == [None, True]
    assert sweep[0]["gap_aco"] is None  # sin MMAS no hay gap_aco
    umb = _leer(tmp_path / "umbrales_w.json")
    assert [u["w"] for u in umb["umbrales"]] == [pytest.approx(14.0, abs=1e-12)]


def test_e2e_reproducible_con_la_misma_semilla(corrida_base, tmp_path):
    ex.ejecutar(_cfg_diminuta(tmp_path))
    for nombre in ("sweep_w.json", "history_aco_w25.json", "history_ga_w0.json"):
        assert (tmp_path / nombre).read_bytes() == (corrida_base / nombre).read_bytes()
    a, b = _leer(tmp_path / "umbrales_w.json"), _leer(corrida_base / "umbrales_w.json")
    a.pop("config"), b.pop("config")  # solo difiere experimento.salida
    assert a == b


def test_e2e_sensibilidad_no_sobrescribe_la_base(tmp_path):
    base = tmp_path / "base"
    ex.ejecutar(_cfg_diminuta(base))
    antes = {p.name: p.read_bytes() for p in base.iterdir()}
    cfg = apply_overrides(load_config(SENSIBILIDAD), [*DIMINUTA, f"experimento.salida={base.as_posix()}"])
    destino = ex.ejecutar(cfg)
    assert destino == base / "sensibilidad" / "consumo5.6"
    assert {p.name: p.read_bytes() for p in base.iterdir() if p.is_file()} == antes
    nombres = {p.name for p in destino.iterdir()}
    assert nombres == {"sweep_w.json", "umbrales_w.json", "comparacion_base.json",
                       "history_aco_w0.json", "history_aco_w25.json"}
    hist = _leer(destino / "history_aco_w25.json")
    assert set(hist["variantes"]) == {"mmas"}  # solo MMAS (§7.5)
    # Mismas semillas que el MMAS de la base (números aleatorios comunes).
    hist_base = _leer(base / "history_aco_w25.json")
    assert [c["seed"] for c in hist["variantes"]["mmas"]["corridas"]] == \
        [c["seed"] for c in hist_base["variantes"]["mmas"]["corridas"]]
    # La envolvente usa la unión: todos los candidatos de la base están en la de sensibilidad.
    cand_base = {tuple(c["tour"]) for c in _leer(base / "umbrales_w.json")["candidatos"]}
    cand_sens = {tuple(c["tour"]) for c in _leer(destino / "umbrales_w.json")["candidatos"]}
    assert cand_base <= cand_sens
    comp = _leer(destino / "comparacion_base.json")
    assert "\n  " in (destino / "comparacion_base.json").read_bytes().decode("utf-8")  # sigue con sangría
    assert (destino / "history_aco_w25.json").read_bytes().count(b"\n") == 1  # compacto
    assert comp["consumo_l100"] == {"base": 4.6, "sensibilidad": 5.6}
    assert [fila["w"] for fila in comp["por_w"]] == [0, 25]
    for fila in comp["por_w"]:
        for lado in ("base", "sensibilidad"):
            assert set(fila[lado]) == {"cost", "combustible", "tour"} and fila[lado]["combustible"] > 0
        assert fila["mismo_recorrido"] == (fila["base"]["tour"] == fila["sensibilidad"]["tour"])
    assert {"base", "sensibilidad", "mismos_ganadores"} <= set(comp["umbrales"])
    sweep_sens = _leer(destino / "sweep_w.json")
    assert all(e["gap_ga"] is None for e in sweep_sens)


def test_sensibilidad_con_otra_rejilla_de_w(tmp_path):
    """Sensibilidad en w = 0 y 10 sobre una base en w = 0 y 25: la comparación tiene la base solo en w = 0."""
    base = tmp_path / "base"
    ex.ejecutar(_cfg_diminuta(base))
    cfg = apply_overrides(load_config(SENSIBILIDAD),
                          [*DIMINUTA, "costo.valor_hora=[0, 10]", f"experimento.salida={base.as_posix()}"])
    destino = ex.ejecutar(cfg)
    assert _leer(destino / "umbrales_w.json")["rango_w"] == [0, 10]
    w0, w10 = _leer(destino / "comparacion_base.json")["por_w"]
    assert w0["w"] == 0 and w0["base"] is not None and isinstance(w0["mismo_recorrido"], bool)
    assert w10["w"] == 10 and w10["base"] is None and w10["mismo_recorrido"] is None


@pytest.mark.parametrize(
    ("sets", "carpeta"),
    [
        (["costo.precio_l=1.9"], "precio1.9"),
        (["costo.consumo_l100=5.6", "costo.precio_l=1.9"], "consumo5.6_precio1.9"),
        (["costo.consumo_l100=6"], "consumo6"),
    ],
)
def test_etiqueta_de_la_carpeta_de_sensibilidad(tmp_path, sets, carpeta):
    """La sensibilidad solo necesita que existan los archivos del barrido base para preparar el plan."""
    save_json(tmp_path / "sweep_w.json", [])
    save_json(tmp_path / "umbrales_w.json", {})
    cfg = apply_overrides(load_config(SWEEP), [*DIMINUTA, f"experimento.salida={tmp_path.as_posix()}", *sets])
    plan = ex.preparar(cfg)
    assert plan.salida == tmp_path / "sensibilidad" / carpeta and plan.base is not None


def test_sensibilidad_sin_barrido_base_es_error(tmp_path):
    cfg = apply_overrides(load_config(SENSIBILIDAD), [*DIMINUTA, f"experimento.salida={tmp_path.as_posix()}"])
    with pytest.raises(FileNotFoundError, match="barrido base"):
        ex.preparar(cfg)


# ------------------------------------------------------------------------- 8. run.py part2 y validación


def test_part2_conecta_el_manejador_real(monkeypatch):
    recibido = {}

    def falso(cfg):
        recibido["cfg"] = cfg
        return 7

    monkeypatch.setattr(ex, "main", falso)
    assert cli.SUBCOMANDOS["part2"].manejador({"x": 1}) == 7 and recibido["cfg"] == {"x": 1}


def test_cargar_la_cli_no_importa_el_experimento():
    """Import perezoso: `src.common.cli` no carga `src.part2.experiment` hasta que se usa part2."""
    codigo = "import sys, src.common.cli; print('src.part2.experiment' in sys.modules)"
    res = subprocess.run([sys.executable, "-c", codigo], cwd=ROOT, capture_output=True, encoding="utf-8", check=True)
    assert res.stdout.strip() == "False"


@pytest.mark.parametrize(
    ("override", "fragmento"),
    [
        ("aco.alpha=abc", "aco.alpha"),
        ("ga.pc=1.5", "ga.pc"),
        ("runs=0", "runs"),
        ("costo.valor_hora=[0, 10, 5]", "valor_hora"),
        ("costo.valor_hora=.inf", "valor_hora"),
        ("costo.consumo_l100=-4", "consumo_l100"),
        ("methods=[aco, ga, exacto]", "exacto"),
        ("experimento.variantes_aco=[mmas, acs]", "variantes_aco"),
        ("ga.generaciones=5", "presupuesto"),  # 5 + 4 · 5 = 25 ≠ 21
    ],
)
def test_run_py_part2_con_config_invalida_falla_antes_de_correr(tmp_path, capsys, override, fragmento):
    """Sobre la config diminuta: si la validación fallara, la corrida sería corta y la prueba fallaría por el código."""
    sets = [*DIMINUTA, f"experimento.salida={tmp_path.as_posix()}", override]
    argv = ["part2", "--config", str(SWEEP), *(x for s in sets for x in ("--set", s))]
    assert cli.main(argv) == 2
    assert fragmento in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_preparar_valida_toda_la_config_sin_correr(tmp_path):
    plan = ex.preparar(_cfg_diminuta(tmp_path))
    assert plan.w == [0.0, 25.0] and plan.solvers == ("mmas", "as", "ga")
    assert list(tmp_path.iterdir()) == []


def test_la_demo_no_escribe_en_la_salida_del_barrido():
    """La demo (T3.7) hereda de base.yaml: con la misma salida sobrescribiría sweep_w.json del barrido."""
    demo, sweep = load_config(DEMO)["experimento"]["salida"], load_config(SWEEP)["experimento"]["salida"]
    assert demo != sweep and demo == "results/data/part2/demo"


def test_preparar_acepta_la_config_base_sin_exacto(tmp_path):
    """Spec v1.14: el exacto es opcional y no existe; `base.yaml` (methods sin exacto) pasa la validación."""
    cfg = apply_overrides(load_config(BASE_PART2), [f"experimento.salida={tmp_path.as_posix()}"])
    assert ex.preparar(cfg).solvers == ("mmas", "as", "ga")


def test_configs_del_repo():
    sweep = load_config(SWEEP)
    assert sweep["costo"]["valor_hora"] == [0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100]  # §7.5
    assert sweep["methods"] == ["aco", "ga"] and sweep["runs"] == 10
    assert sweep["experimento"]["variantes_aco"] == ["mmas", "as"]
    sens = load_config(SENSIBILIDAD)
    assert sens["methods"] == ["aco"] and sens["experimento"]["variantes_aco"] == ["mmas"]
    assert sens["costo"]["consumo_l100"] == 5.6  # §7.5: 5,6 (y 6,2 con --set)
    assert sens["costo"]["valor_hora"] == sweep["costo"]["valor_hora"]
