"""Pruebas del descenso por gradiente (Spec §5.1, §6.2 y §6.3): paso fijo con proyección (T1.2) y
búsqueda de paso con retroceso de Armijo (T1.3, al final del archivo).

Casi todas usan la cuadrática de conftest.py (f = ||x - x*||², dominio ±5, name "cuadratica"), cuya
trayectoria con paso fijo se conoce en forma cerrada: x_{t+1} - x* = (1 - 2η)(x_t - x*) mientras no
actúe la proyección. Las anclas y la estadística usan las funciones reales de functions.py.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

from src.common.config import apply_overrides, load_config
from src.common.counter import CountedProblem
from src.common.seeds import make_rng
from src.part1 import gd
from src.part1.functions import get_function

ROOT = Path(__file__).resolve().parents[1]
BASE_PART1 = ROOT / "configs" / "part1" / "base.yaml"
DEMO_PART1 = ROOT / "configs" / "part1" / "demo.yaml"

TOL_GRAD = 1e-8
X_STAR_INTERIOR = [1.0, -2.0]   # mínimo dentro de ±5
X_STAR_EXTERIOR = [10.0, 0.0]   # mínimo fuera de ±5: la proyección actúa en la primera coordenada
LIMITE_CUADRATICA = 5.0         # dominio de la Cuadratica de conftest.py


def _cfg(eta, tol_grad=TOL_GRAD, record_frames=True, variante="fijo", nombre="cuadratica"):
    """Configuración mínima armada a mano (la resolvería el runner de T1.7)."""
    return {
        "variante": variante,
        "gd": {"eta": {nombre: eta}, "tol_grad": tol_grad},
        "record_frames": record_frames,
    }


def _correr(func, eta, k, budget, seed=0, **kw):
    """Ejecuta gd.optimize sobre `func`; devuelve (resultado, problem)."""
    problem = CountedProblem(func, k=k, budget=budget)
    resultado = gd.optimize(problem, _cfg(eta, **kw), np.random.default_rng(seed))
    return resultado, problem


def _x0(resultado):
    return np.array(resultado["frames"][0]["positions"][0])


# ---------------------------------------------------------------- a), b) convergencia

# Paso fijo converge a x* en la cuadrática con el número exacto de gradientes de la forma cerrada:
# comprueba a la vez el bucle, la parada por ‖∇f‖ < tol y que n_f = 0 (solo se paga ∇f).
def test_converge_en_cuadratica_con_cuenta_exacta(cuadratica):
    # Preparación y ejecución.
    func = cuadratica(X_STAR_INTERIOR)
    k, budget = 4, 10_000
    res, _ = _correr(func, eta=0.25, k=k, budget=budget)
    # Aserciones: llega a x*, para por gradiente y no cobra f.
    np.testing.assert_allclose(res["x_best"], X_STAR_INTERIOR, atol=1e-6)
    assert res["f_best"] < 1e-12
    assert res["eval_equiv"] < budget            # paró por gradiente, no por presupuesto
    assert res["n_f"] == 0
    # Con η = 0.25: x_t - x* = 0.5^t (x_0 - x*) y ||g_t|| = 2 ||x_t - x*||.
    d0 = np.linalg.norm(_x0(res) - np.array(X_STAR_INTERIOR))
    t_estrella = 0
    while not (2 * d0 * 0.5**t_estrella < TOL_GRAD):
        t_estrella += 1
    assert res["n_grad"] == t_estrella + 1


# Con η = 0.5 la cuadrática llega a x* en un paso: 2 gradientes (el del paso y el que ve ∇f = 0).
def test_eta_medio_converge_en_un_paso(cuadratica):
    res, _ = _correr(cuadratica(X_STAR_INTERIOR), eta=0.5, k=4, budget=10_000)
    assert res["n_grad"] == 2
    np.testing.assert_allclose(res["x_best"], X_STAR_INTERIOR, atol=1e-12)


# ---------------------------------------------------------------- c) proyección

# Con x* fuera del dominio, Π mantiene todos los iterados dentro y el mejor queda en el borde;
# como ∇f nunca se anula, la corrida solo termina por presupuesto.
def test_proyeccion_al_dominio(cuadratica):
    k, budget = 4, 400
    res, _ = _correr(cuadratica(X_STAR_EXTERIOR), eta=0.25, k=k, budget=budget)
    posiciones = np.array([fr["positions"][0] for fr in res["frames"]])
    assert np.all(posiciones >= -LIMITE_CUADRATICA) and np.all(posiciones <= LIMITE_CUADRATICA)
    assert res["x_best"][0] == LIMITE_CUADRATICA
    assert posiciones[-1][0] == LIMITE_CUADRATICA
    assert res["x_best"][1] == pytest.approx(0.0, abs=1e-6)
    assert res["n_grad"] == math.floor(budget / k)    # el gradiente nunca se anula: no para


# ---------------------------------------------------------------- d) presupuesto

# n_grad = ⌊budget/k⌋ y eval_equiv ≤ budget para varios k y presupuestos (incluso no múltiplos de
# k): el presupuesto nunca se excede (§6.2).
@pytest.mark.parametrize(
    "k, budget, n_grad_esperado",
    [(4, 400, 100), (4, 10.5, 2), (6, 100, 16), (1, 37, 37), (4, 8, 2)],  # 10.5: no múltiplo de k
)
def test_presupuesto_se_respeta(cuadratica, k, budget, n_grad_esperado):
    res, problem = _correr(cuadratica(X_STAR_EXTERIOR), eta=0.25, k=k, budget=budget)
    assert res["n_grad"] == n_grad_esperado == math.floor(budget / k)
    assert res["eval_equiv"] == float(k * n_grad_esperado)   # (4, 10.5) -> 8.0
    assert res["eval_equiv"] <= budget
    assert res["eval_equiv"] == problem.eval_equiv()


# Si no alcanza ni para un ∇f, optimize no lanza y devuelve x0 (registrado con observe, sin costo).
def test_presupuesto_menor_que_k_devuelve_resultado_valido(cuadratica):
    func = cuadratica(X_STAR_INTERIOR)
    res, _ = _correr(func, eta=0.25, k=4, budget=3)   # BudgetExhausted no sale de optimize
    x0 = _x0(res)
    assert res["n_grad"] == 0 and res["n_f"] == 0
    assert res["eval_equiv"] == 0.0
    assert res["x_best"] == x0.tolist()
    assert res["f_best"] == float(np.sum((x0 - func.x_star) ** 2))
    assert len(res["frames"]) == 1
    assert res["history"] == [{"eval_equiv": 0.0, "f_best": res["f_best"]}]


# ---------------------------------------------------------------- e) conteo

# Paso fijo: observe evalúa f sin cobrarla (n_f = 0 aunque f sí se llama) y cada ∇f cuesta k;
# n_grad coincide con las llamadas reales a grad.
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200)])
def test_observe_no_cobra_y_grad_si(cuadratica, x_star, budget):
    func = cuadratica(x_star)
    res, problem = _correr(func, eta=0.25, k=4, budget=budget)
    assert res["n_f"] == 0 and problem.n_f == 0
    assert func.llamadas_f > 0                   # observe sí evaluó f, sin cobrarla
    assert func.llamadas_grad == res["n_grad"] == problem.n_grad
    assert res["eval_equiv"] == 4 * res["n_grad"]


# ---------------------------------------------------------------- f) historial

# history es la curva de convergencia: empieza en eval_equiv 0 (x0), f_best baja estrictamente,
# eval_equiv sube y es múltiplo de k (en paso fijo solo se paga ∇f).
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200)])
def test_historial(cuadratica, x_star, budget):
    # Preparación y ejecución.
    k = 4
    res, problem = _correr(cuadratica(x_star), eta=0.25, k=k, budget=budget)
    hist = res["history"]
    # Aserciones: igual al del contador, monotonía y último punto = f_best.
    assert hist == problem.history
    assert hist[0]["eval_equiv"] == 0.0
    f_hist = [h["f_best"] for h in hist]
    e_hist = [h["eval_equiv"] for h in hist]
    assert all(b < a for a, b in zip(f_hist, f_hist[1:]))
    assert all(b > a for a, b in zip(e_hist, e_hist[1:]))
    assert all(e % k == 0 for e in e_hist)
    assert hist[-1]["f_best"] == res["f_best"]


# ---------------------------------------------------------------- g) frames

def _comprobar_forma_frames(frames):
    for i, fr in enumerate(frames):
        assert set(fr) == {"iter", "positions", "best"}
        assert type(fr["iter"]) is int and fr["iter"] == i
        assert len(fr["positions"]) == 1 and len(fr["positions"][0]) == 2
        assert all(type(v) is float for v in fr["positions"][0])
        assert len(fr["best"]) == 2 and all(type(v) is float for v in fr["best"])


def _mejor_visto(posiciones, x_star):
    """Mejor punto visto hasta cada frame (mejora estricta, como CountedProblem)."""
    mejores, mejor, f_mejor = [], None, math.inf
    for p in posiciones:
        valor = float(np.sum((np.asarray(p) - x_star) ** 2))
        if valor < f_mejor:
            mejor, f_mejor = list(p), valor
        mejores.append(mejor)
    return mejores


# Frames: forma de §5.1, uno por punto aceptado incluido x0 (n_grad frames si para por
# ‖∇f‖ < tol, n_grad + 1 si para por presupuesto); "best" = mejor punto visto hasta ese frame,
# aunque el GD oscile o diverja.
@pytest.mark.parametrize(
    "x_star, eta, budget, por_presupuesto",
    [
        (X_STAR_INTERIOR, 0.25, 10_000, False),   # para por gradiente
        (X_STAR_EXTERIOR, 0.25, 200, True),       # para por presupuesto
        ([0.0, 0.0], 1.0, 36, True),              # oscila x_0, -x_0: f(x_t) = f(x_0) sin mejorar
        ([0.0, 0.0], 1.5, 40, True),              # diverge hasta el borde: el mejor es x_0
    ],
)
def test_frames(cuadratica, x_star, eta, budget, por_presupuesto):
    # Ejecución.
    func = cuadratica(x_star)
    res, _ = _correr(func, eta=eta, k=4, budget=budget)
    frames = res["frames"]
    # Aserciones: forma, número de frames según el motivo de parada y mejor visto.
    _comprobar_forma_frames(frames)
    if por_presupuesto:
        assert len(frames) == res["n_grad"] + 1
    else:
        assert len(frames) == res["n_grad"]
    posiciones = [fr["positions"][0] for fr in frames]
    assert [fr["best"] for fr in frames] == _mejor_visto(posiciones, func.x_star)
    assert frames[-1]["best"] == res["x_best"]


# x_best es el mejor punto visto, no el último iterado (contrato §5.1).
@pytest.mark.parametrize("eta, budget", [(1.0, 36), (1.5, 40)])
def test_mejor_visto_no_es_el_ultimo(cuadratica, eta, budget):
    """Sin descenso (η ≥ 1 en la cuadrática), el mejor punto es x_0, no el último visitado."""
    func = cuadratica([0.0, 0.0])
    res, _ = _correr(func, eta=eta, k=4, budget=budget)
    x0 = _x0(res)
    assert res["x_best"] == x0.tolist()
    assert res["f_best"] == float(np.sum(x0**2))
    # Con η = 1 el iterado alterna x_0 y su reflejo -x_0: el último difiere de x_best solo si
    # budget/k (número de pasos) es impar, como 36/4 = 9.
    assert res["frames"][-1]["positions"][0] != res["x_best"]


# iter numera 0, 1, 2, ... y el frame 0 es x0 = rng.uniform(lo, hi) con la semilla dada.
def test_frames_iter_y_primer_frame(cuadratica):
    res, _ = _correr(cuadratica(X_STAR_INTERIOR), eta=0.25, k=4, budget=10_000)
    assert [fr["iter"] for fr in res["frames"]] == list(range(len(res["frames"])))
    lo, hi = np.full(2, -LIMITE_CUADRATICA), np.full(2, LIMITE_CUADRATICA)
    esperado = np.random.default_rng(0).uniform(lo, hi)
    assert res["frames"][0]["positions"][0] == esperado.tolist()
    assert res["frames"][0]["best"] == esperado.tolist()


# Con record_frames = False la clave "frames" no aparece en el resultado.
def test_sin_frames_si_record_frames_falso(cuadratica):
    res, _ = _correr(cuadratica(X_STAR_INTERIOR), eta=0.25, k=4, budget=10_000,
                     record_frames=False)
    assert "frames" not in res


# En 3D no se graban frames aunque record_frames sea True (solo hay animación en 2D, §5.1).
def test_sin_frames_en_3d(cuadratica):
    res, _ = _correr(cuadratica([1.0, -2.0, 0.5]), eta=0.25, k=6, budget=10_000)
    assert "frames" not in res


# Si la config no trae record_frames, se asume False (no hay frames).
def test_record_frames_ausente_equivale_a_falso(cuadratica):
    cfg = _cfg(0.25)
    del cfg["record_frames"]
    problem = CountedProblem(cuadratica(X_STAR_INTERIOR), k=4, budget=10_000)
    assert "frames" not in gd.optimize(problem, cfg, np.random.default_rng(0))


# ---------------------------------------------------------------- h) reproducibilidad

# Misma semilla, mismo resultado completo: las corridas son reproducibles.
def test_misma_semilla_mismo_resultado(cuadratica):
    a, _ = _correr(cuadratica(X_STAR_EXTERIOR), eta=0.25, k=4, budget=200, seed=7)
    b, _ = _correr(cuadratica(X_STAR_EXTERIOR), eta=0.25, k=4, budget=200, seed=7)
    assert a == b


# Semillas distintas (1 y 2) dan puntos iniciales distintos: el x0 depende de la semilla.
def test_semillas_distintas_dan_x0_distinto(cuadratica):
    a, _ = _correr(cuadratica(X_STAR_INTERIOR), eta=0.25, k=4, budget=10_000, seed=1)
    b, _ = _correr(cuadratica(X_STAR_INTERIOR), eta=0.25, k=4, budget=10_000, seed=2)
    assert a["frames"][0]["positions"] != b["frames"][0]["positions"]


# Paso fijo usa el rng en una sola llamada uniform (x0): el estado final coincide con un testigo.
@pytest.mark.parametrize("dim", [2, 3])
def test_una_sola_llamada_al_rng(cuadratica, dim):
    func = cuadratica(np.ones(dim))
    problem = CountedProblem(func, k=2 * dim, budget=1_000)
    rng = np.random.default_rng(11)
    gd.optimize(problem, _cfg(0.25), rng)
    testigo = np.random.default_rng(11)
    testigo.uniform(func.bounds[:, 0], func.bounds[:, 1])
    assert rng.random() == testigo.random()


# ---------------------------------------------------------------- i) JSON y tipos

# El resultado se serializa a JSON sin NaN/inf, con las claves de §5.1 y tipos nativos de Python.
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200),
                                            (X_STAR_INTERIOR, 3)])
def test_resultado_serializable_y_tipos_nativos(cuadratica, x_star, budget):
    res, _ = _correr(cuadratica(x_star), eta=0.25, k=4, budget=budget)
    json.dumps(res, allow_nan=False)
    assert set(res) == {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history", "frames"}
    assert type(res["f_best"]) is float
    assert type(res["n_f"]) is int and type(res["n_grad"]) is int
    assert type(res["eval_equiv"]) is float
    assert type(res["x_best"]) is list and all(type(v) is float for v in res["x_best"])
    for h in res["history"]:
        assert type(h["eval_equiv"]) is float and type(h["f_best"]) is float


# ---------------------------------------------------------------- j) validaciones

def _optimizar_con(cuadratica, cfg):
    problem = CountedProblem(cuadratica(X_STAR_INTERIOR), k=4, budget=100)
    return gd.optimize(problem, cfg, np.random.default_rng(0))


# Una variante desconocida lanza ValueError cuyo mensaje lista las válidas.
@pytest.mark.parametrize("variante", [None, "", "Fijo", "newton", 1])
def test_variante_desconocida(cuadratica, variante):
    cfg = _cfg(0.25, variante=variante)
    with pytest.raises(ValueError, match="fijo"):
        _optimizar_con(cuadratica, cfg)


# Sin la clave variante, optimize falla con un mensaje claro en vez de elegir una por defecto.
def test_variante_ausente(cuadratica):
    cfg = _cfg(0.25)
    del cfg["variante"]
    with pytest.raises(ValueError, match="armijo"):
        _optimizar_con(cuadratica, cfg)


# Si gd.eta no tiene paso para la función, el error lista las funciones que sí lo tienen.
def test_funcion_ausente_en_eta(cuadratica):
    cfg = _cfg(0.25, nombre="rosenbrock")
    cfg["gd"]["eta"]["rastrigin"] = 2e-3
    with pytest.raises(ValueError, match="rastrigin, rosenbrock"):
        _optimizar_con(cuadratica, cfg)


# η no positivo, no finito, bool, texto o None se rechaza con ValueError que nombra eta.
@pytest.mark.parametrize("eta", [0, 0.0, -0.1, math.nan, math.inf, -math.inf, True, False,
                                 np.bool_(True), "0.1", None])
def test_eta_invalido(cuadratica, eta):
    with pytest.raises(ValueError, match="eta"):
        _optimizar_con(cuadratica, _cfg(eta))


# tol_grad inválido (≤ 0, NaN, inf, bool, texto, None) se rechaza con ValueError que lo nombra.
@pytest.mark.parametrize("tol", [0, -1e-8, math.nan, math.inf, True, "1e-8", None])
def test_tol_grad_invalido(cuadratica, tol):
    with pytest.raises(ValueError, match="tol_grad"):
        _optimizar_con(cuadratica, _cfg(0.25, tol_grad=tol))


# Una config inválida falla antes de evaluar f/∇f y de tocar el rng (no gasta presupuesto ni azar).
def test_validacion_no_evalua_ni_usa_el_rng(cuadratica):
    func = cuadratica(X_STAR_INTERIOR)
    problem = CountedProblem(func, k=4, budget=100)
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        gd.optimize(problem, _cfg(-1.0), rng)
    assert func.llamadas_f == 0 and func.llamadas_grad == 0
    assert rng.random() == np.random.default_rng(0).random()


# ---------------------------------------------------------------- k) anclas con funciones reales
# Valores de un cálculo independiente entregado en el encargo de T1.2 (12-oct-2026); no se ajustan
# para forzar la prueba.

ANCLAS = [
    ("rosenbrock", 2, 0.00188113761729464, [0.956664450501, 0.915028888636], 5000, 20000.0),
    ("rosenbrock", 3, 0.00116349071584227,
     [0.984691667467, 0.969559509834, 0.939897864465], 5000, 30000.0),
    ("rastrigin", 2, 4.97479024764738, [0.994958637778, -1.98991223375], 19, 76.0),
    ("rastrigin", 3, 29.8485131821896,
     [0.994958637678, -1.98991223372, -4.97469139088], 19, 114.0),
]


def _correr_real(nombre, dim, run_id, k=None, budget=None, record_frames=None):
    cfg = load_config(BASE_PART1)
    cfg["variante"] = "fijo"
    if record_frames is not None:
        cfg["record_frames"] = record_frames
    k = 2 * dim if k is None else k
    budget = 10_000 * dim if budget is None else budget
    problem = CountedProblem(get_function(nombre, dim), k=k, budget=budget)
    return gd.optimize(problem, cfg, make_rng(0, run_id))


# Paso fijo con la config base sobre Rosenbrock y Rastrigin reales reproduce valores calculados de
# forma independiente (f_best, x_best, n_grad, eval_equiv).
@pytest.mark.parametrize("nombre, dim, f_best, x_best, n_grad, eval_equiv", ANCLAS)
def test_anclas_funciones_reales(nombre, dim, f_best, x_best, n_grad, eval_equiv):
    res = _correr_real(nombre, dim, run_id=0)
    assert np.isclose(res["f_best"], f_best, rtol=1e-6, atol=1e-9)
    np.testing.assert_allclose(res["x_best"], x_best, rtol=1e-6, atol=1e-6)
    assert res["n_f"] == 0
    assert res["n_grad"] == n_grad
    assert res["eval_equiv"] == eval_equiv
    assert ("frames" in res) == (dim == 2)


# El x0 de Rosenbrock 2D con semilla 0 coincide con el valor de referencia (la semilla se usa bien).
def test_ancla_punto_inicial_rosenbrock_2d():
    res = _correr_real("rosenbrock", 2, run_id=0)
    np.testing.assert_allclose(res["frames"][0]["positions"][0], [0.56099507, -0.94295362],
                               atol=1e-8)


# ---------------------------------------------------------------- l) estadística con 30 semillas
# Valores de un cálculo independiente entregado en el encargo de T1.2 (12-oct-2026); no se ajustan
# para forzar la prueba.

# Paso fijo, Rosenbrock 2D, 30 semillas: mediana y tasas de éxito (1e-4 y 1e-2) de referencia.
def test_estadistica_30_semillas_rosenbrock_2d():
    f_best = [_correr_real("rosenbrock", 2, i, k=4, budget=20_000, record_frames=False)["f_best"]
              for i in range(30)]
    assert np.isclose(np.median(f_best), 0.0019054868310523, rtol=1e-6)
    assert sum(f <= 1e-4 for f in f_best) == 1
    assert sum(f <= 1e-2 for f in f_best) == 30


# Paso fijo, Rastrigin 2D, 30 semillas: ninguna corrida logra f ≤ 1e-4 y todas paran por ‖∇f‖ <
# tol mucho antes del presupuesto (16 a 23 evaluaciones de ∇f).
def test_estadistica_30_semillas_rastrigin_2d():
    res = [_correr_real("rastrigin", 2, i, k=4, budget=20_000, record_frames=False)
           for i in range(30)]
    assert sum(r["f_best"] <= 1e-4 for r in res) == 0
    assert all(16 <= r["n_grad"] <= 23 for r in res)


# ---------------------------------------------------------------- m) configuración

# base.yaml trae el bloque gd con los valores del Spec (η por función, η₀/β/c, tol_grad) y sin
# variante (la fija el runner): nada de números mágicos en el código.
def test_base_tiene_bloque_gd_del_spec():
    gd_cfg = load_config(BASE_PART1)["gd"]
    assert gd_cfg["eta"] == {"rosenbrock": 1e-3, "rastrigin": 2e-3}
    assert type(gd_cfg["eta"]["rosenbrock"]) is float and type(gd_cfg["eta"]["rastrigin"]) is float
    assert gd_cfg["armijo"] == {"eta0": 1.0, "beta": 0.5, "c": 1e-4}
    assert gd_cfg["tol_grad"] == 1e-8 and type(gd_cfg["tol_grad"]) is float
    assert "variante" not in load_config(BASE_PART1)


# demo.yaml hereda el bloque gd de base.yaml sin cambios.
def test_demo_hereda_bloque_gd():
    assert load_config(DEMO_PART1)["gd"] == load_config(BASE_PART1)["gd"]


# --set cambia una hoja del bloque gd sin tocar las demás y conserva el tipo float.
def test_overrides_del_bloque_gd():
    cfg = load_config(BASE_PART1)
    nuevo = apply_overrides(cfg, ["gd.eta.rastrigin=0.001"])
    assert nuevo["gd"]["eta"]["rastrigin"] == 0.001
    assert nuevo["gd"]["eta"]["rosenbrock"] == cfg["gd"]["eta"]["rosenbrock"]
    tol = apply_overrides(cfg, ["gd.tol_grad=1e-6"])["gd"]["tol_grad"]
    assert tol == 1e-6 and type(tol) is float


# Overrides inválidos (reemplazar el bloque gd.eta por un número o crear una clave nueva) fallan.
@pytest.mark.parametrize("override", ["gd.eta=0.5", "gd.eta.sphere=1"])
def test_overrides_invalidos_del_bloque_gd(override):
    with pytest.raises(ValueError):
        apply_overrides(load_config(BASE_PART1), [override])


# ================================================================ T1.3: variante "armijo"
# Búsqueda de paso con retroceso de Armijo (Spec §6.3): desde eta0, eta ← beta·eta hasta que el
# ensayo proyectado x' = Π(x − eta g) cumpla f(x') ≤ f(x) − c·<g, x − x'> (sin recorte, <g, x − x'>
# = eta‖g‖²). Cada ensayo cuesta 1 evaluación de f; f(x0) se cobra una sola vez y luego se reutiliza
# el f del ensayo aceptado, así que n_f = 1 + (número total de ensayos).

def _cfg_armijo(eta0=1.0, beta=0.5, c=1e-4, tol_grad=TOL_GRAD, record_frames=True):
    """Configuración mínima de la variante armijo, SIN la clave gd.eta (no se usa)."""
    return {
        "variante": "armijo",
        "gd": {"armijo": {"eta0": eta0, "beta": beta, "c": c}, "tol_grad": tol_grad},
        "record_frames": record_frames,
    }


def _correr_armijo(func, k=4, budget=10_000, seed=0, **kw):
    """Ejecuta la variante armijo sobre `func`; devuelve (resultado, problem)."""
    problem = CountedProblem(func, k=k, budget=budget)
    resultado = gd.optimize(problem, _cfg_armijo(**kw), np.random.default_rng(seed))
    return resultado, problem


def _t_estrella(d0, factor=0.5, tol=TOL_GRAD):
    """Primer t ≥ 0 con ||g_t|| = 2·d0·factor^t < tol (cuadrática con contracción `factor`)."""
    t = 0
    while not (2 * d0 * factor**t < tol):
        t += 1
    return t


def _f_cuadratica(x, x_star):
    return float(np.sum((np.asarray(x, dtype=float) - np.asarray(x_star, dtype=float)) ** 2))


# ---------------------------------------------------------------- P1-P3 cuentas exactas

# Armijo con un retroceso: n_f, n_grad y eval_equiv exactos (f(x0) + 2 ensayos; 2 gradientes).
@pytest.mark.parametrize("seed", range(5))
def test_armijo_cuenta_exacta_con_retroceso(cuadratica, seed):
    # eta = 1 lleva a −x0 (misma f: falla); eta = 0.5 lleva a x* = 0 (acepta); ∇f(0) = 0 para.
    res, _ = _correr_armijo(cuadratica([0.0, 0.0]), k=4, budget=10_000, seed=seed)
    assert res["n_f"] == 3 and res["n_grad"] == 2
    assert res["eval_equiv"] == 11.0
    assert res["x_best"] == [0.0, 0.0] and res["f_best"] == 0.0
    assert len(res["frames"]) == 2
    assert res["frames"][1]["positions"][0] == [0.0, 0.0]


# Sin retrocesos, n_f = 1 + pasos: f(x) se reutiliza del ensayo aceptado y no se vuelve a cobrar.
@pytest.mark.parametrize("seed", range(3))
def test_armijo_cuenta_exacta_sin_retroceso_reutiliza_f(cuadratica, seed):
    # eta0 = 0.25: el ensayo es el punto medio entre x y x* y se acepta:
    # x_{t+1} − x* = 0.5 (x_t − x*).
    k = 4
    res, _ = _correr_armijo(cuadratica(X_STAR_INTERIOR), eta0=0.25, k=k, seed=seed)
    d0 = np.linalg.norm(_x0(res) - np.array(X_STAR_INTERIOR))
    t = _t_estrella(d0)
    assert res["n_grad"] == t + 1
    assert res["n_f"] == t + 1                  # 1 por f(x0) + 1 ensayo por paso
    assert res["eval_equiv"] == res["n_f"] + k * res["n_grad"]


# Con η₀ = 0.5 el primer ensayo cae en x* y se acepta: 2 evaluaciones de f y 2 de ∇f.
def test_armijo_eta0_medio_cae_en_el_minimo(cuadratica):
    res, _ = _correr_armijo(cuadratica(X_STAR_INTERIOR), eta0=0.5)
    assert res["n_f"] == 2 and res["n_grad"] == 2
    assert res["x_best"] == X_STAR_INTERIOR


# β controla el retroceso: con β = 0.25 cada paso usa 2 ensayos, así que n_f = 1 + 2·pasos.
@pytest.mark.parametrize("seed", range(3))
def test_armijo_efecto_de_beta(cuadratica, seed):
    # beta = 0.25: cada paso son 2 ensayos (eta = 1 falla; eta = 0.25 lleva a 0.5 x).
    res, _ = _correr_armijo(cuadratica([0.0, 0.0]), eta0=1.0, beta=0.25, seed=seed)
    t = _t_estrella(np.linalg.norm(_x0(res)))
    assert res["n_grad"] == t + 1
    assert res["n_f"] == 1 + 2 * t


# ---------------------------------------------------------------- P4 presupuesto pequeño

# Presupuestos pequeños: optimize no lanza, los conteos son los esperados y eval_equiv ≤ budget,
# también cuando el presupuesto se agota en medio de la búsqueda lineal.
@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize(
    "budget, n_f, n_grad, eval_equiv",
    [(0.5, 0, 0, 0.0), (3, 0, 0, 0.0), (4, 0, 1, 4.0), (5, 1, 1, 5.0), (6, 2, 1, 6.0),
     (7, 3, 1, 7.0), (8, 3, 1, 7.0), (11, 3, 2, 11.0), (12, 3, 2, 11.0)],
)
def test_armijo_presupuesto_pequeno(cuadratica, seed, budget, n_f, n_grad, eval_equiv):
    # Ejecución.
    func = cuadratica([0.0, 0.0])
    res, problem = _correr_armijo(func, k=4, budget=budget, seed=seed)   # no lanza
    # Aserciones de conteo y presupuesto.
    assert (res["n_f"], res["n_grad"], res["eval_equiv"]) == (n_f, n_grad, eval_equiv)
    assert res["eval_equiv"] <= budget
    assert res["eval_equiv"] == problem.eval_equiv()
    # Aserciones del mejor punto: x0 si no se aceptó ningún paso; x* = 0 si se aceptó.
    x0 = _x0(res)
    if budget <= 6:
        assert res["x_best"] == x0.tolist()
        assert res["f_best"] == _f_cuadratica(x0, func.x_star)
    else:
        assert res["x_best"] == [0.0, 0.0] and res["f_best"] == 0.0


# ---------------------------------------------------------------- P5 evaluación perezosa

# f(x0) se cobra solo si hace falta: si el primer ∇f ya cumple la tolerancia, n_f = 0.
def test_armijo_evaluacion_perezosa(cuadratica):
    k = 4
    res, _ = _correr_armijo(cuadratica(X_STAR_INTERIOR), k=k, tol_grad=1e6)
    assert res["n_grad"] == 1 and res["n_f"] == 0
    assert res["x_best"] == _x0(res).tolist()
    assert res["eval_equiv"] == k
    assert len(res["frames"]) == 1


# ---------------------------------------------------------------- P6 conteo y registro

# Las llamadas reales a f son n_f cobradas + 1 observe de x0: no hay evaluaciones ocultas.
def test_armijo_conteo_y_registro(cuadratica):
    func = cuadratica(X_STAR_INTERIOR)
    res, problem = _correr_armijo(func, eta0=0.25)
    assert func.llamadas_f == res["n_f"] + 1     # n_f cobradas + 1 observe de x0
    assert func.llamadas_grad == res["n_grad"] == problem.n_grad
    assert problem.n_f == res["n_f"]


# ---------------------------------------------------------------- P7 proyección

# Con x* fuera del dominio, Armijo con proyección se queda dentro y, pegado al borde, acepta casi
# siempre con un solo ensayo: la condición sobre el ensayo proyectado evita gastar el presupuesto
# retrocediendo.
def test_armijo_proyeccion(cuadratica):
    # Ejecución.
    k, budget = 4, 400
    res, _ = _correr_armijo(cuadratica(X_STAR_EXTERIOR), k=k, budget=budget)
    # Aserciones: iterados dentro del dominio y mejor punto en el borde.
    posiciones = np.array([fr["positions"][0] for fr in res["frames"]])
    assert np.all(posiciones >= -LIMITE_CUADRATICA) and np.all(posiciones <= LIMITE_CUADRATICA)
    assert res["x_best"][0] == LIMITE_CUADRATICA
    assert res["x_best"][1] == pytest.approx(0.0, abs=1e-6)
    # No para por gradiente (‖g‖ ≥ 10 en el borde). Pegado al borde, el ensayo eta0 proyectado no
    # se mueve, <g, x − x'> = 0 y se acepta con un solo ensayo. Con la condición literal
    # c·eta·‖g‖² (sin proyección) la búsqueda gastaría el presupuesto retrocediendo.
    assert res["n_grad"] >= 70
    assert res["n_f"] - res["n_grad"] <= 5
    assert budget - k < res["eval_equiv"] <= budget


# ---------------------------------------------------------------- P8 oráculo de Armijo

def _comprobar_oraculo_armijo(func, res, eta0, beta, c, k, budget):
    """Recalcula cada búsqueda lineal con func.f/func.grad directos (sin contador)."""
    lo, hi = func.bounds[:, 0], func.bounds[:, 1]
    posiciones = [np.array(fr["positions"][0]) for fr in res["frames"]]
    ensayos_totales = 0
    for x, x_sig in zip(posiciones, posiciones[1:]):
        g = np.asarray(func.grad(x), dtype=float)
        fx = float(func.f(x))
        eta, j, rechazados = eta0, 0, []
        while True:
            cand = np.clip(x - eta * g, lo, hi)
            if np.array_equal(cand, x_sig):
                break
            rechazados.append(cand)
            eta *= beta
            j += 1
            assert j <= 200, "el frame siguiente no es ningún ensayo eta0·beta^j"
        f_sig = float(func.f(x_sig))
        assert f_sig <= fx - c * float(np.dot(g, x - x_sig))            # (i) Armijo
        for cand in rechazados:                                         # (ii) mayor paso válido
            assert not (float(func.f(cand)) <= fx - c * float(np.dot(g, x - cand)))
        # (iii) consecuencia de (i): el descenso proyectado es >= 0
        assert f_sig <= fx
        ensayos_totales += j + 1
    pasos = len(posiciones) - 1
    assert res["n_f"] >= 1 + ensayos_totales                            # (iv)
    assert res["n_f"] + k * res["n_grad"] == res["eval_equiv"] <= budget
    # Cada paso aceptado va precedido de un gradiente: pasos + 1 si el último gradiente paró por
    # ‖g‖ < tol o no hubo presupuesto para la búsqueda; pasos si el presupuesto se agotó justo al
    # pedir el siguiente gradiente.
    assert res["n_grad"] in (pasos, pasos + 1)


# Oráculo: cada paso aceptado cumple Armijo, es el mayor η₀·β^j válido y n_f, n_grad y eval_equiv
# son coherentes con los ensayos, en Rosenbrock, Rastrigin y la cuadrática con proyección.
@pytest.mark.parametrize(
    "caso, seed, eta0, beta, c, budget",
    [("rosenbrock", 0, 1.0, 0.5, 1e-4, 2000),
     ("rastrigin", 1, 1.0, 0.5, 1e-4, 2000),
     ("cuadratica", 0, 1.0, 0.5, 1e-4, 200),
     ("rosenbrock", 2, 0.3, 0.7, 1e-2, 2000)],
)
def test_armijo_oraculo(cuadratica, caso, seed, eta0, beta, c, budget):
    k = 4
    func = cuadratica(X_STAR_EXTERIOR) if caso == "cuadratica" else get_function(caso, 2)
    res, _ = _correr_armijo(func, k=k, budget=budget, seed=seed, eta0=eta0, beta=beta, c=c)
    assert len(res["frames"]) > 1
    _comprobar_oraculo_armijo(func, res, eta0, beta, c, k, budget)


# ---------------------------------------------------------------- P9 frames

# Frames de Armijo: forma de §5.1, frame 0 = x0 de la semilla, "best" no empeora y el último
# coincide con x_best.
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200),
                                            ([0.0, 0.0], 6)])
def test_armijo_frames(cuadratica, x_star, budget):
    func = cuadratica(x_star)
    res, _ = _correr_armijo(func, budget=budget, seed=3)
    frames = res["frames"]
    _comprobar_forma_frames(frames)
    lo, hi = func.bounds[:, 0], func.bounds[:, 1]
    assert frames[0]["positions"][0] == np.random.default_rng(3).uniform(lo, hi).tolist()
    f_best = [_f_cuadratica(fr["best"], x_star) for fr in frames]
    assert all(b <= a for a, b in zip(f_best, f_best[1:]))
    assert frames[-1]["best"] == res["x_best"]


# x_best puede ser un ensayo rechazado: problem.f registra todos los ensayos en best/history.
def test_armijo_mejor_visto_es_un_ensayo_rechazado(cuadratica):
    # f = ||x||², eta0 = 0.5, c = 0.9: el primer ensayo cae exactamente en x* = 0 (f = 0), pero se
    # rechaza porque 0 ≤ (1 − 2c)·f(x) es falso; eta = 0.25 y 0.125 también fallan y se acepta
    # eta = 0.0625 (f(x') = 0.765625 f(x) ≤ 0.775 f(x)), es decir x' = 0.875 x.
    # El mejor visto es x*.
    # Ejecución.
    res, _ = _correr_armijo(cuadratica([0.0, 0.0]), eta0=0.5, c=0.9, budget=200)
    # Aserciones: el mejor es x*, pero ningún frame (punto aceptado) pasa por x*.
    assert res["x_best"] == [0.0, 0.0] and res["f_best"] == 0.0
    frames = res["frames"]
    np.testing.assert_allclose(frames[1]["positions"][0], 0.875 * _x0(res), rtol=1e-15)
    assert all(fr["best"] == [0.0, 0.0] for fr in frames[1:])
    assert all(fr["positions"][0] != [0.0, 0.0] for fr in frames)


# Sin frames si record_frames es False, si falta la clave o si la dimensión es 3.
def test_armijo_frames_ausentes(cuadratica):
    res, _ = _correr_armijo(cuadratica(X_STAR_INTERIOR), record_frames=False)
    assert "frames" not in res
    cfg = _cfg_armijo()
    del cfg["record_frames"]
    problem = CountedProblem(cuadratica(X_STAR_INTERIOR), k=4, budget=10_000)
    assert "frames" not in gd.optimize(problem, cfg, np.random.default_rng(0))
    res3, _ = _correr_armijo(cuadratica([1.0, -2.0, 0.5]), k=6)
    assert "frames" not in res3


# ---------------------------------------------------------------- P10 historial

# history de Armijo: empieza en x0 con eval_equiv 0, f_best baja estrictamente, eval_equiv sube y
# termina en f_best; es la curva de convergencia de las figuras.
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200),
                                            ([0.0, 0.0], 10_000)])
def test_armijo_historial(cuadratica, x_star, budget):
    # Ejecución.
    func = cuadratica(x_star)
    res, problem = _correr_armijo(func, budget=budget)
    hist = res["history"]
    # Aserciones: igual al del contador, primer punto, monotonía y cierre.
    assert hist == problem.history
    assert hist[0] == {"eval_equiv": 0.0, "f_best": _f_cuadratica(_x0(res), x_star)}
    f_hist = [h["f_best"] for h in hist]
    e_hist = [h["eval_equiv"] for h in hist]
    assert all(b < a for a, b in zip(f_hist, f_hist[1:]))
    assert all(b > a for a, b in zip(e_hist, e_hist[1:]))
    assert e_hist[-1] <= res["eval_equiv"]
    assert hist[-1]["f_best"] == res["f_best"]


# ---------------------------------------------------------------- P11 reproducibilidad

# Misma semilla, mismo resultado; otra semilla, otro x0.
def test_armijo_reproducible(cuadratica):
    a, _ = _correr_armijo(cuadratica(X_STAR_EXTERIOR), budget=200, seed=7)
    b, _ = _correr_armijo(cuadratica(X_STAR_EXTERIOR), budget=200, seed=7)
    assert a == b
    otra, _ = _correr_armijo(cuadratica(X_STAR_EXTERIOR), budget=200, seed=8)
    assert otra["frames"][0]["positions"] != a["frames"][0]["positions"]


# Armijo tampoco usa el rng más allá de x0: una sola llamada uniform, igual que el testigo.
@pytest.mark.parametrize("dim", [2, 3])
def test_armijo_una_sola_llamada_al_rng(cuadratica, dim):
    func = cuadratica(np.ones(dim))
    problem = CountedProblem(func, k=2 * dim, budget=1_000)
    rng = np.random.default_rng(11)
    gd.optimize(problem, _cfg_armijo(), rng)
    testigo = np.random.default_rng(11)
    testigo.uniform(func.bounds[:, 0], func.bounds[:, 1])
    assert rng.random() == testigo.random()


# ---------------------------------------------------------------- P12 JSON y tipos

# Resultado de Armijo serializable a JSON (sin NaN/inf), claves de §5.1, tipos nativos y n_f > 0.
@pytest.mark.parametrize("x_star, budget", [(X_STAR_INTERIOR, 10_000), (X_STAR_EXTERIOR, 200),
                                            ([0.0, 0.0], 7)])
def test_armijo_serializable_y_tipos(cuadratica, x_star, budget):
    res, _ = _correr_armijo(cuadratica(x_star), budget=budget)
    json.dumps(res, allow_nan=False)
    assert set(res) == {"x_best", "f_best", "n_f", "n_grad", "eval_equiv", "history", "frames"}
    assert type(res["f_best"]) is float
    assert type(res["n_f"]) is int and res["n_f"] > 0
    assert type(res["n_grad"]) is int
    assert type(res["eval_equiv"]) is float
    assert type(res["x_best"]) is list and all(type(v) is float for v in res["x_best"])


# ---------------------------------------------------------------- P13 validaciones

# La variante armijo funciona sin la clave gd.eta: no se lee ni se exige.
def test_armijo_cfg_valido_sin_gd_eta(cuadratica):
    cfg = _cfg_armijo()
    assert "eta" not in cfg["gd"]
    res = _optimizar_con(cuadratica, cfg)
    assert res["n_grad"] > 0


# η₀ fuera de (0, ∞), β o c fuera de (0, 1), bool o texto: ValueError que nombra la clave exacta.
@pytest.mark.parametrize(
    "clave, valor",
    [("eta0", v) for v in (0, -1, math.nan, math.inf, True, False, "1")]
    + [("beta", v) for v in (0, 1, 1.0, 1.5, -0.5, math.nan, True, "0.5")]
    + [("c", v) for v in (0, 1, 2, -1e-4, math.nan, math.inf, True)],
)
def test_armijo_parametro_invalido(cuadratica, clave, valor):
    cfg = _cfg_armijo()
    cfg["gd"]["armijo"][clave] = valor
    with pytest.raises(ValueError, match=re.escape(f"gd.armijo.{clave}")):
        _optimizar_con(cuadratica, cfg)


# tol_grad inválido también se rechaza en la variante armijo.
@pytest.mark.parametrize("tol", [0, -1e-8, math.nan, True])
def test_armijo_tol_grad_invalido(cuadratica, tol):
    with pytest.raises(ValueError, match="tol_grad"):
        _optimizar_con(cuadratica, _cfg_armijo(tol_grad=tol))


# Sin el bloque gd.armijo, la variante armijo falla con un mensaje que lo nombra.
def test_armijo_bloque_ausente(cuadratica):
    cfg = _cfg_armijo()
    del cfg["gd"]["armijo"]
    with pytest.raises(ValueError, match=re.escape("gd.armijo")):
        _optimizar_con(cuadratica, cfg)


# gd.armijo que no es un mapa (número, None, lista, texto) se rechaza.
@pytest.mark.parametrize("bloque", [0.5, None, [1.0, 0.5, 1e-4], "armijo"])
def test_armijo_bloque_no_mapa(cuadratica, bloque):
    cfg = _cfg_armijo()
    cfg["gd"]["armijo"] = bloque
    with pytest.raises(ValueError, match=re.escape("gd.armijo")):
        _optimizar_con(cuadratica, cfg)


# Falta una de las claves eta0, beta, c: el error indica cuál.
@pytest.mark.parametrize("clave", ["eta0", "beta", "c"])
def test_armijo_clave_faltante(cuadratica, clave):
    cfg = _cfg_armijo()
    del cfg["gd"]["armijo"][clave]
    with pytest.raises(ValueError, match=re.escape(f"gd.armijo.{clave}")):
        _optimizar_con(cuadratica, cfg)


# Parámetros de Armijo inválidos fallan antes de evaluar f/∇f y de usar el rng.
@pytest.mark.parametrize("clave, valor", [("eta0", -1.0), ("beta", 1.0), ("c", 0)])
def test_armijo_validacion_no_evalua_ni_usa_el_rng(cuadratica, clave, valor):
    func = cuadratica(X_STAR_INTERIOR)
    problem = CountedProblem(func, k=4, budget=100)
    rng = np.random.default_rng(0)
    cfg = _cfg_armijo()
    cfg["gd"]["armijo"][clave] = valor
    with pytest.raises(ValueError):
        gd.optimize(problem, cfg, rng)
    assert func.llamadas_f == 0 and func.llamadas_grad == 0
    assert rng.random() == np.random.default_rng(0).random()


# ---------------------------------------------------------------- P14 anclas con funciones reales
# Valores de un cálculo independiente entregado en el encargo de T1.3 (12-oct-2026); no se ajustan
# para forzar la prueba. En Rastrigin NO se afirman n_f ni n_grad: cerca del mínimo local la mejora
# de f queda por debajo de la resolución de la coma flotante, la condición de Armijo se decide por
# ruido de redondeo y los conteos dependen del último bit de cos/sin en cada plataforma.

ANCLAS_ARMIJO = [
    ("rosenbrock", 2, 0.00971528760766552, [1.09816487097, 1.20685459785], 14332, 1417, 20000.0),
    ("rosenbrock", 3, 0.000452520067148472,
     [0.99046956164, 0.981016381037, 0.962279359182], 18846, 1859, 30000.0),
    ("rastrigin", 2, 1.98991811418658, [-0.994958638488, 0.994958637863], None, None, None),
    ("rastrigin", 3, 4.97479024764738,
     [-1.38478600414e-09, 0.994958637013, -1.98991223309], None, None, None),
]


def _correr_real_armijo(nombre, dim, run_id, k=None, budget=None, record_frames=None, cfg=None):
    if cfg is None:
        cfg = load_config(BASE_PART1)
    cfg["variante"] = "armijo"
    if record_frames is not None:
        cfg["record_frames"] = record_frames
    k = 2 * dim if k is None else k
    budget = 10_000 * dim if budget is None else budget
    problem = CountedProblem(get_function(nombre, dim), k=k, budget=budget)
    return gd.optimize(problem, cfg, make_rng(0, run_id))


# Armijo con la config base sobre las funciones reales reproduce los valores de referencia (conteos
# solo en Rosenbrock; en Rastrigin dependen del redondeo de la plataforma).
@pytest.mark.parametrize("nombre, dim, f_best, x_best, n_f, n_grad, eval_equiv", ANCLAS_ARMIJO)
def test_armijo_anclas_funciones_reales(nombre, dim, f_best, x_best, n_f, n_grad, eval_equiv):
    res = _correr_real_armijo(nombre, dim, run_id=0)
    assert np.isclose(res["f_best"], f_best, rtol=1e-6, atol=1e-9)
    np.testing.assert_allclose(res["x_best"], x_best, rtol=0, atol=1e-6)
    if n_f is not None:
        assert res["n_f"] == n_f
        assert res["n_grad"] == n_grad
        assert res["eval_equiv"] == eval_equiv
    assert ("frames" in res) == (dim == 2)


# El x0 de Armijo con semilla 0 es el mismo que en paso fijo: ambas variantes comparten el inicio.
def test_armijo_ancla_punto_inicial_rosenbrock_2d():
    res = _correr_real_armijo("rosenbrock", 2, run_id=0)
    np.testing.assert_allclose(res["frames"][0]["positions"][0], [0.56099507, -0.94295362],
                               atol=1e-8)


# ---------------------------------------------------------------- P15 estadística con 30 semillas
# Valores de un cálculo independiente entregado en el encargo de T1.3 (12-oct-2026); no se ajustan.

MINIMOS_LOCALES_RASTRIGIN_2D = [0.0, 0.994959, 1.989918, 3.979831, 4.97479, 7.959662, 12.934432,
                                15.919244, 19.899075]


# Armijo, Rosenbrock 2D, 30 semillas: mediana, tasas de éxito y rangos de n_grad y n_f esperados.
def test_armijo_estadistica_30_semillas_rosenbrock_2d():
    res = [_correr_real_armijo("rosenbrock", 2, i, k=4, budget=20_000, record_frames=False)
           for i in range(30)]
    f_best = [r["f_best"] for r in res]
    assert np.isclose(np.median(f_best), 0.00232603586853428, rtol=1e-6)
    assert sum(f <= 1e-4 for f in f_best) == 5
    assert sum(f <= 1e-2 for f in f_best) == 19
    assert all(1368 <= r["n_grad"] <= 1484 for r in res)
    assert all(14064 <= r["n_f"] <= 14528 for r in res)


# Armijo, Rastrigin 2D, 30 semillas: semillas exitosas de referencia y cada f_best a < 2e-6 de algún
# valor de MINIMOS_LOCALES_RASTRIGIN_2D.
def test_armijo_estadistica_30_semillas_rastrigin_2d():
    res = [_correr_real_armijo("rastrigin", 2, i, k=4, budget=20_000, record_frames=False)
           for i in range(30)]
    exitos = [i for i, r in enumerate(res) if r["f_best"] <= 1e-4]
    assert exitos == [5, 10, 12, 17, 25]
    for r in res:
        assert min(abs(r["f_best"] - m) for m in MINIMOS_LOCALES_RASTRIGIN_2D) < 2e-6


# ---------------------------------------------------------------- P16 configuración

# --set gd.armijo.beta cambia solo β (float) y la corrida con esa config respeta el presupuesto.
def test_armijo_override_beta():
    cfg = load_config(BASE_PART1)
    nuevo = apply_overrides(cfg, ["gd.armijo.beta=0.8"])
    assert nuevo["gd"]["armijo"]["beta"] == 0.8 and type(nuevo["gd"]["armijo"]["beta"]) is float
    assert nuevo["gd"]["armijo"]["eta0"] == cfg["gd"]["armijo"]["eta0"]
    assert nuevo["gd"]["armijo"]["c"] == cfg["gd"]["armijo"]["c"]
    res = _correr_real_armijo("rosenbrock", 2, run_id=0, budget=500, cfg=nuevo)
    assert 0 < res["eval_equiv"] <= 500


# Overrides inválidos (reemplazar el bloque gd.armijo por un número o crear una clave nueva) fallan.
@pytest.mark.parametrize("override", ["gd.armijo=0.5", "gd.armijo.alfa=1"])
def test_armijo_overrides_invalidos(override):
    with pytest.raises(ValueError):
        apply_overrides(load_config(BASE_PART1), [override])
