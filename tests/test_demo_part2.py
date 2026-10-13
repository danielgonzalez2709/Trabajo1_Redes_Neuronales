"""Pruebas de T3.7: demo de la Parte 2 (Spec §7.7, [DECIDIDO v1.17]).

Qué se prueba:
  1. `configs/part2/demo.yaml`: MMAS (variante principal, §7.4.1), w = 25, 100 iteraciones, salida propia y
     referencia del gap = `results/data/part2/sweep_w.json`.
  2. Referencia del gap: el mejor costo conocido de `sweep_w.json` en el w de la demo; error claro si falta el archivo,
     falta la entrada de ese w o la referencia no corresponde al modelo de costo actual (no se inventa una referencia).
  3. Extremo a extremo con una demo diminuta y datos reales: gap frente a la referencia, desglose, figura PNG,
     reproducible con la misma semilla, salida en consola rotulada "mejor conocido".
  4. La demo no escribe nada fuera de su carpeta de salida (en particular, no toca el barrido de results/data/part2).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.common import cli
from src.common.config import apply_overrides, load_config
from src.common.results import save_json
from src.part2 import experiment as ex
from src.part2.costos import matriz_costos

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "configs" / "part2" / "demo.yaml"
SWEEP_REAL = ROOT / "results" / "data" / "part2" / "sweep_w.json"
RESULTADOS_PART2 = ROOT / "results" / "data" / "part2"
PNG = b"\x89PNG\r\n\x1a\n"

# Demo diminuta (rápida en las pruebas); la demo real (10 × 100 iteraciones) se mide aparte.
DIMINUTA = ["runs=2", "aco.hormigas=4", "aco.iteraciones=5"]  # 2 × (1 + 4 · 5) = 42 recorridos


def _leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def _cfg_demo(salida: Path, extra: list[str] | None = None) -> dict:
    return apply_overrides(load_config(DEMO), [*DIMINUTA, f"experimento.salida={salida.as_posix()}", *(extra or [])])


@pytest.fixture(scope="module")
def datos():
    return ex.cargar_datos(ROOT / "data" / "processed")


def _matriz(datos, w: float) -> np.ndarray:
    C, _ = matriz_costos(datos.comp, w, {"consumo_wltp_comb_l100": datos.consumo_l100}, datos.precio_l)
    return C


def _entrada_real(w: float) -> dict:
    return next(e for e in _leer(SWEEP_REAL) if e["w"] == w)


# ------------------------------------------------------------------------------------------- 1. config


def test_demo_yaml_corre_solo_mmas_con_w_25_y_100_iteraciones():
    demo = load_config(DEMO)
    assert demo["methods"] == ["aco"] and demo["experimento"]["variantes_aco"] == ["mmas"]  # §7.4.1: principal
    assert demo["costo"]["valor_hora"] == 25 and demo["aco"]["iteraciones"] == 100  # §7.7
    assert demo["experimento"]["salida"] == "results/data/part2/demo"
    assert demo["experimento"]["referencia_gap"] == "results/data/part2/sweep_w.json"  # §7.7 [DECIDIDO v1.17]


def test_la_base_y_el_barrido_no_son_demo():
    for nombre in ("base.yaml", "sweep_w.yaml", "sensibilidad_consumo.yaml"):
        assert load_config(ROOT / "configs" / "part2" / nombre)["experimento"]["referencia_gap"] is None


def test_preparar_la_demo_carga_la_referencia(tmp_path):
    plan = ex.preparar(_cfg_demo(tmp_path))
    assert plan.solvers == ("mmas",) and plan.w == [25.0] and plan.salida == tmp_path
    ref = _entrada_real(25)
    assert plan.referencia["cost"] == ref["cost"] and plan.referencia["w"] == 25.0
    assert plan.referencia["tour"] == ref["tour"]
    assert list(tmp_path.iterdir()) == []  # preparar no escribe


# ------------------------------------------------------------------------------------ 2. referencia


def test_referencia_es_la_entrada_del_mismo_w(datos):
    """Con --set costo.valor_hora=30 la referencia es la de w = 30, no la de 25."""
    ref = ex.leer_referencia(SWEEP_REAL, 30.0, _matriz(datos, 30.0))
    assert ref["cost"] == _entrada_real(30)["cost"] and ref["w"] == 30.0


def test_referencia_sin_archivo_es_error(tmp_path, datos):
    with pytest.raises(FileNotFoundError, match="referencia del gap"):
        ex.leer_referencia(tmp_path / "sweep_w.json", 25.0, _matriz(datos, 25.0))


def test_referencia_sin_la_entrada_del_w_es_error(tmp_path, datos):
    sweep = [e for e in _leer(SWEEP_REAL) if e["w"] != 25]
    save_json(tmp_path / "sweep_w.json", sweep)
    with pytest.raises(ValueError, match="w = 25"):
        ex.leer_referencia(tmp_path / "sweep_w.json", 25.0, _matriz(datos, 25.0))


def test_referencia_que_no_corresponde_al_modelo_de_costo_es_error(tmp_path, datos):
    """Si el costo guardado no es el del recorrido con la matriz actual (otros datos, consumo o precio), la
    referencia no sirve: error en lugar de un gap engañoso."""
    sweep = _leer(SWEEP_REAL)
    for e in sweep:
        if e["w"] == 25:
            e["cost"] = e["cost"] * 0.9
    save_json(tmp_path / "sweep_w.json", sweep)
    with pytest.raises(ValueError, match="no corresponde"):
        ex.leer_referencia(tmp_path / "sweep_w.json", 25.0, _matriz(datos, 25.0))


def test_referencia_con_recorrido_invalido_es_error(tmp_path, datos):
    sweep = _leer(SWEEP_REAL)
    for e in sweep:
        if e["w"] == 25:
            e["tour"] = e["tour"][:-1] + [e["tour"][0]]  # ciudad repetida
    save_json(tmp_path / "sweep_w.json", sweep)
    with pytest.raises(ValueError, match="permutación"):
        ex.leer_referencia(tmp_path / "sweep_w.json", 25.0, _matriz(datos, 25.0))


def test_demo_con_varios_w_es_error(tmp_path):
    with pytest.raises(ValueError, match="un solo valor"):
        ex.preparar(_cfg_demo(tmp_path, ["costo.valor_hora=[20, 25]"]))


def test_demo_con_consumo_distinto_es_error(tmp_path):
    """La referencia del barrido base se calculó con 4,6 l/100 km: con 5,6 el gap no sería comparable."""
    with pytest.raises(ValueError, match="no corresponde"):
        ex.preparar(_cfg_demo(tmp_path, ["costo.consumo_l100=5.6"]))


def test_run_py_demo_sin_referencia_falla_antes_de_correr(tmp_path, capsys):
    salida = tmp_path / "demo"
    sets = [*DIMINUTA, f"experimento.salida={salida.as_posix()}",
            f"experimento.referencia_gap={(tmp_path / 'no_existe.json').as_posix()}"]
    argv = ["part2", "--config", str(DEMO), *(x for s in sets for x in ("--set", s))]
    assert cli.main(argv) == 2
    assert "referencia del gap" in capsys.readouterr().err
    assert not salida.exists()


# ------------------------------------------------------------------------------- 3. extremo a extremo


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    salida = tmp_path_factory.mktemp("demo")
    ex.ejecutar(_cfg_demo(salida))
    return salida


def test_demo_escribe_solo_su_resumen_y_la_figura(demo):
    assert {p.name for p in demo.iterdir()} == {"demo.json", "recorrido_w25.png"}
    assert (demo / "recorrido_w25.png").read_bytes()[:8] == PNG


CLAVES_DEMO = {  # contrato de demo.json, Spec §5.4 [DECIDIDO v1.17]
    "w", "solvers", "tour", "cost", "desglose", "km_peaje", "arcos_con_peaje", "referencia", "gap_mejor_conocido",
    "metodos", "n_tour_evals", "figura", "nota", "semillas", "config",
}


def test_demo_json_tiene_exactamente_las_claves_del_contrato(demo):
    """Ni una clave de más ni una de menos frente a Spec §5.4."""
    assert set(_leer(demo / "demo.json")) == CLAVES_DEMO


def test_demo_gap_frente_al_mejor_conocido(demo, datos):
    res = _leer(demo / "demo.json")
    ref = _entrada_real(25)
    assert res["referencia"]["cost"] == ref["cost"] and res["referencia"]["archivo"].endswith("sweep_w.json")
    assert res["gap_mejor_conocido"] == pytest.approx(100 * (res["cost"] - ref["cost"]) / ref["cost"], rel=1e-12)
    m = res["metodos"]["mmas"]
    assert m["n"] == 2 and m["mejor"] == res["cost"]
    assert m["gap_mejor"] == res["gap_mejor_conocido"]
    assert m["gap_media"] == pytest.approx(100 * (m["media"] - ref["cost"]) / ref["cost"], rel=1e-12)
    assert "mejor conocido" in res["nota"]
    # Mejor recorrido: permutación válida cuyo costo con la matriz de w = 25 es `cost` y cuyo desglose suma `cost`.
    tour = np.array(res["tour"])
    assert sorted(res["tour"]) == list(range(47))
    C = _matriz(datos, 25.0)
    assert C[tour, np.roll(tour, -1)].sum() == pytest.approx(res["cost"], rel=1e-12)
    assert set(res["desglose"]) == {"tiempo", "peajes", "combustible"}
    assert sum(res["desglose"].values()) == pytest.approx(res["cost"], rel=1e-12)
    assert res["n_tour_evals"] == 2 * (1 + 4 * 5)
    assert res["figura"] == "recorrido_w25.png"


def test_demo_reproducible_con_la_misma_semilla(demo, tmp_path):
    ex.ejecutar(_cfg_demo(tmp_path))
    a, b = _leer(demo / "demo.json"), _leer(tmp_path / "demo.json")
    a.pop("config"), b.pop("config")  # solo difiere experimento.salida
    assert a == b


def test_demo_salida_en_consola(tmp_path, capsys):
    ex.ejecutar(_cfg_demo(tmp_path))
    out = capsys.readouterr().out
    assert "mejor conocido" in out and "óptimo" not in out
    for fragmento in ("Tiempo", "Peajes", "Combustible", "Recorridos evaluados", "recorrido_w25.png", "Gap"):
        assert fragmento in out
    assert "Umbrales" not in out  # no es la salida del barrido


def test_figura_recorrido_no_cambia_el_backend_ni_el_estilo_global(tmp_path):
    import matplotlib as mpl

    from src.viz.part2_figs import figura_recorrido

    backend, rc = mpl.get_backend(), dict(mpl.rcParams)
    ruta = figura_recorrido([0, 1, 1, 0], [40, 40, 41, 41], [0, 1, 2, 3], [False, True, False, False],
                            "Título", "Subtítulo", tmp_path / "sub" / "f.png")
    assert ruta.read_bytes()[:8] == PNG
    assert mpl.get_backend() == backend and dict(mpl.rcParams) == rc


def test_figura_recorrido_exige_un_valor_de_peaje_por_arco(tmp_path):
    from src.viz.part2_figs import figura_recorrido

    with pytest.raises(ValueError, match="con_peaje"):
        figura_recorrido([0, 1, 1], [40, 40, 41], [0, 1, 2], [False, True], "T", "S", tmp_path / "f.png")


def test_arcos_con_peaje_de_la_demo_coinciden_con_el_desglose(demo, datos):
    """Los arcos marcados con peaje en la figura son los que suman los peajes del desglose."""
    res = _leer(demo / "demo.json")
    arcos = ex.arcos(datos, res["tour"], 25.0, datos.consumo_l100, datos.precio_l)
    assert arcos["peajes"].sum() == pytest.approx(res["desglose"]["peajes"], rel=1e-12)
    assert res["arcos_con_peaje"] == int((arcos["peajes"] > 0).sum())


# ------------------------------------------------------------------------- 4. no escribe fuera de su salida


def _foto(carpeta: Path, excluir: Path | None = None) -> dict:
    return {p.relative_to(carpeta).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in carpeta.rglob("*") if p.is_file() and (excluir is None or excluir not in p.parents)}


def test_run_py_demo_no_escribe_fuera_de_su_salida(tmp_path):
    """La demo lee la referencia real (results/data/part2/sweep_w.json) pero no toca nada del barrido ni escribe fuera
    de experimento.salida."""
    salida = tmp_path / "salida"
    antes_resultados = _foto(RESULTADOS_PART2, excluir=RESULTADOS_PART2 / "demo")
    antes_tmp = _foto(tmp_path)
    sets = [*DIMINUTA, f"experimento.salida={salida.as_posix()}"]
    assert cli.main(["part2", "--config", str(DEMO), *(x for s in sets for x in ("--set", s))]) == 0
    assert _foto(RESULTADOS_PART2, excluir=RESULTADOS_PART2 / "demo") == antes_resultados
    despues_tmp = _foto(tmp_path)
    nuevos = set(despues_tmp) - set(antes_tmp)
    assert nuevos == {"salida/demo.json", "salida/recorrido_w25.png"}
