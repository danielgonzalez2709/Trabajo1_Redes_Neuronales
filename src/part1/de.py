# %% [markdown]
# # Evolución diferencial DE/rand/1/bin de la Parte 1 (Spec §6.4)
#
# **Propósito.** Minimizar una función de prueba (Rosenbrock o Rastrigin) con una población de
# $NP$ individuos en $\mathbb{R}^d$. En lugar de sumar ruido gaussiano (como el EA), la
# evolución diferencial construye cada candidato con la **diferencia entre dos individuos**:
# el tamaño y la dirección del paso se adaptan solos a la dispersión de la población.
#
# **Ciclo** (matrices de forma $(NP, d)$, una fila por individuo; menor $f$ = mejor):
#
# $$\text{Inicialización} \to \text{Evaluación} \to
#   \underbrace{\text{Padres} \to \text{Mutación} \to \text{Reinicio} \to \text{Cruce}
#   \to \text{Evaluación} \to \text{Selección}}_{\text{una generación}}$$
#
# El esquema es **síncrono**: todos los hijos de una generación se construyen con la población
# que había al *inicio* de esa generación; después se evalúan y se selecciona.
#
# **Mapa de componentes** (cada uno hace UNA sola cosa y recibe todo por parámetro):
#
# | # | Componente | Qué hace | Retorna |
# |---|---|---|---|
# | 0 | `ParametrosDE` | valida el bloque `de:` de la configuración | dataclass |
# | 1 | `generar_poblacion_inicial` | (de `_comun.py`) sortea $NP$ puntos uniformes | `(NP, d)` |
# | 2 | `evaluar_poblacion` | (de `_comun.py`) aplica `f` a cada fila | `(NP,)` |
# | 3 | `sortear_padres` | tres padres $r_1, r_2, r_3$ distintos entre sí y de $i$ | `(NP, 3)` |
# | 4 | `mutar_diferencial` | $v_i = x_{r_1} + F\,(x_{r_2} - x_{r_3})$ | `(NP, d)` |
# | 5 | `reiniciar_fuera_de_dominio` | re-sortea lo que sale de $[l_j, u_j]$ | `ResultadoReinicio` |
# | 6 | `cruzar_binomial` | mezcla padre y mutante, con $j_{\text{rand}}$ | `ResultadoCruce` |
# | 7 | `seleccionar_codiciosa` | el hijo reemplaza al padre si no es peor | `ResultadoSeleccion` |
# | 8 | `optimize` | orquestador: encadena 1-7; cuenta con `CountedProblem` | dict §5.1 |
#
# **Todo el azar** sale del `rng` que recibe `optimize` y que se inyecta a los componentes
# (Spec §4.1: un generador por corrida, con semilla `base_seed + run_id`). Nada global.
#
# **Orden de consumo del rng** (fijo): (1) `rng.uniform` de la población inicial $(NP, d)$,
# una vez; luego, en cada generación, (2) `rng.random((NP, NP))` de los padres, (3)
# `rng.uniform(lb, ub, size=(NP, d))` del reinicio, (4) `rng.random((NP, d))` del cruce y
# (5) `rng.integers(0, d, size=NP)` de $j_{\text{rand}}$. El consumo no depende de los datos.
#
# Las validaciones, la población inicial, la evaluación, los frames y el retorno §5.1 son
# iguales en EA, PSO y DE: viven en `_comun.py` y aquí solo se importan.

# %%
"""Evolución diferencial DE/rand/1/bin de la Parte 1 (Spec §6.4): componentes y orquestador."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from src.common.counter import BudgetExhausted, CountedProblem
from src.common.seeds import validar_entero
from src.part1._comun import (
    DIMENSION_CON_FRAMES,
    construir_frame,
    construir_resultado,
    evaluar_poblacion,
    exigir_forma,
    generar_poblacion_inicial,
    leer_bloque,
    leer_record_frames,
    validar_claves_exactas,
    validar_limites,
    validar_poblacion,
    validar_real,
)

# %% [markdown]
# ## Constantes del módulo (no son parámetros del experimento)
#
# Los valores por defecto del experimento ($NP$, $F$, $CR$...) viven SOLO en
# `configs/part1/base.yaml` (Spec §4.1). Aquí solo hay definiciones estructurales.

# %%
NOMBRE_BLOQUE_DE = "de"              # clave del bloque en la configuración
CLAVES_BLOQUE_DE = ("NP", "F", "CR", "generaciones")
PADRES_POR_INDIVIDUO = 3             # r1, r2, r3 (DE/rand/1)
POBLACION_MINIMA = PADRES_POR_INDIVIDUO + 1   # 3 padres distintos entre sí y distintos de i


# %% [markdown]
# ## 0. `ParametrosDE`: validación del bloque `de:`
#
# Es el único lugar que interpreta el bloque `de:` de la configuración. Reglas:
#
# - claves **exactas** `NP, F, CR, generaciones` (faltantes o de más $\to$ `ValueError` que
#   las nombra; un esquema que no es mapeo $\to$ `TypeError`);
# - $NP \ge 4$ entero (se necesitan tres padres distintos entre sí y distintos de $i$);
# - $F$ real finito $> 0$; $CR$ real finito en $[0, 1]$ ($CR = 0$ es válido: el hijo toma
#   un único gen del mutante);
# - `generaciones` entero $\ge 0$ o `None` (= parar solo por presupuesto, Spec §6.2).

# %%
@dataclass(frozen=True)
class ParametrosDE:
    """Parámetros validados de la evolución diferencial (Spec §6.4).

    Se construye SIEMPRE con `ParametrosDE.desde_config(cfg["de"])`. Es importante porque es
    el único lugar que interpreta el bloque `de:`: el resto de componentes solo reciben
    números ya validados (no hay valores por defecto en el código, viven en base.yaml).

    Attributes
    ----------
    tamano_poblacion : int
        NP, número de individuos (>= 4).
    factor_f : float
        F, escala de la diferencia $x_{r_2} - x_{r_3}$ en la mutación (> 0).
    prob_cruce : float
        CR, probabilidad de que cada gen del hijo venga del mutante (en [0, 1]).
    generaciones : int | None
        None: parar solo por presupuesto (§6.2); entero >= 0: parar antes.
    """

    tamano_poblacion: int
    factor_f: float
    prob_cruce: float
    generaciones: int | None

    @classmethod
    def desde_config(cls, cfg_de: Mapping) -> ParametrosDE:
        """Valida el bloque `de:` de la configuración y construye los parámetros.

        Parameters
        ----------
        cfg_de : Mapping
            Bloque `de:` con EXACTAMENTE las claves `NP`, `F`, `CR` y `generaciones` (los
            valores por defecto viven en `configs/part1/base.yaml`).

        Returns
        -------
        ParametrosDE
            Instancia congelada con tipos nativos de Python.

        Raises
        ------
        TypeError
            Si `cfg_de` no es un mapeo o algún valor tiene un tipo incorrecto (bool donde se
            espera número, float donde se espera entero, etc.).
        ValueError
            Si faltan claves o sobran (typos), si NP < 4, si F no es finito y > 0, si CR no
            está en [0, 1] o si `generaciones` es negativo.
        """
        validar_claves_exactas(cfg_de, CLAVES_BLOQUE_DE, NOMBRE_BLOQUE_DE)

        tamano = validar_entero(cfg_de["NP"], "de.NP", minimo=POBLACION_MINIMA)
        factor_f = validar_real(cfg_de["F"], "de.F", minimo=0.0, minimo_incluido=False)
        prob_cruce = validar_real(cfg_de["CR"], "de.CR", minimo=0.0, minimo_incluido=True,
                                  maximo=1.0)

        generaciones = cfg_de["generaciones"]
        if generaciones is not None:
            generaciones = validar_entero(generaciones, "de.generaciones", minimo=0)

        return cls(tamano_poblacion=tamano, factor_f=factor_f, prob_cruce=prob_cruce,
                   generaciones=generaciones)


# %% [markdown]
# ## 1 y 2. Población inicial y evaluación
#
# Se usan `generar_poblacion_inicial` y `evaluar_poblacion` de `_comun.py` (no se duplican):
# la primera sortea $x_{ij} \sim \mathcal{U}(l_j,\, u_j)$ y la segunda calcula $f(x_i)$ fila
# por fila. Cada llamada a `f` es UNA evaluación del presupuesto: `optimize` le pasa
# `problem.f`, que es quien cuenta y quien lanza `BudgetExhausted`.

# %% [markdown]
# ## 3. `sortear_padres`
#
# Para cada individuo $i$ se eligen tres índices $r_1, r_2, r_3$ **distintos entre sí y
# distintos de $i$**:
#
# $$r_1 \ne r_2 \ne r_3 \ne r_1, \qquad r_k \ne i, \qquad r_k \in \{0, \dots, NP - 1\}$$
#
# Vectorizado en una sola llamada al rng: cada fila $i$ recibe $NP$ números uniformes; se pone
# $+\infty$ en la posición $i$ (para que $i$ nunca sea elegido) y se ordena la fila: los tres
# índices con los números más bajos son una muestra aleatoria **sin repetición** de los otros
# $NP - 1$ individuos.

# %%
def sortear_padres(tamano: int, rng: np.random.Generator) -> np.ndarray:
    """Sortea, para cada individuo, tres padres distintos entre sí y distintos de él.

    La mutación diferencial necesita tres individuos que no sean el propio objetivo ni se
    repitan: si $r_2 = r_3$ la diferencia sería cero y el mutante solo copiaría a $r_1$; si
    algún $r_k = i$ el mutante estaría anclado al objetivo. Aquí se evita sin bucles.

    Parameters
    ----------
    tamano : int
        Número de individuos NP (>= 4).
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    np.ndarray, forma (NP, 3), dtype entero
        Fila i = `[r1, r2, r3]`, índices en `[0, NP)`, distintos entre sí y de i.

    Raises
    ------
    TypeError
        Si `tamano` no es un entero.
    ValueError
        Si `tamano < 4`.

    Notas
    -----
    Orden de consumo del rng: UNA sola llamada, `rng.random((NP, NP))`.
    """
    tamano = validar_entero(tamano, "tamano", minimo=POBLACION_MINIMA)

    # Un número uniforme por (individuo, candidato a padre); forma (NP, NP).
    sorteo = rng.random((tamano, tamano))
    # La diagonal (candidato == individuo) se pone en +inf: al ordenar queda siempre al final
    # y por tanto nunca entre los 3 primeros (NP >= 4 garantiza al menos 3 candidatos).
    np.fill_diagonal(sorteo, np.inf)
    # argsort por filas devuelve los índices de menor a mayor número; forma (NP, NP).
    orden_por_fila = np.argsort(sorteo, axis=1)
    # Las 3 primeras columnas: 3 índices distintos (es una permutación) y distintos de i.
    indices_padres = orden_por_fila[:, :PADRES_POR_INDIVIDUO]        # forma (NP, 3)
    return indices_padres


# %% [markdown]
# ## 4. `mutar_diferencial`
#
# Con $F > 0$ el factor de mutación y $r_1, r_2, r_3$ los padres de $i$:
#
# $$v_i = x_{r_1} + F\,\big(x_{r_2} - x_{r_3}\big), \qquad i = 0,\dots,NP - 1$$
#
# La diferencia $x_{r_2} - x_{r_3}$ es grande mientras la población está dispersa y tiende a
# encogerse cuando la población se concentra (si colapsa en un mínimo local, el paso se anula
# y la búsqueda se estanca). **No** se recorta al dominio aquí: el tratamiento de lo que sale
# del dominio es el componente siguiente (`reiniciar_fuera_de_dominio`).

# %%
def mutar_diferencial(poblacion: np.ndarray, indices_padres: np.ndarray,
                      factor_f: float) -> np.ndarray:
    """Construye los mutantes $v_i = x_{r_1} + F (x_{r_2} - x_{r_3})$ de toda la población.

    Es el operador que define la evolución diferencial: el paso de búsqueda sale de la propia
    población, sin parámetros de escala adicionales. Función pura: no consume azar, no recorta
    y no modifica las entradas.

    Parameters
    ----------
    poblacion : np.ndarray, forma (NP, d)
        Población al INICIO de la generación (esquema síncrono).
    indices_padres : np.ndarray, forma (NP, 3), entero
        Salida de `sortear_padres`: fila i = `[r1, r2, r3]`.
    factor_f : float
        F (> 0).

    Returns
    -------
    np.ndarray, forma (NP, d)
        Mutantes (arreglo nuevo; pueden quedar fuera del dominio).

    Raises
    ------
    ValueError
        Si las formas no son coherentes o hay índices fuera de `[0, NP)`.
    """
    poblacion = validar_poblacion(poblacion, "poblacion")
    tamano = poblacion.shape[0]
    indices_padres = np.asarray(indices_padres)
    if indices_padres.shape != (tamano, PADRES_POR_INDIVIDUO):
        raise ValueError(f"indices_padres debe tener forma {(tamano, PADRES_POR_INDIVIDUO)}; "
                         f"se recibió {indices_padres.shape}")
    if not np.issubdtype(indices_padres.dtype, np.integer):
        raise ValueError(f"indices_padres debe ser entero; se recibió {indices_padres.dtype}")
    if indices_padres.min() < 0 or indices_padres.max() >= tamano:
        raise ValueError(f"indices_padres debe estar en [0, {tamano})")

    # Indexación avanzada: poblacion[columna_de_indices] elige filas; cada resultado es (NP, d).
    base_r1 = poblacion[indices_padres[:, 0]]                        # forma (NP, d)
    extremo_r2 = poblacion[indices_padres[:, 1]]                     # forma (NP, d)
    extremo_r3 = poblacion[indices_padres[:, 2]]                     # forma (NP, d)

    diferencia = extremo_r2 - extremo_r3                             # forma (NP, d)
    mutantes = base_r1 + factor_f * diferencia                       # forma (NP, d)
    return mutantes


# %% [markdown]
# ## 5. `reiniciar_fuera_de_dominio`
#
# Si una componente del mutante sale de $[l_j, u_j]$ **se reinicia** con un sorteo uniforme
# en ese intervalo (no se recorta). Se hace sobre el mutante, ANTES del cruce:
#
# $$v_{ij} \leftarrow \begin{cases} \mathcal{U}(l_j,\, u_j) & \text{si } v_{ij} < l_j \,\lor\,
#   v_{ij} > u_j \\ v_{ij} & \text{en otro caso} \end{cases}$$
#
# El cierre es inclusivo: un valor igual al límite NO sale. El sorteo se hace siempre completo
# $(NP, d)$ y solo se aplica donde hace falta: así el consumo del rng no depende de los datos.

# %%
class ResultadoReinicio(NamedTuple):
    """Salida de `reiniciar_fuera_de_dominio` (arreglos nuevos, sin alias con las entradas).

    mutantes   : (NP, d) mutantes con las componentes fuera reiniciadas dentro del dominio.
    reiniciadas: (NP, d) bool, True donde la componente salía del dominio y se sorteó de nuevo.
                 Es diagnóstico para pruebas y explicación; `optimize` no lo consume.
    """

    mutantes: np.ndarray
    reiniciadas: np.ndarray


def reiniciar_fuera_de_dominio(mutantes: np.ndarray, limites: np.ndarray,
                               rng: np.random.Generator) -> ResultadoReinicio:
    """Reinicia con un sorteo uniforme cada componente del mutante que sale del dominio.

    Conserva la diversidad: recortar apilaría individuos sobre la frontera (muchos genes
    iguales a $l_j$ o $u_j$), mientras que el reinicio los vuelve a repartir por el dominio.
    Las componentes que ya estaban dentro no cambian.

    Parameters
    ----------
    mutantes : np.ndarray, forma (NP, d)
        Salida de `mutar_diferencial`; no se modifica.
    limites : np.ndarray, forma (d, 2)
        Dominio `[mínimo, máximo]` por dimensión (como `problem.func.bounds`).
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    ResultadoReinicio
        `mutantes` (NP, d) y `reiniciadas` (NP, d) bool.

    Raises
    ------
    ValueError
        Si las formas no son coherentes con `limites`.

    Notas
    -----
    Orden de consumo del rng: UNA sola llamada,
    `rng.uniform(lb, ub, size=(NP, d))`, siempre completa (haya o no componentes fuera).
    """
    limites = validar_limites(limites)
    mutantes = validar_poblacion(mutantes, "mutantes")
    if mutantes.shape[1] != limites.shape[0]:
        raise ValueError(f"limites describe {limites.shape[0]} dimensiones pero los mutantes "
                         f"tienen {mutantes.shape[1]}")

    limites_inferiores = limites[:, 0]                               # forma (d,)
    limites_superiores = limites[:, 1]                               # forma (d,)

    # Sorteo completo (NP, d): cada columna usa el rango de SU dimensión (broadcasting de (d,)).
    sorteo = rng.uniform(limites_inferiores, limites_superiores, size=mutantes.shape)

    # Máscara (NP, d): True donde el mutante sale. `<` y `>` comparan cada fila (NP, d)
    # contra los límites (d,) columna a columna; `|` une ambas máscaras.
    reiniciadas = (mutantes < limites_inferiores) | (mutantes > limites_superiores)

    # np.where elige elemento a elemento y devuelve un arreglo NUEVO (copia, sin alias).
    mutantes_nuevos = np.where(reiniciadas, sorteo, mutantes)        # forma (NP, d)
    return ResultadoReinicio(mutantes=mutantes_nuevos, reiniciadas=reiniciadas)


# %% [markdown]
# ## 6. `cruzar_binomial`
#
# Para cada individuo $i$ y cada gen $j$, con $U_{ij} \sim \mathcal{U}(0, 1)$ y
# $j_{\text{rand}, i} \sim \mathcal{U}\{0, \dots, d - 1\}$:
#
# $$u_{ij} = \begin{cases} v_{ij} & \text{si } U_{ij} \le CR \,\lor\, j = j_{\text{rand}, i} \\
#   x_{ij} & \text{en otro caso} \end{cases}$$
#
# $j_{\text{rand}}$ garantiza que el hijo toma **al menos un gen** del mutante (aunque
# $CR = 0$): sin él, el hijo podría ser una copia exacta del padre y gastaría una evaluación.

# %%
class ResultadoCruce(NamedTuple):
    """Salida de `cruzar_binomial` (arreglos nuevos, sin alias con las entradas).

    hijos     : (NP, d) hijos $u_i$.
    de_mutante: (NP, d) bool, True donde el gen del hijo viene del mutante.
                Es diagnóstico para pruebas y explicación; `optimize` no lo consume.
    """

    hijos: np.ndarray
    de_mutante: np.ndarray


def cruzar_binomial(poblacion: np.ndarray, mutantes: np.ndarray, prob_cruce: float,
                    rng: np.random.Generator) -> ResultadoCruce:
    """Cruce binomial entre cada padre $x_i$ y su mutante $v_i$, gen a gen.

    Controla cuánto del mutante entra en el hijo: con CR alto el hijo se parece al mutante
    (búsqueda en todas las direcciones a la vez); con CR bajo cambia pocos genes (búsqueda
    más cercana a los ejes). Siempre hereda al menos un gen del mutante.

    Parameters
    ----------
    poblacion : np.ndarray, forma (NP, d)
        Padres $x_i$; no se modifica.
    mutantes : np.ndarray, forma (NP, d)
        Mutantes $v_i$ (ya dentro del dominio); no se modifica.
    prob_cruce : float
        CR en [0, 1].
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    ResultadoCruce
        `hijos` (NP, d) y `de_mutante` (NP, d) bool.

    Raises
    ------
    ValueError
        Si las formas de `poblacion` y `mutantes` no coinciden.

    Notas
    -----
    Orden de consumo del rng: (1) `rng.random((NP, d))` para $U$ y, después,
    (2) `rng.integers(0, d, size=NP)` para $j_{\\text{rand}}$.
    """
    poblacion = validar_poblacion(poblacion, "poblacion")
    mutantes = exigir_forma(mutantes, poblacion.shape, "mutantes")
    tamano, dimension = poblacion.shape

    # Un uniforme por gen; forma (NP, d). Se sortea ANTES que j_rand (orden fijo).
    uniformes = rng.random((tamano, dimension))
    # Un gen obligatorio por individuo; forma (NP,), valores en {0, ..., d-1}.
    columna_obligatoria = rng.integers(0, dimension, size=tamano)

    # Índice de columna de cada gen; forma (d,) -> (1, d) al comparar con (NP, 1).
    indice_de_gen = np.arange(dimension)
    # (NP, d) == comparación de (1, d) contra (NP, 1): True solo en la columna j_rand de cada fila.
    es_gen_obligatorio = indice_de_gen[np.newaxis, :] == columna_obligatoria[:, np.newaxis]
    # `|` une las dos condiciones del cruce binomial; forma (NP, d), bool.
    de_mutante = (uniformes <= prob_cruce) | es_gen_obligatorio

    # np.where toma el mutante donde la máscara es True y el padre donde es False (copia).
    hijos = np.where(de_mutante, mutantes, poblacion)                # forma (NP, d)
    return ResultadoCruce(hijos=hijos, de_mutante=de_mutante)


# %% [markdown]
# ## 7. `seleccionar_codiciosa`
#
# El hijo reemplaza a su padre si **no es peor** (el hijo gana en empate):
#
# $$x_i \leftarrow \begin{cases} u_i & \text{si } f(u_i) \le f(x_i) \\ x_i & \text{en otro caso}
#   \end{cases}$$
#
# Por construcción la aptitud de cada puesto de la población nunca empeora (con $f$ finita: si
# $f$ devolviera NaN, la comparación es falsa y ese puesto quedaría congelado). Aceptar el
# empate deja que la población se desplace por mesetas planas en lugar de quedarse quieta.

# %%
class ResultadoSeleccion(NamedTuple):
    """Salida de `seleccionar_codiciosa` (arreglos nuevos, sin alias con las entradas).

    poblacion   : (NP, d) población de la siguiente generación.
    aptitudes   : (NP,) aptitud de cada fila de `poblacion`.
    reemplazaron: (NP,) bool, True si el hijo reemplazó a su padre. Es diagnóstico para
                  pruebas y explicación; `optimize` no lo consume.
    """

    poblacion: np.ndarray
    aptitudes: np.ndarray
    reemplazaron: np.ndarray


def seleccionar_codiciosa(poblacion: np.ndarray, aptitudes: np.ndarray, hijos: np.ndarray,
                          aptitudes_hijos: np.ndarray) -> ResultadoSeleccion:
    """Selección codiciosa uno a uno: el hijo i compite solo contra el padre i.

    Es lo que hace elitista a la evolución diferencial sin ordenar la población: el mejor
    valor de f de la población nunca empeora (el individuo puede cambiar si un hijo empata,
    porque el hijo gana en empate, `<=`).

    Parameters
    ----------
    poblacion : np.ndarray, forma (NP, d)
        Padres $x_i$; no se modifica.
    aptitudes : np.ndarray, forma (NP,)
        $f(x_i)$.
    hijos : np.ndarray, forma (NP, d)
        Hijos $u_i$; no se modifica.
    aptitudes_hijos : np.ndarray, forma (NP,)
        $f(u_i)$.

    Returns
    -------
    ResultadoSeleccion
        `poblacion` (NP, d), `aptitudes` (NP,) y `reemplazaron` (NP,) bool.

    Raises
    ------
    ValueError
        Si las formas no son coherentes entre sí.
    """
    poblacion = validar_poblacion(poblacion, "poblacion")
    tamano, dimension = poblacion.shape
    aptitudes = exigir_forma(aptitudes, (tamano,), "aptitudes")
    hijos = exigir_forma(hijos, (tamano, dimension), "hijos")
    aptitudes_hijos = exigir_forma(aptitudes_hijos, (tamano,), "aptitudes_hijos")

    # Máscara (NP,): True donde el hijo NO es peor (empate incluido).
    reemplazaron = aptitudes_hijos <= aptitudes

    # La máscara (NP,) se vuelve columna (NP, 1) para difundirse sobre las d dimensiones;
    # np.where devuelve arreglos NUEVOS (sin alias con las entradas).
    nueva_poblacion = np.where(reemplazaron[:, np.newaxis], hijos, poblacion)   # (NP, d)
    nuevas_aptitudes = np.where(reemplazaron, aptitudes_hijos, aptitudes)       # (NP,)
    return ResultadoSeleccion(poblacion=nueva_poblacion, aptitudes=nuevas_aptitudes,
                              reemplazaron=reemplazaron)


# %% [markdown]
# ## 8. `optimize`: el orquestador
#
# Encadena los componentes siguiendo el Spec §6.4. Con $T$ generaciones completas el conteo de
# evaluaciones es exacto (la población inicial cuenta, Spec §6.2; cada hijo cuesta una):
#
# $$n_f = NP\,(T + 1), \qquad n_{\text{grad}} = 0, \qquad \text{eval\_equiv} = n_f$$
#
# El presupuesto $B$ corta la corrida: la generación que no cabe se trunca en la evaluación
# exacta que lo excedería (`BudgetExhausted`), se descarta (población no actualizada, sin
# frame) y se devuelve el mejor punto visto. Con $B = 20\,000$ y $NP = 30$ en 2D:
# $30 \cdot 666 = 19\,980$ más 20 evaluaciones de la generación truncada (665 generaciones
# completas, frames `iter` 0 a 665).

# %%
def _registrar_frame(frames: list[dict], iteracion: int, poblacion: np.ndarray,
                     aptitudes: np.ndarray) -> None:
    """Agrega a `frames` el frame de `iteracion` con el mejor individuo de la población.

    Se llama una vez con la población inicial (iter 0) y una vez por generación completada.
    """
    mejor = poblacion[np.argmin(aptitudes)]                          # forma (d,)
    frames.append(construir_frame(iteracion, poblacion, mejor))


def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Ejecuta DE/rand/1/bin sobre `problem` hasta agotar el presupuesto (o `generaciones`).

    Es el único componente que conoce `CountedProblem` y la configuración completa: lee el
    dominio y la dimensión de `problem.func`, delega cada fase en un componente y deja que
    `CountedProblem` cuente (nunca se cuenta a mano, Spec §6.2).

    Parameters
    ----------
    problem : CountedProblem
        Función envuelta con su contador y presupuesto; debe admitir al menos 1 evaluación.
    cfg : dict
        Configuración ya cargada: `cfg["de"]` (bloque de parámetros) y `cfg["record_frames"]`.
    rng : np.random.Generator
        Única fuente de azar; se inyecta a la inicialización, a los padres, al reinicio y al
        cruce.

    Returns
    -------
    dict
        Contrato §5.1: `x_best` (list), `f_best` (float), `n_f` (int), `n_grad` (int, siempre
        0), `eval_equiv` (float), `history` (copia de `problem.history`) y, solo si
        `problem.func.dim == 2` y `cfg["record_frames"]`, `frames`: un frame por generación
        completada (iter 0 = población inicial) con `best` = mejor individuo de la población.

    Raises
    ------
    ValueError
        Configuración inválida (ver `ParametrosDE.desde_config`), falta `de` o
        `record_frames`, o presupuesto que no alcanza para ninguna evaluación.
    TypeError
        Tipos incorrectos en la configuración.

    Notas
    -----
    Orden de consumo del rng (fijo): (1) `rng.uniform` de la población inicial (NP, d), una
    vez; luego, por generación, (2) `rng.random((NP, NP))` de los padres, (3)
    `rng.uniform(lb, ub, size=(NP, d))` del reinicio, (4) `rng.random((NP, d))` del cruce y
    (5) `rng.integers(0, d, size=NP)` de $j_{\\text{rand}}$.

    Con `generaciones = None` el bucle no tiene tope propio: termina cuando `CountedProblem`
    lanza `BudgetExhausted` (se captura dentro de `optimize`). Por eso el presupuesto debe
    ser finito; `CountedProblem` ya rechaza un presupuesto infinito en su constructor.
    """
    # `ParametrosDE.desde_config`: validar la configuración y leer el dominio del problema.
    parametros = ParametrosDE.desde_config(leer_bloque(cfg, NOMBRE_BLOQUE_DE))
    guardar_frames = leer_record_frames(cfg) and problem.func.dim == DIMENSION_CON_FRAMES
    limites = validar_limites(problem.func.bounds)                  # forma (d, 2)
    if problem.budget_exhausted():
        raise ValueError(f"el presupuesto ({problem.budget}) no alcanza para ninguna "
                         "evaluación de f")
    tamano = parametros.tamano_poblacion

    frames: list[dict] = []

    # Un solo try/except: si el presupuesto se agota en cualquier evaluación, la generación
    # incompleta se descarta y se devuelve el mejor punto visto (patrón Spec §5.1, T0.4).
    try:
        # `generar_poblacion_inicial` + `evaluar_poblacion`: NP evaluaciones (§6.2).
        poblacion = generar_poblacion_inicial(tamano, limites, rng)  # forma (NP, d)
        aptitudes = evaluar_poblacion(poblacion, problem.f)          # forma (NP,)
        if guardar_frames:
            _registrar_frame(frames, 0, poblacion, aptitudes)

        generacion = 0
        while parametros.generaciones is None or generacion < parametros.generaciones:
            generacion += 1

            # `sortear_padres` + `mutar_diferencial`: padres (NP, 3) y mutantes (NP, d)
            # con la población al INICIO de la generación.
            indices_padres = sortear_padres(tamano, rng)
            mutantes = mutar_diferencial(poblacion, indices_padres, parametros.factor_f)

            # `reiniciar_fuera_de_dominio`: reinicia lo que sale del dominio (antes del cruce).
            reinicio = reiniciar_fuera_de_dominio(mutantes, limites, rng)

            # `cruzar_binomial`: cruce con el padre; hijos (NP, d).
            cruce = cruzar_binomial(poblacion, reinicio.mutantes, parametros.prob_cruce, rng)

            # `evaluar_poblacion` (1 evaluación por hijo) + `seleccionar_codiciosa`.
            aptitudes_hijos = evaluar_poblacion(cruce.hijos, problem.f)     # forma (NP,)
            seleccion = seleccionar_codiciosa(poblacion, aptitudes, cruce.hijos,
                                              aptitudes_hijos)
            poblacion = seleccion.poblacion
            aptitudes = seleccion.aptitudes

            # Frame de la generación completada (la truncada por presupuesto no llega aquí).
            if guardar_frames:
                _registrar_frame(frames, generacion, poblacion, aptitudes)
    except BudgetExhausted:
        # Presupuesto agotado: la generación incompleta no registra frame y el mejor punto
        # visto está en problem.best_x / problem.best_f.
        pass

    # Retorno del contrato §5.1 con tipos nativos de Python.
    return construir_resultado(problem, frames, guardar_frames)
