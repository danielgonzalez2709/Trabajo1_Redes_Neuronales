# %% [markdown]
# # Optimización de hiperparámetros de la Parte 1: orquestación (T1.10-B; Spec §6.9)
#
# Aplica las reglas R1–R8 de Spec §6.9 que necesitan correr o escribir; usa también §4.1
# (comandos y config), §5.4 (archivos) y §6.2 (presupuesto y $k$).
#
# **Ruta de lectura:**
# 1. `ejecutar_hpo` (sección 5): los seis pasos en orden.
# 2. `validar_ejecucion` (sección 3): qué se rechaza antes de crear nada.
# 3. `_correr_tarea_hpo` y `_datos_de_unidad` (auxiliares): una tarea y una unidad.
# 4. `hpo.py`: sorteo, puntaje y ganador (piezas puras que se llaman aquí).
# 5. `comparar_resumenes` (sección 4): la tabla final por defecto contra afinado.
#
# **Propósito.** Correr la búsqueda de hiperparámetros (HPO) que describe el bloque `hpo:` de
# una config de la Parte 1, guardar los ensayos y la selección, escribir la config afinada,
# repetir el experimento con ella y compararlo con el experimento por defecto. Es el manejador
# de `python run.py hpo`. Las piezas puras (unidades, sorteo, puntaje, ganador, config
# afinada) están en `hpo.py`; una corrida la ejecuta `corrida.py` y el experimento completo,
# `experiment.py`.
#
# **Mapa del módulo:**
#
# | # | Nombre | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `hereda_relativo` | valor de `hereda` de la config afinada | `str` |
# | 2 | `es_demo` | si `salida` está dentro de una carpeta `*_demo` | `bool` |
# | 3 | `validar_ejecucion` | revisa todo lo que puede fallar antes de correr | `None` |
# | 4 | `comparar_resumenes` | filas "por defecto contra afinado" | `list[dict]` |
# | 5 | `ejecutar_hpo` | ensayos, selección, config afinada, experimento final, tabla | `str` |
# | 6 | `manejador_hpo` | manejador del subcomando `hpo` de `run.py` | `int` |
#
# `comando_hpo` (auxiliar pública) arma el comando que se escribe en la cabecera de la config
# afinada: `--config` y los `--set` salvo los de `workers` y `hpo.reanudar`.
#
# **Archivos que escribe** (claves de la config):
#
# | Ruta | Contenido |
# |---|---|
# | `<hpo.salida>/ensayos_<unidad>.json` | `meta` y ensayos con registros compactos y puntajes |
# | `<hpo.salida>/seleccion.json` | por unidad: ganador, defecto, elegido, corridas de ajuste |
# | `<hpo.config_salida>` | config afinada: hereda de la de `--config` y trae lo que cambió |
# | `<hpo.salida_afinada>/…`, `<hpo.tablas_afinada>/tabla_*.csv` | experimento final |
# | `<hpo.tablas_afinada>/comparacion.csv` | una fila por (func, dim, method) |
# | `<salida>/…`, `<tablas>/…` | solo en el demo, si falta su resumen por defecto |
#
# **Conteo y azar.** Cada corrida de ajuste pasa por `ejecutar_corrida` con $k = 2n$ y el
# presupuesto del experimento (Spec §6.2); su generador es `make_rng(hpo.base_seed, run_id)`
# (Spec §4.1). Aquí no se evalúa ninguna función.

# %%
"""Optimización de hiperparámetros de la Parte 1: ensayos, selección, config afinada y CLI."""

from __future__ import annotations

import copy
import csv
import io
import os
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path

import yaml

from src.common.config import (
    CLAVE_HEREDA,
    SEPARADOR_CLAVE,
    SEPARADOR_VALOR,
    apply_overrides,
    cargar_yaml,
    load_config,
)
from src.common.results import load_json, save_json, to_jsonable
from src.common.seeds import seeds_for_runs
from src.part1.corrida import FACTOR_K_PRINCIPAL, ejecutar_corrida
from src.part1.experiment import (
    CLAVE_BASE_SEED,
    CLAVE_DIM,
    CLAVE_FUNC,
    CLAVE_METODOS,
    CLAVE_PRESUPUESTO,
    CLAVE_RUNS,
    CLAVE_SALIDA,
    CLAVE_TABLAS,
    CLAVE_WORKERS,
    CODIFICACION,
    CODIGO_CORRECTO,
    CODIGO_ERROR_DE_USO,
    K_REGLA,
    NOMBRE_SUMMARY,
    SALTO_DE_LINEA,
    Informar,
    ejecutar_experimento,
    mapeador,
    validar_config,
)
from src.part1.functions import get_function
from src.part1.hpo import (
    CAMPO_EVAL_EQUIV,
    CAMPO_EVALS_EXITO,
    CAMPO_F_BEST,
    CAMPO_N_F,
    CAMPO_N_GRAD,
    CAMPOS_REGISTRO,
    CLAVE_CONFIG_SALIDA,
    CLAVE_ENSAYOS,
    CLAVE_ESPACIOS,
    CLAVE_HPO,
    CLAVE_HPO_BASE_SEED,
    CLAVE_HPO_SALIDA,
    CLAVE_REANUDAR,
    CLAVE_SALIDA_AFINADA,
    CLAVE_SEMILLA_BUSQUEDA,
    CLAVE_SEMILLAS,
    CLAVE_TABLAS_AFINADA,
    MARCADOR_FUNC,
    SEPARADOR_RUTA,
    SUFIJO_UMBRAL,
    UMBRAL_HPO,
    Unidad,
    aplicar_ensayo,
    bloque_del_metodo,
    clave_celda,
    config_afinada,
    construir_unidades,
    elegir_ganador,
    puntuar_ensayos,
    sortear_ensayos,
    validar_hpo,
)
from src.part1.metricas import (
    FORMATO_CONTEO,
    FORMATO_F,
    FORMATO_PORCENTAJE,
    INDEFINIDO,
    SEPARADOR_DE_COLUMNAS,
    UMBRAL_PRINCIPAL,
    clave_umbral,
    es_exito,
    evals_hasta_exito,
)

# %% [markdown]
# ## Constantes del módulo
#
# Nombres de archivos y de campos de los JSON, textos de la salida y columnas de la
# comparación. Los valores del protocolo (ensayos, semillas, espacios, carpetas) no están
# aquí: viven en el bloque `hpo:` de `configs/part1/base.yaml`.

# %%
RUTA_CONFIG_POR_DEFECTO = "configs/part1/base.yaml"
COMANDO_HPO = "python run.py hpo --config {ruta}"
COMANDO_PART1 = "python run.py part1 --config {ruta}"

PREFIJO_ENSAYOS = "ensayos_"             # <hpo.salida>/ensayos_<unidad>.json
EXTENSION_JSON = ".json"
NOMBRE_SELECCION = "seleccion.json"
NOMBRE_COMPARACION = "comparacion.csv"
SUFIJO_DEMO = "_demo"                    # carpeta de un demo: results/data/part1_hpo_demo

CAMPO_META = "meta"
CAMPO_ENSAYOS = "ensayos"                # lista de ensayos de ensayos_<unidad>.json
CAMPO_INDICE = "indice"
CAMPO_PARAMETROS = "parametros"
CAMPO_POR_CELDA = "por_celda"
CAMPO_PUNTAJE = "puntaje"
CAMPO_CONFIGURACIONES = "configuraciones"      # lista de entradas de summary.json

# Claves de --set que no cambian el resultado: no se escriben en la cabecera de la config
# afinada, para que una corrida reanudada o con otro `workers` dé los mismos bytes.
CLAVES_SIN_EFECTO = (CLAVE_WORKERS, f"{CLAVE_HPO}{SEPARADOR_CLAVE}{CLAVE_REANUDAR}")
PREFIJO_AVANCE = "HPO"                  # cada línea de avance de una unidad empieza así
TITULO_COMPARACION = "Comparación: valores por defecto contra valores afinados"
CABECERA_CONFIG_AFINADA = (
    "# Config afinada de la Parte 1 (T1.10), generada por:\n"
    "#   {comando}\n"
    "# No se edita a mano: se regenera con ese mismo comando (omite los --set de workers y\n"
    "# hpo.reanudar, que no cambian el resultado).\n"
    "# Solo trae lo que cambió respecto a la config de la que hereda, más salida y tablas.\n"
    "# El detalle de la selección está en {seleccion}.\n"
)

# Comparación (Spec §6.5 y §6.6): métricas de summary.json por configuración.
SUFIJO_PRINCIPAL = clave_umbral(UMBRAL_PRINCIPAL)          # "1e-04"
SUFIJO_DEFECTO = "_defecto"
SUFIJO_AFINADO = "_afinado"
CLAVES_CONFIGURACION = ("func", "dim", "method")
# (nombre de la columna sin sufijo, (bloque, campo) en una entrada de summary.json)
METRICAS_COMPARADAS = (
    ("f_final_mediana", ("f_final", "mediana")),
    ("f_final_media", ("f_final", "media")),
    (f"tasa_exito_{SUFIJO_PRINCIPAL}", ("tasa_exito", SUFIJO_PRINCIPAL)),
    (f"tasa_exito_{SUFIJO_UMBRAL}", ("tasa_exito", SUFIJO_UMBRAL)),
    (f"evals_hasta_exito_{SUFIJO_PRINCIPAL}", ("evals_hasta_exito_medio", SUFIJO_PRINCIPAL)),
)
COLUMNA_CAMBIO = f"cambio_tasa_exito_{SUFIJO_PRINCIPAL}"   # afinado − defecto
COLUMNAS_COMPARACION = [*CLAVES_CONFIGURACION,
                        *(f"{nombre}{sufijo}" for nombre, _ in METRICAS_COMPARADAS
                          for sufijo in (SUFIJO_DEFECTO, SUFIJO_AFINADO)),
                        COLUMNA_CAMBIO]
# Claves de `meta` que deben coincidir entre los dos summary.json para comparar.
CLAVES_META_COMPARABLES = ("semillas", CLAVE_PRESUPUESTO, CLAVE_FUNC, CLAVE_DIM, CLAVE_METODOS)
FORMATO_CAMBIO = "+.1f"                  # cambio de la tasa, en puntos porcentuales con signo
CIEN = 100                               # fracción -> porcentaje


# %% [markdown]
# ## 1 y 2. `hereda_relativo` y `es_demo`
#
# **`hereda`.** La config afinada se carga como
# `apply_overrides(load_config(hpo.config_salida), overrides)`. Para que herede de la config
# que recibió el comando, su clave `hereda` es la ruta de esa config **relativa a la carpeta de
# `hpo.config_salida`** (así la lee `load_config`), con separadores `/`:
#
# | `--config` | `hpo.config_salida` | `hereda` |
# |---|---|---|
# | `configs/part1/base.yaml` | `configs/part1/tuned.yaml` | `base.yaml` |
# | `configs/part1/hpo_demo.yaml` | `<d>/tuned.yaml` | `../../../configs/part1/hpo_demo.yaml` |
#
# con `<d>` = `results/data/part1_hpo_demo`.
#
# **Demo.** Una config es de demo si alguna carpeta que contiene a `salida` termina en `_demo`
# (p. ej. `results/data/part1_hpo_demo/experimento`). Solo el demo genera su propio resumen
# por defecto cuando falta.

# %%
def hereda_relativo(ruta_config: str | os.PathLike, config_salida: str | os.PathLike) -> str:
    """Ruta de `ruta_config` relativa a la carpeta de `config_salida`, con separadores `/`.

    Las dos rutas se resuelven contra el directorio de trabajo; no hace falta que existan.

    Raises
    ------
    ValueError
        No hay ruta relativa entre las dos (en Windows: unidades de disco distintas).
    """
    origen = Path(ruta_config).resolve()
    carpeta = Path(config_salida).resolve().parent
    try:
        relativa = os.path.relpath(origen, carpeta)
    except ValueError as error:
        raise ValueError(f"no hay ruta relativa de {carpeta} a {origen} para la clave "
                         f"'{CLAVE_HEREDA}' de la config afinada: {error}") from error
    return Path(relativa).as_posix()


def es_demo(cfg: Mapping) -> bool:
    """True si alguna carpeta que contiene a `cfg["salida"]` termina en `_demo`."""
    return any(padre.name.endswith(SUFIJO_DEMO) for padre in Path(cfg[CLAVE_SALIDA]).parents)


# %% [markdown]
# ## 3. `validar_ejecucion`
#
# Todo lo que puede fallar antes de correr, en este orden; no crea carpetas ni archivos:
#
# | Paso | Regla |
# |---|---|
# | 1 | `validar_config(cfg)` y `validar_hpo(cfg)` |
# | 2 | `overrides` es una lista (o tupla) de textos |
# | 3 | `ruta_config` existe y `apply_overrides(load_config(ruta_config), overrides) == cfg` |
# | 4 | `hpo.config_salida` no es `ruta_config` ni un archivo de su cadena de `hereda` |
# | 5 | hay ruta relativa para `hereda` (`hereda_relativo`) |
# | 6 | ningún `--set` toca `salida`, `tablas` ni una ruta afinada (con `{func}` sustituido) |
# | 7 | existe `<salida>/summary.json` (salvo en el demo); su `meta` coincide con `cfg` |
#
# En el paso 7, "coincide" se mira en `CLAVES_META_COMPARABLES` (semillas, presupuesto, func,
# dim, methods), las mismas que exige `comparar_resumenes`.
#
# El paso 6 protege R8: los `--set` se vuelven a aplicar sobre la config afinada, así que uno
# sobre una ruta afinada anularía el valor elegido y uno sobre `salida` o `tablas` mandaría el
# experimento final a la carpeta de los valores por defecto. El paso 4 evita sobrescribir la
# config de origen o una de sus bases.

# %%
def _validar_overrides(overrides) -> list[str]:
    """Copia de `overrides` como lista; TypeError si no es una lista o tupla de textos."""
    if not isinstance(overrides, (list, tuple)) or not all(
            isinstance(override, str) for override in overrides):
        raise TypeError(f"overrides debe ser una lista de textos 'clave=valor' (los --set); se "
                        f"recibió {overrides!r}")
    return list(overrides)


def _validar_ruta_config(ruta_config) -> Path:
    """`ruta_config` como Path; TypeError si no es una ruta, FileNotFoundError si no existe."""
    if not isinstance(ruta_config, (str, os.PathLike)):
        raise TypeError(f"la ruta de --config debe ser un texto; se recibió {ruta_config!r}")
    ruta = Path(ruta_config)
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe el archivo de --config: {ruta.as_posix()}")
    return ruta


def _cadena_de_herencia(ruta: Path) -> list[Path]:
    """Rutas resueltas de `ruta` y de cada archivo del que hereda, en orden.

    Se llama después de `load_config(ruta)`, que ya comprobó que los archivos existen y que
    la cadena no tiene ciclos; el bucle se detiene igual si una ruta se repite.
    """
    cadena: list[Path] = []
    actual = ruta
    while actual.resolve() not in cadena:
        cadena.append(actual.resolve())
        datos = cargar_yaml(actual.read_text(encoding=CODIFICACION))
        base = datos.get(CLAVE_HEREDA) if isinstance(datos, Mapping) else None
        if base is None:
            break
        actual = actual.parent / base
    return cadena


def _validar_config_salida(ruta: Path, config_salida: str) -> None:
    """Paso 4: la config afinada no sobrescribe `--config` ni un archivo del que hereda."""
    nombre = f"{CLAVE_HPO}.{CLAVE_CONFIG_SALIDA}"
    cadena = _cadena_de_herencia(ruta)
    destino = Path(config_salida).resolve()
    if destino == cadena[0]:
        raise ValueError(f"{nombre} ({config_salida!r}) es el mismo archivo que --config "
                         f"({ruta.as_posix()}): la HPO lo sobrescribiría")
    if destino in cadena:
        raise ValueError(f"{nombre} ({config_salida!r}) es un archivo del que hereda --config "
                         f"(clave '{CLAVE_HEREDA}'): la HPO lo sobrescribiría")


def _clave_de_override(override: str) -> str:
    """Clave de un `--set` ya validado por `apply_overrides`: "pso.w=0.9" -> "pso.w"."""
    texto = override.split(SEPARADOR_VALOR, 1)[0]
    return SEPARADOR_CLAVE.join(parte.strip() for parte in texto.split(SEPARADOR_CLAVE))


def _rutas_afinadas(unidades: Sequence[Unidad]) -> list[str]:
    """Rutas concretas (con `{func}` sustituido) de los hiperparámetros de `unidades`."""
    rutas = []
    for unidad in unidades:
        for parametro in unidad.parametros:
            segmentos = [unidad.func if segmento == MARCADOR_FUNC else segmento
                         for segmento in parametro.ruta.split(SEPARADOR_RUTA)]
            rutas.append(SEPARADOR_RUTA.join(segmentos))
    return rutas


def _rechazar_overrides_protegidos(cfg: Mapping, overrides: Sequence[str]) -> None:
    """Paso 6: ValueError si un `--set` toca `salida`, `tablas` o una ruta afinada."""
    motivos = {CLAVE_SALIDA: "mandaría el experimento final a la carpeta por defecto",
               CLAVE_TABLAS: "mandaría las tablas finales a la carpeta por defecto"}
    for ruta in _rutas_afinadas(construir_unidades(cfg)):
        motivos[ruta] = "anularía el valor afinado"
    for override in overrides:
        clave = _clave_de_override(override)
        if clave in motivos:
            raise ValueError(
                f"el --set de '{clave}' no se admite en hpo: se vuelve a aplicar sobre la "
                f"config afinada y {motivos[clave]} (R8); cambia ese valor en el archivo de "
                "--config")


def _meta_de_config(cfg: Mapping) -> dict:
    """Valores de `meta` de summary.json que fija `cfg` y que deben coincidir al comparar."""
    return {"semillas": seeds_for_runs(cfg[CLAVE_BASE_SEED], cfg[CLAVE_RUNS]),
            CLAVE_PRESUPUESTO: cfg[CLAVE_PRESUPUESTO], CLAVE_FUNC: list(cfg[CLAVE_FUNC]),
            CLAVE_DIM: list(cfg[CLAVE_DIM]), CLAVE_METODOS: list(cfg[CLAVE_METODOS])}


def _exigir_metas_iguales(meta_a, meta_b, nombre_a: str, nombre_b: str) -> None:
    """ValueError que nombra la primera clave de CLAVES_META_COMPARABLES que no coincide."""
    for nombre, meta in ((nombre_a, meta_a), (nombre_b, meta_b)):
        if not isinstance(meta, Mapping):
            raise ValueError(f"{nombre} no trae un 'meta' (mapeo)")
    for clave in CLAVES_META_COMPARABLES:
        if meta_a.get(clave) != meta_b.get(clave):
            raise ValueError(f"meta['{clave}'] vale {meta_a.get(clave)!r} en {nombre_a} y "
                             f"{meta_b.get(clave)!r} en {nombre_b}: la comparación no sería "
                             "justa")


def _validar_summary_por_defecto(cfg: Mapping, ruta: Path) -> None:
    """Paso 7: el summary por defecto existe (salvo en el demo) y su meta es la de `cfg`."""
    summary = Path(cfg[CLAVE_SALIDA]) / NOMBRE_SUMMARY
    if not summary.is_file():
        if es_demo(cfg):
            return
        raise FileNotFoundError(
            f"no existe {summary.as_posix()} (resultados con los valores por defecto): corre "
            f"antes `{COMANDO_PART1.format(ruta=ruta.as_posix())}` con los mismos --set")
    datos = load_json(summary)
    meta = datos.get(CAMPO_META) if isinstance(datos, Mapping) else None
    try:
        _exigir_metas_iguales(meta, _meta_de_config(cfg), summary.as_posix(), "la config")
    except ValueError as error:
        if es_demo(cfg):
            raise ValueError(f"{error}; borra {summary.as_posix()} y el demo lo vuelve a "
                             "generar") from error
        raise


def validar_ejecucion(cfg: dict, ruta_config: str | os.PathLike,
                      overrides: Sequence[str]) -> None:
    """Revisa todo lo que puede fallar antes de correr la HPO (tabla de arriba).

    No crea carpetas ni archivos y no modifica `cfg`.

    Raises
    ------
    TypeError
        Los de `validar_config` y `validar_hpo`; `overrides` no es una lista de textos;
        `ruta_config` no es una ruta.
    ValueError
        Los de `validar_config`, `validar_hpo` y `load_config`; la config no coincide con
        `--config` + `--set`; `hpo.config_salida` sobrescribiría `--config` o una de sus
        bases; un `--set` protegido (R8); el summary por defecto tiene otro `meta`.
    FileNotFoundError
        `ruta_config` no existe; falta `<salida>/summary.json` (fuera del demo).
    """
    validar_config(cfg)
    validar_hpo(cfg)
    overrides = _validar_overrides(overrides)
    ruta = _validar_ruta_config(ruta_config)
    if apply_overrides(load_config(ruta), overrides) != cfg:
        raise ValueError(f"la config recibida no coincide con --config + --set "
                         f"({ruta.as_posix()} con {overrides!r})")
    config_salida = cfg[CLAVE_HPO][CLAVE_CONFIG_SALIDA]
    _validar_config_salida(ruta, config_salida)
    hereda_relativo(ruta, config_salida)
    _rechazar_overrides_protegidos(cfg, overrides)
    _validar_summary_por_defecto(cfg, ruta)


# %% [markdown]
# ## Auxiliares de `ejecutar_hpo`
#
# **Tarea elemental** = (unidad, ensayo, función, dimensión): la tupla
# `(metodo, cfg_del_ensayo, func, dim, base_seed_ajuste, n_semillas, presupuesto_por_dim)`.
# `_correr_tarea_hpo` corre sus semillas (`run_id` = 0, …, `n_semillas` − 1) dentro del
# proceso que la ejecuta y devuelve solo el **registro compacto** (una entrada por semilla):
#
# | Campo | Valor |
# |---|---|
# | `f_best`, `n_f`, `n_grad`, `eval_equiv` | los de `result` (Spec §5.1) |
# | `evals_hasta_exito_1e-06` | 1.er `eval_equiv` de `history` con $f - f^* \le 10^{-6}$, o None |
#
# La historia y los frames no salen del proceso. Es una función de nivel de módulo para que
# `ProcessPoolExecutor` la pueda enviar a otro proceso con `spawn` (Windows), y el orden de
# los resultados es el de las tareas (`map`), no el de llegada.
#
# **Meta de una unidad.** Los datos de la config de los que dependen sus ensayos: unidad,
# método, función, índice, celdas, ensayos, semillas, presupuesto, $k$, espacio, bloque del
# método en la config y semilla de búsqueda.
#
# **Reanudar.** Con `hpo.reanudar: true`, un `ensayos_<unidad>.json` se reutiliza sin correr
# nada si su `meta` es igual al actual y sus registros están completos (`ensayos` ensayos,
# las celdas de la unidad y `semillas` entradas por campo). Los registros son la fuente de
# verdad: los puntajes se recalculan con `puntuar_ensayos` y, si difieren de los guardados
# (p. ej. un formato de puntaje anterior), el archivo se reescribe y se informa.

# %%
def _correr_tarea_hpo(tarea: tuple) -> dict:
    """Corre las semillas de una tarea elemental y devuelve su registro compacto."""
    metodo, cfg, func, dim, base_seed, n_semillas, presupuesto_por_dim = tarea
    f_star = get_function(func, dim).f_star
    registro = {campo: [] for campo in CAMPOS_REGISTRO}
    for run_id in range(n_semillas):
        corrida = ejecutar_corrida(func, dim, metodo, base_seed, run_id, cfg,
                                   k=FACTOR_K_PRINCIPAL * dim,
                                   presupuesto_por_dim=presupuesto_por_dim, grabar_frames=False)
        resultado = corrida["result"]
        f_best = float(resultado["f_best"])
        registro[CAMPO_F_BEST].append(f_best)
        registro[CAMPO_N_F].append(int(resultado["n_f"]))
        registro[CAMPO_N_GRAD].append(int(resultado["n_grad"]))
        registro[CAMPO_EVAL_EQUIV].append(float(resultado["eval_equiv"]))
        registro[CAMPO_EVALS_EXITO].append(
            evals_hasta_exito(corrida, f_star, UMBRAL_HPO)
            if es_exito(f_best, f_star, UMBRAL_HPO) else None)
    return registro


def _config_sin_workers(cfg: Mapping) -> dict:
    """Copia profunda de `cfg` sin `workers`, la base de la config de cada tarea.

    `workers` solo decide cuántos procesos se usan; al quitarlo, cada tarea recibe la misma
    config con cualquier número de procesos (como `_config_de_corrida` de `experiment.py`).
    """
    config = copy.deepcopy(dict(cfg))
    del config[CLAVE_WORKERS]
    return config


def _meta_de_unidad(cfg: Mapping, unidad: Unidad) -> dict:
    """`meta` de ensayos_<unidad>.json, solo con tipos de JSON (listas, no tuplas)."""
    hpo = cfg[CLAVE_HPO]
    return to_jsonable({
        "unidad": unidad.nombre,
        "metodo": unidad.metodo,
        "func": unidad.func,
        "indice": unidad.indice,
        "celdas": [[func, dim] for func, dim in unidad.celdas],
        "ensayos": hpo[CLAVE_ENSAYOS],
        "semillas": hpo[CLAVE_SEMILLAS],
        "semillas_de_ajuste": seeds_for_runs(hpo[CLAVE_HPO_BASE_SEED], hpo[CLAVE_SEMILLAS]),
        "presupuesto_por_dim": cfg[CLAVE_PRESUPUESTO],
        "k_regla": K_REGLA,
        "espacio": hpo[CLAVE_ESPACIOS][unidad.metodo],
        "bloque_base": cfg[bloque_del_metodo(unidad.metodo)],
        "semilla_busqueda": hpo[CLAVE_SEMILLA_BUSQUEDA],
    })


def _f_star_por_celda(unidad: Unidad) -> dict[str, float]:
    """{clave_celda -> f*} de las celdas de `unidad`."""
    return {clave_celda(func, dim): get_function(func, dim).f_star
            for func, dim in unidad.celdas}


def _ruta_de_ensayos(cfg: Mapping, unidad: Unidad) -> Path:
    """`<hpo.salida>/ensayos_<unidad>.json`."""
    return Path(cfg[CLAVE_HPO][CLAVE_HPO_SALIDA]) / (
        f"{PREFIJO_ENSAYOS}{unidad.nombre}{EXTENSION_JSON}")


def _meta_coincide(previo, meta: Mapping) -> bool:
    """True si `previo` es un mapeo cuyo `meta` es igual a `meta`."""
    return isinstance(previo, Mapping) and previo.get(CAMPO_META) == meta


def _registros_completos(previo: Mapping, meta: Mapping, unidad: Unidad) -> bool:
    """True si hay `ensayos` ensayos con índices 0, 1, …, `parametros`, las celdas de la
    unidad y `semillas` entradas en cada campo de cada registro.

    Un campo que falta o tiene otro tipo lanza KeyError, TypeError o AttributeError.
    """
    celdas = [clave_celda(func, dim) for func, dim in unidad.celdas]
    ensayos = previo[CAMPO_ENSAYOS]
    return (len(ensayos) == meta["ensayos"]
            and [e[CAMPO_INDICE] for e in ensayos] == list(range(len(ensayos)))
            and all(isinstance(e[CAMPO_PARAMETROS], Mapping) for e in ensayos)
            and all(list(e[CAMPO_POR_CELDA]) == celdas for e in ensayos)
            and all(len(registro[campo]) == meta["semillas"] for e in ensayos
                    for registro in e[CAMPO_POR_CELDA].values() for campo in CAMPOS_REGISTRO))


def _puntajes_desde_registros(previo: Mapping, unidad: Unidad) -> list[dict]:
    """Puntajes que da `puntuar_ensayos` sobre los registros guardados (la fuente de verdad)."""
    return puntuar_ensayos([e[CAMPO_POR_CELDA] for e in previo[CAMPO_ENSAYOS]],
                           _f_star_por_celda(unidad))


def _motivo_para_no_reutilizar(previo, meta: Mapping, unidad: Unidad) -> str | None:
    """None si los registros de `previo` (un ensayos_<unidad>.json leído) se pueden reutilizar;
    si no, el motivo. Los puntajes guardados no cuentan: se recalculan desde los registros."""
    if not _meta_coincide(previo, meta):
        return "su meta no coincide con el de la config actual"
    try:
        completo = _registros_completos(previo, meta, unidad)
    except (KeyError, TypeError, AttributeError):
        return "su contenido está incompleto o mal formado"
    if not completo:
        return "sus registros no concuerdan con su meta (ensayos, celdas o semillas)"
    try:
        _puntajes_desde_registros(previo, unidad)
    except (TypeError, ValueError) as error:
        return f"sus registros no se pueden puntuar ({error})"
    return None


def _ganador(datos: Mapping) -> int:
    """Índice ganador de los ensayos de `datos` (contenido de un ensayos_<unidad>.json)."""
    return elegir_ganador([ensayo[CAMPO_PUNTAJE] for ensayo in datos[CAMPO_ENSAYOS]])


def _guardar_unidad(ruta: Path, meta: Mapping, ensayos: Sequence[Mapping],
                    por_ensayo: Sequence[Mapping], puntajes: Sequence[Mapping]) -> dict:
    """Escribe ensayos_<unidad>.json y devuelve lo releído (mismo camino al reutilizar)."""
    save_json(ruta, {CAMPO_META: meta, CAMPO_ENSAYOS: [
        {CAMPO_INDICE: indice, CAMPO_PARAMETROS: ensayo, CAMPO_POR_CELDA: celdas,
         CAMPO_PUNTAJE: puntaje}
        for indice, (ensayo, celdas, puntaje) in enumerate(zip(ensayos, por_ensayo, puntajes))]})
    return load_json(ruta)


def _correr_unidad(mapear: Callable, cfg: Mapping, config_corrida: Mapping, unidad: Unidad,
                   meta: Mapping, ruta: Path) -> dict:
    """Sortea, corre, puntúa y guarda los ensayos de `unidad`; devuelve lo que quedó en disco."""
    hpo = cfg[CLAVE_HPO]
    ensayos = sortear_ensayos(unidad, cfg, hpo[CLAVE_ENSAYOS])
    # Orden de las tareas: ensayo y, dentro de él, celda.
    tareas = [(unidad.metodo, aplicar_ensayo(config_corrida, ensayo, unidad.func), func, dim,
               hpo[CLAVE_HPO_BASE_SEED], hpo[CLAVE_SEMILLAS], cfg[CLAVE_PRESUPUESTO])
              for ensayo in ensayos for func, dim in unidad.celdas]
    registros: Iterator[dict] = iter(list(mapear(_correr_tarea_hpo, tareas)))
    por_ensayo = [{clave_celda(func, dim): next(registros) for func, dim in unidad.celdas}
                  for _ in ensayos]
    return _guardar_unidad(ruta, meta, ensayos, por_ensayo,
                           puntuar_ensayos(por_ensayo, _f_star_por_celda(unidad)))


def _reutilizar_unidad(previo: Mapping, meta: Mapping, unidad: Unidad, ruta: Path,
                       encabezado: str, informar: Informar) -> dict:
    """Datos de una unidad reutilizada; si sus puntajes guardados no son los recalculados
    (p. ej. un formato de puntaje anterior), reescribe el archivo sin correr nada."""
    puntajes = _puntajes_desde_registros(previo, unidad)
    ensayos = previo[CAMPO_ENSAYOS]
    if puntajes != [ensayo[CAMPO_PUNTAJE] for ensayo in ensayos]:
        previo = _guardar_unidad(ruta, meta, [e[CAMPO_PARAMETROS] for e in ensayos],
                                 [e[CAMPO_POR_CELDA] for e in ensayos], puntajes)
        informar(f"nota: {ruta.as_posix()} tenía puntajes distintos de los recalculados desde "
                 f"sus registros; se reescribe sin correr nada de la unidad {unidad.nombre}")
    informar(f"{encabezado}: se reutiliza {ruta.as_posix()} (meta igual); ganador: ensayo "
             f"{_ganador(previo)}")
    return previo


def _datos_de_unidad(mapear: Callable, cfg: Mapping, config_corrida: Mapping, unidad: Unidad,
                     total: int, informar: Informar) -> dict:
    """Ensayos de `unidad`: reutilizados (si `hpo.reanudar` lo permite) o corridos."""
    hpo = cfg[CLAVE_HPO]
    meta = _meta_de_unidad(cfg, unidad)
    ruta = _ruta_de_ensayos(cfg, unidad)
    encabezado = f"{PREFIJO_AVANCE} [{unidad.indice + 1}/{total}] {unidad.nombre}"
    if hpo[CLAVE_REANUDAR] and ruta.is_file():
        try:
            previo = load_json(ruta)
        except (OSError, ValueError) as error:
            previo, motivo = None, f"no se pudo leer ({error})"
        else:
            motivo = _motivo_para_no_reutilizar(previo, meta, unidad)
        if motivo is None:
            return _reutilizar_unidad(previo, meta, unidad, ruta, encabezado, informar)
        informar(f"aviso: {ruta.as_posix()} no se reutiliza: {motivo}; la unidad "
                 f"{unidad.nombre} se vuelve a correr")
    datos = _correr_unidad(mapear, cfg, config_corrida, unidad, meta, ruta)
    informar(f"{encabezado}: {len(datos[CAMPO_ENSAYOS])} ensayo(s) × {len(unidad.celdas)} "
             f"celda(s) × {hpo[CLAVE_SEMILLAS]} semilla(s); ganador: ensayo {_ganador(datos)}")
    return datos


def _corridas_contadas(datos: Mapping) -> int:
    """Corridas de ajuste guardadas: entradas de `f_best` en todos los ensayos y celdas."""
    return sum(len(registro[CAMPO_F_BEST]) for ensayo in datos[CAMPO_ENSAYOS]
               for registro in ensayo[CAMPO_POR_CELDA].values())


def _seleccion(cfg: Mapping, unidades: Sequence[Unidad], datos_por_unidad: Sequence[Mapping]
               ) -> dict:
    """Contenido de seleccion.json: datos comunes y una entrada por unidad."""
    hpo = cfg[CLAVE_HPO]
    entradas = []
    for unidad, datos in zip(unidades, datos_por_unidad):
        ensayos = datos[CAMPO_ENSAYOS]
        ganador = _ganador(datos)
        entradas.append({
            "unidad": unidad.nombre,
            "metodo": unidad.metodo,
            "func": unidad.func,
            "celdas": [[func, dim] for func, dim in unidad.celdas],
            "ensayos": len(ensayos),
            "ganador": ganador,
            "defecto": ensayos[0][CAMPO_PARAMETROS],
            "elegido": ensayos[ganador][CAMPO_PARAMETROS],
            "puntaje_defecto": ensayos[0][CAMPO_PUNTAJE],
            "puntaje_ganador": ensayos[ganador][CAMPO_PUNTAJE],
            "corridas_de_ajuste": _corridas_contadas(datos),
        })
    return {
        "meta": {
            "ensayos": hpo[CLAVE_ENSAYOS],
            "semillas": hpo[CLAVE_SEMILLAS],
            "semillas_de_ajuste": seeds_for_runs(hpo[CLAVE_HPO_BASE_SEED], hpo[CLAVE_SEMILLAS]),
            "presupuesto_por_dim": cfg[CLAVE_PRESUPUESTO],
            "semilla_busqueda": hpo[CLAVE_SEMILLA_BUSQUEDA],
            "corridas_de_ajuste_total": sum(e["corridas_de_ajuste"] for e in entradas),
        },
        "unidades": entradas,
    }


def _hojas(datos: Mapping, prefijo: tuple = ()) -> Iterator[tuple[tuple, object]]:
    """(ruta como tupla de claves, valor) de cada valor de `datos` que no es un mapeo."""
    for clave, valor in datos.items():
        if isinstance(valor, Mapping):
            yield from _hojas(valor, (*prefijo, clave))
        else:
            yield (*prefijo, clave), valor


def comando_hpo(ruta_config: str | os.PathLike, overrides: Sequence[str]) -> str:
    """Comando `run.py hpo` con `--config` y los `--set` cuya clave no está en
    `CLAVES_SIN_EFECTO` (`workers` y `hpo.reanudar`).

    Un `--set` con espacios va entre comillas dobles. Sin fechas: dos ejecuciones iguales dan
    el mismo texto con cualquier `workers` y con o sin `hpo.reanudar`.
    """
    partes = [COMANDO_HPO.format(ruta=Path(ruta_config).as_posix())]
    for override in overrides:
        if _clave_de_override(override) in CLAVES_SIN_EFECTO:
            continue
        partes.append(f'--set "{override}"' if " " in override else f"--set {override}")
    return " ".join(partes)


def _escribir_config_afinada(cfg: Mapping, ganadores: Sequence[tuple],
                             ruta_config: str | os.PathLike, overrides: Sequence[str]) -> Path:
    """Escribe `hpo.config_salida` (cabecera + YAML) y comprueba la relectura.

    Raises
    ------
    RuntimeError
        El texto o el archivo releído no dan los valores de `config_afinada`.
    """
    hpo = cfg[CLAVE_HPO]
    destino = Path(hpo[CLAVE_CONFIG_SALIDA])
    afinada = config_afinada(cfg, ganadores, hereda=hereda_relativo(ruta_config, destino))
    cabecera = CABECERA_CONFIG_AFINADA.format(
        comando=comando_hpo(ruta_config, overrides),
        seleccion=(Path(hpo[CLAVE_HPO_SALIDA]) / NOMBRE_SELECCION).as_posix())
    texto = cabecera + yaml.safe_dump(afinada, sort_keys=False, allow_unicode=True)
    if cargar_yaml(texto) != afinada:
        raise RuntimeError(f"el YAML de {destino.as_posix()} no se relee igual que la config "
                           "afinada")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto, encoding=CODIFICACION, newline=SALTO_DE_LINEA)

    releida = load_config(destino)
    for ruta, valor in _hojas(afinada):
        if ruta == (CLAVE_HEREDA,):
            continue
        nodo = releida
        for clave in ruta:
            nodo = nodo.get(clave) if isinstance(nodo, Mapping) else None
        if nodo != valor:
            raise RuntimeError(f"{destino.as_posix()} releído con load_config da "
                               f"{SEPARADOR_CLAVE.join(ruta)} = {nodo!r} y no {valor!r}")
    return destino


# %% [markdown]
# ## 4. `comparar_resumenes`
#
# Una fila por (func, dim, method), en el orden de `configuraciones` del summary por defecto;
# la entrada afinada se busca por esas tres claves. Columnas (`COLUMNAS_COMPARACION`):
# mediana y media de `f_final`, tasas de éxito a $10^{-4}$ y $10^{-6}$ y evaluaciones hasta el
# éxito a $10^{-4}$, cada una por defecto y afinada, y
#
# $$\text{cambio} = \text{tasa}_{\text{afinado}} - \text{tasa}_{\text{defecto}}
#   \quad (\text{tasa de éxito a } 10^{-4};\ \text{columna } \texttt{cambio\_tasa\_exito\_1e-04})$$
#
# Los dos summary deben compartir semillas, presupuesto, funciones, dimensiones y métodos: si
# no, la comparación no sería justa (Spec §6.2) y se lanza ValueError.

# %%
def comparar_resumenes(summary_defecto: Mapping, summary_afinado: Mapping) -> list[dict]:
    """Filas de la comparación "por defecto contra afinado" (tabla de arriba); no modifica nada.

    Raises
    ------
    ValueError
        Un `meta` falta o no coincide en una clave de `CLAVES_META_COMPARABLES`; falta en el
        afinado una configuración del summary por defecto.
    """
    _exigir_metas_iguales(summary_defecto.get(CAMPO_META), summary_afinado.get(CAMPO_META),
                          "el summary por defecto", "el summary afinado")
    afinadas = {tuple(entrada[clave] for clave in CLAVES_CONFIGURACION): entrada
                for entrada in summary_afinado[CAMPO_CONFIGURACIONES]}
    filas = []
    for defecto in summary_defecto[CAMPO_CONFIGURACIONES]:
        clave = tuple(defecto[campo] for campo in CLAVES_CONFIGURACION)
        if clave not in afinadas:
            raise ValueError(f"el summary afinado no tiene la configuración "
                             f"{' '.join(map(str, clave))}")
        afinado = afinadas[clave]
        fila = dict(zip(CLAVES_CONFIGURACION, clave))
        for nombre, (bloque, campo) in METRICAS_COMPARADAS:
            fila[f"{nombre}{SUFIJO_DEFECTO}"] = defecto[bloque][campo]
            fila[f"{nombre}{SUFIJO_AFINADO}"] = afinado[bloque][campo]
        fila[COLUMNA_CAMBIO] = (afinado["tasa_exito"][SUFIJO_PRINCIPAL]
                                - defecto["tasa_exito"][SUFIJO_PRINCIPAL])
        filas.append(fila)
    return filas


def _escribir_csv(ruta: Path, filas: Sequence[Mapping]) -> None:
    """CSV en UTF-8 con saltos LF y las columnas de COLUMNAS_COMPARACION; None = celda vacía."""
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=COLUMNAS_COMPARACION,
                              lineterminator=SALTO_DE_LINEA)
    escritor.writeheader()
    escritor.writerows(filas)                # csv escribe None como texto vacío
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto.getvalue(), encoding=CODIFICACION, newline=SALTO_DE_LINEA)


def _texto(valor, formato: str) -> str:
    """Número con `formato`, o INDEFINIDO si es None."""
    return INDEFINIDO if valor is None else format(valor, formato)


def _porcentaje(fraccion) -> str:
    """Fracción en [0, 1] como porcentaje ("60.0 %"), o INDEFINIDO si es None."""
    return INDEFINIDO if fraccion is None else f"{format(CIEN * fraccion, FORMATO_PORCENTAJE)} %"


def _tabla_de_consola(filas: Sequence[Mapping]) -> str:
    """Tabla con columnas alineadas: números y diferencias con signo (en puntos porcentuales)."""
    principal, hpo = SUFIJO_PRINCIPAL, SUFIJO_UMBRAL
    defecto, afinado = SUFIJO_DEFECTO, SUFIJO_AFINADO
    cabecera = ["función", "dim", "método", "mediana defecto", "mediana afinado",
                f"éxito {principal} defecto", f"éxito {principal} afinado",
                f"cambio éxito {principal}", f"éxito {hpo} defecto", f"éxito {hpo} afinado",
                f"evals {principal} defecto", f"evals {principal} afinado"]
    lineas = [cabecera]
    for fila in filas:
        lineas.append([
            str(fila["func"]), str(fila["dim"]), str(fila["method"]),
            _texto(fila[f"f_final_mediana{defecto}"], FORMATO_F),
            _texto(fila[f"f_final_mediana{afinado}"], FORMATO_F),
            _porcentaje(fila[f"tasa_exito_{principal}{defecto}"]),
            _porcentaje(fila[f"tasa_exito_{principal}{afinado}"]),
            f"{format(CIEN * fila[COLUMNA_CAMBIO], FORMATO_CAMBIO)} pp",
            _porcentaje(fila[f"tasa_exito_{hpo}{defecto}"]),
            _porcentaje(fila[f"tasa_exito_{hpo}{afinado}"]),
            _texto(fila[f"evals_hasta_exito_{principal}{defecto}"], FORMATO_CONTEO),
            _texto(fila[f"evals_hasta_exito_{principal}{afinado}"], FORMATO_CONTEO),
        ])
    anchos = [max(len(linea[columna]) for linea in lineas) for columna in range(len(cabecera))]
    return SALTO_DE_LINEA.join(
        SEPARADOR_DE_COLUMNAS.join(celda.ljust(ancho) for celda, ancho in zip(linea, anchos))
        for linea in lineas)


# %% [markdown]
# ## 5. `ejecutar_hpo`
#
# Pasos, en este orden:
#
# 1. `validar_ejecucion` (antes de crear nada).
# 2. Por cada unidad de `construir_unidades(cfg)`, con un solo `mapeador(workers)`: reutilizar
#    su `ensayos_<unidad>.json` (si `hpo.reanudar` y el `meta` es igual) o sortear los ensayos,
#    correr sus tareas (orden: ensayo, celda), puntuar y guardar el archivo al terminarla.
# 3. Escribir `seleccion.json`; `corridas_de_ajuste` se cuenta en los registros guardados.
# 4. Escribir `hpo.config_salida` y comprobar su relectura.
# 5. Experimento final: `apply_overrides(load_config(hpo.config_salida), overrides)` con
#    `ejecutar_experimento`; escribe en `hpo.salida_afinada` y `hpo.tablas_afinada`.
# 6. Comparar con `<salida>/summary.json` (el demo lo genera si falta) y escribir
#    `comparacion.csv`.
#
# Con $U$ unidades, $T$ ensayos, $S$ semillas y $C_u$ celdas de la unidad $u$, las corridas de
# ajuste son
#
# $$\sum_{u=1}^{U} T \cdot S \cdot C_u$$

# %%
def ejecutar_hpo(cfg: dict, informar: Informar = print,
                 ruta_config: str | os.PathLike = RUTA_CONFIG_POR_DEFECTO,
                 overrides: Sequence[str] = ()) -> str:
    """Corre la HPO de `cfg`, el experimento final y la comparación; devuelve la tabla.

    Parameters
    ----------
    cfg : dict
        Config resuelta: `apply_overrides(load_config(ruta_config), overrides)`. No se
        modifica.
    informar : función que recibe un texto
        Recibe una línea por unidad, los avisos de `reanudar` y el avance de los
        experimentos. Por defecto `print`.
    ruta_config : ruta
        Archivo de `--config`; la config afinada hereda de él.
    overrides : lista de textos
        Los `--set` del comando; se vuelven a aplicar sobre la config afinada.

    Returns
    -------
    str
        Título y tabla de consola de la comparación (sin juicios: números y diferencias).

    Raises
    ------
    TypeError, ValueError, FileNotFoundError
        Los de `validar_ejecucion`, antes de crear carpetas o archivos.
    RuntimeError
        La config afinada no se relee igual o no apunta a `hpo.salida_afinada` /
        `hpo.tablas_afinada`.

    Notas
    -----
    Escribe dentro de `hpo.salida`, `hpo.config_salida`, `hpo.salida_afinada` y
    `hpo.tablas_afinada`; en `salida` y `tablas` solo en el demo sin resumen por defecto.
    """
    # Se valida aquí aunque `manejador_hpo` ya lo hizo: esta función también se llama sin el
    # CLI (pruebas, notebooks) y la validación no escribe nada. `construir_unidades` vuelve a
    # llamar a `validar_hpo` por la misma razón (es pública en hpo.py).
    validar_ejecucion(cfg, ruta_config, overrides)
    overrides = list(overrides)
    hpo = cfg[CLAVE_HPO]
    unidades = construir_unidades(cfg)
    config_corrida = _config_sin_workers(cfg)

    with mapeador(cfg[CLAVE_WORKERS]) as mapear:
        datos_por_unidad = [_datos_de_unidad(mapear, cfg, config_corrida, unidad,
                                             len(unidades), informar)
                            for unidad in unidades]

    seleccion = _seleccion(cfg, unidades, datos_por_unidad)
    save_json(Path(hpo[CLAVE_HPO_SALIDA]) / NOMBRE_SELECCION, seleccion)
    ganadores = [(unidad, entrada["elegido"])
                 for unidad, entrada in zip(unidades, seleccion["unidades"])]
    destino = _escribir_config_afinada(cfg, ganadores, ruta_config, overrides)

    cfg_final = apply_overrides(load_config(destino), overrides)
    if (cfg_final[CLAVE_SALIDA] != hpo[CLAVE_SALIDA_AFINADA]
            or cfg_final[CLAVE_TABLAS] != hpo[CLAVE_TABLAS_AFINADA]):
        raise RuntimeError(f"la config afinada {destino.as_posix()} no escribe en "
                           f"{hpo[CLAVE_SALIDA_AFINADA]} y {hpo[CLAVE_TABLAS_AFINADA]}")
    informar(f"Experimento final con los valores afinados ({destino.as_posix()})")
    ejecutar_experimento(cfg_final, informar)

    summary_defecto = Path(cfg[CLAVE_SALIDA]) / NOMBRE_SUMMARY
    if not summary_defecto.is_file():
        if not es_demo(cfg):
            # validar_ejecucion ya exigió este archivo fuera del demo: solo se llega aquí si
            # alguien lo borró mientras corría la HPO.
            raise FileNotFoundError(
                f"no existe {summary_defecto.as_posix()}: corre antes "
                f"`{COMANDO_PART1.format(ruta=Path(ruta_config).as_posix())}`")
        informar(f"Demo: no existe {summary_defecto.as_posix()}; se genera su resumen por "
                 "defecto con la misma config")
        ejecutar_experimento(cfg, informar)
    filas = comparar_resumenes(load_json(summary_defecto),
                               load_json(Path(hpo[CLAVE_SALIDA_AFINADA]) / NOMBRE_SUMMARY))
    ruta_csv = Path(hpo[CLAVE_TABLAS_AFINADA]) / NOMBRE_COMPARACION
    _escribir_csv(ruta_csv, filas)
    return SALTO_DE_LINEA.join([f"{TITULO_COMPARACION} ({ruta_csv.as_posix()})",
                                _tabla_de_consola(filas)])


# %% [markdown]
# ## 6. `manejador_hpo`
#
# Es la función que `src/common/cli.py` llama con la config final de `run.py hpo`, la ruta de
# `--config` y la lista de `--set`.
#
# | Caso | Qué hace | Retorna |
# |---|---|---|
# | `validar_ejecucion` lanza TypeError, ValueError o FileNotFoundError | motivo en stderr | 2 |
# | config válida | corre la HPO e imprime la comparación | 0 |
#
# Un error posterior a la validación sale como excepción.

# %%
def manejador_hpo(cfg: dict, ruta_config: str | os.PathLike, overrides: Sequence[str]) -> int:
    """Manejador de `python run.py hpo`: valida, corre la HPO e imprime la comparación."""
    # Valida antes para convertir sus errores en el código 2; ejecutar_hpo valida de nuevo.
    try:
        validar_ejecucion(cfg, ruta_config, overrides)
    except (TypeError, ValueError, FileNotFoundError) as error:
        print(f"run.py hpo: error: configuración inválida: {error}", file=sys.stderr)
        return CODIGO_ERROR_DE_USO

    print(ejecutar_hpo(cfg, ruta_config=ruta_config, overrides=overrides))
    return CODIGO_CORRECTO
