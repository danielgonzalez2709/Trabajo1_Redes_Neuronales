# %% [markdown]
# # Métricas de la Parte 1 (T1.7; Spec §5.4, §6.2, §6.5 y §6.6)
#
# **Propósito.** Convertir las corridas de UNA configuración (función, dimensión, método) en
# las estadísticas de Spec §6.6, detectar resultados sospechosos y dar formato a las tablas.
#
# **Entrada.** Cada corrida es un diccionario con la forma de Spec §5.4:
# `{"func", "dim", "method", "seed", "k", "budget", "config", "result"}`, donde `result` es el
# retorno de `optimize` (Spec §5.1). Este módulo no ejecuta optimizadores ni evalúa funciones:
# solo lee esos diccionarios. De la función de prueba usa únicamente su `f_star`.
#
# **Mapa de utilidades** (funciones puras: no leen ni escriben archivos y no muestran nada):
#
# | # | Utilidad | Qué hace | Retorna |
# |---|---|---|---|
# | 1 | `clave_umbral` | nombre de texto de un umbral de éxito | `str` |
# | 2 | `resumir_configuracion` | estadísticas de §6.6 de una configuración | `dict` |
# | 3 | `avisos` | textos sobre resultados sospechosos | `list[str]` |
# | 4 | `formatear_tabla_consola` | tabla de texto con columnas alineadas | `str` |
# | 5 | `a_filas_csv` | una fila plana por configuración | `list[dict]` |
#
# **Valores indefinidos.** La salida no lleva NaN ni infinitos (Spec §5.4 los prohíbe en los
# JSON): lo que no se puede calcular vale `None`. Los números son `int` y `float` de Python.

# %%
"""Métricas de la Parte 1: resumen por configuración, avisos y formato de tablas (Spec §6.6)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

# METODOS_SIN_GRADIENTE: métodos en los que se espera n_grad == 0. FACTOR_K_PRINCIPAL: el 2
# de la regla k = 2n (Spec §6.2).
from src.part1.corrida import FACTOR_K_PRINCIPAL, METODOS_SIN_GRADIENTE
from src.part1.functions import get_function

# %% [markdown]
# ## Constantes del módulo
#
# Los umbrales de éxito son los de Spec §6.5: el principal ($10^{-4}$) y los dos que también
# se reportan ($10^{-2}$ y $10^{-6}$). Las demás, por grupo:
#
# | Grupo | Constantes |
# |---|---|
# | avisos | `TOLERANCIA_BAJO_F_STAR`, `METODO_SIN_F`, `TASA_TOTAL` |
# | resumen | `CAMPOS_DE_CONFIGURACION`, `DDOF_MUESTRAL` |
# | tabla de consola | `INDEFINIDO`, `SEPARADOR_DE_COLUMNAS`, `FORMATO_*` |
# | filas CSV | `SEPARADOR_DE_CLAVES` |
#
# `METODOS_SIN_GRADIENTE` y `FACTOR_K_PRINCIPAL` se importan de `corrida.py`.

# %%
UMBRAL_PRINCIPAL = 1e-4                       # §6.5: éxito si f − f* <= 1e-4
UMBRALES = (UMBRAL_PRINCIPAL, 1e-2, 1e-6)     # §6.5: el principal y los dos adicionales
TOLERANCIA_BAJO_F_STAR = 1e-9                 # margen del aviso "f_best por debajo de f*"
METODO_SIN_F = "gdfijo"                       # método en el que se espera n_f == 0

CAMPOS_DE_CONFIGURACION = ("func", "dim", "method", "k")   # deben coincidir en las corridas
DDOF_MUESTRAL = 1                             # `ddof` de numpy: la desviación divide entre n − 1
TASA_TOTAL = 1.0                              # tasa de éxito del 100 %

INDEFINIDO = "—"                              # texto de la tabla para un valor None
SEPARADOR_DE_COLUMNAS = " | "
FORMATO_F = ".3e"                             # f_final en la tabla de consola
FORMATO_CONTEO = ".1f"                        # n_f y n_grad medios en la tabla de consola
FORMATO_PORCENTAJE = ".1f"                    # tasa de éxito en la tabla, en porcentaje
SEPARADOR_DE_CLAVES = "_"                     # une las claves anidadas en las filas planas


# %% [markdown]
# ## 1. `clave_umbral`
#
# Las claves de los diccionarios guardados deben ser texto (Spec §5.4), así que cada umbral se
# nombra con su notación científica sin decimales: `1e-04`, `1e-02`, `1e-06`.

# %%
def clave_umbral(umbral: float) -> str:
    """Clave de texto de un umbral de éxito: `clave_umbral(1e-4) == "1e-04"`."""
    return f"{umbral:.0e}"


# %% [markdown]
# ## Auxiliares de `resumir_configuracion`
#
# **Éxito.** Una corrida es exitosa para el umbral $u$ si
#
# $$f_{\text{best}} - f^* \le u$$
#
# (la igualdad cuenta como éxito). **Evaluaciones hasta el éxito:** `history` guarda un punto
# cada vez que mejora el mejor valor visto (Spec §5.1), en orden; se toma el `eval_equiv` del
# PRIMER punto que cumple la condición.

# %%
def _finito_o_none(valor) -> float | None:
    """Devuelve `valor` como float de Python, o None si es NaN o infinito."""
    numero = float(valor)
    return numero if math.isfinite(numero) else None


def _media(valores: Sequence[float]) -> float | None:
    """Media aritmética como float de Python; None si no hay valores o no es finita."""
    if len(valores) == 0:
        return None
    return _finito_o_none(np.mean(np.asarray(valores, dtype=float)))


def _valor_comun(corridas: Sequence[Mapping], campo: str):
    """Devuelve `corrida[campo]` si es igual en todas las corridas; si no, ValueError."""
    valores = [corrida[campo] for corrida in corridas]
    distintos = [valor for valor in valores if valor != valores[0]]
    if distintos:
        raise ValueError(
            f"las corridas mezclan valores de '{campo}': {valores[0]!r} y {distintos[0]!r}; "
            "resumir_configuracion recibe las corridas de UNA sola configuración"
        )
    return valores[0]


def _es_exito(f_best: float, f_star: float, umbral: float) -> bool:
    """Condición de éxito de §6.5: f_best − f* <= umbral (la igualdad cuenta)."""
    return f_best - f_star <= umbral


def _evals_hasta_exito(corrida: Mapping, f_star: float, umbral: float) -> float:
    """`eval_equiv` del primer punto de `history` con f_best − f* <= umbral.

    Se llama solo con corridas exitosas para `umbral`. Si ningún punto de la historia cumple
    (historia que no coincide con el `f_best` final), lanza ValueError.
    """
    for punto in corrida["result"]["history"]:
        if _es_exito(punto["f_best"], f_star, umbral):
            return float(punto["eval_equiv"])
    raise ValueError(
        f"corrida {corrida['func']} {corrida['dim']}D {corrida['method']} semilla "
        f"{corrida['seed']}: f_best cumple el umbral {clave_umbral(umbral)} pero ningún "
        "punto de result['history'] lo cumple"
    )


def _estadisticas_f_final(f_finales: Sequence[float]) -> dict:
    """Media, desviación muestral, mediana, mejor (mínimo) y peor (máximo) de `f_finales`."""
    valores = np.asarray(f_finales, dtype=float)
    # Con una sola corrida la desviación muestral divide entre 0: queda indefinida (None).
    if valores.size > DDOF_MUESTRAL:
        desviacion = _finito_o_none(np.std(valores, ddof=DDOF_MUESTRAL))
    else:
        desviacion = None
    return {
        "media": _finito_o_none(np.mean(valores)),
        "desv": desviacion,
        "mediana": _finito_o_none(np.median(valores)),
        "mejor": _finito_o_none(np.min(valores)),
        "peor": _finito_o_none(np.max(valores)),
    }


# %% [markdown]
# ## 2. `resumir_configuracion`
#
# Estadísticas de Spec §6.6 sobre las $R$ corridas de una configuración. La desviación es la
# muestral:
#
# $$s = \sqrt{\frac{1}{R - 1} \sum_{r=1}^{R} \left(f_r - \bar f\right)^2}$$
#
# Las evaluaciones equivalentes (Spec §6.2) se dan de tres formas, con $n$ la dimensión:
#
# | Campo | Fórmula por corrida | $k$ |
# |---|---|---|
# | `eval_equiv_medio` | `result["eval_equiv"]` | el de la corrida |
# | `eval_equiv_medio_k2n` | $n_f + 2n \cdot n_{\text{grad}}$ | $2n$ (recosteo) |
# | `eval_equiv_medio_k1` | $n_f + n_{\text{grad}}$ | $1$ (recosteo) |
#
# `evals_hasta_exito_medio` se lee de `history`, cuyos `eval_equiv` están medidos con el $k$
# de la corrida: ese campo no se recostea.

# %%
def resumir_configuracion(corridas: Sequence[Mapping]) -> dict:
    """Resume las corridas de UNA configuración (func, dim, method) según Spec §6.6.

    Parameters
    ----------
    corridas : secuencia de dict
        Corridas con la forma de Spec §5.4. Todas deben compartir `func`, `dim`, `method`
        y `k`. No se modifican.

    Returns
    -------
    dict
        Con estas claves, en este orden: `func`, `dim`, `method`, `k`, `n_corridas`;
        `f_final` = {`media`, `desv` (muestral; None con una sola corrida), `mediana`,
        `mejor`, `peor`} de `result["f_best"]`; `n_f_medio`, `n_grad_medio`;
        `eval_equiv_medio`, `eval_equiv_medio_k2n`, `eval_equiv_medio_k1`;
        `tasa_exito` = {clave de umbral: fracción de corridas exitosas};
        `evals_hasta_exito_medio` = {clave de umbral: media sobre las corridas exitosas, o
        None si no hay ninguna}.

    Raises
    ------
    ValueError
        Si la lista está vacía, si las corridas mezclan `func`, `dim`, `method` o `k`, o si
        una corrida exitosa no tiene en `history` ningún punto que cumpla el umbral.
    """
    if len(corridas) == 0:
        raise ValueError("la lista de corridas está vacía: no hay nada que resumir")
    func, dim, method, k = (_valor_comun(corridas, campo) for campo in CAMPOS_DE_CONFIGURACION)
    dim = int(dim)
    f_star = get_function(func, dim).f_star

    resultados = [corrida["result"] for corrida in corridas]
    f_finales = [resultado["f_best"] for resultado in resultados]
    n_f = [resultado["n_f"] for resultado in resultados]
    n_grad = [resultado["n_grad"] for resultado in resultados]

    # Recosteo de §6.2 con los contadores de cada corrida: k = 2n y k = 1.
    equiv_k2n = [evaluaciones + FACTOR_K_PRINCIPAL * dim * gradientes
                 for evaluaciones, gradientes in zip(n_f, n_grad)]
    equiv_k1 = [evaluaciones + gradientes for evaluaciones, gradientes in zip(n_f, n_grad)]

    tasa_exito = {}
    evals_hasta_exito_medio = {}
    for umbral in UMBRALES:
        exitosas = [corrida for corrida in corridas
                    if _es_exito(corrida["result"]["f_best"], f_star, umbral)]
        clave = clave_umbral(umbral)
        tasa_exito[clave] = len(exitosas) / len(corridas)
        # _media devuelve None si ninguna corrida fue exitosa (lista vacía).
        evals_hasta_exito_medio[clave] = _media(
            [_evals_hasta_exito(corrida, f_star, umbral) for corrida in exitosas])

    return {
        "func": str(func),
        "dim": dim,
        "method": str(method),
        "k": float(k),
        "n_corridas": len(corridas),
        "f_final": _estadisticas_f_final(f_finales),
        "n_f_medio": _media(n_f),
        "n_grad_medio": _media(n_grad),
        "eval_equiv_medio": _media([resultado["eval_equiv"] for resultado in resultados]),
        "eval_equiv_medio_k2n": _media(equiv_k2n),
        "eval_equiv_medio_k1": _media(equiv_k1),
        "tasa_exito": tasa_exito,
        "evals_hasta_exito_medio": evals_hasta_exito_medio,
    }


# %% [markdown]
# ## 3. `avisos`
#
# Señales de que un resultado merece revisión antes de publicarlo:
#
# | Tipo | Condición | Se lee de |
# |---|---|---|
# | (a) | alguna corrida con $f_{\text{best}} < f^* - 10^{-9}$ | corridas |
# | (b) | tasa de éxito del 100 % en TODOS los umbrales | resumen |
# | (c) | `n_grad > 0` en `ea`/`pso`/`de`, o `n_f > 0` en `gdfijo` | corridas |
# | (d) | alguna corrida con `eval_equiv > budget` | corridas |
#
# Los tipos (a), (c) y (d) dan un texto por configuración y contador afectado, con el número
# de corridas afectadas y sus semillas. El tipo (b) da un texto por resumen y no nombra
# semillas. En (a), (c) y (d) el nombre de la configuración se toma de la primera corrida
# de su lista; en (b), del resumen.

# %%
def _nombre_configuracion(datos: Mapping) -> str:
    """Texto que identifica una configuración: "rastrigin 2D pso"."""
    return f"{datos['func']} {datos['dim']}D {datos['method']}"


def _texto_semillas(corridas: Sequence[Mapping]) -> str:
    """Semillas de `corridas`, en el orden recibido: "semillas: 0, 4"."""
    return "semillas: " + ", ".join(str(corrida["seed"]) for corrida in corridas)


def _bajo_f_star(corrida: Mapping) -> bool:
    """Tipo (a): f_best < f* − TOLERANCIA_BAJO_F_STAR."""
    f_star = get_function(corrida["func"], corrida["dim"]).f_star
    return corrida["result"]["f_best"] < f_star - TOLERANCIA_BAJO_F_STAR


def _contador_inesperado(corrida: Mapping) -> str | None:
    """Tipo (c): nombre del contador que debería ser 0 y no lo es; None si no aplica."""
    if corrida["method"] in METODOS_SIN_GRADIENTE and corrida["result"]["n_grad"] > 0:
        return "n_grad"
    if corrida["method"] == METODO_SIN_F and corrida["result"]["n_f"] > 0:
        return "n_f"
    return None


def _sobre_presupuesto(corrida: Mapping) -> bool:
    """Tipo (d): eval_equiv > budget."""
    return corrida["result"]["eval_equiv"] > corrida["budget"]


def avisos(resumenes: Sequence[Mapping],
           corridas_por_configuracion: Sequence[Sequence[Mapping]]) -> list[str]:
    """Textos (en español) sobre resultados sospechosos de todo el experimento.

    Parameters
    ----------
    resumenes : secuencia de dict
        Un retorno de `resumir_configuracion` por configuración. Solo se usa para el tipo (b).
    corridas_por_configuracion : secuencia de secuencias de dict
        Una lista de corridas (Spec §5.4) por configuración. Se usa para los tipos (a), (c)
        y (d). Las dos secuencias se recorren por separado: no se exige que tengan la misma
        longitud ni el mismo orden.

    Returns
    -------
    list[str]
        Lista vacía si no hay nada sospechoso. Orden: primero todos los avisos de tipo (a),
        luego (b), (c) y (d); dentro de cada tipo, el orden de las configuraciones recibidas.
        No usa azar: la misma entrada da la misma lista.

    Notas
    -----
    Un resultado sospechoso se informa con un texto, no con una excepción. Las entradas deben
    tener las claves de Spec §5.4 y de `resumir_configuracion`; no se modifican.
    """
    textos_bajo_f_star = []
    textos_contadores = []
    textos_presupuesto = []
    for corridas in corridas_por_configuracion:
        if len(corridas) == 0:
            continue
        nombre = _nombre_configuracion(corridas[0])

        por_debajo = [corrida for corrida in corridas if _bajo_f_star(corrida)]
        if por_debajo:
            textos_bajo_f_star.append(
                f"{nombre}: {len(por_debajo)} corrida(s) con f_best < f* − "
                f"{TOLERANCIA_BAJO_F_STAR:g} ({_texto_semillas(por_debajo)})")

        for contador in ("n_grad", "n_f"):
            afectadas = [corrida for corrida in corridas
                         if _contador_inesperado(corrida) == contador]
            if afectadas:
                textos_contadores.append(
                    f"{nombre}: {len(afectadas)} corrida(s) con {contador} > 0 en un método "
                    f"que no debería usarlo ({_texto_semillas(afectadas)})")

        pasadas = [corrida for corrida in corridas if _sobre_presupuesto(corrida)]
        if pasadas:
            textos_presupuesto.append(
                f"{nombre}: {len(pasadas)} corrida(s) con eval_equiv mayor que el "
                f"presupuesto ({_texto_semillas(pasadas)})")

    umbrales = ", ".join(clave_umbral(umbral) for umbral in UMBRALES)
    textos_exito_total = []
    for resumen in resumenes:
        tasas = [resumen["tasa_exito"][clave_umbral(umbral)] for umbral in UMBRALES]
        if all(tasa == TASA_TOTAL for tasa in tasas):
            textos_exito_total.append(
                f"{_nombre_configuracion(resumen)}: tasa de éxito del 100 % en todos los "
                f"umbrales ({umbrales}) sobre {resumen['n_corridas']} corrida(s)")

    return textos_bajo_f_star + textos_exito_total + textos_contadores + textos_presupuesto


# %% [markdown]
# ## 4. `formatear_tabla_consola`
#
# Una línea de cabecera y una por configuración. Columnas: función, dimensión, método,
# media ± desviación de `f_final`, mediana, tasa de éxito del umbral principal y `n_f` y
# `n_grad` medios. Un valor `None` se escribe como "—".

# %%
def _texto_numero(valor: float | None, formato: str) -> str:
    """Número con el formato pedido, o INDEFINIDO si es None."""
    return INDEFINIDO if valor is None else format(valor, formato)


def _texto_porcentaje(fraccion: float) -> str:
    """Fracción en [0, 1] como porcentaje: 0.6 se escribe "60.0 %"."""
    return f"{format(100 * fraccion, FORMATO_PORCENTAJE)} %"


def _celdas_de_resumen(resumen: Mapping) -> list[str]:
    """Textos de una fila de la tabla, en el orden de las columnas."""
    f_final = resumen["f_final"]
    media_y_desviacion = (f"{_texto_numero(f_final['media'], FORMATO_F)} ± "
                          f"{_texto_numero(f_final['desv'], FORMATO_F)}")
    return [
        str(resumen["func"]),
        str(resumen["dim"]),
        str(resumen["method"]),
        media_y_desviacion,
        _texto_numero(f_final["mediana"], FORMATO_F),
        _texto_porcentaje(resumen["tasa_exito"][clave_umbral(UMBRAL_PRINCIPAL)]),
        _texto_numero(resumen["n_f_medio"], FORMATO_CONTEO),
        _texto_numero(resumen["n_grad_medio"], FORMATO_CONTEO),
    ]


def formatear_tabla_consola(resumenes: Sequence[Mapping]) -> str:
    """Tabla de texto con columnas alineadas: cabecera y una línea por resumen.

    Las líneas se separan con "\\n" y la última no termina en salto de línea. Todas tienen
    el mismo largo: cada celda se rellena con espacios hasta el ancho de su columna.
    """
    cabecera = ["función", "dim", "método", "f_final media ± desv", "mediana",
                f"éxito {clave_umbral(UMBRAL_PRINCIPAL)}", "n_f medio", "n_grad medio"]
    filas = [cabecera] + [_celdas_de_resumen(resumen) for resumen in resumenes]

    # Ancho de cada columna: el de su celda más larga, contando la cabecera.
    anchos = [max(len(fila[columna]) for fila in filas) for columna in range(len(cabecera))]
    lineas = [SEPARADOR_DE_COLUMNAS.join(celda.ljust(ancho)
                                         for celda, ancho in zip(fila, anchos))
              for fila in filas]
    return "\n".join(lineas)


# %% [markdown]
# ## 5. `a_filas_csv`
#
# Aplana cada resumen: los diccionarios anidados (`f_final`, `tasa_exito`,
# `evals_hasta_exito_medio`) pasan a claves `padre_hija`, por ejemplo `f_final_media` o
# `tasa_exito_1e-04`. Los `None` se conservan.

# %%
def a_filas_csv(resumenes: Sequence[Mapping]) -> list[dict]:
    """Una fila plana (dict sin anidar, claves de texto) por resumen, en el mismo orden."""
    filas = []
    for resumen in resumenes:
        fila = {}
        for clave, valor in resumen.items():
            if isinstance(valor, Mapping):
                # Un nivel de anidación: cada clave hija se une a la del padre.
                for clave_hija, valor_hijo in valor.items():
                    fila[f"{clave}{SEPARADOR_DE_CLAVES}{clave_hija}"] = valor_hijo
            else:
                fila[clave] = valor
        filas.append(fila)
    return filas
