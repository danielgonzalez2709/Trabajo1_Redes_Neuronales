"""Pruebas de `src/viz/part1_datos.py` (T4.2; Spec §6.7): datos de las figuras de la Parte 1, con corridas sintéticas.

Ninguna prueba depende de `results/data/part1/runs/` (ignorada por git).
"""
import copy

import numpy as np
import pytest

from src.part1.functions import get_function
from src.viz import part1_datos as pd1
from tests.sinteticos_part1 import CONFIG, corrida, escribir_experimento

TRES = [
    corrida(seed=0, history=[(1, 8), (10, 4), (50, 1)]),
    corrida(seed=1, history=[(5, 6), (20, 2)]),
    corrida(seed=2, history=[(1, 10)]),
]


# --------------------------------------------------------------------------------------------- rejilla


def test_rejilla_geometrica_de_enteros_unicos_de_1_al_presupuesto():
    r = pd1.rejilla(20000.0)
    assert r[0] == 1 and r[-1] == 20000
    assert np.issubdtype(r.dtype, np.integer)
    assert np.all(np.diff(r) > 0)
    assert 150 <= r.size <= pd1.PUNTOS_REJILLA


def test_rejilla_rechaza_presupuesto_no_entero_o_menor_que_1():
    for malo in (0, 10.5):
        with pytest.raises(ValueError):
            pd1.rejilla(malo)


# ------------------------------------------------------------------------------------ curva de convergencia


def _en(curva, x):
    (i,) = np.flatnonzero(curva["rejilla"] == x)
    return {k: curva[k][i] for k in ("mediana", "q25", "q75")}


def test_curva_en_escalon_con_mediana_y_cuartiles_a_mano():
    curva = pd1.curva_convergencia(TRES, f_star=0.0)
    assert curva["rejilla"][-1] == 100  # último punto de la rejilla = presupuesto
    # x = 1: A = 8, B aún sin registro (NaN, se ignora), C = 10
    assert _en(curva, 1) == pytest.approx({"mediana": 9.0, "q25": 8.5, "q75": 9.5})
    # x = 9: sigue el valor del último registro con eval_equiv <= x
    assert _en(curva, 9) == pytest.approx({"mediana": 8.0, "q25": 7.0, "q75": 9.0})  # A = 8, B = 6, C = 10
    assert _en(curva, 10) == pytest.approx({"mediana": 6.0, "q25": 5.0, "q75": 8.0})  # A = 4, B = 6, C = 10
    # x = presupuesto: el valor se mantiene constante desde el último registro (A = 1, B = 2, C = 10)
    assert _en(curva, 100) == pytest.approx({"mediana": 2.0, "q25": 1.5, "q75": 6.0})


def test_curva_resta_f_star():
    curva = pd1.curva_convergencia(TRES, f_star=0.5)
    assert _en(curva, 100)["mediana"] == pytest.approx(1.5)


def test_curva_nan_antes_del_primer_registro_de_todas_las_corridas():
    curva = pd1.curva_convergencia([corrida(history=[(5, 6), (20, 2)])], f_star=0.0)
    antes = curva["rejilla"] < 5
    assert antes.any()
    for k in ("mediana", "q25", "q75"):
        assert np.all(np.isnan(curva[k][antes])) and not np.any(np.isnan(curva[k][~antes]))
    assert curva["mediana"][-1] == 2.0  # constante hasta el presupuesto


def test_curva_registro_en_cero_cuenta_desde_el_primer_punto():
    curva = pd1.curva_convergencia([corrida(method="gdfijo", history=[(0, 7), (4, 3)])], f_star=0.0)
    assert _en(curva, 1)["mediana"] == 7.0 and _en(curva, 4)["mediana"] == 3.0


def test_curva_exige_un_presupuesto_comun():
    with pytest.raises(ValueError, match="presupuesto"):
        pd1.curva_convergencia([corrida(seed=0), corrida(seed=1, budget=200.0)], f_star=0.0)


def test_f_finales_resta_f_star_por_corrida():
    assert pd1.f_finales(TRES, f_star=0.25) == pytest.approx([0.75, 1.75, 9.75])


# ----------------------------------------------------------------------------------------------- malla


@pytest.mark.parametrize("nombre", ["rosenbrock", "rastrigin"])
def test_malla_cubre_el_dominio_y_evalua_f(nombre):
    func = get_function(nombre, 2)
    x, y, z = pd1.malla(nombre, 9)
    assert x.shape == y.shape == (9,) and z.shape == (9, 9)
    assert (x[0], x[-1]) == tuple(func.bounds[0]) and (y[0], y[-1]) == tuple(func.bounds[1])
    assert z[2, 5] == pytest.approx(func.f([x[5], y[2]]))  # z[fila = y, columna = x], como espera Plotly


# ----------------------------------------------------------------------------------- métodos afinados


def _grupos(config, metodos=("gdfijo", "gdarmijo", "pso"), funcs=("rosenbrock", "rastrigin")):
    return {(f, 2, m): [corrida(func=f, method=m, seed=s, config=config) for s in (0, 1)]
            for f in funcs for m in metodos}


def test_metodos_afinados_solo_eta_de_rosenbrock():
    afinada = copy.deepcopy(CONFIG)
    afinada["gd"]["eta"]["rosenbrock"] = 1.5e-3
    cambios = pd1.metodos_afinados(_grupos(CONFIG), _grupos(afinada))
    assert cambios == {("rosenbrock", 2): ["gdfijo"], ("rastrigin", 2): []}


def test_metodos_afinados_armijo_cambia_en_todas_y_pso_igual_no_aparece():
    afinada = copy.deepcopy(CONFIG)
    afinada["gd"]["armijo"]["beta"] = 0.2
    afinada["salida"] = "otra/carpeta"  # claves ajenas a los hiperparámetros no cuentan
    cambios = pd1.metodos_afinados(_grupos(CONFIG), _grupos(afinada))
    assert cambios == {("rosenbrock", 2): ["gdarmijo"], ("rastrigin", 2): ["gdarmijo"]}


def test_metodos_afinados_bloque_propio():
    afinada = copy.deepcopy(CONFIG)
    afinada["pso"]["w"] = 0.5
    cambios = pd1.metodos_afinados(_grupos(CONFIG), _grupos(afinada))
    assert cambios == {("rosenbrock", 2): ["pso"], ("rastrigin", 2): ["pso"]}


# ------------------------------------------------------------------------------------- comparabilidad


def test_comparables_acepta_mismas_semillas_presupuesto_y_k():
    pd1.comprobar_comparables(_grupos(CONFIG), _grupos(CONFIG))


@pytest.mark.parametrize("cambio", [{"seed": 7}, {"budget": 200.0}, {"k": 1.0}])
def test_comparables_rechaza_metas_distintas(cambio):
    otro = _grupos(CONFIG)
    otro[("rosenbrock", 2, "pso")][1].update(cambio)
    with pytest.raises(ValueError):
        pd1.comprobar_comparables(_grupos(CONFIG), otro)


def test_comparables_rechaza_configuraciones_que_faltan():
    otro = _grupos(CONFIG)
    del otro[("rastrigin", 2, "pso")]
    with pytest.raises(ValueError):
        pd1.comprobar_comparables(_grupos(CONFIG), otro)


# ------------------------------------------------------------------------------------------------ carga


def _escribir_experimento(carpeta, omitir=None):
    corridas = {("rosenbrock", 2, m): [corrida(method=m, seed=s) for s in (0, 1)] for m in ("gdfijo", "pso")}
    escribir_experimento(carpeta, corridas, semillas=(0, 1), omitir=omitir)


def test_cargar_experimento_agrupa_por_configuracion_en_el_orden_de_meta(tmp_path):
    _escribir_experimento(tmp_path)
    exp = pd1.cargar_experimento(tmp_path)
    assert list(exp["corridas"]) == [("rosenbrock", 2, "gdfijo"), ("rosenbrock", 2, "pso")]
    assert [c["seed"] for c in exp["corridas"][("rosenbrock", 2, "pso")]] == [0, 1]
    assert exp["meta"]["semillas"] == [0, 1]


def test_cargar_experimento_incompleto_o_ausente_lanza_datos_faltantes(tmp_path):
    with pytest.raises(pd1.DatosFaltantes):
        pd1.cargar_experimento(tmp_path / "no_existe")
    _escribir_experimento(tmp_path, omitir=("rosenbrock", 2, "pso", 1))
    with pytest.raises(pd1.DatosFaltantes, match="1 de 4"):
        pd1.cargar_experimento(tmp_path)
