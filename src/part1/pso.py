# %% [markdown]
# # PSO gbest con inercia de la Parte 1 (Spec §6.4, v1.4)
#
# **Propósito.** Minimizar una función de prueba (Rosenbrock o Rastrigin) con un enjambre de
# $N$ partículas en $\mathbb{R}^d$. Cada partícula $i$ tiene una posición $x_i$, una velocidad
# $v_i$ y recuerda el mejor punto que ha visitado $b_i$ (su mejor personal). Todas comparten el
# mejor punto de todo el enjambre $g$ (topología *gbest*).
#
# **Ciclo** (un solo enjambre, matrices de forma $(N, d)$, una fila por partícula):
#
# $$\text{Inicialización} \to \text{Evaluación} \to \text{Memoria} \to \text{Movimiento}
#   \to \text{Evaluación} \to \dots$$
#
# **Mapa de componentes** (cada uno hace UNA sola cosa y recibe todo por parámetro):
#
# | # | Componente | Qué hace | Retorna |
# |---|---|---|---|
# | 0 | `ParametrosPSO` | valida el bloque `pso:` de la configuración | dataclass |
# | 1 | `generar_enjambre_inicial` | sortea $N$ posiciones; velocidades en 0 | `EnjambreInicial` |
# | 2 | `calcular_velocidad_maxima` | $v_{\max}$ por dimensión desde el dominio | `(d,)` o `None` |
# | 3 | `evaluar_poblacion` | (de `_comun.py`) aplica `f` a cada fila | `(N,)` |
# | 4 | `actualizar_memoria_personal` | $b_i \leftarrow x_i$ si mejora | `ResultadoMemoria` |
# | 5 | `actualizar_mejor_global` | elige $g$ entre los $b_i$ | `MejorGlobal` |
# | 6 | `calcular_velocidades` | ecuación de velocidad con inercia (sin limitar) | `(N, d)` |
# | 7 | `limitar_velocidades` | recorta cada componente a $\pm v_{\max}$ | `(N, d)` |
# | 8 | `aplicar_frontera` | recorta x al dominio y anula esa velocidad | `ResultadoFrontera` |
# | 9 | `optimize` | orquestador: encadena 1-8; cuenta con `CountedProblem` | dict §5.1 |
#
# **Todo el azar** sale del `rng` que recibe `optimize` y que se inyecta a los componentes
# (Spec §4.1: un generador por corrida, con semilla `base_seed + run_id`). Nada global.
#
# **Orden de consumo del rng** (fijo): (1) `rng.uniform` de las posiciones $(N, d)$ (las
# velocidades iniciales son 0 y no consumen azar); luego, en cada iteración, (2) $R_1$ y
# (3) $R_2$, ambas de forma $(N, d)$ y en ese orden, ANTES de mover el enjambre.
#
# Las validaciones, la población inicial, la evaluación, los frames y el retorno §5.1 son
# iguales en EA, PSO y DE: viven en `_comun.py` y aquí solo se importan.

# %%
"""PSO gbest con inercia de la Parte 1 (Spec §6.4): componentes y orquestador."""

from __future__ import annotations

import warnings
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
# Los valores por defecto del experimento ($N$, $w$, $c_1$, $c_2$...) viven SOLO en
# `configs/part1/base.yaml` (Spec §4.1). Aquí solo hay definiciones estructurales.

# %%
NOMBRE_BLOQUE_PSO = "pso"            # clave del bloque en la configuración
CLAVES_BLOQUE_PSO = ("N", "w", "c1", "c2", "vmax_frac", "iteraciones")
ENJAMBRE_MINIMO = 2                  # con N < 2 no hay enjambre (Spec §6.4)
UMBRAL_AVISO_INERCIA = 1.0           # w >= 1: la velocidad no se amortigua; solo se avisa


# %% [markdown]
# ## 0. `ParametrosPSO`: validación del bloque `pso:`
#
# Es el único lugar que interpreta el bloque `pso:` de la configuración. Reglas:
#
# - claves **exactas** `N, w, c1, c2, vmax_frac, iteraciones` (faltantes o de más $\to$
#   `ValueError` que las nombra);
# - $N \ge 2$ entero; $w, c_1, c_2$ reales finitos $\ge 0$ (sin `bool`);
# - `vmax_frac` $\in (0, \infty)$ o `None` (= sin límite de velocidad);
# - `iteraciones` entero $\ge 0$ o `None` (= parar solo por presupuesto, Spec §6.2);
# - $w \ge 1$ no se rechaza: emite un `UserWarning`. No se fija ningún umbral sobre
#   $c_1 + c_2$ (no hay fuente verificada).

# %%
def _avisar_si_inercia_no_amortigua(inercia: float) -> None:
    """Emite un UserWarning si w >= 1 (la velocidad anterior no se amortigua); no rechaza.

    Se llama solo desde `ParametrosPSO.desde_config`: `stacklevel=3` hace que el aviso apunte
    al llamador de `desde_config` y no a esta función ni a `desde_config`.
    """
    if inercia >= UMBRAL_AVISO_INERCIA:
        warnings.warn(
            f"pso.w = {inercia} >= {UMBRAL_AVISO_INERCIA}: la inercia no amortigua la "
            "velocidad y el enjambre puede no converger",
            UserWarning,
            stacklevel=3,
        )


@dataclass(frozen=True)
class ParametrosPSO:
    """Parámetros validados del PSO (Spec §6.4).

    Se construye SIEMPRE con `ParametrosPSO.desde_config(cfg["pso"])`. Es importante porque
    es el único lugar que interpreta el bloque `pso:`: el resto de componentes solo reciben
    números ya validados (no hay valores por defecto en el código, viven en base.yaml).

    Attributes
    ----------
    tamano_enjambre : int
        N, número de partículas (>= 2).
    inercia : float
        w, factor que amortigua la velocidad anterior (>= 0).
    coef_cognitivo : float
        c1, peso de la atracción hacia el mejor personal (>= 0).
    coef_social : float
        c2, peso de la atracción hacia el mejor global (>= 0).
    fraccion_vmax : float | None
        `v_max = fraccion_vmax * (ub - lb)` por dimensión; None = sin límite.
    iteraciones : int | None
        None: parar solo por presupuesto (§6.2); entero >= 0: parar antes.
    """

    tamano_enjambre: int
    inercia: float
    coef_cognitivo: float
    coef_social: float
    fraccion_vmax: float | None
    iteraciones: int | None

    @classmethod
    def desde_config(cls, cfg_pso: Mapping) -> ParametrosPSO:
        """Valida el bloque `pso:` de la configuración y construye los parámetros.

        Parameters
        ----------
        cfg_pso : Mapping
            Bloque `pso:` con EXACTAMENTE las claves `N`, `w`, `c1`, `c2`, `vmax_frac` e
            `iteraciones` (los valores por defecto viven en `configs/part1/base.yaml`).

        Returns
        -------
        ParametrosPSO
            Instancia congelada con tipos nativos de Python.

        Raises
        ------
        TypeError
            Si `cfg_pso` no es un mapeo o algún valor tiene un tipo incorrecto (bool donde se
            espera número, float donde se espera entero, etc.).
        ValueError
            Si faltan claves o sobran (typos), si N < 2, si w/c1/c2 son negativos, NaN o inf,
            si `vmax_frac` no es positivo finito o si `iteraciones` es negativo.

        Warns
        -----
        UserWarning
            Si `w >= 1` (la inercia no amortigua la velocidad); no se rechaza.
        """
        validar_claves_exactas(cfg_pso, CLAVES_BLOQUE_PSO, NOMBRE_BLOQUE_PSO)

        tamano = validar_entero(cfg_pso["N"], "pso.N", minimo=ENJAMBRE_MINIMO)
        # El mínimo se pasa como entero: así el mensaje de error dice ">= 0" y "> 0".
        inercia = validar_real(cfg_pso["w"], "pso.w", minimo=0, minimo_incluido=True)
        coef_cognitivo = validar_real(cfg_pso["c1"], "pso.c1", minimo=0, minimo_incluido=True)
        coef_social = validar_real(cfg_pso["c2"], "pso.c2", minimo=0, minimo_incluido=True)

        fraccion_vmax = cfg_pso["vmax_frac"]
        if fraccion_vmax is not None:
            fraccion_vmax = validar_real(fraccion_vmax, "pso.vmax_frac", minimo=0,
                                         minimo_incluido=False)

        iteraciones = cfg_pso["iteraciones"]
        if iteraciones is not None:
            iteraciones = validar_entero(iteraciones, "pso.iteraciones", minimo=0)

        _avisar_si_inercia_no_amortigua(inercia)

        return cls(
            tamano_enjambre=tamano,
            inercia=inercia,
            coef_cognitivo=coef_cognitivo,
            coef_social=coef_social,
            fraccion_vmax=fraccion_vmax,
            iteraciones=iteraciones,
        )


# %% [markdown]
# ## 1. `generar_enjambre_inicial`
#
# Las posiciones se sortean uniformes en el dominio (igual que la población inicial del EA) y
# las partículas arrancan **en reposo**:
#
# $$x_{ij} \sim \mathcal{U}(l_j,\, u_j), \qquad v_{ij}^{(0)} = 0, \qquad
#   b_i^{(0)} = x_i^{(0)}$$
#
# con $i = 1,\dots,N$ y $j = 1,\dots,d$; $l_j, u_j$ son las columnas 0 y 1 de `limites`.

# %%
class EnjambreInicial(NamedTuple):
    """Salida de `generar_enjambre_inicial`.

    posiciones  : (N, d) posiciones uniformes dentro del dominio.
    velocidades : (N, d) ceros (las partículas arrancan en reposo).
    """

    posiciones: np.ndarray
    velocidades: np.ndarray


def generar_enjambre_inicial(tamano: int, limites: np.ndarray,
                             rng: np.random.Generator) -> EnjambreInicial:
    """Sortea las posiciones iniciales y pone todas las velocidades en cero.

    Es el punto de partida de la búsqueda: cuantas más partículas repartidas por todo el
    dominio, más regiones se exploran desde el principio (Spec §6.2: este enjambre CUENTA en
    el presupuesto cuando se evalúa). Con $v_i(0) = 0$ y, además, $b_i = x_i$, el término
    cognitivo y el de inercia valen exactamente cero en la primera iteración: el primer
    movimiento es puramente social (solo la atracción hacia $g$). La partícula que ya es $g$
    tiene ambas atracciones en cero y no se mueve hasta que $g$ cambie.

    Parameters
    ----------
    tamano : int
        Número de partículas N (>= 1).
    limites : np.ndarray, forma (d, 2)
        Dominio: `limites[j] = [mínimo, máximo]` de la dimensión j (como
        `problem.func.bounds`).
    rng : np.random.Generator
        Generador de azar inyectado por el llamador.

    Returns
    -------
    EnjambreInicial
        `posiciones` (N, d) y `velocidades` (N, d) = ceros; no comparten memoria.

    Notas
    -----
    Orden de consumo del rng: UNA sola llamada `rng.uniform(...)` (vía
    `generar_poblacion_inicial` de `_comun.py`); las velocidades en cero no consumen azar.
    """
    # Las posiciones se sortean con el componente común a EA, PSO y DE (forma (N, d)).
    posiciones = generar_poblacion_inicial(tamano, limites, rng)
    # Velocidades en reposo, misma forma (N, d); arreglo propio, sin compartir memoria.
    velocidades = np.zeros_like(posiciones)
    return EnjambreInicial(posiciones=posiciones, velocidades=velocidades)


# %% [markdown]
# ## 2. `calcular_velocidad_maxima`
#
# El límite de velocidad evita saltos enormes que lanzarían a la partícula contra la frontera.
# Se calcula una vez por dimensión a partir de la anchura del dominio:
#
# $$v_{\max,j} = \phi_v \,(u_j - l_j), \qquad j = 1,\dots,d$$
#
# con $\phi_v$ = `vmax_frac`. Si `vmax_frac` es `None` no hay límite.

# %%
def calcular_velocidad_maxima(limites: np.ndarray,
                              fraccion_vmax: float | None) -> np.ndarray | None:
    """Calcula `v_max` por dimensión como fracción de la anchura del dominio.

    Parameters
    ----------
    limites : np.ndarray, forma (d, 2)
        Dominio `[mínimo, máximo]` por dimensión.
    fraccion_vmax : float | None
        Fracción de la anchura (> 0), o None para no limitar la velocidad.

    Returns
    -------
    np.ndarray, forma (d,) | None
        `fraccion_vmax * (ub - lb)` por dimensión, o None si `fraccion_vmax` es None.
    """
    limites = validar_limites(limites)
    if fraccion_vmax is None:
        return None

    # `limites[:, 0]` = columna 0 de todas las filas: el mínimo de cada dimensión.
    limites_inferiores = limites[:, 0]                       # forma (d,)
    limites_superiores = limites[:, 1]                       # forma (d,)
    anchura_del_dominio = limites_superiores - limites_inferiores   # forma (d,)
    velocidad_maxima = fraccion_vmax * anchura_del_dominio   # forma (d,)
    return velocidad_maxima


# %% [markdown]
# ## 3. Evaluación del enjambre
#
# Se usa `evaluar_poblacion` de `_comun.py` (no se duplica): aplica `f` a cada fila y guarda la
# aptitud $a_i = f(x_i)$. Cada llamada es UNA evaluación del presupuesto; `optimize` le pasa
# `problem.f`, que es quien cuenta y quien lanza `BudgetExhausted`.

# %% [markdown]
# ## 4. `actualizar_memoria_personal`
#
# Cada partícula recuerda el mejor punto que ha visitado. La memoria cambia **solo con mejora
# estricta** (un empate no la cambia):
#
# $$b_i \leftarrow \begin{cases} x_i & \text{si } f(x_i) < f(b_i) \\ b_i & \text{en otro caso}
#   \end{cases}$$
#
# Por construcción $f(b_i)$ nunca empeora.

# %%
class ResultadoMemoria(NamedTuple):
    """Salida de `actualizar_memoria_personal` (arreglos nuevos, sin alias con las entradas).

    mejores_personales  : (N, d) memoria actualizada.
    aptitudes_personales: (N,) aptitud de cada fila de `mejores_personales`.
    mejoraron           : (N,) bool, True si la partícula mejoró su memoria en este paso.
    """

    mejores_personales: np.ndarray
    aptitudes_personales: np.ndarray
    mejoraron: np.ndarray


def actualizar_memoria_personal(posiciones: np.ndarray, aptitudes: np.ndarray,
                                mejores_personales: np.ndarray,
                                aptitudes_personales: np.ndarray) -> ResultadoMemoria:
    """Actualiza la memoria personal de cada partícula con mejora ESTRICTA.

    Es el componente que da "memoria" al enjambre: sin él, $b_i$ sería siempre la posición
    actual, el término cognitivo valdría cero y solo quedaría la atracción hacia $g$ (y la
    inercia). Devuelve copias; las entradas no se modifican.

    Parameters
    ----------
    posiciones : np.ndarray, forma (N, d)
        Posiciones actuales $x_i$.
    aptitudes : np.ndarray, forma (N,)
        $f(x_i)$ de las posiciones actuales.
    mejores_personales : np.ndarray, forma (N, d)
        Memorias actuales $b_i$.
    aptitudes_personales : np.ndarray, forma (N,)
        $f(b_i)$.

    Returns
    -------
    ResultadoMemoria
        `mejores_personales` (N, d), `aptitudes_personales` (N,) y `mejoraron` (N,) bool.

    Raises
    ------
    ValueError
        Si las formas no son coherentes entre sí.
    """
    posiciones = validar_poblacion(posiciones, "posiciones")
    numero_de_particulas, dimension = posiciones.shape
    aptitudes = exigir_forma(aptitudes, (numero_de_particulas,), "aptitudes")
    mejores_personales = exigir_forma(mejores_personales, (numero_de_particulas, dimension),
                                      "mejores_personales")
    aptitudes_personales = exigir_forma(aptitudes_personales, (numero_de_particulas,),
                                        "aptitudes_personales")

    # Máscara booleana (N,): True donde la posición actual es ESTRICTAMENTE mejor.
    mejoraron = aptitudes < aptitudes_personales

    # np.where elige elemento a elemento y devuelve un arreglo NUEVO (copia, sin alias).
    # La máscara (N,) se vuelve columna (N, 1) para difundirse sobre las d dimensiones.
    nuevas_mejores = np.where(mejoraron[:, np.newaxis], posiciones, mejores_personales)
    nuevas_aptitudes = np.where(mejoraron, aptitudes, aptitudes_personales)
    return ResultadoMemoria(mejores_personales=nuevas_mejores,
                            aptitudes_personales=nuevas_aptitudes, mejoraron=mejoraron)


# %% [markdown]
# ## 5. `actualizar_mejor_global`
#
# El mejor global es el mejor de las **memorias personales** (no de las posiciones actuales):
#
# $$k = \operatorname*{arg\,min}_{i}\, f(b_i), \qquad g = b_k$$
#
# Con empate en $f(b_i)$ gana el índice menor (`np.argmin` devuelve la primera ocurrencia).
# La misma $g$ se usa para todas las partículas.

# %%
class MejorGlobal(NamedTuple):
    """Salida de `actualizar_mejor_global`.

    posicion : (d,) copia de la memoria personal ganadora.
    aptitud  : float, f(g).
    indice   : int, fila (partícula) que posee la memoria ganadora.
    """

    posicion: np.ndarray
    aptitud: float
    indice: int


def actualizar_mejor_global(mejores_personales: np.ndarray,
                            aptitudes_personales: np.ndarray) -> MejorGlobal:
    """Elige el mejor global $g$ entre las memorias personales.

    Parameters
    ----------
    mejores_personales : np.ndarray, forma (N, d)
        Memorias $b_i$; no se modifica.
    aptitudes_personales : np.ndarray, forma (N,)
        $f(b_i)$ alineada con las filas de `mejores_personales`.

    Returns
    -------
    MejorGlobal
        `posicion` (d,) es una COPIA; `aptitud` float; `indice` int (menor en empate).

    Raises
    ------
    ValueError
        Si las formas no son coherentes.
    """
    mejores_personales = validar_poblacion(mejores_personales, "mejores_personales")
    numero_de_particulas = mejores_personales.shape[0]
    aptitudes_personales = exigir_forma(aptitudes_personales, (numero_de_particulas,),
                                        "aptitudes_personales")

    # np.argmin devuelve el PRIMER índice del mínimo: el desempate es el índice menor.
    indice = int(np.argmin(aptitudes_personales))
    # `mejores_personales[indice]` es la FILA `indice` (una partícula, forma (d,)); `.copy()`
    # evita que modificar g altere la memoria del enjambre.
    posicion = mejores_personales[indice].copy()                 # forma (d,)
    return MejorGlobal(posicion=posicion, aptitud=float(aptitudes_personales[indice]),
                       indice=indice)


# %% [markdown]
# ## 6. `calcular_velocidades`
#
# Ecuación de velocidad con inercia, con $\odot$ el producto elemento a elemento:
#
# $$v_i \leftarrow w\, v_i \;+\; c_1\, R_1 \odot (b_i - x_i) \;+\; c_2\, R_2 \odot (g - x_i)$$
#
# - $w\,v_i$: **inercia** (conserva parte de la dirección anterior).
# - $c_1 R_1 \odot (b_i - x_i)$: atracción **cognitiva** hacia el mejor personal.
# - $c_2 R_2 \odot (g - x_i)$: atracción **social** hacia el mejor global.
# - $R_1, R_2 \sim \mathcal{U}(0,1)$, **distintos por partícula y por dimensión** y nuevos en cada
#   iteración; aquí se reciben ya sorteados (forma $(N, d)$) para poder reconstruir la ecuación
#   a mano. $g$ tiene forma $(d,)$ y se difunde sobre las $N$ filas.
#
# Este componente NO limita la velocidad: eso lo hace `limitar_velocidades`.

# %%
def calcular_velocidades(posiciones: np.ndarray, velocidades: np.ndarray,
                         mejores_personales: np.ndarray, mejor_global: np.ndarray,
                         inercia: float, coef_cognitivo: float, coef_social: float,
                         aleatorios_cognitivos: np.ndarray,
                         aleatorios_sociales: np.ndarray) -> np.ndarray:
    """Aplica la ecuación de velocidad del PSO a todo el enjambre (sin limitar).

    Es el corazón del algoritmo: combina memoria propia (cognitivo) y conocimiento colectivo
    (social). Ecuación pura y vectorizada: sin azar interno (R1 y R2 se inyectan).

    Parameters
    ----------
    posiciones : np.ndarray, forma (N, d)
        Posiciones actuales $x_i$.
    velocidades : np.ndarray, forma (N, d)
        Velocidades actuales $v_i$.
    mejores_personales : np.ndarray, forma (N, d)
        Mejores personales $b_i$.
    mejor_global : np.ndarray, forma (d,)
        Mejor global $g$ (la misma para todas las partículas).
    inercia, coef_cognitivo, coef_social : float
        $w$, $c_1$, $c_2$.
    aleatorios_cognitivos, aleatorios_sociales : np.ndarray, forma (N, d)
        $R_1$ y $R_2$ ya sorteados.

    Returns
    -------
    np.ndarray, forma (N, d)
        Velocidades nuevas (arreglo nuevo; las entradas no se modifican).

    Raises
    ------
    ValueError
        Si las formas no son coherentes con (N, d) y (d,).
    """
    posiciones = validar_poblacion(posiciones, "posiciones")
    forma = posiciones.shape                                         # (N, d)
    velocidades = exigir_forma(velocidades, forma, "velocidades")
    mejores_personales = exigir_forma(mejores_personales, forma, "mejores_personales")
    mejor_global = exigir_forma(mejor_global, (forma[1],), "mejor_global")
    aleatorios_cognitivos = exigir_forma(aleatorios_cognitivos, forma, "aleatorios_cognitivos")
    aleatorios_sociales = exigir_forma(aleatorios_sociales, forma, "aleatorios_sociales")

    # Término de inercia: parte de la velocidad anterior; forma (N, d).
    termino_inercia = inercia * velocidades

    # Distancia de cada partícula a su mejor personal; forma (N, d).
    hacia_mejor_personal = mejores_personales - posiciones
    termino_cognitivo = coef_cognitivo * aleatorios_cognitivos * hacia_mejor_personal

    # g tiene forma (d,): al restarle posiciones (N, d) se difunde (broadcasting) sobre las N
    # filas, o sea la misma g para todas las partículas; forma (N, d).
    hacia_mejor_global = mejor_global - posiciones
    termino_social = coef_social * aleatorios_sociales * hacia_mejor_global

    velocidades_nuevas = termino_inercia + termino_cognitivo + termino_social   # (N, d)
    return velocidades_nuevas


# %% [markdown]
# ## 7. `limitar_velocidades`
#
# Recorte componente a componente al intervalo $[-v_{\max,j},\, v_{\max,j}]$:
#
# $$v_{ij} \leftarrow \operatorname{clip}\big(v_{ij},\; -v_{\max,j},\; v_{\max,j}\big)$$
#
# Si no hay $v_{\max}$ (`None`) la velocidad no se toca.

# %%
def limitar_velocidades(velocidades: np.ndarray,
                        velocidad_maxima: np.ndarray | None) -> np.ndarray:
    """Recorta cada componente de la velocidad a ±`velocidad_maxima` de su dimensión.

    Evita pasos tan largos que lancen a la partícula fuera del dominio en cada iteración.

    Parameters
    ----------
    velocidades : np.ndarray, forma (N, d)
        Velocidades a limitar; no se modifica.
    velocidad_maxima : np.ndarray, forma (d,) | None
        `v_max` por dimensión; None = sin límite (se devuelve una copia sin cambio).

    Returns
    -------
    np.ndarray, forma (N, d)
        Arreglo nuevo con las velocidades limitadas.

    Raises
    ------
    ValueError
        Si `velocidad_maxima` no tiene forma (d,).
    """
    velocidades = validar_poblacion(velocidades, "velocidades")
    if velocidad_maxima is None:
        return velocidades.copy()

    velocidad_maxima = exigir_forma(velocidad_maxima, (velocidades.shape[1],),
                                    "velocidad_maxima")
    limite_inferior_velocidad = -velocidad_maxima                    # forma (d,)
    limite_superior_velocidad = velocidad_maxima                     # forma (d,)
    # np.clip con cotas de forma (d,) las aplica por columna (broadcasting sobre las N filas).
    return np.clip(velocidades, limite_inferior_velocidad, limite_superior_velocidad)


# %% [markdown]
# ## 8. `aplicar_frontera`
#
# Con la posición tentativa $x' = x + v$ y el dominio $[l_j, u_j]$, una componente que sale se
# **recorta a la frontera** y **solo su velocidad pasa a 0** (las demás no cambian):
#
# $$x'_{ij} \leftarrow \operatorname{clip}(x'_{ij},\, l_j,\, u_j), \qquad
#   v_{ij} \leftarrow 0 \;\text{ si } x'_{ij} < l_j \,\lor\, x'_{ij} > u_j$$
#
# Así ninguna posición evaluada sale del dominio.

# %%
class ResultadoFrontera(NamedTuple):
    """Salida de `aplicar_frontera` (arreglos nuevos, sin alias con las entradas).

    posiciones  : (N, d) posiciones recortadas al dominio.
    velocidades : (N, d) velocidades con 0 en las componentes que salieron.
    salieron    : (N, d) bool, True donde la posición tentativa estaba fuera del dominio.
    """

    posiciones: np.ndarray
    velocidades: np.ndarray
    salieron: np.ndarray


def aplicar_frontera(posiciones_tentativas: np.ndarray, velocidades: np.ndarray,
                     limites: np.ndarray) -> ResultadoFrontera:
    """Recorta al dominio las componentes que salieron y anula SU velocidad.

    Parameters
    ----------
    posiciones_tentativas : np.ndarray, forma (N, d)
        Posiciones $x + v$ antes de aplicar el dominio; no se modifica.
    velocidades : np.ndarray, forma (N, d)
        Velocidades (ya limitadas) que produjeron esas posiciones; no se modifica.
    limites : np.ndarray, forma (d, 2)
        Dominio `[mínimo, máximo]` por dimensión.

    Returns
    -------
    ResultadoFrontera
        `posiciones` (N, d), `velocidades` (N, d) y `salieron` (N, d) bool.

    Raises
    ------
    ValueError
        Si las formas no son coherentes con `limites`.
    """
    limites = validar_limites(limites)
    posiciones_tentativas = validar_poblacion(posiciones_tentativas, "posiciones_tentativas")
    velocidades = exigir_forma(velocidades, posiciones_tentativas.shape, "velocidades")
    if posiciones_tentativas.shape[1] != limites.shape[0]:
        raise ValueError(f"limites describe {limites.shape[0]} dimensiones pero las posiciones "
                         f"tienen {posiciones_tentativas.shape[1]}")

    limites_inferiores = limites[:, 0]                               # forma (d,)
    limites_superiores = limites[:, 1]                               # forma (d,)

    # Máscara (N, d): True en cada componente que quedó fuera del dominio. `<` y `>` comparan
    # cada fila (N, d) contra los límites (d,) columna a columna; `|` une las dos máscaras.
    salieron = ((posiciones_tentativas < limites_inferiores)
                | (posiciones_tentativas > limites_superiores))

    # np.clip recorta cada columna a su [inferior, superior] (nuevo arreglo).
    posiciones = np.clip(posiciones_tentativas, limites_inferiores, limites_superiores)
    # np.where pone 0 solo donde la máscara es True; las demás velocidades se conservan.
    velocidades_nuevas = np.where(salieron, 0.0, velocidades)
    return ResultadoFrontera(posiciones=posiciones, velocidades=velocidades_nuevas,
                             salieron=salieron)


# %% [markdown]
# ## 9. `optimize`: el orquestador
#
# Encadena los componentes siguiendo el Spec §6.4. Con $T$ iteraciones completas el conteo de
# evaluaciones es exacto (el enjambre inicial cuenta, Spec §6.2):
#
# $$n_f = N\,(T + 1), \qquad n_{\text{grad}} = 0, \qquad \text{eval\_equiv} = n_f$$
#
# El presupuesto $B$ corta la corrida: la iteración que no cabe se trunca en la evaluación
# exacta que lo excedería (`BudgetExhausted`), se descarta sin registrar frame y se devuelve el
# mejor punto visto. Con $B = 20\,000$ y $N = 30$ en 2D: $30 \cdot 666 = 19\,980$ más 20
# evaluaciones de la iteración truncada (665 iteraciones completas, frames `iter` 0 a 665).

# %%
def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Ejecuta el PSO gbest sobre `problem` hasta agotar el presupuesto (o `iteraciones`).

    Es el único componente que conoce `CountedProblem` y la configuración completa: lee el
    dominio y la dimensión de `problem.func`, delega cada fase en un componente y deja que
    `CountedProblem` cuente (nunca se cuenta a mano, Spec §6.2).

    Parameters
    ----------
    problem : CountedProblem
        Función envuelta con su contador y presupuesto; debe admitir al menos 1 evaluación.
    cfg : dict
        Configuración ya cargada: `cfg["pso"]` (bloque de parámetros) y `cfg["record_frames"]`.
    rng : np.random.Generator
        Única fuente de azar; se inyecta a la inicialización y a los sorteos R1 y R2.

    Returns
    -------
    dict
        Contrato §5.1: `x_best` (list), `f_best` (float), `n_f` (int), `n_grad` (int, siempre
        0), `eval_equiv` (float), `history` (copia de `problem.history`) y, solo si
        `problem.func.dim == 2` y `cfg["record_frames"]`, `frames`: un frame por iteración
        completada (iter 0 = enjambre inicial) con `best` = mejor GLOBAL $g$ hasta entonces.

    Raises
    ------
    ValueError
        Configuración inválida (ver `ParametrosPSO.desde_config`), falta `pso` o
        `record_frames`, o presupuesto que no alcanza para ninguna evaluación.
    TypeError
        Tipos incorrectos en la configuración.

    Notas
    -----
    Orden de consumo del rng (fijo): (1) `rng.uniform` de las posiciones (N, d), una vez;
    luego, por iteración, (2) `rng.random((N, d))` para R1 y (3) `rng.random((N, d))` para R2,
    en ese orden y antes de mover el enjambre.

    Con `iteraciones = None` el bucle no tiene tope propio: termina cuando `CountedProblem`
    lanza `BudgetExhausted` (se captura dentro de `optimize`). Por eso el presupuesto debe
    ser finito; `CountedProblem` ya rechaza un presupuesto infinito en su constructor.
    """
    # Paso 1: validar la configuración y leer el dominio del problema.
    parametros = ParametrosPSO.desde_config(leer_bloque(cfg, NOMBRE_BLOQUE_PSO))
    guardar_frames = leer_record_frames(cfg) and problem.func.dim == DIMENSION_CON_FRAMES
    limites = validar_limites(problem.func.bounds)                  # forma (d, 2)
    if problem.budget_exhausted():
        raise ValueError(f"el presupuesto ({problem.budget}) no alcanza para ninguna "
                         "evaluación de f")
    velocidad_maxima = calcular_velocidad_maxima(limites, parametros.fraccion_vmax)  # (d,)|None
    tamano = parametros.tamano_enjambre
    dimension = limites.shape[0]

    frames: list[dict] = []

    # Un solo try/except: si el presupuesto se agota en cualquier evaluación, la iteración
    # incompleta se descarta y se devuelve el mejor punto visto (patrón Spec §5.1, T0.4).
    try:
        # Paso 2: enjambre inicial (posiciones uniformes, velocidades en 0).
        enjambre = generar_enjambre_inicial(tamano, limites, rng)
        posiciones = enjambre.posiciones                             # forma (N, d)
        velocidades = enjambre.velocidades                           # forma (N, d)

        # Paso 3: evaluarlo (cuenta N evaluaciones, Spec §6.2).
        aptitudes = evaluar_poblacion(posiciones, problem.f)         # forma (N,)

        # Paso 4: memoria inicial b_i = x_i y mejor global g.
        mejores_personales = posiciones.copy()                       # forma (N, d)
        aptitudes_personales = aptitudes.copy()                      # forma (N,)
        mejor_global = actualizar_mejor_global(mejores_personales, aptitudes_personales)
        if guardar_frames:
            frames.append(construir_frame(0, posiciones, mejor_global.posicion))

        # Con `iteraciones = None` el bucle no tiene tope propio: termina cuando CountedProblem
        # lanza BudgetExhausted (se captura abajo). Por eso el presupuesto debe ser finito
        # (CountedProblem ya rechaza inf en su constructor).
        iteracion = 0
        while parametros.iteraciones is None or iteracion < parametros.iteraciones:
            iteracion += 1

            # Paso 5: sortear R1 y luego R2 (orden fijo del rng), forma (N, d) cada una.
            aleatorios_cognitivos = rng.random((tamano, dimension))
            aleatorios_sociales = rng.random((tamano, dimension))

            # Paso 6: ecuación de velocidad y límite de velocidad.
            velocidades_sin_limite = calcular_velocidades(
                posiciones, velocidades, mejores_personales, mejor_global.posicion,
                parametros.inercia, parametros.coef_cognitivo, parametros.coef_social,
                aleatorios_cognitivos, aleatorios_sociales,
            )                                                        # forma (N, d)
            velocidades_limitadas = limitar_velocidades(velocidades_sin_limite,
                                                        velocidad_maxima)

            # Paso 7: mover (posición tentativa) y aplicar la frontera del dominio.
            posiciones_tentativas = posiciones + velocidades_limitadas       # forma (N, d)
            frontera = aplicar_frontera(posiciones_tentativas, velocidades_limitadas, limites)
            posiciones = frontera.posiciones
            velocidades = frontera.velocidades

            # Paso 8: evaluar, actualizar memorias y mejor global; registrar el frame.
            aptitudes = evaluar_poblacion(posiciones, problem.f)     # forma (N,)
            memoria = actualizar_memoria_personal(posiciones, aptitudes, mejores_personales,
                                                  aptitudes_personales)
            mejores_personales = memoria.mejores_personales
            aptitudes_personales = memoria.aptitudes_personales
            mejor_global = actualizar_mejor_global(mejores_personales, aptitudes_personales)
            if guardar_frames:
                frames.append(construir_frame(iteracion, posiciones, mejor_global.posicion))
    except BudgetExhausted:
        # Presupuesto agotado: no se hace nada más. La iteración incompleta no registra frame y
        # el mejor punto visto está en problem.best_x / problem.best_f.
        pass

    # Paso 9: armar el retorno del contrato §5.1 con tipos nativos de Python.
    return construir_resultado(problem, frames, guardar_frames)
