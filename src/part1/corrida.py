# %% [markdown]
# # Una corrida de la Parte 1 (T1.7; Spec §5.1, §5.4, §6.2 y §6.3)
#
# **Propósito.** Ejecutar UNA corrida (una función, una dimensión, un método y una semilla) y
# devolver el diccionario de Spec §5.4. El módulo no escribe archivos, no imprime y no modifica
# el `cfg` que recibe: quien lo llama decide qué hacer con el diccionario.
#
# **Mapa del módulo:**
#
# | # | Nombre | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `obtener_optimizador` | elige el `optimize` de un método de §5.4 | función |
# | 2 | `ejecutar_corrida` | valida, arma el problema contado y corre el método | `dict` |
#
# **Conteo.** El costo de un gradiente y el presupuesto se entregan a `CountedProblem`
# (Spec §6.2); este módulo no cuenta evaluaciones:
#
# $$k = 2n \;\;(\text{si no se indica otro}), \qquad
#   \text{presupuesto} = \text{presupuesto\_por\_dim} \cdot n$$
#
# **Azar.** El generador de la corrida es `make_rng(base_seed, run_id)` (Spec §4.1) y solo lo
# usa el optimizador.

# %%
"""Una corrida de la Parte 1: despachador de métodos y diccionario de resultados (Spec §5.4)."""

from __future__ import annotations

import copy
from collections.abc import Callable

import numpy as np

from src.common.counter import CountedProblem
from src.common.seeds import make_rng, validar_entero
from src.part1 import de, ea, gd, pso
from src.part1._comun import validar_real
from src.part1.functions import get_function

# %% [markdown]
# ## Constantes del módulo
#
# `METODOS` son los identificadores de Spec §5.4. Los dos de descenso por gradiente comparten
# `gd.optimize` y se distinguen por `cfg["variante"]` (Spec §6.3); `METODOS_GD` guarda qué
# variante corresponde a cada uno.

# %%
PRESUPUESTO_POR_DIM_DEFECTO = 10_000     # Spec §6.2: 10 000 · n evaluaciones equivalentes
K_SENSIBILIDAD = 1                       # Spec §6.2: k de la tabla de sensibilidad
FACTOR_K_PRINCIPAL = 2                   # Spec §6.2: k = 2n (regla principal)
DIMENSION_MINIMA = 1                     # la dimensión mínima de cada función la exige ella misma

METODOS_GD = {"gdfijo": gd.VARIANTE_FIJO, "gdarmijo": gd.VARIANTE_ARMIJO}
METODOS_SIN_GRADIENTE = ("ea", "pso", "de")
METODOS = (*METODOS_GD, *METODOS_SIN_GRADIENTE)

CLAVE_VARIANTE = "variante"              # clave de cfg que lee gd.optimize
CLAVE_RECORD_FRAMES = "record_frames"    # clave de cfg que leen los cinco optimizadores

# Módulo que implementa cada método; su `optimize` se busca al despachar.
_MODULOS = {"gdfijo": gd, "gdarmijo": gd, "ea": ea, "pso": pso, "de": de}


# %% [markdown]
# ## 1. `obtener_optimizador`
#
# | `method` | Función |
# |---|---|
# | `gdfijo`, `gdarmijo` | `gd.optimize` |
# | `ea` | `ea.optimize` |
# | `pso` | `pso.optimize` |
# | `de` | `de.optimize` |
#
# La variante del GD no se decide aquí: la fija `ejecutar_corrida` en la configuración.

# %%
def _validar_metodo(method) -> str:
    """Devuelve `method` si es uno de `METODOS`; si no, ValueError que lista los válidos."""
    if not isinstance(method, str) or method not in METODOS:
        raise ValueError(f"método desconocido {method!r}; métodos válidos: {', '.join(METODOS)}")
    return method


def obtener_optimizador(method: str) -> Callable:
    """Devuelve la función `optimize(problem, cfg, rng)` (contrato §5.1) del método `method`.

    Un `method` que no está en `METODOS` lanza ValueError con la lista de los válidos.
    """
    return _MODULOS[_validar_metodo(method)].optimize


# %% [markdown]
# ## 2. `ejecutar_corrida`
#
# Pasos, en este orden:
#
# 1. Validar `dim`, las semillas, $k$, el presupuesto, `method`, `grabar_frames` y `cfg`.
# 2. Construir la función (ahí se validan `func` y la dimensión mínima), el `CountedProblem`
#    con $k$ y el presupuesto, y el generador. El optimizador aún no se ha llamado.
# 3. Copiar `cfg` en profundidad y fijar en la copia `record_frames` y, solo en los métodos
#    de `METODOS_GD`, `variante`.
# 4. Llamar al `optimize` del método y armar el diccionario de Spec §5.4.
#
# La semilla que se devuelve es la efectiva (Spec §5.4):
#
# $$\text{seed} = \text{base\_seed} + \text{run\_id}$$

# %%
def _validar_bool(valor, nombre: str) -> bool:
    """Devuelve `valor` como bool nativo; si no es bool lanza TypeError."""
    if not isinstance(valor, (bool, np.bool_)):
        raise TypeError(f"{nombre} debe ser bool; se recibió {valor!r} ({type(valor).__name__})")
    return bool(valor)


def _preparar_config(cfg: dict, method: str, grabar_frames: bool) -> dict:
    """Copia profunda de `cfg` con `record_frames` y, si el método es un GD, `variante`."""
    config = copy.deepcopy(cfg)
    config[CLAVE_RECORD_FRAMES] = grabar_frames
    if method in METODOS_GD:
        config[CLAVE_VARIANTE] = METODOS_GD[method]
    return config


def ejecutar_corrida(func: str, dim: int, method: str, base_seed: int, run_id: int, cfg: dict,
                     k: float | None = None,
                     presupuesto_por_dim: float = PRESUPUESTO_POR_DIM_DEFECTO,
                     grabar_frames: bool = False) -> dict:
    """Ejecuta una corrida y devuelve el diccionario de Spec §5.4.

    Parameters
    ----------
    func : str
        Identificador de la función (clave de `FUNCIONES`, p. ej. "rastrigin").
    dim : int
        Dimensión n (entero >= 1; la función puede exigir más).
    method : str
        Uno de `METODOS`.
    base_seed, run_id : int
        Enteros >= 0; el generador es `make_rng(base_seed, run_id)` (Spec §4.1).
    cfg : dict
        Configuración resuelta (p. ej. la de `configs/part1/base.yaml`). No se modifica.
    k : float | None
        Costo de un gradiente en evaluaciones de f. None = 2·dim (regla principal, §6.2).
    presupuesto_por_dim : float
        Evaluaciones equivalentes por dimensión; el presupuesto es `presupuesto_por_dim·dim`.
    grabar_frames : bool
        Valor que se fija en `record_frames`. Los optimizadores solo devuelven "frames" si
        además dim == 2 (§5.1). El `record_frames` que traiga `cfg` no se usa.

    Returns
    -------
    dict
        {"func", "dim", "method", "seed", "k", "budget", "config", "result"}:
        - "seed": semilla efectiva `base_seed + run_id` (int).
        - "k" y "budget": los que guarda `CountedProblem`, es decir float de Python
          (con k = None, "k" vale `float(2·dim)`, que es igual a `2·dim`).
        - "config": la copia profunda de `cfg` que recibió el optimizador.
        - "result": el retorno de `optimize` (§5.1), sin cambios.

    Raises
    ------
    TypeError
        `dim`, `base_seed` o `run_id` no enteros (o bool); `k` o `presupuesto_por_dim` no
        numéricos (o bool); `grabar_frames` no bool; `cfg` no es un dict.
    ValueError
        Enteros fuera de rango; `k` o `presupuesto_por_dim` no finitos o <= 0; `method` o
        `func` desconocidos; `dim` menor que el mínimo de la función.
    """
    # 1) Validaciones de los argumentos.
    dim = validar_entero(dim, "dim", minimo=DIMENSION_MINIMA)
    base_seed = validar_entero(base_seed, "base_seed")
    run_id = validar_entero(run_id, "run_id")
    if k is None:
        k = FACTOR_K_PRINCIPAL * dim
    k = validar_real(k, "k", 0, minimo_incluido=False)
    presupuesto_por_dim = validar_real(presupuesto_por_dim, "presupuesto_por_dim", 0,
                                       minimo_incluido=False)
    method = _validar_metodo(method)
    grabar_frames = _validar_bool(grabar_frames, "grabar_frames")
    if not isinstance(cfg, dict):
        raise TypeError(f"cfg debe ser un dict; se recibió {type(cfg).__name__}")

    # 2) Función (valida `func` y el mínimo de `dim`), problema contado y generador.
    funcion = get_function(func, dim)
    problem = CountedProblem(funcion, k, presupuesto_por_dim * dim)
    rng = make_rng(base_seed, run_id)

    # 3) Configuración de la corrida: copia de `cfg` con las claves que fija este módulo.
    config = _preparar_config(cfg, method, grabar_frames)

    # 4) Corrida y diccionario de Spec §5.4.
    result = obtener_optimizador(method)(problem, config, rng)
    return {
        "func": funcion.name,
        "dim": dim,
        "method": method,
        "seed": base_seed + run_id,
        "k": problem.k,
        "budget": problem.budget,
        "config": config,
        "result": result,
    }
