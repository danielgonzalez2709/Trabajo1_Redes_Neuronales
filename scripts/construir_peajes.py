"""Construye data/processed/peajes_tramos.csv (T2.4; Spec §5.3 y §7.2 Bloque 3). Sin red.

Cada fila es un tramo entre dos puntos de cobro o enlaces publicados por el operador, encadenado con
el siguiente de la misma vía (el `hasta` de una fila es el `desde` de la siguiente, salvo los cortes de
CORTES_DE_CADENA). Las tarifas son transcripciones de los crudos de data/raw/peajes_2026-10-12/
(vehículos ligeros, tarifa general, sin descuentos ni telepeaje). Los km salen de una fuente oficial:
  - vías de la Red de Carreteras del Estado: suma de `longitud` del Catálogo RCE 2025 entre dos p.k.
    (argumento `rce` de cada fila; la prueba lo recalcula desde el zip si está en data/raw);
  - vías forales: resta de p.k. de enlaces publicados por Bidegi (AP-1/AP-8 Gipuzkoa) o Interbiak (AP-8 y VSM).
Lo que ninguna fuente oficial da queda como TODO(dato-faltante); nunca se deduce de prensa u OSM.

Limitación conocida (documentada en `nota`): los peajes cerrados y de barrera no son aditivos; la suma
de los tramos de una vía puede diferir de la tarifa del recorrido completo (la nota de la primera fila
de cada vía da el recorrido completo publicado para que T2.5 lo compare).

Uso:
    .venv/Scripts/python.exe scripts/construir_peajes.py [--salida RUTA]
"""

from __future__ import annotations

import argparse
import csv
import io
import struct
import sys
import zipfile
from pathlib import Path

from comun_bloque1 import PROCESSED
from medir_km_osm import EXTRACTO, TRAMOS as TRAMOS_OSM, TRAMOS_PROVINCIA as TRAMOS_OSM_PROVINCIA, descripcion

COLUMNAS = ["id", "via", "desde", "hasta", "operador", "ambito", "provincia", "km",
            "tarifa_ligeros_eur", "eur_km", "vigente_desde", "vigente_hasta", "fuente_url",
            "fecha_consulta", "nota"]
FECHA_CONSULTA = "2026-10-12"
TODO = "TODO(dato-faltante)"
SALIDA_POR_DEFECTO = PROCESSED / "peajes_tramos.csv"
ARCHIVO_CATALOGO = "mitma_260306-catalogorce2025.zip"  # en data/raw/peajes_2026-10-12/
INICIO_2026 = "2026-01-01"
FIN_AP68 = "2026-11-10"      # fin de la concesión de Avasa (BOE-A-2026-19039; respuesta del Gobierno al Congreso)
POST_AP68 = "2026-11-11"
MARCA_RCE = "{RCE}"          # en `nota`, se sustituye por la referencia al Catálogo RCE de la fila

# ------------------------------------------------------------------------------------------------
# Fuentes citadas en las filas (todas en data/raw/peajes_2026-10-12/ y en data/fuentes.md)
_MIN = "https://cdnfomento.blob.core.windows.net/portal-web-transportes/carreteras/nuestrared/autopistaspeaje/peajes-actuales"
URL_AP68 = f"{_MIN}/autopista-ap-68,-bilbao---zaragoza-2026.pdf"
URL_AP6 = f"{_MIN}/autopista-ap-6,-villalba---adanero-2026.pdf"
URL_AP51 = f"{_MIN}/autopista-ap-51,-conexion-ap-6---avila-2026.pdf"
URL_AP61 = f"{_MIN}/autopista-ap-61,-conexion-ap-6---segovia-2026.pdf"
URL_AP66 = f"{_MIN}/autopista-ap-66,-campomanes---leon-2026.pdf"
URL_AP71 = f"{_MIN}/autopista-ap-71,-leon---astorga-2026.pdf"
URL_AP53 = f"{_MIN}/autopista-ap-53,-santiago---alto-de-santo-domingo-2026.pdf"
URL_AP7_ME = f"{_MIN}/autopista-ap-7,-malaga---estepona-2026.pdf"
URL_AP7_EG = f"{_MIN}/autopista-ap-7,-estepona---guadiaro-2026.pdf"
URL_AP7_AC = f"{_MIN}/autopista-ap-7,-alicante---cartagena-2026.pdf"
URL_AP9 = ("https://cdn.transportes.gob.es/portal-web-transportes/carreteras/nuestrared/autopistaspeaje/"
           "peajes-actuales/autopista-ap-9,-ferrol---frontera-portuguesa-2026.pdf")
URL_CATALOGO = ("https://cdn.transportes.gob.es/portal-web-transportes/carreteras/red_carreteras/rce/"
                "260306-catalogorce2025.zip")
URL_DEPENDIENTES = "https://www.transportes.gob.es/carreteras/nuestra-red/autopistas-peaje/peajes-dependientes-de-la-age"
URL_CONGRESO_AP68 = "https://www.congreso.es/l15p/e10/e_0102096_n_000.pdf"
URL_BIZKAIA_AP68 = ("https://www.bizkaia.eus/es/web/comunicacion/noticias/-/news/detailView/bizkaia-rebaja-a-35-euros-"
                    "el-pago-maximo-mensual-por-circular-por-las-vias-de-peaje-del-territorio-a-partir-del-1-de-enero-de-2027")
_SEITT = "https://cdn.transportes.gob.es/portal-web-seitt/media/document"
URL_R2 = f"{_SEITT}/tarifas_r2_2026.pdf"
URL_R3 = f"{_SEITT}/precios_web_r3_2026.pdf"
URL_R4 = f"{_SEITT}/tarifas_r4_2026_1.pdf"
URL_R4_2025 = f"{_SEITT}/tarifas_r4_2025.pdf"
URL_M12 = f"{_SEITT}/tarifa_m12_2026.pdf"
URL_AP41 = f"{_SEITT}/precios_web_ap41_2026.pdf"
URL_SEITT_AP41 = "https://www.seitt.es/areas-negocio/autopistas/ap-41"
URL_SEITT_M12 = "https://www.seitt.es/areas-negocio/autopistas/m-12"
URL_BON_AP15 = "https://bon.navarra.es/es/anuncio/-/texto/2025/258/9"
URL_BIDEGI = ("https://www.bidegi.eus/documents/42696171/0/2026__AP-8_AP-1_AP-636_tarifak.pdf/"
              "0c9dbcf3-f3e7-e6f6-709b-8cbb7d9da9d5")
URL_BIDEGI_SAL_AP8 = ("https://www.bidegi.eus/documents/42696171/678110/28.+Salidas+y+areas+de+servicio+AP-8.pdf/"
                      "883055a0-35e8-9a0a-777c-61ef4d1e3b2c?t=1633353936698")
URL_BIDEGI_SAL_AP1 = ("https://www.bidegi.eus/documents/42696171/678110/29.+Salidas+y+areas+de+servicio+AP-1.pdf/"
                      "e270e853-4265-e876-42b5-7c3a459f1df4?t=1633353937414")
URL_DF_BIZKAIA = "https://interbiak.bizkaia.eus/documents/d/interbiak/DF_PEAJES_2026"
URL_INTERBIAK_AP8 = "https://interbiak.bizkaia.eus/es/-/autopista-ap-8"
URL_INTERBIAK_VSM = "https://interbiak.bizkaia.eus/es/-/variante-sur-metropolitana"
URL_C32 = "https://www.autopistas.com/wp-content/uploads/2025/12/26_001-Aucat-C32-Castelldefels-Vendrell-T26.pdf"

CAT = f"Catálogo RCE 2025 ({URL_CATALOGO})"

# ------------------------------------------------------------------------------------------------
# Notas comunes
N_AP68 = ("Tarifa general ligeros de Avasa (PDF Ministerio 'peajes vigentes desde 01/01/2026'). Vigente hasta el fin "
          "de la concesión, 10-nov-2026 (BOE-A-2026-19039, RD 730/2026; respuesta del Gobierno al Congreso, 23-feb-2026: "
          "tramos estatales de La Rioja y Aragón libres desde el día siguiente; Bizkaia, Álava y Navarra deciden). "
          "Recorrido completo Bilbao-Zaragoza publicado: 39,90 EUR; la suma de esta cadena da 41,50 EUR (peaje cerrado, "
          "no aditivo). La Rioja: exención/bonificación solo para movimientos internos de La Rioja (RD 2027/2009 y "
          "584/2014), no aplicable a pares de capitales.")
N_AP68_VASCO = (" km sin fuente oficial por tramo: el Catálogo RCE excluye el tramo vasco (empieza en el p.k. 77+597, "
                "L.P. Álava-Burgos) y la Diputación de Bizkaia solo publica 22,3 km para todo su tramo.")
N_SEITT = ("Tarifa en efectivo/tarjeta (la de telepeaje es menor y no se usa: descuento). Horario de cobro 06:00-24:00; "
           "gratis de 00:00 a 06:00 (se ignora: se asume viaje diurno). IVA incluido.")
N_RCE = "km = suma de 'longitud' del " + CAT + " entre los p.k. indicados (clase 'Autopista de peaje' salvo que se diga)."
N_NO_ADITIVO = "Peaje cerrado/de barrera: la suma de tramos no coincide exactamente con el recorrido completo."
N_CONTRASTE_AP68 = (" Contraste del método en la misma ruta: Bilbao-Haro (suma AP68-01..04) 87,138 km frente al "
                    "p.k. 87+000 de Haro en el Catálogo (+0,16 %); Haro-Logroño 39,826 km frente a 40,06 (-0,58 %).")
N_POST = "No vigente el 1-oct-2026 (posterior a la fecha de corte); solo para el escenario opcional post_ap68."
JUSTIFICACION_ALICANTE_MURCIA = (
    "Validación Alicante-Murcia: la ruta OSRM 'rapida' 2-28 (81,88 km, crudo osrm_2026-10-12/rutas/02_28_rapida) "
    "va por A-31 (3,0 km), A-70 (28,5 km) y A-7 (39,3 km), sin ninguna intersección 'toll'; las tres son 'Autovía' "
    "en el Catálogo RCE 2025 (A-31 y A-70 en Alicante; A-7 en Alicante y Murcia). Peaje esperado: 0 EUR. La AP-7 "
    "Alicante-Cartagena no está en el corredor Alicante-Murcia. La AP-7 Circunvalación de Alicante es gratuita "
    "(tarifa 0 EUR, BOE-A-2025-25961), aunque el Catálogo 2025 la clasifica como 'Autopista de peaje'.")

# Filas que, documentadamente, no están vigentes en la fecha de corte.
NO_VIGENTES_EN_CORTE = ("AP68-POST-BI", "AP68-POST-VI")

# Pares de filas consecutivas de la misma vía que no encadenan (hasta != desde), con su motivo.
CORTES_DE_CADENA = {
    ("AP15-01", "AP15-02"): ("la AP-15 entre Noáin y el empalme oeste con la variante A-15 (anillo de Pamplona) no tiene "
                           "fila: la ruta medida usa la variante oeste A-15, libre (12,53 km)"),
    ("R2-02", "R2-03"): "del p.k. 10,52 al 15,5 la R-2 comparte calzada con la M-50 (libre, sin fila)",
    ("AP7-04", "AP7-AC-01"): "otra concesión de la AP-7 (Ausur, Alicante-Cartagena), sin continuidad con Guadiaro",
    ("AP8-03", "AP8-VSM-01"): "la Variante Sur Metropolitana es un ramal distinto de la AP-8 (Bizkaia)",
}

# ------------------------------------------------------------------------------------------------
# Cobertura de rutas_pasos_peaje.csv (corrida OSRM 2026-10-12): `ref` de OSM -> vía de la tabla.
ALIAS_REF = {
    "AP-9M": "AP-9", "AP-9 M": "AP-9",   # AP-9 entre el enlace de la AP-9F y el de la A-6 (p.k. 13,8-16,4)
    "A-66": "AP-66",                     # 'Autopista Ruta de la Plata' Campomanes-La Magdalena: es la AP-66 de peaje
    "A-8": "AP-8",                       # 'Bizkaiko Golkoko Autobidea' Bilbao-Ermua: AP-8 de Interbiak (DF 147/2025)
    "DO": "AP-8",                        # 'Kantauriko autobidea' Donostia-Eibar: AP-8 de Bidegi
    "AP-1; AP-8": "AP-8",                # 'Kantauriko autobidea' Eibar-Donostia: AP-1/AP-8 de Bidegi
}
REFS_SIN_FILA = {
    "": ("Pasos sin ref de OSM: por sus coordenadas caen en enlaces/accesos de vías que sí tienen filas (AP-68 en "
         "Bilbao, Altube, Armiñón/Zambrana, Haro, Logroño, Tudela, Gallur; AP-6/AP-51 Villacastín; AP-66/AP-71 León; "
         "AP-1 Vitoria; AP-15 Pamplona; R-2 y M-12 Madrid; AP-9 Pontevedra). T2.5 los asigna por ubicación."),
    "N-622": ("Carretera convencional sin peaje (Catálogo RCE: N-622 Burgos/Palencia 'Carretera convencional'; el tramo "
              "Vitoria-Altube es foral y no figura en ninguna tarifa consultada). Los 2 cruces 'toll' están al final del "
              "paso, en el acceso a la AP-68 en Altube: se cobra en las filas AP-68."),
    "GI-20": ("Variante de Donostia (antigua AP-8, gestionada por Bidegi) sin tarifa propia en la tabla de Bidegi 2026; "
              "el recorrido hacia Donostia se cobra en la fila AP8-03."),
    "PA-34": ("Acceso oeste de Pamplona, sin tarifa en el BON 258/2025 ni en Audenasa: 1 cruce 'toll' junto a la AP-15."),
}

# ------------------------------------------------------------------------------------------------
# Lectura del Catálogo RCE (shapefile .dbf dentro del zip) sin dependencias externas.

_DBF_REGISTROS = slice(4, 12)    # cabecera: nº de registros (uint32), bytes de cabecera y de registro (uint16 ×2)
_DBF_DESCRIPTOR = 32             # cada descriptor de campo ocupa 32 bytes y empiezan en el byte 32
_DBF_FIN_DESCRIPTORES = 0x0D
_DBF_NOMBRE = slice(0, 11)       # nombre del campo, relleno con NUL
_DBF_LONGITUD = 16               # byte con la longitud del campo
_DBF_BORRADO = b"*"              # primer byte de un registro borrado


def _leer_dbf(datos: bytes, codificacion: str = "utf-8"):
    """Recorre un .dbf (dBASE III): cabecera de 32 bytes, descriptores de campo de 32 bytes hasta 0x0D
    y registros de ancho fijo (1 byte de marca de borrado + campos). Devuelve cada registro como dict de texto."""
    n_registros, bytes_cabecera, bytes_registro = struct.unpack("<IHH", datos[_DBF_REGISTROS])
    campos, pos = [], _DBF_DESCRIPTOR
    while datos[pos] != _DBF_FIN_DESCRIPTORES:
        descriptor = datos[pos:pos + _DBF_DESCRIPTOR]
        campos.append((descriptor[_DBF_NOMBRE].split(b"\0")[0].decode(), descriptor[_DBF_LONGITUD]))
        pos += _DBF_DESCRIPTOR
    for k in range(n_registros):
        inicio = bytes_cabecera + k * bytes_registro
        registro = datos[inicio:inicio + bytes_registro]
        if registro[:1] == _DBF_BORRADO:
            continue
        fila, desplazamiento = {}, 1
        for nombre, largo in campos:
            fila[nombre] = registro[desplazamiento:desplazamiento + largo].decode(codificacion, errors="replace").strip()
            desplazamiento += largo
        yield fila


def leer_catalogo(zip_path: Path) -> list[dict[str, str]]:
    """Tramos del Catálogo RCE 2025 (carretera, provincia, pk_inicio, pk_fin, longitud, inicio, fin, clase)."""
    with zipfile.ZipFile(zip_path) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".dbf"))
        return list(_leer_dbf(z.read(nombre)))


def km_catalogo(tramos: list[dict[str, str]], carretera: str, pk_a: float, pk_b: float,
                provincias: tuple[str, ...] | None = None) -> float:
    """Suma de `longitud` de los tramos de `carretera` contenidos en [pk_a, pk_b] (redondeo a 3 decimales),
    limitada a `provincias` si se indican (la AP-7 repite p.k. en otras provincias).
    Lanza ValueError si un tramo cruza uno de los dos p.k. límite (quedaría fuera en silencio)."""
    eps, total = 1e-6, 0.0
    for t in tramos:
        if t["carretera"] != carretera or (provincias is not None and t["provincia"] not in provincias):
            continue
        ini, fin = float(t["pk_inicio"]), float(t["pk_fin"])
        if ini >= pk_a - eps and fin <= pk_b + eps:
            total += float(t["longitud"])
        elif ini < pk_b - eps and fin > pk_a + eps:
            raise ValueError(f"{carretera}: el tramo p.k. {ini}-{fin} cruza el límite {pk_a}-{pk_b}")
    return round(total, 3)


# ------------------------------------------------------------------------------------------------
# Definición de las filas. km: número (oficial) o None (TODO). tarifa: número o None (TODO).
# rce: (carretera, p.k. inicial, p.k. final[, provincias]) del Catálogo RCE si el km sale de él.

def _f(*, ident, via, desde, hasta, operador, ambito, provincia, km, tarifa, url, nota,
       vig_desde=INICIO_2026, vig_hasta="", rce=None):
    return dict(ident=ident, via=via, desde=desde, hasta=hasta, operador=operador, ambito=ambito,
                provincia=provincia, km=km, tarifa=tarifa, url=url, nota=nota, vig_desde=vig_desde,
                vig_hasta=vig_hasta, rce=rce)


def _pk(valor: float) -> str:
    """p.k. con coma decimal, sin ceros sobrantes: 51.7 -> '51,7'."""
    return f"{valor:g}".replace(".", ",")


def _nota_rce(rce: tuple) -> str:
    carretera, pk_a, pk_b = rce[:3]
    return f"{N_RCE} Tramo {carretera} p.k. {_pk(pk_a)}-{_pk(pk_b)}."


EVIDENCIA_OSM = "data/raw/peajes_2026-10-12/medicion_km_osm_2026-10-12.json"
MARCA_KM_APROX = "km aproximado: medido en OSM"


def _nota_osm(ident: str) -> str:
    """Texto obligatorio (Spec v1.9) de un km medido en OSM, con el método y el crudo usados."""
    if ident in TRAMOS_OSM:
        crudo, ini, fin = TRAMOS_OSM[ident]
        metodo = (f"longitud a lo largo de la ruta del crudo osrm_2026-10-12/rutas/{crudo} entre "
                  f"'{descripcion(ini)}' y '{descripcion(fin)}'")
    else:
        crudo, ini, fin, prov = TRAMOS_OSM_PROVINCIA[ident]
        metodo = (f"longitud de la ruta del crudo osrm_2026-10-12/rutas/{crudo} dentro del polígono IGN de {prov}, "
                  f"entre '{descripcion(ini)}' y '{descripcion(fin)}'")
    return f" {MARCA_KM_APROX} ({metodo}; {EXTRACTO}; script medir_km_osm.py, evidencia {EVIDENCIA_OSM})."


MALAGA = ("Málaga", "Cádiz")
ALICANTE = ("Alicante/Alacant", "Murcia")


def definiciones() -> list[dict]:
    av = "Avasa (Autopista Vasco-Aragonesa, C.E.S.A.)"
    filas = [
        # --- AP-68 Bilbao-Zaragoza (estatal en concesión hasta 10-nov-2026) -------------------------
        _f(ident="AP68-01", via="AP-68", desde="Bilbao", hasta="Altube", operador=av, ambito="estatal",
           provincia="Bizkaia; Araba/Álava", km=35.594, tarifa=6.85, url=URL_AP68,
           nota=N_AP68 + N_AP68_VASCO + " Diputación de Bizkaia (nota 22-jul-2026): su tramo cuesta hoy 6,85 EUR."
           + _nota_osm("AP68-01") + N_CONTRASTE_AP68,
           vig_hasta=FIN_AP68),
        _f(ident="AP68-02", via="AP-68", desde="Altube", hasta="Enlace AP-1 (Autop. Burgos)", operador=av,
           ambito="estatal", provincia="Araba/Álava", km=32.49, tarifa=6.00, url=URL_AP68,
           nota=N_AP68 + N_AP68_VASCO + _nota_osm("AP68-02") + N_CONTRASTE_AP68, vig_hasta=FIN_AP68),
        _f(ident="AP68-03", via="AP-68", desde="Enlace AP-1 (Autop. Burgos)", hasta="Zambrana", operador=av,
           ambito="estatal", provincia="Araba/Álava", km=4.056, tarifa=0.90, url=URL_AP68,
           nota=N_AP68 + N_AP68_VASCO + _nota_osm("AP68-03") + N_CONTRASTE_AP68, vig_hasta=FIN_AP68),
        _f(ident="AP68-04", via="AP-68", desde="Zambrana", hasta="Haro", operador=av, ambito="estatal",
           provincia="Araba/Álava; Burgos; La Rioja", km=14.997, tarifa=1.90, url=URL_AP68,
           nota=N_AP68 + N_AP68_VASCO + " Haro = p.k. 87+000 y L.P. Álava-Burgos = 77+597 (Catálogo RCE); el "
           "p.k. de Zambrana no está publicado. Tramo de Burgos: 0,3 km (Catálogo); la respuesta al Congreso no lo "
           "menciona." + _nota_osm("AP68-04") + N_CONTRASTE_AP68, vig_hasta=FIN_AP68),
        _f(ident="AP68-05", via="AP-68", desde="Haro", hasta="Logroño", operador=av, ambito="estatal",
           provincia="La Rioja", km=40.06, tarifa=4.85, url=URL_AP68, rce=("AP-68", 87.0, 126.9),
           nota=N_AP68 + " {RCE} Haro = Enl. LR-111; Logroño = Enl. N-111.", vig_hasta=FIN_AP68),
        _f(ident="AP68-06", via="AP-68", desde="Logroño", hasta="Enlace AP-15 (Autop. Navarra)", operador=av,
           ambito="estatal", provincia="La Rioja; Navarra", km=80.24, tarifa=9.40, url=URL_AP68,
           rce=("AP-68", 126.9, 208.3),
           nota=N_AP68 + " {RCE} Tramo navarro transferido a Navarra (RD 1230/2025, citado en el "
           "BOE-A-2026-19039), aunque el Catálogo 2025 aún lo lista (p.k. 162,53-166,48 y 201,85-237,0).",
           vig_hasta=FIN_AP68),
        _f(ident="AP68-07", via="AP-68", desde="Enlace AP-15 (Autop. Navarra)", hasta="Zaragoza", operador=av,
           ambito="estatal", provincia="Navarra; Zaragoza", km=84.26, tarifa=11.60, url=URL_AP68,
           rce=("AP-68", 208.3, 291.83),
           nota=N_AP68 + " {RCE} Zaragoza = Int. A-68 (después, 3,37 km 'Autopista libre').", vig_hasta=FIN_AP68),
        _f(ident="AP68-POST-BI", via="AP-68", desde="Bilbao", hasta="Límite Bizkaia (tramo vizcaíno)",
           operador="Diputación Foral de Bizkaia (Interbiak)", ambito="foral", provincia="Bizkaia", km=22.3,
           tarifa=4.20, url=URL_BIZKAIA_AP68,
           nota=N_POST + " Nota oficial de la Diputación Foral de Bizkaia (22-jul-2026): tramo vizcaíno de 22,3 km "
           "en gestión foral desde el 11-nov-2026; tabla 'Ligeros 6,85 (actual) -> 4,20 (desde 11 de noviembre)'. "
           "El mismo texto habla de 'reducción media del 20 %', que no cuadra con -38,7 %. El Decreto Foral que la "
           "regulará (vigencia transitoria de dos meses) no está publicado a 2026-10-12.", vig_desde=POST_AP68),
        _f(ident="AP68-POST-VI", via="AP-68", desde="Límite Bizkaia", hasta="L.P. Álava-Burgos (tramo alavés)",
           operador="Diputación Foral de Álava (Arabat)", ambito="foral", provincia="Araba/Álava", km=55.416,
           tarifa=None, url=URL_CONGRESO_AP68,
           nota=N_POST + " SUPUESTO DEL SPEC (§7.1: 'los tramos de Álava seguirán cobrando'), no dato oficial: las "
           "fuentes oficiales solo dicen que Álava es titular y decide si cobra (respuesta del Gobierno al Congreso, "
           "23-feb-2026) y el BOTHA 2026/083 subvenciona el peaje de Avasa solo hasta el 10-nov-2026. La tarifa solo "
           "consta en prensa (proyecto de norma foral, 6 céntimos/km, 55 km): TODO." + _nota_osm("AP68-POST-VI")
           + " Contraste: medido 55,416 km frente a 77,597 km (p.k. del Catálogo en la L.P. Álava-Burgos) - 22,3 km de "
           "Bizkaia = 55,297 km (+0,22 %); en la misma medición el tramo vizcaíno da 22,343 km frente a 22,3 oficiales (+0,19 %).",
           vig_desde=POST_AP68),
        # --- AP-6 / AP-61 / AP-51 (Castellana) -----------------------------------------------------
        _f(ident="AP6-01", via="AP-6", desde="Villalba (Enl. N-6, p.k. 51+700)", hasta="San Rafael (Enl. AP-61)",
           operador="Castellana", ambito="estatal", provincia="Madrid; Segovia", km=9.58, tarifa=5.65, url=URL_AP6,
           rce=("AP-6", 51.7, 61.3),
           nota="Tarifa general ligeros. Recorrido completo Villalba-Adanero 15,70 EUR; la cadena suma 13,50. "
           + N_NO_ADITIVO + " {RCE} Excluye los p.k. 39,56-51,7 ('libre de peaje para movimientos internos')."),
        _f(ident="AP6-02", via="AP-6", desde="San Rafael (Enl. AP-61)", hasta="Villacastín (Enl. AP-51/N-110)",
           operador="Castellana", ambito="estatal", provincia="Segovia", km=19.65, tarifa=3.20, url=URL_AP6,
           rce=("AP-6", 61.3, 81.0), nota="Tarifa general ligeros (en el PDF 'VILLASCASTIN'). {RCE}"),
        _f(ident="AP6-03", via="AP-6", desde="Villacastín (Enl. AP-51/N-110)", hasta="Adanero (Conexión A-6/N-6)",
           operador="Castellana", ambito="estatal", provincia="Segovia; Ávila", km=28.25, tarifa=4.65, url=URL_AP6,
           rce=("AP-6", 81.0, 109.6), nota="Tarifa general ligeros. {RCE}"),
        _f(ident="AP61-01", via="AP-61", desde="San Rafael (Conexión AP-6)", hasta="Hontoria (Enl. N-603/SG-V-7241)",
           operador="Castellana", ambito="estatal", provincia="Segovia", km=24.81, tarifa=3.05, url=URL_AP61,
           rce=("AP-61", 61.1, 86.0),
           nota="Nivel NORMAL ligeros (no hay tarifa general: valle 2,00, punta 4,95; decisión pendiente). "
           "Explotación conjunta Villalba-Segovia normal 8,60 EUR. {RCE}"),
        _f(ident="AP61-02", via="AP-61", desde="Hontoria (Enl. N-603/SG-V-7241)", hasta="Segovia",
           operador="Castellana", ambito="estatal", provincia="Segovia", km=2.08, tarifa=0.00, url=URL_AP61,
           rce=("AP-61", 86.0, 88.6),
           nota="Hontoria-Segovia 0,00 EUR en el PDF. {RCE} Clase 'libre de peaje para movimientos internos'."),
        _f(ident="AP51-01", via="AP-51", desde="Villacastín (Conexión AP-6)", hasta="Vicolozano (Enl. N-110)",
           operador="Castellana", ambito="estatal", provincia="Segovia; Ávila", km=22.078, tarifa=1.75,
           url=URL_AP51, rce=("AP-51", 80.83, 103.0),
           nota="Nivel NORMAL ligeros Villacastín-Vicolozano/Ávila (valle 1,05-1,10, punta 2,90-2,95; decisión "
           "pendiente). Explotación conjunta Villalba-Ávila normal 11,85 EUR. {RCE}"),
        _f(ident="AP51-02", via="AP-51", desde="Vicolozano (Enl. N-110)", hasta="Ávila (Conexión AV-20)",
           operador="Castellana", ambito="estatal", provincia="Ávila", km=1.892, tarifa=0.00, url=URL_AP51,
           rce=("AP-51", 103.0, 104.9),
           nota="Vicolozano-Ávila 0,00 EUR en el PDF. {RCE} Clase 'libre de peaje para movimientos internos'."),
        # --- AP-66 (Aucalsa) y AP-71 (Aulesa) ----------------------------------------------------
        _f(ident="AP66-01", via="AP-66", desde="Campomanes (Conexión A-66)", hasta="Oblanca (Enl. CL-626)",
           operador="Aucalsa", ambito="estatal", provincia="Asturias; León", km=28.21, tarifa=5.90, url=URL_AP66,
           rce=("AP-66", 65.0, 92.3),
           nota="Tarifa ligeros 'con aplicación RD-L 20/2022' (la tabla de descuentos por paso dinámico no se usa). "
           "Recorrido completo Campomanes-León 16,20 EUR; la cadena suma 16,50. OSM etiqueta parte como 'A-66'. "
           "{RCE}"),
        _f(ident="AP66-02", via="AP-66", desde="Oblanca (Enl. CL-626)", hasta="La Magdalena (Enl. CL-626)",
           operador="Aucalsa", ambito="estatal", provincia="León", km=20.2, tarifa=4.30, url=URL_AP66,
           rce=("AP-66", 92.3, 112.5), nota="Tarifa ligeros. {RCE}"),
        _f(ident="AP66-03", via="AP-66", desde="La Magdalena (Enl. CL-626)", hasta="León (Enl. N-120)",
           operador="Aucalsa", ambito="estatal", provincia="León", km=27.85, tarifa=6.30, url=URL_AP66,
           rce=("AP-66", 112.5, 141.4), nota="Tarifa ligeros. {RCE}"),
        _f(ident="AP71-01", via="AP-71", desde="León (Enl. A-66/LE-30)", hasta="Villadangos (Enl. LE-413)",
           operador="Aulesa", ambito="estatal", provincia="León", km=10.6, tarifa=1.75, url=URL_AP71,
           rce=("AP-71", 0.0, 9.5),
           nota="Tarifa DIURNA ligeros (07-23 h; nocturna 0,70; no hay tarifa general: decisión pendiente). "
           "Recorrido completo León-Astorga diurna 6,20 EUR; la cadena suma 6,60. Mapeo Villadangos=Enl. LE-413 y "
           "Hospital de Órbigo=Enl. LE-420: interpretación del curador. {RCE}"),
        _f(ident="AP71-02", via="AP-71", desde="Villadangos (Enl. LE-413)", hasta="Hospital de Órbigo (Enl. LE-420)",
           operador="Aulesa", ambito="estatal", provincia="León", km=13.9, tarifa=2.50, url=URL_AP71,
           rce=("AP-71", 9.5, 23.3), nota="Tarifa diurna ligeros (nocturna 1,00). {RCE}"),
        _f(ident="AP71-03", via="AP-71", desde="Hospital de Órbigo (Enl. LE-420)",
           hasta="Astorga (Enl. N-120/LE-6453)", operador="Aulesa", ambito="estatal", provincia="León", km=10.2,
           tarifa=2.35, url=URL_AP71, rce=("AP-71", 23.3, 34.2),
           nota="Tarifa diurna ligeros (nocturna 0,95). {RCE}"),
        # --- AP-9 (Audasa) y AP-53 (Acega) ----------------------------------------------------------
        _f(ident="AP9-01", via="AP-9", desde="A Coruña (Enl. AC-11)", hasta="A Barcala", operador="Audasa",
           ambito="estatal", provincia="A Coruña", km=5.214, tarifa=0.00, url=URL_AP9, rce=("AP-9", 2.6, 7.814),
           nota="Exento: RD 633/2006 (nota del PDF: A Coruña-A Barcala sin peaje). Clase del Catálogo: 'Autopista "
           "con peaje bonificado'. {RCE}"),
        _f(ident="AP9-02", via="AP-9", desde="A Barcala", hasta="Santiago norte (Enl. SC-20)", operador="Audasa",
           ambito="estatal", provincia="A Coruña", km=59.7, tarifa=8.80, url=URL_AP9, rce=("AP-9", 7.814, 67.0),
           nota="Tarifa general ligeros 'A Coruña o A Barcala - Santiago' (tabla A de recurrencia no usada). Incluye "
           "el enlace con la A-6 (OSM: 'AP-9M'); el PDF publica A Barcala-Guísamo/Sta. Marta 2,05 y "
           "Guísamo-Santiago 7,85, pero el p.k. de 'Guísamo' en la AP-9 no está identificado: no se parte. {RCE}"),
        _f(ident="AP9-03", via="AP-9", desde="Santiago norte (Enl. SC-20)", hasta="Santiago sur (Enl. AG-56)",
           operador="Audasa", ambito="estatal", provincia="A Coruña", km=7.7, tarifa=0.00, url=URL_AP9,
           rce=("AP-9", 67.0, 74.7),
           nota="Catálogo: 'Autopista libre de peaje para movimientos internos'. El PDF publica 'Santiago-Santiago "
           "4,55' sin explicar qué recorrido es: no se usa. Contraste del cazador: la calculadora oficial de Audasa da "
           "A Coruña -> Pontevedra = 16,35 EUR (ligeros), igual a la suma de la cadena AP9-01..04 (0,00 + 8,80 + 0,00 "
           "+ 7,55); evidencia alucinaciones/evidencias/T2.4_audasa_calculadora_2026-10-12.json. {RCE}"),
        _f(ident="AP9-04", via="AP-9", desde="Santiago sur (Enl. AG-56)", hasta="Pontevedra (Enl. PO-531)",
           operador="Audasa", ambito="estatal", provincia="A Coruña; Pontevedra", km=54.3, tarifa=7.55, url=URL_AP9,
           rce=("AP-9", 74.7, 128.8),
           nota="Tarifa general ligeros 'Santiago-Pontevedra'. Mapeo Pontevedra=Enl. PO-531: interpretación del "
           "curador. {RCE}"),
        _f(ident="AP53-01", via="AP-53", desde="Santiago (Int. N-525/SC-11)",
           hasta="Alto de Santo Domingo (Enl. N-525/AG-53)", operador="Acega", ambito="estatal",
           provincia="A Coruña; Pontevedra", km=56.36, tarifa=7.25, url=URL_AP53, rce=("AP-53", 0.0, 56.6),
           nota="Tarifa ligeros 'con aplicación RD-L 20/2022' (tabla de recurrencia extraordinaria no usada). {RCE}"),
        # --- AP-7 Málaga-Guadiaro (Ausol) ---------------------------------------------------------
        _f(ident="AP7-01", via="AP-7", desde="Málaga (Enl. A-387/A-7)", hasta="Marbella (Conexión A-7)",
           operador="Ausol", ambito="estatal", provincia="Málaga", km=27.606, tarifa=5.70, url=URL_AP7_ME,
           rce=("AP-7", 185.58, 213.0, MALAGA),
           nota="Nivel NORMAL (troncal de Calahonda): se aplica a todos en temporada baja; el 1-oct-2026 es "
           "temporada baja (alta = jun-sep y 17 días de Semana Santa). Especial 9,25. Málaga-Estepona normal 9,55 = "
           "5,70 + 3,85. {RCE}"),
        _f(ident="AP7-02", via="AP-7", desde="Marbella (Conexión A-7)", hasta="Estepona (Enl. A-7)",
           operador="Ausol", ambito="estatal", provincia="Málaga", km=24.47, tarifa=3.85, url=URL_AP7_ME,
           rce=("AP-7", 156.44, 180.54, MALAGA),
           nota="Nivel normal (troncal de San Pedro de Alcántara); especial 6,25. Entre los p.k. 180,54 y 185,58 la "
           "AP-7 no figura en el Catálogo (tramo común con la A-7). {RCE}"),
        _f(ident="AP7-03", via="AP-7", desde="Estepona (Enl. A-7)", hasta="Manilva (Enl. A-377)", operador="Ausol",
           ambito="estatal", provincia="Málaga", km=12.2, tarifa=1.20, url=URL_AP7_EG,
           rce=("AP-7", 142.3, 154.01, MALAGA),
           nota="Nivel normal (temporada baja); especial 2,00. Estepona-Guadiaro 2,45 (troncal de Manilva); la "
           "cadena suma 2,40. Mapeo Manilva=Enl. A-377: interpretación del curador. {RCE}"),
        _f(ident="AP7-04", via="AP-7", desde="Manilva (Enl. A-377)", hasta="Guadiaro (Conexión A-7)",
           operador="Ausol", ambito="estatal", provincia="Málaga; Cádiz", km=10.28, tarifa=1.20, url=URL_AP7_EG,
           rce=("AP-7", 133.48, 142.3, MALAGA), nota="Nivel normal; especial 2,00. {RCE}"),
        # --- AP-7 Alicante-Cartagena (Ausur) ------------------------------------------------------
        _f(ident="AP7-AC-01", via="AP-7", desde="Entronque con la A-7 (salida 724)",
           hasta="San Miguel de Salinas (Enl. CV-95, salida 758)", operador="Ausur", ambito="estatal",
           provincia="Alicante/Alacant", km=32.8, tarifa=2.85, url=URL_AP7_AC, rce=("AP-7", 724.0, 758.3, ALICANTE),
           nota="TARIFA TEMPORADA BAJA ligeros (troncal de Los Montesinos); el 1-oct-2026 es temporada baja (alta = "
           "jun-sep y 17 días de Semana Santa); alta 5,10. Recorrido 724-800 = 5,70 = 2,85 + 2,85. Los números de "
           "salida del PDF coinciden con los p.k. del Catálogo. " + JUSTIFICACION_ALICANTE_MURCIA + " {RCE}"),
        _f(ident="AP7-AC-02", via="AP-7", desde="San Miguel de Salinas (Enl. CV-95, salida 758)",
           hasta="Los Beatos-El Algar (Conexión AP-7R, salida 800)", operador="Ausur", ambito="estatal",
           provincia="Alicante/Alacant; Murcia", km=43.8, tarifa=2.85, url=URL_AP7_AC,
           rce=("AP-7", 758.3, 799.8, ALICANTE),
           nota="Temporada baja ligeros (troncal de La Zenia); alta 5,10. Catálogo: tramos 'de peaje' y 'libre de "
           "peaje para movimientos internos'. {RCE}"),
        # --- SEITT --------------------------------------------------------------------------------
        _f(ident="R2-01", via="R-2", desde="Enl. M-40", hasta="Enl. M-12", operador="SEITT", ambito="SEITT",
           provincia="Madrid", km=5.1, tarifa=0.60, url=URL_R2, rce=("R-2", 0.0, 3.8),
           nota=N_SEITT + " Troncal Aeropuerto (p.k. 3,50, web SEITT). {RCE}"),
        _f(ident="R2-02", via="R-2", desde="Enl. M-12", hasta="Confluencia M-50 (Jarama)", operador="SEITT",
           ambito="SEITT", provincia="Madrid", km=5.1, tarifa=0.60, url=URL_R2, rce=("R-2", 3.8, 10.52),
           nota=N_SEITT + " Troncal Alcobendas (p.k. 7,50). Del p.k. 10,52 al 15,5 la R-2 comparte calzada con la "
           "M-50 (libre). {RCE}"),
        _f(ident="R2-03", via="R-2", desde="Ajalvir (Confluencia M-50)", hasta="Alcalá de Henares (Enl. M-100)",
           operador="SEITT", ambito="SEITT", provincia="Madrid", km=8.1, tarifa=0.95, url=URL_R2,
           rce=("R-2", 15.5, 24.4),
           nota=N_SEITT + " Ajalvir-Alcalá. Recorrido Ajalvir-NII Taracena 5,20; la cadena R2-03..06 suma 5,25. "
           "Mapeo de nombres a enlaces por los p.k. de la web SEITT (Alcalá 24, Meco 34, Cabanillas 44, Guadalajara "
           "Norte 55). {RCE}"),
        _f(ident="R2-04", via="R-2", desde="Alcalá de Henares (Enl. M-100)", hasta="Meco (Enl. M-116)",
           operador="SEITT", ambito="SEITT", provincia="Madrid", km=8.9, tarifa=1.05, url=URL_R2,
           rce=("R-2", 24.4, 33.3), nota=N_SEITT + " {RCE}"),
        _f(ident="R2-05", via="R-2", desde="Meco (Enl. M-116)", hasta="Cabanillas (Enl. N-320)", operador="SEITT",
           ambito="SEITT", provincia="Madrid; Guadalajara", km=10.6, tarifa=1.25, url=URL_R2,
           rce=("R-2", 33.3, 43.9), nota=N_SEITT + " {RCE}"),
        _f(ident="R2-06", via="R-2", desde="Cabanillas (Enl. N-320)", hasta="NII-Taracena (Enl. A-2/CM-1003)",
           operador="SEITT", ambito="SEITT", provincia="Guadalajara", km=15.3, tarifa=2.00, url=URL_R2,
           rce=("R-2", 43.9, 59.7),
           nota=N_SEITT + " Cabanillas-NII Taracena (incluye troncal Marchamalo, p.k. 54,30; Guadalajara "
           "Norte-Taracena interno 0,00 por bonificación 100 %). {RCE}"),
        _f(ident="R3-01", via="R-3", desde="Madrid (Conexión M-23/M-40)", hasta="Enl. M-50", operador="SEITT",
           ambito="SEITT", provincia="Madrid", km=8.2, tarifa=0.95, url=URL_R3, rce=("R-3", 0.0, 7.3),
           nota=N_SEITT + " Madrid/M-40-M-50. Recorrido completo Madrid-A-3 3,40 = 0,95 + 2,45. {RCE}"),
        _f(ident="R3-02", via="R-3", desde="Enl. M-50", hasta="Conexión A-3", operador="SEITT", ambito="SEITT",
           provincia="Madrid", km=21.1, tarifa=2.45, url=URL_R3, rce=("R-3", 7.3, 29.5), nota=N_SEITT + " {RCE}"),
        _f(ident="R4-01", via="R-4", desde="Enl. M-50", hasta="Ocaña (Enl. A-40)", operador="SEITT", ambito="SEITT",
           provincia="Madrid; Toledo", km=46.5, tarifa=6.25, url=URL_R4, rce=("R-4", 0.0, 45.6),
           nota=N_SEITT + " Recorrido M-50-Ocaña/A-40 (troncales Pinto p.k. 4 y Aranjuez p.k. 29). El PDF se titula "
           "'Peaje 2026 R4' pero su encabezado dice 'En vigor desde el 1 de enero de 2025'. Se toma como tarifa 2026 "
           "porque: (a) es el PDF que la web SEITT enlaza como 'Tarifas R4 2026'; (b) cita como base el Acuerdo del "
           "Consejo de Ministros de 9-dic-2025 (BOE-A-2025-25961, 18-dic-2025), posterior al 1-ene-2025; (c) sus "
           "importes difieren de la tarifa 2025 (" + URL_R4_2025 + ", 'Peaje 2025 R4': M-50-Ocaña 6,15 efectivo, "
           "con encabezado '2023'; tarifas_r4_2026.pdf, no enlazado, repite los importes de 2025). El encabezado es "
           "una errata recurrente de los PDF de la SEITT: decisión humana si se prefiere 2025-01-01. Después del "
           "Enl. A-40 quedan 7,6 km hasta la A-4/AP-36 sin tarifa propia. {RCE}"),
        _f(ident="AP41-01", via="AP-41", desde="Enl. R-5 (Madrid)", hasta="Conexión A-40 (Toledo)", operador="SEITT",
           ambito="SEITT", provincia="Madrid; Toledo", km=48.6, tarifa=5.95, url=URL_AP41, rce=("AP-41", 0.0, 47.6),
           nota=N_SEITT + " Recorrido R5-Toledo (semitroncales Madrid p.k. 6+350 y Toledo p.k. 45+800, web SEITT "
           + URL_SEITT_AP41 + "). La web declara 51,80 km de peaje; el Catálogo da 48,6 km: discrepancia. "
           "Validación Madrid-Toledo: la ruta OSRM 'rapida' (74,65 km) no tiene pasos 'toll' y va por la A-42, "
           "'Autovía' en el Catálogo (Madrid 26,91 km y Toledo 47,187 km): peaje 0 EUR; esta fila sirve para el "
           "contraste. {RCE}"),
        _f(ident="M12-01", via="M-12", desde="Enl. M-40", hasta="Enl. M-13", operador="SEITT", ambito="SEITT",
           provincia="Madrid", km=3.16, tarifa=1.00, url=URL_M12, rce=("M-12", 0.0, 3.55),
           nota=N_SEITT + " Troncal Barajas (p.k. 3+000/3+300). Web SEITT: peaje en ambos sentidos entre la M-40 y "
           "la M-11. Corte en la M-13 (decisión humana del 12-oct, Spec v1.9) para que los troncales de Barajas caigan "
           "en el tramo que paga. Longitudes: SEITT declara 8,40 km de peaje y 5,89 km libres (14,29 km); el Catálogo "
           "da 10,865 km a la M-12 entera: discrepancia. {RCE}"),
        _f(ident="M12-02", via="M-12", desde="Enl. M-13", hasta="Enl. A-1", operador="SEITT", ambito="SEITT",
           provincia="Madrid", km=6.455, tarifa=0.00, url=URL_SEITT_M12, rce=("M-12", 3.55, 10.865),
           nota="Sin peaje de paso: la web SEITT da como libres M-13-T4, T4-R-2 y R-2-A-1; solo cobra el lateral de "
           "Alcobendas (0,55 efectivo, p.k. 7) en sentido sur desde la Salida 7 a la T4 y desde la Salida 3 a la "
           "M-11. El Catálogo clasifica hasta la M-110 como 'Autopista de peaje': discrepancia. {RCE}"),
        # --- AP-4 (validación Sevilla-Cádiz) ------------------------------------------------------
        _f(ident="AP4-01", via="AP-4", desde="Sevilla", hasta="Cádiz", operador="Ministerio de Transportes (sin "
           "concesión)", ambito="estatal", provincia="Sevilla; Cádiz", km=92.623, tarifa=0.00, url=URL_DEPENDIENTES,
           rce=("AP-4", 12.9, 105.36),
           nota="Sin peaje desde el 1-ene-2020 (fin de la concesión de Aumar el 31-dic-2019, página 'Peajes "
           "dependientes de la AGE'). Catálogo: 'Autopista libre'. Fila con tarifa 0 para la validación de T2.5. "
           "{RCE}", vig_desde="2020-01-01"),
        # --- AP-15 (Audenasa, Gobierno de Navarra) -----------------------------------------------
        _f(ident="AP15-01", via="AP-15", desde="Enlace AP-68 (Tudela)", hasta="Pamplona (Noáin)", operador="Audenasa",
           ambito="autonomico", provincia="Navarra", km=82.978, tarifa=11.40, url=URL_BON_AP15,
           nota="Tramo Sur. Suma de los peajes base ligeros de las troncales de Marcilla (6,85) y Tiebas (4,55), IVA "
           "incluido (Acuerdo del Gobierno de Navarra, BON 258 de 30-dic-2025; estaciones según Audenasa). Tarifa "
           "base oficial 0,110243 EUR/km sin IVA (0,1334 con 21 % IVA), pero la longitud del tramo no está "
           "publicada. Peaje de acceso: Marcilla enlace 3,45 y Zuasti 0,90 (Zuasti no figura entre las 4 "
           "estaciones de la web de Audenasa). Que el recorrido completo pague las dos troncales es interpretación "
           "del curador. Vigencia del acuerdo: año 2026; concesión hasta 2029 (Parlamento, no descargado)."
           + _nota_osm("AP15-01") + " Contraste (no oficial, derivado): 11,40 / 0,1334 = 85,46 km (OSM -2,9 %). "
           "Entre este tramo y AP15-02 la ruta usa la variante oeste A-15 de Pamplona (libre, 12,53 km): el trozo de "
           "AP-15 entre Noáin y el empalme oeste no está en la tabla (hueco documentado en CORTES_DE_CADENA).",
           vig_hasta="2026-12-31"),
        _f(ident="AP15-02", via="AP-15", desde="Pamplona oeste (empalme con la variante A-15)", hasta="Irurtzun", operador="Audenasa",
           ambito="autonomico", provincia="Navarra", km=15.705, tarifa=2.65, url=URL_BON_AP15,
           nota="Tramo Norte: troncal de Sarasa, peaje base ligeros IVA incluido (BON 258/2025). Tarifa base 0,121368 "
           "EUR/km sin IVA (0,1469 con IVA); longitud no publicada." + _nota_osm("AP15-02")
           + " Contraste (no oficial, derivado): 2,65 / 0,1469 = 18,04 km; OSM da -12,9 %: el peaje de Sarasa "
           "puede cubrir también parte del anillo de Pamplona que la ruta no recorre (sin verificar). El tramo empieza "
           "en el empalme oeste con la variante A-15, no en Noáin: el trozo Noáin-empalme oeste no tiene fila.",
           vig_hasta="2026-12-31"),
        # --- AP-8 / VSM Bizkaia (Interbiak) ---------------------------------------------------------
        _f(ident="AP8-01", via="AP-8", desde="Accesos Oeste (Bilbao)", hasta="Ermua",
           operador="Interbiak (Diputación Foral de Bizkaia)", ambito="foral", provincia="Bizkaia",
           km=round(105.800 - 75.580, 3), tarifa=4.60, url=URL_DF_BIZKAIA,
           nota="Decreto Foral 147/2025 (BOB 30-dic-2025), art. 1, ligeros IVA incl. km = p.k. Urgoiti 105+800 "
           "(enlace más occidental del tramo de peaje) - p.k. Ermua 75+580, publicados por Interbiak ("
           + URL_INTERBIAK_AP8 + "); que 'Accesos Oeste' = Urgoiti/Erletxeta es interpretación del curador. OSM "
           "etiqueta el paso como 'A-8'. Recorrido Bilbao-Donostia (Bidegi) 13,81; la cadena AP8-01..03 suma 13,25.",
           vig_hasta="2026-12-31"),
        _f(ident="AP8-02", via="AP-8", desde="Ermua", hasta="Eibar", operador="Interbiak / Bidegi", ambito="foral",
           provincia="Bizkaia; Gipuzkoa", km=5.009, tarifa=1.22, url=URL_BIDEGI,
           nota="Tabla conjunta AP-1/AP-8 de Bidegi (vigente desde 01-01-2026). Ermua-Límite Gipuzkoa = 0,49 en el "
           "DF 147/2025; el resto lo cobra Bidegi. Los p.k. de Interbiak y Bidegi son sistemas distintos: no hay "
           "longitud oficial." + _nota_osm("AP8-02") + " Ermua se sitúa en su p.k. oficial 75+580 proyectado desde "
           "la salida 88 de OSM (Durango, p.k. 88+300): queda 1,77 km al este de la salida 77 de OSM, que daba 6,778 km "
           "(eur_km 0,1800 en lugar de 0,2436). Contraste del método: Urgoiti-Ermua 30,226 km frente a 30,22 de "
           "Interbiak (+0,02 %; anclas distintas, Urgoiti frente a Durango) y Eibar-Donostia 42,573 frente a 43,3 "
           "de Bidegi (-1,68 %)."),
        _f(ident="AP8-03", via="AP-8", desde="Eibar", hasta="Donostia-San Sebastián",
           operador="Bidegi (Diputación Foral de Gipuzkoa)", ambito="foral", provincia="Gipuzkoa",
           km=round(71.0 - 27.7, 3), tarifa=7.43, url=URL_BIDEGI,
           nota="Tabla Bidegi 2026: Eibar -> 'Zarautz nagusia / Donostia-San Sebastián, Astigarraga, Hernani'. km = "
           "p.k. Eibar (salida 71) 71 - p.k. Donostia/Lasarte (salida 27) 27,7, del plano de salidas de Bidegi ("
           + URL_BIDEGI_SAL_AP8 + "). OSM etiqueta los pasos como 'AP-1; AP-8' y 'DO'. P.k. verificados visualmente en "
           "el PDF de Bidegi por Jose Miguel Pulgarin el 2026-10-12."),
        _f(ident="AP8-VSM-01", via="AP-8", desde="Arrigorriaga (VSM, enlace AP-68)", hasta="Ortuella (VSM)",
           operador="Interbiak (Diputación Foral de Bizkaia)", ambito="foral", provincia="Bizkaia",
           km=round(126.450 - 113.0, 3), tarifa=1.85, url=URL_DF_BIZKAIA,
           nota="Variante Sur Metropolitana ('Supersur'), DF 147/2025 art. 2, ligeros. km = p.k. 126,450 (enlace "
           "Trapagaran, conexión con la A-8 Cantabria) - p.k. 113 (Arrigorriaga), de la web de Interbiak ("
           + URL_INTERBIAK_VSM + "); que 'Ortuella' de la tarifa = enlace Trapagaran es interpretación del curador.",
           vig_hasta="2026-12-31"),
        # --- AP-1 Eibar-Vitoria (Bidegi / Arabat) --------------------------------------------------
        _f(ident="AP1-01", via="AP-1", desde="Eibar (enlace AP-8)", hasta="Eskoriatza",
           operador="Bidegi (Diputación Foral de Gipuzkoa)", ambito="foral", provincia="Gipuzkoa",
           km=round(145.8 - 123.5, 3), tarifa=4.96, url=URL_BIDEGI,
           nota="Tabla Bidegi 2026, ligeros. km = p.k. 145,8 (enlace AP-8) - 123,5 (Eskoriatza), plano de salidas "
           "AP-1 de Bidegi (" + URL_BIDEGI_SAL_AP1 + "). Eibar-Vitoria directo 10,04; la cadena suma 10,18. P.k. "
           "verificados visualmente en el PDF de Bidegi por Jose Miguel Pulgarin el 2026-10-12."),
        _f(ident="AP1-02", via="AP-1", desde="Eskoriatza", hasta="Vitoria-Gasteiz (Etxabarri-Ibiña)",
           operador="Bidegi / Arabat", ambito="foral", provincia="Gipuzkoa; Araba/Álava", km=15.794, tarifa=5.22,
           url=URL_BIDEGI,
           nota="Tabla Bidegi 2026 (Luko y Etxabarri-Ibiña gestionados por Arabat según la leyenda). Tramo de "
           "Gipuzkoa hasta el p.k. ~113,9 (31,9 km según Bidegi); la longitud del tramo alavés no está publicada."
           + _nota_osm("AP1-02") + " Contraste del método: enlace AP-8-Eskoriatza 22,330 km frente a 22,3 de Bidegi "
           "(+0,13 %); tramo guipuzcoano de la AP-1 31,297 km frente a 31,9 (-1,89 %)."),
        # --- C-32 Castelldefels-El Vendrell (Aucat, Generalitat) ----------------------------------------
        _f(ident="C32-01", via="C-32", desde="Castelldefels Sud (salida 44)", hasta="Sitges (salida 31)",
           operador="Aucat (Abertis)", ambito="autonomico", provincia="Barcelona", km=13.474, tarifa=8.42, url=URL_C32,
           nota="Folleto del operador 'Peajes 2026' (enero 2026, IVA incl.): turismos = CATEGORÍA II (la I es "
           "motocicletas). Troncal de Vallcarca. Barcelona-El Vendrell O. 13,45 = 8,42 + 5,03. Fuente del operador, "
           "no del DOGC (no localizado). Longitud no publicada." + _nota_osm("C32-01")
           + " Sin contraste oficial (los números de salida 44 y 31 darían 13 km si siguieran el p.k.)."),
        _f(ident="C32-02", via="C-32", desde="Sitges (salida 31)", hasta="El Vendrell O./Coma-ruga (salida 2)",
           operador="Aucat (Abertis)", ambito="autonomico", provincia="Barcelona; Tarragona", km=29.054, tarifa=5.03,
           url=URL_C32,
           nota="Categoría II, troncal de Cubelles (acceso Cubelles 2,69 y acceso Calafell 0,79 no usados)."
           + _nota_osm("C32-02") + " Sin contraste oficial (las salidas 31 y 2 darían 29 km si siguieran el p.k.)."),
    ]
    return filas


# Derivados de las filas (el id se escribe una sola vez, en `definiciones`): la prueba recalcula estos km.
KM_RCE: dict[str, tuple[str, float, float]] = {
    d["ident"]: tuple(d["rce"][:3]) for d in definiciones() if d["rce"]}
PROVINCIAS_RCE: dict[str, tuple[str, ...]] = {
    d["ident"]: d["rce"][3] for d in definiciones() if d["rce"] and len(d["rce"]) > 3}


# ------------------------------------------------------------------------------------------------

def _num(v: float | None, dec: int) -> str:
    return TODO if v is None else f"{v:.{dec}f}"


def _eur_km(km: float | None, tarifa: float | None) -> str:
    """tarifa / km con 4 decimales (formato de Python). Tarifa 0 => 0.0000 aunque falte el km."""
    if tarifa == 0:
        return "0.0000"
    if km is None or tarifa is None:
        return TODO
    return f"{tarifa / km:.4f}"


def construir() -> list[dict[str, str]]:
    salida = []
    for d in definiciones():
        nota = d["nota"]
        if d["rce"]:
            if MARCA_RCE not in nota:
                raise ValueError(f"{d['ident']}: tiene 'rce' pero su nota no lleva {MARCA_RCE}")
            nota = nota.replace(MARCA_RCE, _nota_rce(d["rce"]))
        if MARCA_RCE in nota:
            raise ValueError(f"{d['ident']}: su nota lleva {MARCA_RCE} pero la fila no tiene 'rce'")
        salida.append({
            "id": d["ident"], "via": d["via"], "desde": d["desde"], "hasta": d["hasta"], "operador": d["operador"],
            "ambito": d["ambito"], "provincia": d["provincia"], "km": _num(d["km"], 3),
            "tarifa_ligeros_eur": _num(d["tarifa"], 2), "eur_km": _eur_km(d["km"], d["tarifa"]),
            "vigente_desde": d["vig_desde"], "vigente_hasta": d["vig_hasta"], "fuente_url": d["url"],
            "fecha_consulta": FECHA_CONSULTA, "nota": nota})
    return salida


def escribir(ruta: Path) -> list[dict[str, str]]:
    """Escribe el CSV y devuelve las filas escritas."""
    filas = construir()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = io.StringIO()
    escritor = csv.DictWriter(texto, fieldnames=COLUMNAS, lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(filas)
    ruta.write_text(texto.getvalue(), encoding="utf-8", newline="")
    return filas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    args = parser.parse_args(argv)
    filas = escribir(args.salida)
    sin_km = sum(f["km"] == TODO for f in filas)
    sin_tarifa = sum(f["tarifa_ligeros_eur"] == TODO for f in filas)
    print(f"{args.salida}: {len(filas)} filas; {sin_km} sin km y {sin_tarifa} sin tarifa (TODO(dato-faltante))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
