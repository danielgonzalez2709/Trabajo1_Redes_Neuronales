"""Utilidades comunes del Bloque 2 (T2.3, Spec §7.2): pares, URL de OSRM, crudos y su validación. Sin red.

Orden del pipeline del Bloque 2 (único lugar donde se documenta; comandos completos en scripts/osrm/README.md):

    0. scripts/osrm/osrm.sh arrancar
         Servidor OSRM local (T2.2) en http://127.0.0.1:5001 con el extracto spain-261001.
    1. python scripts/descargar_datos.py --bloque 2 --fecha AAAA-MM-DD [--limite N]
         ÚNICO paso con red (solo el OSRM local). 1 081 pares i < j x {rapida, sin_peaje} y 20 pares de
         simetría (j -> i) a data/raw/osrm_<fecha>/{rutas,simetria}/, un .json.gz por petición. Reanudable.
         Esos crudos NO se versionan (Spec §7.2 Bloque 2, v1.5): se quedan en la máquina de quien ejecuta.
    2. python scripts/construir_rutas.py --fecha AAAA-MM-DD
         Sin red. data/processed/rutas.csv, rutas_resumen.json y rutas_pasos_peaje.csv (contrato Spec §5.3).
    3. pytest tests/test_rutas.py

Duplicación intencional: scripts/osrm/prueba_aceptacion.py (T2.2) repite la URL y el recuento de la clase toll
porque solo usa la biblioteca estándar y se ejecuta con `python3 -I`, sin importar nada del proyecto.
"""

from __future__ import annotations

import csv
import gzip
import itertools
import json
import urllib.parse
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from comun_bloque1 import PROCESSED, RAIZ, RAW, DatoFaltanteError

__all__ = [
    "ALTERNATIVAS", "CITIES_CSV", "DATA_VERSION_ESPERADA", "EXTRACTO_OSM", "FUENTE", "N_SIMETRIA", "OSRM_URL_LOCAL",
    "PROCESSED", "RAIZ", "RAW", "SUBDIR_RUTAS", "SUBDIR_SIMETRIA", "VERSION_OSRM",
    "Ciudad", "DatoFaltanteError", "cargar_crudo", "leer_ciudades", "leer_crudo", "nombre_crudo", "pares",
    "pares_simetria", "problema_crudo", "ruta_principal", "url_ruta",
]

CITIES_CSV = PROCESSED / "cities.csv"
OSRM_URL_LOCAL = "http://127.0.0.1:5001"  # servidor de T2.2 (scripts/osrm/osrm.sh, OSRM_PUERTO por defecto)

# Fecha de los datos del extracto OSM con el que se preparó el OSRM local (T2.2): osmosis_replication_timestamp de
# spain-261001.osm.pbf, que OSRM devuelve en cada respuesta como "data_version" (--data_version osmosis).
# Evidencia: data/raw/osrm_2026-10-10/geofabrik_spain-261001_cabecera_pbf.json y data/fuentes.md.
DATA_VERSION_ESPERADA = "2026-10-01T20:22:06Z"
# Versión del binario y extracto (OSRM no los devuelve en la respuesta; evidencia de T2.2:
# data/raw/osrm_2026-10-10/osrm_version_perfil.txt y scripts/osrm/README.md).
VERSION_OSRM = "v26.10.0"
EXTRACTO_OSM = "spain-261001"
FUENTE = f"OSRM {VERSION_OSRM} (perfil car.lua, MLD) sobre OSM Geofabrik {EXTRACTO_OSM}"

ALTERNATIVAS = ("rapida", "sin_peaje")
PARAMETROS_URL = "alternatives=false&steps=true&geometries=polyline&overview=simplified"
EXCLUIR_PEAJE = "&exclude=toll"

# Simetría (Spec §7.2): 20 pares aleatorios con la regla de semillas del Spec §4.1, rng = default_rng(base_seed +
# run_id), base_seed = 0 y una única "corrida" (run_id = 0).
N_SIMETRIA = 20
BASE_SEED = 0
RUN_ID_SIMETRIA = 0

SUBDIR_RUTAS = "rutas"
SUBDIR_SIMETRIA = "simetria"

# Errores posibles al leer un .json.gz roto o truncado (FileNotFoundError y BadGzipFile son OSError).
_ERRORES_LECTURA = (OSError, EOFError, zlib.error, ValueError)


@dataclass(frozen=True)
class Ciudad:
    id: int
    capital: str
    lon: float
    lat: float

    @property
    def coord_url(self) -> str:
        """'lon,lat' con 6 decimales (los de cities.csv): el orden que exige OSRM."""
        return f"{self.lon:.6f},{self.lat:.6f}"


def leer_ciudades(cities_csv: Path) -> list[Ciudad]:
    """Ciudades de cities.csv indexadas por posición; exige ids 0..n-1 consecutivos (el índice es el id)."""
    with cities_csv.open(encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    ciudades = [Ciudad(int(f["id"]), f["capital"], float(f["lon"]), float(f["lat"])) for f in filas]
    if [c.id for c in ciudades] != list(range(len(ciudades))):
        raise DatoFaltanteError(f"{cities_csv}: la columna id debe ser 0..{len(ciudades) - 1} en orden")
    return ciudades


def pares(n: int) -> list[tuple[int, int]]:
    """Todos los pares (i, j) con i < j, en orden lexicográfico (1 081 para n = 47)."""
    return list(itertools.combinations(range(n), 2))


def pares_simetria(n: int, k: int = N_SIMETRIA) -> list[tuple[int, int]]:
    """k pares (i < j) sin reemplazo con np.random.default_rng(BASE_SEED + RUN_ID_SIMETRIA), ordenados."""
    todos = pares(n)
    rng = np.random.default_rng(BASE_SEED + RUN_ID_SIMETRIA)
    elegidos = rng.choice(len(todos), size=min(k, len(todos)), replace=False)
    return [todos[int(e)] for e in sorted(elegidos)]


def url_ruta(base: str, origen: Ciudad, destino: Ciudad, alternativa: str) -> str:
    """URL del servicio route de OSRM (lon,lat;lon,lat). `exclude=toll` solo en la alternativa sin_peaje."""
    if alternativa not in ALTERNATIVAS:
        raise ValueError(f"alternativa desconocida: {alternativa!r}; válidas: {ALTERNATIVAS}")
    url = f"{base.rstrip('/')}/route/v1/driving/{origen.coord_url};{destino.coord_url}?{PARAMETROS_URL}"
    return url + EXCLUIR_PEAJE if alternativa == "sin_peaje" else url


def nombre_crudo(origen: int, destino: int, alternativa: str) -> str:
    """Nombre del crudo de una petición origen -> destino (ids de cities.csv con 2 dígitos)."""
    return f"{origen:02d}_{destino:02d}_{alternativa}.json.gz"


def leer_crudo(ruta: Path) -> dict:
    """Crudo {url, fecha_consulta_utc, origen, destino, alternativa, respuesta}; error si está corrupto."""
    return json.loads(gzip.decompress(ruta.read_bytes()).decode("utf-8"))


def ruta_principal(respuesta: dict) -> dict:
    return respuesta["routes"][0]


def _consulta(url: str) -> str:
    """Ruta + consulta de la URL, sin esquema ni servidor."""
    partes = urllib.parse.urlsplit(url)
    return f"{partes.path}?{partes.query}"


def _tiene_pasos(respuesta: dict) -> bool:
    rutas = respuesta.get("routes")
    return bool(rutas) and any(leg.get("steps") for leg in rutas[0].get("legs", []))


def problema_crudo(crudo: dict, url_esperada: str) -> str | None:
    """Motivo por el que un crudo no es utilizable, o None. Único validador (descarga y construir_rutas).

    Compara la ruta y la consulta de la URL, NO el servidor: cambiar de puerto (--osrm-url) no invalida lo
    descargado; cambiar las coordenadas de cities.csv o los parámetros, sí.
    """
    if not (isinstance(crudo, dict) and isinstance(crudo.get("respuesta"), dict)
            and isinstance(crudo.get("url"), str) and isinstance(crudo.get("fecha_consulta_utc"), str)):
        return "estructura inesperada (faltan url, fecha_consulta_utc o respuesta)"
    resp = crudo["respuesta"]
    if resp.get("code") != "Ok":
        return f"code={resp.get('code')!r} message={resp.get('message')!r}"
    if resp.get("data_version") != DATA_VERSION_ESPERADA:
        return f"data_version={resp.get('data_version')!r} (se esperaba {DATA_VERSION_ESPERADA!r})"
    if _consulta(crudo["url"]) != _consulta(url_esperada):
        return (f"URL {_consulta(crudo['url'])} distinta de la esperada {_consulta(url_esperada)}: "
                "¿cambiaron las coordenadas de cities.csv o los parámetros después de descargar?")
    if not _tiene_pasos(resp):
        return "la respuesta no tiene pasos (se pidió steps=true; T2.5 los necesita)"
    return None


def cargar_crudo(archivo: Path, url_esperada: str) -> tuple[dict | None, str | None]:
    """(crudo, None) si `archivo` existe y es válido según problema_crudo; si no, (None, motivo)."""
    try:
        crudo = leer_crudo(archivo)
        motivo = problema_crudo(crudo, url_esperada)
    except _ERRORES_LECTURA as exc:
        return None, f"crudo ilegible ({type(exc).__name__}: {exc})"
    except (AttributeError, KeyError, TypeError, IndexError) as exc:  # JSON válido con forma inesperada
        return None, f"estructura inesperada ({type(exc).__name__}: {exc})"
    return (None, motivo) if motivo else (crudo, None)
