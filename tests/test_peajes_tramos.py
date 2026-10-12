"""Pruebas de data/processed/peajes_tramos.csv (T2.4; Spec §5.3 y §7.2 Bloque 3). Sin red.

Comprueban el contrato de columnas, la trazabilidad (fuente y fecha por fila), la coherencia
eur_km = tarifa / km, las vigencias (AP-68 por provincia), la cobertura de las vías de
rutas_pasos_peaje.csv, la presencia de las vías de los 5 pares de validación, los km frente al
Catálogo RCE 2025 (si el zip está en data/raw) y la integridad de la evidencia (MANIFEST.txt).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

import construir_peajes as cp
import medir_km_osm as mk

RAIZ = Path(__file__).resolve().parents[1]
CSV_PATH = RAIZ / "data" / "processed" / "peajes_tramos.csv"
PASOS_PATH = RAIZ / "data" / "processed" / "rutas_pasos_peaje.csv"
CRUDOS = RAIZ / "data" / "raw" / "peajes_2026-10-12"
FUENTES_MD = RAIZ / "data" / "fuentes.md"
COLUMNAS = ["id", "via", "desde", "hasta", "operador", "ambito", "provincia", "km",
            "tarifa_ligeros_eur", "eur_km", "vigente_desde", "vigente_hasta", "fuente_url",
            "fecha_consulta", "nota"]  # Spec §5.3, exactas y en este orden
AMBITOS = {"estatal", "SEITT", "foral", "autonomico"}
TODO = "TODO(dato-faltante)"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CORTE = "2026-10-01"
FIN_AP68 = "2026-11-10"
DIA_POST_AP68 = "2026-11-11"


@pytest.fixture(scope="module")
def filas() -> list[dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _num(celda: str) -> float | None:
    return None if celda in (TODO, "") else float(celda)


def _vigente(f: dict[str, str], dia: str) -> bool:
    return (not f["vigente_desde"] or f["vigente_desde"] <= dia) and (
        not f["vigente_hasta"] or dia <= f["vigente_hasta"])


def _provincias(f: dict[str, str]) -> set[str]:
    return {p.strip() for p in f["provincia"].split(";")}


# --- Contrato y trazabilidad -------------------------------------------------------------------

def test_columnas_exactas_del_contrato():
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        assert next(csv.reader(f)) == COLUMNAS


def test_ninguna_fila_sin_fuente_url_ni_fecha_consulta(filas):
    assert filas
    for f in filas:
        assert f["fuente_url"].startswith("https://"), f["id"]
        assert ISO.match(f["fecha_consulta"]), f["id"]


def test_toda_fuente_url_fue_capturada_en_data_raw(filas):
    """Cada URL citada tiene su descarga registrada en cabeceras_http.txt (evidencia cruda)."""
    cabeceras = (CRUDOS / "cabeceras_http.txt").read_text(encoding="utf-8", errors="replace")
    for f in filas:
        assert f"URL: {f['fuente_url']}\n" in cabeceras, f["id"]


def test_toda_url_de_la_tabla_aparece_literal_en_fuentes_md(filas):
    """fuente_url y las URL citadas en `nota` figuran completas en data/fuentes.md (con su fecha de consulta)."""
    texto = FUENTES_MD.read_text(encoding="utf-8")
    urls = {f["fuente_url"] for f in filas}
    for f in filas:
        urls |= {u.rstrip(").,;") for u in re.findall(r"https://[^\s]+", f["nota"])}
    faltan = sorted(u for u in urls if u not in texto)
    assert not faltan, faltan


def test_ambito_pertenece_al_vocabulario(filas):
    for f in filas:
        assert f["ambito"] in AMBITOS, f["id"]


def test_id_unico_y_sin_celdas_obligatorias_vacias(filas):
    assert not [i for i, n in Counter(f["id"] for f in filas).items() if n > 1]
    for f in filas:
        for c in ("id", "via", "desde", "hasta", "operador", "provincia", "km", "tarifa_ligeros_eur",
                  "eur_km", "vigente_desde", "nota"):
            assert f[c].strip(), (f["id"], c)


def test_todo_solo_con_el_marcador_exacto(filas):
    for f in filas:
        for c in COLUMNAS:
            if "TODO" in f[c] and c != "nota":
                assert f[c] == TODO, (f["id"], c)


def test_km_positivo_y_tarifa_no_negativa(filas):
    for f in filas:
        km, tarifa = _num(f["km"]), _num(f["tarifa_ligeros_eur"])
        if km is not None:
            assert km > 0, f["id"]
        if tarifa is not None:
            assert tarifa >= 0, f["id"]


def test_eur_km_coherente_con_tarifa_sobre_km(filas):
    for f in filas:
        km, tarifa, eur_km = _num(f["km"]), _num(f["tarifa_ligeros_eur"]), _num(f["eur_km"])
        if tarifa == 0:
            assert eur_km == 0, f["id"]
        elif km is None or tarifa is None:
            assert f["eur_km"] == TODO, f["id"]
        else:
            assert eur_km is not None and abs(eur_km - tarifa / km) <= 0.00005, f["id"]
            assert re.match(r"^\d+\.\d{4}$", f["eur_km"]), f["id"]


def test_fechas_iso_y_desde_no_posterior_a_hasta(filas):
    for f in filas:
        for c in ("vigente_desde", "vigente_hasta", "fecha_consulta"):
            if f[c]:
                assert ISO.match(f[c]), (f["id"], c)
                dt.date.fromisoformat(f[c])
        if f["vigente_hasta"]:
            assert f["vigente_desde"] <= f["vigente_hasta"], f["id"]


def test_toda_fila_vigente_en_la_fecha_de_corte_tiene_tarifa_numerica(filas):
    for f in filas:
        if _vigente(f, CORTE):
            assert _num(f["tarifa_ligeros_eur"]) is not None, f["id"]


def test_filas_vigentes_en_la_fecha_de_corte_salvo_las_documentadas(filas):
    no_vigentes = {f["id"] for f in filas if not _vigente(f, CORTE)}
    assert no_vigentes == set(cp.NO_VIGENTES_EN_CORTE)
    for f in filas:
        if f["id"] in no_vigentes:
            assert f["vigente_desde"] > CORTE and "posterior a la fecha de corte" in f["nota"], f["id"]


# --- AP-68: vigencias por provincia --------------------------------------------------------------

def test_ap68_tarifa_de_avasa_termina_el_10_nov_2026(filas):
    vigentes = [f for f in filas if f["via"] == "AP-68" and _vigente(f, CORTE)]
    assert vigentes
    for f in vigentes:
        assert f["vigente_hasta"] == FIN_AP68, f["id"]
        assert f["operador"].startswith("Avasa"), f["id"]


def test_ap68_la_rioja_navarra_aragon_sin_peaje_de_avasa_tras_el_10_nov(filas):
    for f in filas:
        if f["via"] == "AP-68" and _provincias(f) & {"La Rioja", "Navarra", "Zaragoza", "Burgos"}:
            assert f["vigente_hasta"] == FIN_AP68, f["id"]
            assert not _vigente(f, DIA_POST_AP68), f["id"]


@pytest.mark.parametrize("provincia", ["Bizkaia", "Araba/Álava"])
def test_ap68_alava_y_bizkaia_cobran_el_1_oct_y_despues_del_10_nov(filas, provincia):
    ap68 = [f for f in filas if f["via"] == "AP-68" and provincia in _provincias(f)]
    assert any(_vigente(f, CORTE) for f in ap68), provincia
    post = [f for f in ap68 if _vigente(f, DIA_POST_AP68)]
    assert post, provincia
    for f in post:
        assert f["ambito"] == "foral" and f["vigente_desde"] == DIA_POST_AP68, f["id"]


# --- Valores transcritos (segunda transcripción, independiente de la tabla) -----------------------
#
# CADENAS: (ids de la cadena en orden, importe publicado de cada tramo en el mismo orden, tarifa oficial del
# recorrido completo). Los importes de cada tramo y del recorrido completo están en el crudo citado; su suma
# no aparece en ningún crudo. Donde suma != recorrido completo, el peaje no es aditivo y la nota de la primera
# fila documenta ambas cifras.
CADENAS = {
    # mitma_tarifas_2026_ap-6.pdf: Villalba-San Rafael 5,65; San Rafael-Villacastín 3,20; Villacastín-Adanero
    # 4,65; Villalba-Adanero 15,70.
    "AP-6 Villalba-Adanero": (["AP6-01", "AP6-02", "AP6-03"], (5.65, 3.20, 4.65), 15.70),
    # mitma_tarifas_2026_ap-71.pdf (diurna): 1,75; 2,50; 2,35; León-Astorga 6,20.
    "AP-71 León-Astorga": (["AP71-01", "AP71-02", "AP71-03"], (1.75, 2.50, 2.35), 6.20),
    # mitma_tarifas_2026_ap-66.pdf: 5,90; 4,30; 6,30; Campomanes-León 16,20.
    "AP-66 Campomanes-León": (["AP66-01", "AP66-02", "AP66-03"], (5.90, 4.30, 6.30), 16.20),
    # mitma_tarifas_2026_ap-68.pdf (tarifa general): Bilbao-Altube 6,85; Altube-Autop.Burgos 6,00;
    # Autop.Burgos-Zambrana 0,90; Zambrana-Haro 1,90; Haro-Logroño 4,85; Logroño-Autop.Navarra 9,40;
    # Autop.Navarra-Zaragoza 11,60; Bilbao-Zaragoza 39,90.
    "AP-68 Bilbao-Zaragoza": ([f"AP68-0{k}" for k in range(1, 8)],
                              (6.85, 6.00, 0.90, 1.90, 4.85, 9.40, 11.60), 39.90),
    # seitt_tarifas_r2_2026.pdf (efectivo): Ajalvir-Alcalá 0,95; Alcalá-Meco 1,05; Meco-Cabanillas 1,25;
    # Cabanillas-NII-Taracena 2,00; Ajalvir-NII-Taracena 5,20.
    "R-2 Ajalvir-Taracena": (["R2-03", "R2-04", "R2-05", "R2-06"], (0.95, 1.05, 1.25, 2.00), 5.20),
    # interbiak_DF_PEAJES_2026.pdf: Accesos Oeste-Ermua 4,60; bidegi_2026_AP-8_AP-1_AP-636_tarifak.pdf:
    # Ermua-Eibar 1,22; Eibar-Zarautz nagusia/Donostia 7,43; Acceso Oeste (Bilbao)-Donostia 13,81.
    "AP-8 Bilbao-Donostia": (["AP8-01", "AP8-02", "AP8-03"], (4.60, 1.22, 7.43), 13.81),
    # bidegi_2026_AP-8_AP-1_AP-636_tarifak.pdf: Eibar-Eskoriatza 4,96; Eskoriatza-Etxabarri-Ibiña 5,22;
    # Eibar-Etxabarri-Ibiña 10,04.
    "AP-1 Eibar-Vitoria": (["AP1-01", "AP1-02"], (4.96, 5.22), 10.04),
    # mitma_tarifas_2026_ap-7_estepona-guadiaro.pdf (normal): Estepona-Manilva 1,20; Manilva-Guadiaro 1,20;
    # Estepona-Guadiaro 2,45.
    "AP-7 Estepona-Guadiaro": (["AP7-03", "AP7-04"], (1.20, 1.20), 2.45),
    # mitma_tarifas_2026_ap-7_malaga-estepona.pdf (normal): troncal Calahonda 5,70 (= Málaga-Marbella);
    # troncal San Pedro 3,85 (= Marbella-Estepona); Málaga-Estepona 9,55.
    "AP-7 Málaga-Estepona": (["AP7-01", "AP7-02"], (5.70, 3.85), 9.55),
    # mitma_tarifas_2026_ap-7_alicante-cartagena.pdf (temporada baja): troncales Los Montesinos 2,85 y
    # La Zenia 2,85; 724 Entronque A-7 - 800 Los Beatos 5,70.
    "AP-7 Alicante-Cartagena": (["AP7-AC-01", "AP7-AC-02"], (2.85, 2.85), 5.70),
    # seitt_precios_web_r3_2026.pdf (efectivo): Madrid/M-40-M-50 0,95; M-50-Conexión A-3 2,45; Madrid-A-3 3,40.
    "R-3 Madrid-A-3": (["R3-01", "R3-02"], (0.95, 2.45), 3.40),
    # abertis_26_001-Aucat-C32-Castelldefels-Vendrell-T26.pdf (categoría II): troncal Vallcarca 8,42;
    # troncal Cubelles 5,03; Barcelona C-32 - El Vendrell O. 13,45.
    "C-32 Castelldefels-El Vendrell": (["C32-01", "C32-02"], (8.42, 5.03), 13.45),
}
# Filas que no forman cadena con otra: importe publicado tal cual en el crudo citado.
REFERENCIA = {
    "R2-01": 0.60, "R2-02": 0.60,              # seitt_tarifas_r2_2026.pdf: Aeropuerto 0,60; Alcobendas 0,60
    "AP61-01": 3.05, "AP61-02": 0.00,          # mitma_tarifas_2026_ap-61.pdf: San Rafael-Hontoria normal; Hontoria-Segovia
    "AP51-01": 1.75, "AP51-02": 0.00,          # mitma_tarifas_2026_ap-51.pdf: Villacastín-Vicolozano normal; Vicolozano-Ávila
    "AP9-01": 0.00, "AP9-02": 8.80,            # mitma_tarifas_2026_ap-9.pdf: exento RD 633/2006; A Coruña o A Barcala-Santiago
    "AP9-03": 0.00, "AP9-04": 7.55,            # Catálogo 'libre movimientos internos'; Santiago-Pontevedra
    "AP53-01": 7.25,                           # mitma_tarifas_2026_ap-53.pdf: Santiago-Alto de Santo Domingo
    "R4-01": 6.25,                             # seitt_tarifas_r4_2026_1.pdf: M-50-Ocaña/A-40 efectivo
    "AP41-01": 5.95,                           # seitt_precios_web_ap41_2026.pdf: R5-Toledo efectivo
    "M12-01": 1.00, "M12-02": 0.00,            # seitt_tarifa_m12_2026.pdf: Peaje Barajas efectivo; web SEITT tramos libres
    "AP4-01": 0.00,                            # mitma_peajes_dependientes_de_la_age.html: sin peaje desde 2020
    "AP15-01": 11.40,                          # bon_2025_258_9.html: Marcilla tronco 6,85 + Tiebas 4,55
    "AP15-02": 2.65,                           # bon_2025_258_9.html: Sarasa
    "AP8-VSM-01": 1.85,                        # interbiak_DF_PEAJES_2026.pdf: Arrigorriaga-Ortuella
    "AP68-POST-BI": 4.20,                      # bizkaia_nota_2026-07-22_bidesaria_ap68.html: ligeros desde 11-nov
}
# km forales: (p.k. inicial, p.k. final) publicados por el operador (planos de Bidegi, web de Interbiak).
KM_FORALES = {
    "AP8-01": (105.800, 75.580),    # Interbiak AP-8: Urgoiti 105+800, Ermua 75+580
    "AP8-03": (71.0, 27.7),         # Bidegi AP-8: Eibar 71, Donostia/Lasarte 27,7
    "AP8-VSM-01": (126.450, 113.0),  # Interbiak VSM: Trapagaran 126,450, Arrigorriaga 113
    "AP1-01": (145.8, 123.5),       # Bidegi AP-1: enlace AP-8 145,8, Eskoriatza 123,5
}
KM_PUBLICADO = {"AP68-POST-BI": 22.3}  # nota de la Diputación Foral de Bizkaia: tramo vizcaíno de 22,3 km
# km aproximados medidos en OSM (Spec v1.9): medicion_km_osm_2026-10-12.json, transcritos aquí otra vez.
KM_APROX_OSM = {
    "AP68-01": 35.594, "AP68-02": 32.49, "AP68-03": 4.056, "AP68-04": 14.997, "AP68-POST-VI": 55.416,
    "AP15-01": 82.978, "AP15-02": 15.705, "AP8-02": 5.009, "AP1-02": 15.794, "C32-01": 13.474, "C32-02": 29.054,
}
# Contrastes con una longitud oficial (±10 %): (ids cuyo km aproximado se suma, km oficial, fuente).
CONTRASTES_KM = {
    "AP-68 Bilbao-Haro": (["AP68-01", "AP68-02", "AP68-03", "AP68-04"], 87.0, "Catálogo RCE: Haro p.k. 87+000"),
    "AP-68 tramo alavés": (["AP68-POST-VI"], 77.597 - 22.3, "Catálogo p.k. 77+597 - 22,3 km de Bizkaia"),
}
EVIDENCIA_OSM = CRUDOS / "medicion_km_osm_2026-10-12.json"
NODOS_OSM = CRUDOS / "osm_motorway_junction_spain-261001.csv"
# Cifras de contraste de la evidencia que cada nota cita (nombre del contraste -> filas cuya nota lo cita).
CONTRASTE_EN_NOTA = {
    "AP-68 Haro-Logroño": ["AP68-01", "AP68-02", "AP68-03", "AP68-04"],
    "AP-68 Bilbao-Haro (suma AP68-01..04)": ["AP68-01", "AP68-02", "AP68-03", "AP68-04"],
    "AP-8 Urgoiti-Ermua (fila AP8-01)": ["AP8-02"],
    "AP-8 Eibar-Donostia (fila AP8-03)": ["AP8-02"],
    "AP-1 enlace AP-8-Eskoriatza (fila AP1-01)": ["AP1-02"],
    "AP-1 tramo guipuzcoano": ["AP1-02"],
    "AP-68 tramo vizcaíno": ["AP68-POST-VI"],
    "AP-68 tramo alavés (fila AP68-POST-VI)": ["AP68-POST-VI"],
}
# Contraste derivado de la AP-15 (BON 258/2025): longitud implícita = peaje con IVA / (tarifa base €/km × 1,21).
# id -> (peaje con IVA, tarifa base €/km sin IVA).
AP15_DERIVADO = {"AP15-01": (11.40, 0.110243), "AP15-02": (2.65, 0.121368)}
# Excluido del ±10 %: AP15-02 da -12,9 %. No es una longitud oficial sino una cuenta inversa del peaje (redondeado
# a 0,05 €), y el peaje de Sarasa puede cubrir también parte del anillo de Pamplona que la ruta medida no recorre
# (empieza en el empalme oeste con la variante A-15). Se documenta en la nota y se deja para decisión humana.
AP15_EXCLUIDOS_DEL_10 = {"AP15-02"}


def _fila(filas, ident):
    return next(f for f in filas if f["id"] == ident)


def _importes_en_texto(texto: str) -> set[float]:
    """Cifras en euros con coma decimal ('15,70') que aparecen en un texto."""
    return {float(c.replace(",", ".")) for c in re.findall(r"(?<![\d,])\d+,\d{2}(?![\d])", texto)}


@pytest.mark.parametrize("nombre", sorted(CADENAS))
def test_tarifa_de_cada_tramo_de_la_cadena_fila_a_fila(filas, nombre):
    ids, importes, _ = CADENAS[nombre]
    assert len(ids) == len(importes), nombre
    for ident, importe in zip(ids, importes):
        assert _num(_fila(filas, ident)["tarifa_ligeros_eur"]) == importe, ident


@pytest.mark.parametrize("nombre", sorted(CADENAS))
def test_nota_documenta_suma_y_recorrido_oficial(filas, nombre):
    """La nota de la primera fila da el recorrido completo oficial y, si el peaje no es aditivo, la suma."""
    ids, importes, oficial = CADENAS[nombre]
    suma = round(sum(importes), 2)
    cifras = _importes_en_texto(_fila(filas, ids[0])["nota"])
    assert oficial in cifras, nombre
    if abs(suma - oficial) > 0.005:
        assert suma in cifras, nombre


@pytest.mark.parametrize("ident", sorted(REFERENCIA))
def test_tarifas_de_referencia(filas, ident):
    assert _num(_fila(filas, ident)["tarifa_ligeros_eur"]) == REFERENCIA[ident]


def test_toda_tarifa_numerica_esta_comprobada_por_cadena_o_referencia(filas):
    en_cadena = {i for ids, _, _ in CADENAS.values() for i in ids}  # cubiertas fila a fila
    assert not en_cadena & set(REFERENCIA)
    for f in filas:
        if _num(f["tarifa_ligeros_eur"]) is not None:
            assert f["id"] in en_cadena | set(REFERENCIA), f["id"]


def test_km_forales_igual_a_la_resta_de_pk_publicados(filas):
    for ident, (pk_a, pk_b) in KM_FORALES.items():
        assert abs(_num(_fila(filas, ident)["km"]) - abs(pk_a - pk_b)) < 1e-6, ident
    for ident, km in KM_PUBLICADO.items():
        assert _num(_fila(filas, ident)["km"]) == km, ident


def test_todo_km_numerico_tiene_origen_documentado(filas):
    oficiales = set(cp.KM_RCE) | set(KM_FORALES) | set(KM_PUBLICADO)
    aproximados = set(KM_APROX_OSM)
    assert not oficiales & aproximados
    assert aproximados == set(mk.TRAMOS) | set(mk.TRAMOS_PROVINCIA)
    for f in filas:
        if _num(f["km"]) is not None:
            assert f["id"] in oficiales | aproximados, f["id"]
        # el texto de la nota distingue los km aproximados de los oficiales
        assert (cp.MARCA_KM_APROX in f["nota"]) == (f["id"] in aproximados), f["id"]


def test_km_aproximados_osm(filas):
    """km medidos en OSM: > 0, iguales a la evidencia y con el extracto y el crudo citados en la nota."""
    evidencia = json.loads(EVIDENCIA_OSM.read_text(encoding="utf-8"))
    assert "spain-261001" in evidencia["extracto"]
    for ident, km in KM_APROX_OSM.items():
        f = _fila(filas, ident)
        assert _num(f["km"]) == km > 0, ident
        assert evidencia["filas"][ident]["km"] == km, ident
        assert "spain-261001" in f["nota"] and "osrm_2026-10-12/rutas/" in f["nota"], ident


@pytest.mark.parametrize("nombre", sorted(CONTRASTES_KM))
def test_km_aproximados_dentro_del_10_por_ciento_del_contraste_oficial(filas, nombre):
    ids, oficial, _ = CONTRASTES_KM[nombre]
    medido = sum(_num(_fila(filas, i)["km"]) for i in ids)
    assert abs(medido - oficial) <= 0.10 * oficial, (nombre, medido, oficial)


def test_cifras_de_contraste_de_las_notas_salen_de_la_evidencia(filas):
    evidencia = json.loads(EVIDENCIA_OSM.read_text(encoding="utf-8"))
    assert set(CONTRASTE_EN_NOTA) == set(evidencia["contrastes"])
    for nombre, ids in CONTRASTE_EN_NOTA.items():
        cifra = f"{evidencia['contrastes'][nombre]['km']:.3f}".replace(".", ",")
        for ident in ids:
            assert cifra in _fila(filas, ident)["nota"], (nombre, ident, cifra)


@pytest.mark.parametrize("ident", sorted(AP15_DERIVADO))
def test_ap15_contraste_derivado_del_bon(filas, ident):
    peaje, tarifa_base = AP15_DERIVADO[ident]
    implicito = peaje / (tarifa_base * 1.21)
    f = _fila(filas, ident)
    assert f"{implicito:.2f}".replace(".", ",") in f["nota"], ident
    if ident not in AP15_EXCLUIDOS_DEL_10:
        assert abs(_num(f["km"]) - implicito) <= 0.10 * implicito, ident


def test_nodos_osm_citados_existen_en_la_extraccion_del_pbf():
    with NODOS_OSM.open(encoding="utf-8", newline="") as fh:
        nodos = {r["osm_id"]: (float(r["lon"]), float(r["lat"])) for r in csv.DictReader(fh)}
    citados = 0
    for descripcion, lon, lat in mk.EXTREMOS.values():
        m = re.search(r"nodo osm (\d+)", descripcion)
        if m:
            citados += 1
            assert nodos[m.group(1)] == (lon, lat), descripcion
    assert citados >= 15


def test_medir_sin_crudos_explica_que_faltan(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mk, "RUTAS", tmp_path)
    with pytest.raises(FileNotFoundError, match="crudos OSRM de T2.3"):
        mk.medir()
    assert mk.main(["--salida", str(tmp_path / "x.json")]) == 2
    assert "No se versionan" in capsys.readouterr().err
    assert not (tmp_path / "x.json").exists()


def test_m12_corte_en_la_m13_decidido(filas):
    """Spec v1.9 [DECIDIDO]: corte de la M-12 en la M-13, con los troncales de Barajas en el tramo que paga."""
    m1, m2 = _fila(filas, "M12-01"), _fila(filas, "M12-02")
    carretera, pk_a, pk_b = cp.KM_RCE["M12-01"]
    for pk_troncal in (3.000, 3.300):  # troncales de Barajas, web SEITT
        assert pk_a <= pk_troncal <= pk_b, pk_troncal
    assert m1["hasta"] == m2["desde"] == "Enl. M-13"
    assert cp.KM_RCE["M12-02"][1] == pk_b
    assert _num(m1["tarifa_ligeros_eur"]) > 0 and _num(m2["tarifa_ligeros_eur"]) == 0


def test_contrastes_del_metodo_en_la_evidencia_dentro_del_10_por_ciento():
    evidencia = json.loads(EVIDENCIA_OSM.read_text(encoding="utf-8"))
    assert len(evidencia["contrastes"]) >= 5
    for nombre, c in evidencia["contrastes"].items():
        assert c["km"] > 0 and abs(c["km"] - c["km_oficial"]) <= 0.10 * c["km_oficial"], nombre


def test_medicion_osm_reproducible_desde_los_crudos():
    if not all((mk.RUTAS / f"{c}.json.gz").exists() for c, *_ in [*mk.TRAMOS.values(), *mk.CONTRASTES.values()]):
        pytest.skip("crudos OSRM de T2.3 no disponibles (no se versionan, Spec §7.2 Bloque 2)")
    evidencia = json.loads(EVIDENCIA_OSM.read_text(encoding="utf-8"))
    assert mk.medir() == evidencia


def test_tarifa_general_no_descuento(filas):
    """SEITT publica telepeaje y efectivo: se usa efectivo/tarjeta (sin descuento)."""
    for f in filas:
        if f["ambito"] == "SEITT":
            assert "efectivo" in f["nota"].lower(), f["id"]


# --- Cobertura -----------------------------------------------------------------------------------

def test_vias_obligatorias_presentes(filas):
    vias = {f["via"] for f in filas}
    for via in ("AP-68", "AP-15", "M-12", "AP-9", "AP-4", "AP-41", "AP-7"):
        assert via in vias, via


def test_ap7_de_validacion_no_solo_en_malaga(filas):
    """Par Alicante-Murcia: hay filas AP-7 vigentes en Alicante/Murcia y la justificación del 0 EUR."""
    ap7 = [f for f in filas if f["via"] == "AP-7" and _vigente(f, CORTE)
           and _provincias(f) & {"Alicante/Alacant", "Murcia"}]
    assert ap7
    assert any("Validación Alicante-Murcia" in f["nota"] for f in ap7)


def test_cada_ref_de_rutas_pasos_peaje_tiene_fila_o_justificacion(filas):
    vias = {f["via"] for f in filas}
    with PASOS_PATH.open(encoding="utf-8", newline="") as fh:
        refs = {r["ref"] for r in csv.DictReader(fh)}
    for ref in refs:
        destino = cp.ALIAS_REF.get(ref, ref)
        assert destino in vias or ref in cp.REFS_SIN_FILA, repr(ref)
    for ref, motivo in cp.REFS_SIN_FILA.items():
        assert motivo.strip() and ref in refs, repr(ref)


def _cadena(filas, via, ids):
    tramos = [next(f for f in filas if f["id"] == i) for i in ids]
    assert all(t["via"] == via for t in tramos)
    for a, b in zip(tramos, tramos[1:]):
        assert a["hasta"] == b["desde"], (a["id"], b["id"])
    return tramos


def test_pares_de_validacion_tienen_tramos_encadenados(filas):
    bilbao_zaragoza = _cadena(filas, "AP-68", [f"AP68-0{k}" for k in range(1, 8)])
    assert bilbao_zaragoza[0]["desde"].startswith("Bilbao") and bilbao_zaragoza[-1]["hasta"].startswith("Zaragoza")
    coruna_pontevedra = _cadena(filas, "AP-9", ["AP9-01", "AP9-02", "AP9-03", "AP9-04"])
    assert coruna_pontevedra[0]["desde"].startswith("A Coruña")
    assert coruna_pontevedra[-1]["hasta"].startswith("Pontevedra")
    ap4 = next(f for f in filas if f["via"] == "AP-4")
    assert _num(ap4["tarifa_ligeros_eur"]) == 0 and _vigente(ap4, CORTE)


def test_todas_las_vias_encadenan_salvo_los_cortes_documentados(filas):
    """Filas consecutivas de la misma vía (vigentes en la fecha de corte): hasta == desde, o corte documentado."""
    vigentes = [f for f in filas if _vigente(f, CORTE)]
    cortes_vistos = set()
    for a, b in zip(vigentes, vigentes[1:]):
        if a["via"] != b["via"]:
            continue
        if a["hasta"] != b["desde"]:
            assert (a["id"], b["id"]) in cp.CORTES_DE_CADENA, (a["id"], b["id"])
            cortes_vistos.add((a["id"], b["id"]))
    assert cortes_vistos == set(cp.CORTES_DE_CADENA)
    for motivo in cp.CORTES_DE_CADENA.values():
        assert motivo.strip()


# --- km frente al Catálogo RCE 2025 y evidencia --------------------------------------------------

def test_rce_de_cada_fila_es_de_su_misma_via_sin_zip(filas):
    """Sin el zip: el tramo del Catálogo citado por cada fila es de su misma vía y la nota lo cita."""
    por_id = {f["id"]: f for f in filas}
    for ident, (carretera, pk_a, pk_b) in cp.KM_RCE.items():
        f = por_id[ident]
        assert f["via"] == carretera and pk_a < pk_b, ident
        assert _num(f["km"]) is not None, ident
        assert f"Tramo {carretera} p.k. " in f["nota"], ident
    assert set(cp.PROVINCIAS_RCE) <= set(cp.KM_RCE)


def test_km_catalogo_rechaza_tramos_que_cruzan_un_limite():
    tramos = [{"carretera": "X", "provincia": "P", "pk_inicio": "0", "pk_fin": "10", "longitud": "10"},
              {"carretera": "X", "provincia": "P", "pk_inicio": "10", "pk_fin": "20", "longitud": "10"}]
    assert cp.km_catalogo(tramos, "X", 0.0, 20.0) == 20.0
    assert cp.km_catalogo(tramos, "X", 10.0, 20.0) == 10.0
    with pytest.raises(ValueError):
        cp.km_catalogo(tramos, "X", 5.0, 20.0)
    with pytest.raises(ValueError):
        cp.km_catalogo(tramos, "X", 0.0, 15.0)


def test_km_igual_a_la_suma_del_catalogo_rce(filas):
    zip_cat = CRUDOS / cp.ARCHIVO_CATALOGO
    if not zip_cat.exists():
        pytest.skip("Catálogo RCE 2025 no versionado (.gitignore); se identifica por su SHA-256 en MANIFEST.txt")
    tramos = cp.leer_catalogo(zip_cat)
    por_id = {f["id"]: f for f in filas}
    assert cp.KM_RCE
    for ident, (carretera, pk_a, pk_b) in cp.KM_RCE.items():
        esperado = cp.km_catalogo(tramos, carretera, pk_a, pk_b, cp.PROVINCIAS_RCE.get(ident))
        assert esperado > 0, ident
        assert abs(_num(por_id[ident]["km"]) - esperado) < 1e-6, ident


def test_manifest_cubre_todos_los_crudos_con_sha256_correcto():
    lineas = (CRUDOS / "MANIFEST.txt").read_text(encoding="utf-8").splitlines()
    registro = {}
    for linea in lineas:
        if linea.strip() and not linea.startswith("#"):
            sha, nombre = linea.split(None, 1)
            registro[nombre.strip()] = sha
    presentes = {p.name for p in CRUDOS.iterdir() if p.is_file() and p.name != "MANIFEST.txt"}
    assert presentes <= set(registro)
    for nombre in presentes:
        assert hashlib.sha256((CRUDOS / nombre).read_bytes()).hexdigest() == registro[nombre], nombre


@pytest.mark.parametrize("rce, nota", [(("AP-6", 51.7, 61.3), "sin marca"), (None, "con {RCE}")])
def test_construir_rechaza_marca_rce_incoherente(monkeypatch, rce, nota):
    """La coherencia entre `rce` y la marca {RCE} se valida con ValueError (no con assert, que -O elimina)."""
    fila = cp._f(ident="X-01", via="AP-6", desde="A", hasta="B", operador="O", ambito="estatal", provincia="P",
                 km=1.0, tarifa=1.0, url="https://x", nota=nota, rce=rce)
    monkeypatch.setattr(cp, "definiciones", lambda: [fila])
    with pytest.raises(ValueError):
        cp.construir()


def test_construccion_reproducible(tmp_path):
    destino = tmp_path / "peajes_tramos.csv"
    cp.escribir(destino)
    assert destino.read_bytes() == CSV_PATH.read_bytes()
