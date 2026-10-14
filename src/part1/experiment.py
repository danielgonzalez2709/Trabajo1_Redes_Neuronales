# %% [markdown]
# # Experimento de la Parte 1 (T1.7 y T1.8; Spec §4.1, §5.4, §6.2, §6.5, §6.6 y §6.8)
#
# **Propósito.** Ejecutar todas las corridas que describe una config de la Parte 1, guardar
# un JSON por corrida, resumirlas en `summary.json` y en dos tablas CSV, y servir de manejador
# de `python run.py part1`. Una corrida la ejecuta `corrida.py` y las estadísticas las calcula
# `metricas.py`: este módulo solo valida la config, reparte el trabajo y escribe los archivos.
#
# **Mapa del módulo:**
#
# | # | Nombre | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `validar_config` | revisa la config antes de crear carpetas o correr | `None` |
# | 2 | `avisos_de_tabla` | avisos de `metricas.py` con el nombre de su tabla | `list[str]` |
# | 3 | `rutas_de_figuras` | rutas de las figuras de trayectoria que pide la config | `list[Path]` |
# | 4 | `ejecutar_experimento` | corre, guarda y resume el experimento | `str` |
# | 5 | `manejador_part1` | manejador del subcomando `part1` de `run.py` | `int` |
#
# Entre las auxiliares, `mapeador` (corre tareas en serie o en un grupo de procesos) también es
# pública: la usa `hpo_experimento.py`.
#
# **Archivos que escribe** (`salida` y `tablas` son claves de la config):
#
# | Ruta | Contenido |
# |---|---|
# | `<salida>/runs/{func}_{dim}d_{method}_seed{s}.json` | corrida con $k = 2n$ (Spec §5.4) |
# | `<salida>/k1/runs/{func}_{dim}d_{method}_seed{s}.json` | re-ejecución de un GD con $k = 1$ |
# | `<salida>/summary.json` | `meta`, `configuraciones`, `sensibilidad_k1`, `avisos` |
# | `<tablas>/tabla_principal.csv` | una fila por configuración, $k = 2n$ |
# | `<tablas>/tabla_sensibilidad_k1.csv` | una fila por configuración, sensibilidad $k = 1$ |
# | `<salida>/trayectoria_{func}_2d.png` | solo con `figura_trayectoria: true` (Spec §6.8) |
#
# **Conteo y azar.** El costo del gradiente, el presupuesto y el generador de cada corrida los
# arma `ejecutar_corrida` (Spec §6.2 y §4.1); aquí no se evalúa ninguna función. La figura de
# trayectoria la dibuja `src/viz/part1_demo.py` con lo que ya está en los JSON de corrida.

# %%
"""Experimento de la Parte 1: validación de la config, corridas, summary.json y tablas."""

from __future__ import annotations

import contextlib
import copy
import csv
import io
import math
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from numbers import Integral, Real
from pathlib import Path
from time import perf_counter

from src.common.results import load_json, run_filename, save_json
from src.common.seeds import seeds_for_runs, validar_entero
from src.part1._comun import DIMENSION_CON_FRAMES
from src.part1.corrida import (
    CLAVE_RECORD_FRAMES,
    DIMENSION_MINIMA,
    K_SENSIBILIDAD,
    METODOS,
    METODOS_GD,
    ejecutar_corrida,
)
from src.part1.functions import FUNCIONES, get_function
from src.part1.metricas import (
    UMBRAL_PRINCIPAL,
    UMBRALES,
    a_filas_csv,
    avisos,
    formatear_tabla_consola,
    resumir_configuracion,
)

# %% [markdown]
# ## Constantes del módulo
#
# Nombres de las claves de la config (Spec §4.1), de los archivos y carpetas (Spec §5.4) y
# textos de la salida. Los valores por defecto de los parámetros no están aquí: viven en
# `configs/part1/base.yaml`. `CLAVE_RECORD_FRAMES` se importa de `corrida.py`.

# %%
CLAVE_FUNC = "func"
CLAVE_DIM = "dim"
CLAVE_METODOS = "methods"
CLAVE_RUNS = "runs"
CLAVE_BASE_SEED = "base_seed"
CLAVE_PRESUPUESTO = "presupuesto_por_dim"
CLAVE_WORKERS = "workers"
CLAVE_SALIDA = "salida"
CLAVE_TABLAS = "tablas"
CLAVE_FIGURA = "figura_trayectoria"
CLAVES_OBLIGATORIAS = (CLAVE_FUNC, CLAVE_DIM, CLAVE_METODOS, CLAVE_RUNS, CLAVE_BASE_SEED,
                       CLAVE_RECORD_FRAMES, CLAVE_PRESUPUESTO, CLAVE_WORKERS, CLAVE_SALIDA,
                       CLAVE_TABLAS, CLAVE_FIGURA)
# Claves que no cambian el resultado de una corrida: no se guardan en su JSON.
CLAVES_FUERA_DE_LA_CORRIDA = (CLAVE_WORKERS, CLAVE_FIGURA)

MINIMO_POSITIVO = 1                      # runs, presupuesto_por_dim y workers: enteros >= 1
WORKERS_EN_SERIE = 1                     # con este valor no se crean procesos
RUN_ID_CON_FRAMES = 0                    # Spec §5.4: solo esta corrida pide frames
K_REGLA = "2n"                           # Spec §6.2: regla principal, k = 2·dim

CARPETA_CORRIDAS = "runs"                # <salida>/runs y <salida>/k1/runs
CARPETA_K1 = "k1"
NOMBRE_SUMMARY = "summary.json"
NOMBRE_CSV_PRINCIPAL = "tabla_principal.csv"
NOMBRE_CSV_SENSIBILIDAD = "tabla_sensibilidad_k1.csv"
NOMBRE_FIGURA = "trayectoria_{func}_{dim}d.png"
CODIFICACION = "utf-8"
SALTO_DE_LINEA = "\n"

ETIQUETA_PRINCIPAL = "Tabla principal (k = 2n)"
ETIQUETA_SENSIBILIDAD = "Sensibilidad k = 1"
TITULO_AVISOS = "Avisos (resultados que conviene revisar):"
TEXTO_SIN_AVISOS = "ninguno"
TEXTO_FIGURA = "Figura de trayectoria: {ruta}"
TEXTO_TIEMPO = "Tiempo de ejecución: {segundos:.1f} s"
CODIGO_CORRECTO = 0
CODIGO_ERROR_DE_USO = 2                  # el mismo código con el que argparse informa un error

Informar = Callable[[str], None]


# %% [markdown]
# ## 1. `validar_config`
#
# | Clave | Regla |
# |---|---|
# | `func`, `dim`, `methods` | lista no vacía, sin repetidos |
# | `func` | cada elemento es una clave de `FUNCIONES` |
# | `dim` | cada elemento es un entero $\ge 1$ (no bool) que la función admite |
# | `methods` | cada elemento es uno de `METODOS` |
# | `runs`, `presupuesto_por_dim`, `workers` | entero $\ge 1$ (no bool) |
# | `base_seed` | entero $\ge 0$ (no bool) |
# | `record_frames`, `figura_trayectoria` | bool |
# | `figura_trayectoria` | si es `true`: `record_frames` es `true` y 2 está en `dim` |
# | `salida`, `tablas` | texto con algún carácter que no sea espacio |
# | toda la config | ningún real no finito (NaN, $\pm\infty$), a cualquier profundidad |
#
# De los bloques de cada método (`gd:`, `ea:`, `pso:`, `de:`) aquí solo se revisan los valores
# no finitos. El resto lo valida cada optimizador al empezar su corrida: `ea`, `pso` y `de`
# su bloque completo; el GD, solo las claves que usa su variante.

# %%
def _exigir_clave(cfg: Mapping, clave: str):
    """Devuelve `cfg[clave]`; si la clave no está, ValueError."""
    if clave not in cfg:
        raise ValueError(f"falta la clave '{clave}' en la config de la Parte 1")
    return cfg[clave]


def _validar_lista(cfg: Mapping, clave: str) -> list:
    """Devuelve `cfg[clave]` si es una lista no vacía; si no, TypeError o ValueError."""
    valor = _exigir_clave(cfg, clave)
    if not isinstance(valor, list):
        raise TypeError(f"{clave} debe ser una lista (p. ej. [a, b]); se recibió {valor!r} "
                        f"({type(valor).__name__})")
    if len(valor) == 0:
        raise ValueError(f"{clave} no puede ser una lista vacía")
    return valor


def _rechazar_repetidos(elementos: Sequence, clave: str) -> None:
    """ValueError si algún elemento de `elementos` aparece más de una vez."""
    repetidos = [elemento for posicion, elemento in enumerate(elementos)
                 if elemento in elementos[:posicion]]
    if repetidos:
        raise ValueError(f"{clave} tiene elementos repetidos: {repetidos[0]!r}")


def _validar_identificadores(cfg: Mapping, clave: str, validos: Sequence[str]) -> list[str]:
    """Lista `cfg[clave]` de textos que están en `validos`, sin repetidos."""
    elementos = _validar_lista(cfg, clave)
    for elemento in elementos:
        if not isinstance(elemento, str) or elemento not in validos:
            raise ValueError(f"{clave}: identificador desconocido {elemento!r}; "
                             f"válidos: {', '.join(validos)}")
    _rechazar_repetidos(elementos, clave)
    return elementos


def _validar_dimensiones(cfg: Mapping) -> list[int]:
    """Lista `cfg["dim"]` de enteros >= DIMENSION_MINIMA (no bool), sin repetidos."""
    elementos = _validar_lista(cfg, CLAVE_DIM)
    dimensiones = [validar_entero(elemento, f"{CLAVE_DIM}[{posicion}]", minimo=DIMENSION_MINIMA)
                   for posicion, elemento in enumerate(elementos)]
    _rechazar_repetidos(dimensiones, CLAVE_DIM)
    return dimensiones


def _validar_bool(cfg: Mapping, clave: str) -> None:
    """TypeError si `cfg[clave]` no es un bool de Python."""
    valor = _exigir_clave(cfg, clave)
    if not isinstance(valor, bool):
        raise TypeError(f"{clave} debe ser bool (true o false); se recibió {valor!r} "
                        f"({type(valor).__name__})")


def _validar_texto(cfg: Mapping, clave: str) -> None:
    """TypeError si `cfg[clave]` no es texto; ValueError si está vacío o solo tiene espacios."""
    valor = _exigir_clave(cfg, clave)
    if not isinstance(valor, str):
        raise TypeError(f"{clave} debe ser un texto (ruta de una carpeta); se recibió "
                        f"{valor!r} ({type(valor).__name__})")
    if not valor.strip():
        raise ValueError(f"{clave} no puede ser un texto vacío")


def _rechazar_no_finitos(valor, ruta: str) -> None:
    """ValueError con la ruta de la clave si `valor` contiene un real NaN o infinito.

    Recorre diccionarios y listas (o tuplas) a cualquier profundidad. La ruta une las claves
    con puntos y marca las posiciones de lista con corchetes: `pso.w`, `extra.valores[1]`.
    """
    if isinstance(valor, Mapping):
        for clave, hijo in valor.items():
            _rechazar_no_finitos(hijo, f"{ruta}.{clave}" if ruta else str(clave))
    elif isinstance(valor, (list, tuple)):
        for posicion, hijo in enumerate(valor):
            _rechazar_no_finitos(hijo, f"{ruta}[{posicion}]")
    elif isinstance(valor, Real) and not isinstance(valor, Integral):
        if not math.isfinite(valor):
            raise ValueError(f"{ruta} no es finito ({valor!r}): la config no admite NaN ni "
                             "infinitos; \"sin límite\" se escribe null (Spec §4.1)")


def validar_config(cfg: dict) -> None:
    """Revisa la config de la Parte 1 (Spec §4.1); no crea carpetas, no corre y no la modifica.

    Raises
    ------
    TypeError
        `cfg` no es un mapeo; una clave tiene un tipo que no corresponde (lista, entero no
        bool, bool o texto según la tabla de arriba).
    ValueError
        Falta una clave; lista vacía o con repetidos; identificador desconocido; entero fuera
        de rango; texto vacío; dimensión que la función no admite; `figura_trayectoria` sin
        frames que dibujar; real no finito (el mensaje da la ruta de la clave, p. ej. `pso.w`).
    """
    if not isinstance(cfg, Mapping):
        raise TypeError(f"la config debe ser un mapeo (dict); se recibió {type(cfg).__name__}")
    for clave in CLAVES_OBLIGATORIAS:
        _exigir_clave(cfg, clave)

    funciones = _validar_identificadores(cfg, CLAVE_FUNC, sorted(FUNCIONES))
    dimensiones = _validar_dimensiones(cfg)
    _validar_identificadores(cfg, CLAVE_METODOS, METODOS)
    # Cada función comprueba su dimensión mínima al construirse (p. ej. Rosenbrock exige 2).
    for func in funciones:
        for dim in dimensiones:
            get_function(func, dim)

    validar_entero(cfg[CLAVE_RUNS], CLAVE_RUNS, minimo=MINIMO_POSITIVO)
    validar_entero(cfg[CLAVE_BASE_SEED], CLAVE_BASE_SEED)
    validar_entero(cfg[CLAVE_PRESUPUESTO], CLAVE_PRESUPUESTO, minimo=MINIMO_POSITIVO)
    validar_entero(cfg[CLAVE_WORKERS], CLAVE_WORKERS, minimo=MINIMO_POSITIVO)
    _validar_bool(cfg, CLAVE_RECORD_FRAMES)
    _validar_texto(cfg, CLAVE_SALIDA)
    _validar_texto(cfg, CLAVE_TABLAS)
    _validar_bool(cfg, CLAVE_FIGURA)
    # La figura se dibuja con los frames, que solo existen en 2D y con record_frames (§5.4).
    if cfg[CLAVE_FIGURA] and not cfg[CLAVE_RECORD_FRAMES]:
        raise ValueError(f"{CLAVE_FIGURA}: true exige {CLAVE_RECORD_FRAMES}: true (la figura "
                         "se dibuja con los frames de la corrida)")
    if cfg[CLAVE_FIGURA] and DIMENSION_CON_FRAMES not in dimensiones:
        raise ValueError(f"{CLAVE_FIGURA}: true exige que {DIMENSION_CON_FRAMES} esté en "
                         f"{CLAVE_DIM} (solo las corridas en {DIMENSION_CON_FRAMES}D guardan "
                         f"frames); se recibió {CLAVE_DIM}: {dimensiones}")
    _rechazar_no_finitos(cfg, "")


# %% [markdown]
# ## 2. `avisos_de_tabla`
#
# Los avisos se calculan dos veces: sobre la tabla principal y sobre las re-ejecuciones con
# $k = 1$. Cada texto empieza con la etiqueta de su tabla para poder distinguirlos.

# %%
def avisos_de_tabla(etiqueta: str, resumenes: Sequence[Mapping],
                    corridas_por_configuracion: Sequence[Sequence[Mapping]]) -> list[str]:
    """Textos de `metricas.avisos` con el prefijo `"<etiqueta>: "`."""
    return [f"{etiqueta}: {texto}" for texto in avisos(resumenes, corridas_por_configuracion)]


# %% [markdown]
# ## Auxiliares de `ejecutar_experimento`
#
# **Tarea.** Una tarea es la tupla de argumentos de una corrida. `_correr_tarea` es una
# función de nivel de módulo para que `ProcessPoolExecutor` pueda enviarla a otro proceso
# también cuando los procesos se crean con `spawn` (Windows).
#
# **Orden.** Las corridas de una configuración se piden con `map` (el de Python o el del
# ejecutor): los dos devuelven los resultados en el orden de las tareas, es decir por
# `run_id`, sin importar cuál termina primero. Los archivos los escribe el proceso principal.
#
# **Frames** (Spec §5.4). Una corrida pide frames si se cumplen las tres condiciones:
#
# $$\text{record\_frames} \;\wedge\; n = 2 \;\wedge\; \text{run\_id} = 0$$

# %%
def _correr_tarea(tarea: tuple) -> dict:
    """Ejecuta una corrida a partir de su tupla de argumentos y devuelve su diccionario."""
    func, dim, method, base_seed, run_id, cfg, k, presupuesto_por_dim, grabar_frames = tarea
    return ejecutar_corrida(func, dim, method, base_seed, run_id, cfg, k=k,
                            presupuesto_por_dim=presupuesto_por_dim,
                            grabar_frames=grabar_frames)


@contextlib.contextmanager
def mapeador(workers: int) -> Iterator[Callable]:
    """Entrega una función `map(funcion, tareas)`: la de Python o la de un grupo de procesos.

    Es pública porque también la usa `hpo_experimento.py`.
    """
    if workers == WORKERS_EN_SERIE:
        yield map
    else:
        with ProcessPoolExecutor(max_workers=workers) as ejecutor:
            yield ejecutor.map


def _configuraciones(cfg: Mapping) -> list[tuple[str, int, str]]:
    """Ternas (func, dim, method) en el orden de la config: func, luego dim, luego method."""
    return [(func, dim, method) for func in cfg[CLAVE_FUNC] for dim in cfg[CLAVE_DIM]
            for method in cfg[CLAVE_METODOS]]


def _config_de_corrida(cfg: Mapping) -> dict:
    """Copia profunda de `cfg` sin `workers` ni `figura_trayectoria`: la config de cada corrida.

    `workers` solo decide cuántos procesos se usan y `figura_trayectoria`, si se dibuja una
    figura al terminar; al quitarlas, el JSON de una corrida es el mismo byte a byte con
    cualquier número de procesos, con figura o sin ella.
    """
    config = copy.deepcopy(dict(cfg))
    for clave in CLAVES_FUERA_DE_LA_CORRIDA:
        del config[clave]
    return config


def _pide_frames(cfg: Mapping, dim: int, run_id: int) -> bool:
    """Condición de Spec §5.4: record_frames, dim == 2 y run_id == 0."""
    return (cfg[CLAVE_RECORD_FRAMES] and dim == DIMENSION_CON_FRAMES
            and run_id == RUN_ID_CON_FRAMES)


def _correr_tabla(mapear: Callable, cfg: Mapping, configuraciones: Sequence[tuple],
                  k: float | None, con_frames: bool, carpeta: Path, etiqueta: str,
                  informar: Informar) -> tuple[list[dict], list[str]]:
    """Corre, guarda y resume cada configuración de `configuraciones`, una tras otra.

    Parameters
    ----------
    mapear : función `map(funcion, tareas)` de `mapeador`.
    k : costo del gradiente que recibe `ejecutar_corrida` (None = 2·dim).
    con_frames : si es False, ninguna corrida de esta tabla pide frames.
    carpeta : carpeta de los JSON de corridas.
    etiqueta : nombre de la tabla en los avisos y en el avance.

    Returns
    -------
    (resúmenes, avisos) : un resumen de `resumir_configuracion` por configuración, en el
    orden recibido, y los avisos de todas ellas (por configuración y, dentro de cada una, en
    el orden de tipos de `metricas.avisos`).
    """
    config_corrida = _config_de_corrida(cfg)
    resumenes = []
    textos = []
    for numero, (func, dim, method) in enumerate(configuraciones, start=1):
        tareas = [(func, dim, method, cfg[CLAVE_BASE_SEED], run_id, config_corrida, k,
                   cfg[CLAVE_PRESUPUESTO], con_frames and _pide_frames(cfg, dim, run_id))
                  for run_id in range(cfg[CLAVE_RUNS])]
        corridas = list(mapear(_correr_tarea, tareas))
        for corrida in corridas:
            # corrida["seed"] es la semilla efectiva base_seed + run_id (Spec §5.4).
            save_json(carpeta / run_filename(func, dim, method, corrida["seed"]), corrida)
        resumen = resumir_configuracion(corridas)
        resumenes.append(resumen)
        textos.extend(avisos_de_tabla(etiqueta, [resumen], [corridas]))
        informar(f"[{numero}/{len(configuraciones)}] {etiqueta}: {func} {dim}D {method}, "
                 f"{len(corridas)} corrida(s)")
    return resumenes, textos


def _tabla_de_sensibilidad(configuraciones: Sequence[tuple], principales: Sequence[Mapping],
                           reejecutadas: Mapping[tuple, Mapping]) -> list[dict]:
    """Una entrada por configuración: la re-ejecución con k = 1 si existe, o copia de la principal.

    `reejecutadas` asocia (func, dim, method) con su resumen de k = 1; solo trae los métodos
    de `METODOS_GD`.
    """
    return [copy.deepcopy(dict(reejecutadas.get(configuracion, principal)))
            for configuracion, principal in zip(configuraciones, principales)]


def _escribir_csv(ruta: Path, resumenes: Sequence[Mapping]) -> None:
    """Escribe `resumenes` como CSV en UTF-8 con saltos LF; un None queda como celda vacía."""
    filas = a_filas_csv(resumenes)
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=list(filas[0]), lineterminator=SALTO_DE_LINEA)
    escritor.writeheader()
    escritor.writerows(filas)                # csv escribe None como texto vacío
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto.getvalue(), encoding=CODIFICACION, newline=SALTO_DE_LINEA)


def _nota_de_sensibilidad(metodos: Sequence[str]) -> str:
    """Dice qué métodos de `metodos` se re-ejecutaron y cuáles repiten su fila principal.

    Conserva el orden de `metodos`; un grupo sin métodos no se escribe.
    """
    reejecutados = [metodo for metodo in metodos if metodo in METODOS_GD]
    copiados = [metodo for metodo in metodos if metodo not in METODOS_GD]
    partes = []
    if reejecutados:
        partes.append(f"re-ejecutados con k = {K_SENSIBILIDAD}: {', '.join(reejecutados)}")
    if copiados:
        partes.append(f"filas de la tabla principal: {', '.join(copiados)}")
    return "; ".join(partes)


def _texto_de_tablas(principales: Sequence[Mapping], sensibilidad: Sequence[Mapping],
                     metodos: Sequence[str]) -> str:
    """Las dos tablas de consola, cada una bajo su título y separadas por una línea vacía."""
    return SALTO_DE_LINEA.join([
        ETIQUETA_PRINCIPAL,
        formatear_tabla_consola(principales),
        "",
        f"{ETIQUETA_SENSIBILIDAD} ({_nota_de_sensibilidad(metodos)})",
        formatear_tabla_consola(sensibilidad),
    ])


# %% [markdown]
# ## 3. `rutas_de_figuras`
#
# Con `figura_trayectoria: true` (Spec §6.8) hay una figura por función de la config, en el
# orden de `func`: `<salida>/trayectoria_{func}_2d.png`. Con `false`, ninguna. Cada figura
# reúne la corrida con `run_id = 0` de cada método en 2D, la única que guarda frames (§5.4).
#
# `rutas_de_figuras` solo calcula las rutas; la usan `ejecutar_experimento` (que escribe las
# figuras) y `manejador_part1` (que las informa). `src/viz/part1_demo.py` se importa dentro
# de `_escribir_figuras`: sin figura, el experimento no carga matplotlib.

# %%
def rutas_de_figuras(cfg: Mapping) -> list[Path]:
    """Rutas de las figuras de trayectoria de `cfg`, una por función; vacía si no se piden."""
    if not cfg[CLAVE_FIGURA]:
        return []
    salida = Path(cfg[CLAVE_SALIDA])
    return [salida / NOMBRE_FIGURA.format(func=func, dim=DIMENSION_CON_FRAMES)
            for func in cfg[CLAVE_FUNC]]


def _escribir_figuras(cfg: Mapping) -> None:
    """Dibuja cada figura de `rutas_de_figuras` con las corridas ya guardadas en `runs/`."""
    rutas = rutas_de_figuras(cfg)
    if not rutas:
        return
    from src.viz import part1_demo           # perezosa: solo aquí hace falta matplotlib

    carpeta = Path(cfg[CLAVE_SALIDA]) / CARPETA_CORRIDAS
    semilla = seeds_for_runs(cfg[CLAVE_BASE_SEED], cfg[CLAVE_RUNS])[RUN_ID_CON_FRAMES]
    for func, ruta in zip(cfg[CLAVE_FUNC], rutas):
        corridas = [load_json(carpeta / run_filename(func, DIMENSION_CON_FRAMES, method,
                                                     semilla))
                    for method in cfg[CLAVE_METODOS]]
        part1_demo.figura_trayectoria(corridas, ruta)


# %% [markdown]
# ## 4. `ejecutar_experimento`
#
# Pasos, en este orden:
#
# 1. Validar la config (antes de crear carpetas).
# 2. **Tabla principal:** por cada (func, dim, method) en el orden de la config, correr las
#    `runs` semillas con $k = 2n$, guardar cada JSON en `<salida>/runs/` y resumir.
# 3. **Sensibilidad $k = 1$** (Spec §6.2): solo los métodos de `METODOS_GD` se vuelven a
#    correr, con el mismo presupuesto y las mismas semillas, sin frames, y se guardan en
#    `<salida>/k1/runs/`. En `ea`, `pso` y `de` la entrada de sensibilidad es una copia de la
#    principal (su campo `k` conserva el valor $2n$ con el que se ejecutaron).
# 4. Escribir `<salida>/summary.json` y los dos CSV de `<tablas>/`.
# 5. Con `figura_trayectoria: true`, escribir las figuras de `rutas_de_figuras`.
#
# El presupuesto de cada corrida es el de Spec §6.2:
#
# $$\text{presupuesto} = \text{presupuesto\_por\_dim} \cdot n$$

# %%
def ejecutar_experimento(cfg: dict, informar: Informar = print) -> str:
    """Corre el experimento de `cfg`, escribe sus archivos y devuelve las tablas de consola.

    Parameters
    ----------
    cfg : dict
        Config resuelta de la Parte 1 (p. ej. `load_config("configs/part1/base.yaml")`).
        No se modifica.
    informar : función que recibe un texto
        Recibe una línea por configuración terminada. Por defecto `print`.

    Returns
    -------
    str
        La tabla principal y, aparte, la de sensibilidad k = 1 (`formatear_tabla_consola`),
        cada una bajo una línea de título.

    Raises
    ------
    TypeError, ValueError
        Los de `validar_config`, antes de crear carpetas o archivos. Después, los que lance
        el optimizador de una corrida al validar su bloque de la config.

    Notas
    -----
    Solo escribe dentro de `cfg["salida"]` y `cfg["tablas"]`. No borra archivos que hubiera
    antes en esas carpetas: sobrescribe los que tienen el mismo nombre.
    """
    validar_config(cfg)
    salida = Path(cfg[CLAVE_SALIDA])
    configuraciones = _configuraciones(cfg)
    configuraciones_gd = [configuracion for configuracion in configuraciones
                          if configuracion[2] in METODOS_GD]

    with mapeador(cfg[CLAVE_WORKERS]) as mapear:
        principales, avisos_principal = _correr_tabla(
            mapear, cfg, configuraciones, k=None, con_frames=True,
            carpeta=salida / CARPETA_CORRIDAS, etiqueta=ETIQUETA_PRINCIPAL, informar=informar)
        resumenes_k1, avisos_k1 = _correr_tabla(
            mapear, cfg, configuraciones_gd, k=K_SENSIBILIDAD, con_frames=False,
            carpeta=salida / CARPETA_K1 / CARPETA_CORRIDAS, etiqueta=ETIQUETA_SENSIBILIDAD,
            informar=informar)

    sensibilidad = _tabla_de_sensibilidad(configuraciones, principales,
                                          dict(zip(configuraciones_gd, resumenes_k1)))
    save_json(salida / NOMBRE_SUMMARY, {
        "meta": {
            "runs": cfg[CLAVE_RUNS],
            "base_seed": cfg[CLAVE_BASE_SEED],
            "semillas": seeds_for_runs(cfg[CLAVE_BASE_SEED], cfg[CLAVE_RUNS]),
            "presupuesto_por_dim": cfg[CLAVE_PRESUPUESTO],
            "umbrales": list(UMBRALES),
            "umbral_principal": UMBRAL_PRINCIPAL,
            "k_regla": K_REGLA,
            "k_sensibilidad": K_SENSIBILIDAD,
            "func": list(cfg[CLAVE_FUNC]),
            "dim": list(cfg[CLAVE_DIM]),
            "methods": list(cfg[CLAVE_METODOS]),
        },
        "configuraciones": principales,
        "sensibilidad_k1": sensibilidad,
        "avisos": avisos_principal + avisos_k1,
    })

    tablas = Path(cfg[CLAVE_TABLAS])
    _escribir_csv(tablas / NOMBRE_CSV_PRINCIPAL, principales)
    _escribir_csv(tablas / NOMBRE_CSV_SENSIBILIDAD, sensibilidad)
    _escribir_figuras(cfg)
    return _texto_de_tablas(principales, sensibilidad, cfg[CLAVE_METODOS])


# %% [markdown]
# ## 5. `manejador_part1`
#
# Es la función que `src/common/cli.py` llama con la config final de `run.py part1`.
#
# | Caso | Qué hace | Retorna |
# |---|---|---|
# | config que `validar_config` rechaza | escribe el motivo en la salida de error | 2 |
# | config válida | corre el experimento e imprime las tablas, el tiempo y los avisos | 0 |
#
# Entre las tablas y los avisos imprime la ruta de cada figura de trayectoria (si la config
# las pide) y el tiempo de ejecución.
#
# Solo se convierten en código 2 los errores de `validar_config`. Un error posterior (por
# ejemplo, el de un optimizador que rechaza su bloque) sale como excepción.

# %%
def manejador_part1(cfg: dict) -> int:
    """Manejador de `python run.py part1`: valida, corre el experimento e imprime el resumen.

    Los avisos que imprime son los que quedaron guardados en `<salida>/summary.json`. El
    tiempo es el de `ejecutar_experimento` completo: las corridas, los archivos y la figura.
    """
    try:
        validar_config(cfg)
    except (TypeError, ValueError) as error:
        print(f"run.py part1: error: configuración inválida: {error}", file=sys.stderr)
        return CODIGO_ERROR_DE_USO

    inicio = perf_counter()
    tablas = ejecutar_experimento(cfg)
    segundos = perf_counter() - inicio
    print(tablas)
    print()
    for ruta in rutas_de_figuras(cfg):
        print(TEXTO_FIGURA.format(ruta=ruta))
    print(TEXTO_TIEMPO.format(segundos=segundos))
    textos = load_json(Path(cfg[CLAVE_SALIDA]) / NOMBRE_SUMMARY)["avisos"]
    print()
    print(TITULO_AVISOS)
    for texto in textos or [TEXTO_SIN_AVISOS]:
        print(f"  - {texto}")
    return CODIGO_CORRECTO
