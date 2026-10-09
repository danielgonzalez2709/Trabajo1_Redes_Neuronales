"""ÚNICO script del proyecto que accede a internet (Spec §3, §7.2).

Paso 1 del pipeline del Bloque 1 (orden completo en scripts/comun_bloque1.py).

Descarga los datos crudos de la Parte 2 a data/raw/ con la fecha de descarga en el nombre.
Los experimentos y el procesamiento leen solo de data/raw/.

Uso:
    python scripts/descargar_datos.py --bloque 1

Bloque 1 (coordenadas de las capitales de provincia), fuentes:
  1. IGN, API OGC Features, colección `nuc` (IGR Poblaciones: núcleos de población).
     Se consultan todos los códigos de capitalidad con el dígito "capital de provincia" (3.º) = 1.
  2. IGN, API OGC Features, colección `administrativeunit` (límites provinciales oficiales).
  3. INE, Relación de municipios y sus códigos (26codmun.xlsx, a 1-ene-2026).
  4. OpenStreetMap / Nominatim (respaldo y control de homónimos), 1 petición/s.

Nota: el Nomenclátor Geográfico de Municipios y Entidades de Población (NGMEP,
BD_MUNICIPIOS-ENTIDADES.ZIP) del Centro de Descargas del CNIG exige reCAPTCHA y no se
descarga de forma automática; ver data/fuentes.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import itertools
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from comun_bloque1 import CPRO_EXCLUIDAS, RAW

USER_AGENT = "Trabajo1-TSP-Espana/0.1 (proyecto academico; descarga unica de datos)"
IGN_API = "https://api-features.ign.es/collections"
INE_CODMUN_URL = "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Homónimos fuera de España (Spec §7.2): consulta Nominatim sin restringir país.
HOMONIMOS = ["Mérida", "Córdoba", "León", "Valencia", "Guadalajara"]


class DescargaError(RuntimeError):
    """Fallo de red o respuesta HTTP de error al descargar un crudo (sin reintentos)."""


def _url(base: str, params: dict) -> str:
    """Único lugar donde se construye la URL de una consulta (se guarda tal cual en el crudo)."""
    return f"{base}?{urllib.parse.urlencode(params)}"


def _get(url: str, timeout: int = 600) -> bytes:
    """Descarga `url`, ya construida con _url (o una URL fija)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise DescargaError(f"HTTP {exc.code} ({exc.reason}) al descargar {url}") from exc
    except urllib.error.URLError as exc:
        raise DescargaError(f"Sin conexión o URL no accesible ({exc.reason}) al descargar {url}") from exc


def codigos_capital_de_provincia() -> list[str]:
    """Todos los códigos ValorTipoCapital (6 dígitos) con el 3.er dígito = 1.

    Fuente de la codificación: IGN, Especificaciones IGR-PO, Anexo I, 3.8 ValorTipoCapital
    ("Se permiten combinaciones de código": 100000 nación, 010000 CC. AA., 001000 provincia,
    000100 municipio, 000010 EATIM, 000001 comarca).
    """
    codigos = []
    for bits in itertools.product("01", repeat=5):
        b = list(bits)
        codigos.append("".join(b[:2] + ["1"] + b[2:]))
    return codigos


def descargar_ign_capitales(fecha: str) -> Path:
    consultas = []
    for codigo in codigos_capital_de_provincia():
        params = {"f": "json", "limit": 1000, "skipGeometry": "true", "capital": codigo}
        url = _url(f"{IGN_API}/nuc/items", params)
        respuesta = json.loads(_get(url))
        consultas.append({"url": url, "fecha_consulta": fecha, "respuesta": respuesta})
    destino = RAW / f"ign_nuc_capitales_provincia_{fecha}.json"
    destino.write_text(json.dumps(consultas, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def descargar_ign_provincias(fecha: str) -> Path:
    params = {"f": "json", "limit": 100, "nationallevelname": "Provincia"}
    contenido = _get(_url(f"{IGN_API}/administrativeunit/items", params))
    destino = RAW / f"ign_provincias_{fecha}.geojson.gz"
    with gzip.open(destino, "wb", compresslevel=9) as fh:
        fh.write(contenido)
    return destino


def descargar_ine_codmun(fecha: str) -> Path:
    destino = RAW / f"ine_26codmun_{fecha}.xlsx"
    destino.write_bytes(_get(INE_CODMUN_URL))
    return destino


def descargar_nominatim(fecha: str, capitales_ign: Path) -> Path:
    consultas_ign = json.loads(capitales_ign.read_text(encoding="utf-8"))
    nombres = sorted(
        {
            feat["properties"]["nombre"]
            for c in consultas_ign
            for feat in c["respuesta"]["features"]
            if feat["properties"]["cpro"] not in CPRO_EXCLUIDAS
        }
    )
    resultados = []
    consultas = [("es", n.split("/")[0], n) for n in nombres] + [("libre", h, h) for h in HOMONIMOS]
    for modo, texto, nombre_ign in consultas:
        params = {"q": texto, "format": "jsonv2", "addressdetails": 1, "limit": 3, "accept-language": "es"}
        if modo == "es":
            params["countrycodes"] = "es"
        url = _url(NOMINATIM_URL, params)
        respuesta = json.loads(_get(url, timeout=60))
        resultados.append(
            {"modo": modo, "consulta": texto, "nombre_ign": nombre_ign, "url": url,
             "fecha_consulta": fecha, "respuesta": respuesta}
        )
        time.sleep(1.1)  # política de uso de Nominatim: máx. 1 petición/s
    destino = RAW / f"nominatim_capitales_{fecha}.json"
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def bloque1(fecha: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    capitales = descargar_ign_capitales(fecha)
    print(f"IGN capitales -> {capitales}")
    print(f"IGN provincias -> {descargar_ign_provincias(fecha)}")
    print(f"INE codmun -> {descargar_ine_codmun(fecha)}")
    print(f"Nominatim -> {descargar_nominatim(fecha, capitales)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bloque", type=int, choices=[1], required=True)
    args = parser.parse_args()
    fecha = dt.date.today().isoformat()
    try:
        if args.bloque == 1:
            bloque1(fecha)
    except DescargaError as exc:
        raise SystemExit(f"ERROR de descarga: {exc}") from exc


if __name__ == "__main__":
    main()
