"""Pruebas de `src/part1/eta_deslizador.py` (T4.2-A; Spec §6.7 punto 5: deslizador de η).

Grupos:

    1. rejilla de η          -> extremos, 4 por década, orden, sin duplicados, marcas
    2. submuestreo           -> índices geométricos con el primero y el último
    3. datos del deslizador  -> contrato del JSON, x0 común, la marca `defecto` reproduce la corrida
    4. guardado y script     -> el JSON se relee igual, sin NaN/inf; envoltorio de `scripts/`
    5. archivo real          -> coincide con la corrida guardada (skip si no existe)

Las corridas usan un presupuesto pequeño (`PRESUPUESTO` por dimensión); la configuración es la
real: `configs/part1/base.yaml`.
"""

from __future__ import annotations

import copy
import math
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from src.common.config import load_config
from src.common.results import load_json, run_filename
from src.part1 import eta_deslizador as ed
from src.part1.corrida import ejecutar_corrida

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_BASE = RAIZ / "configs" / "part1" / "base.yaml"
CONFIG_AFINADA = RAIZ / "configs" / "part1" / "tuned.yaml"
SCRIPT = RAIZ / "scripts" / "part1_eta_deslizador.py"
PRESUPUESTO = 40            # por dimensión: 80 evaluaciones equivalentes = 20 gradientes en 2D
ETA_AFINADO = 1.5e-3        # valor de prueba, distinto del de defecto y fuera de la rejilla
CLAVES_META = {"func", "dim", "method", "seed", "k", "budget", "x0", "puntos_max"}
CLAVES_ETA = {"eta", "marca", "f_best", "n_grad", "n_iter", "iteraciones", "puntos"}


def cfg_pequena() -> dict:
    cfg = load_config(CONFIG_BASE)
    cfg["presupuesto_por_dim"] = PRESUPUESTO
    return cfg


def cfg_con_eta(eta: float) -> dict:
    cfg = cfg_pequena()
    cfg["gd"]["eta"]["rosenbrock"] = eta
    return cfg


@pytest.fixture(scope="module")
def datos() -> dict:
    return ed.construir_datos(cfg_pequena(), cfg_con_eta(ETA_AFINADO))


def marcas(entradas) -> list:
    return [e[1] if isinstance(e, tuple) else e["marca"] for e in entradas]


# ---------------------------------------------------------------- 1. rejilla de η
def test_rejilla_extremos_incluidos_y_cuatro_por_decada():
    valores = ed.rejilla_eta(1e-5, 1e-2)
    assert valores[0] == 1e-5 and valores[-1] == 1e-2
    assert len(valores) == 3 * ed.PUNTOS_POR_DECADA + 1
    for a, b in zip(valores, valores[1:]):
        assert b / a == pytest.approx(10 ** (1 / ed.PUNTOS_POR_DECADA), rel=1e-12)


def test_rejilla_rechaza_intervalos_invalidos():
    for minimo, maximo in ((0.0, 1e-2), (1e-2, 1e-5), (1e-3, 1e-3), (-1.0, 1.0), (1e-3, math.inf)):
        with pytest.raises(ValueError):
            ed.rejilla_eta(minimo, maximo)


def test_valores_con_defecto_en_la_rejilla_no_se_duplica():
    valores = ed.valores_eta(1e-5, 1e-2, defecto=1e-3)
    etas = [v for v, _ in valores]
    assert len(etas) == 13                                  # 1e-3 ya es un punto de la rejilla
    assert etas == sorted(etas) and len(set(etas)) == len(etas)
    assert marcas(valores).count(ed.MARCA_DEFECTO) == 1
    assert ed.MARCA_AFINADO not in marcas(valores)
    assert (1e-3, ed.MARCA_DEFECTO) in valores              # lleva el valor exacto de la config


def test_valores_con_afinado_fuera_de_la_rejilla_se_anade_ordenado():
    valores = ed.valores_eta(1e-5, 1e-2, defecto=1e-3, afinado=ETA_AFINADO)
    etas = [v for v, _ in valores]
    assert len(etas) == 14 and etas == sorted(etas)
    assert marcas(valores).count(ed.MARCA_DEFECTO) == 1
    assert marcas(valores).count(ed.MARCA_AFINADO) == 1
    assert (ETA_AFINADO, ed.MARCA_AFINADO) in valores


def test_valores_con_afinado_igual_al_defecto_no_lo_marca():
    valores = ed.valores_eta(1e-5, 1e-2, defecto=1e-3, afinado=1e-3)
    assert ed.MARCA_AFINADO not in marcas(valores) and len(valores) == 13


def test_valores_con_defecto_fuera_de_la_rejilla_se_anade():
    valores = ed.valores_eta(1e-5, 1e-2, defecto=2e-3)
    assert len(valores) == 14 and (2e-3, ed.MARCA_DEFECTO) in valores
    assert [v for v, _ in valores] == sorted(v for v, _ in valores)


# ---------------------------------------------------------------- 2. submuestreo
@pytest.mark.parametrize("n_iter", [0, 1, 2, 5, 149, 150, 151, 500, 5000, 123_457])
@pytest.mark.parametrize("puntos_max", [2, 3, 10, 150])
def test_indices_submuestreo(n_iter, puntos_max):
    indices = ed.indices_submuestreo(n_iter, puntos_max)
    assert indices[0] == 0 and indices[-1] == n_iter
    assert all(isinstance(i, int) for i in indices)
    assert all(a < b for a, b in zip(indices, indices[1:]))
    assert len(indices) <= puntos_max
    if n_iter + 1 <= puntos_max:
        assert indices == list(range(n_iter + 1))           # cabe entera: no se submuestrea


def test_indices_submuestreo_es_geometrico():
    indices = ed.indices_submuestreo(5000, 150)
    saltos = [b - a for a, b in zip(indices, indices[1:])]
    assert saltos[0] == 1 and saltos[-1] > saltos[0]         # denso al principio, ralo al final
    # el redondeo al entero puede alterar un salto en 1: se compara cada salto con el anterior - 1
    assert all(a - 1 <= b for a, b in zip(saltos, saltos[1:]))
    razones = [b / a for a, b in zip(indices[60:], indices[61:])]      # lejos del redondeo
    assert max(razones) / min(razones) < 1.05                # razón casi constante: geométrico


def test_indices_submuestreo_rechaza_argumentos_invalidos():
    with pytest.raises(ValueError):
        ed.indices_submuestreo(-1, 150)
    with pytest.raises(ValueError):
        ed.indices_submuestreo(10, 1)


# ---------------------------------------------------------------- 3. datos del deslizador
def test_contrato_del_json(datos):
    assert set(datos) == {"meta", "etas"}
    meta = datos["meta"]
    assert set(meta) == CLAVES_META
    assert (meta["func"], meta["dim"], meta["method"]) == ("rosenbrock", 2, "gdfijo")
    assert meta["seed"] == cfg_pequena()["base_seed"]
    assert isinstance(meta["k"], float) and meta["k"] == 4.0
    assert isinstance(meta["budget"], float) and meta["budget"] == 2.0 * PRESUPUESTO
    assert meta["puntos_max"] == ed.PUNTOS_MAX
    assert len(meta["x0"]) == 2
    for entrada in datos["etas"]:
        assert set(entrada) == CLAVES_ETA
        assert isinstance(entrada["eta"], float) and isinstance(entrada["f_best"], float)
        assert isinstance(entrada["n_grad"], int) and isinstance(entrada["n_iter"], int)
        assert entrada["marca"] in (None, ed.MARCA_DEFECTO, ed.MARCA_AFINADO)


def test_todos_los_eta_comparten_x0(datos):
    for entrada in datos["etas"]:
        assert entrada["puntos"][0] == datos["meta"]["x0"]


def test_rejilla_de_los_datos(datos):
    etas = [e["eta"] for e in datos["etas"]]
    espacio = cfg_pequena()["hpo"]["espacios"]["gdfijo"]["eta"]
    assert etas[0] == espacio["min"] and etas[-1] == espacio["max"]
    assert etas == sorted(etas) and len(set(etas)) == len(etas)
    assert len(etas) == 14                                   # 13 de la rejilla + el afinado
    assert marcas(datos["etas"]).count(ed.MARCA_DEFECTO) == 1
    assert marcas(datos["etas"]).count(ed.MARCA_AFINADO) == 1
    afinado = next(e for e in datos["etas"] if e["marca"] == ed.MARCA_AFINADO)
    assert afinado["eta"] == ETA_AFINADO


def test_sin_config_afinada_no_hay_marca_afinado():
    sin_afinada = ed.construir_datos(cfg_pequena())
    assert ed.MARCA_AFINADO not in marcas(sin_afinada["etas"])
    assert len(sin_afinada["etas"]) == 13
    igual = ed.construir_datos(cfg_pequena(), cfg_pequena())
    assert igual == sin_afinada


def test_la_marca_defecto_reproduce_ejecutar_corrida(datos):
    cfg = cfg_pequena()
    corrida = ejecutar_corrida("rosenbrock", 2, "gdfijo", cfg["base_seed"], 0, cfg,
                               presupuesto_por_dim=cfg["presupuesto_por_dim"], grabar_frames=True)
    resultado = corrida["result"]
    defecto = next(e for e in datos["etas"] if e["marca"] == ed.MARCA_DEFECTO)
    assert defecto["eta"] == cfg["gd"]["eta"]["rosenbrock"]
    assert defecto["f_best"] == resultado["f_best"]
    assert defecto["n_grad"] == resultado["n_grad"]
    assert defecto["n_iter"] == resultado["frames"][-1]["iter"]
    assert defecto["puntos"][-1] == resultado["frames"][-1]["positions"][0]
    assert datos["meta"]["x0"] == resultado["frames"][0]["positions"][0]
    assert (datos["meta"]["k"], datos["meta"]["budget"]) == (corrida["k"], corrida["budget"])
    for i, punto in zip(defecto["iteraciones"], defecto["puntos"]):
        assert resultado["frames"][i]["iter"] == i
        assert punto == resultado["frames"][i]["positions"][0]


def test_cada_eta_reproduce_su_corrida(datos):
    entrada = datos["etas"][0]                               # el menor η: no lleva marca
    cfg = cfg_con_eta(entrada["eta"])
    resultado = ejecutar_corrida("rosenbrock", 2, "gdfijo", cfg["base_seed"], 0, cfg,
                                 presupuesto_por_dim=PRESUPUESTO, grabar_frames=True)["result"]
    assert entrada["marca"] is None
    assert entrada["f_best"] == resultado["f_best"]
    assert entrada["puntos"][-1] == resultado["frames"][-1]["positions"][0]


def test_submuestreo_en_los_datos():
    puntos_max = 5                                           # 20 gradientes -> 21 iterados > 5
    datos = ed.construir_datos(cfg_pequena(), puntos_max=puntos_max)
    assert datos["meta"]["puntos_max"] == puntos_max
    for entrada in datos["etas"]:
        iteraciones = entrada["iteraciones"]
        assert len(iteraciones) == len(entrada["puntos"]) <= puntos_max
        assert iteraciones[0] == 0 and iteraciones[-1] == entrada["n_iter"]
        assert all(a < b for a, b in zip(iteraciones, iteraciones[1:]))
        assert all(len(p) == 2 for p in entrada["puntos"])
    assert any(e["n_iter"] + 1 > puntos_max for e in datos["etas"])   # sí hubo submuestreo


def test_la_config_de_entrada_no_se_modifica():
    cfg, afinada = cfg_pequena(), cfg_con_eta(ETA_AFINADO)
    copia_cfg, copia_afinada = copy.deepcopy(cfg), copy.deepcopy(afinada)
    ed.construir_datos(cfg, afinada)
    assert cfg == copia_cfg and afinada == copia_afinada


# ---------------------------------------------------------------- 4. guardado y script
def _sin_no_finitos(obj) -> bool:
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_sin_no_finitos(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_sin_no_finitos(v) for v in obj)
    return True


def test_el_json_guardado_se_relee_igual_y_sin_no_finitos(datos, tmp_path):
    ruta = ed.guardar(datos, tmp_path / "sub" / "eta_deslizador.json")
    assert ruta == tmp_path / "sub" / "eta_deslizador.json"
    assert load_json(ruta) == datos                          # load_json rechaza NaN/Infinity
    assert _sin_no_finitos(datos)
    assert "NaN" not in ruta.read_text(encoding="utf-8")


def _escribir_config(ruta: Path, cfg: dict) -> Path:
    ruta.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return ruta


def test_generar_usa_la_salida_de_la_config(tmp_path):
    cfg = cfg_pequena()
    cfg["salida"] = str(tmp_path / "salida")
    base = _escribir_config(tmp_path / "base.yaml", cfg)
    afinada = _escribir_config(tmp_path / "tuned.yaml", {**cfg_con_eta(ETA_AFINADO)})
    ruta = ed.generar(base, afinada)
    assert ruta == tmp_path / "salida" / ed.NOMBRE_ARCHIVO
    assert ed.MARCA_AFINADO in marcas(load_json(ruta)["etas"])
    # config afinada inexistente: se genera sin la marca `afinado`
    ruta = ed.generar(base, tmp_path / "no_existe.yaml", tmp_path / "otro.json")
    assert ruta == tmp_path / "otro.json"
    assert ed.MARCA_AFINADO not in marcas(load_json(ruta)["etas"])


def test_script_se_ejecuta_desde_la_raiz(tmp_path):
    cfg = cfg_pequena()
    base = _escribir_config(tmp_path / "base.yaml", cfg)
    salida = tmp_path / "eta.json"
    proceso = subprocess.run(
        [sys.executable, str(SCRIPT), "--config", str(base), "--afinada", str(tmp_path / "no.yaml"),
         "--salida", str(salida)], cwd=RAIZ, capture_output=True, text=True, check=False)
    assert proceso.returncode == 0, proceso.stderr
    assert load_json(salida) == ed.construir_datos(cfg)


def test_script_valores_por_defecto():
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "configs/part1/base.yaml" in texto and "configs/part1/tuned.yaml" in texto


# ---------------------------------------------------------------- 5. archivo real
def test_archivo_real_coincide_con_la_corrida_guardada():
    cfg = load_config(CONFIG_BASE)
    real = RAIZ / cfg["salida"] / ed.NOMBRE_ARCHIVO
    corrida = RAIZ / cfg["salida"] / "runs" / run_filename("rosenbrock", 2, "gdfijo", cfg["base_seed"])
    if not real.exists() or not corrida.exists():
        pytest.skip("falta eta_deslizador.json o la corrida rosenbrock_2d_gdfijo_seed0.json")
    datos, guardada = load_json(real), load_json(corrida)
    defecto = [e for e in datos["etas"] if e["marca"] == ed.MARCA_DEFECTO]
    assert len(defecto) == 1
    assert defecto[0]["f_best"] == guardada["result"]["f_best"]
    assert defecto[0]["n_grad"] == guardada["result"]["n_grad"]
    assert datos["meta"]["x0"] == guardada["result"]["frames"][0]["positions"][0]
    assert defecto[0]["puntos"][-1] == guardada["result"]["frames"][-1]["positions"][0]
    assert (datos["meta"]["k"], datos["meta"]["budget"]) == (guardada["k"], guardada["budget"])
    assert real.stat().st_size < 150_000
    if CONFIG_AFINADA.exists():
        afinado = load_config(CONFIG_AFINADA)["gd"]["eta"]["rosenbrock"]
        if afinado != cfg["gd"]["eta"]["rosenbrock"]:
            assert [e["eta"] for e in datos["etas"] if e["marca"] == ed.MARCA_AFINADO] == [afinado]
