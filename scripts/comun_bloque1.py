"""Utilidades comunes del Bloque 1 (T2.1): rutas, constantes, lectura del NGMEP y geometría. Sin red.

Orden del pipeline del Bloque 1 (único lugar donde se documenta):

    1. python scripts/descargar_datos.py --bloque 1
         ÚNICO paso con internet. Descarga IGR Poblaciones, límites provinciales, INE 26codmun y Nominatim
         a data/raw/ con la fecha en el nombre. El NGMEP (data/raw/BD_Municipios-Entidades/) es descarga
         manual porque el portal del CNIG exige reCAPTCHA.
    2. python scripts/construir_cities.py --fecha AAAA-MM-DD
         Construye data/processed/cities.csv (coordenadas del NGMEP), cities_verificacion.csv y
         cities_mapa_control.png.
    3. python scripts/validar_cities_ngmep.py
         Valida cities.csv contra el NGMEP crudo y mide la distancia a IGR Poblaciones (crudo):
         data/processed/cities_contraste_ngmep.csv.
    4. python scripts/caracterizar_bloque1.py --fecha AAAA-MM-DD
         Estadísticas descriptivas: data/processed/caracterizacion_bloque1.json.
    5. pytest tests/
"""

from __future__ import annotations

import csv
import math
import unicodedata
from pathlib import Path

# ----------------------------------------------------------------------------- constantes

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
PROCESSED = RAIZ / "data" / "processed"
NGMEP = RAW / "BD_Municipios-Entidades"

FECHA_DESCARGA_NGMEP = "2026-10-07"  # descarga manual registrada en data/fuentes.md
VERSION_NGMEP = "202603"  # del nombre del .mdb publicado (202603_NGMEP.mdb); el .mdb no se versiona
CPRO_EXCLUIDAS = {7, 35, 38, 51, 52}  # Illes Balears, Las Palmas, S. C. de Tenerife, Ceuta, Melilla
UMBRAL_IGR_KM = 2.5  # distancia máxima IGR -> NGMEP (justificada en tests/test_cities_ngmep.py)
R_TIERRA_KM = 6371.0088  # radio medio terrestre (IUGG), km


class DatoFaltanteError(ValueError):
    """Falta un dato obligatorio en los crudos (TODO(dato-faltante)): el pipeline se detiene."""


# ----------------------------------------------------------------------------- archivos


def ruta_unica(directorio: Path, patron: str) -> Path:
    """Único archivo de `directorio` que cumple `patron`; error si hay cero o varios."""
    encontrados = sorted(directorio.glob(patron))
    if len(encontrados) != 1:
        raise FileNotFoundError(f"Se esperaba exactamente un archivo {patron!r} en {directorio}; "
                                f"hay {len(encontrados)}: {[p.name for p in encontrados]}")
    return encontrados[0]


def num(texto: str) -> float:
    """Número con coma decimal del NGMEP ('-2,512507724') -> float."""
    return float(texto.replace(",", "."))


def leer_ngmep(nombre: str) -> list[dict[str, str]]:
    """Lee un CSV del NGMEP: separador ';', codificación cp1252 (contiene el byte 0x92)."""
    with (NGMEP / nombre).open(encoding="cp1252", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def version_ngmep() -> str:
    """Versión del NGMEP usada (ver VERSION_NGMEP y data/fuentes.md)."""
    return VERSION_NGMEP


def entidades_capital_ngmep() -> dict[str, dict[str, str]]:
    """Entidad NGMEP de la capital de cada provincia, indexada por COD_PROV ('01'..'52').

    Criterio de la Memoria NGMEP 2026: PROVINCIAS.CAPITAL -> MUNICIPIOS (mismo COD_PROV y
    NOMBRE_ACTUAL == CAPITAL) -> COD_INE_CAPITAL -> ENTIDADES.CODIGOINE ("Capital de municipio").
    """
    provincias = leer_ngmep("PROVINCIAS.csv")
    municipios = leer_ngmep("MUNICIPIOS.csv")
    entidades = {e["CODIGOINE"]: e for e in leer_ngmep("ENTIDADES.csv")}
    resultado = {}
    for p in provincias:
        candidatos = [m for m in municipios
                      if m["COD_PROV"] == p["COD_PROV"] and m["NOMBRE_ACTUAL"] == p["CAPITAL"]]
        if len(candidatos) != 1:
            raise ValueError(f"Provincia {p['COD_PROV']}: {len(candidatos)} municipios llamados {p['CAPITAL']!r}")
        resultado[p["COD_PROV"]] = entidades[candidatos[0]["COD_INE_CAPITAL"]]
    return resultado


def coordenadas_osm(fila: dict[str, str]) -> tuple[float, float]:
    """(lat, lon) OSM de una fila de cities_verificacion.csv; error explícito si falta (OSM es control obligatorio)."""
    if not fila.get("osm_lat") or not fila.get("osm_lon"):
        raise DatoFaltanteError(f"{fila.get('capital')}: falta el punto OSM/Nominatim de control "
                                "(TODO(dato-faltante)); vuelva a ejecutar construir_cities.py")
    return float(fila["osm_lat"]), float(fila["osm_lon"])


# ----------------------------------------------------------------------------- nombres


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def variantes(nombre: str) -> set[str]:
    """Variantes normalizadas de un nombre: partes de un nombre bilingüe 'A/B' y el artículo
    pospuesto de la convención del INE ('Coruña, A' -> 'a coruña')."""
    partes = {normalizar(nombre)} | {normalizar(p) for p in nombre.split("/")}
    for p in list(partes):
        if ", " in p:
            base, articulo = p.rsplit(", ", 1)
            partes.add(f"{articulo} {base}")
    return partes


# ----------------------------------------------------------------------------- geometría


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_TIERRA_KM * math.asin(math.sqrt(a))


def punto_en_multipoligono(lon: float, lat: float, geometria: dict) -> bool:
    """Regla par-impar (ray casting) sobre todos los anillos; resuelve agujeros y multipolígonos."""
    if geometria["type"] == "Polygon":
        poligonos = [geometria["coordinates"]]
    elif geometria["type"] == "MultiPolygon":
        poligonos = geometria["coordinates"]
    else:
        raise ValueError(f"Geometría no soportada: {geometria['type']}")
    dentro = False
    for poligono in poligonos:
        for anillo in poligono:
            j = len(anillo) - 1
            for i in range(len(anillo)):
                xi, yi = anillo[i][0], anillo[i][1]
                xj, yj = anillo[j][0], anillo[j][1]
                if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                    dentro = not dentro
                j = i
    return dentro
