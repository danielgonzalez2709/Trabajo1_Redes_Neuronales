# %% [markdown]
# # Optimización de hiperparámetros de la Parte 1: piezas puras (T1.10-A; Spec §6.9)
#
# Implementa las reglas R1–R8 de Spec §6.9 que no necesitan correr nada; usa también §4.1
# (config) y §6.2-§6.6 (presupuesto, umbrales y métricas).
#
# **Propósito.** Las piezas deterministas de la búsqueda de hiperparámetros (HPO): validar el
# bloque `hpo:` de la config, formar las unidades de búsqueda, sortear los ensayos, aplicar un
# ensayo a una copia de la config, puntuar los ensayos de una unidad, elegir el ganador y armar
# la config afinada. Este módulo no corre optimizadores, no lee ni escribe archivos y no
# imprime: la orquestación (correr los ensayos, guardar, CLI) es de T1.10-B.
#
# **Mapa del módulo:**
#
# | # | Nombre | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `validar_hpo` | revisa el bloque `hpo:` antes de correr nada | `None` |
# | 2 | `construir_unidades` | unidades de búsqueda (`Unidad`, `Hiperparametro`) | `list` |
# | 3 | `sortear_ensayos` | ensayo 0 = defecto; el resto, muestreo aleatorio válido | `list[dict]` |
# | 4 | `aplicar_ensayo` | copia profunda de la config con el ensayo puesto | `dict` |
# | 5 | `clave_celda` | nombre de texto de una celda (función, dimensión) | `str` |
# | 6 | `puntuar_ensayos` | rangos, tasa de éxito y evaluaciones de cada ensayo | `list[dict]` |
# | 7 | `elegir_ganador` | índice del ganador (el 0 salvo rango medio menor) | `int` |
# | 8 | `config_afinada` | config que hereda de la base con solo lo que cambió | `dict` |
#
# También es pública la auxiliar `bloque_del_metodo` (bloque de la config de un método; la
# usa `hpo_experimento.py`).
#
# **Protocolo.** Cada unidad recibe `hpo.ensayos` ensayos; cada ensayo se evalúa con
# `hpo.semillas` semillas (de `hpo.base_seed` en adelante), disjuntas de las semillas de
# reporte `base_seed .. base_seed + runs − 1`, y con el presupuesto del experimento (Spec §6.2).
#
# **Azar.** El generador de la unidad $i$ es `make_rng(hpo.semilla_busqueda, i)` (Spec §6.9 R4);
# solo lo usa `sortear_ensayos`.

# %%
"""Optimización de hiperparámetros de la Parte 1: validación, unidades, muestreo y selección."""

from __future__ import annotations

import copy
import math
import os
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from numbers import Integral, Real
from pathlib import PurePath

from src.common.config import CLAVE_HEREDA, SEPARADOR_CLAVE
from src.common.seeds import make_rng, validar_entero
from src.part1._comun import validar_claves_exactas
from src.part1.corrida import CLAVE_RECORD_FRAMES, CLAVE_VARIANTE, METODOS, METODOS_GD
from src.part1.de import NOMBRE_BLOQUE_DE, ParametrosDE
from src.part1.ea import NOMBRE_BLOQUE_EA, ParametrosEA
from src.part1.experiment import (
    CLAVE_BASE_SEED,
    CLAVE_DIM,
    CLAVE_FUNC,
    CLAVE_METODOS,
    CLAVE_RUNS,
    CLAVE_SALIDA,
    CLAVE_TABLAS,
)
from src.part1.metricas import UMBRALES, clave_umbral
from src.part1.pso import NOMBRE_BLOQUE_PSO, ParametrosPSO

# %% [markdown]
# ## Constantes del módulo
#
# Claves del bloque `hpo:` y de cada hiperparámetro, tipos de muestreo, el tope de intentos
# por ensayo, el umbral de la selección y los nombres de los campos de registros y puntajes.
# Los valores por defecto del protocolo no están aquí: viven en `configs/part1/base.yaml`.

# %%
CLAVE_HPO = "hpo"
CLAVE_ENSAYOS = "ensayos"
CLAVE_SEMILLAS = "semillas"
CLAVE_HPO_BASE_SEED = "base_seed"
CLAVE_SEMILLA_BUSQUEDA = "semilla_busqueda"
CLAVE_REANUDAR = "reanudar"
CLAVE_HPO_SALIDA = "salida"
CLAVE_SALIDA_AFINADA = "salida_afinada"
CLAVE_TABLAS_AFINADA = "tablas_afinada"
CLAVE_CONFIG_SALIDA = "config_salida"
CLAVE_ESPACIOS = "espacios"
CLAVES_HPO = (CLAVE_ENSAYOS, CLAVE_SEMILLAS, CLAVE_HPO_BASE_SEED, CLAVE_SEMILLA_BUSQUEDA,
              CLAVE_REANUDAR, CLAVE_HPO_SALIDA, CLAVE_SALIDA_AFINADA, CLAVE_TABLAS_AFINADA,
              CLAVE_CONFIG_SALIDA, CLAVE_ESPACIOS)
CLAVES_DE_TEXTO = (CLAVE_HPO_SALIDA, CLAVE_SALIDA_AFINADA, CLAVE_TABLAS_AFINADA,
                   CLAVE_CONFIG_SALIDA)
MINIMO_POSITIVO = 1                      # ensayos, semillas y runs: enteros >= 1

CLAVE_RUTA = "ruta"
CLAVE_TIPO = "tipo"
CLAVE_MIN = "min"
CLAVE_MAX = "max"
CLAVES_HIPERPARAMETRO = (CLAVE_RUTA, CLAVE_TIPO, CLAVE_MIN, CLAVE_MAX)
TIPO_UNIFORME = "uniforme"
TIPO_LOG = "log"
TIPO_ENTERO = "entero"
TIPOS = (TIPO_UNIFORME, TIPO_LOG, TIPO_ENTERO)

MARCADOR_FUNC = "{func}"                 # segmento de ruta que se sustituye por la función
LLAVES = ("{", "}")                      # solo pueden aparecer dentro de MARCADOR_FUNC
SEPARADOR_RUTA = SEPARADOR_CLAVE         # "gd.armijo.beta": el mismo separador que --set
SEPARADOR_UNIDAD = "_"                   # nombre de unidad: método + "_" + función
SUFIJO_DIMENSION = "d"                   # clave de celda: "<func>_<dim>d"
BLOQUE_GD = "gd"                         # gdfijo y gdarmijo comparten el bloque gd:
# Claves que no se afinan: rompen la comparación justa (§6.2) o no son hiperparámetros.
CLAVES_NO_AFINABLES = ("generaciones", "iteraciones", "esquema", "reevaluar_elite", "tol_grad",
                       CLAVE_VARIANTE, CLAVE_RECORD_FRAMES)

INTENTOS_MAXIMOS = 200                   # sorteos por ensayo antes de rendirse (R4)

CLAVE_GD_ETA = "eta"                     # gd.eta.<función>: paso fijo
CLAVE_GD_ARMIJO = "armijo"               # gd.armijo.{eta0, beta, c}
CLAVE_ETA0 = "eta0"
CLAVE_BETA = "beta"
CLAVE_C = "c"
COTA_INFERIOR_PASO = 0.0                 # η y η₀: reales finitos > 0 (exclusivo)
INTERVALO_ARMIJO = (0.0, 1.0)            # β y c: 0 < valor < 1 (abierto)

UMBRAL_HPO = min(UMBRALES)               # 1e-6: el umbral más estricto de Spec §6.5
SUFIJO_UMBRAL = clave_umbral(UMBRAL_HPO)

CAMPO_F_BEST = "f_best"
CAMPO_N_F = "n_f"
CAMPO_N_GRAD = "n_grad"
CAMPO_EVAL_EQUIV = "eval_equiv"
CAMPO_EVALS_EXITO = f"evals_hasta_exito_{SUFIJO_UMBRAL}"
CAMPOS_REGISTRO = (CAMPO_F_BEST, CAMPO_N_F, CAMPO_N_GRAD, CAMPO_EVAL_EQUIV, CAMPO_EVALS_EXITO)

PUNTAJE_INDICE = "indice"
PUNTAJE_RANGO_MEDIO = "rango_medio"
PUNTAJE_TASA = f"tasa_exito_{SUFIJO_UMBRAL}"
PUNTAJE_EVALS = f"evals_hasta_exito_{SUFIJO_UMBRAL}"
PUNTAJE_MEDIANA = "mediana_recortada"
PUNTAJE_RANGO = "rango"
PUNTAJE_TASA_POR_CELDA = f"{PUNTAJE_TASA}_por_celda"
PUNTAJE_EVALS_POR_CELDA = f"{PUNTAJE_EVALS}_por_celda"
PUNTAJE_SEMILLAS_POR_CELDA = "semillas_por_celda"
PUNTAJE_EXITOS_POR_CELDA = f"exitos_{SUFIJO_UMBRAL}_por_celda"
PUNTAJE_SUMA_EVALS_POR_CELDA = f"suma_evals_hasta_exito_{SUFIJO_UMBRAL}_por_celda"

HEREDA_POR_DEFECTO = "base.yaml"         # la config afinada hereda de la base (Spec §4.1)


# %% [markdown]
# ## Auxiliares de validación y de rutas
#
# Una **ruta** es una cadena de claves separadas por `.` (como en `--set`), p. ej.
# `gd.armijo.beta`. El segmento `{func}` se sustituye por el nombre de una función:
# `gd.eta.{func}` con `rastrigin` es `gd.eta.rastrigin`.

# %%
def _exigir_clave(cfg: Mapping, clave: str, nombre: str):
    """Devuelve `cfg[clave]`; si la clave no está, ValueError que nombra `nombre`."""
    if clave not in cfg:
        raise ValueError(f"falta la clave '{nombre}' en la config de la Parte 1")
    return cfg[clave]


def _validar_texto(valor, nombre: str) -> str:
    """Devuelve `valor` si es texto con algún carácter que no sea espacio; si no, error."""
    if not isinstance(valor, str):
        raise TypeError(f"{nombre} debe ser un texto; se recibió {valor!r} "
                        f"({type(valor).__name__})")
    if not valor.strip():
        raise ValueError(f"{nombre} no puede ser un texto vacío")
    return valor


def _validar_real_finito(valor, nombre: str):
    """Devuelve `valor` sin convertir si es un real finito; bool o no real -> TypeError."""
    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise TypeError(f"{nombre} debe ser un número real; se recibió {valor!r} "
                        f"({type(valor).__name__})")
    if not math.isfinite(valor):
        raise ValueError(f"{nombre} debe ser finito; se recibió {valor!r}")
    return valor


def _rechazar_no_finitos(valor, ruta: str) -> None:
    """ValueError con la ruta de la clave si `valor` contiene un real NaN o infinito.

    Recorre mapeos y listas (o tuplas) a cualquier profundidad.
    """
    if isinstance(valor, Mapping):
        for clave, hijo in valor.items():
            _rechazar_no_finitos(hijo, f"{ruta}{SEPARADOR_RUTA}{clave}")
    elif isinstance(valor, (list, tuple)):
        for posicion, hijo in enumerate(valor):
            _rechazar_no_finitos(hijo, f"{ruta}[{posicion}]")
    elif isinstance(valor, Real) and not isinstance(valor, Integral):
        if not math.isfinite(valor):
            raise ValueError(f"{ruta} no es finito ({valor!r}): el bloque hpo no admite NaN "
                             "ni infinitos")


def _segmentos_de_ruta(ruta, nombre: str) -> list[str]:
    """Separa una ruta en segmentos no vacíos; `{func}` solo puede ser un segmento entero."""
    _validar_texto(ruta, nombre)
    segmentos = ruta.split(SEPARADOR_RUTA)
    if not all(segmentos):
        raise ValueError(f"{nombre} = {ruta!r}: hay segmentos vacíos (dos puntos seguidos o "
                         "un punto en un extremo)")
    for segmento in segmentos:
        if segmento != MARCADOR_FUNC and any(llave in segmento for llave in LLAVES):
            raise ValueError(f"{nombre} = {ruta!r}: el marcador {MARCADOR_FUNC} debe ser un "
                             f"segmento completo (p. ej. gd.eta.{MARCADOR_FUNC})")
    return segmentos


def _sustituir_func(segmentos: Sequence[str], func: str | None, ruta: str) -> list[str]:
    """Segmentos con `{func}` cambiado por `func`; ValueError si hace falta y `func` es None."""
    if MARCADOR_FUNC in segmentos and func is None:
        raise ValueError(f"la ruta {ruta!r} lleva {MARCADOR_FUNC} y no se indicó la función "
                         "(func = None)")
    return [func if segmento == MARCADOR_FUNC else segmento for segmento in segmentos]


def _nodo_padre(cfg: Mapping, segmentos: Sequence[str], ruta: str) -> Mapping:
    """Mapeo que contiene la hoja de `segmentos`; ValueError si la ruta no existe en `cfg`."""
    nodo = cfg
    for posicion, segmento in enumerate(segmentos):
        if not isinstance(nodo, Mapping) or segmento not in nodo:
            tramo = SEPARADOR_RUTA.join(segmentos[:posicion + 1])
            raise ValueError(f"la ruta {ruta!r} no existe en la config (falta '{tramo}')")
        if posicion == len(segmentos) - 1:
            return nodo
        nodo = nodo[segmento]
    raise ValueError(f"la ruta {ruta!r} está vacía")


def _leer_hoja(cfg: Mapping, segmentos: Sequence[str], ruta: str):
    """Valor de la hoja de `segmentos` en `cfg`; ValueError si no existe o es un mapeo."""
    valor = _nodo_padre(cfg, segmentos, ruta)[segmentos[-1]]
    if isinstance(valor, Mapping):
        raise ValueError(f"la ruta {ruta!r} apunta a un bloque, no a un valor")
    return valor


def bloque_del_metodo(metodo: str) -> str:
    """Primer segmento que deben tener las rutas de `metodo`: `gd` para los GD; si no, él."""
    return BLOQUE_GD if metodo in METODOS_GD else metodo


# %% [markdown]
# ## 1. `validar_hpo`
#
# | Clave | Regla |
# |---|---|
# | `hpo` | mapeo con exactamente las claves de `CLAVES_HPO` |
# | `ensayos`, `semillas` | entero $\ge 1$ (no bool) |
# | `base_seed`, `semilla_busqueda` | entero $\ge 0$ (no bool) |
# | `reanudar` | bool |
# | `salida`, `salida_afinada`, `tablas_afinada`, `config_salida` | texto no vacío |
# | `espacios` | método de `METODOS` → nombre corto (sin puntos) → `{ruta, tipo, min, max}` |
# | `tipo` | `uniforme`, `log` ($\text{min} > 0$) o `entero` (extremos enteros) |
# | `min`, `max` | reales finitos (no bool), $\text{min} < \text{max}$ |
# | `ruta` | empieza por el bloque del método; existe y es una hoja para cada función de `func` |
#
# Además: ninguna ruta termina en una clave de `CLAVES_NO_AFINABLES`; una ruta concreta no
# aparece en dos hiperparámetros; un método no mezcla rutas con y sin `{func}`; cada método de
# `methods` tiene un espacio no vacío; las semillas de ajuste
# $[b_h,\ b_h + s - 1]$ y de reporte $[b,\ b + R - 1]$ son disjuntas; y las carpetas de
# salida no coinciden (rutas comparadas con `os.path.normpath`, sin tocar el disco). R8:
# `hpo.salida_afinada` y `hpo.salida` no están dentro de `salida`, ni `salida` dentro de
# `hpo.salida_afinada`; en las tablas solo se exige que no coincidan (el demo pone
# `hpo.tablas_afinada` dentro de `tablas`).
#
# Los espacios de métodos que no están en `methods` se validan igual (forma y rutas), pero no
# forman unidades.

# %%
def _validar_nombre_corto(nombre_corto, nombre: str) -> None:
    """El nombre corto de un hiperparámetro es texto no vacío y sin puntos (para `--set`)."""
    if not isinstance(nombre_corto, str):
        raise TypeError(f"{nombre}: el nombre del hiperparámetro debe ser texto; se recibió "
                        f"{nombre_corto!r}")
    if not nombre_corto or SEPARADOR_RUTA in nombre_corto:
        raise ValueError(f"{nombre}: el nombre del hiperparámetro {nombre_corto!r} no puede "
                         f"estar vacío ni llevar '{SEPARADOR_RUTA}'")


def _validar_limites(hiper: Mapping, nombre: str) -> None:
    """Tipo de muestreo y extremos de un hiperparámetro (tabla de arriba)."""
    tipo = hiper[CLAVE_TIPO]
    if not isinstance(tipo, str) or tipo not in TIPOS:
        raise ValueError(f"{nombre}.{CLAVE_TIPO} = {tipo!r} no es válido; válidos: "
                         f"{', '.join(TIPOS)}")
    minimo = _validar_real_finito(hiper[CLAVE_MIN], f"{nombre}.{CLAVE_MIN}")
    maximo = _validar_real_finito(hiper[CLAVE_MAX], f"{nombre}.{CLAVE_MAX}")
    if tipo == TIPO_ENTERO:
        for clave, valor in ((CLAVE_MIN, minimo), (CLAVE_MAX, maximo)):
            if not isinstance(valor, Integral):
                raise TypeError(f"{nombre}.{clave} debe ser un entero (tipo {TIPO_ENTERO}); "
                                f"se recibió {valor!r} ({type(valor).__name__})")
    if not minimo < maximo:
        raise ValueError(f"{nombre}: se necesita min < max; se recibió min = {minimo!r}, "
                         f"max = {maximo!r}")
    if tipo == TIPO_LOG and minimo <= 0:
        raise ValueError(f"{nombre}: el tipo {TIPO_LOG} exige min > 0; se recibió "
                         f"min = {minimo!r}")


def _rutas_concretas(cfg: Mapping, metodo: str, hiper: Mapping, nombre: str,
                     funciones: Sequence[str]) -> list[str]:
    """Valida la ruta de un hiperparámetro y devuelve sus rutas concretas (sin `{func}`)."""
    ruta = hiper[CLAVE_RUTA]
    segmentos = _segmentos_de_ruta(ruta, f"{nombre}.{CLAVE_RUTA}")
    bloque = bloque_del_metodo(metodo)
    if segmentos[0] != bloque:
        raise ValueError(f"{nombre}.{CLAVE_RUTA} = {ruta!r}: las rutas de '{metodo}' deben "
                         f"empezar por el bloque '{bloque}'")
    variantes = funciones if MARCADOR_FUNC in segmentos else [None]
    concretas = []
    for func in variantes:
        concreta = _sustituir_func(segmentos, func, ruta)
        texto = SEPARADOR_RUTA.join(concreta)
        if concreta[-1] in CLAVES_NO_AFINABLES:
            raise ValueError(f"{nombre}.{CLAVE_RUTA} = {ruta!r}: '{concreta[-1]}' no se afina "
                             "(rompe la comparación justa o no es un hiperparámetro)")
        _leer_hoja(cfg, concreta, texto)
        concretas.append(texto)
    return concretas


def _validar_espacios(cfg: Mapping, espacios, funciones: Sequence[str],
                      metodos: Sequence[str]) -> None:
    """Forma de cada espacio, sus rutas, la regla R5 y las rutas repetidas."""
    nombre_espacios = f"{CLAVE_HPO}.{CLAVE_ESPACIOS}"
    if not isinstance(espacios, Mapping):
        raise TypeError(f"{nombre_espacios} debe ser un mapeo método -> espacio; se recibió "
                        f"{type(espacios).__name__}")
    duenos = []                          # (ruta concreta, nombre del hiperparámetro)
    for metodo, espacio in espacios.items():
        nombre_metodo = f"{nombre_espacios}.{metodo}"
        if metodo not in METODOS:
            raise ValueError(f"{nombre_espacios}: método desconocido {metodo!r}; válidos: "
                             f"{', '.join(METODOS)}")
        if not isinstance(espacio, Mapping):
            raise TypeError(f"{nombre_metodo} debe ser un mapeo nombre -> hiperparámetro; se "
                            f"recibió {type(espacio).__name__}")
        con_marcador = []
        for nombre_corto, hiper in espacio.items():
            nombre = f"{nombre_metodo}.{nombre_corto}"
            _validar_nombre_corto(nombre_corto, nombre)
            validar_claves_exactas(hiper, CLAVES_HIPERPARAMETRO, nombre)
            _validar_limites(hiper, nombre)
            for concreta in _rutas_concretas(cfg, metodo, hiper, nombre, funciones):
                duenos.append((concreta, nombre))
            con_marcador.append(MARCADOR_FUNC in hiper[CLAVE_RUTA].split(SEPARADOR_RUTA))
        if any(con_marcador) and not all(con_marcador):
            raise ValueError(f"{nombre_metodo} mezcla rutas con y sin {MARCADOR_FUNC}: o todas "
                             "lo llevan (una unidad por función) o ninguna (una sola unidad)")
    vistos = {}
    for concreta, nombre in duenos:
        if concreta in vistos:
            raise ValueError(f"la ruta {concreta!r} aparece en dos hiperparámetros: "
                             f"{vistos[concreta]} y {nombre}")
        vistos[concreta] = nombre
    for metodo in metodos:
        if not espacios.get(metodo):
            raise ValueError(f"el método {metodo!r} está en {CLAVE_METODOS} pero "
                             f"{nombre_espacios}.{metodo} falta o está vacío")


def _validar_semillas(cfg: Mapping, hpo: Mapping) -> None:
    """R2: semillas de ajuste y de reporte disjuntas."""
    base_reporte = validar_entero(_exigir_clave(cfg, CLAVE_BASE_SEED, CLAVE_BASE_SEED),
                                  CLAVE_BASE_SEED)
    runs = validar_entero(_exigir_clave(cfg, CLAVE_RUNS, CLAVE_RUNS), CLAVE_RUNS,
                          minimo=MINIMO_POSITIVO)
    base_ajuste = hpo[CLAVE_HPO_BASE_SEED]
    ultima_ajuste = base_ajuste + hpo[CLAVE_SEMILLAS] - 1
    ultima_reporte = base_reporte + runs - 1
    if base_ajuste <= ultima_reporte and base_reporte <= ultima_ajuste:
        raise ValueError(
            f"las semillas de ajuste {base_ajuste}..{ultima_ajuste} (hpo.base_seed, "
            f"hpo.semillas) se solapan con las semillas de reporte {base_reporte}.."
            f"{ultima_reporte} (base_seed, runs): deben ser disjuntas"
        )


def _validar_carpetas(cfg: Mapping, hpo: Mapping) -> None:
    """Las carpetas de la HPO y de la config afinada no pisan las del experimento."""
    salida = _validar_texto(_exigir_clave(cfg, CLAVE_SALIDA, CLAVE_SALIDA), CLAVE_SALIDA)
    tablas = _validar_texto(_exigir_clave(cfg, CLAVE_TABLAS, CLAVE_TABLAS), CLAVE_TABLAS)
    pares = (
        (f"{CLAVE_HPO}.{CLAVE_SALIDA_AFINADA}", hpo[CLAVE_SALIDA_AFINADA], CLAVE_SALIDA, salida),
        (f"{CLAVE_HPO}.{CLAVE_SALIDA_AFINADA}", hpo[CLAVE_SALIDA_AFINADA],
         f"{CLAVE_HPO}.{CLAVE_HPO_SALIDA}", hpo[CLAVE_HPO_SALIDA]),
        (f"{CLAVE_HPO}.{CLAVE_TABLAS_AFINADA}", hpo[CLAVE_TABLAS_AFINADA], CLAVE_TABLAS, tablas),
        (f"{CLAVE_HPO}.{CLAVE_HPO_SALIDA}", hpo[CLAVE_HPO_SALIDA], CLAVE_SALIDA, salida),
    )
    for nombre, carpeta, nombre_otra, otra in pares:
        if os.path.normpath(carpeta) == os.path.normpath(otra):
            raise ValueError(f"{nombre} ({carpeta!r}) no puede ser la misma carpeta que "
                             f"{nombre_otra} ({otra!r})")
    # R8: dentro de `salida` no se escribe nada de la HPO, y el experimento afinado no contiene
    # al de por defecto. `salida` sí puede estar dentro de `hpo.salida` (el demo lo hace).
    contenidas = (
        (f"{CLAVE_HPO}.{CLAVE_SALIDA_AFINADA}", hpo[CLAVE_SALIDA_AFINADA], CLAVE_SALIDA, salida),
        (CLAVE_SALIDA, salida, f"{CLAVE_HPO}.{CLAVE_SALIDA_AFINADA}", hpo[CLAVE_SALIDA_AFINADA]),
        (f"{CLAVE_HPO}.{CLAVE_HPO_SALIDA}", hpo[CLAVE_HPO_SALIDA], CLAVE_SALIDA, salida),
    )
    for nombre, carpeta, nombre_otra, otra in contenidas:
        if _esta_dentro(carpeta, otra):
            raise ValueError(f"{nombre} ({carpeta!r}) no puede estar dentro de {nombre_otra} "
                             f"({otra!r}): la HPO no escribe en las carpetas por defecto (R8)")


def _esta_dentro(carpeta: str, otra: str) -> bool:
    """True si `carpeta` está dentro de `otra` (rutas normalizadas, sin tocar el disco)."""
    return PurePath(os.path.normpath(otra)) in PurePath(os.path.normpath(carpeta)).parents


def validar_hpo(cfg: dict) -> None:
    """Revisa el bloque `hpo:` de la config de la Parte 1; no corre nada y no modifica `cfg`.

    No valida el resto de la config (eso lo hace `experiment.validar_config`); solo lee de
    ella `func`, `methods`, `base_seed`, `runs`, `salida`, `tablas` y las rutas de los espacios.

    Raises
    ------
    TypeError
        Una clave tiene un tipo que no corresponde (el mensaje la nombra, p. ej.
        `hpo.espacios.pso.w.min`).
    ValueError
        Falta o sobra una clave; valor fuera de rango; real no finito; método desconocido o
        sin espacio; ruta inválida, inexistente, fuera de su bloque, no afinable o repetida;
        mezcla de rutas con y sin `{func}`; semillas solapadas; carpetas iguales o una dentro
        de otra (R8).
    """
    if not isinstance(cfg, Mapping):
        raise TypeError(f"la config debe ser un mapeo (dict); se recibió {type(cfg).__name__}")
    hpo = _exigir_clave(cfg, CLAVE_HPO, CLAVE_HPO)
    validar_claves_exactas(hpo, CLAVES_HPO, CLAVE_HPO)
    _rechazar_no_finitos(hpo, CLAVE_HPO)

    for clave in (CLAVE_ENSAYOS, CLAVE_SEMILLAS):
        validar_entero(hpo[clave], f"{CLAVE_HPO}.{clave}", minimo=MINIMO_POSITIVO)
    for clave in (CLAVE_HPO_BASE_SEED, CLAVE_SEMILLA_BUSQUEDA):
        validar_entero(hpo[clave], f"{CLAVE_HPO}.{clave}")
    if not isinstance(hpo[CLAVE_REANUDAR], bool):
        raise TypeError(f"{CLAVE_HPO}.{CLAVE_REANUDAR} debe ser bool (true o false); se "
                        f"recibió {hpo[CLAVE_REANUDAR]!r}")
    for clave in CLAVES_DE_TEXTO:
        _validar_texto(hpo[clave], f"{CLAVE_HPO}.{clave}")

    funciones = _exigir_clave(cfg, CLAVE_FUNC, CLAVE_FUNC)
    metodos = _exigir_clave(cfg, CLAVE_METODOS, CLAVE_METODOS)
    for clave, valor in ((CLAVE_FUNC, funciones), (CLAVE_METODOS, metodos)):
        if not isinstance(valor, list):
            raise TypeError(f"{clave} debe ser una lista; se recibió {valor!r}")
    _validar_espacios(cfg, hpo[CLAVE_ESPACIOS], funciones, metodos)
    _validar_semillas(cfg, hpo)
    _validar_carpetas(cfg, hpo)


# %% [markdown]
# ## 2. `construir_unidades`
#
# Una **unidad de búsqueda** es un conjunto de hiperparámetros que se afina junto, con sus
# celdas (función, dimensión). Regla R5:
#
# | Rutas del método | Unidades | Celdas de cada unidad |
# |---|---|---|
# | ninguna lleva `{func}` | una, con el nombre del método | todos los pares de `func` × `dim` |
# | todas llevan `{func}` | una por función: `<método>_<función>` | las dimensiones de esa función |
#
# Orden: el de `methods` y, dentro de un método con `{func}`, el de `func`. Las celdas van en
# el orden `func` y luego `dim`. El índice de una unidad es su posición en la lista.

# %%
@dataclass(frozen=True)
class Hiperparametro:
    """Un hiperparámetro del espacio de búsqueda (intervalo cerrado [minimo, maximo])."""

    nombre: str                          # nombre corto en hpo.espacios.<método>
    ruta: str                            # tal cual en el espacio (puede llevar {func})
    tipo: str                            # uno de TIPOS
    minimo: float | int                  # int si tipo == entero; si no, float
    maximo: float | int


@dataclass(frozen=True)
class Unidad:
    """Unidad de búsqueda: un método (y quizá una función) con sus celdas y su espacio."""

    nombre: str                          # método, o método + "_" + función
    metodo: str                          # uno de METODOS
    func: str | None                     # función si las rutas llevan {func}; si no, None
    indice: int                          # posición en construir_unidades
    celdas: tuple                        # ((func, dim), ...)
    parametros: tuple                    # (Hiperparametro, ...) en el orden del espacio


def _hiperparametro(nombre_corto: str, hiper: Mapping) -> Hiperparametro:
    """Hiperparametro con extremos int (tipo entero) o float (uniforme y log)."""
    convertir = int if hiper[CLAVE_TIPO] == TIPO_ENTERO else float
    return Hiperparametro(nombre_corto, hiper[CLAVE_RUTA], hiper[CLAVE_TIPO],
                          convertir(hiper[CLAVE_MIN]), convertir(hiper[CLAVE_MAX]))


def _lleva_marcador(ruta: str) -> bool:
    """True si algún segmento de `ruta` es `{func}`."""
    return MARCADOR_FUNC in ruta.split(SEPARADOR_RUTA)


def construir_unidades(cfg: dict) -> list[Unidad]:
    """Unidades de búsqueda de `cfg` según R5 (tabla de arriba); llama a `validar_hpo`.

    Raises
    ------
    TypeError, ValueError
        Los de `validar_hpo`; y ValueError si falta `dim`.
    """
    validar_hpo(cfg)
    espacios = cfg[CLAVE_HPO][CLAVE_ESPACIOS]
    funciones = cfg[CLAVE_FUNC]
    dimensiones = _exigir_clave(cfg, CLAVE_DIM, CLAVE_DIM)
    unidades = []
    for metodo in cfg[CLAVE_METODOS]:
        parametros = tuple(_hiperparametro(nombre_corto, hiper)
                           for nombre_corto, hiper in espacios[metodo].items())
        # validar_hpo ya exigió que todas las rutas del método lleven {func} o ninguna.
        if _lleva_marcador(parametros[0].ruta):
            grupos = [(f"{metodo}{SEPARADOR_UNIDAD}{func}", func,
                       tuple((func, dim) for dim in dimensiones)) for func in funciones]
        else:
            grupos = [(metodo, None,
                       tuple((func, dim) for func in funciones for dim in dimensiones))]
        for nombre, func, celdas in grupos:
            unidades.append(Unidad(nombre, metodo, func, len(unidades), celdas, parametros))
    return unidades


# %% [markdown]
# ## 3. `sortear_ensayos`
#
# **Ensayo 0** = valores por defecto, leídos de la config recibida (con `{func}` sustituido por
# la función de la unidad). **Ensayos 1..T−1**: con el generador de la unidad,
# `make_rng(hpo.semilla_busqueda, indice)`, se sortea cada hiperparámetro en el orden de su
# espacio:
#
# Con $a = \text{min}$ y $b = \text{max}$:
#
# | Tipo | Sorteo |
# |---|---|
# | `uniforme` | $v \sim \mathcal{U}(a, b)$ |
# | `log` | $v = \exp(u)$, $u \sim \mathcal{U}(\ln a, \ln b)$, recortado a $[a, b]$ |
# | `entero` | $v$ entero uniforme en $\{a, \dots, b\}$ |
#
# El recorte del tipo `log` corrige el redondeo de $\exp(\ln x)$, que puede salirse del
# intervalo por una cifra.
#
# **Validez.** El ensayo se aplica a una copia de la config y se valida con la regla del
# método: `ParametrosEA/PSO/DE.desde_config` sobre su bloque, o las reglas del GD
# ($\eta > 0$ finito; Armijo: $\eta_0 > 0$ finito, $0 < \beta < 1$, $0 < c < 1$). Un ensayo
# inválido se vuelve a sortear con el mismo generador, hasta `INTENTOS_MAXIMOS` veces; los
# descartados no cuentan como ensayo. Los avisos (`warnings`) de `desde_config`, como el de
# $w \ge 1$ del PSO, se silencian solo durante esta validación: los emite la corrida.

# %%
def _sortear_valor(parametro: Hiperparametro, rng):
    """Un valor de `parametro` como int o float de Python (tabla de arriba)."""
    if parametro.tipo == TIPO_ENTERO:
        return int(rng.integers(parametro.minimo, parametro.maximo, endpoint=True))
    if parametro.tipo == TIPO_LOG:
        valor = float(math.exp(rng.uniform(math.log(parametro.minimo),
                                           math.log(parametro.maximo))))
        return float(min(max(valor, parametro.minimo), parametro.maximo))
    return float(rng.uniform(parametro.minimo, parametro.maximo))


def _exigir_paso_positivo(valor, nombre: str) -> None:
    """η o η₀: real (no bool) finito y > COTA_INFERIOR_PASO."""
    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise TypeError(f"{nombre} debe ser un número real; se recibió {valor!r}")
    if not (COTA_INFERIOR_PASO < valor < math.inf):          # también rechaza NaN
        raise ValueError(f"{nombre} debe ser finito y > {COTA_INFERIOR_PASO}; se recibió "
                         f"{valor!r}")


def _exigir_intervalo_armijo(valor, nombre: str) -> None:
    """β o c: real (no bool) en el intervalo abierto INTERVALO_ARMIJO."""
    inferior, superior = INTERVALO_ARMIJO
    if isinstance(valor, bool) or not isinstance(valor, Real):
        raise TypeError(f"{nombre} debe ser un número real; se recibió {valor!r}")
    if not (inferior < valor < superior):                    # también rechaza NaN
        raise ValueError(f"{nombre} debe cumplir {inferior} < {nombre} < {superior}; se "
                         f"recibió {valor!r}")


def _bloque_gd(copia: Mapping, clave: str) -> Mapping:
    """Sub-bloque `gd.<clave>` de la copia; ValueError si no es un mapeo."""
    bloque = copia.get(BLOQUE_GD, {})
    sub = bloque.get(clave) if isinstance(bloque, Mapping) else None
    if not isinstance(sub, Mapping):
        raise ValueError(f"{BLOQUE_GD}.{clave} debe ser un mapeo; se recibió {sub!r}")
    return sub


def _validar_gdfijo(copia: Mapping, unidad: Unidad) -> None:
    """η de cada función de las celdas de la unidad."""
    etas = _bloque_gd(copia, CLAVE_GD_ETA)
    for func in dict.fromkeys(func for func, _ in unidad.celdas):
        if func not in etas:
            raise ValueError(f"{BLOQUE_GD}.{CLAVE_GD_ETA} no tiene paso para {func!r}")
        _exigir_paso_positivo(etas[func], f"{BLOQUE_GD}.{CLAVE_GD_ETA}.{func}")


def _validar_gdarmijo(copia: Mapping, unidad: Unidad) -> None:
    """η₀, β y c de `gd.armijo`."""
    armijo = _bloque_gd(copia, CLAVE_GD_ARMIJO)
    prefijo = f"{BLOQUE_GD}.{CLAVE_GD_ARMIJO}"
    for clave in (CLAVE_ETA0, CLAVE_BETA, CLAVE_C):
        if clave not in armijo:
            raise ValueError(f"falta la clave {prefijo}.{clave}")
    _exigir_paso_positivo(armijo[CLAVE_ETA0], f"{prefijo}.{CLAVE_ETA0}")
    _exigir_intervalo_armijo(armijo[CLAVE_BETA], f"{prefijo}.{CLAVE_BETA}")
    _exigir_intervalo_armijo(armijo[CLAVE_C], f"{prefijo}.{CLAVE_C}")


# Regla de validez de cada método: recibe la copia de la config con el ensayo puesto.
_VALIDADORES: dict[str, Callable[[Mapping, Unidad], object]] = {
    "gdfijo": _validar_gdfijo,
    "gdarmijo": _validar_gdarmijo,
    "ea": lambda copia, unidad: ParametrosEA.desde_config(copia[NOMBRE_BLOQUE_EA]),
    "pso": lambda copia, unidad: ParametrosPSO.desde_config(copia[NOMBRE_BLOQUE_PSO]),
    "de": lambda copia, unidad: ParametrosDE.desde_config(copia[NOMBRE_BLOQUE_DE]),
}


def _motivo_invalido(unidad: Unidad, cfg: Mapping, ensayo: Mapping) -> str | None:
    """None si el ensayo es válido para su método; si no, el texto del error."""
    copia = aplicar_ensayo(cfg, ensayo, unidad.func)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _VALIDADORES[unidad.metodo](copia, unidad)
    except (TypeError, ValueError) as error:
        return str(error)
    return None


def _sortear_valido(unidad: Unidad, cfg: Mapping, rng) -> dict:
    """Primer ensayo válido de hasta INTENTOS_MAXIMOS sorteos; si no hay, ValueError."""
    motivo = None
    for _ in range(INTENTOS_MAXIMOS):
        candidato = {p.ruta: _sortear_valor(p, rng) for p in unidad.parametros}
        motivo = _motivo_invalido(unidad, cfg, candidato)
        if motivo is None:
            return candidato
    raise ValueError(f"unidad {unidad.nombre!r}: ninguna de {INTENTOS_MAXIMOS} combinaciones "
                     f"sorteadas es válida (último motivo: {motivo}); revisa "
                     f"{CLAVE_HPO}.{CLAVE_ESPACIOS}.{unidad.metodo}")


def sortear_ensayos(unidad: Unidad, cfg: dict, n_ensayos: int) -> list[dict]:
    """Ensayos de `unidad`: el 0 son los valores por defecto; los demás, sorteados (R4).

    Parameters
    ----------
    unidad : Unidad
        Una unidad de `construir_unidades(cfg)` (se supone `cfg` ya validada).
    cfg : dict
        Config resuelta; de ella salen los valores por defecto y `hpo.semilla_busqueda`.
        No se modifica.
    n_ensayos : int
        Número de ensayos (>= 1), contando el 0.

    Returns
    -------
    list[dict]
        `n_ensayos` diccionarios {ruta tal cual en el espacio -> valor}, en el orden del
        espacio, con valores int o float de Python (en el ensayo 0, los de la config).

    Raises
    ------
    TypeError, ValueError
        `n_ensayos` no es un entero >= 1; los valores por defecto no son válidos; ningún
        sorteo válido en `INTENTOS_MAXIMOS` intentos.
    """
    n_ensayos = validar_entero(n_ensayos, "n_ensayos", minimo=MINIMO_POSITIVO)
    cero = {p.ruta: _leer_hoja(cfg, _sustituir_func(p.ruta.split(SEPARADOR_RUTA), unidad.func,
                                                    p.ruta), p.ruta)
            for p in unidad.parametros}
    motivo = _motivo_invalido(unidad, cfg, cero)
    if motivo is not None:
        raise ValueError(f"unidad {unidad.nombre!r}: los valores por defecto de la config no "
                         f"son válidos ({motivo})")
    rng = make_rng(cfg[CLAVE_HPO][CLAVE_SEMILLA_BUSQUEDA], unidad.indice)
    ensayos = [cero]
    while len(ensayos) < n_ensayos:
        ensayos.append(_sortear_valido(unidad, cfg, rng))
    return ensayos


# %% [markdown]
# ## 4. `aplicar_ensayo`
#
# Copia profunda de la config con cada ruta del ensayo puesta a su valor; `{func}` se
# sustituye por `func`. La config original no cambia.

# %%
def aplicar_ensayo(cfg: dict, ensayo: Mapping, func: str | None) -> dict:
    """Copia profunda de `cfg` con los valores de `ensayo` ({ruta -> valor}) puestos.

    Raises
    ------
    ValueError
        Una ruta lleva `{func}` y `func` es None; una ruta no existe en `cfg` o apunta a un
        bloque.
    """
    copia = copy.deepcopy(cfg)
    for ruta, valor in ensayo.items():
        segmentos = _sustituir_func(ruta.split(SEPARADOR_RUTA), func, ruta)
        texto = SEPARADOR_RUTA.join(segmentos)
        _leer_hoja(copia, segmentos, texto)                  # existe y es una hoja
        _nodo_padre(copia, segmentos, texto)[segmentos[-1]] = valor
    return copia


# %% [markdown]
# ## 5, 6 y 7. `clave_celda`, `puntuar_ensayos` y `elegir_ganador` (R6)
#
# **Entrada.** Por ensayo y por celda, un registro compacto con una lista por campo, un
# elemento por semilla: `f_best`, `n_f`, `n_grad`, `eval_equiv` y `evals_hasta_exito_1e-06`
# (None si la semilla no llegó al umbral). La clave de una celda es `"<func>_<dim>d"`.
#
# **Puntaje de un ensayo** $e$ en la celda $c$, con $u = 10^{-6}$ (el umbral más estricto de
# Spec §6.5) y $d_s = f_{\text{best},s} - f^*$ por semilla $s$:
#
# $$m(e, c) = \operatorname{mediana}_s\ \max(d_s,\ u)$$
#
# El recorte va **antes** de la mediana: todo lo que ya está por debajo del umbral más
# estricto cuenta como empate, para no elegir por diferencias de ruido numérico. El rango de
# $e$ en $c$ es la posición de $m(e, c)$ entre todos los ensayos de la unidad (1 = menor; un
# empate recibe el rango promedio). Se usan **rangos** porque Rosenbrock y Rastrigin tienen
# escalas distintas: promediar $m$ dejaría que la función de valores grandes decida sola.
#
# **Claves** (menor es mejor en cada una):
#
# | Paso | Clave |
# |---|---|
# | 1 | puntaje principal $r$: promedio de los rangos sobre las celdas |
# | 2 | menos el promedio de la tasa de éxito a $u$ (fracción de semillas con $d_s \le u$) |
# | 3 | promedio de las evaluaciones hasta el éxito a $u$; una celda sin éxitos vale $+\infty$ |
# | 4 | índice del ensayo |
#
# **Regla.** Sea $r_0$ el puntaje principal del ensayo 0 (valores por defecto) y $r^*$ el
# mínimo de todos los ensayos. Si $r^* \ge r_0$, gana el ensayo 0 sin mirar los pasos 2 a 4.
# Si $r^* < r_0$, entre los ensayos con $r = r^*$ deciden los pasos 2, 3 y 4, en ese orden.
# Por qué: con 5 semillas (`hpo.semillas` de base.yaml) un desempate puede venir de una sola
# corrida (un éxito más), así que solo el puntaje principal puede desplazar al defecto.
#
# Las evaluaciones de una celda son la media sobre sus semillas exitosas (como
# `evals_hasta_exito_medio`, Spec §6.6). **Exactitud:** las claves 1 a 3 se calculan con
# `Fraction` a partir de valores que el JSON conserva sin redondeo, guardados en el puntaje:
#
# | Campo por celda | Valor |
# |---|---|
# | `rango` | rango promedio: múltiplo de 1/2, exacto en float |
# | `semillas_por_celda` | número de semillas (int) |
# | `exitos_1e-06_por_celda` | semillas con $d_s \le u$ (int) |
# | `suma_evals_hasta_exito_1e-06_por_celda` | suma de sus evaluaciones hasta el éxito (int) |
#
# Tasa de la celda = éxitos / semillas; evaluaciones de la celda = suma / éxitos. Así un empate
# exacto (p. ej. tasas 3/5 y 5/5 frente a 4/5 y 4/5) sigue siendo empate. **Supuesto:** las
# evaluaciones hasta el éxito son enteras (con $k = 2n$, `eval_equiv` =
# $n_f + 2n \cdot n_{\text{grad}}$ es entero); `puntuar_ensayos` lanza ValueError si alguna no
# lo es. Los campos `rango_medio`, `tasa_exito_1e-06`, `evals_hasta_exito_1e-06` y los
# `..._por_celda` que se muestran son el float de esas mismas fracciones. En el puntaje,
# $+\infty$ se guarda como None (Spec §5.4).

# %%
def clave_celda(func: str, dim: int) -> str:
    """Clave de texto de una celda: `clave_celda("rastrigin", 2) == "rastrigin_2d"`."""
    return f"{func}{SEPARADOR_UNIDAD}{dim}{SUFIJO_DIMENSION}"


def _mediana(valores: Sequence[float]) -> float:
    """Mediana; con un número par de valores, la media exacta de los dos centrales."""
    ordenados = sorted(valores)
    mitad = len(ordenados) // 2
    if len(ordenados) % 2 == 1:
        return ordenados[mitad]
    return float((Fraction(ordenados[mitad - 1]) + Fraction(ordenados[mitad])) / 2)


def _evaluaciones_enteras(valor, nombre: str) -> int:
    """Evaluaciones hasta el éxito como int; ValueError si no son un real finito entero."""
    valor = _validar_real_finito(valor, nombre)
    if not float(valor).is_integer():
        raise ValueError(f"{nombre} = {valor!r} no es entero: la clave de orden exacta supone "
                         "evaluaciones enteras (eval_equiv con k = 2n)")
    return int(valor)


def _resumir_celda(registro, f_star, nombre: str) -> tuple[float, int, int, int]:
    """(m, semillas, éxitos, suma de evaluaciones de los éxitos) de una celda."""
    if not isinstance(registro, Mapping):
        raise TypeError(f"{nombre} debe ser un mapeo campo -> lista; se recibió "
                        f"{type(registro).__name__}")
    for campo in CAMPOS_REGISTRO:
        if campo not in registro:
            raise ValueError(f"{nombre}: falta el campo '{campo}'")
        if not isinstance(registro[campo], (list, tuple)):
            raise TypeError(f"{nombre}.{campo} debe ser una lista (una entrada por semilla)")
    longitudes = {campo: len(registro[campo]) for campo in CAMPOS_REGISTRO}
    if len(set(longitudes.values())) != 1 or longitudes[CAMPO_F_BEST] == 0:
        raise ValueError(f"{nombre}: las listas deben tener la misma longitud (>= 1); "
                         f"longitudes: {longitudes}")
    f_star = _validar_real_finito(f_star, f"f* de {nombre}")
    diferencias = [_validar_real_finito(f, f"{nombre}.{CAMPO_F_BEST}[{s}]") - f_star
                   for s, f in enumerate(registro[CAMPO_F_BEST])]
    mediana = float(_mediana([max(d, UMBRAL_HPO) for d in diferencias]))
    exitos = 0
    suma = 0
    for s, (diferencia, valor) in enumerate(zip(diferencias, registro[CAMPO_EVALS_EXITO])):
        exito = diferencia <= UMBRAL_HPO
        if exito != (valor is not None):
            raise ValueError(f"{nombre}.{CAMPO_EVALS_EXITO}[{s}] = {valor!r} no concuerda con "
                             f"f_best − f* = {diferencia!r} (None si y solo si no hay éxito)")
        if exito:
            exitos += 1
            suma += _evaluaciones_enteras(valor, f"{nombre}.{CAMPO_EVALS_EXITO}[{s}]")
    return mediana, len(diferencias), exitos, suma


def _rango_promedio(valor: float, todos: Sequence[float]) -> Fraction:
    """Rango de `valor` en `todos` (1 = menor); un empate recibe el promedio de sus rangos."""
    menores = sum(otro < valor for otro in todos)
    iguales = sum(otro == valor for otro in todos)          # incluye al propio valor
    return Fraction(2 * menores + iguales + 1, 2)


def _float_o_none(valor: Fraction | None) -> float | None:
    """Fraction como float de Python; None se conserva."""
    return None if valor is None else float(valor)


def _por_celda_exacto(puntaje: Mapping) -> dict:
    """{celda -> (tasa, evaluaciones medias o None)} exactas, desde los conteos guardados."""
    semillas = puntaje[PUNTAJE_SEMILLAS_POR_CELDA]
    exitos = puntaje[PUNTAJE_EXITOS_POR_CELDA]
    sumas = puntaje[PUNTAJE_SUMA_EVALS_POR_CELDA]
    return {celda: (Fraction(exitos[celda], semillas[celda]),
                    Fraction(sumas[celda], exitos[celda]) if exitos[celda] else None)
            for celda in semillas}


def _claves_exactas(puntaje: Mapping) -> tuple:
    """(rango medio, tasa media, evaluaciones medias o None = +inf), exactos (R6)."""
    rangos = [Fraction(rango) for rango in puntaje[PUNTAJE_RANGO].values()]
    por_celda = list(_por_celda_exacto(puntaje).values())
    rango = sum(rangos, Fraction(0)) / len(rangos)
    tasa = sum((tasa for tasa, _ in por_celda), Fraction(0)) / len(por_celda)
    evals = [media for _, media in por_celda]
    media = (None if any(valor is None for valor in evals)
             else sum(evals, Fraction(0)) / len(evals))
    return rango, tasa, media


def puntuar_ensayos(registros: Sequence[Mapping],
                    f_star_por_celda: Mapping[str, float]) -> list[dict]:
    """Puntaje de cada ensayo de una unidad (R6; tablas de arriba).

    Parameters
    ----------
    registros : lista con un elemento por ensayo, en orden de índice
        Cada elemento es {clave_celda -> registro compacto}; todos con las mismas celdas.
    f_star_por_celda : {clave_celda -> f*}

    Returns
    -------
    list[dict]
        Un puntaje por ensayo con `indice`, `rango_medio`, `tasa_exito_1e-06`,
        `evals_hasta_exito_1e-06` (None si alguna celda no tiene éxitos),
        `mediana_recortada` y `rango` ({celda -> valor}), la tasa y las evaluaciones por
        celda (`..._por_celda`) y los conteos exactos por celda (semillas, éxitos y suma de
        evaluaciones). Solo int, float y None de Python, sin NaN ni infinitos.

    Raises
    ------
    TypeError, ValueError
        Lista vacía; ensayos con celdas distintas; celda sin f*; registro sin un campo, con
        listas de distinta longitud, con valores no finitos, con evaluaciones que no
        concuerdan con el éxito o que no son enteras.
    """
    if not isinstance(registros, Sequence) or len(registros) == 0:
        raise ValueError("puntuar_ensayos necesita una lista no vacía de ensayos")
    celdas = list(registros[0])
    for indice, registro in enumerate(registros):
        if not isinstance(registro, Mapping) or set(registro) != set(celdas):
            raise ValueError(f"el ensayo {indice} no tiene las mismas celdas que el ensayo 0 "
                             f"({', '.join(celdas)})")
    for celda in celdas:
        if celda not in f_star_por_celda:
            raise ValueError(f"falta f* de la celda {celda!r}")

    resumenes = [{celda: _resumir_celda(registro[celda], f_star_por_celda[celda],
                                        f"ensayo {indice}, celda {celda}")
                  for celda in celdas} for indice, registro in enumerate(registros)]
    rangos = [{} for _ in registros]
    for celda in celdas:
        medianas = [resumen[celda][0] for resumen in resumenes]
        for indice, mediana in enumerate(medianas):
            rangos[indice][celda] = _rango_promedio(mediana, medianas)

    puntajes = []
    for indice, resumen in enumerate(resumenes):
        exactos = {
            PUNTAJE_RANGO: {celda: float(rangos[indice][celda]) for celda in celdas},
            PUNTAJE_SEMILLAS_POR_CELDA: {celda: resumen[celda][1] for celda in celdas},
            PUNTAJE_EXITOS_POR_CELDA: {celda: resumen[celda][2] for celda in celdas},
            PUNTAJE_SUMA_EVALS_POR_CELDA: {celda: resumen[celda][3] for celda in celdas},
        }
        # Lo que se muestra sale de la misma cuenta exacta que usa elegir_ganador.
        rango, tasa, media = _claves_exactas(exactos)
        por_celda = _por_celda_exacto(exactos)
        puntajes.append({
            PUNTAJE_INDICE: indice,
            PUNTAJE_RANGO_MEDIO: float(rango),
            PUNTAJE_TASA: float(tasa),
            PUNTAJE_EVALS: _float_o_none(media),
            PUNTAJE_MEDIANA: {celda: resumen[celda][0] for celda in celdas},
            PUNTAJE_RANGO: exactos[PUNTAJE_RANGO],
            PUNTAJE_TASA_POR_CELDA: {celda: float(por_celda[celda][0]) for celda in celdas},
            PUNTAJE_EVALS_POR_CELDA: {celda: _float_o_none(por_celda[celda][1])
                                      for celda in celdas},
            PUNTAJE_SEMILLAS_POR_CELDA: exactos[PUNTAJE_SEMILLAS_POR_CELDA],
            PUNTAJE_EXITOS_POR_CELDA: exactos[PUNTAJE_EXITOS_POR_CELDA],
            PUNTAJE_SUMA_EVALS_POR_CELDA: exactos[PUNTAJE_SUMA_EVALS_POR_CELDA],
        })
    return puntajes


def _clave_de_orden(puntaje: Mapping, indice: int) -> tuple:
    """Claves 1 a 4 de R6 (menor = mejor), con los valores exactos; ver elegir_ganador."""
    rango, tasa, media = _claves_exactas(puntaje)
    # (0, media) si todas las celdas tienen éxitos; (1, 0) representa +inf.
    clave_evals = (1, Fraction(0)) if media is None else (0, media)
    return rango, -tasa, clave_evals, indice


def elegir_ganador(puntajes: Sequence[Mapping]) -> int:
    """Índice del ensayo ganador (R6).

    Sea r0 el rango medio del ensayo 0 y r* el mínimo de todos. Si r* >= r0 gana el 0, sin
    mirar los desempates. Si r* < r0, entre los ensayos con rango medio r* gana el de mayor
    tasa, luego el de menos evaluaciones y luego el de menor índice. `puntajes` es la salida
    de `puntuar_ensayos` (o la releída de un JSON), en orden de índice; las claves usan sus
    conteos enteros, no los float que se muestran.
    """
    if len(puntajes) == 0:
        raise ValueError("elegir_ganador necesita al menos un puntaje")
    claves = [_clave_de_orden(puntaje, indice) for indice, puntaje in enumerate(puntajes)]
    rango_defecto = claves[0][0]
    rango_minimo = min(clave[0] for clave in claves)   # incluye al 0: r* <= r0
    if rango_minimo >= rango_defecto:                    # o sea, r* == r0
        return 0
    # Solo compiten los que tienen el mejor rango medio; los desempates deciden entre ellos.
    empatados = [indice for indice, clave in enumerate(claves) if clave[0] == rango_minimo]
    return min(empatados, key=claves.__getitem__)


# %% [markdown]
# ## 8. `config_afinada`
#
# Config que hereda de la base y lleva solo los hiperparámetros cuyo valor ganador es
# distinto del de `cfg`, anidados por bloque (con `{func}` sustituido):
#
# ```yaml
# hereda: base.yaml
# salida: <hpo.salida_afinada>
# tablas: <hpo.tablas_afinada>
# gd: {eta: {rastrigin: 0.0031}}
# pso: {N: 40, w: 0.6}
# ```
#
# Los bloques aparecen en el orden de las unidades. Un ganador igual al defecto no escribe
# nada de su método.

# %%
def _poner_anidado(destino: dict, segmentos: Sequence[str], valor) -> None:
    """Pone `valor` en `destino` siguiendo `segmentos`; crea los mapeos que falten."""
    nodo = destino
    for segmento in segmentos[:-1]:
        nodo = nodo.setdefault(segmento, {})
    nodo[segmentos[-1]] = valor


def config_afinada(cfg: dict, ganadores: Sequence[tuple],
                   hereda: str = HEREDA_POR_DEFECTO) -> dict:
    """Config afinada (tabla de arriba); no modifica `cfg`.

    Parameters
    ----------
    cfg : dict
        Config resuelta con la que se corrió la HPO (de ella salen los valores por defecto y
        `hpo.salida_afinada` / `hpo.tablas_afinada`).
    ganadores : lista de (Unidad, ensayo ganador)
        El ensayo es un {ruta -> valor} como los de `sortear_ensayos`.
    hereda : str
        Valor de la clave `hereda` (ruta de la base relativa a la config afinada).

    Raises
    ------
    ValueError
        Al ensayo le falta una ruta de su unidad; una ruta no existe en `cfg`.
    """
    hpo = cfg[CLAVE_HPO]
    afinada = {CLAVE_HEREDA: hereda, CLAVE_SALIDA: hpo[CLAVE_SALIDA_AFINADA],
               CLAVE_TABLAS: hpo[CLAVE_TABLAS_AFINADA]}
    for unidad, ensayo in ganadores:
        for parametro in unidad.parametros:
            if parametro.ruta not in ensayo:
                raise ValueError(f"el ensayo ganador de {unidad.nombre!r} no trae la ruta "
                                 f"{parametro.ruta!r}")
            segmentos = _sustituir_func(parametro.ruta.split(SEPARADOR_RUTA), unidad.func,
                                        parametro.ruta)
            valor = ensayo[parametro.ruta]
            if valor != _leer_hoja(cfg, segmentos, SEPARADOR_RUTA.join(segmentos)):
                _poner_anidado(afinada, segmentos, valor)
    return afinada
