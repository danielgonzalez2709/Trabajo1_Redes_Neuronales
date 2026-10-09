"""Bloque 1 (T2.1): construye data/processed/cities.csv a partir de data/raw/ (sin internet).

Paso 2 del pipeline (orden completo en scripts/comun_bloque1.py).

Fuente principal de las coordenadas (decisión del equipo 2026-10-08, Spec §7.2): NGMEP del IGN,
entidad TIPO = "Capital de municipio" de ENTIDADES.csv (criterio en comun_bloque1.entidades_capital_ngmep).
IGR Poblaciones, el INE y OSM/Nominatim son contraste y control.

Entradas:
    data/raw/BD_Municipios-Entidades/                   IGN, NGMEP (descarga manual)
    data/raw/ign_nuc_capitales_provincia_<fecha>.json   IGN, IGR Poblaciones (colección nuc), contraste
    data/raw/ign_provincias_<fecha>.geojson.gz          IGN, unidades administrativas (provincias)
    data/raw/ine_26codmun_<fecha>.xlsx                  INE, relación de municipios a 1-ene-2026
    data/raw/nominatim_capitales_<fecha>.json           OSM/Nominatim, control obligatorio y homónimos

Salidas:
    data/processed/cities.csv                 contrato Spec §5.3
    data/processed/cities_verificacion.csv    evidencia de cada comprobación por capital
    data/processed/cities_mapa_control.png    mapa de control (puntos sobre límites IGN)

Uso:
    python scripts/construir_cities.py --fecha 2026-10-07 [--fecha-ngmep 2026-10-07]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from pathlib import Path

from comun_bloque1 import (CPRO_EXCLUIDAS, FECHA_DESCARGA_NGMEP, PROCESSED, RAW, UMBRAL_IGR_KM, DatoFaltanteError,
                           entidades_capital_ngmep, haversine_km, leer_ngmep, normalizar, num,
                           punto_en_multipoligono, variantes, version_ngmep)

# ----------------------------------------------------------------------------- constantes

# Lista de verificación manual tal como aparece en el Spec §7.2.
LISTA_SPEC = [
    "Vitoria-Gasteiz", "A Coruña", "Ourense", "Girona", "Lleida", "Castelló de la Plana",
    "Donostia/San Sebastián", "Pamplona/Iruña", "Mérida", "Córdoba", "León", "Valencia", "Guadalajara",
]
TIPOS_CIUDAD_OSM = {"city", "town", "municipality", "village"}
SIN_NOMBRE_INE = "TODO(dato-faltante)"

COLUMNAS = ["id", "capital", "provincia", "lat", "lon", "fuente", "fecha_consulta", "verificado_manual", "nota"]
COLUMNAS_VERIF = [
    "id", "capital", "codigoine", "origencoor_ngmep", "codine_ign", "cmun_ine", "nombre_ine", "provincia_ign",
    "provincia_ine", "tipo_ign", "capital_ign", "fecha_registro_ign", "lat", "lon", "lat_igr", "lon_igr",
    "dist_igr_km", "en_provincia_ign", "osm_lat", "osm_lon", "osm_tipo", "osm_en_misma_provincia", "dist_osm_km",
    "en_lista_verificacion", "verificado_manual",
]


# ----------------------------------------------------------------------------- lectura de crudos


def leer_capitales_igr(ruta: Path) -> list[dict]:
    consultas = json.loads(ruta.read_text(encoding="utf-8"))
    vistas: dict[int, dict] = {}
    for consulta in consultas:
        for feat in consulta["respuesta"]["features"]:
            p = feat["properties"]
            if p["capital"][2] != "1":
                raise ValueError(f"Registro sin capitalidad provincial: {p}")
            if p["cpro"] in vistas and vistas[p["cpro"]]["codine"] != p["codine"]:
                raise ValueError(f"Dos capitales para la provincia {p['cpro']}: {vistas[p['cpro']]} / {p}")
            vistas[p["cpro"]] = p
    return [vistas[k] for k in sorted(vistas)]


def leer_provincias_ign(ruta: Path) -> dict[int, dict]:
    with gzip.open(ruta, "rt", encoding="utf-8") as fh:
        datos = json.load(fh)
    provincias = {}
    for feat in datos["features"]:
        codigo = feat["properties"]["nationalcode"]  # 34 + CCAA(2) + CPRO(2) + 00000
        cpro = int(codigo[4:6])
        if cpro == 0 or not codigo.endswith("00000"):
            continue
        provincias[cpro] = {"nombre": feat["properties"]["nameunit"], "geometry": feat["geometry"]}
    return provincias


def leer_ine(ruta: Path) -> tuple[dict[str, str], dict[int, str]]:
    import openpyxl  # solo para leer el xlsx oficial del INE

    libro = openpyxl.load_workbook(ruta, read_only=True)
    municipios: dict[str, str] = {}
    provincias: dict[int, str] = {}
    for hoja in libro.worksheets:
        filas = list(hoja.iter_rows(values_only=True))
        provincias[int(hoja.title)] = str(filas[1][0]).strip()
        for fila in filas[3:]:
            if fila[0] and fila[1]:
                municipios[f"{fila[0]}{fila[1]}"] = str(fila[3]).strip()
    return municipios, provincias


def leer_nominatim(ruta: Path) -> tuple[dict[str, dict | None], dict[str, dict]]:
    """Devuelve (resultado de nivel ciudad por nombre IGR, primer resultado sin filtro de país por homónimo)."""
    consultas = json.loads(ruta.read_text(encoding="utf-8"))
    respaldo: dict[str, dict | None] = {}
    homonimos: dict[str, dict] = {}
    for c in consultas:
        if c["modo"] == "es":
            ciudad = [r for r in c["respuesta"] if r.get("addresstype") in TIPOS_CIUDAD_OSM]
            respaldo[c["nombre_ign"]] = ciudad[0] if ciudad else None
        else:
            homonimos[c["consulta"]] = c["respuesta"][0] if c["respuesta"] else {}
    return respaldo, homonimos


def exigir_resultado_osm(respaldo_osm: dict[str, dict | None], nombre: str) -> dict:
    """Resultado OSM de nivel ciudad para `nombre`; su falta es un error explícito (control obligatorio)."""
    resultado = respaldo_osm.get(nombre)
    if not resultado:
        raise DatoFaltanteError(f"{nombre}: Nominatim no devolvió un resultado de nivel ciudad "
                                "(TODO(dato-faltante)); revise data/raw/nominatim_capitales_*.json")
    return resultado


# ----------------------------------------------------------------------------- construcción


def capitales_en_lista_spec(peninsulares: list[dict], municipios_ine: dict[str, str]) -> tuple[set[str], list[str]]:
    """Códigos INE de las capitales de la lista del Spec y nombres de la lista que no son capital provincial."""
    def nombres_de(capital_igr: dict) -> set[str]:
        return variantes(capital_igr["nombre"]) | variantes(municipios_ine.get(capital_igr["codine"][:5], ""))

    en_lista, sin_capital = set(), []
    for nombre in LISTA_SPEC:
        coinciden = [c for c in peninsulares if normalizar(nombre) in nombres_de(c)]
        if len(coinciden) == 1:
            en_lista.add(coinciden[0]["codine"])
        else:
            sin_capital.append(nombre)
    return en_lista, sin_capital


def verificar_capital(capital_igr: dict, entidad_ngmep: dict, provincia: dict, nombre_prov_ngmep: str,
                      osm: dict, nombre_ine: str) -> dict:
    """Comprobaciones de una capital. Las coordenadas salen del NGMEP; IGR y OSM son contraste/control."""
    cod_prov = f"{capital_igr['cpro']:02d}"
    # Conservación de ids, orden y nombres: el NGMEP debe describir la misma entidad que el IGR.
    if (entidad_ngmep["CODIGOINE"] != capital_igr["codine"] or entidad_ngmep["NOMBRE"] != capital_igr["nombre"]
            or nombre_prov_ngmep != provincia["nombre"]):
        raise ValueError(f"NGMEP e IGR no coinciden en {cod_prov}: {entidad_ngmep['CODIGOINE']} "
                         f"{entidad_ngmep['NOMBRE']!r} / {capital_igr['codine']} {capital_igr['nombre']!r} / "
                         f"{nombre_prov_ngmep!r} vs {provincia['nombre']!r}")
    # Coordenadas NGMEP redondeadas a 6 decimales (~0,1 m): las mismas que se escriben y se comprueban.
    lat = round(num(entidad_ngmep["LATITUD_ETRS89_REGCAN95"]), 6)
    lon = round(num(entidad_ngmep["LONGITUD_ETRS89_REGCAN95"]), 6)
    lat_igr, lon_igr = float(capital_igr["latitud"]), float(capital_igr["longitud"])
    lat_osm, lon_osm = float(osm["lat"]), float(osm["lon"])
    return {
        "lat": lat, "lon": lon, "lat_igr": lat_igr, "lon_igr": lon_igr,
        "dist_igr": haversine_km(lat_igr, lon_igr, lat, lon),
        "en_prov": punto_en_multipoligono(lon, lat, provincia["geometry"]),
        "lat_osm": lat_osm, "lon_osm": lon_osm,
        "osm_en_prov": punto_en_multipoligono(lon_osm, lat_osm, provincia["geometry"]),
        "dist_osm": haversine_km(lat, lon, lat_osm, lon_osm),
        "ine_ok": nombre_ine != SIN_NOMBRE_INE and capital_igr["codine"][:2] == cod_prov,
    }


def armar_nota(capital_igr: dict, entidad_ngmep: dict, version: str, chequeo: dict, osm: dict, nombre_ine: str,
               provincia_ine: str, en_lista: bool, verificado: bool) -> str:
    nota = [
        f"CODIGOINE {entidad_ngmep['CODIGOINE']} (NGMEP {version}, {entidad_ngmep['TIPO']})",
        f"ORIGENCOOR NGMEP '{entidad_ngmep['ORIGENCOOR']}'",
        f"distancia a IGR Poblaciones (mismo código; {capital_igr['tipo']}, capitalidad {capital_igr['capital']}): "
        f"{chequeo['dist_igr']:.3f} km",
        f"municipio INE {capital_igr['codine'][:5]} '{nombre_ine}' (relación INE 1-ene-2026)",
        f"punto dentro de la provincia IGN: {'sí' if chequeo['en_prov'] else 'NO'}",
        f"OSM/Nominatim a {chequeo['dist_osm']:.1f} km ({osm.get('addresstype')}; "
        f"{'misma provincia' if chequeo['osm_en_prov'] else 'OTRA provincia'})",
    ]
    if capital_igr["tipo"] != "NUCL":
        nota.append(f"IGR Poblaciones la publica como {capital_igr['tipo']} (no NUCL)")
    if en_lista:
        nota.append(
            "VERIFICACIÓN (lista Spec §7.2): CODIGOINE NGMEP = código IGR; municipio oficial INE 2026 y provincia "
            f"INE {capital_igr['cpro']:02d} '{provincia_ine}'; punto NGMEP y punto OSM dentro del polígono "
            f"provincial IGN; distancia a IGR <= {f'{UMBRAL_IGR_KM:.1f}'.replace('.', ',')} km; "
            + ("superada" if verificado else "NO superada -> TODO(revisión humana)")
        )
    return "; ".join(nota)


def avisos_capital(capital_igr: dict, nombre_ine: str) -> list[str]:
    avisos = []
    if capital_igr["tipo"] != "NUCL":
        avisos.append(f"{capital_igr['nombre']}: tipo {capital_igr['tipo']} en IGR Poblaciones (no NUCL)")
    if not variantes(nombre_ine) & variantes(capital_igr["nombre"]):
        avisos.append(f"{capital_igr['nombre']}: nombre IGN distinto del nombre INE '{nombre_ine}'")
    return avisos


def avisos_homonimos(homonimos_osm: dict[str, dict], sin_capital: list[str]) -> list[str]:
    avisos = [f"Lista Spec: '{n}' no corresponde a ninguna capital de provincia peninsular del IGN"
              for n in sin_capital]
    for consulta, resultado in homonimos_osm.items():
        pais = (resultado.get("address") or {}).get("country_code", "?")
        if pais != "es":
            avisos.append(f"Homónimo: Nominatim sin filtro de país resuelve '{consulta}' a "
                          f"'{resultado.get('display_name', '')}' ({pais})")
    return avisos


def construir(fecha: str, fecha_ngmep: str) -> tuple[list[dict], list[dict], list[str], dict[int, dict]]:
    """Orquestador: lee los crudos, verifica cada capital y arma las filas de salida."""
    version = version_ngmep()
    fuente = f"IGN - NGMEP {version} (ENTIDADES.csv, TIPO 'Capital de municipio')"
    ngmep = entidades_capital_ngmep()
    nombre_prov_ngmep = {p["COD_PROV"]: p["PROVINCIA"] for p in leer_ngmep("PROVINCIAS.csv")}
    capitales = leer_capitales_igr(RAW / f"ign_nuc_capitales_provincia_{fecha}.json")
    provincias = leer_provincias_ign(RAW / f"ign_provincias_{fecha}.geojson.gz")
    municipios_ine, provincias_ine = leer_ine(RAW / f"ine_26codmun_{fecha}.xlsx")
    respaldo_osm, homonimos_osm = leer_nominatim(RAW / f"nominatim_capitales_{fecha}.json")

    peninsulares = [c for c in capitales if c["cpro"] not in CPRO_EXCLUIDAS]
    en_lista, sin_capital = capitales_en_lista_spec(peninsulares, municipios_ine)

    filas, verificacion, avisos = [], [], []
    for idx, capital_igr in enumerate(peninsulares):
        cod_prov = f"{capital_igr['cpro']:02d}"
        entidad_ngmep = ngmep[cod_prov]
        provincia = provincias[capital_igr["cpro"]]
        nombre_ine = municipios_ine.get(capital_igr["codine"][:5], SIN_NOMBRE_INE)
        provincia_ine = provincias_ine[capital_igr["cpro"]]
        osm = exigir_resultado_osm(respaldo_osm, capital_igr["nombre"])
        chequeo = verificar_capital(capital_igr, entidad_ngmep, provincia, nombre_prov_ngmep[cod_prov], osm,
                                    nombre_ine)
        es_de_lista = capital_igr["codine"] in en_lista
        verificado = (es_de_lista and chequeo["en_prov"] and chequeo["osm_en_prov"] and chequeo["ine_ok"]
                      and chequeo["dist_igr"] <= UMBRAL_IGR_KM)
        filas.append({
            "id": idx, "capital": capital_igr["nombre"], "provincia": provincia["nombre"],
            "lat": f"{chequeo['lat']:.6f}", "lon": f"{chequeo['lon']:.6f}", "fuente": fuente,
            "fecha_consulta": fecha_ngmep, "verificado_manual": "true" if verificado else "false",
            "nota": armar_nota(capital_igr, entidad_ngmep, version, chequeo, osm, nombre_ine, provincia_ine,
                               es_de_lista, verificado),
        })
        verificacion.append({
            "id": idx, "capital": capital_igr["nombre"], "codigoine": entidad_ngmep["CODIGOINE"],
            "origencoor_ngmep": entidad_ngmep["ORIGENCOOR"], "codine_ign": capital_igr["codine"],
            "cmun_ine": capital_igr["codine"][:5], "nombre_ine": nombre_ine, "provincia_ign": provincia["nombre"],
            "provincia_ine": provincia_ine, "tipo_ign": capital_igr["tipo"], "capital_ign": capital_igr["capital"],
            "fecha_registro_ign": capital_igr["fecha"][:10], "lat": f"{chequeo['lat']:.6f}",
            "lon": f"{chequeo['lon']:.6f}", "lat_igr": f"{chequeo['lat_igr']:.9f}",
            "lon_igr": f"{chequeo['lon_igr']:.9f}", "dist_igr_km": f"{chequeo['dist_igr']:.3f}",
            "en_provincia_ign": str(chequeo["en_prov"]).lower(), "osm_lat": f"{chequeo['lat_osm']:.6f}",
            "osm_lon": f"{chequeo['lon_osm']:.6f}", "osm_tipo": osm.get("addresstype", ""),
            "osm_en_misma_provincia": str(chequeo["osm_en_prov"]).lower(),
            "dist_osm_km": f"{chequeo['dist_osm']:.2f}", "en_lista_verificacion": str(es_de_lista).lower(),
            "verificado_manual": "true" if verificado else "false",
        })
        avisos += avisos_capital(capital_igr, nombre_ine)
    return filas, verificacion, avisos + avisos_homonimos(homonimos_osm, sin_capital), provincias


# ----------------------------------------------------------------------------- salida


def escribir_csv(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)


def dibujar_mapa(filas: list[dict], provincias: dict[int, dict], ruta: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 9), dpi=150)
    for cpro, prov in provincias.items():
        if cpro in CPRO_EXCLUIDAS:
            continue
        geom = prov["geometry"]
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poligono in poligonos:
            anillo = poligono[0]
            paso = max(1, len(anillo) // 2000)  # solo para dibujar; la comprobación usa todos los vértices
            xs = [p[0] for p in anillo[::paso]] + [anillo[0][0]]
            ys = [p[1] for p in anillo[::paso]] + [anillo[0][1]]
            ax.plot(xs, ys, color="#888888", linewidth=0.5)
    for f in filas:
        color = "#1f77b4" if f["verificado_manual"] == "true" else "#ff7f0e"
        ax.scatter(float(f["lon"]), float(f["lat"]), s=14, color=color, zorder=3)
        ax.annotate(f["capital"], (float(f["lon"]), float(f["lat"])), fontsize=5.5,
                    xytext=(3, 3), textcoords="offset points")
    ax.set_xlim(-9.6, 3.6)
    ax.set_ylim(35.9, 44.0)
    ax.set_aspect(1 / math.cos(math.radians(40)))
    ax.set_xlabel("Longitud (°, ETRS89)")
    ax.set_ylabel("Latitud (°, ETRS89)")
    ax.set_title(f"Control T2.1: {len(filas)} capitales de provincia peninsulares (NGMEP {version_ngmep()}) "
                 "sobre límites provinciales IGN\n"
                 "azul = lista de verificación manual del Spec (superada); "
                 "naranja = resto (mismas comprobaciones automáticas)", fontsize=9)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fecha", required=True, help="Fecha de descarga de los crudos automáticos (AAAA-MM-DD)")
    parser.add_argument("--fecha-ngmep", default=FECHA_DESCARGA_NGMEP, help="Fecha de la descarga manual del NGMEP")
    args = parser.parse_args()
    filas, verificacion, avisos, provincias = construir(args.fecha, args.fecha_ngmep)
    escribir_csv(PROCESSED / "cities.csv", COLUMNAS, filas)
    escribir_csv(PROCESSED / "cities_verificacion.csv", COLUMNAS_VERIF, verificacion)
    dibujar_mapa(filas, provincias, PROCESSED / "cities_mapa_control.png")
    print(f"{len(filas)} capitales escritas en {PROCESSED / 'cities.csv'}")
    for aviso in avisos:
        print(f"AVISO: {aviso}")


if __name__ == "__main__":
    main()
