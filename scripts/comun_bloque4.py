"""Utilidades comunes del Bloque 4 (T2.6, Spec §7.2): precio de la Gasolina 95 E5. Sin red.

Orden del pipeline del Bloque 4 (único lugar donde se documenta):

    1. python scripts/descargar_datos.py --bloque 4 [--fecha AAAA-MM-DD]
         ÚNICO paso con internet. Por defecto pide la fecha de corte (Spec §7.1, 2026-10-01) al servicio REST del
         Ministerio y guarda las 4 respuestas (urls_consultas) en data/raw/carburantes_minetur_hist_<fecha>.json.gz.
         Si el servidor no devuelve OK para ESA fecha, no guarda nada (nunca sustituye por el precio del día).
    2. python scripts/construir_combustible.py [--fecha AAAA-MM-DD]
         Sin red. data/processed/combustible.json y combustible_resumen.json (contrato Spec §5.3 v1.6).
    3. pytest tests/test_combustible.py

Servicio REST (verificado el 2026-10-11 en URL_BASE + "/help"):
  - EstacionesTerrestresHist/{FECHA}: todas las estaciones y todos los productos de ese día. La fecha va como
    dd-mm-aaaa: con AAAA-MM-DD contesta HTTP 400 "Fecha ha de tener el formato dd-mm-aaaa", y con una fecha futura
    "no puede ser posterior a <hoy>". El precio está en el campo "Precio Gasolina 95 E5", texto con coma decimal
    ("1,749"); "" si la estación no lo vende o no lo comunicó.
  - EstacionesTerrestresHist/FiltroProducto/{FECHA}/1: solo estaciones con precio del producto 1, en "PrecioProducto".
    Se usa como CONTRASTE: debe dar exactamente las mismas estaciones y precios.
  - Listados/ProductosPetroliferos/: confirma que IDProducto 1 = "Gasolina 95 E5".
  - Listados/ComunidadesAutonomas/: confirma los IDCCAA de los territorios no peninsulares.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import re
import zlib
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from comun_bloque1 import PROCESSED, RAIZ, RAW, DatoFaltanteError

__all__ = [
    "AMBITO", "CAMPO_PRECIO", "CCAA_NO_PENINSULARES", "DECIMALES", "FECHA_CORTE", "ID_PRODUCTO", "NOMBRES_CONSULTAS",
    "PROCESSED", "PRODUCTO", "RAIZ", "RAW", "URL_BASE",
    "DatoFaltanteError", "estadisticos", "fecha_api", "fecha_respuesta", "leer_crudo", "nombre_crudo", "precio",
    "urls_consultas", "validar_estaciones", "validar_listados",
]

FECHA_CORTE = "2026-10-01"  # Spec §7.1 [DECIDIDO]
URL_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"
PRODUCTO = "Gasolina 95 E5"  # Spec §7.2 Bloque 4 [DECIDIDO]
ID_PRODUCTO = "1"  # Listados/ProductosPetroliferos/ (se comprueba en cada crudo)
CAMPO_PRECIO = "Precio Gasolina 95 E5"  # campo de EstacionesTerrestresHist/{FECHA}
CAMPO_PRECIO_FILTRO = "PrecioProducto"  # campo de EstacionesTerrestresHist/FiltroProducto/{FECHA}/{ID}
# IDCCAA del Ministerio (Listados/ComunidadesAutonomas/, se comprueba en cada crudo) fuera de la España peninsular.
CCAA_NO_PENINSULARES = {"04": "Baleares", "05": "Canarias", "18": "Ceuta", "19": "Melilla"}
# Spec §7.2 Bloque 4 v1.6 [DECIDIDO] (decisión humana del 2026-10-11): combustible.json usa la media PENINSULAR, sin
# CCAA_NO_PENINSULARES; la nacional queda como sensibilidad en combustible_resumen.json.
AMBITO = "peninsular"
NOMBRES_CONSULTAS = ("historico", "historico_producto", "productos", "ccaa")
DECIMALES = Decimal("0.0001")  # media y mediana en €/l con 4 decimales (los precios traen 3), mitad al par

_PRECIO = re.compile(r"\d+,\d+")
_ERRORES_LECTURA = (OSError, EOFError, zlib.error, ValueError)


def fecha_api(fecha_iso: str) -> str:
    """AAAA-MM-DD -> dd-mm-aaaa, el único formato que acepta el histórico."""
    return dt.date.fromisoformat(fecha_iso).strftime("%d-%m-%Y")


def fecha_respuesta(fecha_iso: str) -> str:
    """Prefijo del campo "Fecha" de la respuesta para ese día ("01/10/2026 0:00:00" -> "01/10/2026")."""
    return dt.date.fromisoformat(fecha_iso).strftime("%d/%m/%Y")


def urls_consultas(fecha_iso: str) -> dict[str, str]:
    """Las 4 consultas del Bloque 4, en el orden de NOMBRES_CONSULTAS. Único lugar donde se construyen las URL."""
    f = fecha_api(fecha_iso)
    urls = {
        "historico": f"{URL_BASE}/EstacionesTerrestresHist/{f}",
        "historico_producto": f"{URL_BASE}/EstacionesTerrestresHist/FiltroProducto/{f}/{ID_PRODUCTO}",
        "productos": f"{URL_BASE}/Listados/ProductosPetroliferos/",
        "ccaa": f"{URL_BASE}/Listados/ComunidadesAutonomas/",
    }
    assert tuple(urls) == NOMBRES_CONSULTAS
    return urls


def nombre_crudo(fecha_iso: str) -> str:
    """La fecha del nombre es la de los DATOS (la pedida al histórico); la de consulta va dentro del crudo."""
    return f"carburantes_minetur_hist_{fecha_iso}.json.gz"


def leer_crudo(ruta: Path) -> dict:
    try:
        return json.loads(gzip.decompress(ruta.read_bytes()))
    except FileNotFoundError as exc:
        raise DatoFaltanteError(f"no existe {ruta} (TODO(dato-faltante)); ejecute primero "
                                "scripts/descargar_datos.py --bloque 4") from exc
    except _ERRORES_LECTURA as exc:
        raise DatoFaltanteError(f"crudo ilegible {ruta}: {exc}; vuelva a descargarlo "
                                "(scripts/descargar_datos.py --bloque 4)") from exc


def precio(texto: str) -> Decimal:
    """Precio del Ministerio ("1,749", coma decimal) -> Decimal exacto. Otro formato detiene el proceso."""
    if not isinstance(texto, str) or not _PRECIO.fullmatch(texto):
        raise DatoFaltanteError(f"precio con formato inesperado: {texto!r} (se esperaba p. ej. '1,749')")
    return Decimal(texto.replace(",", "."))


def _redondear(valor: Decimal) -> float:
    return float(valor.quantize(DECIMALES, rounding=ROUND_HALF_EVEN))


def estadisticos(precios: list[Decimal]) -> dict:
    """n, media y mediana (aritmética exacta con Decimal, redondeo final a 4 decimales, mitad al par), min y max."""
    if not precios:
        raise DatoFaltanteError("no hay ningún precio con el que calcular (TODO(dato-faltante))")
    orden = sorted(precios)
    n = len(orden)
    mitad = n // 2
    mediana = orden[mitad] if n % 2 else (orden[mitad - 1] + orden[mitad]) / 2
    return {"n": n, "media": _redondear(sum(orden) / n), "mediana": _redondear(mediana),
            "min": float(orden[0]), "max": float(orden[-1])}


def validar_estaciones(resp: dict, fecha_iso: str, nombre: str) -> list[dict]:
    """Respuesta de EstacionesTerrestresHist: OK, del día pedido y con estaciones. Devuelve ListaEESSPrecio."""
    if not isinstance(resp, dict) or resp.get("ResultadoConsulta") != "OK":
        resultado = resp.get("ResultadoConsulta") if isinstance(resp, dict) else resp
        raise DatoFaltanteError(f"'{nombre}': ResultadoConsulta = {resultado!r} (se esperaba 'OK')")
    fecha = resp.get("Fecha")
    if not isinstance(fecha, str) or fecha.split(" ")[0] != fecha_respuesta(fecha_iso):
        raise DatoFaltanteError(f"'{nombre}': Fecha = {fecha!r}, pero se pidió {fecha_respuesta(fecha_iso)}; "
                                "no se sustituye por otro día")
    lista = resp.get("ListaEESSPrecio")
    if not isinstance(lista, list) or not lista:
        raise DatoFaltanteError(f"'{nombre}': ListaEESSPrecio vacía (TODO(dato-faltante))")
    return lista


def _lista_de_objetos(valor: object, listado: str) -> list[dict]:
    if not isinstance(valor, list) or not all(isinstance(e, dict) for e in valor):
        raise DatoFaltanteError(f"Listados/{listado}: se esperaba una lista de objetos y llegó "
                                f"{type(valor).__name__} (TODO(dato-faltante))")
    return valor


def validar_listados(productos: object, ccaa: object) -> None:
    """Listados del Ministerio: IDProducto ID_PRODUCTO = PRODUCTO y los IDCCAA de CCAA_NO_PENINSULARES con su nombre.
    La usan la descarga (antes de guardar el crudo) y el procesamiento. Cualquier fallo: DatoFaltanteError."""
    productos = _lista_de_objetos(productos, "ProductosPetroliferos")
    ccaa = _lista_de_objetos(ccaa, "ComunidadesAutonomas")
    nombre = next((p.get("NombreProducto") for p in productos if p.get("IDProducto") == ID_PRODUCTO), None)
    if nombre != PRODUCTO:
        raise DatoFaltanteError(f"IDProducto {ID_PRODUCTO} es {nombre!r} en Listados/ProductosPetroliferos; "
                                f"se esperaba {PRODUCTO!r}")
    nombres = {c.get("IDCCAA"): c.get("CCAA") for c in ccaa}
    for codigo, esperado in CCAA_NO_PENINSULARES.items():
        if nombres.get(codigo) != esperado:
            raise DatoFaltanteError(f"IDCCAA {codigo} es {nombres.get(codigo)!r} en Listados/ComunidadesAutonomas; "
                                    f"se esperaba {esperado!r}")
