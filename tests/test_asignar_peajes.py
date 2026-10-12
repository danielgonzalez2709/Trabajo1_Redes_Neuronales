"""Pruebas de T2.5 (Spec §7.2 Bloque 3, cálculo por ruta): scripts/asignar_peajes.py. Sin red.

Primera parte: casos límite con datos sintéticos (una vía recta "XX-1" a 40° N con tres tramos de 10, 20 y 10 km:
1,00 EUR, 3,00 EUR y 0,00 EUR). Segunda parte: los 5 pares de validación y la coherencia de los archivos reales
(data/processed/rutas.csv, rutas_peajes_detalle.csv y peajes_avisos.csv).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

import asignar_peajes as ap

RAIZ = Path(__file__).resolve().parents[1]
PROCESADOS = RAIZ / "data" / "processed"
LAT = 40.0
LON0 = -4.0
KM_POR_GRADO_LON = 111.32 * math.cos(math.radians(LAT))


def lon(km: float) -> float:
    """Longitud del punto situado a `km` al este de LON0 (misma latitud)."""
    return LON0 + km / KM_POR_GRADO_LON


# ------------------------------------------------------------------------------------------------ datos sintéticos

COLS_TRAMOS = ["id", "via", "desde", "hasta", "operador", "ambito", "provincia", "km", "tarifa_ligeros_eur", "eur_km",
               "vigente_desde", "vigente_hasta", "fuente_url", "fecha_consulta", "nota"]


def _tramo(id_, via, km, tarifa, desde="2026-01-01", hasta=""):
    return {"id": id_, "via": via, "desde": "a", "hasta": "b", "operador": "x", "ambito": "estatal", "provincia": "p",
            "km": km, "tarifa_ligeros_eur": tarifa, "eur_km": "0", "vigente_desde": desde, "vigente_hasta": hasta,
            "fuente_url": "https://x", "fecha_consulta": "2026-10-12", "nota": ""}


TRAMOS = [_tramo("T1", "XX-1", "10", "1.00"), _tramo("T2", "XX-1", "20", "3.00"), _tramo("T3", "XX-1", "10", "0.00")]
CADENAS = [("T1", "C", 1, "XX-1"), ("T2", "C", 2, "XX-1"), ("T3", "C", 3, "XX-1")]
ANCLAS = [("C", 0, lon(0)), ("C", 10, lon(10)), ("C", 30, lon(30)), ("C", 40, lon(40))]


def _escribir(ruta: Path, cols: list[str], filas: list) -> Path:
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for fila in filas:
            w.writerow([fila[c] for c in cols] if isinstance(fila, dict) else fila)
    return ruta


def _entradas(tmp: Path, tramos=None, cadenas=None, anclas=None) -> dict[str, Path]:
    tramos = TRAMOS if tramos is None else tramos
    cadenas = CADENAS if cadenas is None else cadenas
    anclas = ANCLAS if anclas is None else anclas
    return {
        "tramos": _escribir(tmp / "peajes_tramos.csv", COLS_TRAMOS, tramos),
        "cadenas": _escribir(tmp / "peajes_cadenas.csv", ["id_tramo", "cadena", "orden", "refs_osrm"], cadenas),
        "anclas": _escribir(tmp / "peajes_anclas.csv",
                            ["cadena", "km_cadena", "lon", "lat", "etiqueta", "tipo_coord", "origen_km",
                             "fuente_coord"],
                            [[c, km, f"{lo:.7f}", (a[0] if a else LAT), f"p{km}", "nodo_osm", "x", "x"]
                             for c, km, lo, *a in anclas]),  # un 4.º valor opcional fija la latitud del ancla
    }


@pytest.fixture()
def cadenas(tmp_path):
    e = _entradas(tmp_path)
    return ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")


def paso(i, k, ref, km0, km1, dist=None, n=4, n_toll=None, lat=LAT):
    """Paso de OSRM de `km0` a `km1` sobre XX-1 (todas las intersecciones toll por defecto)."""
    return {"i": i, "j": 9, "alternativa": "rapida", "paso": k, "ref": ref, "nombre": "", "dist_m": 1000 * (dist or abs(km1 - km0)),
            "n_intersecciones": n, "n_intersecciones_toll": n if n_toll is None else n_toll,
            "lon_ini": lon(km0), "lat_ini": lat, "lon_fin": lon(km1), "lat_fin": lat}


def calcular(cadenas, *pasos):
    return ap.peaje_de_ruta(cadenas, list(pasos))


# ------------------------------------------------------------------------------------------------ tramo completo y parcial

def test_paso_que_recorre_un_tramo_entero_cobra_su_tarifa(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 10, 30))
    assert r.peaje_eur == pytest.approx(3.00, abs=1e-6)
    assert r.km_peaje == pytest.approx(20.0, abs=0.1)
    assert r.vias == ["XX-1"]
    assert [d["tramo_id"] for d in r.detalle] == ["T2"]


def test_paso_parcial_cobra_los_km_recorridos_por_el_eur_km_del_tramo(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 12, 22))  # 10 km de 20 en T2 (50 %): 3,00 x 0,5
    assert r.peaje_eur == pytest.approx(1.50, abs=0.02)
    assert r.km_peaje == pytest.approx(10.0, abs=0.1)
    assert r.detalle[0]["fraccion"] == pytest.approx(0.5, abs=0.01)


def test_dos_tramos_encadenados_suman_y_la_via_no_se_repite(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 0, 10), paso(0, 2, "XX-1", 10, 30))
    assert r.peaje_eur == pytest.approx(4.00, abs=1e-6)
    assert r.km_peaje == pytest.approx(30.0, abs=0.1)
    assert r.vias == ["XX-1"]
    assert [d["tramo_id"] for d in r.detalle] == ["T1", "T2"]


def test_un_paso_largo_que_cruza_varios_tramos_se_reparte_entre_ellos(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 5, 35))  # 5 km de T1, T2 entero y 5 km de T3
    por_tramo = {d["tramo_id"]: d["importe_eur"] for d in r.detalle}
    assert por_tramo["T1"] == pytest.approx(0.50, abs=0.02)
    assert por_tramo["T2"] == pytest.approx(3.00, abs=1e-6)
    assert por_tramo["T3"] == 0.0
    assert r.peaje_eur == pytest.approx(3.50, abs=0.02)


def test_el_hueco_entre_dos_pasos_de_la_misma_via_se_cobra_como_recorrido_continuo(cadenas):
    """OSM puede dejar sin la clase toll un trozo de autopista (AP-7 de Málaga): se cobra de extremo a extremo."""
    r = calcular(cadenas, paso(0, 1, "XX-1", 0, 8), paso(0, 3, "XX-1", 12, 30))
    assert r.peaje_eur == pytest.approx(4.00, abs=1e-6)


def test_sentido_inverso_da_lo_mismo(cadenas):
    a = calcular(cadenas, paso(0, 1, "XX-1", 3, 28))
    b = calcular(cadenas, paso(0, 1, "XX-1", 28, 3))
    assert a.peaje_eur == pytest.approx(b.peaje_eur)
    assert a.km_peaje == pytest.approx(b.km_peaje)


def test_fraccion_de_95_por_ciento_o_mas_cobra_la_tarifa_completa(tmp_path):
    e = _entradas(tmp_path, tramos=[_tramo("L", "XX-1", "100", "10.00")], cadenas=[("L", "C", 1, "XX-1")],
                  anclas=[("C", 0, lon(0)), ("C", 100, lon(100))])
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    assert calcular(cad, paso(0, 1, "XX-1", 4, 100)).peaje_eur == pytest.approx(10.00, abs=1e-6)  # 96 %: completo
    assert calcular(cad, paso(0, 1, "XX-1", 10, 100)).peaje_eur == pytest.approx(9.00, abs=0.02)  # 90 %: proporcional


# ------------------------------------------------------------------------------------------------ sin peaje y gratuitos

def test_ruta_sin_pasos_no_paga_nada(cadenas):
    r = calcular(cadenas)
    assert (r.peaje_eur, r.km_peaje, r.vias, r.detalle, r.avisos) == (0.0, 0.0, [], [], [])


def test_tramo_gratuito_no_cuenta_km_de_peaje_ni_via(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 30, 40))
    assert r.peaje_eur == 0.0 and r.km_peaje == 0.0 and r.vias == []
    assert [d["tramo_id"] for d in r.detalle] == ["T3"]  # queda en el detalle con importe 0


def test_pasos_sin_ref_son_enlaces_y_no_se_cobran(cadenas):
    r = calcular(cadenas, paso(0, 1, None, 10, 30), paso(0, 2, "", 10, 30))
    assert r.peaje_eur == 0.0 and r.detalle == []
    assert r.avisos == []  # los enlaces sin ref no generan aviso por paso (se cuentan aparte)


def test_ref_sin_cadena_no_se_cobra_y_se_avisa(cadenas):
    r = calcular(cadenas, paso(0, 1, "ZZ-9", 10, 30))
    assert r.peaje_eur == 0.0
    assert [a["motivo"] for a in r.avisos] == ["ref_sin_cadena"]
    assert r.avisos[0]["ref"] == "ZZ-9"


def test_paso_lejos_de_la_cadena_no_se_cobra_y_se_avisa(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 10, 30, lat=LAT + 1.0))  # 110 km al norte
    assert r.peaje_eur == 0.0
    assert [a["motivo"] for a in r.avisos] == ["lejos_de_la_cadena"]


# ------------------------------------------------------------------------------------------------ extremos y ajustes

def test_extremos_fuera_de_la_cadena_se_recortan_a_sus_extremos(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", -8, 12))  # empieza 8 km antes del inicio: no hay tramo ahí
    por_tramo = {d["tramo_id"]: d["importe_eur"] for d in r.detalle}
    assert por_tramo["T1"] == pytest.approx(1.00, abs=1e-6)
    assert por_tramo["T2"] == pytest.approx(0.30, abs=0.02)  # 2 km de 20


def test_extremo_a_menos_de_1_5_km_de_un_ancla_se_ajusta_a_ella(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 11.2, 28.9))  # 1,2 km y 1,1 km de los anclas 10 y 30
    assert r.peaje_eur == pytest.approx(3.00, abs=1e-6)  # ya sería 17,7/20 = 88 %; el ajuste lo hace completo


def test_extremo_a_mas_de_1_5_km_de_un_ancla_se_proyecta(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 13.0, 30))  # 17 km de 20 = 85 %
    assert r.peaje_eur == pytest.approx(2.55, abs=0.02)


def test_un_ancla_con_el_mismo_km_actua_como_extremo_equivalente(tmp_path):
    """Entradas alternativas al inicio de la cadena (p. ej. Basauri en la AP-68) se tratan como el inicio."""
    anclas = [("C", 0, lon(0)), ("C", 0, lon(-3.0)), ("C", 10, lon(10)), ("C", 30, lon(30)), ("C", 40, lon(40))]
    e = _entradas(tmp_path, anclas=anclas)
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    r = calcular(cad, paso(0, 1, "XX-1", -3.0, 10))
    assert r.peaje_eur == pytest.approx(1.00, abs=1e-6)


def test_dos_cadenas_con_la_misma_ref_se_distinguen_por_la_geografia(tmp_path):
    lejos = 200.0  # km al este: otra "AP-15"
    tramos = [*TRAMOS, _tramo("U1", "XX-1", "10", "5.00")]
    cadenas = [*CADENAS, ("U1", "D", 1, "XX-1")]
    anclas = [*ANCLAS, ("D", 0, lon(lejos)), ("D", 10, lon(lejos + 10))]
    e = _entradas(tmp_path, tramos=tramos, cadenas=cadenas, anclas=anclas)
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    r = calcular(cad, paso(0, 1, "XX-1", lejos, lejos + 10))
    assert [d["tramo_id"] for d in r.detalle] == ["U1"]
    assert r.peaje_eur == pytest.approx(5.00, abs=1e-6)
    r = calcular(cad, paso(0, 1, "XX-1", 0, 10))
    assert [d["tramo_id"] for d in r.detalle] == ["T1"]


def test_paso_incoherente_con_su_longitud_genera_aviso_pero_se_cobra(cadenas):
    r = calcular(cadenas, paso(0, 1, "XX-1", 10, 30, dist=40.0))  # OSRM dice 40 km y la cadena solo 20
    assert r.peaje_eur == pytest.approx(3.00, abs=1e-6)
    assert [a["motivo"] for a in r.avisos] == ["km_incoherente"]


# ------------------------------------------------------------------------------------------------ lectura y vigencia

def test_tramo_con_vigencia_posterior_al_corte_se_ignora(tmp_path):
    tramos = [*TRAMOS, _tramo("PX", "XX-1", "5", "TODO(dato-faltante)", desde="2026-11-11")]
    e = _entradas(tmp_path, tramos=tramos)  # PX no está en peajes_cadenas.csv: tiene que bastar con la vigencia
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    assert [t.id for t in cad["C"].tramos] == ["T1", "T2", "T3"]


def test_tramo_vencido_antes_del_corte_se_ignora(tmp_path):
    tramos = [_tramo("T1", "XX-1", "10", "1.00", hasta="2026-09-30"), *TRAMOS[1:]]
    e = _entradas(tmp_path, tramos=tramos)  # T1 sigue en la cadena: sus 10 km mantienen la posición de los anclas
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    assert [t.id for t in cad["C"].tramos] == ["T2", "T3"]


def test_tramo_vigente_con_tarifa_todo_es_un_error(tmp_path):
    tramos = [_tramo("T1", "XX-1", "10", "TODO(dato-faltante)"), *TRAMOS[1:]]
    e = _entradas(tmp_path, tramos=tramos)
    with pytest.raises(ap.DatoFaltanteError, match="T1"):
        ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")


def test_tramo_vigente_sin_cadena_es_un_error(tmp_path):
    e = _entradas(tmp_path, cadenas=CADENAS[:2])
    with pytest.raises(ap.DatoFaltanteError, match="T3"):
        ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")


def test_la_cadena_sin_dos_anclas_no_se_puede_proyectar_y_avisa(tmp_path):
    e = _entradas(tmp_path, anclas=[("C", 0, lon(0))])
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    r = calcular(cad, paso(0, 1, "XX-1", 10, 30))
    assert r.peaje_eur == 0.0
    assert [a["motivo"] for a in r.avisos] == ["cadena_sin_anclas"]


def test_la_posicion_de_un_ancla_fuera_de_la_cadena_es_un_error(tmp_path):
    e = _entradas(tmp_path, anclas=[*ANCLAS, ("C", 99, lon(99))])  # la cadena mide 40 km
    with pytest.raises(ap.DatoFaltanteError, match="99"):
        ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")


def test_vigencia_incluye_los_dos_limites_el_dia_del_corte(tmp_path):
    """vigente_desde == corte y vigente_hasta == corte son ambos vigentes (límites cerrados)."""
    assert ap._vigente({"vigente_desde": "2026-10-01", "vigente_hasta": "2026-10-01"}, "2026-10-01")
    assert ap._vigente({"vigente_desde": "2026-10-01", "vigente_hasta": ""}, "2026-10-01")
    assert ap._vigente({"vigente_desde": "2026-01-01", "vigente_hasta": "2026-10-01"}, "2026-10-01")
    assert not ap._vigente({"vigente_desde": "2026-10-02", "vigente_hasta": ""}, "2026-10-01")
    assert not ap._vigente({"vigente_desde": "2026-01-01", "vigente_hasta": "2026-09-30"}, "2026-10-01")
    tramos = [TRAMOS[0], _tramo("T2", "XX-1", "20", "3.00", desde="2026-10-01", hasta="2026-10-01"), TRAMOS[2]]
    e = _entradas(tmp_path, tramos=tramos)
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    assert [t.id for t in cad["C"].tramos] == ["T1", "T2", "T3"]


def test_el_orden_de_la_cadena_es_numerico_y_no_de_texto(tmp_path):
    """Con 12 tramos, "10" < "2" como texto: el tramo de orden 2 debe quedar en el km 10 aunque el CSV venga al revés."""
    ids = [f"T{k:02d}" for k in range(1, 13)]
    tramos = [_tramo(i, "XX-1", "10", "1.00") for i in ids]
    cadenas = [(i, "C", k, "XX-1") for k, i in reversed(list(enumerate(ids, start=1)))]
    e = _entradas(tmp_path, tramos=tramos, cadenas=cadenas, anclas=[("C", 0, lon(0)), ("C", 120, lon(120))])
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")["C"]
    assert [t.id for t in cad.tramos] == ids
    assert [t.inicio_km for t in cad.tramos] == [10.0 * k for k in range(12)]


def test_un_paso_con_extremo_recortado_no_genera_aviso_de_km_incoherente(cadenas):
    """El km entre extremos solo es comparable con OSRM si ninguno se recortó: aquí OSRM mide 20 y la cadena 12."""
    r = calcular(cadenas, paso(0, 1, "XX-1", -8, 12, dist=20.0))
    assert r.avisos == []
    assert r.peaje_eur == pytest.approx(1.30, abs=0.02)
    r = calcular(cadenas, paso(0, 1, "XX-1", 28, 48, dist=40.0))  # recortado por el final
    assert r.avisos == []


@pytest.mark.parametrize("d_primero", [False, True])
def test_con_dos_cadenas_validas_de_la_misma_ref_gana_la_mas_cercana(tmp_path, d_primero):
    """D corre paralela a C unos 2,2 km al norte: las dos son válidas (< 5 km) y gana la de menor distancia total,
    sea cual sea el orden en que aparecen en peajes_cadenas.csv."""
    tramos = [*TRAMOS, _tramo("U1", "XX-1", "10", "5.00")]
    cadenas_ = [("U1", "D", 1, "XX-1"), *CADENAS] if d_primero else [*CADENAS, ("U1", "D", 1, "XX-1")]
    anclas = [*ANCLAS, ("D", 0, lon(0), LAT + 0.02), ("D", 10, lon(10), LAT + 0.02)]
    e = _entradas(tmp_path, tramos=tramos, cadenas=cadenas_, anclas=anclas)
    cad = ap.leer_cadenas(e["tramos"], e["cadenas"], e["anclas"], "2026-10-01")
    assert list(cad)[0] == ("D" if d_primero else "C")
    r = calcular(cad, paso(0, 1, "XX-1", 0, 10))
    assert [d["tramo_id"] for d in r.detalle] == ["T1"]
    assert r.peaje_eur == pytest.approx(1.00, abs=1e-6)
    r = calcular(cad, paso(0, 1, "XX-1", 0, 10, lat=LAT + 0.02))  # ahora D es la más cercana
    assert [d["tramo_id"] for d in r.detalle] == ["U1"]


# ------------------------------------------------------------------------------------------------ archivos

COLS_RUTAS = ["i", "j", "alternativa", "dist_km", "tiempo_h", "km_peaje", "peaje_eur", "vias_peaje", "fuente",
              "fecha_extracto_osm"]
COLS_PASOS = ["i", "j", "alternativa", "paso", "ref", "nombre", "dist_m", "n_intersecciones", "n_intersecciones_toll",
              "lon_ini", "lat_ini", "lon_fin", "lat_fin"]


def _ruta(i, j, alt):
    return [i, j, alt, "10.0", "0.5", "", "", "", "OSRM, con coma", "2026-10-01T20:22:06Z"]


@pytest.fixture()
def corrida(tmp_path):
    e = _entradas(tmp_path)
    rutas = _escribir(tmp_path / "rutas.csv", COLS_RUTAS, [
        _ruta(0, 9, "rapida"), _ruta(0, 9, "sin_peaje"), _ruta(1, 9, "rapida"), _ruta(1, 9, "sin_peaje")])
    pasos = _escribir(tmp_path / "rutas_pasos_peaje.csv", COLS_PASOS, [
        paso(0, 1, "XX-1", 0, 10), paso(0, 2, "XX-1", 10, 30),            # (0,9) rápida: 4,00
        {**paso(1, 1, "XX-1", 10, 30), "alternativa": "sin_peaje"},        # (1,9) sin_peaje cobra igual: 3,00
        paso(1, 2, "ZZ-9", 0, 5)])                                          # (1,9) rápida: solo un aviso
    salida = tmp_path / "salida"
    args = ["--rutas", str(rutas), "--pasos", str(pasos), "--tramos", str(e["tramos"]), "--cadenas", str(e["cadenas"]),
            "--anclas", str(e["anclas"]), "--salida-dir", str(salida), "--fecha-corte", "2026-10-01"]
    return {"rutas": rutas, "salida": salida, "args": args}


def _leer(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_actualiza_las_tres_columnas_y_deja_el_resto_intacto(corrida):
    antes = _leer(corrida["rutas"])
    assert ap.main(corrida["args"]) == 0
    despues = _leer(corrida["rutas"])
    assert [{k: v for k, v in f.items() if k not in ("km_peaje", "peaje_eur", "vias_peaje")} for f in despues] == \
           [{k: v for k, v in f.items() if k not in ("km_peaje", "peaje_eur", "vias_peaje")} for f in antes]
    por = {(f["i"], f["alternativa"]): f for f in despues}
    assert por[("0", "rapida")]["peaje_eur"] == "4.00" and float(por[("0", "rapida")]["km_peaje"]) == pytest.approx(30, abs=0.1)
    assert por[("0", "rapida")]["vias_peaje"] == "XX-1"
    assert por[("0", "sin_peaje")]["peaje_eur"] == "0.00" and por[("0", "sin_peaje")]["km_peaje"] == "0.0000"
    assert por[("0", "sin_peaje")]["vias_peaje"] == ""
    assert por[("1", "sin_peaje")]["peaje_eur"] == "3.00"  # una ruta sin_peaje con clase toll se cobra igual
    assert por[("1", "rapida")]["peaje_eur"] == "0.00"
    assert tuple(despues[0]) == tuple(COLS_RUTAS)


def test_es_idempotente_byte_a_byte(corrida):
    assert ap.main(corrida["args"]) == 0
    primera = corrida["rutas"].read_bytes()
    detalle = (corrida["salida"] / "rutas_peajes_detalle.csv").read_bytes()
    assert ap.main(corrida["args"]) == 0
    assert corrida["rutas"].read_bytes() == primera
    assert (corrida["salida"] / "rutas_peajes_detalle.csv").read_bytes() == detalle
    assert b"\r" not in primera


def test_detalle_y_avisos_cuadran_con_rutas(corrida):
    ap.main(corrida["args"])
    detalle = _leer(corrida["salida"] / "rutas_peajes_detalle.csv")
    rutas = _leer(corrida["rutas"])
    for f in rutas:
        suma = sum(float(d["importe_eur"]) for d in detalle
                   if (d["i"], d["j"], d["alternativa"]) == (f["i"], f["j"], f["alternativa"]))
        assert float(f["peaje_eur"]) == pytest.approx(suma, abs=0.005)
    avisos = _leer(corrida["salida"] / "peajes_avisos.csv")
    assert [(a["i"], a["motivo"], a["ref"]) for a in avisos] == [("1", "ref_sin_cadena", "ZZ-9")]


def test_resumen_json_cuenta_pasos_sin_asignar(corrida):
    ap.main(corrida["args"])
    r = json.loads((corrida["salida"] / "peajes_resumen.json").read_text(encoding="utf-8"))
    assert r["n_filas"] == 4 and r["n_filas_con_peaje"] == 2
    assert r["pasos_no_asignados"]["ref_sin_cadena"]["n"] == 1
    assert r["fecha_corte"] == "2026-10-01"


def test_un_paso_de_una_ruta_que_no_esta_en_rutas_csv_es_un_error(corrida, capsys):
    """Un paso de una ruta que no está en rutas.csv es una inconsistencia entre T2.3 y T2.5."""
    with (corrida["rutas"].parent / "rutas_pasos_peaje.csv").open("a", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerow([7, 7, "rapida", 1, "XX-1", "", 1000, 2, 2, lon(0), LAT, lon(10), LAT])
    assert ap.main(corrida["args"]) == 2
    assert "7" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------ datos reales

@pytest.fixture(scope="module")
def reales() -> dict[tuple[int, int, str], dict]:
    return {(int(f["i"]), int(f["j"]), f["alternativa"]): f for f in _leer(PROCESADOS / "rutas.csv")}


def test_rutas_csv_real_tiene_las_tres_columnas_completas(reales):
    assert len(reales) == 2162
    for f in reales.values():
        assert f["km_peaje"] != "" and f["peaje_eur"] != ""
        assert float(f["peaje_eur"]) >= 0 and float(f["km_peaje"]) >= 0
        assert (float(f["peaje_eur"]) > 0) == (f["vias_peaje"] != "")
        assert float(f["km_peaje"]) <= float(f["dist_km"]) + 5.0  # los km de peaje no pueden superar el recorrido


def test_rutas_csv_real_coincide_con_lo_que_calcula_el_script(reales, tmp_path):
    """El CSV versionado es reproducible: volver a ejecutar sobre una copia da los mismos bytes."""
    copia = tmp_path / "rutas.csv"
    copia.write_bytes((PROCESADOS / "rutas.csv").read_bytes())
    assert ap.main(["--rutas", str(copia), "--salida-dir", str(tmp_path / "s")]) == 0
    assert copia.read_bytes() == (PROCESADOS / "rutas.csv").read_bytes()
    for nombre in ("rutas_peajes_detalle.csv", "peajes_avisos.csv", "peajes_resumen.json"):
        assert (tmp_path / "s" / nombre).read_bytes() == (PROCESADOS / nombre).read_bytes()


def test_los_avisos_reales_son_solo_los_38_pasos_con_ref_sin_cadena():
    """Cierra el mutante de H-20: anclas intermedias con el km corrido generan `km_incoherente` sin que nada falle."""
    resumen = json.loads((PROCESADOS / "peajes_resumen.json").read_text(encoding="utf-8"))
    assert resumen["avisos_por_motivo"] == {"ref_sin_cadena": 38}


def test_pares_sin_peaje_del_resumen_cuestan_cero(reales):
    marcados = json.loads((PROCESADOS / "rutas_resumen.json").read_text(encoding="utf-8"))["pares_sin_peaje"]["pares"]
    assert len(marcados) == 547
    for i, j in marcados:
        for alt in ("rapida", "sin_peaje"):
            f = reales[(i, j, alt)]
            assert f["peaje_eur"] == "0.00" and f["km_peaje"] == "0.0000" and f["vias_peaje"] == ""


def test_validacion_bilbao_zaragoza_es_la_suma_de_los_7_tramos_de_la_ap68(reales):
    """Suma de tramos = 41,50 EUR (publicado para el recorrido completo: 39,90; peaje cerrado, Spec v1.9)."""
    f = reales[(44, 46, "rapida")]
    assert float(f["peaje_eur"]) == pytest.approx(41.50, abs=0.005)
    assert f["vias_peaje"] == "AP-68"
    assert float(f["km_peaje"]) == pytest.approx(291.697, abs=0.01)
    assert reales[(44, 46, "sin_peaje")]["peaje_eur"] == "0.00"  # la alternativa gratuita no pasa por ninguna toll


def test_validacion_sevilla_cadiz_es_gratis_en_las_dos_alternativas(reales):
    for alt in ("rapida", "sin_peaje"):
        f = reales[(9, 37, alt)]
        assert (f["peaje_eur"], f["km_peaje"], f["vias_peaje"]) == ("0.00", "0.0000", "")


def test_validacion_madrid_toledo_va_por_la_a42_y_cuesta_cero(reales):
    for alt in ("rapida", "sin_peaje"):
        f = reales[(26, 41, alt)]
        assert (f["peaje_eur"], f["km_peaje"], f["vias_peaje"]) == ("0.00", "0.0000", "")


def test_validacion_alicante_murcia_va_por_autovias_y_cuesta_cero(reales):
    for alt in ("rapida", "sin_peaje"):
        f = reales[(2, 28, alt)]
        assert (f["peaje_eur"], f["km_peaje"], f["vias_peaje"]) == ("0.00", "0.0000", "")


def test_validacion_coruna_pontevedra_coincide_con_la_calculadora_de_audasa(reales):
    """16,35 EUR (calculadora oficial de Audasa, T2.4): 0,00 + 8,80 + 0,00 + 7,55. AP9-03 vale 0 EUR."""
    f = reales[(13, 33, "rapida")]
    assert float(f["peaje_eur"]) == pytest.approx(16.35, abs=0.005)
    assert f["vias_peaje"] == "AP-9"
    assert reales[(13, 33, "sin_peaje")]["peaje_eur"] == "0.00"


def test_las_26_rutas_sin_peaje_con_clase_toll_se_cobran_como_cualquier_otra(reales):
    pares = json.loads((PROCESADOS / "rutas_resumen.json").read_text(encoding="utf-8"))["avisos"][
        "sin_peaje_con_clase_toll"]["pares"]
    assert len(pares) == 26
    cobradas = [p for p in pares if float(reales[(p[0], p[1], "sin_peaje")]["peaje_eur"]) > 0]
    assert len(cobradas) >= 1
    for p in pares:  # la fila sin_peaje de estos pares tiene pasos en rutas_pasos_peaje.csv: no la tratamos como 0 de oficio
        f = reales[(p[0], p[1], "sin_peaje")]
        assert (f["vias_peaje"] != "") == (float(f["peaje_eur"]) > 0)


def test_toda_via_cobrada_esta_en_la_tabla_de_tramos(reales):
    with (PROCESADOS / "peajes_tramos.csv").open(encoding="utf-8", newline="") as f:
        vias = {r["via"] for r in csv.DictReader(f)}
    usadas = {v for f in reales.values() for v in f["vias_peaje"].split(";") if v}
    assert usadas and usadas <= vias
