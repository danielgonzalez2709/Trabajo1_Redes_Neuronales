"""Paso 2 del pipeline del Bloque 4 (orden completo en scripts/comun_bloque4.py). Sin red.

Lee el crudo data/raw/carburantes_minetur_hist_<fecha>.json.gz (lo escribe `descargar_datos.py --bloque 4`) y
escribe en data/processed/:

  - combustible.json (contrato Spec §5.3 v1.6, claves exactas): producto, ambito, precio_medio_eur_l,
    precio_mediano_eur_l, n_estaciones, fecha, fuente_url, archivo_raw. Modelo [DECIDIDO] del Spec §7.2 Bloque 4
    v1.6 (decisión humana del 2026-10-11): precio MEDIO PENINSULAR, ambito = "peninsular": estaciones con precio de
    Gasolina 95 E5 fuera de Baleares, Canarias, Ceuta y Melilla (comun_bloque4.CCAA_NO_PENINSULARES), porque el
    recorrido solo pasa por capitales peninsulares. Media aritmética simple por estación (sin ponderar por ventas).
  - combustible_resumen.json (contrato Spec §5.3 v1.6, claves exactas): desglose (estaciones sin precio, nacional
    como sensibilidad, peninsular, cada territorio no peninsular, contraste con el filtro por producto).

Estaciones sin precio (campo vacío o solo espacios): se excluyen y se cuentan (n_sin_precio).
Cualquier incoherencia del crudo (fecha distinta, resultado no OK, IDEESS repetido, precio con otro formato, producto
1 que no sea Gasolina 95 E5, filtro por producto que no coincide) detiene el proceso sin escribir (DatoFaltanteError).

Uso:
    python scripts/construir_combustible.py [--fecha AAAA-MM-DD] [--salida DIR]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from decimal import Decimal
from pathlib import Path

import comun_bloque4 as cb4
from comun_bloque4 import PROCESSED, RAIZ, RAW, DatoFaltanteError

CRITERIO_SIN_PRECIO = (f"estaciones con el campo '{cb4.CAMPO_PRECIO}' vacío (o solo espacios): no venden el producto "
                       "o no comunicaron precio ese día; se excluyen")


def _legible(ruta: Path) -> str:
    try:
        return ruta.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return ruta.as_posix()


def _consultas(crudo: dict) -> dict[str, dict]:
    """Consultas del crudo por nombre; comprueba que estén las 4 y que su URL sea la de la fecha del crudo."""
    fecha = crudo.get("fecha_datos")
    if not isinstance(fecha, str):
        raise DatoFaltanteError("el crudo no tiene 'fecha_datos'")
    esperadas = cb4.urls_consultas(fecha)
    por_nombre = {c.get("nombre"): c for c in crudo.get("consultas", [])}
    for nombre, url in esperadas.items():
        if nombre not in por_nombre:
            raise DatoFaltanteError(f"falta la consulta '{nombre}' en el crudo (TODO(dato-faltante))")
        if por_nombre[nombre].get("url") != url:
            raise DatoFaltanteError(f"la consulta '{nombre}' tiene URL {por_nombre[nombre].get('url')!r}; "
                                    f"se esperaba {url!r}")
    return por_nombre


def _precios_historico(lista: list[dict]) -> tuple[dict[str, tuple[str, Decimal]], int]:
    """{IDEESS: (IDCCAA, precio)} de las estaciones con precio, y nº de estaciones sin precio."""
    precios: dict[str, tuple[str, Decimal]] = {}
    vistos: set[str] = set()
    sin_precio = 0
    for e in lista:
        ideess = e.get("IDEESS")
        if ideess in vistos:
            raise DatoFaltanteError(f"IDEESS repetido en el histórico: {ideess!r}")
        vistos.add(ideess)
        if cb4.CAMPO_PRECIO not in e or "IDCCAA" not in e:
            raise DatoFaltanteError(f"estación {ideess!r} sin el campo '{cb4.CAMPO_PRECIO}' o 'IDCCAA'")
        texto = e[cb4.CAMPO_PRECIO]
        if isinstance(texto, str) and not texto.strip():
            sin_precio += 1
            continue
        precios[ideess] = (e["IDCCAA"], cb4.precio(texto))
    return precios, sin_precio


def _contraste(precios: dict[str, tuple[str, Decimal]], lista_filtro: list[dict], url: str) -> dict:
    filtro = {e.get("IDEESS"): cb4.precio(e.get(cb4.CAMPO_PRECIO_FILTRO)) for e in lista_filtro}
    if len(filtro) != len(lista_filtro):
        raise DatoFaltanteError("IDEESS repetido en el filtro por producto")
    solo_hist = set(precios) - set(filtro)
    solo_filtro = set(filtro) - set(precios)
    distintos = [i for i in set(precios) & set(filtro) if precios[i][1] != filtro[i]]
    if solo_hist or solo_filtro or distintos:
        raise DatoFaltanteError(
            f"el histórico completo y el filtro por producto {cb4.ID_PRODUCTO} no coinciden: {len(solo_hist)} "
            f"estaciones solo en el histórico, {len(solo_filtro)} solo en el filtro, {len(distintos)} con otro "
            "precio. Escalar (dos respuestas oficiales del mismo día se contradicen)")
    return {"url": url, "n_estaciones": len(filtro), "coincide": True}


def calcular(crudo: dict, archivo_raw: str) -> tuple[dict, dict]:
    """(combustible.json, combustible_resumen.json) a partir del crudo. `archivo_raw` = ruta legible del crudo."""
    consultas = _consultas(crudo)
    fecha = crudo["fecha_datos"]
    hist = consultas["historico"]
    lista = cb4.validar_estaciones(hist["respuesta"], fecha, "historico")
    lista_filtro = cb4.validar_estaciones(consultas["historico_producto"]["respuesta"], fecha, "historico_producto")
    cb4.validar_listados(consultas["productos"]["respuesta"], consultas["ccaa"]["respuesta"])

    precios, sin_precio = _precios_historico(lista)
    contraste = _contraste(precios, lista_filtro, consultas["historico_producto"]["url"])
    nacional = cb4.estadisticos([p for _, p in precios.values()])
    peninsular = cb4.estadisticos([p for c, p in precios.values() if c not in cb4.CCAA_NO_PENINSULARES])
    no_peninsular = {nombre: cb4.estadisticos([p for c, p in precios.values() if c == codigo])
                     for codigo, nombre in cb4.CCAA_NO_PENINSULARES.items()
                     if any(c == codigo for c, _ in precios.values())}

    combustible = {
        "producto": cb4.PRODUCTO,
        "ambito": cb4.AMBITO,
        "precio_medio_eur_l": peninsular["media"],
        "precio_mediano_eur_l": peninsular["mediana"],
        "n_estaciones": peninsular["n"],
        "fecha": fecha,
        "fuente_url": hist["url"],
        "archivo_raw": archivo_raw,
    }
    resumen = {
        "producto": cb4.PRODUCTO,
        "id_producto": cb4.ID_PRODUCTO,
        "campo_precio": cb4.CAMPO_PRECIO,
        "ambito": cb4.AMBITO,
        "fecha": fecha,
        "fecha_respuesta": hist["respuesta"]["Fecha"],
        "fecha_consulta_utc": hist.get("fecha_consulta_utc"),
        "fuente_url": hist["url"],
        "archivo_raw": archivo_raw,
        "redondeo": "media y mediana con aritmética decimal exacta y redondeo final a 4 decimales (mitad al par)",
        "n_estaciones_respuesta": len(lista),
        "n_sin_precio": sin_precio,
        "criterio_sin_precio": CRITERIO_SIN_PRECIO,
        "nacional": nacional,
        "peninsular": peninsular,
        "no_peninsular": no_peninsular,
        "ccaa_no_peninsulares": cb4.CCAA_NO_PENINSULARES,
        "contraste_filtro_producto": contraste,
    }
    return combustible, resumen


def _escribir_json(ruta: Path, datos: dict) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def construir(ruta_raw: Path, salida_dir: Path) -> dict:
    """Valida el crudo y escribe combustible.json y combustible_resumen.json en `salida_dir`. Devuelve el primero."""
    combustible, resumen = calcular(cb4.leer_crudo(ruta_raw), _legible(ruta_raw))
    salida_dir.mkdir(parents=True, exist_ok=True)
    _escribir_json(salida_dir / "combustible.json", combustible)
    _escribir_json(salida_dir / "combustible_resumen.json", resumen)
    return combustible


def _fecha_iso(texto: str) -> str:
    try:
        return dt.date.fromisoformat(texto).isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"fecha AAAA-MM-DD no válida: {texto!r}") from exc


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fecha", type=_fecha_iso, default=cb4.FECHA_CORTE,
                        help=f"fecha de los datos del crudo (por defecto la de corte, {cb4.FECHA_CORTE})")
    parser.add_argument("--salida", type=Path, default=PROCESSED,
                        help="carpeta de salida (por defecto data/processed)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        combustible = construir(RAW / cb4.nombre_crudo(args.fecha), args.salida)
    except DatoFaltanteError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    resumen = json.loads((args.salida / "combustible_resumen.json").read_text(encoding="utf-8"))
    print(f"{combustible['producto']} ({combustible['fecha']}), {combustible['ambito']} (sin "
          f"{', '.join(cb4.CCAA_NO_PENINSULARES.values())}): media {combustible['precio_medio_eur_l']} €/l, "
          f"mediana {combustible['precio_mediano_eur_l']} €/l, {combustible['n_estaciones']} estaciones")
    n = resumen["nacional"]
    print(f"Nacional (sensibilidad): media {n['media']} €/l, mediana {n['mediana']} €/l, {n['n']} estaciones "
          f"({resumen['n_sin_precio']} sin precio excluidas de {resumen['n_estaciones_respuesta']})")
    print(f"-> {_legible(args.salida / 'combustible.json')}, {_legible(args.salida / 'combustible_resumen.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
