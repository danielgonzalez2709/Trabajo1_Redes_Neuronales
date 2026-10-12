"""Modelo de costo de la Parte 2 (Spec §5.2 y §7.3 [DECIDIDO]).

Para cada par (i, j) y cada alternativa a ∈ {rapida, sin_peaje}:

    c_ij^a(w) = w · t_ij^a + P_ij^a + d_ij^a · (consumo / 100) · precio_l
    c_ij(w)   = mín(c_ij^rapida(w), c_ij^sin_peaje(w))

con w = valor de la hora (€/h), t en horas, P = peaje en €, d en km, consumo en l/100 km y precio_l en €/l.

Decisiones sobre huecos del Spec (propuestas, PENDIENTES de confirmación; no son [DECIDIDO]):
  - `Componentes` es un `dataclass` inmutable con seis matrices, `<columna>_<alternativa>`.
  - Desempate: si las dos alternativas cuestan exactamente lo mismo, se elige "rapida".
  - Diagonal de `alternativa_elegida`: "rapida". No es un caso especial: en la diagonal ambas alternativas cuestan 0
    y se aplica el desempate. El contrato solo admite {"rapida", "sin_peaje"}, así que no hay un tercer valor.

Simetría y diagonal son por construcción: `rutas.csv` guarda cada par una vez (i < j), la matriz se arma por espejo
(Spec §7.2 Bloque 2 asume c_ij = c_ji) y la diagonal vale 0.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

N_CIUDADES = 47  # Spec §5.2: C[47, 47] (las 47 capitales de cities.csv)
ALTERNATIVAS = ("rapida", "sin_peaje")  # Spec §5.3
COLUMNAS = ("tiempo_h", "dist_km", "peaje_eur")  # columnas de rutas.csv que lee el cargador (§7.3)
ARCHIVO_RUTAS = "rutas.csv"
CLAVE_CONSUMO = "consumo_wltp_comb_l100"  # clave de vehiculo.yaml (Spec §5.3)


@dataclass(frozen=True, eq=False)
class Componentes:
    """Componentes del costo por alternativa: matrices n×n simétricas con diagonal 0 (n = 47 con los datos reales).

    `tiempo_h_*` en horas, `dist_km_*` en km y `peaje_eur_*` en €. `eq=False`: `==` compara identidad (comparar
    matrices numpy campo a campo no da un bool).
    """

    tiempo_h_rapida: np.ndarray
    dist_km_rapida: np.ndarray
    peaje_eur_rapida: np.ndarray
    tiempo_h_sin_peaje: np.ndarray
    dist_km_sin_peaje: np.ndarray
    peaje_eur_sin_peaje: np.ndarray


def _leer_fila(fila: dict[str, str], donde: str) -> tuple[int, int, str, dict[str, float]]:
    """(i, j, alternativa, {columna: valor}) de una fila de rutas.csv; `ValueError` con `donde` si no es válida."""
    try:
        i, j = int(fila["i"]), int(fila["j"])
    except (TypeError, ValueError):
        raise ValueError(f"{donde}: i, j no son enteros: {fila['i']!r}, {fila['j']!r}") from None
    alt = fila["alternativa"]
    if alt not in ALTERNATIVAS:
        raise ValueError(f"{donde}: alternativa desconocida {alt!r}; se espera una de {ALTERNATIVAS}")
    if not 0 <= i < j < N_CIUDADES:
        raise ValueError(f"{donde}: se espera 0 <= i < j < {N_CIUDADES} y se recibió i={i}, j={j}")
    valores = {}
    for col in COLUMNAS:
        try:
            valores[col] = float(fila[col])
        except (TypeError, ValueError):
            raise ValueError(f"{donde}: {col} vacío o no numérico: {fila[col]!r}") from None
        if not math.isfinite(valores[col]):
            raise ValueError(f"{donde}: {col} no es finito: {fila[col]!r}")
    return i, j, alt, valores


def _pares_faltantes(vistas: set[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Filas (i, j, alternativa) con i < j que deberían estar en rutas.csv y no están."""
    return [(i, j, alt) for i in range(N_CIUDADES) for j in range(i + 1, N_CIUDADES) for alt in ALTERNATIVAS
            if (i, j, alt) not in vistas]


def cargar_componentes(path="data/processed") -> Componentes:
    """Lee `<path>/rutas.csv` y arma las seis matrices 47×47 (tiempo, distancia y peaje de ambas alternativas).

    `rutas.csv` guarda solo i < j: cada valor se copia a (i, j) y a (j, i); la diagonal es 0. Las matrices devueltas
    son de solo lectura. Lanza `FileNotFoundError` si no existe el archivo y `ValueError` si falta una columna, un
    par o una alternativa, si hay filas repetidas o fuera de i < j, o si un valor está vacío, no es numérico o es
    NaN/inf.
    """
    ruta = Path(path) / ARCHIVO_RUTAS
    with ruta.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        ausentes = [c for c in ("i", "j", "alternativa", *COLUMNAS) if c not in (lector.fieldnames or [])]
        if ausentes:
            raise ValueError(f"{ruta}: faltan las columnas {ausentes}")
        filas = list(lector)

    matrices = {(col, alt): np.full((N_CIUDADES, N_CIUDADES), np.nan) for col in COLUMNAS for alt in ALTERNATIVAS}
    vistas: set[tuple[int, int, str]] = set()
    for numero, fila in enumerate(filas, start=2):  # la línea 1 es el encabezado
        i, j, alt, valores = _leer_fila(fila, f"{ruta}, línea {numero}")
        if (i, j, alt) in vistas:
            raise ValueError(f"{ruta}, línea {numero}: fila repetida para el par ({i}, {j}, {alt!r})")
        vistas.add((i, j, alt))
        for col, valor in valores.items():
            matrices[col, alt][i, j] = matrices[col, alt][j, i] = valor  # espejo: rutas.csv guarda solo i < j

    faltantes = _pares_faltantes(vistas)
    if faltantes:
        raise ValueError(f"{ruta}: faltan {len(faltantes)} filas (i, j, alternativa): {faltantes}")

    for m in matrices.values():
        np.fill_diagonal(m, 0.0)
        m.flags.writeable = False
    return Componentes(**{f"{col}_{alt}": m for (col, alt), m in matrices.items()})


def _finito_no_negativo(valor, nombre: str) -> float:
    """`valor` como float si es finito y >= 0 (el 0 se admite); si no, `ValueError`."""
    valor = float(valor)
    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nombre} debe ser finito y >= 0; se recibió {valor}")
    return valor


def _costo_alternativa(tiempo_h, dist_km, peaje_eur, valor_hora, consumo, precio_l):
    """Spec §7.3: c^a = w · t^a + P^a + d^a · (consumo / 100) · precio_l."""
    return valor_hora * tiempo_h + peaje_eur + dist_km * (consumo / 100) * precio_l


def matriz_costos(comp: Componentes, valor_hora: float, vehiculo: dict,
                  precio_l: float) -> tuple[np.ndarray, np.ndarray]:
    """Matriz de costos C (en €) y alternativa elegida en cada celda (Spec §7.3).

    Devuelve `(C, alternativa_elegida)`, ambas n×n (47×47 con los datos reales): `C[i, j]` es el menor de los costos
    de las dos alternativas y `alternativa_elegida[i, j]` ∈ {"rapida", "sin_peaje"} dice cuál fue. En un empate
    exacto (incluida la diagonal, donde ambas cuestan 0) se elige "rapida".

    `valor_hora` es w en €/h, `precio_l` en €/l y el consumo (l/100 km) se lee de `vehiculo["consumo_wltp_comb_l100"]`
    (`KeyError` si falta). Los tres deben ser finitos y >= 0 (`ValueError` si no). Función pura: no lee archivos, no
    guarda estado y no modifica sus argumentos.
    """
    w = _finito_no_negativo(valor_hora, "valor_hora")
    consumo = _finito_no_negativo(vehiculo[CLAVE_CONSUMO], CLAVE_CONSUMO)
    precio = _finito_no_negativo(precio_l, "precio_l")

    rapida = _costo_alternativa(comp.tiempo_h_rapida, comp.dist_km_rapida, comp.peaje_eur_rapida, w, consumo, precio)
    sin_peaje = _costo_alternativa(comp.tiempo_h_sin_peaje, comp.dist_km_sin_peaje, comp.peaje_eur_sin_peaje,
                                   w, consumo, precio)

    gana_sin_peaje = sin_peaje < rapida  # estricto: el empate es para "rapida"
    c = np.where(gana_sin_peaje, sin_peaje, rapida)
    elegida = np.where(gana_sin_peaje, "sin_peaje", "rapida")
    return c, elegida
