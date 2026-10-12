# %% [markdown]
# # Algoritmo evolutivo (EA) de la Parte 1 — esquema de clase (Spec §6.4, v1.4)
#
# **Propósito.** Minimizar una función de prueba (Rosenbrock o Rastrigin) con una población de
# $N$ puntos de $\mathbb{R}^d$. En cada generación la población nueva se arma con tres grupos:
#
# $$P_{t+1} = \big[\; \text{élite} \;;\; \text{mutantes} \;;\; \text{hijos de cruce} \;\big]_{1:N}$$
#
# Sin selección por aptitud: la única presión de selección es la élite. La parada es por
# presupuesto de evaluaciones (Spec §6.2), no por número fijo de generaciones.
#
# **Mapa de componentes** (cada uno hace UNA sola cosa y recibe todo por parámetro):
#
# | # | Componente | Qué hace | Retorna |
# |---|---|---|---|
# | 0 | `ParametrosEA` | valida el bloque `ea:` y calcula los tamaños de los grupos | dataclass |
# | 1 | `generar_poblacion_inicial` | sortea $N$ puntos uniformes en el dominio | `(N, d)` |
# | 2 | `evaluar_poblacion` | aplica `f` a cada fila | `(N,)` |
# | 3 | `seleccionar_elite` | copia los $n_e$ mejores | `(elite, aptitudes_elite)` |
# | 4 | `mutar_individuos` | perturba UN gen de copias de individuos al azar | `ResultadoMutacion` |
# | 5 | `cruzar_individuos` | cruce de un punto entre parejas al azar | `ResultadoCruce` |
# | 6 | `ensamblar_nueva_generacion` | une élite + mutantes + hijos y recorta a $N$ | `(N, d)` |
# | 7 | `optimize` | orquestador: encadena 1-6 y lleva el conteo con `CountedProblem` | dict §5.1 |
#
# Fuente del esquema: material de clase IRNA202602, "intro algoritmos evolutivos"
# (https://colab.research.google.com/drive/1QvaXDJAPgiuQOuKcvZB-lpiRbPGqLHne).
#
# **Todo el azar** sale del `rng` que recibe `optimize` y que se inyecta a los componentes
# (Spec §4.1: un generador por corrida, con semilla `base_seed + run_id`). Nada global.

# %%
"""Algoritmo evolutivo de la Parte 1 (esquema de clase, Spec §6.4): componentes y orquestador."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from src.common.counter import BudgetExhausted, CountedProblem
from src.common.seeds import validar_entero

# %% [markdown]
# ## Constantes del módulo (no son parámetros del experimento)
#
# Los valores por defecto del experimento (N, fracciones...) viven SOLO en
# `configs/part1/base.yaml` (Spec §4.1). Aquí solo hay definiciones estructurales.

# %%
ESQUEMA_CLASE = "clase"              # único esquema implementado (Spec v1.4)
CLAVES_BLOQUE_EA = ("esquema", "N", "frac_e", "frac_m", "frac_c", "reevaluar_elite", "generaciones")
POBLACION_MINIMA = 2                 # con N < 2 no hay con quién cruzar (Spec §6.4, validación)
TAMANO_PAREJA = 2                    # cada pareja de padres produce 2 hijos
DIMENSION_CON_FRAMES = 2             # §5.1: los frames solo se guardan si dim == 2


# %% [markdown]
# ## 0. `ParametrosEA`: tamaños de los grupos
#
# Con $N$ individuos y las fracciones $f_e, f_m, f_c$ del bloque `ea:` se fijan los tamaños:
#
# $$n_e = \operatorname{round}(N f_e), \qquad n_m = \lfloor N f_m \rfloor, \qquad
#   \operatorname{par}(n) = n + (n \bmod 2)$$
#
# $$n_c = \max\Big(\operatorname{par}(\lfloor N f_c \rfloor),\;
#   \operatorname{par}(N - n_e - n_m)\Big)$$
#
# - `round` es el de Python (las mitades van al entero par: $7.5 \to 8$, $4.5 \to 4$).
# - $n_c$ es siempre par (se cruzan parejas) y el segundo término del máximo **rellena** cuando
#   $n_e + n_m + n_c < N$ (p. ej. $N=30$: $4+3+22 = 29$ sube $n_c$ a 24).
# - Si la suma excede $N$ (p. ej. $N=50$: $8+5+38 = 51$), `ensamblar_nueva_generacion` quita
#   hijos del final.
# - Restricciones: $n_e + n_m \le N$ y $n_c \le N$ (los cruzantes no se repiten).

# %%
def _validar_fraccion(valor, nombre: str) -> float:
    """Exige un número real finito y >= 0; rechaza bool, NaN e infinitos (estilo counter.py)."""
    es_numero = isinstance(valor, (int, float, np.integer, np.floating))
    if isinstance(valor, (bool, np.bool_)) or not es_numero:
        raise TypeError(f"{nombre} debe ser un número real; se recibió {valor!r} "
                        f"({type(valor).__name__})")
    fraccion = float(valor)
    if not (0.0 <= fraccion < math.inf):  # la comparación también rechaza NaN
        raise ValueError(f"{nombre} debe ser finito y >= 0; se recibió {valor!r}")
    return fraccion


def _siguiente_par(cantidad: int) -> int:
    """Menor número par que es >= cantidad (par hacia arriba)."""
    return cantidad + cantidad % 2


def _validar_claves_del_bloque(cfg_ea: Mapping) -> None:
    """Exige que el bloque `ea:` sea un mapeo con EXACTAMENTE las claves de CLAVES_BLOQUE_EA.

    Falta de claves -> ValueError que las nombra; claves de más (typos) -> ValueError.
    """
    if not isinstance(cfg_ea, Mapping):
        raise TypeError(f"el bloque 'ea' debe ser un mapeo; se recibió "
                        f"{type(cfg_ea).__name__}")
    faltantes = [clave for clave in CLAVES_BLOQUE_EA if clave not in cfg_ea]
    sobrantes = [clave for clave in cfg_ea if clave not in CLAVES_BLOQUE_EA]
    if faltantes:
        raise ValueError(f"faltan claves en el bloque 'ea': {', '.join(faltantes)}")
    if sobrantes:
        raise ValueError(
            f"claves desconocidas en el bloque 'ea': {', '.join(map(str, sobrantes))}; "
            f"válidas: {', '.join(CLAVES_BLOQUE_EA)}"
        )


def _validar_valores_del_bloque(cfg_ea: Mapping) -> tuple:
    """Valida esquema, tipos y rangos de cada valor del bloque `ea:` (ya con sus claves).

    Returns
    -------
    tuple
        `(tamano, fraccion_elite, fraccion_mutantes, fraccion_cruce, reevaluar_elite,
        generaciones)` con tipos nativos de Python.
    """
    # El esquema debe ser el único implementado.
    if cfg_ea["esquema"] != ESQUEMA_CLASE:
        raise ValueError(
            f"ea.esquema={cfg_ea['esquema']!r} no está implementado: solo existe "
            f"{ESQUEMA_CLASE!r} (Spec v1.4)"
        )

    tamano = validar_entero(cfg_ea["N"], "ea.N", minimo=POBLACION_MINIMA)
    fraccion_elite = _validar_fraccion(cfg_ea["frac_e"], "ea.frac_e")
    fraccion_mutantes = _validar_fraccion(cfg_ea["frac_m"], "ea.frac_m")
    fraccion_cruce = _validar_fraccion(cfg_ea["frac_c"], "ea.frac_c")

    reevaluar_elite = cfg_ea["reevaluar_elite"]
    if not isinstance(reevaluar_elite, (bool, np.bool_)):
        raise TypeError(f"ea.reevaluar_elite debe ser bool; se recibió {reevaluar_elite!r} "
                        f"({type(reevaluar_elite).__name__})")

    generaciones = cfg_ea["generaciones"]
    if generaciones is not None:
        generaciones = validar_entero(generaciones, "ea.generaciones", minimo=0)

    return (tamano, fraccion_elite, fraccion_mutantes, fraccion_cruce, bool(reevaluar_elite),
            generaciones)


def _calcular_tamanos_de_grupos(tamano: int, fraccion_elite: float, fraccion_mutantes: float,
                                fraccion_cruce: float,
                                reevaluar_elite: bool) -> tuple[int, int, int]:
    """Calcula `(n_elite, n_mutantes, n_cruzantes)` con las fórmulas de la celda anterior.

    Lanza ValueError si `n_elite + n_mutantes > tamano`, si `n_cruzantes > tamano` o si toda la
    población es élite sin reevaluación (ninguna generación evaluaría individuos nuevos).
    """
    n_elite = round(tamano * fraccion_elite)
    n_mutantes = int(tamano * fraccion_mutantes)
    if n_elite + n_mutantes > tamano:
        raise ValueError(
            f"n_elite + n_mutantes = {n_elite} + {n_mutantes} excede N = {tamano} "
            f"(frac_e={fraccion_elite}, frac_m={fraccion_mutantes})"
        )

    n_cruzantes_por_fraccion = _siguiente_par(int(tamano * fraccion_cruce))
    n_cruzantes_para_rellenar = _siguiente_par(tamano - n_elite - n_mutantes)
    n_cruzantes = max(n_cruzantes_por_fraccion, n_cruzantes_para_rellenar)
    if n_cruzantes > tamano:
        raise ValueError(
            f"n_cruzantes = {n_cruzantes} excede N = {tamano}: los cruzantes se eligen sin "
            f"repetir y deben formar parejas (frac_c={fraccion_cruce})"
        )
    if n_elite == tamano and not reevaluar_elite:
        raise ValueError(
            f"toda la población es élite (n_elite = N = {tamano}) y reevaluar_elite=false: "
            "ninguna generación evaluaría individuos nuevos"
        )
    return n_elite, n_mutantes, n_cruzantes


@dataclass(frozen=True)
class ParametrosEA:
    """Parámetros validados del EA y tamaños derivados de los grupos (Spec §6.4).

    Se construye SIEMPRE con `ParametrosEA.desde_config(cfg["ea"])`, que valida el bloque y
    calcula `n_elite`, `n_mutantes` y `n_cruzantes` con las fórmulas de la celda anterior. Es
    importante porque es el único lugar que interpreta el bloque `ea:` de la configuración:
    el resto de componentes solo reciben enteros.

    Attributes
    ----------
    tamano_poblacion : int
        N, número de individuos por generación (>= 2).
    fraccion_elite, fraccion_mutantes, fraccion_cruce : float
        `frac_e`, `frac_m`, `frac_c` de la config (fracciones de N, >= 0).
    reevaluar_elite : bool
        False: la élite conserva su aptitud y no cuesta evaluaciones.
    generaciones : int | None
        None: parar solo por presupuesto (§6.2); entero >= 0: parar antes.
    n_elite, n_mutantes, n_cruzantes : int
        Tamaños de los grupos; `n_cruzantes` es siempre par.
    """

    tamano_poblacion: int
    fraccion_elite: float
    fraccion_mutantes: float
    fraccion_cruce: float
    reevaluar_elite: bool
    generaciones: int | None
    n_elite: int
    n_mutantes: int
    n_cruzantes: int

    @classmethod
    def desde_config(cls, cfg_ea: Mapping) -> ParametrosEA:
        """Valida el bloque `ea:` de la configuración y calcula los tamaños de los grupos.

        Parameters
        ----------
        cfg_ea : Mapping
            Bloque `ea:` con EXACTAMENTE las claves `esquema`, `N`, `frac_e`, `frac_m`,
            `frac_c`, `reevaluar_elite` y `generaciones` (no hay valores por defecto en el
            código: viven en `configs/part1/base.yaml`).

        Returns
        -------
        ParametrosEA
            Instancia congelada con los parámetros y los tamaños de los grupos.

        Raises
        ------
        TypeError
            Si `cfg_ea` no es un mapeo o algún valor tiene un tipo incorrecto (bool donde se
            espera número, float donde se espera entero, etc.).
        ValueError
            Si faltan claves o sobran (typos), si `esquema` no es "clase", si N < 2, si una
            fracción es negativa/NaN/inf, si `n_elite + n_mutantes > N`, si `n_cruzantes > N` o
            si toda la población es élite sin reevaluación (ninguna generación evaluaría nada).
        """
        _validar_claves_del_bloque(cfg_ea)
        (tamano, fraccion_elite, fraccion_mutantes, fraccion_cruce, reevaluar_elite,
         generaciones) = _validar_valores_del_bloque(cfg_ea)
        n_elite, n_mutantes, n_cruzantes = _calcular_tamanos_de_grupos(
            tamano, fraccion_elite, fraccion_mutantes, fraccion_cruce, reevaluar_elite
        )
        return cls(
            tamano_poblacion=tamano,
            fraccion_elite=fraccion_elite,
            fraccion_mutantes=fraccion_mutantes,
            fraccion_cruce=fraccion_cruce,
            reevaluar_elite=reevaluar_elite,
            generaciones=generaciones,
            n_elite=n_elite,
            n_mutantes=n_mutantes,
            n_cruzantes=n_cruzantes,
        )


# %% [markdown]
# ## Validaciones compartidas por los componentes
#
# Pequeñas funciones para no repetir comprobaciones de forma y tipo (se reutilizan en `pso.py`).

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


# %% [markdown]
# ## 1. `generar_poblacion_inicial`
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
# ## 2. `evaluar_poblacion`
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
# ## 3. `seleccionar_elite`
#
# Con $\pi$ la permutación que ordena las aptitudes de menor a mayor (**orden estable**: ante un
# empate va primero el índice menor), la élite son las $n_e$ primeras filas:
#
# $$a_{\pi(1)} \le a_{\pi(2)} \le \dots \le a_{\pi(N)}, \qquad
#   E = \big[x_{\pi(1)};\ \dots;\ x_{\pi(n_e)}\big]$$
#
# La élite se calcula SIEMPRE con las aptitudes de la población **actual**: el cuaderno de clase
# ordenaba con las aptitudes de la población inicial; aquí se usan las actuales
# (docs/spec/propuestas/CAMBIO-EA.md §8). Se devuelven **copias**.

# %%
def seleccionar_elite(poblacion: np.ndarray, aptitudes: np.ndarray,
                      n_elite: int) -> tuple[np.ndarray, np.ndarray]:
    """Copia los `n_elite` individuos de menor aptitud, ordenados de mejor a peor.

    La élite es la única presión de selección del esquema de clase: pasa intacta a la siguiente
    generación, así el mejor punto encontrado nunca se pierde (elitismo).

    Parameters
    ----------
    poblacion : np.ndarray, forma (N, d)
        Población actual; no se modifica.
    aptitudes : np.ndarray, forma (N,)
        Aptitud de cada fila de `poblacion` (menor = mejor).
    n_elite : int
        Cuántos individuos copiar; 0 <= n_elite <= N.

    Returns
    -------
    elite : np.ndarray, forma (n_elite, d)
        Copias de los mejores individuos, del mejor al peor.
    aptitudes_elite : np.ndarray, forma (n_elite,)
        Aptitud de cada fila de `elite` (alineada con ella).
    """
    poblacion = validar_poblacion(poblacion)
    aptitudes = np.asarray(aptitudes, dtype=float)
    n_elite = validar_entero(n_elite, "n_elite", minimo=0)
    numero_de_individuos = poblacion.shape[0]
    if aptitudes.shape != (numero_de_individuos,):
        raise ValueError(f"aptitudes debe tener forma ({numero_de_individuos},); "
                         f"se recibió {aptitudes.shape}")
    if n_elite > numero_de_individuos:
        raise ValueError(f"n_elite = {n_elite} excede el tamaño de la población "
                         f"({numero_de_individuos})")

    # np.argsort devuelve los ÍNDICES que ordenan de menor a mayor; kind="stable" conserva el
    # orden original entre empates (reproducible).
    indices_de_mejor_a_peor = np.argsort(aptitudes, kind="stable")   # forma (N,)
    indices_elite = indices_de_mejor_a_peor[:n_elite]                # forma (n_elite,)

    # Indexar con un arreglo de índices crea COPIAS (no vistas): modificar la élite no altera
    # la población original.
    elite = poblacion[indices_elite]                                 # forma (n_elite, d)
    aptitudes_elite = aptitudes[indices_elite]                       # forma (n_elite,)
    return elite, aptitudes_elite


# %% [markdown]
# ## 4. `mutar_individuos`
#
# Se eligen $n_m$ individuos al azar **sin repetir** (de toda la población, sin ordenar) y se
# muta una **copia** de cada uno: a **un** gen $g_k$ elegido al azar se le suma ruido gaussiano
# escalado por la desviación estándar poblacional de ese gen en la generación actual:
#
# $$\sigma_j = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\big(x_{ij} - \bar{x}_j\big)^2}
#   \quad(\text{ddof}=0)$$
#
# $$x'_{k,g_k} = \operatorname{clip}\big(x_{k,g_k} + \sigma_{g_k}\, z_k,\; l_{g_k},\; u_{g_k}\big),
#   \qquad z_k \sim \mathcal{N}(0, 1)$$
#
# Los demás genes del mutante quedan idénticos a los de su origen. Cuando la población converge,
# $\sigma_j \to 0$ y la mutación se apaga (comportamiento a discutir en el blog).

# %%
class ResultadoMutacion(NamedTuple):
    """Salida de `mutar_individuos`: permite identificar qué se mutó y de quién.

    mutantes       : (n_mutantes, d) los individuos mutados.
    indices_origen : (n_mutantes,) fila de la población de la que se copió cada mutante.
    genes_mutados  : (n_mutantes,) columna (gen) perturbada en cada mutante.
    """

    mutantes: np.ndarray
    indices_origen: np.ndarray
    genes_mutados: np.ndarray


def mutar_individuos(poblacion: np.ndarray, n_mutantes: int, limites: np.ndarray,
                     rng: np.random.Generator) -> ResultadoMutacion:
    """Crea `n_mutantes` mutantes: copias de individuos al azar con UN gen perturbado.

    Es el componente de exploración local del EA: aporta variedad cerca de puntos ya
    existentes, con un tamaño de salto que se adapta solo (sigma poblacional por gen).

    Parameters
    ----------
    poblacion : np.ndarray, forma (N, d)
        Población actual COMPLETA y sin ordenar; no se modifica (se mutan copias).
    n_mutantes : int
        Cuántos mutantes crear; 0 <= n_mutantes <= N.
    limites : np.ndarray, forma (d, 2)
        Dominio `[mínimo, máximo]` por gen; el gen mutado se recorta a su rango.
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    ResultadoMutacion
        `mutantes` (n_mutantes, d); `indices_origen` (n_mutantes,) filas de `poblacion` de las
        que se copió, sin repetir; `genes_mutados` (n_mutantes,) gen perturbado en cada mutante.

    Notas
    -----
    Orden de consumo del rng (fijo):
    (1) `rng.choice(N, size=n_mutantes, replace=False)` -> `indices_origen`;
    (2) `rng.integers(0, d, size=n_mutantes)` -> `genes_mutados`;
    (3) `rng.standard_normal(size=n_mutantes)` -> ruido N(0, 1), que se escala por sigma.
    Con `n_mutantes = 0` no se consume azar.
    """
    poblacion = validar_poblacion(poblacion)
    limites = validar_limites(limites)
    n_mutantes = validar_entero(n_mutantes, "n_mutantes", minimo=0)
    numero_de_individuos, dimension = poblacion.shape
    if limites.shape[0] != dimension:
        raise ValueError(f"limites describe {limites.shape[0]} dimensiones pero la población "
                         f"tiene {dimension}")
    if n_mutantes > numero_de_individuos:
        raise ValueError(f"n_mutantes = {n_mutantes} excede el tamaño de la población "
                         f"({numero_de_individuos})")

    if n_mutantes == 0:
        return ResultadoMutacion(
            mutantes=np.empty((0, dimension), dtype=float),
            indices_origen=np.empty(0, dtype=np.int64),
            genes_mutados=np.empty(0, dtype=np.int64),
        )

    # Desviación estándar de cada columna (gen) sobre la población completa; ddof=0 = poblacional.
    desviacion_por_gen = poblacion.std(axis=0, ddof=0)               # forma (d,)

    # (1) Qué individuos se mutan: sin repetir.
    indices_origen = rng.choice(numero_de_individuos, size=n_mutantes, replace=False)
    # (2) Qué gen (columna) se perturba en cada mutante.
    genes_mutados = rng.integers(0, dimension, size=n_mutantes)
    # (3) Ruido N(0, 1), uno por mutante.
    ruido_estandar = rng.standard_normal(size=n_mutantes)

    # Copias de los individuos elegidos (indexar con un arreglo crea una copia).
    mutantes = poblacion[indices_origen]                             # forma (n_mutantes, d)

    # Cada mutante cambia UN solo valor: el del gen que le tocó.
    for k in range(n_mutantes):
        gen = genes_mutados[k]
        valor_nuevo = mutantes[k, gen] + ruido_estandar[k] * desviacion_por_gen[gen]
        limite_inferior, limite_superior = limites[gen]
        # np.clip recorta el valor al rango [límite_inferior, límite_superior] de ese gen.
        mutantes[k, gen] = np.clip(valor_nuevo, limite_inferior, limite_superior)

    return ResultadoMutacion(mutantes=mutantes, indices_origen=indices_origen,
                             genes_mutados=genes_mutados)


# %% [markdown]
# ## 5. `cruzar_individuos`
#
# Se eligen $n_c$ individuos al azar **sin repetir** y **sin mirar su aptitud**; el orden sorteado
# los "baraja". Con $m = n_c / 2$, la pareja $k$ es $(\text{cruzante}_k,\ \text{cruzante}_{k+m})$:
# el primero es el **padre** $p$ y el segundo la **madre** $q$. Cada pareja sortea un punto de
# corte $c_k \in \{1, \dots, d-1\}$ (nunca 0 ni $d$) y produce dos hijos:
#
# $$h^{(1)} = \big(p_1,\dots,p_{c},\; q_{c+1},\dots,q_d\big), \qquad
#   h^{(2)} = \big(q_1,\dots,q_{c},\; p_{c+1},\dots,p_d\big)$$
#
# Fila $2k$ de `hijos` = $h^{(1)}$ de la pareja $k$; fila $2k+1$ = $h^{(2)}$. En 2D el único corte
# posible es $c = 1$: los hijos solo intercambian coordenadas (a discutir en el blog). El corte 0
# daría un hijo idéntico a la madre (el cuaderno de clase lo permitía; aquí no).

# %%
class ResultadoCruce(NamedTuple):
    """Salida de `cruzar_individuos`: de cada hijo se deducen sus padres y su punto de corte.

    hijos         : (n_cruzantes, d) fila 2k = hijo 1 de la pareja k, fila 2k+1 = hijo 2.
    indices_padre : (n_cruzantes // 2,) fila de la población del padre de cada pareja.
    indices_madre : (n_cruzantes // 2,) fila de la población de la madre de cada pareja.
    puntos_corte  : (n_cruzantes // 2,) punto de corte de cada pareja, en {1, ..., d-1}.
    """

    hijos: np.ndarray
    indices_padre: np.ndarray
    indices_madre: np.ndarray
    puntos_corte: np.ndarray


def cruzar_individuos(poblacion: np.ndarray, n_cruzantes: int,
                      rng: np.random.Generator) -> ResultadoCruce:
    """Cruce de un punto entre parejas de individuos elegidos al azar.

    Es el componente de recombinación del EA: mezcla información de dos puntos distintos de la
    población para proponer puntos nuevos que ninguno de los dos padres tenía.

    Parameters
    ----------
    poblacion : np.ndarray, forma (N, d)
        Población actual COMPLETA y sin ordenar; no se modifica. Requiere d >= 2.
    n_cruzantes : int
        Individuos que se cruzan; debe ser PAR y 0 <= n_cruzantes <= N.
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    ResultadoCruce
        `hijos` (n_cruzantes, d), 2 por pareja (fila 2k = hijo 1, fila 2k+1 = hijo 2);
        `indices_padre`, `indices_madre` y `puntos_corte`, cada uno de forma
        (n_cruzantes // 2,), uno por PAREJA.

    Notas
    -----
    Orden de consumo del rng (fijo):
    (1) `rng.choice(N, size=n_cruzantes, replace=False)` -> cruzantes (su orden ya "baraja");
    (2) `rng.integers(1, d, size=n_cruzantes // 2)` -> puntos de corte en {1, ..., d-1}.
    Con `n_cruzantes = 0` no se consume azar.
    """
    poblacion = validar_poblacion(poblacion)
    n_cruzantes = validar_entero(n_cruzantes, "n_cruzantes", minimo=0)
    numero_de_individuos, dimension = poblacion.shape
    if n_cruzantes % 2 != 0:
        raise ValueError(f"n_cruzantes debe ser par (parejas); se recibió {n_cruzantes}")
    if dimension < 2:
        raise ValueError(f"el cruce de un punto requiere d >= 2; la población tiene d = "
                         f"{dimension}")
    if n_cruzantes > numero_de_individuos:
        raise ValueError(f"n_cruzantes = {n_cruzantes} excede el tamaño de la población "
                         f"({numero_de_individuos})")

    if n_cruzantes == 0:
        return ResultadoCruce(
            hijos=np.empty((0, dimension), dtype=float),
            indices_padre=np.empty(0, dtype=np.int64),
            indices_madre=np.empty(0, dtype=np.int64),
            puntos_corte=np.empty(0, dtype=np.int64),
        )

    numero_de_parejas = n_cruzantes // 2

    # (1) Cruzantes sin repetir; el orden sorteado decide quién es padre y quién madre.
    indices_cruzantes = rng.choice(numero_de_individuos, size=n_cruzantes, replace=False)
    indices_padre = indices_cruzantes[:numero_de_parejas]            # primera mitad
    indices_madre = indices_cruzantes[numero_de_parejas:]            # segunda mitad

    # (2) Un punto de corte por pareja, en {1, ..., d-1}: el límite superior de `integers` no
    # se incluye y el 0 se excluye a propósito (ver la celda markdown).
    puntos_corte = rng.integers(1, dimension, size=numero_de_parejas)

    # Cada pareja produce 2 hijos; se guardan en filas consecutivas (2k y 2k + 1).
    hijos = np.empty((n_cruzantes, dimension), dtype=float)
    for k in range(numero_de_parejas):
        padre = poblacion[indices_padre[k]]                          # forma (d,)
        madre = poblacion[indices_madre[k]]                          # forma (d,)
        corte = puntos_corte[k]
        # np.concatenate une dos trozos de fila en una sola fila de d valores.
        hijos[TAMANO_PAREJA * k] = np.concatenate([padre[:corte], madre[corte:]])
        hijos[TAMANO_PAREJA * k + 1] = np.concatenate([madre[:corte], padre[corte:]])

    return ResultadoCruce(hijos=hijos, indices_padre=indices_padre, indices_madre=indices_madre,
                          puntos_corte=puntos_corte)


# %% [markdown]
# ## 6. `ensamblar_nueva_generacion`
#
# La nueva población apila los tres grupos **en este orden** y conserva las primeras $N$ filas:
#
# $$P_{t+1} = \begin{bmatrix} E \\ M \\ H \end{bmatrix}_{1:N}, \qquad
#   n_e + n_m \le N \le n_e + n_m + n_c$$
#
# Si sobran filas se quitan las **últimas de hijos**: nunca élite ni mutantes. Si faltan, es un
# error de configuración (no se inventan individuos).

# %%
def ensamblar_nueva_generacion(elite: np.ndarray, mutantes: np.ndarray, hijos: np.ndarray,
                               tamano: int) -> np.ndarray:
    """Une élite, mutantes e hijos (en ese orden) y recorta por el final a `tamano` filas.

    Mantiene el tamaño de la población constante en N. Poner la élite primero permite que
    `optimize` reconozca sus filas (las primeras `n_elite`) y les conserve la aptitud sin
    reevaluarlas, lo que ahorra evaluaciones (Spec §6.2).

    Parameters
    ----------
    elite : np.ndarray, forma (n_elite, d)
    mutantes : np.ndarray, forma (n_mutantes, d)
    hijos : np.ndarray, forma (n_hijos, d)
        Los tres grupos pueden tener 0 filas; ninguno se modifica.
    tamano : int
        N, filas de la nueva población.

    Returns
    -------
    np.ndarray, forma (tamano, d)
        Arreglo nuevo (no comparte memoria con las entradas).

    Raises
    ------
    ValueError
        Si las dimensiones d no coinciden, si faltan filas (élite + mutantes + hijos < tamano)
        o si élite + mutantes ya superan `tamano`.
    """
    elite = validar_poblacion(elite, "elite")
    mutantes = validar_poblacion(mutantes, "mutantes")
    hijos = validar_poblacion(hijos, "hijos")
    tamano = validar_entero(tamano, "tamano", minimo=1)
    dimensiones = {elite.shape[1], mutantes.shape[1], hijos.shape[1]}
    if len(dimensiones) != 1:
        raise ValueError(f"elite, mutantes e hijos deben tener el mismo d; se recibieron "
                         f"{elite.shape[1]}, {mutantes.shape[1]} y {hijos.shape[1]}")

    filas_que_no_se_pueden_quitar = elite.shape[0] + mutantes.shape[0]
    filas_disponibles = filas_que_no_se_pueden_quitar + hijos.shape[0]
    if filas_que_no_se_pueden_quitar > tamano:
        raise ValueError(f"élite + mutantes = {filas_que_no_se_pueden_quitar} filas exceden "
                         f"tamano = {tamano}; no se recortan élite ni mutantes")
    if filas_disponibles < tamano:
        raise ValueError(f"faltan filas: élite + mutantes + hijos = {filas_disponibles} < "
                         f"tamano = {tamano}")

    # np.vstack apila los arreglos uno debajo de otro (por filas) y devuelve un arreglo nuevo.
    todos_los_individuos = np.vstack([elite, mutantes, hijos])       # (disponibles, d)
    nueva_poblacion = todos_los_individuos[:tamano]                  # quita las últimas filas
    return nueva_poblacion


# %% [markdown]
# ## 7. `optimize`: el orquestador
#
# Encadena los componentes siguiendo el Spec §6.4. Con $T$ generaciones completadas y la élite
# sin reevaluar, el conteo de evaluaciones es exacto:
#
# $$n_f = N + T\,(N - n_e), \qquad n_{\text{grad}} = 0, \qquad \text{eval\_equiv} = n_f$$
#
# (con `reevaluar_elite: true`, $n_f = N\,(T+1)$). El presupuesto $B$ corta la corrida: la
# generación que no cabe se trunca en la evaluación exacta que lo excedería
# (`BudgetExhausted`), se descarta sin registrar frame y se devuelve el mejor punto visto.
# Con $B = 20\,000$ en 2D: $50 + 42 \cdot 475 = 20\,000$ (475 generaciones, exacto).

# %%
def _leer_bloque_ea(cfg: Mapping) -> Mapping:
    """Extrae `cfg["ea"]`; si falta el bloque lanza ValueError con mensaje claro."""
    if "ea" not in cfg:
        raise ValueError("falta el bloque 'ea' en la configuración (definido en "
                         "configs/part1/base.yaml)")
    return cfg["ea"]


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


def _evaluar_generacion(nueva_poblacion: np.ndarray, aptitudes_elite: np.ndarray,
                        parametros: ParametrosEA,
                        evaluar_individuo: Callable[[np.ndarray], float]) -> np.ndarray:
    """Devuelve las aptitudes (N,) de la nueva población, evaluando solo lo necesario.

    Si `reevaluar_elite` es False, la élite (las primeras `n_elite` filas) conserva la aptitud
    que ya tenía y solo se evalúan las filas posteriores: ahorra `n_elite` evaluaciones por
    generación (Spec §6.2). Si es True, se evalúan las N filas.
    """
    if parametros.reevaluar_elite:
        return evaluar_poblacion(nueva_poblacion, evaluar_individuo)

    filas_nuevas = nueva_poblacion[parametros.n_elite:]              # forma (N - n_elite, d)
    aptitudes_filas_nuevas = evaluar_poblacion(filas_nuevas, evaluar_individuo)
    return np.concatenate([aptitudes_elite, aptitudes_filas_nuevas])


def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Ejecuta el EA de clase sobre `problem` hasta agotar el presupuesto (o `generaciones`).

    Es el único componente que conoce `CountedProblem` y la configuración completa: lee el
    dominio y la dimensión de `problem.func`, delega cada fase en un componente y deja que
    `CountedProblem` cuente (nunca se cuenta a mano, Spec §6.2).

    Parameters
    ----------
    problem : CountedProblem
        Función envuelta con su contador y presupuesto; debe admitir al menos 1 evaluación.
    cfg : dict
        Configuración ya cargada: `cfg["ea"]` (bloque de parámetros) y `cfg["record_frames"]`.
    rng : np.random.Generator
        Única fuente de azar; se inyecta a la población inicial, la mutación y el cruce.

    Returns
    -------
    dict
        Contrato §5.1: `x_best` (list), `f_best` (float), `n_f` (int), `n_grad` (int, siempre
        0), `eval_equiv` (float), `history` (copia de `problem.history`) y, solo si
        `problem.func.dim == 2` y `cfg["record_frames"]`, `frames`: un frame por generación
        completada (iter 0 = población inicial) con `best` = mejor punto GLOBAL hasta entonces.

    Raises
    ------
    ValueError
        Configuración inválida (ver `ParametrosEA.desde_config`), falta `ea` o
        `record_frames`, o presupuesto que no alcanza para ninguna evaluación.
    """
    # Paso 1: validar la configuración y leer el dominio del problema.
    parametros = ParametrosEA.desde_config(_leer_bloque_ea(cfg))
    guardar_frames = leer_record_frames(cfg) and problem.func.dim == DIMENSION_CON_FRAMES
    limites = validar_limites(problem.func.bounds)                  # forma (d, 2)
    if problem.budget_exhausted():
        raise ValueError(f"el presupuesto ({problem.budget}) no alcanza para ninguna "
                         "evaluación de f")

    frames: list[dict] = []

    # Un solo try/except: si el presupuesto se agota en cualquier evaluación, la generación
    # incompleta se descarta y se devuelve el mejor punto visto (patrón Spec §5.1, T0.4).
    try:
        # Paso 2: población inicial uniforme en el dominio.
        poblacion = generar_poblacion_inicial(parametros.tamano_poblacion, limites, rng)

        # Paso 3: evaluarla (cuenta N evaluaciones, Spec §6.2) y registrar el frame iter 0.
        aptitudes = evaluar_poblacion(poblacion, problem.f)          # forma (N,)
        if guardar_frames:
            frames.append(construir_frame(0, poblacion, problem.best_x))

        generacion = 0
        while parametros.generaciones is None or generacion < parametros.generaciones:
            generacion += 1

            # Paso 4: élite de la población ACTUAL con sus aptitudes actuales.
            elite, aptitudes_elite = seleccionar_elite(poblacion, aptitudes, parametros.n_elite)

            # Paso 5: mutantes (copias de individuos al azar, un gen perturbado).
            mutacion = mutar_individuos(poblacion, parametros.n_mutantes, limites, rng)

            # Paso 6: hijos de cruce de un punto (primero se muta y luego se cruza: orden fijo
            # del consumo del rng).
            cruce = cruzar_individuos(poblacion, parametros.n_cruzantes, rng)

            # Paso 7: nueva generación = élite + mutantes + hijos, recortada a N.
            poblacion = ensamblar_nueva_generacion(
                elite, mutacion.mutantes, cruce.hijos, parametros.tamano_poblacion
            )

            # Paso 8: evaluar la nueva generación (la élite conserva su aptitud) y registrar
            # su frame.
            aptitudes = _evaluar_generacion(poblacion, aptitudes_elite, parametros, problem.f)
            if guardar_frames:
                frames.append(construir_frame(generacion, poblacion, problem.best_x))
    except BudgetExhausted:
        # Presupuesto agotado: no se hace nada más. La generación incompleta no registra frame y
        # el mejor punto visto está en problem.best_x / problem.best_f.
        pass

    # Paso 9: armar el retorno del contrato §5.1 con tipos nativos de Python.
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
