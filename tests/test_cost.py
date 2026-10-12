"""Modelo de costo de la Parte 2 (T3.1; Spec §5.2 y §7.3). Solo lee archivos versionados; no usa internet.

    c_ij^a(w) = w · t_ij^a + P_ij^a + d_ij^a · (consumo / 100) · precio_l        a ∈ {rapida, sin_peaje}
    c_ij(w)   = mín(c_ij^rapida, c_ij^sin_peaje)

Qué comprueba (criterios de aceptación de §7.3, v1.11):
  1. Pares calculados a mano (valores literales copiados de rutas.csv y resultados escritos como números).
  2. Con w = 0 se elige, en cada par, la alternativa de menor `peaje + combustible`, incluidos los pares cuya
     `sin_peaje` también paga peaje.
  3. Diagonal 0 y simetría: cada celda (i, j) y (j, i) toma los valores de la fila correcta de rutas.csv.
  4. Casos sintéticos de 3 ciudades: fórmula, mínimo, suma frente a solo peaje y desempate.
  5. Sensibilidad a `valor_hora`, `consumo` y `precio_l`, y rechazo de valores negativos o no finitos.
  6. `cargar_componentes` falla con un error claro ante datos incompletos (copias rotas en `tmp_path`).

NO repite lo que ya comprueba test_data_integrity.py sobre rutas.csv (matrices completas, finitas y positivas, cota
ortodrómica, asimetría medida): aquí rutas.csv se lee por separado con `csv` solo como referencia independiente.
"""

from __future__ import annotations

import csv
import dataclasses
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.part2.costos import Componentes, cargar_componentes, matriz_costos

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"

N = 47  # Spec §5.2: C[47, 47]
ALTERNATIVAS = ("rapida", "sin_peaje")
COLUMNAS = ("tiempo_h", "dist_km", "peaje_eur")

# Parámetros de las pruebas con cifras a mano. Son los valores de vehiculo.yaml y combustible.json en la fecha de
# corte; `test_los_literales_son_los_de_los_datos` avisa si los datos cambian y hay que rehacer las cuentas.
CONSUMO = 4.6       # l/100 km
PRECIO = 1.8318     # €/l
VEHICULO = {"consumo_wltp_comb_l100": CONSUMO}

# Filas literales de rutas.csv: (dist_km, tiempo_h, peaje_eur). Ids de cities.csv: 0 Vitoria-Gasteiz, 3 Almería,
# 11 Ciudad Real, 29 Pamplona/Iruña, 32 Palencia, 44 Bilbao.
FILAS_A_MANO = {
    (0, 44, "rapida"): (65.3703, 0.898389, 6.85),
    (0, 44, "sin_peaje"): (69.6506, 1.285139, 0.00),
    (3, 32, "rapida"): (800.3119, 9.046444, 19.75),
    (3, 32, "sin_peaje"): (786.9778, 9.325611, 1.00),
    (11, 29, "rapida"): (584.4743, 7.043806, 9.49),
    (11, 29, "sin_peaje"): (584.3346, 7.102750, 5.73),
}

# Tolerancias: las cifras a mano están escritas con 6 decimales; el resto solo absorbe el error de coma flotante.
TOL_MANO = 1e-5
RTOL = 1e-12


# --- Carga -------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def filas() -> list[dict[str, str]]:
    with (PROC / "rutas.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def comp() -> Componentes:
    return cargar_componentes(PROC)


def _campo(c: Componentes, columna: str, alternativa: str) -> np.ndarray:
    return getattr(c, f"{columna}_{alternativa}")


def _costo_fila(f: dict[str, str], w: float, consumo: float = CONSUMO, precio: float = PRECIO) -> float:
    """Costo de una fila de rutas.csv con aritmética escalar de Python (referencia independiente de numpy)."""
    return w * float(f["tiempo_h"]) + float(f["peaje_eur"]) + float(f["dist_km"]) * (consumo / 100) * precio


def _por_par(filas: list[dict[str, str]]) -> dict[tuple[int, int], dict[str, dict[str, str]]]:
    pares: dict[tuple[int, int], dict[str, dict[str, str]]] = {}
    for f in filas:
        pares.setdefault((int(f["i"]), int(f["j"])), {})[f["alternativa"]] = f
    return pares


def _sintetico(t_r, d_r, p_r, t_s, d_s, p_s) -> Componentes:
    """Componentes de 3 ciudades a partir de los valores de los pares en orden (0,1), (0,2), (1,2)."""
    filas_, cols = np.triu_indices(3, k=1)

    def m(valores):
        a = np.zeros((3, 3))
        a[filas_, cols] = valores
        return a + a.T

    return Componentes(tiempo_h_rapida=m(t_r), dist_km_rapida=m(d_r), peaje_eur_rapida=m(p_r),
                       tiempo_h_sin_peaje=m(t_s), dist_km_sin_peaje=m(d_s), peaje_eur_sin_peaje=m(p_s))


# --- Contrato (§5.2) ---------------------------------------------------------------------------------------------


def test_componentes_es_inmutable_y_tiene_seis_matrices_47x47(comp):
    campos = [c.name for c in dataclasses.fields(comp)]
    assert sorted(campos) == sorted(f"{col}_{alt}" for col in COLUMNAS for alt in ALTERNATIVAS)
    for nombre in campos:
        m = getattr(comp, nombre)
        assert isinstance(m, np.ndarray) and m.shape == (N, N) and m.dtype == np.float64
        with pytest.raises(ValueError):
            m[0, 1] = 1.0  # las matrices cargadas son de solo lectura
    with pytest.raises(dataclasses.FrozenInstanceError):
        comp.tiempo_h_rapida = np.zeros((N, N))
    assert comp == comp  # eq=False: identidad, sin comparar matrices campo a campo


def test_matriz_costos_devuelve_c_y_alternativa_con_la_forma_del_contrato(comp):
    c, alt = matriz_costos(comp, 25, VEHICULO, PRECIO)
    assert isinstance(c, np.ndarray) and c.shape == (N, N) and c.dtype == np.float64
    assert isinstance(alt, np.ndarray) and alt.shape == (N, N)
    assert set(np.unique(alt).tolist()) == set(ALTERNATIVAS)
    assert np.isfinite(c).all()


def test_el_valor_por_defecto_de_path_es_data_processed(comp, monkeypatch):
    monkeypatch.chdir(RAIZ)
    por_defecto = cargar_componentes()
    for campo in dataclasses.fields(comp):
        assert np.array_equal(getattr(por_defecto, campo.name), getattr(comp, campo.name))


def test_matriz_costos_es_pura_y_no_modifica_sus_entradas(comp):
    antes = {c.name: getattr(comp, c.name).copy() for c in dataclasses.fields(comp)}
    vehiculo = dict(VEHICULO)
    c1, a1 = matriz_costos(comp, 25, vehiculo, PRECIO)
    c2, a2 = matriz_costos(comp, 25, vehiculo, PRECIO)
    assert np.array_equal(c1, c2) and np.array_equal(a1, a2)
    assert vehiculo == VEHICULO
    assert all(np.array_equal(getattr(comp, k), v) for k, v in antes.items())


# --- 1. Pares calculados a mano ----------------------------------------------------------------------------------


def test_los_literales_son_los_de_los_datos(filas):
    """Si rutas.csv, vehiculo.yaml o combustible.json cambian, las cuentas a mano de este archivo hay que rehacerlas."""
    por_clave = {(int(f["i"]), int(f["j"]), f["alternativa"]): f for f in filas}
    for clave, (dist, tiempo, peaje) in FILAS_A_MANO.items():
        f = por_clave[clave]
        assert (float(f["dist_km"]), float(f["tiempo_h"]), float(f["peaje_eur"])) == (dist, tiempo, peaje), clave
    assert yaml.safe_load((PROC / "vehiculo.yaml").read_text(encoding="utf-8"))["consumo_wltp_comb_l100"] == CONSUMO
    assert json.loads((PROC / "combustible.json").read_text(encoding="utf-8"))["precio_medio_eur_l"] == PRECIO


def test_par_a_mano_vitoria_bilbao_cambia_de_alternativa_entre_w_bajo_y_w_alto(comp):
    """Par (0, 44) = Vitoria-Gasteiz–Bilbao (ids de cities.csv). Combustible por km = 4,6 / 100 · 1,8318 = 0,0842628 €/km.

    rapida:    65,3703 km · 0,0842628 = 5,508285 €;  + peaje 6,85  → 12,358285 € sin tiempo
    sin_peaje: 69,6506 km · 0,0842628 = 5,868955 €;  + peaje 0,00  →  5,868955 € sin tiempo
    Cruce: w* = (12,358285 − 5,868955) / (1,285139 − 0,898389) = 6,489330 / 0,386750 = 16,779 €/h.

    w = 10: rapida 10 · 0,898389 + 12,358285 = 21,342175;  sin_peaje 10 · 1,285139 + 5,868955 = 18,720345 → sin_peaje
    w = 25: rapida 25 · 0,898389 + 12,358285 = 34,818010;  sin_peaje 25 · 1,285139 + 5,868955 = 37,997430 → rapida
    """
    # Comprueba que las cifras del docstring salen de la fórmula con los literales de FILAS_A_MANO.
    rapida_10 = 10 * 0.898389 + 6.85 + 65.3703 * (4.6 / 100) * 1.8318
    sin_peaje_10 = 10 * 1.285139 + 0.00 + 69.6506 * (4.6 / 100) * 1.8318
    assert rapida_10 == pytest.approx(21.342175, abs=TOL_MANO)
    assert sin_peaje_10 == pytest.approx(18.720345, abs=TOL_MANO)

    c, alt = matriz_costos(comp, 10, VEHICULO, PRECIO)
    assert c[0, 44] == pytest.approx(18.720345, abs=TOL_MANO)
    assert alt[0, 44] == "sin_peaje"

    c, alt = matriz_costos(comp, 25, VEHICULO, PRECIO)
    assert c[0, 44] == pytest.approx(34.818010, abs=TOL_MANO)
    assert alt[0, 44] == "rapida"


def test_par_a_mano_a_ambos_lados_del_cruce(comp):
    """Mismo par (0, 44), Vitoria-Gasteiz–Bilbao: el cruce está en w* = 16,779 €/h; a 16,7 gana sin_peaje y a 16,9
    gana rapida."""
    assert matriz_costos(comp, 16.7, VEHICULO, PRECIO)[1][0, 44] == "sin_peaje"
    assert matriz_costos(comp, 16.9, VEHICULO, PRECIO)[1][0, 44] == "rapida"


# --- 2. w = 0 (el barrido completo de pares está en la prueba parametrizada de la sección 3) ---------------------


def test_con_w_cero_en_pares_cuya_sin_peaje_tambien_paga_peaje(comp, filas):
    """Pares de §7.2 Bloque 2 (v1.8). Dos a mano (0,0842628 €/km de combustible):

    (3, 32) Almería–Palencia:          rapida 19,75 + 800,3119 · 0,0842628 = 87,186522;
                                       sin_peaje 1,00 + 786,9778 · 0,0842628 = 67,312953
    (11, 29) Ciudad Real–Pamplona:     rapida  9,49 + 584,4743 · 0,0842628 = 58,739441;
                                       sin_peaje 5,73 + 584,3346 · 0,0842628 = 54,967670
    En ambos se elige `sin_peaje` aunque paga peaje: el criterio es el mínimo de `peaje + combustible`.
    """
    c, alt = matriz_costos(comp, 0, VEHICULO, PRECIO)
    assert comp.peaje_eur_sin_peaje[3, 32] == 1.00 and comp.peaje_eur_sin_peaje[11, 29] == 5.73
    assert alt[3, 32] == "sin_peaje" and c[3, 32] == pytest.approx(67.312953, abs=TOL_MANO)
    assert alt[11, 29] == "sin_peaje" and c[11, 29] == pytest.approx(54.967670, abs=TOL_MANO)
    con_peaje = [par for par, a in _por_par(filas).items() if float(a["sin_peaje"]["peaje_eur"]) > 0]
    assert con_peaje, "no hay pares cuya sin_peaje pague peaje: el criterio v1.11 no se ejercitaría"


# --- 3. Diagonal 0 y simetría (criterio v1.11) -------------------------------------------------------------------


def test_cada_celda_de_los_componentes_sale_de_la_fila_correcta_de_rutas_csv(comp, filas):
    """Detecta un espejo mal hecho (celda (j, i) vacía o con otro par), columnas cruzadas o alternativas
    intercambiadas: los 2 162 × 3 valores se comparan con su fila, en (i, j) y en (j, i)."""
    vistos = 0
    for f in filas:
        i, j = int(f["i"]), int(f["j"])
        assert i < j
        for columna in COLUMNAS:
            m = _campo(comp, columna, f["alternativa"])
            assert m[i, j] == float(f[columna]), (i, j, f["alternativa"], columna)
            assert m[j, i] == float(f[columna]), (j, i, f["alternativa"], columna)
            vistos += 1
    assert vistos == N * (N - 1) // 2 * len(ALTERNATIVAS) * len(COLUMNAS)


def test_diagonal_cero_en_componentes_y_en_c(comp):
    for campo in dataclasses.fields(comp):
        assert np.diag(getattr(comp, campo.name)).tolist() == [0.0] * N, campo.name
    for w in (0, 25, 60):
        c, _ = matriz_costos(comp, w, VEHICULO, PRECIO)
        assert np.diag(c).tolist() == [0.0] * N
        assert (c[~np.eye(N, dtype=bool)] > 0).all()  # solo la diagonal vale 0


def test_alternativa_en_la_diagonal_es_rapida(comp):
    """Hueco del Spec (pendiente de confirmar): en la diagonal ambas alternativas cuestan 0 y se aplica la regla de
    desempate general, así que vale 'rapida'. No hay un tercer valor: el contrato fija {"rapida", "sin_peaje"}."""
    for w in (0, 25):
        _, alt = matriz_costos(comp, w, VEHICULO, PRECIO)
        assert np.diag(alt).tolist() == ["rapida"] * N


@pytest.mark.parametrize("w", [0, 10, 25, 60])
def test_c_y_la_alternativa_en_ij_y_ji_salen_de_la_fila_correcta(comp, filas, w):
    """Simetría según v1.11: no se compara c con su traspuesta sin más; cada celda (i, j) y (j, i) debe valer el
    mínimo de los costos de las dos filas de ese par en rutas.csv, calculados aquí con aritmética escalar.
    Con w = 0 es el criterio de aceptación "menor peaje + combustible" en todos los pares."""
    c, alt = matriz_costos(comp, w, VEHICULO, PRECIO)
    pares = _por_par(filas)
    assert len(pares) == N * (N - 1) // 2
    elegidas = set()
    for (i, j), a in pares.items():
        costos = {nombre: _costo_fila(a[nombre], w) for nombre in ALTERNATIVAS}
        esperada = "sin_peaje" if costos["sin_peaje"] < costos["rapida"] else "rapida"
        elegidas.add(esperada)
        for fila, col in ((i, j), (j, i)):
            assert c[fila, col] == pytest.approx(costos[esperada], rel=RTOL), (fila, col)
            assert alt[fila, col] == esperada, (fila, col)
    if w == 0:
        assert elegidas == set(ALTERNATIVAS)  # con w = 0 la prueba ejercita las dos ramas
    assert np.array_equal(c, c.T) and np.array_equal(alt, alt.T)


# --- 4. Casos sintéticos -----------------------------------------------------------------------------------------

R, S = "rapida", "sin_peaje"


@pytest.mark.parametrize("w, c_esperada, alt_esperada", [
    pytest.param(10, [[0, 25, 46], [25, 0, 60], [46, 60, 0]], [[R, R, S], [R, R, R], [S, R, R]], id="w10"),
    pytest.param(0, [[0, 12, 21], [12, 0, 30], [21, 30, 0]], [[R, S, S], [S, R, R], [S, R, R]], id="w0_con_empate"),
])
def test_sintetico_formula_y_minimo(w, c_esperada, alt_esperada):
    """3 ciudades, consumo 5 l/100 km y 2 €/l → 0,10 €/km. Pares en orden (0,1), (0,2), (1,2).

    w = 10: (0,1) rapida 10·1 + 5 + 100·0,1 = 25;  sin_peaje 10·2   + 0 + 120·0,1 = 32 → rapida,    25
            (0,2) rapida 10·2 + 20 + 200·0,1 = 60; sin_peaje 10·2,5 + 0 + 210·0,1 = 46 → sin_peaje, 46
            (1,2) rapida 10·3 + 0 + 300·0,1 = 60;  sin_peaje 10·4   + 1 + 290·0,1 = 70 → rapida,    60
    w = 0:  (0,1) 15 vs 12 → sin_peaje; (0,2) 40 vs 21 → sin_peaje; (1,2) 30 vs 30 → empate → rapida.
    """
    comp = _sintetico(t_r=[1, 2, 3], d_r=[100, 200, 300], p_r=[5, 20, 0],
                      t_s=[2, 2.5, 4], d_s=[120, 210, 290], p_s=[0, 0, 1])
    c, alt = matriz_costos(comp, w, {"consumo_wltp_comb_l100": 5}, 2)
    assert np.allclose(c, c_esperada, rtol=RTOL, atol=0)
    assert alt.tolist() == alt_esperada


def test_sintetico_con_w_cero_el_criterio_es_la_suma_y_no_solo_el_peaje():
    """w = 0, consumo 50 y precio 2 → 1 €/km (exacto). La alternativa de menor peaje NO es la de menor suma:

    (0,1): rapida 10 + 100 = 110;  sin_peaje 0 + 150 = 150   → rapida    (la de MAYOR peaje; recorre 50 km menos)
    (0,2): rapida  2 + 200 = 202;  sin_peaje 5 + 150 = 155   → sin_peaje (la de MAYOR peaje; recorre 50 km menos)
    (1,2): rapida 20 + 100 = 120;  sin_peaje 0 + 110 = 110   → sin_peaje (control: aquí ambos criterios coinciden)

    Elegir solo por peaje daría sin_peaje, rapida, sin_peaje. En los datos reales los dos criterios coinciden en
    todos los pares, así que solo este caso los distingue.
    """
    comp = _sintetico(t_r=[1, 2, 1], d_r=[100, 200, 100], p_r=[10, 2, 20],
                      t_s=[3, 1.5, 2], d_s=[150, 150, 110], p_s=[0, 5, 0])
    assert comp.peaje_eur_sin_peaje[0, 1] < comp.peaje_eur_rapida[0, 1]
    assert comp.peaje_eur_rapida[0, 2] < comp.peaje_eur_sin_peaje[0, 2]
    c, alt = matriz_costos(comp, 0, {"consumo_wltp_comb_l100": 50}, 2)
    assert c[0, 1] == c[1, 0] == 110.0 and alt[0, 1] == alt[1, 0] == "rapida"
    assert c[0, 2] == c[2, 0] == 155.0 and alt[0, 2] == alt[2, 0] == "sin_peaje"
    assert c[1, 2] == c[2, 1] == 110.0 and alt[1, 2] == alt[2, 1] == "sin_peaje"


def test_sintetico_desempate_exacto_elige_rapida():
    """Costos iguales con componentes distintos (valores exactos en binario): w = 8, consumo 50, precio 2 → 1 €/km.

    (0,1): rapida 8·1 + 4 + 16 = 28;  sin_peaje 8·2 + 0 + 12 = 28   → empate → rapida
    (0,2): rapida 8·1 + 4 + 16 = 28;  sin_peaje 8·2 + 0 + 11 = 27   → sin_peaje (el desempate no arrastra)
    (1,2): alternativas idénticas (par sin peaje que reutiliza la rápida) → rapida
    """
    comp = _sintetico(t_r=[1, 1, 3], d_r=[16, 16, 5], p_r=[4, 4, 0],
                      t_s=[2, 2, 3], d_s=[12, 11, 5], p_s=[0, 0, 0])
    c, alt = matriz_costos(comp, 8, {"consumo_wltp_comb_l100": 50}, 2)
    assert c[0, 1] == 28.0 and alt[0, 1] == alt[1, 0] == "rapida"
    assert c[0, 2] == 27.0 and alt[0, 2] == alt[2, 0] == "sin_peaje"
    assert c[1, 2] == 29.0 and alt[1, 2] == alt[2, 1] == "rapida"


def test_pares_reales_con_alternativas_identicas_eligen_rapida(comp, filas):
    """En los pares sin peaje, `sin_peaje` reutiliza la rápida (§7.2): empate en todo w → rapida."""
    identicos = [(i, j) for (i, j), a in _por_par(filas).items()
                 if all(a["rapida"][col] == a["sin_peaje"][col] for col in COLUMNAS)]
    assert identicos
    for w in (0, 25):
        _, alt = matriz_costos(comp, w, VEHICULO, PRECIO)
        assert all(alt[i, j] == "rapida" and alt[j, i] == "rapida" for i, j in identicos)


# --- 5. Sensibilidad a los parámetros ----------------------------------------------------------------------------


def _una_sola_alternativa(comp: Componentes, alternativa: str) -> Componentes:
    """Componentes con las dos alternativas iguales a `alternativa`: el mínimo es trivial y C es lineal en todo."""
    t, d, p = (_campo(comp, col, alternativa) for col in COLUMNAS)
    return Componentes(tiempo_h_rapida=t, dist_km_rapida=d, peaje_eur_rapida=p,
                       tiempo_h_sin_peaje=t, dist_km_sin_peaje=d, peaje_eur_sin_peaje=p)


@pytest.mark.parametrize("alternativa", ALTERNATIVAS)
def test_cada_parametro_mueve_c_como_predice_la_formula(comp, alternativa):
    """Con una sola alternativa: ∂c/∂w = t, ∂c/∂precio = d·consumo/100, ∂c/∂consumo = d·precio/100, c(0, ·, 0) = P."""
    una = _una_sola_alternativa(comp, alternativa)
    t, d, p = (_campo(comp, col, alternativa) for col in COLUMNAS)
    base, _ = matriz_costos(una, 25, VEHICULO, PRECIO)
    assert np.allclose(base, 25 * t + p + d * (CONSUMO / 100) * PRECIO, rtol=RTOL, atol=0)

    mas_w, _ = matriz_costos(una, 40, VEHICULO, PRECIO)
    assert np.allclose(mas_w - base, 15 * t, rtol=1e-9, atol=1e-9)

    mas_precio, _ = matriz_costos(una, 25, VEHICULO, PRECIO + 0.5)
    assert np.allclose(mas_precio - base, d * (CONSUMO / 100) * 0.5, rtol=1e-9, atol=1e-9)

    mas_consumo, _ = matriz_costos(una, 25, {"consumo_wltp_comb_l100": 6.2}, PRECIO)
    assert np.allclose(mas_consumo - base, d * (6.2 - CONSUMO) / 100 * PRECIO, rtol=1e-9, atol=1e-9)

    solo_peaje, _ = matriz_costos(una, 0, VEHICULO, 0)
    assert np.array_equal(solo_peaje, p)
    solo_peaje, _ = matriz_costos(una, 0, {"consumo_wltp_comb_l100": 0}, PRECIO)
    assert np.array_equal(solo_peaje, p)


def test_el_consumo_se_lee_de_consumo_wltp_comb_l100_y_no_de_otra_clave(comp):
    base, _ = matriz_costos(comp, 25, VEHICULO, PRECIO)
    con_extras, _ = matriz_costos(comp, 25, {"consumo_wltp_comb_l100": CONSUMO, "consumo": 99, "anio": 2026}, PRECIO)
    assert np.array_equal(base, con_extras)
    with pytest.raises(KeyError, match="consumo_wltp_comb_l100"):
        matriz_costos(comp, 25, {"consumo": CONSUMO}, PRECIO)


def test_c_es_el_minimo_de_las_dos_alternativas_y_no_decrece_con_w(comp):
    costos_alt = {a: matriz_costos(_una_sola_alternativa(comp, a), 25, VEHICULO, PRECIO)[0] for a in ALTERNATIVAS}
    c, alt = matriz_costos(comp, 25, VEHICULO, PRECIO)
    assert np.array_equal(c, np.minimum(costos_alt["rapida"], costos_alt["sin_peaje"]))
    assert np.array_equal(alt == "sin_peaje", costos_alt["sin_peaje"] < costos_alt["rapida"])
    anterior = matriz_costos(comp, 0, VEHICULO, PRECIO)[0]
    for w in (5, 10, 25, 60):
        actual = matriz_costos(comp, w, VEHICULO, PRECIO)[0]
        assert (actual >= anterior).all()
        anterior = actual


def test_subir_w_mueve_pares_de_sin_peaje_a_rapida_y_nunca_al_reves(comp):
    """La rápida nunca es más lenta que la sin peaje en estos datos, así que al subir w solo se gana tiempo."""
    assert (comp.tiempo_h_rapida <= comp.tiempo_h_sin_peaje).all()
    previa = matriz_costos(comp, 0, VEHICULO, PRECIO)[1] == "rapida"
    cambios = 0
    for w in (10, 25, 60):
        actual = matriz_costos(comp, w, VEHICULO, PRECIO)[1] == "rapida"
        assert (actual | ~previa).all()  # quien ya era rapida lo sigue siendo
        cambios += int((actual & ~previa).sum())
        previa = actual
    assert cambios > 0


@pytest.mark.parametrize("cambio, fragmento", [
    pytest.param({"valor_hora": -1}, "valor_hora", id="valor_hora_negativo"),
    pytest.param({"valor_hora": float("nan")}, "valor_hora", id="valor_hora_nan"),
    pytest.param({"valor_hora": float("inf")}, "valor_hora", id="valor_hora_inf"),
    pytest.param({"vehiculo": {"consumo_wltp_comb_l100": -4.6}}, "consumo_wltp_comb_l100", id="consumo_negativo"),
    pytest.param({"precio_l": float("nan")}, "precio_l", id="precio_nan"),
])
def test_parametros_negativos_o_no_finitos_se_rechazan(comp, cambio, fragmento):
    args = {"valor_hora": 25, "vehiculo": VEHICULO, "precio_l": PRECIO, **cambio}
    with pytest.raises(ValueError, match=fragmento):
        matriz_costos(comp, **args)


# --- 6. cargar_componentes ante datos rotos (copias en tmp_path; los datos reales no se tocan) -------------------


def _escribir(tmp_path: Path, filas: list[dict[str, str]]) -> Path:
    with (tmp_path / "rutas.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    return tmp_path


def test_cargar_una_copia_intacta_da_lo_mismo_y_acepta_str_y_path(tmp_path, comp):
    shutil.copy(PROC / "rutas.csv", tmp_path / "rutas.csv")
    for ruta in (tmp_path, str(tmp_path)):
        copia = cargar_componentes(ruta)
        for campo in dataclasses.fields(comp):
            assert np.array_equal(getattr(copia, campo.name), getattr(comp, campo.name))


def _cambiar(indice: int, **campos: str):
    """Mutación: la fila `indice` con `campos` sustituidos."""
    def aplicar(fs):
        fs[indice] = {**fs[indice], **campos}
    return aplicar


def _quitar(i: int, j: int, alternativa: str | None = None):
    """Mutación: quita las filas del par (i, j); solo la de `alternativa` si se indica."""
    def aplicar(fs):
        fs[:] = [f for f in fs if (int(f["i"]), int(f["j"])) != (i, j)
                 or (alternativa is not None and f["alternativa"] != alternativa)]
    return aplicar


def _duplicar(indice: int):
    def aplicar(fs):
        fs.append(dict(fs[indice]))
    return aplicar


def _quitar_columna(columna: str):
    def aplicar(fs):
        for f in fs:
            del f[columna]
    return aplicar


@pytest.mark.parametrize("cambio, fragmento", [
    pytest.param(_quitar(0, 7), "faltan 2 filas", id="falta_un_par"),
    pytest.param(_cambiar(4, tiempo_h="nan"), "tiempo_h no es finito", id="nan"),
    pytest.param(_cambiar(4, peaje_eur=""), "peaje_eur vacío", id="vacio"),
    pytest.param(_cambiar(4, alternativa="panoramica"), "alternativa desconocida", id="alternativa_desconocida"),
    pytest.param(_duplicar(0), "repetida", id="fila_repetida"),
    pytest.param(_cambiar(4, i="40", j="3"), "i < j", id="fuera_de_orden"),
    pytest.param(_cambiar(4, j="47"), "i < j", id="fuera_de_rango"),
    pytest.param(_cambiar(4, i="tres"), "no son enteros", id="i_no_entero"),
    pytest.param(_quitar_columna("peaje_eur"), "faltan las columnas", id="columna_ausente"),
])
def test_cargar_componentes_falla_con_un_error_claro(tmp_path, filas, cambio, fragmento):
    rotas = [dict(f) for f in filas]
    cambio(rotas)
    with pytest.raises(ValueError, match=fragmento):
        cargar_componentes(_escribir(tmp_path, rotas))


def test_el_error_por_pares_faltantes_dice_cuales(tmp_path, filas):
    rotas = [dict(f) for f in filas]
    _quitar(3, 7, "sin_peaje")(rotas)
    assert len(rotas) == len(filas) - 1
    with pytest.raises(ValueError, match=r"faltan 1 filas .*\(3, 7, 'sin_peaje'\)"):
        cargar_componentes(_escribir(tmp_path, rotas))


def test_cargar_componentes_sin_rutas_csv_falla(tmp_path):
    with pytest.raises(FileNotFoundError, match="rutas.csv"):
        cargar_componentes(tmp_path)
