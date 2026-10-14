"""Pruebas de `src/part1/gif_trayectorias.py` (T4.3-A: datos del GIF de la Parte 1).

Grupos:

    1. marcas           -> crecientes, desde 0 hasta el mayor n_iter, a lo sumo MARCAS_MAX
    2. lo sostenido     -> la variante que termina antes repite su último fotograma
    3. búsqueda por iter -> el fotograma se busca por su campo `iter`, no por su posición
    4. rótulos de f     -> f y f_mejor son f(best) del fotograma
    5. llamadas         -> exactamente las 5 corridas pedidas
    6. contrato         -> claves, longitudes, tipos y sin NaN/inf (corridas reales reducidas)
    7. determinismo     -> dos llamadas iguales; el JSON se relee igual
    8. archivo real     -> existe, cumple el contrato y se regenera igual (5 corridas completas)

Los grupos 1-5 usan un doble de `ejecutar_corrida` con fotogramas sintéticos.
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
from src.common.results import load_json
from src.part1 import gif_trayectorias as gt
from src.part1.eta_deslizador import indices_submuestreo
from src.part1.functions import get_function

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_BASE = RAIZ / "configs" / "part1" / "base.yaml"
SCRIPT = RAIZ / "scripts" / "part1_gif_trayectorias.py"
ARCHIVO_REAL = RAIZ / "results" / "data" / "part1" / "gif_trayectorias.json"
PRESUPUESTO = 40                 # por dimensión: 80 evaluaciones equivalentes en 2D
TAMANO_MAX_REAL = 300_000        # bytes
N_PARTICULAS = 30                # pso.N de base.yaml
PARES = {("rosenbrock", "gdfijo"), ("rosenbrock", "gdarmijo"), ("rastrigin", "gdfijo"),
         ("rastrigin", "gdarmijo"), ("rastrigin", "pso")}
CLAVES_RAIZ = {"meta", "gd", "pso"}
CLAVES_META = {"config", "base_seed", "run_id", "dim", "k", "budget", "marcas_max"}
CLAVES_GD_FUNC = {"iteraciones", "metodos"}
CLAVES_GD_METODO = {"n_iter", "f_best", "n_f", "n_grad", "x", "f"}
CLAVES_PSO = {"iteraciones", "n_iter", "f_best", "n_f", "enjambre", "mejor", "f_mejor"}

# n_iter de cada corrida del doble: Rosenbrock con una variante larga y una corta;
# Rastrigin con todo pequeño (cabe entero en MARCAS_MAX).
N_ITER_DOBLE = {("rosenbrock", "gdfijo"): 5000, ("rosenbrock", "gdarmijo"): 7,
                ("rastrigin", "gdfijo"): 12, ("rastrigin", "gdarmijo"): 20, ("rastrigin", "pso"): 9}
DESPLAZAMIENTO_BEST = 0.25       # en el doble, best != positions[0] para saber de dónde sale f


def cfg_real() -> dict:
    return load_config(CONFIG_BASE)


def cfg_pequena() -> dict:
    cfg = cfg_real()
    cfg["presupuesto_por_dim"] = PRESUPUESTO
    return cfg


def punto(func: str, method: str, i: int, particula: int = 0) -> list[float]:
    """Punto sintético distinto para cada (corrida, iter, partícula)."""
    semilla = sorted(PARES).index((func, method))
    return [0.1 * semilla + 1e-4 * i + 0.01 * particula, -0.05 * semilla - 2e-4 * i]


def fotograma(func: str, method: str, i: int) -> dict:
    n = N_PARTICULAS if method == "pso" else 1
    posiciones = [punto(func, method, i, p) for p in range(n)]
    best = [posiciones[0][0] + DESPLAZAMIENTO_BEST, posiciones[0][1] - DESPLAZAMIENTO_BEST]
    return {"iter": i, "positions": posiciones, "best": best}


def orden_barajado(n_iter: int) -> list[int]:
    """0..n_iter con los intermedios invertidos: la posición en la lista no es el iter."""
    if n_iter < 2:
        return list(range(n_iter + 1))
    return [0, *range(n_iter - 1, 0, -1), n_iter]


class Doble:
    """Sustituto de `ejecutar_corrida` que registra las llamadas y devuelve fotogramas sintéticos."""

    def __init__(self, n_iters=None, iteraciones=None):
        self.n_iters = dict(N_ITER_DOBLE if n_iters is None else n_iters)
        self.iteraciones = iteraciones        # función (func, method, n_iter) -> lista de iter
        self.llamadas = []

    def __call__(self, func, dim, method, base_seed, run_id, cfg, **kwargs):
        self.llamadas.append({"func": func, "dim": dim, "method": method, "base_seed": base_seed,
                              "run_id": run_id, "kwargs": dict(kwargs)})
        n_iter = self.n_iters[(func, method)]
        orden = orden_barajado(n_iter) if self.iteraciones is None else self.iteraciones(func, method, n_iter)
        frames = [fotograma(func, method, i) for i in orden]
        resultado = {"f_best": 0.5 + n_iter, "n_f": 3 * n_iter + 1, "n_grad": n_iter, "frames": frames}
        return {"func": func, "dim": dim, "method": method, "seed": base_seed + run_id,
                "k": float(2 * dim), "budget": float(cfg["presupuesto_por_dim"] * dim), "result": resultado}


@pytest.fixture
def doble(monkeypatch) -> Doble:
    sustituto = Doble()
    monkeypatch.setattr(gt, "ejecutar_corrida", sustituto)
    return sustituto


@pytest.fixture
def datos_doble(doble) -> dict:
    return gt.construir_datos(cfg_real(), "configs/part1/base.yaml")


def f_de(func: str, x) -> float:
    return get_function(func, 2).f(x)


# ---------------------------------------------------------------- 1. marcas
def _comprobar_marcas(iteraciones: list[int], maximo: int):
    assert iteraciones[0] == 0 and iteraciones[-1] == maximo
    assert all(isinstance(t, int) for t in iteraciones)
    assert all(a < b for a, b in zip(iteraciones, iteraciones[1:]))
    assert len(iteraciones) <= gt.MARCAS_MAX


def test_marcas_crecientes_desde_cero_hasta_el_mayor_n_iter(datos_doble):
    assert gt.MARCAS_MAX == 45
    rosen = datos_doble["gd"]["rosenbrock"]["iteraciones"]
    _comprobar_marcas(rosen, 5000)
    assert rosen == indices_submuestreo(5000, gt.MARCAS_MAX)
    rastr = datos_doble["gd"]["rastrigin"]["iteraciones"]
    _comprobar_marcas(rastr, 20)
    assert rastr == list(range(21))                          # cabe entera: no se submuestrea
    pso = datos_doble["pso"]["rastrigin"]["iteraciones"]
    _comprobar_marcas(pso, 9)
    assert pso == list(range(10))
    assert datos_doble["meta"]["marcas_max"] == gt.MARCAS_MAX


def test_marcas_max_es_parametro(doble):
    datos = gt.construir_datos(cfg_real(), "x.yaml", marcas_max=5)
    assert datos["meta"]["marcas_max"] == 5
    for func in ("rosenbrock", "rastrigin"):
        assert len(datos["gd"][func]["iteraciones"]) <= 5
    assert datos["pso"]["rastrigin"]["iteraciones"] == indices_submuestreo(9, 5)


# ---------------------------------------------------------------- 2. lo sostenido
def test_la_variante_corta_sostiene_su_ultimo_fotograma(datos_doble):
    entrada = datos_doble["gd"]["rosenbrock"]
    corta = entrada["metodos"]["gdarmijo"]
    assert corta["n_iter"] == 7
    ultimo = fotograma("rosenbrock", "gdarmijo", 7)
    sostenidas = [j for j, t in enumerate(entrada["iteraciones"]) if t >= 7]
    assert len(sostenidas) > 1
    for j in sostenidas:
        assert corta["x"][j] == ultimo["positions"][0]
        assert corta["f"][j] == f_de("rosenbrock", ultimo["best"])
    larga = entrada["metodos"]["gdfijo"]
    assert larga["x"][-1] == fotograma("rosenbrock", "gdfijo", 5000)["positions"][0]
    # en Rastrigin gdfijo (12) termina antes que gdarmijo (20)
    rastr = datos_doble["gd"]["rastrigin"]
    for j, t in enumerate(rastr["iteraciones"]):
        assert rastr["metodos"]["gdfijo"]["x"][j] == fotograma("rastrigin", "gdfijo", min(t, 12))["positions"][0]


# ---------------------------------------------------------------- 3. búsqueda por iter
def test_x_enjambre_y_mejor_son_los_del_fotograma_de_ese_iter(datos_doble):
    for func in ("rosenbrock", "rastrigin"):
        entrada = datos_doble["gd"][func]
        for metodo, valores in entrada["metodos"].items():
            for j, t in enumerate(entrada["iteraciones"]):
                esperado = fotograma(func, metodo, min(t, valores["n_iter"]))
                assert valores["x"][j] == esperado["positions"][0]
    pso = datos_doble["pso"]["rastrigin"]
    for j, t in enumerate(pso["iteraciones"]):
        esperado = fotograma("rastrigin", "pso", min(t, pso["n_iter"]))
        assert pso["enjambre"][j] == esperado["positions"]
        assert pso["mejor"][j] == esperado["best"]
    # la lista del doble está barajada: buscar por posición habría dado otro punto
    assert pso["enjambre"][1] != fotograma("rastrigin", "pso", orden_barajado(9)[1])["positions"]


def test_fotograma_en_busca_por_iter_y_sostiene():
    frames = [{"iter": i, "positions": [[i, 0.0]], "best": [i, 0.0]} for i in (0, 2, 4, 6)]
    assert gt.fotograma_en(frames, 4)["positions"] == [[4, 0.0]]
    assert gt.fotograma_en(frames, 2)["positions"] == [[2, 0.0]]       # el índice 2 sería iter 4
    assert gt.fotograma_en(frames, 100)["positions"] == [[6, 0.0]]     # min(t, n_iter) = 6


def test_fotograma_en_iter_ausente_lanza_error():
    frames = [{"iter": i, "positions": [[i, 0.0]], "best": [i, 0.0]} for i in (0, 2, 4, 6)]
    with pytest.raises(ValueError, match="iter"):
        gt.fotograma_en(frames, 3)


def test_fotogramas_que_saltan_iter_lanzan_error(monkeypatch):
    saltando = Doble(iteraciones=lambda func, method, n: list(range(0, n + 1, 2)) if n % 2 == 0 else
                     [*range(0, n, 2), n])
    monkeypatch.setattr(gt, "ejecutar_corrida", saltando)
    with pytest.raises(ValueError, match="iter"):
        gt.construir_datos(cfg_real(), "x.yaml")


def test_fotogramas_que_no_empiezan_en_cero_lanzan_error(monkeypatch):
    sin_cero = Doble(iteraciones=lambda func, method, n: list(range(1, n + 1)))
    monkeypatch.setattr(gt, "ejecutar_corrida", sin_cero)
    with pytest.raises(ValueError, match="iter"):
        gt.construir_datos(cfg_real(), "x.yaml")


# ---------------------------------------------------------------- 4. rótulos de f
def test_f_es_la_del_best_del_fotograma(datos_doble):
    # en el doble best = positions[0] + DESPLAZAMIENTO_BEST: f debe salir del best, no de x
    for func in ("rosenbrock", "rastrigin"):
        entrada = datos_doble["gd"][func]
        for metodo, valores in entrada["metodos"].items():
            for j, t in enumerate(entrada["iteraciones"]):
                esperado = fotograma(func, metodo, min(t, valores["n_iter"]))
                assert valores["f"][j] == f_de(func, esperado["best"])
                assert valores["f"][j] != f_de(func, valores["x"][j])
                assert type(valores["f"][j]) is float
    pso = datos_doble["pso"]["rastrigin"]
    for j, mejor in enumerate(pso["mejor"]):
        assert pso["f_mejor"][j] == f_de("rastrigin", mejor)
        assert type(pso["f_mejor"][j]) is float


# ---------------------------------------------------------------- 5. llamadas
def test_se_ejecutan_exactamente_las_cinco_corridas(doble):
    cfg = cfg_real()
    datos = gt.construir_datos(cfg, "configs/part1/base.yaml")
    assert len(doble.llamadas) == 5
    assert {(ll["func"], ll["method"]) for ll in doble.llamadas} == PARES
    for llamada in doble.llamadas:
        assert llamada["dim"] == 2 and llamada["run_id"] == 0
        assert llamada["base_seed"] == cfg["base_seed"]
        assert llamada["kwargs"] == {"presupuesto_por_dim": cfg["presupuesto_por_dim"], "grabar_frames": True}
    assert datos["meta"]["config"] == "configs/part1/base.yaml"
    assert datos["meta"]["k"] == 4.0 and datos["meta"]["budget"] == 2.0 * cfg["presupuesto_por_dim"]
    metodos = datos["gd"]["rosenbrock"]["metodos"]
    assert metodos["gdfijo"]["n_grad"] == 5000 and metodos["gdfijo"]["n_f"] == 15001
    assert metodos["gdfijo"]["f_best"] == 5000.5


def test_la_ruta_de_la_config_se_guarda_con_barras(doble):
    datos = gt.construir_datos(cfg_real(), Path("configs") / "part1" / "base.yaml")
    assert datos["meta"]["config"] == "configs/part1/base.yaml"
    datos = gt.construir_datos(cfg_real(), "configs\\part1\\base.yaml")
    assert datos["meta"]["config"] == "configs/part1/base.yaml"


def test_la_config_no_se_modifica(doble):
    cfg = cfg_real()
    copia = copy.deepcopy(cfg)
    gt.construir_datos(cfg, "x.yaml")
    assert cfg == copia


# ---------------------------------------------------------------- 6. contrato (corridas reales)
def _sin_no_finitos(obj) -> bool:
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_sin_no_finitos(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_sin_no_finitos(v) for v in obj)
    return True


def _es_punto(p) -> bool:
    return isinstance(p, list) and len(p) == 2 and all(type(c) is float for c in p)


def comprobar_contrato(datos: dict, cfg: dict):
    assert set(datos) == CLAVES_RAIZ
    meta = datos["meta"]
    assert set(meta) == CLAVES_META
    assert isinstance(meta["config"], str) and "\\" not in meta["config"]
    assert meta["base_seed"] == cfg["base_seed"] and type(meta["base_seed"]) is int
    assert meta["run_id"] == 0 and meta["dim"] == 2 and type(meta["marcas_max"]) is int
    assert type(meta["k"]) is float and meta["k"] == 4.0
    assert type(meta["budget"]) is float and meta["budget"] == 2.0 * cfg["presupuesto_por_dim"]
    assert set(datos["gd"]) == {"rosenbrock", "rastrigin"}
    for func, entrada in datos["gd"].items():
        assert set(entrada) == CLAVES_GD_FUNC
        assert set(entrada["metodos"]) == {"gdfijo", "gdarmijo"}
        iteraciones = entrada["iteraciones"]
        maximo = max(v["n_iter"] for v in entrada["metodos"].values())
        assert iteraciones[0] == 0 and iteraciones[-1] == maximo
        assert all(a < b for a, b in zip(iteraciones, iteraciones[1:]))
        assert len(iteraciones) <= meta["marcas_max"]
        for valores in entrada["metodos"].values():
            assert set(valores) == CLAVES_GD_METODO
            assert all(type(valores[c]) is int for c in ("n_iter", "n_f", "n_grad"))
            assert type(valores["f_best"]) is float
            assert len(valores["x"]) == len(valores["f"]) == len(iteraciones)
            assert all(_es_punto(p) for p in valores["x"])
            assert all(type(v) is float for v in valores["f"])
    assert set(datos["pso"]) == {"rastrigin"}
    pso = datos["pso"]["rastrigin"]
    assert set(pso) == CLAVES_PSO
    iteraciones = pso["iteraciones"]
    assert iteraciones[0] == 0 and iteraciones[-1] == pso["n_iter"]
    assert all(a < b for a, b in zip(iteraciones, iteraciones[1:]))
    assert len(iteraciones) <= meta["marcas_max"]
    assert type(pso["n_iter"]) is int and type(pso["n_f"]) is int and type(pso["f_best"]) is float
    assert len(pso["enjambre"]) == len(pso["mejor"]) == len(pso["f_mejor"]) == len(iteraciones)
    for enjambre in pso["enjambre"]:
        assert len(enjambre) == N_PARTICULAS and all(_es_punto(p) for p in enjambre)
    assert all(_es_punto(p) for p in pso["mejor"])
    assert all(type(v) is float for v in pso["f_mejor"])
    assert _sin_no_finitos(datos)


@pytest.fixture(scope="module")
def datos_reducidos() -> dict:
    return gt.construir_datos(cfg_pequena(), "configs/part1/base.yaml")


def test_contrato_con_corridas_reales_reducidas(datos_reducidos):
    comprobar_contrato(datos_reducidos, cfg_pequena())


# ---------------------------------------------------------------- 7. determinismo y guardado
def test_determinismo_y_relectura(datos_reducidos, tmp_path):
    otra = gt.construir_datos(cfg_pequena(), "configs/part1/base.yaml")
    assert otra == datos_reducidos
    ruta = gt.guardar(datos_reducidos, tmp_path / "sub" / gt.NOMBRE_ARCHIVO)
    assert ruta == tmp_path / "sub" / gt.NOMBRE_ARCHIVO
    assert load_json(ruta) == datos_reducidos


def _escribir_config(ruta: Path, cfg: dict) -> Path:
    ruta.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return ruta


def test_generar_usa_la_salida_de_la_config(tmp_path):
    cfg = cfg_pequena()
    cfg["salida"] = str(tmp_path / "salida")
    base = _escribir_config(tmp_path / "base.yaml", cfg)
    ruta = gt.generar(base)
    assert ruta == tmp_path / "salida" / gt.NOMBRE_ARCHIVO
    comprobar_contrato(load_json(ruta), cfg)
    otra = gt.generar(base, tmp_path / "otro.json")
    assert otra == tmp_path / "otro.json"


def test_script_se_ejecuta(tmp_path):
    cfg = cfg_pequena()
    base = _escribir_config(tmp_path / "base.yaml", cfg)
    salida = tmp_path / "gif.json"
    proceso = subprocess.run([sys.executable, str(SCRIPT), "--config", str(base), "--salida", str(salida)],
                             cwd=RAIZ, capture_output=True, text=True, check=False)
    assert proceso.returncode == 0, proceso.stderr
    assert str(salida) in proceso.stdout
    assert load_json(salida) == gt.construir_datos(cfg, str(base))


def test_script_valores_por_defecto():
    texto = SCRIPT.read_text(encoding="utf-8")
    assert "configs/part1/base.yaml" in texto and "results/data/part1/gif_trayectorias.json" in texto


# ---------------------------------------------------------------- 8. archivo real
def aplanar(puntos: list) -> list[float]:
    """pytest.approx no compara listas anidadas: se aplanan los puntos."""
    return [c for p in puntos for c in p]


def test_archivo_real_cumple_el_contrato_y_se_regenera_igual(tmp_path):
    assert ARCHIVO_REAL.exists(), "falta results/data/part1/gif_trayectorias.json"
    assert ARCHIVO_REAL.stat().st_size < TAMANO_MAX_REAL
    real = load_json(ARCHIVO_REAL)
    comprobar_contrato(real, cfg_real())
    nuevo = load_json(gt.generar(CONFIG_BASE, tmp_path / gt.NOMBRE_ARCHIVO))
    tolerancia = {"rel": 1e-6, "abs": 1e-9}
    for func in ("rosenbrock", "rastrigin"):
        assert nuevo["gd"][func]["iteraciones"] == real["gd"][func]["iteraciones"]
        for metodo in ("gdfijo", "gdarmijo"):
            a, b = nuevo["gd"][func]["metodos"][metodo], real["gd"][func]["metodos"][metodo]
            assert a["n_iter"] == b["n_iter"]
            assert aplanar(a["x"]) == pytest.approx(aplanar(b["x"]), **tolerancia)
            assert a["f"] == pytest.approx(b["f"], **tolerancia)
    a, b = nuevo["pso"]["rastrigin"], real["pso"]["rastrigin"]
    assert a["iteraciones"] == b["iteraciones"] and a["n_iter"] == b["n_iter"]
    assert aplanar(a["mejor"]) == pytest.approx(aplanar(b["mejor"]), **tolerancia)
    assert aplanar(sum(a["enjambre"], [])) == pytest.approx(aplanar(sum(b["enjambre"], [])), **tolerancia)
    assert a["f_mejor"] == pytest.approx(b["f_mejor"], **tolerancia)
