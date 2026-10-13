"""Pruebas de `src/part1/hpo.py` (T1.10-A: piezas puras de la optimización de hiperparámetros).

Grupos:

    1. muestreo                  -> límites, tipos, escala log, reproducibilidad, ensayo 0
    2. combinaciones inválidas   -> se re-sortean; tope de intentos; defecto inválido
    3. aplicar_ensayo            -> copia profunda, sustitución de {func}
    4. unidades (R5)             -> las 6 unidades de la base, orden, celdas, mezcla de rutas
    5. semillas (R2)             -> ajuste y reporte disjuntas, bordes
    6. validar_hpo               -> una prueba por regla
    7. selección (R6)            -> rangos, recorte a 1e-6, desempates, errores
    8. config_afinada            -> solo lo que cambió, anidado, ida y vuelta por YAML
    9. higiene del módulo

La configuración parte de la real: `configs/part1/base.yaml`. Ninguna prueba corre un
optimizador: los registros de la selección se escriben a mano.
"""

from __future__ import annotations

import copy
import json
import math
import re
import shutil
import statistics
import warnings
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.common.config import apply_overrides, load_config
from src.common.seeds import make_rng
from src.part1 import hpo
from src.part1.de import ParametrosDE
from src.part1.ea import ParametrosEA
from src.part1.hpo import (
    Hiperparametro,
    Unidad,
    aplicar_ensayo,
    clave_celda,
    config_afinada,
    construir_unidades,
    elegir_ganador,
    puntuar_ensayos,
    sortear_ensayos,
    validar_hpo,
)
from src.part1.metricas import UMBRALES, clave_umbral
from src.part1.pso import ParametrosPSO

RAIZ = Path(__file__).resolve().parents[1]
RUTA_BASE = RAIZ / "configs" / "part1" / "base.yaml"
RUTA_DEMO = RAIZ / "configs" / "part1" / "demo.yaml"
RUTA_HPO = RAIZ / "src" / "part1" / "hpo.py"
RUTA_PRUEBAS = Path(__file__).resolve()
LARGO_MAXIMO = 100

SUFIJO = "1e-06"                         # clave_umbral(1e-6)
TASA = f"tasa_exito_{SUFIJO}"
EVALS = f"evals_hasta_exito_{SUFIJO}"

NOMBRES_UNIDADES = ["gdfijo_rosenbrock", "gdfijo_rastrigin", "gdarmijo", "ea", "pso", "de"]
CUATRO_CELDAS = (("rosenbrock", 2), ("rosenbrock", 3), ("rastrigin", 2), ("rastrigin", 3))


@pytest.fixture
def cfg():
    """Config real de la Parte 1 (nueva en cada prueba)."""
    return load_config(RUTA_BASE)


def _unidad(cfg, nombre):
    return next(u for u in construir_unidades(cfg) if u.nombre == nombre)


def _espacio(cfg, metodo):
    return cfg["hpo"]["espacios"][metodo]


def _sin_no_finitos(valor):
    """True si `valor` no contiene floats NaN/inf ni tipos de numpy, a cualquier profundidad."""
    if isinstance(valor, dict):
        return all(isinstance(k, str) and _sin_no_finitos(v) for k, v in valor.items())
    if isinstance(valor, (list, tuple)):
        return all(_sin_no_finitos(v) for v in valor)
    if isinstance(valor, (np.generic, np.ndarray)):
        return False
    if isinstance(valor, float):
        return math.isfinite(valor)
    return valor is None or isinstance(valor, (int, str, bool))


# ================================================================================================
# 1. Muestreo
# ================================================================================================

def test_cada_tipo_respeta_sus_limites_y_su_tipo_de_python(cfg):
    for unidad in construir_unidades(cfg):
        ensayos = sortear_ensayos(unidad, cfg, 60)
        assert len(ensayos) == 60
        for ensayo in ensayos[1:]:
            assert list(ensayo) == [p.ruta for p in unidad.parametros]
            for p in unidad.parametros:
                valor = ensayo[p.ruta]
                assert p.minimo <= valor <= p.maximo
                if p.tipo == "entero":
                    assert type(valor) is int
                else:
                    assert type(valor) is float


def test_entero_devuelve_int_y_alcanza_los_dos_extremos(cfg):
    _espacio(cfg, "pso")["N"].update(min=2, max=4)
    valores = [e["pso.N"] for e in sortear_ensayos(_unidad(cfg, "pso"), cfg, 200)[1:]]
    assert set(valores) == {2, 3, 4}
    assert all(type(v) is int for v in valores)


def test_log_no_es_uniforme_su_mediana_es_la_media_geometrica(cfg):
    # gdfijo: eta log en [1e-5, 1e-2]; media geométrica sqrt(1e-5 * 1e-2) ≈ 3.16e-4.
    # Uniforme en el mismo intervalo tendría mediana ≈ 5e-3.
    ensayos = sortear_ensayos(_unidad(cfg, "gdfijo_rosenbrock"), cfg, 2001)
    valores = [e["gd.eta.{func}"] for e in ensayos[1:]]
    mediana = statistics.median(valores)
    assert 2e-4 < mediana < 5e-4
    assert abs(mediana - 5e-3) > 4e-3
    assert min(valores) >= 1e-5 and max(valores) <= 1e-2


def test_uniforme_tiene_media_cerca_del_centro(cfg):
    # pso.w uniforme en [0.3, 0.95]: centro 0.625.
    valores = [e["pso.w"] for e in sortear_ensayos(_unidad(cfg, "pso"), cfg, 1001)[1:]]
    assert abs(statistics.mean(valores) - 0.625) < 0.03


def test_mismo_generador_mismos_ensayos_y_otra_semilla_otros(cfg):
    unidad = _unidad(cfg, "de")
    a = sortear_ensayos(unidad, cfg, 10)
    b = sortear_ensayos(unidad, copy.deepcopy(cfg), 10)
    assert a == b
    otra = apply_overrides(cfg, ["hpo.semilla_busqueda=7"])
    c = sortear_ensayos(_unidad(otra, "de"), otra, 10)
    assert c[0] == a[0]                  # el ensayo 0 es el defecto en los dos casos
    assert c[1:] != a[1:]


def test_el_generador_es_make_rng_de_semilla_busqueda_e_indice(cfg):
    # Reimplementación de R4 para gdfijo_rastrigin (índice 1): un solo parámetro log.
    unidad = _unidad(cfg, "gdfijo_rastrigin")
    assert unidad.indice == 1
    rng = make_rng(cfg["hpo"]["semilla_busqueda"], unidad.indice)
    esperados = [min(max(float(math.exp(rng.uniform(math.log(1e-5), math.log(1e-2)))), 1e-5),
                     1e-2) for _ in range(5)]
    obtenidos = [e["gd.eta.{func}"] for e in sortear_ensayos(unidad, cfg, 6)[1:]]
    assert obtenidos == esperados


def test_el_ensayo_0_es_exactamente_el_defecto_en_las_6_unidades(cfg):
    esperado = {
        "gdfijo_rosenbrock": {"gd.eta.{func}": 1e-3},
        "gdfijo_rastrigin": {"gd.eta.{func}": 2e-3},
        "gdarmijo": {"gd.armijo.eta0": 1.0, "gd.armijo.beta": 0.5, "gd.armijo.c": 1e-4},
        "ea": {"ea.N": 50, "ea.frac_e": 0.15, "ea.frac_m": 0.10, "ea.frac_c": 0.75},
        "pso": {"pso.N": 30, "pso.w": 0.7298, "pso.c1": 1.49618, "pso.c2": 1.49618,
                "pso.vmax_frac": 0.2},
        "de": {"de.NP": 30, "de.F": 0.7, "de.CR": 0.9},
    }
    for unidad in construir_unidades(cfg):
        cero = sortear_ensayos(unidad, cfg, 3)[0]
        assert cero == esperado[unidad.nombre]
        assert list(cero) == list(esperado[unidad.nombre])
        for clave, valor in cero.items():
            assert type(valor) is type(esperado[unidad.nombre][clave])


def test_el_ensayo_0_se_lee_de_la_config_recibida(cfg):
    otra = apply_overrides(cfg, ["pso.w=0.6", "gd.eta.rastrigin=0.0025"])
    assert sortear_ensayos(_unidad(otra, "pso"), otra, 1)[0]["pso.w"] == 0.6
    assert sortear_ensayos(_unidad(otra, "gdfijo_rastrigin"), otra, 1)[0] == {
        "gd.eta.{func}": 0.0025}


def test_n_ensayos_debe_ser_entero_positivo(cfg):
    unidad = _unidad(cfg, "de")
    with pytest.raises(ValueError):
        sortear_ensayos(unidad, cfg, 0)
    with pytest.raises(TypeError):
        sortear_ensayos(unidad, cfg, True)


# ================================================================================================
# 2. Combinaciones inválidas
# ================================================================================================

def _espacio_ea_con_invalidos(cfg):
    _espacio(cfg, "ea").update({
        "N": {"ruta": "ea.N", "tipo": "entero", "min": 2, "max": 10},
        "frac_e": {"ruta": "ea.frac_e", "tipo": "uniforme", "min": 0.3, "max": 0.8},
        "frac_m": {"ruta": "ea.frac_m", "tipo": "uniforme", "min": 0.3, "max": 0.8},
        "frac_c": {"ruta": "ea.frac_c", "tipo": "uniforme", "min": 0.4, "max": 0.9},
    })


def _ea_valido(cfg, ensayo):
    copia = aplicar_ensayo(cfg, ensayo, None)
    try:
        ParametrosEA.desde_config(copia["ea"])
    except (TypeError, ValueError):
        return False
    return True


def _sortear_ea_a_mano(rng):
    return {"ea.N": int(rng.integers(2, 10, endpoint=True)),
            "ea.frac_e": float(rng.uniform(0.3, 0.8)),
            "ea.frac_m": float(rng.uniform(0.3, 0.8)),
            "ea.frac_c": float(rng.uniform(0.4, 0.9))}


def test_los_ensayos_invalidos_del_ea_se_resortean_y_no_se_devuelven(cfg):
    _espacio_ea_con_invalidos(cfg)
    # El espacio sí tiene combinaciones inválidas (con un generador ajeno a la prueba).
    rng_prueba = np.random.default_rng(123)
    invalidos = sum(not _ea_valido(cfg, _sortear_ea_a_mano(rng_prueba)) for _ in range(300))
    assert invalidos > 100
    ensayos = sortear_ensayos(_unidad(cfg, "ea"), cfg, 40)
    assert len(ensayos) == 40
    assert all(_ea_valido(cfg, e) for e in ensayos)


def test_el_resorteo_consume_el_mismo_generador(cfg):
    # Reimplementación de R4: se sortea en el orden del espacio hasta la primera válida.
    _espacio_ea_con_invalidos(cfg)
    unidad = _unidad(cfg, "ea")
    rng = make_rng(cfg["hpo"]["semilla_busqueda"], unidad.indice)
    esperados = []
    while len(esperados) < 5:
        candidato = _sortear_ea_a_mano(rng)
        if _ea_valido(cfg, candidato):
            esperados.append(candidato)
    assert sortear_ensayos(unidad, cfg, 6)[1:] == esperados


def test_un_espacio_sin_combinaciones_validas_falla_tras_el_tope(cfg):
    # N ∈ {2, 3} con frac_e, frac_m ≥ 0.9: n_elite + n_mutantes > N siempre.
    _espacio(cfg, "ea").update({
        "N": {"ruta": "ea.N", "tipo": "entero", "min": 2, "max": 3},
        "frac_e": {"ruta": "ea.frac_e", "tipo": "uniforme", "min": 0.9, "max": 0.95},
        "frac_m": {"ruta": "ea.frac_m", "tipo": "uniforme", "min": 0.9, "max": 0.95},
    })
    assert hpo.INTENTOS_MAXIMOS == 200
    with pytest.raises(ValueError, match=r"ea.*200|200.*ea"):
        sortear_ensayos(_unidad(cfg, "ea"), cfg, 2)


def test_valores_por_defecto_invalidos_dan_error_sin_resortear(cfg):
    otra = apply_overrides(cfg, ["ea.frac_e=0.95"])      # n_elite 48 + n_mutantes 5 > 50
    with pytest.raises(ValueError, match="ea"):
        sortear_ensayos(_unidad(otra, "ea"), otra, 3)


def test_reglas_de_armijo_se_aplican_al_sortear(cfg):
    _espacio(cfg, "gdarmijo")["beta"].update(min=0.5, max=1.5)
    _espacio(cfg, "gdarmijo")["c"].update(tipo="uniforme", min=0.5, max=2.0)
    ensayos = sortear_ensayos(_unidad(cfg, "gdarmijo"), cfg, 30)
    assert all(0 < e["gd.armijo.beta"] < 1 and 0 < e["gd.armijo.c"] < 1 for e in ensayos)


def test_reglas_de_pso_y_de_se_aplican_al_sortear(cfg):
    _espacio(cfg, "pso")["N"].update(min=1, max=3)       # N = 1 es inválido
    _espacio(cfg, "de")["NP"].update(min=2, max=5)       # NP < 4 es inválido
    for nombre, clase in (("pso", ParametrosPSO), ("de", ParametrosDE)):
        for ensayo in sortear_ensayos(_unidad(cfg, nombre), cfg, 20):
            clase.desde_config(aplicar_ensayo(cfg, ensayo, None)[nombre])
    assert {e["pso.N"] for e in sortear_ensayos(_unidad(cfg, "pso"), cfg, 40)[1:]} == {2, 3}


def test_sortear_no_emite_el_aviso_de_inercia(cfg):
    _espacio(cfg, "pso")["w"].update(min=1.0, max=1.5)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sortear_ensayos(_unidad(cfg, "pso"), cfg, 5)


# ================================================================================================
# 3. aplicar_ensayo
# ================================================================================================

def test_aplicar_ensayo_no_modifica_el_cfg_y_sustituye_func(cfg):
    antes = copy.deepcopy(cfg)
    copia = aplicar_ensayo(cfg, {"gd.eta.{func}": 0.004, "pso.w": 0.5}, "rastrigin")
    assert cfg == antes
    assert copia["gd"]["eta"] == {"rosenbrock": 1e-3, "rastrigin": 0.004}
    assert copia["pso"]["w"] == 0.5
    copia["ea"]["N"] = 999
    assert cfg["ea"]["N"] == 50                           # copia profunda


def test_aplicar_ensayo_con_func_none_y_marcador_falla(cfg):
    with pytest.raises(ValueError, match="func"):
        aplicar_ensayo(cfg, {"gd.eta.{func}": 0.004}, None)


def test_aplicar_ensayo_con_ruta_inexistente_falla(cfg):
    with pytest.raises(ValueError, match="pso.inercia"):
        aplicar_ensayo(cfg, {"pso.inercia": 0.5}, None)


# ================================================================================================
# 4. Unidades (R5)
# ================================================================================================

def test_la_config_por_defecto_forma_las_6_unidades_en_orden(cfg):
    unidades = construir_unidades(cfg)
    assert [u.nombre for u in unidades] == NOMBRES_UNIDADES
    assert [u.indice for u in unidades] == list(range(6))
    assert [u.metodo for u in unidades] == ["gdfijo", "gdfijo", "gdarmijo", "ea", "pso", "de"]
    assert [u.func for u in unidades] == ["rosenbrock", "rastrigin", None, None, None, None]
    assert unidades[0].celdas == (("rosenbrock", 2), ("rosenbrock", 3))
    assert unidades[1].celdas == (("rastrigin", 2), ("rastrigin", 3))
    for unidad in unidades[2:]:
        assert unidad.celdas == CUATRO_CELDAS
    assert [p.nombre for p in unidades[3].parametros] == ["N", "frac_e", "frac_m", "frac_c"]
    assert unidades[4].parametros[1] == Hiperparametro("w", "pso.w", "uniforme", 0.3, 0.95)
    assert unidades[0].parametros == (
        Hiperparametro("eta", "gd.eta.{func}", "log", 1e-5, 1e-2),)
    assert isinstance(unidades[0], Unidad)
    with pytest.raises(AttributeError):
        unidades[0].nombre = "otro"                       # dataclass congelada


def test_los_espacios_por_defecto_son_los_del_protocolo(cfg):
    esperado = {
        "gdfijo": [("eta", "gd.eta.{func}", "log", 1e-5, 1e-2)],
        "gdarmijo": [("eta0", "gd.armijo.eta0", "log", 0.1, 10.0),
                     ("beta", "gd.armijo.beta", "uniforme", 0.1, 0.9),
                     ("c", "gd.armijo.c", "log", 1e-5, 1e-1)],
        "ea": [("N", "ea.N", "entero", 20, 200), ("frac_e", "ea.frac_e", "uniforme", 0.05, 0.30),
               ("frac_m", "ea.frac_m", "uniforme", 0.05, 0.40),
               ("frac_c", "ea.frac_c", "uniforme", 0.40, 0.90)],
        "pso": [("N", "pso.N", "entero", 10, 100), ("w", "pso.w", "uniforme", 0.3, 0.95),
                ("c1", "pso.c1", "uniforme", 0.5, 2.5), ("c2", "pso.c2", "uniforme", 0.5, 2.5),
                ("vmax_frac", "pso.vmax_frac", "uniforme", 0.05, 0.5)],
        "de": [("NP", "de.NP", "entero", 10, 100), ("F", "de.F", "uniforme", 0.3, 1.2),
               ("CR", "de.CR", "uniforme", 0.1, 1.0)],
    }
    espacios = cfg["hpo"]["espacios"]
    assert list(espacios) == list(esperado)
    for metodo, filas in esperado.items():
        obtenidas = [(n, d["ruta"], d["tipo"], d["min"], d["max"])
                     for n, d in espacios[metodo].items()]
        assert obtenidas == filas
        for n, d in espacios[metodo].items():
            tipo_esperado = int if d["tipo"] == "entero" else float
            assert type(d["min"]) is tipo_esperado and type(d["max"]) is tipo_esperado


def test_el_bloque_hpo_por_defecto(cfg):
    h = cfg["hpo"]
    assert (h["ensayos"], h["semillas"], h["base_seed"], h["semilla_busqueda"]) == (30, 5, 1000, 1)
    assert h["reanudar"] is False
    assert h["salida"] == "results/data/part1_hpo"
    assert h["salida_afinada"] == "results/data/part1_tuned"
    assert h["tablas_afinada"] == "results/tables/part1_tuned"
    assert h["config_salida"] == "configs/part1/tuned.yaml"


def test_set_sobre_un_extremo_del_espacio_funciona(cfg):
    otra = apply_overrides(cfg, ["hpo.espacios.pso.w.max=0.9"])
    assert otra["hpo"]["espacios"]["pso"]["w"]["max"] == 0.9
    assert _unidad(otra, "pso").parametros[1].maximo == 0.9


def test_mezclar_rutas_con_y_sin_func_en_un_metodo_falla(cfg):
    _espacio(cfg, "gdfijo")["eta_r"] = {"ruta": "gd.eta.rosenbrock", "tipo": "log",
                                        "min": 1e-5, "max": 1e-2}
    with pytest.raises(ValueError, match="gdfijo"):
        construir_unidades(cfg)


def test_un_metodo_con_func_en_todas_sus_rutas_y_una_sola_funcion(cfg):
    otra = apply_overrides(cfg, ["func=[rastrigin]", "dim=[2]", "methods=[gdfijo, de]"])
    unidades = construir_unidades(otra)
    assert [u.nombre for u in unidades] == ["gdfijo_rastrigin", "de"]
    assert [u.indice for u in unidades] == [0, 1]
    assert unidades[1].celdas == (("rastrigin", 2),)


def test_el_espacio_de_un_metodo_fuera_de_methods_no_forma_unidad(cfg):
    otra = apply_overrides(cfg, ["methods=[pso]"])
    assert [u.nombre for u in construir_unidades(otra)] == ["pso"]


def test_el_espacio_de_un_metodo_fuera_de_methods_se_valida(cfg):
    otra = apply_overrides(cfg, ["methods=[pso]", "hpo.espacios.ea.N.tipo=normal"])
    with pytest.raises(ValueError, match="hpo.espacios.ea.N.tipo"):
        validar_hpo(otra)


def test_la_config_del_demo_es_valida():
    demo = load_config(RUTA_DEMO)
    validar_hpo(demo)
    assert [u.nombre for u in construir_unidades(demo)] == ["pso", "gdfijo_rastrigin"]


# ================================================================================================
# 5. Semillas (R2)
# ================================================================================================

@pytest.mark.parametrize("base_seed_hpo", [25, 29, 26, 0])
def test_semillas_de_ajuste_que_tocan_las_de_reporte_fallan(cfg, base_seed_hpo):
    # Reporte: 0..29. Ajuste con 5 semillas: 25..29, 29..33, 26..30 y 0..4 tocan 0..29.
    otra = apply_overrides(cfg, [f"hpo.base_seed={base_seed_hpo}"])
    with pytest.raises(ValueError, match="semillas"):
        validar_hpo(otra)


def test_semillas_disjuntas_en_el_borde_pasan(cfg):
    validar_hpo(apply_overrides(cfg, ["hpo.base_seed=30"]))     # 30..34 vs 0..29
    validar_hpo(cfg)                                              # 1000..1004 vs 0..29


def test_semillas_de_reporte_por_encima_de_las_de_ajuste(cfg):
    # Ajuste 1000..1004; reporte 995..1024 se solapa; reporte 1005.. no.
    with pytest.raises(ValueError, match="semillas"):
        validar_hpo(apply_overrides(cfg, ["base_seed=995"]))
    validar_hpo(apply_overrides(cfg, ["base_seed=1005"]))


@pytest.mark.parametrize("clave", ["base_seed", "runs"])
def test_sin_base_seed_o_runs_falla(cfg, clave):
    del cfg[clave]
    with pytest.raises(ValueError, match=clave):
        validar_hpo(cfg)


# ================================================================================================
# 6. validar_hpo
# ================================================================================================

def test_la_config_por_defecto_pasa_y_no_se_modifica(cfg):
    antes = copy.deepcopy(cfg)
    assert validar_hpo(cfg) is None
    assert cfg == antes


def _poner(*ruta_y_valor):
    *ruta, valor = ruta_y_valor

    def mutar(c):
        nodo = c
        for clave in ruta[:-1]:
            nodo = nodo[clave]
        nodo[ruta[-1]] = valor
    return mutar


def _quitar(*ruta):
    def mutar(c):
        nodo = c
        for clave in ruta[:-1]:
            nodo = nodo[clave]
        del nodo[ruta[-1]]
    return mutar


def _hiper(metodo, nombre, ruta, tipo="uniforme", minimo=0.1, maximo=0.5):
    return _poner("hpo", "espacios", metodo, nombre,
                  {"ruta": ruta, "tipo": tipo, "min": minimo, "max": maximo})


CASOS_INVALIDOS = [
    # (id, mutación, excepción, fragmento del mensaje)
    ("falta-ensayos", _quitar("hpo", "ensayos"), ValueError, "ensayos"),
    ("clave-de-mas", _poner("hpo", "extra", 1), ValueError, "extra"),
    ("ensayos-bool", _poner("hpo", "ensayos", True), TypeError, "hpo.ensayos"),
    ("ensayos-0", _poner("hpo", "ensayos", 0), ValueError, "hpo.ensayos"),
    ("semillas-float", _poner("hpo", "semillas", 1.5), TypeError, "hpo.semillas"),
    ("semillas-0", _poner("hpo", "semillas", 0), ValueError, "hpo.semillas"),
    ("base-seed-negativa", _poner("hpo", "base_seed", -1), ValueError, "hpo.base_seed"),
    ("busqueda-bool", _poner("hpo", "semilla_busqueda", True), TypeError,
     "hpo.semilla_busqueda"),
    ("reanudar-texto", _poner("hpo", "reanudar", "no"), TypeError, "hpo.reanudar"),
    ("salida-vacia", _poner("hpo", "salida", "  "), ValueError, "hpo.salida"),
    ("salida-numero", _poner("hpo", "salida", 3), TypeError, "hpo.salida"),
    ("config-salida-vacia", _poner("hpo", "config_salida", ""), ValueError,
     "hpo.config_salida"),
    ("espacios-lista", _poner("hpo", "espacios", []), TypeError, "hpo.espacios"),
    ("metodo-desconocido", _poner("hpo", "espacios", "sa", {}), ValueError, "sa"),
    ("metodo-sin-espacio", _quitar("hpo", "espacios", "de"), ValueError, "de"),
    ("metodo-espacio-vacio", _poner("hpo", "espacios", "de", {}), ValueError, "de"),
    ("espacio-no-mapeo", _poner("hpo", "espacios", "de", [1]), TypeError, "hpo.espacios.de"),
    ("nombre-con-punto", _hiper("pso", "w.x", "pso.w"), ValueError, "w.x"),
    ("hiper-no-mapeo", _poner("hpo", "espacios", "pso", "w", 0.5), TypeError,
     "hpo.espacios.pso.w"),
    ("hiper-falta-clave", _quitar("hpo", "espacios", "pso", "w", "max"), ValueError, "max"),
    ("hiper-clave-de-mas", _poner("hpo", "espacios", "pso", "w", "paso", 1), ValueError,
     "paso"),
    ("tipo-desconocido", _poner("hpo", "espacios", "pso", "w", "tipo", "normal"), ValueError,
     "hpo.espacios.pso.w.tipo"),
    ("min-igual-max", _poner("hpo", "espacios", "pso", "w", "min", 0.95), ValueError,
     "hpo.espacios.pso.w"),
    ("min-mayor-max", _poner("hpo", "espacios", "pso", "w", "min", 2.0), ValueError,
     "hpo.espacios.pso.w"),
    ("min-bool", _poner("hpo", "espacios", "pso", "w", "min", False), TypeError,
     "hpo.espacios.pso.w.min"),
    ("max-texto", _poner("hpo", "espacios", "pso", "w", "max", "1"), TypeError,
     "hpo.espacios.pso.w.max"),
    ("min-nan", _poner("hpo", "espacios", "pso", "w", "min", float("nan")), ValueError,
     "hpo.espacios.pso.w.min"),
    ("max-inf", _poner("hpo", "espacios", "pso", "w", "max", float("inf")), ValueError,
     "hpo.espacios.pso.w.max"),
    ("log-min-0", _hiper("de", "F", "de.F", "log", 0.0, 1.0), ValueError, "hpo.espacios.de.F"),
    ("log-min-negativo", _hiper("de", "F", "de.F", "log", -1.0, 1.0), ValueError,
     "hpo.espacios.de.F"),
    ("entero-min-float", _poner("hpo", "espacios", "pso", "N", "min", 20.0), TypeError,
     "hpo.espacios.pso.N.min"),
    ("entero-max-bool", _poner("hpo", "espacios", "pso", "N", "max", True), TypeError,
     "hpo.espacios.pso.N.max"),
    ("ruta-no-texto", _poner("hpo", "espacios", "pso", "w", "ruta", 3), TypeError,
     "hpo.espacios.pso.w.ruta"),
    ("ruta-vacia", _poner("hpo", "espacios", "pso", "w", "ruta", ""), ValueError,
     "hpo.espacios.pso.w.ruta"),
    ("ruta-segmento-vacio", _poner("hpo", "espacios", "pso", "w", "ruta", "pso..w"), ValueError,
     "pso..w"),
    ("ruta-inexistente", _poner("hpo", "espacios", "pso", "w", "ruta", "pso.inercia"),
     ValueError, "pso.inercia"),
    ("ruta-fuera-del-bloque", _poner("hpo", "espacios", "pso", "w", "ruta", "de.F"), ValueError,
     "de.F"),
    ("ruta-gd-fuera-de-gd", _poner("hpo", "espacios", "gdarmijo", "beta", "ruta", "ea.frac_e"),
     ValueError, "ea.frac_e"),
    ("ruta-a-un-mapeo", _hiper("gdarmijo", "armijo", "gd.armijo"), ValueError, "gd.armijo"),
    ("marcador-parcial", _poner("hpo", "espacios", "gdfijo", "eta", "ruta", "gd.eta.x{func}"),
     ValueError, "{func}"),
    ("prohibida-iteraciones", _hiper("pso", "T", "pso.iteraciones", "entero", 1, 5), ValueError,
     "iteraciones"),
    ("prohibida-generaciones", _hiper("ea", "G", "ea.generaciones", "entero", 1, 5), ValueError,
     "generaciones"),
    ("prohibida-tol-grad", _hiper("gdarmijo", "tol", "gd.tol_grad", "log", 1e-9, 1e-6),
     ValueError, "tol_grad"),
    ("ruta-repetida", _hiper("de", "F2", "de.F"), ValueError, "de.F"),
    # gd.eta.rosenbrock coincide con gd.eta.{func} de gdfijo tras sustituir el marcador.
    ("ruta-repetida-entre-metodos", _hiper("gdarmijo", "eta_r", "gd.eta.rosenbrock", "log",
                                           1e-5, 1e-2), ValueError, "gd.eta.rosenbrock"),
    ("salida-afinada-igual-a-salida", _poner("hpo", "salida_afinada", "results/data/part1"),
     ValueError, "salida_afinada"),
    ("salida-afinada-igual-a-hpo-salida", _poner("hpo", "salida_afinada",
                                                 "results/data/part1_hpo/"),
     ValueError, "salida_afinada"),
    ("tablas-afinada-igual-a-tablas", _poner("hpo", "tablas_afinada", "./results/tables/part1"),
     ValueError, "tablas_afinada"),
    ("hpo-salida-igual-a-salida", _poner("hpo", "salida", "results/data/../data/part1"),
     ValueError, "hpo.salida"),
    # R8: carpetas una dentro de otra.
    ("salida-afinada-dentro-de-salida", _poner("hpo", "salida_afinada",
                                               "results/data/part1/afinado"),
     ValueError, "hpo.salida_afinada"),
    ("salida-dentro-de-salida-afinada", _poner("hpo", "salida_afinada", "results/data"),
     ValueError, "salida"),
    ("hpo-salida-dentro-de-salida", _poner("hpo", "salida", "./results/data/part1/hpo"),
     ValueError, "hpo.salida"),
]


def test_salida_dentro_de_hpo_salida_y_tablas_afinada_dentro_de_tablas_se_admiten(cfg):
    """Es la forma del demo: salida y tablas_afinada dentro de otras carpetas de la HPO."""
    cfg["salida"] = "results/data/part1_hpo/experimento"
    cfg["hpo"]["tablas_afinada"] = "results/tables/part1/afinado"
    validar_hpo(cfg)


def test_carpetas_hermanas_con_prefijo_comun_se_admiten(cfg):
    """`part1_tuned` no está dentro de `part1` aunque su texto empiece igual."""
    assert cfg["hpo"]["salida_afinada"] == "results/data/part1_tuned"
    validar_hpo(cfg)


@pytest.mark.parametrize("mutar, error, fragmento", [c[1:] for c in CASOS_INVALIDOS],
                         ids=[c[0] for c in CASOS_INVALIDOS])
def test_validar_hpo_rechaza(cfg, mutar, error, fragmento):
    mutar(cfg)
    with pytest.raises(error, match=re.escape(fragmento)):
        validar_hpo(cfg)


def test_sin_bloque_hpo_falla(cfg):
    del cfg["hpo"]
    with pytest.raises(ValueError, match="hpo"):
        validar_hpo(cfg)


def test_hpo_no_mapeo_falla(cfg):
    cfg["hpo"] = [1]
    with pytest.raises(TypeError, match="hpo"):
        validar_hpo(cfg)


def test_un_real_no_finito_en_el_bloque_falla_con_su_ruta(cfg):
    cfg["hpo"]["espacios"]["de"]["CR"]["max"] = float("-inf")
    with pytest.raises(ValueError, match=re.escape("hpo.espacios.de.CR.max")):
        validar_hpo(cfg)


def test_construir_unidades_valida(cfg):
    cfg["hpo"]["ensayos"] = 0
    with pytest.raises(ValueError, match="hpo.ensayos"):
        construir_unidades(cfg)


# ================================================================================================
# 7. Selección (R6)
# ================================================================================================

def _reg(f_best, evals=None):
    """Registro compacto de una celda; `evals` por defecto: 100.0 si f_best <= 1e-6, si no None."""
    n = len(f_best)
    if evals is None:
        evals = [100.0 if f <= 1e-6 else None for f in f_best]
    return {"f_best": list(f_best), "n_f": [10] * n, "n_grad": [0] * n,
            "eval_equiv": [10.0] * n, EVALS: list(evals)}


F_STAR_CERO = {"rosenbrock_2d": 0.0, "rastrigin_2d": 0.0}


def test_clave_celda():
    assert clave_celda("rastrigin", 2) == "rastrigin_2d"
    assert clave_celda("rosenbrock", 3) == "rosenbrock_3d"


def test_el_umbral_es_el_mas_estricto_de_metricas():
    assert hpo.UMBRAL_HPO == min(UMBRALES) == 1e-6
    assert clave_umbral(hpo.UMBRAL_HPO) == SUFIJO


def test_a_gana_el_menor_rango_medio_aunque_otro_tenga_la_mejor_celda_absoluta():
    # m (una semilla):   rosenbrock_2d   rastrigin_2d   suma absoluta
    #   ensayo 0           1e-1            1.0            1.1      <- ganaría por suma
    #   ensayo 1           1e-5            1.1            1.10001
    #   ensayo 2           1e-3            1.2            1.201
    # rangos rosenbrock: e1=1, e2=2, e0=3; rastrigin: e0=1, e1=2, e2=3
    # rango medio: e0 = 2.0, e1 = 1.5, e2 = 2.5 -> gana el ensayo 1.
    registros = [
        {"rosenbrock_2d": _reg([1e-1]), "rastrigin_2d": _reg([1.0])},
        {"rosenbrock_2d": _reg([1e-5]), "rastrigin_2d": _reg([1.1])},
        {"rosenbrock_2d": _reg([1e-3]), "rastrigin_2d": _reg([1.2])},
    ]
    puntajes = puntuar_ensayos(registros, F_STAR_CERO)
    assert [p["rango_medio"] for p in puntajes] == [2.0, 1.5, 2.5]
    assert puntajes[1]["rango"] == {"rosenbrock_2d": 1.0, "rastrigin_2d": 2.0}
    assert elegir_ganador(puntajes) == 1


F_DEFECTO_PEOR = 10.0          # m = 10 en toda celda: peor que cualquier retador de abajo


def _con_defecto_peor(retadores):
    """Antepone un ensayo 0 con m = F_DEFECTO_PEOR en cada celda (rango estrictamente peor).

    Así los desempates se prueban entre retadores: con la regla R6, un empate en el puntaje
    principal con el ensayo 0 lo gana siempre el 0.
    """
    defecto = {celda: _reg([F_DEFECTO_PEOR] * len(registro["f_best"]))
               for celda, registro in retadores[0].items()}
    return [defecto, *retadores]


def test_b_empate_por_recorte_se_decide_por_la_tasa_de_exito():
    # Ensayo 1: f = [1e-9, 1e-9, 1e-3] -> recortes [1e-6, 1e-6, 1e-3], m = 1e-6, tasa 2/3.
    # Ensayo 2: f = [1e-8, 1e-8, 1e-8] -> m = 1e-6, tasa 1.  Rangos 3, 1.5 y 1.5 -> gana 2.
    registros = _con_defecto_peor([{"rastrigin_2d": _reg([1e-9, 1e-9, 1e-3])},
                                   {"rastrigin_2d": _reg([1e-8, 1e-8, 1e-8])}])
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p["mediana_recortada"]["rastrigin_2d"] for p in puntajes] == [10.0, 1e-6, 1e-6]
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert puntajes[1][TASA] == pytest.approx(2 / 3)
    assert puntajes[2][TASA] == 1.0
    assert elegir_ganador(puntajes) == 2


def test_b_empate_tambien_en_tasa_se_decide_por_las_evaluaciones():
    # Retadores: m = 1e-6, tasa 1. Evaluaciones medias: ensayo 1 = 300, ensayo 2 = 200 -> 2.
    registros = _con_defecto_peor([{"rastrigin_2d": _reg([1e-9] * 3, [300.0, 300.0, 300.0])},
                                   {"rastrigin_2d": _reg([1e-9] * 3, [100.0, 200.0, 300.0])}])
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p[EVALS] for p in puntajes] == [None, 300.0, 200.0]
    assert elegir_ganador(puntajes) == 2


def test_b_evaluaciones_infinitas_pierden_ante_finitas():
    # Celda A: e1 [1e-9, 1e-9] -> m 1e-6, tasa 1; e2 [1e-9, 1] -> m (1e-6 + 1)/2, tasa 1/2.
    # Celda B: e1 [1, 1] -> m 1, tasa 0;          e2 [1e-9, 1] -> m (1e-6 + 1)/2, tasa 1/2.
    # Rangos (e0 = 3 en las dos): e1 = (1 + 2)/2 = 1.5; e2 = (2 + 1)/2 = 1.5. Tasas: 0.5 y 0.5.
    # Evaluaciones: e1 tiene la celda B sin éxitos (+inf -> None); e2 = 100 -> gana 2.
    registros = _con_defecto_peor(
        [{"rosenbrock_2d": _reg([1e-9, 1e-9]), "rastrigin_2d": _reg([1.0, 1.0])},
         {"rosenbrock_2d": _reg([1e-9, 1.0]), "rastrigin_2d": _reg([1e-9, 1.0])}])
    puntajes = puntuar_ensayos(registros, F_STAR_CERO)
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert [p[TASA] for p in puntajes[1:]] == [0.5, 0.5]
    assert puntajes[1][EVALS] is None and puntajes[2][EVALS] == 100.0
    assert elegir_ganador(puntajes) == 2


def _celda_con_exitos(exitos, evals=100.0, semillas=5):
    """Celda de `semillas` semillas: las `exitos` primeras en f* (con `evals`), el resto en 1."""
    return _reg([0.0] * exitos + [1.0] * (semillas - exitos),
                [evals] * exitos + [None] * (semillas - exitos))


def test_b1_a_empate_exacto_de_tasa_entre_retadores_lo_gana_el_menor_indice():
    # 5 semillas, 2 celdas; el ensayo 0 es peor en las dos (rango 3). Medianas recortadas de
    # los retadores iguales (1e-6 en las dos celdas) -> rangos 1.5 y 1.5.
    # Tasas: e1 = (3/5 + 5/5)/2 = 4/5; e2 = (4/5 + 4/5)/2 = 4/5 -> empate exacto.
    # Evaluaciones: 100 en todas -> empate; gana el menor índice, el 1.
    # Con Fraction(float): 0.6 + 1.0 < 0.8 + 0.8 en binario, y ganaría el 2 (error B1).
    registros = _con_defecto_peor(
        [{"rosenbrock_2d": _celda_con_exitos(3), "rastrigin_2d": _celda_con_exitos(5)},
         {"rosenbrock_2d": _celda_con_exitos(4), "rastrigin_2d": _celda_con_exitos(4)}])
    puntajes = puntuar_ensayos(registros, F_STAR_CERO)
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert puntajes[1][TASA] == puntajes[2][TASA] == 0.8
    assert elegir_ganador(puntajes) == 1
    assert elegir_ganador(json.loads(json.dumps(puntajes))) == 1


def test_b1_b_empate_exacto_de_tasa_entre_retadores_se_decide_por_las_evaluaciones():
    # Celda 1: e1 1 éxito, e2 2 -> m = 1 en los dos; celda 2: e1 4 éxitos, e2 3 -> m = 1e-6.
    # El ensayo 0 (m = 10) es peor en las dos: rangos 3, 1.5 y 1.5.
    # Tasas: e1 = (1/5 + 4/5)/2 = 1/2; e2 = (2/5 + 3/5)/2 = 1/2 -> empate exacto.
    # Evaluaciones: e1 = 900, e2 = 100 -> gana el 2. (0.2 + 0.8 > 0.4 + 0.6 en binario.)
    registros = _con_defecto_peor([{"rosenbrock_2d": _celda_con_exitos(1, 900.0),
                                    "rastrigin_2d": _celda_con_exitos(4, 900.0)},
                                   {"rosenbrock_2d": _celda_con_exitos(2, 100.0),
                                    "rastrigin_2d": _celda_con_exitos(3, 100.0)}])
    puntajes = puntuar_ensayos(registros, F_STAR_CERO)
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert [p[EVALS] for p in puntajes] == [None, 900.0, 100.0]
    assert elegir_ganador(puntajes) == 2
    assert elegir_ganador(json.loads(json.dumps(puntajes))) == 2


# R6: solo un puntaje principal estrictamente menor desplaza al ensayo 0.

def test_r6_a_empate_principal_con_el_defecto_lo_gana_el_0_aunque_pierda_los_desempates():
    # e0: f = [1e-9, 1e-9, 1e-3] -> m = 1e-6, tasa 2/3, evaluaciones 500.
    # e1: f = [1e-9] * 3        -> m = 1e-6, tasa 1,   evaluaciones 100.
    # Rangos 1.5 y 1.5: e1 gana los desempates 2 y 3, pero el empate principal lo gana el 0.
    registros = [{"rastrigin_2d": _reg([1e-9, 1e-9, 1e-3], [500.0, 500.0, None])},
                 {"rastrigin_2d": _reg([1e-9] * 3, [100.0] * 3)}]
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p["rango_medio"] for p in puntajes] == [1.5, 1.5]
    assert puntajes[1][TASA] > puntajes[0][TASA]
    assert puntajes[1][EVALS] < puntajes[0][EVALS]
    assert elegir_ganador(puntajes) == 0
    assert elegir_ganador(json.loads(json.dumps(puntajes))) == 0


def test_r6_b_un_puntaje_principal_menor_gana_aunque_el_defecto_tenga_mejor_tasa():
    # e0: f = [0, 0, 1, 1, 1] -> m = 1, tasa 2/5.  e1: f = [0.5] * 5 -> m = 0.5, tasa 0.
    registros = [{"rastrigin_2d": _celda_con_exitos(2)},
                 {"rastrigin_2d": _reg([0.5] * 5)}]
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p["rango_medio"] for p in puntajes] == [2.0, 1.0]
    assert puntajes[0][TASA] > puntajes[1][TASA]
    assert puntajes[1][EVALS] is None
    assert elegir_ganador(puntajes) == 1


@pytest.mark.parametrize("retadores, ganador", [
    # Desempate 2: e2 tiene tasa 1 y e1 2/3 (los dos con m = 1e-6).
    ([_reg([1e-9, 1e-9, 1e-3]), _reg([1e-9] * 3)], 2),
    # Desempate 3: misma tasa (1); evaluaciones 300 y 200.
    ([_reg([1e-9] * 3, [300.0] * 3), _reg([1e-9] * 3, [100.0, 200.0, 300.0])], 2),
    # Empate en todo: el menor índice entre los retadores.
    ([_reg([1e-9] * 3), _reg([1e-9] * 3)], 1),
], ids=["tasa", "evaluaciones", "indice"])
def test_r6_c_entre_retadores_empatados_y_mejores_que_el_0_deciden_los_desempates(
        retadores, ganador):
    registros = _con_defecto_peor([{"rastrigin_2d": registro} for registro in retadores])
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert elegir_ganador(puntajes) == ganador


def test_r6_d_caso_real_de_pso_y_de_un_exito_mas_no_desplaza_al_defecto():
    # 4 celdas x 5 semillas; e2 es peor en todas (m = 10, rango 3).
    #   celda           e0 (éxitos, m)    e1 (éxitos, m)    rangos e0 / e1
    #   rosenbrock_2d   5, 1e-6           2, 0.3            1   / 2
    #   rastrigin_2d    2, 0.5            5, 1e-6           2   / 1
    #   rosenbrock_3d   3, 1e-6           4, 1e-6           1.5 / 1.5
    #   rastrigin_3d    5, 1e-6           5, 1e-6           1.5 / 1.5
    # Rango medio 1.5 = 1.5. Éxitos: e0 15/20, e1 16/20; evaluaciones: e0 900, e1 100.
    # Con la clave lexicográfica completa ganaría el 1; con R6 gana el 0.
    def celda(exitos, resto, evals):
        return _reg([0.0] * exitos + [resto] * (5 - exitos),
                    [evals] * exitos + [None] * (5 - exitos))
    e0 = {"rosenbrock_2d": celda(5, 0.0, 900.0), "rastrigin_2d": celda(2, 0.5, 900.0),
          "rosenbrock_3d": celda(3, 1.0, 900.0), "rastrigin_3d": celda(5, 0.0, 900.0)}
    e1 = {"rosenbrock_2d": celda(2, 0.3, 100.0), "rastrigin_2d": celda(5, 0.0, 100.0),
          "rosenbrock_3d": celda(4, 1.0, 100.0), "rastrigin_3d": celda(5, 0.0, 100.0)}
    e2 = {clave: _reg([F_DEFECTO_PEOR] * 5) for clave in e0}
    f_star = {clave: 0.0 for clave in e0}
    puntajes = puntuar_ensayos([e0, e1, e2], f_star)
    assert [p["rango_medio"] for p in puntajes] == [1.5, 1.5, 3.0]
    assert puntajes[0][TASA] == 0.75 and puntajes[1][TASA] == 0.8
    assert [p[EVALS] for p in puntajes] == [900.0, 100.0, None]
    assert elegir_ganador(puntajes) == 0
    assert elegir_ganador(json.loads(json.dumps(puntajes))) == 0


def test_el_puntaje_guarda_los_conteos_exactos_por_celda():
    registros = [{"rastrigin_2d": _reg([0.0, 0.0, 1.0], [7.0, 10.0, None])}]
    puntaje = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})[0]
    assert puntaje["semillas_por_celda"] == {"rastrigin_2d": 3}
    assert puntaje[f"exitos_{SUFIJO}_por_celda"] == {"rastrigin_2d": 2}
    assert puntaje[f"suma_evals_hasta_exito_{SUFIJO}_por_celda"] == {"rastrigin_2d": 17}
    assert type(puntaje[f"suma_evals_hasta_exito_{SUFIJO}_por_celda"]["rastrigin_2d"]) is int
    assert puntaje[EVALS] == 8.5 and puntaje[TASA] == 2 / 3


def test_evaluaciones_no_enteras_dan_error():
    registros = [{"rastrigin_2d": _reg([0.0], [7.5])}]
    with pytest.raises(ValueError, match="entero"):
        puntuar_ensayos(registros, {"rastrigin_2d": 0.0})


def test_c_empate_total_gana_el_ensayo_0():
    registros = [{"rastrigin_2d": _reg([0.5, 0.7])} for _ in range(3)]
    assert elegir_ganador(puntuar_ensayos(registros, {"rastrigin_2d": 0.0})) == 0


def test_c_entre_empatados_que_no_son_el_0_gana_el_menor_indice():
    # m: e0 = 1, e1 = e2 = 1e-3 -> rangos 3, 1.5, 1.5; mismas tasas (0) y evals (None) -> 1.
    registros = [{"rastrigin_2d": _reg([1.0])}, {"rastrigin_2d": _reg([1e-3])},
                 {"rastrigin_2d": _reg([1e-3])}]
    puntajes = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})
    assert [p["rango_medio"] for p in puntajes] == [3.0, 1.5, 1.5]
    assert elegir_ganador(puntajes) == 1


def test_d_rangos_promedio_con_empates():
    # m = [1, 1, 2] -> rangos [1.5, 1.5, 3]; m = [3, 1, 1, 1] -> [4, 2, 2, 2].
    tres = [{"rastrigin_2d": _reg([f])} for f in (1.0, 1.0, 2.0)]
    assert [p["rango"]["rastrigin_2d"] for p in puntuar_ensayos(tres, {"rastrigin_2d": 0.0})] \
        == [1.5, 1.5, 3.0]
    cuatro = [{"rastrigin_2d": _reg([f])} for f in (3.0, 1.0, 1.0, 1.0)]
    assert [p["rango"]["rastrigin_2d"] for p in puntuar_ensayos(cuatro, {"rastrigin_2d": 0.0})] \
        == [4.0, 2.0, 2.0, 2.0]


def test_e_celda_sin_exitos_da_evaluaciones_none():
    registros = [{"rastrigin_2d": _reg([0.5, 0.7, 0.9])}]
    puntaje = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})[0]
    assert puntaje[TASA] == 0.0
    assert puntaje[EVALS] is None


def test_f_mediana_con_valores_recortados():
    # f − f* = [1e-9, 1e-9, 5e-6] -> recortes [1e-6, 1e-6, 5e-6] -> m = 1e-6.
    registros = [{"rastrigin_2d": _reg([1e-9, 1e-9, 5e-6])}]
    puntaje = puntuar_ensayos(registros, {"rastrigin_2d": 0.0})[0]
    assert puntaje["mediana_recortada"]["rastrigin_2d"] == 1e-6
    assert puntaje[TASA] == pytest.approx(2 / 3)


def test_la_mediana_par_promedia_los_dos_centrales_y_usa_f_star():
    # f* = 1: f − f* = [2, 4, 1, 3] -> m = (2 + 3)/2 = 2.5.
    registros = [{"rastrigin_2d": _reg([3.0, 5.0, 2.0, 4.0])}]
    puntaje = puntuar_ensayos(registros, {"rastrigin_2d": 1.0})[0]
    assert puntaje["mediana_recortada"]["rastrigin_2d"] == 2.5


def test_los_puntajes_no_tienen_no_finitos_ni_numpy():
    registros = [{"rosenbrock_2d": _reg([1e-9, 1.0]), "rastrigin_2d": _reg([2.0, 3.0])},
                 {"rosenbrock_2d": _reg([1e-3, 1.0]), "rastrigin_2d": _reg([1e-7, 3.0])}]
    puntajes = puntuar_ensayos(registros, F_STAR_CERO)
    assert _sin_no_finitos(puntajes)
    for clave in ("rango_medio", TASA, EVALS, "mediana_recortada", "rango"):
        assert all(clave in p for p in puntajes)


def test_puntuar_rechaza_celdas_distintas_entre_ensayos():
    registros = [{"rastrigin_2d": _reg([1.0])}, {"rosenbrock_2d": _reg([1.0])}]
    with pytest.raises(ValueError, match="celdas"):
        puntuar_ensayos(registros, F_STAR_CERO)


def test_puntuar_rechaza_una_celda_sin_f_star():
    with pytest.raises(ValueError, match="rastrigin_3d"):
        puntuar_ensayos([{"rastrigin_3d": _reg([1.0])}], F_STAR_CERO)


def test_puntuar_rechaza_listas_de_longitud_distinta():
    registro = _reg([1.0, 2.0])
    registro["n_f"] = [1]
    with pytest.raises(ValueError, match="longitud"):
        puntuar_ensayos([{"rastrigin_2d": registro}], F_STAR_CERO)


def test_puntuar_rechaza_una_lista_vacia_de_ensayos():
    with pytest.raises(ValueError):
        puntuar_ensayos([], F_STAR_CERO)


def test_el_resultado_no_depende_del_orden_de_las_celdas():
    a = [{"rosenbrock_2d": _reg([1e-1]), "rastrigin_2d": _reg([1.0])},
         {"rosenbrock_2d": _reg([1e-5]), "rastrigin_2d": _reg([1.1])}]
    b = [{"rastrigin_2d": r["rastrigin_2d"], "rosenbrock_2d": r["rosenbrock_2d"]} for r in a]
    pa, pb = puntuar_ensayos(a, F_STAR_CERO), puntuar_ensayos(b, F_STAR_CERO)
    assert [p["rango_medio"] for p in pa] == [p["rango_medio"] for p in pb]
    assert elegir_ganador(pa) == elegir_ganador(pb)


# ================================================================================================
# 8. config_afinada
# ================================================================================================

def _ganadores(cfg, cambios):
    """(Unidad, ensayo) por unidad: el ensayo 0 con las rutas de `cambios[nombre]` cambiadas."""
    ganadores = []
    for unidad in construir_unidades(cfg):
        ensayo = dict(sortear_ensayos(unidad, cfg, 1)[0])
        ensayo.update(cambios.get(unidad.nombre, {}))
        ganadores.append((unidad, ensayo))
    return ganadores


def test_config_afinada_solo_lleva_lo_que_cambio(cfg):
    antes = copy.deepcopy(cfg)
    ganadores = _ganadores(cfg, {
        "gdfijo_rastrigin": {"gd.eta.{func}": 0.0031},
        "pso": {"pso.N": 30, "pso.w": 0.6},                 # N igual al defecto
        "ea": {"ea.N": 80},
    })
    afinada = config_afinada(cfg, ganadores)
    assert afinada == {
        "hereda": "base.yaml",
        "salida": "results/data/part1_tuned",
        "tablas": "results/tables/part1_tuned",
        "gd": {"eta": {"rastrigin": 0.0031}},
        "ea": {"N": 80},
        "pso": {"w": 0.6},
    }
    assert list(afinada) == ["hereda", "salida", "tablas", "gd", "ea", "pso"]
    assert cfg == antes
    assert _sin_no_finitos(afinada)


def test_config_afinada_con_todos_los_ganadores_en_el_ensayo_0(cfg):
    afinada = config_afinada(cfg, _ganadores(cfg, {}), hereda="otra.yaml")
    assert afinada == {"hereda": "otra.yaml", "salida": "results/data/part1_tuned",
                       "tablas": "results/tables/part1_tuned"}


def test_config_afinada_anida_func_y_armijo_en_el_mismo_bloque(cfg):
    afinada = config_afinada(cfg, _ganadores(cfg, {
        "gdfijo_rosenbrock": {"gd.eta.{func}": 2e-4},
        "gdarmijo": {"gd.armijo.beta": 0.3},
    }))
    assert afinada["gd"] == {"eta": {"rosenbrock": 2e-4}, "armijo": {"beta": 0.3}}


def test_config_afinada_ida_y_vuelta_por_yaml(cfg, tmp_path):
    cambios = {
        "gdfijo_rosenbrock": {"gd.eta.{func}": 1.2345e-05},
        "gdarmijo": {"gd.armijo.c": 0.0031622776601683794, "gd.armijo.eta0": 2.5},
        "ea": {"ea.N": 120, "ea.frac_c": 0.6},
        "pso": {"pso.vmax_frac": 0.35},
        "de": {"de.F": 0.55, "de.NP": 45},
    }
    afinada = config_afinada(cfg, _ganadores(cfg, cambios))
    shutil.copyfile(RUTA_BASE, tmp_path / "base.yaml")
    ruta = tmp_path / "tuned.yaml"
    ruta.write_text(yaml.safe_dump(afinada, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    leida = load_config(ruta)
    esperada = copy.deepcopy(cfg)
    esperada["salida"] = "results/data/part1_tuned"
    esperada["tablas"] = "results/tables/part1_tuned"
    for nombre, rutas in cambios.items():
        func = "rosenbrock" if nombre == "gdfijo_rosenbrock" else None
        esperada = aplicar_ensayo(esperada, rutas, func)
    assert leida == esperada
    assert type(leida["ea"]["N"]) is int and type(leida["gd"]["eta"]["rosenbrock"]) is float


# ================================================================================================
# 9. Higiene del módulo
# ================================================================================================

@pytest.mark.parametrize("ruta", [RUTA_HPO, RUTA_PRUEBAS], ids=["hpo.py", "test_hpo.py"])
def test_lineas_de_hasta_100_caracteres_en_lf(ruta):
    crudo = ruta.read_bytes()
    assert b"\r" not in crudo
    lineas = crudo.decode("utf-8").splitlines()
    largas = [i + 1 for i, linea in enumerate(lineas) if len(linea) > LARGO_MAXIMO]
    assert largas == [], f"líneas de más de {LARGO_MAXIMO} caracteres: {largas}"


def test_todo_codigo_va_dentro_de_una_celda_de_codigo_percent():
    celda_actual = None
    lineas = RUTA_HPO.read_text(encoding="utf-8").splitlines()
    for numero, linea in enumerate(lineas, start=1):
        if linea.startswith("# %%"):
            celda_actual = "markdown" if "[markdown]" in linea else "codigo"
        elif re.match(r"(def |class |import |from |@|[A-Za-z_]+\s*=)", linea):
            assert celda_actual == "codigo", f"línea {numero} fuera de una celda de código"


def test_cabecera_markdown_con_los_nombres_publicos():
    texto = RUTA_HPO.read_text(encoding="utf-8")
    assert texto.startswith("# %% [markdown]")
    cabecera = texto.split("# %%\n")[0]
    for nombre in ("validar_hpo", "construir_unidades", "sortear_ensayos", "aplicar_ensayo",
                   "clave_celda", "puntuar_ensayos", "elegir_ganador", "config_afinada"):
        assert f"`{nombre}`" in cabecera


def test_el_modulo_no_usa_azar_global_ni_corre_ni_escribe():
    texto = RUTA_HPO.read_text(encoding="utf-8")
    for prohibido in ("np.random", "import random", "CountedProblem", "default_rng",
                      "ejecutar_corrida", "print(", "open(", "write_text", "save_json",
                      "load_json", "load_config"):
        assert prohibido not in texto, prohibido
