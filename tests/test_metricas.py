"""Pruebas de las métricas de la Parte 1 (T1.7; Spec §5.4, §6.2, §6.5 y §6.6).

Un grupo de pruebas por pieza de `src/part1/metricas.py`:

    1. constantes y clave_umbral
    2. resumir_configuracion   -> estadísticas de f_final calculadas a mano
    3. resumir_configuracion   -> tasas de éxito y evaluaciones hasta el éxito
    4. resumir_configuracion   -> evaluaciones equivalentes (k real, k = 2n y k = 1)
    5. resumir_configuracion   -> entradas inválidas
    6. avisos
    7. salidas sin NaN/inf, con tipos nativos y guardables con save_json
    8. formatear_tabla_consola y a_filas_csv
    9. higiene del archivo

Las corridas son SINTÉTICAS (diccionarios del Spec §5.4 escritos a mano): aquí no se ejecuta
ningún optimizador. Los valores esperados están escritos como literales.
"""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.common.results import load_json, save_json
from src.part1 import metricas
from src.part1.metricas import (
    METODO_SIN_F,
    METODOS_SIN_GRADIENTE,
    TOLERANCIA_BAJO_F_STAR,
    UMBRAL_PRINCIPAL,
    UMBRALES,
    a_filas_csv,
    avisos,
    clave_umbral,
    formatear_tabla_consola,
    resumir_configuracion,
)

RUTA_METRICAS = Path(metricas.__file__)
LARGO_MAXIMO = 100
CLAVES_UMBRAL = ("1e-04", "1e-02", "1e-06")
CLAVES_RESUMEN = (
    "func", "dim", "method", "k", "n_corridas", "f_final", "n_f_medio", "n_grad_medio",
    "eval_equiv_medio", "eval_equiv_medio_k2n", "eval_equiv_medio_k1", "tasa_exito",
    "evals_hasta_exito_medio",
)
CLAVES_F_FINAL = ("media", "desv", "mediana", "mejor", "peor")


# ------------------------------------------------------------------------------------------
# Constructores de corridas sintéticas (Spec §5.4)

def corrida(f_best, historia=None, *, func="rastrigin", dim=2, method="pso", seed=0, k=4.0,
            budget=20000.0, n_f=100, n_grad=0, eval_equiv=None):
    """Diccionario de una corrida (§5.4). `historia` es una lista de pares (eval_equiv, f_best).

    Sin `historia` se usa un solo punto con el `f_best` final; sin `eval_equiv` se calcula
    n_f + k·n_grad.
    """
    if eval_equiv is None:
        eval_equiv = float(n_f + k * n_grad)
    if historia is None:
        historia = [(1.0, f_best)]
    return {
        "func": func, "dim": dim, "method": method, "seed": seed, "k": k, "budget": budget,
        "config": {},
        "result": {
            "x_best": [0.0] * dim, "f_best": f_best, "n_f": n_f, "n_grad": n_grad,
            "eval_equiv": eval_equiv,
            "history": [{"eval_equiv": float(e), "f_best": f} for e, f in historia],
        },
    }


def corridas_estadisticas():
    """4 corridas con f_best = 1, 2, 3, 6 (ninguna exitosa) y n_f = 100, 200, 300, 400."""
    return [corrida(f, seed=i, n_f=n)
            for i, (f, n) in enumerate([(1.0, 100), (2.0, 200), (3.0, 300), (6.0, 400)])]


def corridas_umbrales():
    """5 corridas de Rastrigin (f* = 0) que separan los tres umbrales.

    f_best: 0.0 y 5e-7 (éxito en los tres), 1e-4 (justo en el borde del principal),
    5e-3 (solo 1e-2) y 2.0 (ninguno).
    """
    return [
        corrida(0.0, [(30, 5.0), (60, 5e-3), (90, 5e-5), (120, 5e-7), (150, 0.0)], seed=0),
        corrida(5e-7, [(30, 1.0), (200, 8e-5), (400, 5e-7)], seed=1),
        corrida(1e-4, [(30, 3.0), (500, 1e-4)], seed=2),
        corrida(5e-3, [(30, 0.5), (700, 5e-3)], seed=3),
        corrida(2.0, [(30, 2.0)], seed=4),
    ]


def corrida_gd(k, eval_equiv):
    """GD sintético en dim 2 con n_f = 3 y n_grad = 10."""
    return corrida(0.5, method="gdarmijo", k=k, n_f=3, n_grad=10, eval_equiv=eval_equiv)


def no_finitos(objeto, ruta="$"):
    """Rutas de todos los float NaN/inf dentro de dicts, listas y tuplas anidados."""
    if isinstance(objeto, float) and not math.isfinite(objeto):
        return [ruta]
    if isinstance(objeto, dict):
        return [r for c, v in objeto.items() for r in no_finitos(v, f"{ruta}.{c}")]
    if isinstance(objeto, (list, tuple)):
        return [r for i, v in enumerate(objeto) for r in no_finitos(v, f"{ruta}[{i}]")]
    return []


def tipos_no_nativos(objeto, ruta="$"):
    """Rutas de los valores cuyo tipo exacto no es None, bool, int, float, str, dict o list."""
    if type(objeto) is dict:
        return [r for c, v in objeto.items() for r in tipos_no_nativos(v, f"{ruta}.{c}")]
    if type(objeto) is list:
        return [r for i, v in enumerate(objeto) for r in tipos_no_nativos(v, f"{ruta}[{i}]")]
    if objeto is None or type(objeto) in (bool, int, float, str):
        return []
    return [f"{ruta} ({type(objeto).__name__})"]


# ------------------------------------------------------------------------------------------
# 1. Constantes y clave_umbral

def test_constantes_del_spec():
    assert UMBRAL_PRINCIPAL == 1e-4
    assert UMBRALES == (1e-4, 1e-2, 1e-6)
    assert TOLERANCIA_BAJO_F_STAR == 1e-9
    assert METODOS_SIN_GRADIENTE == ("ea", "pso", "de")
    assert METODO_SIN_F == "gdfijo"


def test_clave_umbral():
    assert clave_umbral(1e-4) == "1e-04"
    assert clave_umbral(1e-2) == "1e-02"
    assert clave_umbral(1e-6) == "1e-06"
    assert tuple(clave_umbral(u) for u in UMBRALES) == CLAVES_UMBRAL


# ------------------------------------------------------------------------------------------
# 2. Estadísticas de f_final calculadas a mano

def test_claves_y_orden_del_resumen():
    resumen = resumir_configuracion(corridas_estadisticas())
    assert tuple(resumen) == CLAVES_RESUMEN
    assert tuple(resumen["f_final"]) == CLAVES_F_FINAL
    assert tuple(resumen["tasa_exito"]) == CLAVES_UMBRAL
    assert tuple(resumen["evals_hasta_exito_medio"]) == CLAVES_UMBRAL


def test_identificacion_de_la_configuracion():
    resumen = resumir_configuracion(corridas_estadisticas())
    assert resumen["func"] == "rastrigin"
    assert resumen["dim"] == 2
    assert resumen["method"] == "pso"
    assert resumen["k"] == 4.0
    assert resumen["n_corridas"] == 4


def test_estadisticas_de_f_final_a_mano():
    # f_best = 1, 2, 3, 6: media 3; desvíos -2, -1, 0, 3; suma de cuadrados 14.
    f_final = resumir_configuracion(corridas_estadisticas())["f_final"]
    assert f_final["media"] == pytest.approx(3.0, abs=1e-12)
    assert f_final["mediana"] == pytest.approx(2.5, abs=1e-12)
    assert f_final["mejor"] == 1.0
    assert f_final["peor"] == 6.0


def test_desviacion_muestral_ddof_1_y_no_ddof_0():
    f_final = resumir_configuracion(corridas_estadisticas())["f_final"]
    desv_ddof_1 = 2.160246899469287     # sqrt(14 / 3)
    desv_ddof_0 = 1.8708286933869707    # sqrt(14 / 4)
    assert f_final["desv"] == pytest.approx(desv_ddof_1, rel=1e-12)
    assert f_final["desv"] != pytest.approx(desv_ddof_0, rel=1e-6)


def test_las_estadisticas_no_dependen_del_orden_de_las_corridas():
    corridas = corridas_estadisticas()
    assert resumir_configuracion(corridas[::-1])["f_final"] == pytest.approx(
        resumir_configuracion(corridas)["f_final"])


def test_n_f_y_n_grad_medios_por_separado():
    resumen = resumir_configuracion(corridas_estadisticas())
    assert resumen["n_f_medio"] == pytest.approx(250.0)
    assert resumen["n_grad_medio"] == 0.0

    gd = [corrida(0.5, method="gdarmijo", seed=0, n_f=3, n_grad=10),
          corrida(0.5, method="gdarmijo", seed=1, n_f=7, n_grad=30)]
    resumen = resumir_configuracion(gd)
    assert resumen["n_f_medio"] == pytest.approx(5.0)
    assert resumen["n_grad_medio"] == pytest.approx(20.0)


def test_una_sola_corrida_da_desviacion_none():
    resumen = resumir_configuracion([corrida(3.0)])
    assert resumen["n_corridas"] == 1
    assert resumen["f_final"] == {"media": 3.0, "desv": None, "mediana": 3.0, "mejor": 3.0,
                                  "peor": 3.0}


def test_no_modifica_las_corridas():
    corridas = corridas_umbrales()
    copia = corridas_umbrales()
    resumir_configuracion(corridas)
    assert corridas == copia


# ------------------------------------------------------------------------------------------
# 3. Tasas de éxito y evaluaciones hasta el éxito

def test_tasas_de_exito_en_los_tres_umbrales():
    tasas = resumir_configuracion(corridas_umbrales())["tasa_exito"]
    assert tasas["1e-04"] == pytest.approx(0.6)     # 0.0, 5e-7 y 1e-4 (borde)
    assert tasas["1e-02"] == pytest.approx(0.8)     # además 5e-3
    assert tasas["1e-06"] == pytest.approx(0.4)     # solo 0.0 y 5e-7


@pytest.mark.parametrize("umbral", UMBRALES)
def test_el_borde_exacto_cuenta_como_exito(umbral):
    clave = clave_umbral(umbral)
    en_el_borde = resumir_configuracion([corrida(umbral)])
    assert en_el_borde["tasa_exito"][clave] == 1.0
    apenas_por_encima = resumir_configuracion([corrida(math.nextafter(umbral, math.inf))])
    assert apenas_por_encima["tasa_exito"][clave] == 0.0


def test_evals_hasta_el_exito_toma_el_primer_punto_que_cumple():
    evals = resumir_configuracion(corridas_umbrales())["evals_hasta_exito_medio"]
    assert evals["1e-02"] == pytest.approx(365.0)           # (60 + 200 + 500 + 700) / 4
    assert evals["1e-04"] == pytest.approx(790.0 / 3.0)     # (90 + 200 + 500) / 3
    assert evals["1e-06"] == pytest.approx(260.0)           # (120 + 400) / 2


def test_evals_hasta_el_exito_no_es_el_ultimo_punto_de_la_historia():
    unica = [corrida(0.0, [(30, 5.0), (60, 5e-3), (90, 5e-5), (120, 5e-7), (150, 0.0)])]
    evals = resumir_configuracion(unica)["evals_hasta_exito_medio"]
    assert evals == {"1e-04": 90.0, "1e-02": 60.0, "1e-06": 120.0}


def test_none_cuando_ninguna_corrida_tiene_exito():
    resumen = resumir_configuracion(corridas_estadisticas())
    assert resumen["tasa_exito"] == {"1e-04": 0.0, "1e-02": 0.0, "1e-06": 0.0}
    assert resumen["evals_hasta_exito_medio"] == {"1e-04": None, "1e-02": None, "1e-06": None}


def test_none_solo_en_el_umbral_sin_exitos():
    resumen = resumir_configuracion([corrida(5e-3, [(30, 0.5), (700, 5e-3)])])
    assert resumen["evals_hasta_exito_medio"] == {"1e-04": None, "1e-02": 700.0, "1e-06": None}


def test_el_exito_se_mide_contra_f_star_de_la_funcion(monkeypatch):
    # Rosenbrock y Rastrigin tienen f* = 0: con un f* = 1 ficticio se ve que f* sí se resta.
    monkeypatch.setattr(metricas, "get_function",
                        lambda nombre, dim: SimpleNamespace(f_star=1.0))
    corridas = [corrida(1.0, [(10, 4.0), (20, 1.005), (40, 1.0)], seed=0),
                corrida(1.005, [(10, 4.0), (50, 1.005)], seed=1)]
    resumen = resumir_configuracion(corridas)
    assert resumen["tasa_exito"] == {"1e-04": 0.5, "1e-02": 1.0, "1e-06": 0.5}
    assert resumen["evals_hasta_exito_medio"] == {"1e-04": 40.0, "1e-02": 35.0, "1e-06": 40.0}
    assert resumen["f_final"]["mejor"] == 1.0     # f_final es f_best, sin restar f*


def test_get_function_recibe_func_y_dim_de_las_corridas(monkeypatch):
    llamadas = []

    def falsa(nombre, dim):
        llamadas.append((nombre, dim))
        return SimpleNamespace(f_star=0.0)

    monkeypatch.setattr(metricas, "get_function", falsa)
    resumir_configuracion([corrida(1.0, func="rosenbrock", dim=3)])
    assert set(llamadas) == {("rosenbrock", 3)}


def test_corrida_exitosa_sin_punto_de_historia_que_cumpla_es_error():
    incoherente = corrida(0.0, [(30, 5.0)])     # f_best final 0.0, pero la historia no llega
    with pytest.raises(ValueError, match="history"):
        resumir_configuracion([incoherente])


# ------------------------------------------------------------------------------------------
# 4. Evaluaciones equivalentes: k real, k = 2n y k = 1

def test_gd_con_k_1():
    resumen = resumir_configuracion([corrida_gd(k=1.0, eval_equiv=13.0)])
    assert resumen["k"] == 1.0
    assert resumen["eval_equiv_medio"] == 13.0
    assert resumen["eval_equiv_medio_k2n"] == 43.0      # 3 + 2·2·10
    assert resumen["eval_equiv_medio_k1"] == 13.0       # 3 + 10


def test_gd_con_k_2n():
    resumen = resumir_configuracion([corrida_gd(k=4.0, eval_equiv=43.0)])
    assert resumen["k"] == 4.0
    assert resumen["eval_equiv_medio"] == 43.0
    assert resumen["eval_equiv_medio_k2n"] == 43.0
    assert resumen["eval_equiv_medio_k1"] == 13.0


def test_eval_equiv_medio_sale_del_campo_de_la_corrida_y_no_se_recalcula():
    # eval_equiv = 999 no coincide con n_f + k·n_grad: se ve de dónde sale cada campo.
    resumen = resumir_configuracion([corrida_gd(k=4.0, eval_equiv=999.0)])
    assert resumen["eval_equiv_medio"] == 999.0
    assert resumen["eval_equiv_medio_k2n"] == 43.0
    assert resumen["eval_equiv_medio_k1"] == 13.0


def test_recosteo_k2n_usa_la_dimension():
    en_3d = corrida(0.5, func="rosenbrock", dim=3, method="gdarmijo", k=6.0, n_f=3, n_grad=10)
    resumen = resumir_configuracion([en_3d])
    assert resumen["eval_equiv_medio_k2n"] == 63.0      # 3 + 2·3·10
    assert resumen["eval_equiv_medio_k1"] == 13.0


def test_evaluaciones_equivalentes_son_medias_sobre_las_corridas():
    gd = [corrida(0.5, method="gdarmijo", seed=0, n_f=3, n_grad=10),      # 43 con k = 4
          corrida(0.5, method="gdarmijo", seed=1, n_f=7, n_grad=30)]      # 127 con k = 4
    resumen = resumir_configuracion(gd)
    assert resumen["eval_equiv_medio"] == pytest.approx(85.0)
    assert resumen["eval_equiv_medio_k2n"] == pytest.approx(85.0)
    assert resumen["eval_equiv_medio_k1"] == pytest.approx(25.0)       # (13 + 37) / 2


# ------------------------------------------------------------------------------------------
# 5. Entradas inválidas

def test_lista_vacia_es_error():
    with pytest.raises(ValueError, match="vacía"):
        resumir_configuracion([])


@pytest.mark.parametrize("campo, otro", [
    ("func", "rosenbrock"), ("dim", 3), ("method", "de"), ("k", 1.0),
])
def test_mezcla_de_configuraciones_es_error(campo, otro):
    mezcla = [corrida(1.0, seed=0), corrida(1.0, seed=1, **{campo: otro})]
    with pytest.raises(ValueError, match=campo):
        resumir_configuracion(mezcla)


def test_acepta_tuplas_y_no_solo_listas():
    assert resumir_configuracion(tuple(corridas_estadisticas()))["n_corridas"] == 4


# ------------------------------------------------------------------------------------------
# 6. Avisos

def _avisos_de(*configuraciones):
    """Resume cada configuración y devuelve los avisos de todas juntas."""
    resumenes = [resumir_configuracion(c) for c in configuraciones]
    return avisos(resumenes, list(configuraciones))


def caso_limpio():
    """Configuración sin nada sospechoso: PSO con éxito parcial y dentro del presupuesto."""
    return corridas_umbrales()


def test_caso_limpio_no_da_avisos():
    assert _avisos_de(caso_limpio()) == []


def test_sin_configuraciones_no_hay_avisos():
    assert avisos([], []) == []


def test_aviso_f_por_debajo_de_f_star():
    sospechosa = corridas_umbrales()
    sospechosa[4] = corrida(-1e-6, [(30, -1e-6)], seed=4)
    textos = _avisos_de(sospechosa)
    assert len(textos) == 1
    assert textos[0].startswith("rastrigin 2D pso: 1 corrida(s) con f_best < f*")
    assert textos[0].endswith("(semillas: 4)")     # semilla de la corrida sospechosa


def test_f_apenas_por_debajo_de_f_star_dentro_de_la_tolerancia_no_avisa():
    tolerada = corridas_umbrales()
    tolerada[4] = corrida(-1e-9, [(30, -1e-9)], seed=4)     # f* - 1e-9 exacto: no es menor
    assert not [t for t in _avisos_de(tolerada) if "f*" in t]


def test_aviso_exito_total_en_los_tres_umbrales():
    perfectas = [corrida(0.0, [(30, 0.0)], seed=s) for s in range(3)]
    textos = _avisos_de(perfectas)
    assert len(textos) == 1
    assert "100 %" in textos[0]
    assert "rastrigin" in textos[0] and "pso" in textos[0]


def test_exito_total_solo_en_el_umbral_principal_no_avisa():
    casi = [corrida(5e-5, [(30, 5e-5)], seed=s) for s in range(3)]     # falla 1e-6
    resumen = resumir_configuracion(casi)
    assert resumen["tasa_exito"] == {"1e-04": 1.0, "1e-02": 1.0, "1e-06": 0.0}
    assert avisos([resumen], [casi]) == []


@pytest.mark.parametrize("metodo", METODOS_SIN_GRADIENTE)
def test_aviso_n_grad_positivo_en_metodo_sin_gradiente(metodo):
    corridas = [corrida(2.0, method=metodo, seed=0),
                corrida(2.0, method=metodo, seed=1, n_grad=5, eval_equiv=120.0)]
    textos = _avisos_de(corridas)
    assert len(textos) == 1
    assert textos[0].startswith(f"rastrigin 2D {metodo}: 1 corrida(s) con n_grad > 0")
    assert textos[0].endswith("(semillas: 1)")


@pytest.mark.parametrize("metodo", ["gdfijo", "gdarmijo"])
def test_n_grad_positivo_en_gd_no_avisa(metodo):
    n_f = 0 if metodo == "gdfijo" else 3
    assert _avisos_de([corrida(2.0, method=metodo, n_f=n_f, n_grad=10)]) == []


def test_aviso_n_f_positivo_en_gd_de_paso_fijo():
    textos = _avisos_de([corrida(2.0, method="gdfijo", n_f=1, n_grad=10)])
    assert len(textos) == 1
    assert "n_f" in textos[0] and "gdfijo" in textos[0]


def test_aviso_eval_equiv_mayor_que_el_presupuesto():
    textos = _avisos_de([corrida(2.0, n_f=20001, budget=20000.0)])
    assert len(textos) == 1
    assert "presupuesto" in textos[0]


def test_eval_equiv_igual_al_presupuesto_no_avisa():
    assert _avisos_de([corrida(2.0, n_f=20000, budget=20000.0)]) == []


def test_avisos_de_varias_configuraciones_deterministas_y_en_orden_estable():
    bajo_f_star = [corrida(-1.0, [(30, -1.0)], func="rosenbrock", method="de", seed=0),
                   corrida(2.0, func="rosenbrock", method="de", seed=1)]
    perfecta = [corrida(0.0, [(30, 0.0)], method="ea", seed=s) for s in range(2)]
    con_f = [corrida(2.0, method="gdfijo", n_f=2, n_grad=10)]
    pasada = [corrida(2.0, dim=3, k=6.0, n_f=30001, budget=30000.0)]
    configuraciones = (bajo_f_star, caso_limpio(), perfecta, con_f, pasada)

    textos = _avisos_de(*configuraciones)
    assert len(textos) == 4
    assert all(isinstance(t, str) and t for t in textos)
    assert textos == _avisos_de(*configuraciones)       # misma entrada, misma salida
    # Orden: por tipo de aviso (a, b, c, d).
    assert textos[0].startswith("rosenbrock 2D de: 1 corrida(s) con f_best < f*")
    assert textos[1].startswith("rastrigin 2D ea: tasa de éxito del 100 %")
    assert textos[2].startswith("rastrigin 2D gdfijo: 1 corrida(s) con n_f > 0")
    assert textos[3].startswith("rastrigin 3D pso: 1 corrida(s) con eval_equiv mayor que el "
                                "presupuesto")


def test_varios_avisos_del_mismo_tipo_siguen_el_orden_de_las_configuraciones():
    primera = [corrida(2.0, func="rosenbrock", n_f=20001)]
    segunda = [corrida(2.0, func="rastrigin", n_f=20001)]
    textos = _avisos_de(primera, segunda)
    assert len(textos) == 2
    assert "rosenbrock" in textos[0] and "rastrigin" in textos[1]


def test_avisos_no_modifica_sus_entradas():
    corridas = [corrida(-1.0, [(30, -1.0)], n_f=20001)]
    resumenes = [resumir_configuracion(corridas)]
    copia_corridas = [corrida(-1.0, [(30, -1.0)], n_f=20001)]
    copia_resumenes = [resumir_configuracion(copia_corridas)]
    avisos(resumenes, [corridas])
    assert corridas == copia_corridas and resumenes == copia_resumenes


# ------------------------------------------------------------------------------------------
# 7. Sin NaN/inf, tipos nativos y guardable con save_json

CASOS_DE_SALIDA = {
    "estadisticas": corridas_estadisticas,
    "umbrales": corridas_umbrales,
    "una_corrida": lambda: [corrida(3.0)],
    "gd": lambda: [corrida_gd(k=4.0, eval_equiv=43.0)],
    "k_entero": lambda: [corrida(3.0, k=4, budget=20000)],
}


@pytest.mark.parametrize("caso", sorted(CASOS_DE_SALIDA))
def test_el_resumen_no_tiene_nan_ni_inf_y_usa_tipos_nativos(caso):
    resumen = resumir_configuracion(CASOS_DE_SALIDA[caso]())
    assert no_finitos(resumen) == []
    assert tipos_no_nativos(resumen) == []
    assert type(resumen["dim"]) is int and type(resumen["n_corridas"]) is int
    assert type(resumen["k"]) is float


def test_el_buscador_de_no_finitos_de_la_prueba_si_detecta():
    assert no_finitos({"a": [1.0, {"b": math.nan}], "c": (math.inf,)}) == ["$.a[1].b", "$.c[0]"]


@pytest.mark.parametrize("caso", sorted(CASOS_DE_SALIDA))
def test_las_filas_csv_no_tienen_nan_ni_inf(caso):
    filas = a_filas_csv([resumir_configuracion(CASOS_DE_SALIDA[caso]())])
    assert no_finitos(filas) == []
    assert tipos_no_nativos(filas) == []


def test_resumenes_y_avisos_se_guardan_con_save_json(tmp_path):
    configuraciones = [CASOS_DE_SALIDA[caso]() for caso in sorted(CASOS_DE_SALIDA)]
    configuraciones.append([corrida(-1.0, [(30, -1.0)], n_f=20001)])
    resumenes = [resumir_configuracion(c) for c in configuraciones]
    contenido = {"resumenes": resumenes, "avisos": avisos(resumenes, configuraciones),
                 "filas": a_filas_csv(resumenes)}
    ruta = save_json(tmp_path / "summary.json", contenido)
    assert load_json(ruta) == contenido


# ------------------------------------------------------------------------------------------
# 8. Formato: tabla de consola y filas planas

def _resumenes_de_formato():
    return [resumir_configuracion(corridas_estadisticas()),
            resumir_configuracion(corridas_umbrales()),
            resumir_configuracion([corrida(3.0, func="rosenbrock", dim=3, method="gdarmijo",
                                           k=6.0, n_f=3, n_grad=10)])]


def test_la_tabla_tiene_cabecera_y_una_linea_por_configuracion():
    resumenes = _resumenes_de_formato()
    tabla = formatear_tabla_consola(resumenes)
    assert isinstance(tabla, str)
    lineas = tabla.split("\n")
    assert len(lineas) == len(resumenes) + 1
    assert all(linea.strip() for linea in lineas)
    cabecera = lineas[0]
    for titulo in ("función", "dim", "método", "f_final", "mediana", "1e-04", "n_f", "n_grad"):
        assert titulo in cabecera


def test_la_tabla_contiene_los_valores():
    lineas = formatear_tabla_consola(_resumenes_de_formato()).split("\n")
    # 1.ª configuración: media 3, desv 2.1602..., mediana 2.5, éxito 0 %, n_f 250, n_grad 0.
    fila = lineas[1]
    for texto in ("rastrigin", "pso", "3.000e+00", "2.160e+00", "±", "2.500e+00", "0.0 %",
                  "250.0", "0.0"):
        assert texto in fila
    # 2.ª configuración: tasa de éxito del 60 % en el umbral principal.
    assert "60.0 %" in lineas[2]
    # 3.ª configuración: una corrida (desv indefinida), 3D, GD con Armijo.
    for texto in ("rosenbrock", "gdarmijo", "—", "3.0", "10.0"):
        assert texto in lineas[3]


def test_la_tabla_no_muestra_nan_ni_none():
    tabla = formatear_tabla_consola(_resumenes_de_formato())
    for prohibido in ("nan", "NaN", "inf", "None"):
        assert prohibido not in tabla


def test_la_raya_solo_aparece_donde_la_desviacion_es_indefinida():
    lineas = formatear_tabla_consola(_resumenes_de_formato()).split("\n")
    assert "—" not in lineas[1] and "—" not in lineas[2]
    assert lineas[3].count("—") == 1


def test_las_columnas_de_la_tabla_estan_alineadas():
    lineas = formatear_tabla_consola(_resumenes_de_formato()).split("\n")
    assert len({len(linea) for linea in lineas}) == 1
    # El separador de columnas cae en las mismas posiciones en todas las líneas.
    posiciones = [{i for i, c in enumerate(linea) if c == "|"} for linea in lineas]
    assert posiciones[0] and all(p == posiciones[0] for p in posiciones)


def test_la_tabla_sin_configuraciones_es_solo_la_cabecera():
    assert len(formatear_tabla_consola([]).split("\n")) == 1


def test_filas_csv_planas_con_las_mismas_claves():
    resumenes = _resumenes_de_formato()
    filas = a_filas_csv(resumenes)
    assert len(filas) == len(resumenes)
    claves = list(filas[0])
    for fila in filas:
        assert list(fila) == claves
        assert all(isinstance(c, str) for c in fila)
        assert not any(isinstance(v, (dict, list, tuple)) for v in fila.values())


def test_filas_csv_claves_exactas():
    fila = a_filas_csv(_resumenes_de_formato())[0]
    assert list(fila) == [
        "func", "dim", "method", "k", "n_corridas",
        "f_final_media", "f_final_desv", "f_final_mediana", "f_final_mejor", "f_final_peor",
        "n_f_medio", "n_grad_medio",
        "eval_equiv_medio", "eval_equiv_medio_k2n", "eval_equiv_medio_k1",
        "tasa_exito_1e-04", "tasa_exito_1e-02", "tasa_exito_1e-06",
        "evals_hasta_exito_medio_1e-04", "evals_hasta_exito_medio_1e-02",
        "evals_hasta_exito_medio_1e-06",
    ]


def test_filas_csv_conservan_los_valores_y_los_none():
    resumenes = _resumenes_de_formato()
    filas = a_filas_csv(resumenes)
    assert filas[0]["f_final_media"] == resumenes[0]["f_final"]["media"]
    assert filas[0]["evals_hasta_exito_medio_1e-04"] is None
    assert filas[1]["tasa_exito_1e-04"] == pytest.approx(0.6)
    assert filas[1]["evals_hasta_exito_medio_1e-06"] == pytest.approx(260.0)
    assert filas[2]["f_final_desv"] is None
    assert filas[2]["func"] == "rosenbrock" and filas[2]["dim"] == 3
    assert filas[2]["eval_equiv_medio_k2n"] == 63.0


def test_filas_csv_sin_configuraciones():
    assert a_filas_csv([]) == []


# ------------------------------------------------------------------------------------------
# 9. Higiene del archivo

def test_lineas_de_hasta_100_caracteres_y_fin_de_linea_lf():
    for ruta in (RUTA_METRICAS, Path(__file__)):
        crudo = ruta.read_bytes()
        assert b"\r" not in crudo
        largas = [n for n, linea in enumerate(crudo.decode("utf-8").splitlines(), start=1)
                  if len(linea) > LARGO_MAXIMO]
        assert largas == [], f"{ruta.name}: líneas de más de {LARGO_MAXIMO} caracteres"


def test_el_modulo_empieza_con_una_celda_markdown_y_tiene_celdas_de_codigo():
    texto = RUTA_METRICAS.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    assert "\n# %%\n" in texto


def test_el_modulo_no_lee_ni_escribe_archivos_ni_imprime():
    texto = RUTA_METRICAS.read_text(encoding="utf-8")
    for prohibido in ("print(", "open(", "save_json", "load_json", "import random",
                      "np.random"):
        assert prohibido not in texto
