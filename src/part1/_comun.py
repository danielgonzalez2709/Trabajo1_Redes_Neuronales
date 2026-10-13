# %% [markdown]
# # Utilidades comunes a EA, PSO y DE de la Parte 1 (T1.6b; Spec §5.1, §6.2 y §6.4)
#
# **Propósito.** Reunir en un solo lugar lo que los tres métodos poblacionales (`ea.py`,
# `pso.py`, `de.py`) hacen igual: leer y validar su bloque de la configuración, validar formas,
# sortear y evaluar la población inicial, registrar frames y armar el retorno del contrato §5.1.
# Cada método importa de aquí y **no** de otro método; este archivo no importa a ninguno.
#
# "Común" significa común a las tres metaheurísticas de la Parte 1: no tiene relación con
# `src/common/` (contador, semillas y configuración, compartidos por las dos partes).
#
# **Mapa de utilidades** (funciones puras; cada una hace UNA sola cosa):
#
# | # | Utilidad | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `validar_real` | exige un real finito dentro de un intervalo | `float` |
# | 2 | `leer_bloque` | extrae `cfg[nombre]` (el bloque de un método) | mapeo |
# | 3 | `validar_claves_exactas` | exige un mapeo con exactamente unas claves | `None` |
# | 4 | `validar_limites` | exige un dominio $(d, 2)$ finito y ordenado | `(d, 2)` |
# | 5 | `validar_poblacion` | exige una matriz $(N, d)$ con $d \ge 1$ | `(N, d)` |
# | 6 | `exigir_forma` | exige una forma exacta | arreglo `float64` |
# | 7 | `generar_poblacion_inicial` | sortea $N$ puntos uniformes en el dominio | `(N, d)` |
# | 8 | `evaluar_poblacion` | aplica `f` a cada fila | `(N,)` |
# | 9 | `leer_record_frames` | extrae `cfg["record_frames"]` | `bool` |
# | 10 | `construir_frame` | arma un frame del contrato §5.1 | `dict` |
# | 11 | `construir_resultado` | arma el retorno de `optimize` (§5.1) | `dict` |
#
# **Azar.** Solo `generar_poblacion_inicial` consume azar, y lo toma del `rng` que recibe
# (Spec §4.1: un generador por corrida, con semilla `base_seed + run_id`). Nada global.

# %%
"""Utilidades comunes a EA, PSO y DE de la Parte 1: validaciones, población, frames, retorno."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

import numpy as np

from src.common.counter import CountedProblem
from src.common.seeds import validar_entero

# %% [markdown]
# ## Constantes del módulo (no son parámetros del experimento)

# %%
DIMENSION_CON_FRAMES = 2             # §5.1: los frames solo se guardan si dim == 2


# %% [markdown]
# ## 1. `validar_real`
#
# Los parámetros reales de los tres bloques (`frac_e`, `w`, `c1`, `F`, `CR`...) se validan con
# la misma regla, que solo cambia en el intervalo permitido:
#
# $$m \le x \;\;(\text{o } m < x), \qquad x \le M \;\;(\text{si hay máximo}), \qquad
#   x \text{ finito}$$
#
# El mínimo y el máximo se escriben en el mensaje de error tal como se reciben (`0` se lee
# "0" y `0.0` se lee "0.0").

# %%
def validar_real(valor, nombre: str, minimo: float, minimo_incluido: bool,
                 maximo: float | None = None) -> float:
    """Exige un real finito en el intervalo pedido; rechaza bool, texto, NaN e infinitos.

    `minimo_incluido=False` exige `valor > minimo`; `maximo`, si no es None, es inclusivo.
    Tipo incorrecto -> TypeError; no finito o fuera de rango -> ValueError (estilo counter.py).
    """
    # 1) Tipo: bool y texto no son reales aunque float() los acepte.
    es_numero = isinstance(valor, (int, float, np.integer, np.floating))
    if isinstance(valor, (bool, np.bool_)) or not es_numero:
        raise TypeError(f"{nombre} debe ser un número real; se recibió {valor!r} "
                        f"({type(valor).__name__})")
    numero = float(valor)

    # 2) Finito: descarta NaN, +inf y -inf antes de comparar con el rango.
    requisito = f"finito y {'>=' if minimo_incluido else '>'} {minimo}"
    if maximo is not None:
        requisito += f" y <= {maximo}"
    if not math.isfinite(numero):
        raise ValueError(f"{nombre} debe ser {requisito}; se recibió {valor!r}")

    # 3) Rango: mínimo (inclusivo o exclusivo) y, si se pidió, máximo inclusivo.
    por_debajo = numero < minimo if minimo_incluido else numero <= minimo
    por_encima = maximo is not None and numero > maximo
    if por_debajo or por_encima:
        raise ValueError(f"{nombre} debe ser {requisito}; se recibió {valor!r}")
    return numero


# %% [markdown]
# ## 2 y 3. `leer_bloque` y `validar_claves_exactas`
#
# Cada método tiene su bloque en la configuración (`ea:`, `pso:`, `de:`), definido completo en
# `configs/part1/base.yaml`. El código no tiene valores por defecto: si falta una clave o
# sobra una (un error de tecleo), se rechaza nombrándola.

# %%
def leer_bloque(cfg: Mapping, nombre: str) -> Mapping:
    """Extrae `cfg[nombre]`; si falta el bloque lanza ValueError con mensaje claro."""
    if nombre not in cfg:
        raise ValueError(f"falta el bloque '{nombre}' en la configuración (definido en "
                         "configs/part1/base.yaml)")
    return cfg[nombre]


def validar_claves_exactas(bloque: Mapping, claves: tuple, nombre: str) -> None:
    """Exige que el bloque `nombre` sea un mapeo con EXACTAMENTE las claves de `claves`.

    No es mapeo -> TypeError; falta de claves -> ValueError que las nombra; claves de más
    (typos) -> ValueError que las nombra junto con las válidas.
    """
    if not isinstance(bloque, Mapping):
        raise TypeError(f"el bloque '{nombre}' debe ser un mapeo; se recibió "
                        f"{type(bloque).__name__}")
    faltantes = [clave for clave in claves if clave not in bloque]
    sobrantes = [clave for clave in bloque if clave not in claves]
    if faltantes:
        raise ValueError(f"faltan claves en el bloque '{nombre}': {', '.join(faltantes)}")
    if sobrantes:
        raise ValueError(
            f"claves desconocidas en el bloque '{nombre}': {', '.join(map(str, sobrantes))}; "
            f"válidas: {', '.join(claves)}"
        )


# %% [markdown]
# ## 4, 5 y 6. Validaciones de forma
#
# Pequeñas funciones para no repetir comprobaciones de forma y tipo en los componentes.

# %%
def validar_limites(limites) -> np.ndarray:
    """Devuelve `limites` como arreglo float (d, 2) con [inferior, superior] por dimensión."""
    limites = np.asarray(limites, dtype=float)
    if limites.ndim != 2 or limites.shape[1] != 2 or limites.shape[0] < 1:
        raise ValueError(f"limites debe tener forma (d, 2); se recibió {limites.shape}")
    if not np.all(np.isfinite(limites)):
        raise ValueError("limites debe ser finito (sin NaN ni inf)")
    if np.any(limites[:, 0] > limites[:, 1]):
        raise ValueError("limites: el límite inferior no puede superar al superior")
    return limites


def validar_poblacion(poblacion, nombre: str = "poblacion") -> np.ndarray:
    """Devuelve `poblacion` como arreglo float (N, d); exige 2 dimensiones y d >= 1."""
    poblacion = np.asarray(poblacion, dtype=float)
    if poblacion.ndim != 2 or poblacion.shape[1] < 1:
        raise ValueError(f"{nombre} debe tener forma (N, d); se recibió {poblacion.shape}")
    return poblacion


def exigir_forma(arreglo, forma: tuple, nombre: str) -> np.ndarray:
    """Devuelve `arreglo` como float64 y exige que tenga exactamente `forma`."""
    # np.asarray NO copia si ya es float64 (devuelve el mismo objeto): valida pero no modifica.
    arreglo = np.asarray(arreglo, dtype=float)
    if arreglo.shape != forma:
        raise ValueError(f"{nombre} debe tener forma {forma}; se recibió {arreglo.shape}")
    return arreglo


# %% [markdown]
# ## 7. `generar_poblacion_inicial`
#
# Cada gen $j$ de cada individuo $i$ se sortea uniforme en el dominio de esa dimensión:
#
# $$x_{ij} \sim \mathcal{U}(l_j,\, u_j), \qquad i = 1,\dots,N,\quad j = 1,\dots,d$$
#
# donde $l_j, u_j$ son las columnas 0 y 1 de `limites` (forma $(d, 2)$).

# %%
def generar_poblacion_inicial(tamano: int, limites: np.ndarray,
                              rng: np.random.Generator) -> np.ndarray:
    """Sortea la población inicial: `tamano` puntos uniformes dentro del dominio.

    Es el punto de partida de la búsqueda: cuantos más puntos repartidos por todo el dominio,
    más regiones se exploran desde el principio (Spec §6.2: esta población CUENTA en el
    presupuesto cuando se evalúa).

    Parameters
    ----------
    tamano : int
        Número de individuos N (>= 1).
    limites : np.ndarray, forma (d, 2)
        Dominio: `limites[j] = [mínimo, máximo]` del gen j (como `problem.func.bounds`).
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    np.ndarray, forma (tamano, d), dtype float64
        Cada fila es un individuo; todos sus genes están dentro de `limites`.

    Notas
    -----
    Orden de consumo del rng: UNA sola llamada,
    `rng.uniform(limites_inferiores, limites_superiores, size=(tamano, d))`.
    """
    tamano = validar_entero(tamano, "tamano", minimo=1)
    limites = validar_limites(limites)

    limites_inferiores = limites[:, 0]   # forma (d,): el mínimo de cada gen
    limites_superiores = limites[:, 1]   # forma (d,): el máximo de cada gen
    dimension = limites.shape[0]

    # rng.uniform con límites de forma (d,) y size=(N, d): cada columna usa SU rango.
    poblacion = rng.uniform(limites_inferiores, limites_superiores, size=(tamano, dimension))
    return poblacion


# %% [markdown]
# ## 8. `evaluar_poblacion`
#
# Aplica la función objetivo a cada individuo (fila) y guarda su **aptitud**:
#
# $$a_i = f(x_i), \qquad i = 1,\dots,N \quad (\text{menor aptitud} = \text{mejor})$$
#
# Cada llamada a `evaluar_individuo` es UNA evaluación del presupuesto: `optimize` le pasa
# `problem.f`, que es quien cuenta y quien lanza `BudgetExhausted`.

# %%
def evaluar_poblacion(poblacion: np.ndarray,
                      evaluar_individuo: Callable[[np.ndarray], float]) -> np.ndarray:
    """Evalúa los individuos uno por uno, en orden de fila.

    Evaluar fila por fila (y no con una operación vectorizada) es lo que permite que
    `CountedProblem` cuente exactamente una evaluación por individuo y corte la generación
    en el punto exacto en que se agota el presupuesto (Spec §6.2).

    Parameters
    ----------
    poblacion : np.ndarray, forma (N, d)
        Individuos a evaluar; no se modifica.
    evaluar_individuo : Callable[[np.ndarray], float]
        Recibe una fila 1D de forma (d,) y devuelve su aptitud (p. ej. `problem.f`).
        Si lanza una excepción (p. ej. `BudgetExhausted`) se propaga tal cual.

    Returns
    -------
    np.ndarray, forma (N,), dtype float64
        `aptitudes[i]` es la aptitud de `poblacion[i]`.
    """
    poblacion = validar_poblacion(poblacion)
    numero_de_individuos = poblacion.shape[0]

    aptitudes = np.empty(numero_de_individuos, dtype=float)   # forma (N,), se llena abajo
    for fila in range(numero_de_individuos):
        individuo = poblacion[fila]                           # forma (d,): una fila
        aptitudes[fila] = evaluar_individuo(individuo)
    return aptitudes


# %% [markdown]
# ## 9 y 10. `leer_record_frames` y `construir_frame`
#
# Los frames alimentan las animaciones y solo se guardan en 2D
# (`DIMENSION_CON_FRAMES`) y si la configuración trae `record_frames: true`. Cada frame es la
# foto de una iteración: `{"iter", "positions", "best"}` (contrato §5.1).

# %%
def leer_record_frames(cfg: Mapping) -> bool:
    """Extrae `cfg["record_frames"]` (bool); falta -> ValueError, no bool -> TypeError."""
    if "record_frames" not in cfg:
        raise ValueError("falta la clave 'record_frames' en la configuración")
    valor = cfg["record_frames"]
    if not isinstance(valor, (bool, np.bool_)):
        raise TypeError(f"record_frames debe ser bool; se recibió {valor!r} "
                        f"({type(valor).__name__})")
    return bool(valor)


def construir_frame(iteracion: int, poblacion: np.ndarray, mejor_global: np.ndarray) -> dict:
    """Frame del contrato §5.1: {"iter", "positions" [[x, y], ...], "best" [x, y]}."""
    return {
        "iter": iteracion,
        "positions": poblacion.tolist(),
        "best": mejor_global.tolist(),
    }


# %% [markdown]
# ## 11. `construir_resultado`
#
# Los tres `optimize` terminan igual: leen del `CountedProblem` el mejor punto visto y los
# contadores (nadie cuenta a mano, Spec §6.2) y los devuelven con tipos nativos de Python:
#
# $$\text{eval\_equiv} = n_f + k\, n_{\text{grad}}$$
#
# La clave `frames` solo aparece si `guardar_frames` es verdadero.

# %%
def construir_resultado(problem: CountedProblem, frames: list[dict],
                        guardar_frames: bool) -> dict:
    """Arma el retorno de `optimize` (contrato §5.1) a partir del estado de `problem`.

    Parameters
    ----------
    problem : CountedProblem
        Problema ya usado por el optimizador: aporta `best_x`, `best_f`, `n_f`, `n_grad`,
        `eval_equiv()` e `history`. Debe haber aceptado al menos una evaluación de f.
    frames : list[dict]
        Frames registrados durante la corrida (ver `construir_frame`).
    guardar_frames : bool
        True: el retorno incluye la clave `frames` con la lista recibida; False: la omite.

    Returns
    -------
    dict
        `x_best` (list), `f_best` (float), `n_f` (int), `n_grad` (int), `eval_equiv` (float),
        `history` (copia de `problem.history`) y, solo si `guardar_frames`, `frames`.
    """
    resultado = {
        "x_best": problem.best_x.tolist(),
        "f_best": float(problem.best_f),
        "n_f": int(problem.n_f),
        "n_grad": int(problem.n_grad),
        "eval_equiv": float(problem.eval_equiv()),
        "history": [dict(punto) for punto in problem.history],
    }
    if guardar_frames:
        resultado["frames"] = frames
    return resultado
