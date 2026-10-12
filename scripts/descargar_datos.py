"""ÚNICO script del proyecto que accede a internet (Spec §3, §7.2).

Paso 1 del pipeline del Bloque 1 (orden completo en scripts/comun_bloque1.py), del Bloque 2
(orden completo en scripts/comun_bloque2.py) y del Bloque 4 (orden completo en scripts/comun_bloque4.py).

Descarga los datos crudos de la Parte 2 a data/raw/ con una fecha en el nombre del archivo o de la carpeta: la de
descarga en el Bloque 1, la indicada con --fecha en el Bloque 2 y la de los DATOS pedidos al histórico en el Bloque 4
(la fecha y hora de consulta van dentro del crudo en los Bloques 2 y 4).
Los experimentos y el procesamiento leen solo de data/raw/.

Uso:
    python scripts/descargar_datos.py --bloque 1
    python scripts/descargar_datos.py --bloque 2 --fecha AAAA-MM-DD [--osrm-url URL] [--limite N]
    python scripts/descargar_datos.py --bloque 4 [--fecha AAAA-MM-DD]

Bloque 1 (coordenadas de las capitales de provincia), fuentes:
  1. IGN, API OGC Features, colección `nuc` (IGR Poblaciones: núcleos de población).
     Se consultan todos los códigos de capitalidad con el dígito "capital de provincia" (3.º) = 1.
  2. IGN, API OGC Features, colección `administrativeunit` (límites provinciales oficiales).
  3. INE, Relación de municipios y sus códigos (26codmun.xlsx, a 1-ene-2026).
  4. OpenStreetMap / Nominatim (respaldo y control de homónimos), 1 petición/s.

Nota: el Nomenclátor Geográfico de Municipios y Entidades de Población (NGMEP,
BD_MUNICIPIOS-ENTIDADES.ZIP) del Centro de Descargas del CNIG exige reCAPTCHA y no se
descarga de forma automática; ver data/fuentes.md.

Bloque 2 (rutas por carretera, Spec §7.2), fuente: OSRM LOCAL (T2.2, scripts/osrm/README.md), no internet.
  - 1 081 pares (i, j), i < j, de data/processed/cities.csv x {rapida, sin_peaje (exclude=toll)}, con
    steps=true y overview=simplified, y 20 pares de simetría (j -> i) elegidos con np.random.default_rng(0).
  - Un archivo por petición: data/raw/osrm_<fecha>/{rutas,simetria}/<origen>_<destino>_<alternativa>.json.gz
    (JSON compacto con gzip) con {url, fecha_consulta_utc, origen, destino, alternativa, respuesta}.
  - --fecha es OBLIGATORIA. Reanudable: si se corta (Ctrl+C incluido), relanzar el MISMO comando (misma --fecha)
    no repite los crudos válidos (validador único: comun_bloque2.problema_crudo).
  - Aborta si la respuesta trae otro data_version (protege la fecha de corte, Spec §7.1) o si el servidor no
    responde tras 3 intentos. Las respuestas con code != "Ok" se guardan y se listan al final, la corrida sigue
    y el código de salida es 1.
  - Los crudos de data/raw/osrm_<fecha>/{rutas,simetria}/ NO se versionan (Spec §7.2 Bloque 2, v1.5).

Bloque 4 (precio de la Gasolina 95 E5, Spec §7.2), fuente: servicio REST del Ministerio para la Transición Ecológica
(Geoportal de Gasolineras), endpoint HISTÓRICO por fecha.
  - --fecha opcional; por defecto la fecha de corte (comun_bloque4.FECHA_CORTE, Spec §7.1).
  - 4 consultas (comun_bloque4.urls_consultas): histórico completo, histórico filtrado por producto 1 (contraste) y
    los listados de productos y de CC. AA. Se guardan juntas en data/raw/carburantes_minetur_hist_<fecha>.json.gz
    (JSON + gzip) con {fecha_datos, fecha_consulta_utc, consultas: [{nombre, url, fecha_consulta_utc, respuesta}]}.
  - Si el histórico no devuelve OK o devuelve otro día, aborta SIN guardar nada: nunca se sustituye por el precio de
    hoy. No sobrescribe un crudo existente (bórrelo a mano si de verdad hay que repetir la descarga).
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import http.client
import itertools
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, NamedTuple

import comun_bloque2 as cb2
import comun_bloque4 as cb4
from comun_bloque1 import CPRO_EXCLUIDAS, RAW
from comun_bloque2 import CITIES_CSV

USER_AGENT = "Trabajo1-TSP-Espana/0.1 (proyecto academico; descarga unica de datos)"
IGN_API = "https://api-features.ign.es/collections"
INE_CODMUN_URL = "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Homónimos fuera de España (Spec §7.2): consulta Nominatim sin restringir país.
HOMONIMOS = ["Mérida", "Córdoba", "León", "Valencia", "Guadalajara"]

INTERRUMPIDO = "Interrumpido. Para continuar, relance el MISMO comando (se reanuda)."


class DescargaError(RuntimeError):
    """Fallo de red o respuesta HTTP de error al descargar. Bloque 1 (_get): sin reintentos. Bloque 2
    (_consultar_osrm): los fallos de red se reintentan 3 veces antes de ServidorNoDisponibleError."""


class ServidorNoDisponibleError(DescargaError):
    """El OSRM local no contesta (apagado, puerto equivocado, tiempo agotado) tras los reintentos."""


class DataVersionError(DescargaError):
    """OSRM responde con datos de otro extracto: las rutas no corresponderían a la fecha de corte."""


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


# ============================================================================================ Bloque 2 (OSRM)


def _consultar_osrm(url: str, timeout: int = 120, reintentos: int = 3, pausa_s: float = 2.0) -> dict:
    """GET al OSRM local; devuelve el JSON de la respuesta, también el de los errores HTTP de OSRM (400 con
    {"code": "NoRoute", ...}). Si el servidor no contesta tras `reintentos` intentos: ServidorNoDisponibleError."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ultimo: Exception | None = None
    for intento in range(1, reintentos + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (solo el OSRM local)
                cuerpo = resp.read()
        except urllib.error.HTTPError as exc:  # OSRM contestó: el cuerpo es su respuesta de error
            cuerpo = exc.read()
            try:
                return json.loads(cuerpo)
            except ValueError:
                return {"code": f"HTTP{exc.code}", "message": cuerpo[:300].decode("utf-8", "replace")}
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
            ultimo = exc
            if intento < reintentos:
                time.sleep(pausa_s)
            continue
        try:
            return json.loads(cuerpo)
        except ValueError:
            return {"code": "RespuestaNoJSON", "message": cuerpo[:300].decode("utf-8", "replace")}
    raise ServidorNoDisponibleError(
        f"el servidor OSRM no responde en {url} tras {reintentos} intento(s): {ultimo}. "
        "¿Está arrancado? Ejecute scripts/osrm/osrm.sh arrancar y relance el MISMO comando: la descarga se reanuda."
    )


@dataclass
class ResultadoDescarga:
    """Resumen de una ejecución del Bloque 2. n_pedidas = peticiones previstas (reutilizadas + descargadas)."""

    destino: Path
    n_pedidas: int = 0
    n_reutilizadas: int = 0
    n_descargadas: int = 0
    pares_ok: int = 0
    n_pares: int = 0
    fallos: list[dict] = field(default_factory=list)
    bytes_en_disco: int = 0
    segundos: float = 0.0


class Tarea(NamedTuple):
    """Una petición al OSRM: crudo `subdir/<origen>_<destino>_<alternativa>.json.gz`."""

    subdir: str
    origen: int
    destino: int
    alternativa: str


def _ahora_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _comprobar_data_version(resp: dict, url: str) -> None:
    """Ok sin data_version, u otra data_version (también en errores que la traigan) -> DataVersionError."""
    recibida = resp.get("data_version")
    if (resp.get("code") == "Ok" or recibida is not None) and recibida != cb2.DATA_VERSION_ESPERADA:
        raise DataVersionError(
            f"OSRM respondió data_version={recibida!r} y se esperaba {cb2.DATA_VERSION_ESPERADA!r} (extracto "
            f"{cb2.EXTRACTO_OSM}, fecha de corte del Spec §7.1) en {url}. El servidor se preparó con otro extracto: "
            "NO se guarda nada. Revise scripts/osrm/README.md (no usar spain-latest) y escale al puente."
        )


def _guardar_crudo(archivo: Path, crudo: dict) -> None:
    """JSON compacto + gzip (mtime=0: bytes reproducibles). Se escribe a .tmp y se renombra: un corte nunca deja
    un .json.gz a medias (un .tmp suelto no cuenta como descargado y se sobrescribe al reanudar)."""
    datos = json.dumps(crudo, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    temporal = archivo.with_name(archivo.name + ".tmp")
    temporal.write_bytes(gzip.compress(datos, compresslevel=9, mtime=0))
    os.replace(temporal, archivo)


def _tareas(n: int, limite: int | None) -> tuple[list[Tarea], list[tuple[int, int]]]:
    """Peticiones (rutas i -> j y simetría j -> i) y pares principales. `limite` = prueba rápida: los N primeros
    pares y los N primeros pares de simetría, estos en los dos sentidos para poder medir la simetría."""
    principales, simetria = cb2.pares(n), cb2.pares_simetria(n)
    if limite is not None:
        simetria = simetria[:limite]
        principales = sorted(set(principales[:limite]) | set(simetria))
    tareas = [Tarea(cb2.SUBDIR_RUTAS, i, j, a) for i, j in principales for a in cb2.ALTERNATIVAS]
    tareas += [Tarea(cb2.SUBDIR_SIMETRIA, j, i, a) for i, j in simetria for a in cb2.ALTERNATIVAS]
    return tareas, principales


def _descargar_una(tarea: Tarea, ciudades: list[cb2.Ciudad], destino: Path, osrm_url: str,
                   consultar: Callable[[str], dict]) -> dict | None:
    """Pide y guarda el crudo de `tarea`, salvo que ya haya uno válido (cb2.problema_crudo). Devuelve la respuesta
    descargada, o None si se reutilizó el crudo existente."""
    url = cb2.url_ruta(osrm_url, ciudades[tarea.origen], ciudades[tarea.destino], tarea.alternativa)
    archivo = destino / tarea.subdir / cb2.nombre_crudo(tarea.origen, tarea.destino, tarea.alternativa)
    _, motivo = cb2.cargar_crudo(archivo, url)
    if motivo is None:
        return None
    fecha = _ahora_utc()
    resp = consultar(url)
    _comprobar_data_version(resp, url)
    _guardar_crudo(archivo, {"url": url, "fecha_consulta_utc": fecha, "origen": tarea.origen,
                             "destino": tarea.destino, "alternativa": tarea.alternativa, "respuesta": resp})
    return resp


def descargar_rutas_osrm(cities_csv: Path, destino: Path, osrm_url: str, limite: int | None = None,
                         consultar: Callable[[str], dict] | None = None) -> ResultadoDescarga:
    """Bloque 2: rutas rapida/sin_peaje de los pares i < j y simetría j -> i en `destino` (data/raw/osrm_<fecha>).

    Reanudable: reutiliza los crudos válidos. Las respuestas con code != "Ok" se guardan y se listan en `fallos`
    sin detener la corrida (al reanudar se repiten). `consultar` permite inyectar un doble del servidor.
    """
    consultar = consultar or _consultar_osrm
    inicio = time.monotonic()
    ciudades = cb2.leer_ciudades(cities_csv)
    tareas, principales = _tareas(len(ciudades), limite)
    for sub in (cb2.SUBDIR_RUTAS, cb2.SUBDIR_SIMETRIA):
        (destino / sub).mkdir(parents=True, exist_ok=True)

    res = ResultadoDescarga(destino=destino, n_pedidas=len(tareas), n_pares=len(principales))
    for k, tarea in enumerate(tareas, start=1):
        resp = _descargar_una(tarea, ciudades, destino, osrm_url, consultar)
        if resp is None:
            res.n_reutilizadas += 1
        else:
            res.n_descargadas += 1
            if resp.get("code") != "Ok":
                res.fallos.append({**tarea._asdict(), "code": resp.get("code"), "message": resp.get("message")})
        if k % 100 == 0 or k == len(tareas):
            print(f"  [{k:5d}/{len(tareas)}] descargadas={res.n_descargadas} "
                  f"reutilizadas={res.n_reutilizadas} fallos={len(res.fallos)}", flush=True)

    fallidos = {(f["origen"], f["destino"]) for f in res.fallos if f["subdir"] == cb2.SUBDIR_RUTAS}
    res.pares_ok = sum(1 for p in principales if p not in fallidos)
    res.bytes_en_disco = sum(p.stat().st_size for sub in (cb2.SUBDIR_RUTAS, cb2.SUBDIR_SIMETRIA)
                             for p in (destino / sub).glob("*.json.gz"))
    res.segundos = time.monotonic() - inicio
    return res


def bloque2(fecha: str, osrm_url: str, limite: int | None) -> int:
    destino = RAW / f"osrm_{fecha}"
    print(f"Bloque 2 — rutas OSRM -> {destino}  (servidor {osrm_url}; limite={limite})", flush=True)
    try:
        res = descargar_rutas_osrm(CITIES_CSV, destino, osrm_url, limite=limite)
    except KeyboardInterrupt:
        print(INTERRUMPIDO, file=sys.stderr)
        return 130
    print(f"Peticiones: {res.n_pedidas} (descargadas {res.n_descargadas}, reutilizadas {res.n_reutilizadas}, "
          f"fallos {len(res.fallos)})")
    print(f"Pares con las 2 alternativas Ok: {res.pares_ok} / {res.n_pares}")
    print(f"Tamaño en disco (rutas/ + simetria/): {res.bytes_en_disco / 1e6:.1f} MB "
          f"({res.bytes_en_disco} B); tiempo: {res.segundos:.1f} s")
    for f in res.fallos:
        nombre = cb2.nombre_crudo(f["origen"], f["destino"], f["alternativa"]).removesuffix(".json.gz")
        print(f"FALLO {f['subdir']}/{nombre}: code={f['code']!r} message={f['message']!r}")
    if res.fallos:
        print("Hay fallos: relanzar el MISMO comando solo repite las peticiones fallidas. Si persisten, escalar.")
    return 0 if not res.fallos else 1


# ============================================================================================ Bloque 4 (combustible)


# El servidor del Ministerio (IIS) solo negocia TLS 1.2 con AES256-GCM-SHA384 (intercambio de claves RSA, sin secreto
# perfecto hacia adelante), que la lista de cifrados por defecto de Python excluye: el servidor corta la conexión
# (WinError 10054) en vez de responder con una alerta TLS. Comprobado el 2026-10-11 (curl/Schannel sí conecta).
# El prefijo de CIFRADOS_MINETUR (hasta "!AESCCM") es copia literal de la cadena de cifrados por defecto de CPython,
# la que aplica ssl.create_default_context() (comprobado en Python 3.12.10: misma lista y mismo orden); se le añade
# SOLO AES256-GCM-SHA384.
# La verificación del certificado y del nombre se mantiene (tests/test_combustible.py lo comprueba).
CIFRADOS_MINETUR = ("@SECLEVEL=2:ECDH+AESGCM:ECDH+CHACHA20:ECDH+AES:DHE+AES:!aNULL:!eNULL:!aDSS:!SHA1:!AESCCM:"
                    "AES256-GCM-SHA384")


def contexto_tls_minetur() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.set_ciphers(CIFRADOS_MINETUR)
    return ctx


def _get_json(url: str, timeout: int = 600) -> object:
    """GET de una URL del Ministerio -> JSON (la respuesta trae BOM UTF-8). Un HTTP 400 del histórico (fecha mal
    formada o futura) es DescargaError."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=contexto_tls_minetur()) as resp:
            cuerpo = resp.read()
    except urllib.error.HTTPError as exc:
        detalle = exc.read()[:300].decode("utf-8-sig", "replace")
        raise DescargaError(f"HTTP {exc.code} ({exc.reason}) al descargar {url}: {detalle}") from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
        raise DescargaError(f"Sin conexión o URL no accesible ({exc}) al descargar {url}") from exc
    try:
        return json.loads(cuerpo.decode("utf-8-sig"))
    except ValueError as exc:
        raise DescargaError(f"respuesta no JSON en {url}: {exc}") from exc


def descargar_carburantes(fecha: str, destino_dir: Path, consultar: Callable[[str], object] | None = None) -> Path:
    """Bloque 4: las 4 consultas de comun_bloque4.urls_consultas(fecha) en un único crudo .json.gz.

    Comprueba ANTES de escribir que las dos respuestas de estaciones son OK y del día pedido (no se sustituye por otro
    día) y que los listados son coherentes (comun_bloque4.validar_listados). `consultar` permite inyectar un doble del
    servidor en las pruebas.
    """
    consultar = consultar or _get_json
    destino = destino_dir / cb4.nombre_crudo(fecha)
    if destino.exists():
        raise DescargaError(f"{destino} ya existe; no se sobrescribe un crudo. Bórrelo a mano si hay que repetir.")
    consultas = []
    for nombre, url in cb4.urls_consultas(fecha).items():
        fecha_consulta = _ahora_utc()
        respuesta = consultar(url)
        if nombre.startswith("historico"):
            try:
                cb4.validar_estaciones(respuesta, fecha, nombre)
            except cb4.DatoFaltanteError as exc:
                raise DescargaError(f"{exc}. URL: {url}. No se guarda nada.") from exc
        consultas.append({"nombre": nombre, "url": url, "fecha_consulta_utc": fecha_consulta, "respuesta": respuesta})
    respuestas = {c["nombre"]: c["respuesta"] for c in consultas}
    try:
        cb4.validar_listados(respuestas["productos"], respuestas["ccaa"])
    except cb4.DatoFaltanteError as exc:
        raise DescargaError(f"{exc}. No se guarda nada.") from exc
    destino_dir.mkdir(parents=True, exist_ok=True)
    _guardar_crudo(destino, {"fecha_datos": fecha, "fecha_consulta_utc": consultas[0]["fecha_consulta_utc"],
                             "consultas": consultas})
    return destino


def fecha_bloque4(args: argparse.Namespace) -> str:
    return args.fecha or cb4.FECHA_CORTE


def bloque4(fecha: str) -> int:
    destino = descargar_carburantes(fecha, RAW)
    print(f"Bloque 4 — {cb4.PRODUCTO}, histórico del {fecha} -> {destino} ({destino.stat().st_size} B)")
    print(f"Siguiente paso (sin red): python scripts/construir_combustible.py --fecha {fecha}")
    return 0


def _entero_positivo(texto: str) -> int:
    valor = int(texto)
    if valor < 1:
        raise argparse.ArgumentTypeError("debe ser un entero >= 1")
    return valor


def _fecha_iso(texto: str) -> str:
    try:
        return dt.date.fromisoformat(texto).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"fecha AAAA-MM-DD no válida: {texto!r}") from exc


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bloque", type=int, choices=[1, 2, 4], required=True)
    parser.add_argument("--fecha", type=_fecha_iso, default=None,
                        help="Bloque 2 (OBLIGATORIA): fecha AAAA-MM-DD de la carpeta data/raw/osrm_<fecha>/. Para "
                             "reanudar, también otro día, repetir la MISMA fecha. Bloque 4 (opcional): día pedido al "
                             f"histórico de precios (por defecto la fecha de corte, {cb4.FECHA_CORTE})")
    parser.add_argument("--osrm-url", default=None,
                        help=f"Bloque 2: URL base del OSRM local (por defecto {cb2.OSRM_URL_LOCAL})")
    parser.add_argument("--limite", type=_entero_positivo, default=None,
                        help="Bloque 2, prueba rápida: solo los N primeros pares y los N primeros de simetría "
                             "(en ambos sentidos)")
    return parser


def _avisar_opciones_ignoradas(args: argparse.Namespace, con_fecha: bool = True) -> None:
    opciones = [("--osrm-url", args.osrm_url), ("--limite", args.limite)]
    if con_fecha:
        opciones.append(("--fecha", args.fecha))
    ignoradas = [op for op, valor in opciones if valor is not None]
    if ignoradas:
        print(f"AVISO: {', '.join(ignoradas)}: no se usa(n) con --bloque {args.bloque}; se ignora(n).", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)
    if args.bloque == 2 and args.fecha is None:
        parser.error("--fecha AAAA-MM-DD es obligatoria con --bloque 2 (para reanudar hay que repetir la MISMA "
                     "fecha; sin ella se descargaría todo de nuevo en otra carpeta)")
    try:
        if args.bloque == 1:
            _avisar_opciones_ignoradas(args)
            bloque1(dt.date.today().isoformat())
            return 0
        if args.bloque == 4:
            _avisar_opciones_ignoradas(args, con_fecha=False)
            return bloque4(fecha_bloque4(args))
        return bloque2(args.fecha, args.osrm_url or cb2.OSRM_URL_LOCAL, args.limite)
    except DescargaError as exc:
        raise SystemExit(f"ERROR de descarga: {exc}") from exc


if __name__ == "__main__":
    sys.exit(main())
