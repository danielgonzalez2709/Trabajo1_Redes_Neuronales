"""Valida data/processed/cities.csv contra el NGMEP crudo y mide la distancia a IGR Poblaciones (sin red).

Paso 3 del pipeline (orden completo en scripts/comun_bloque1.py).

Por cada capital:
  * comprueba que lat/lon de cities.csv reproducen, a 6 decimales, la entidad NGMEP "Capital de municipio"
    con el mismo CODIGOINE (fuente principal); si no, se detiene con error;
  * mide la distancia IGR Poblaciones -> NGMEP, leyendo IGR del crudo data/raw/ign_nuc_capitales_provincia_*.json;
  * mide la distancia del punto OSM de control a IGR y a NGMEP (la falta de OSM es un error explícito).

Uso:
    python scripts/validar_cities_ngmep.py
Salida:
    data/processed/cities_contraste_ngmep.csv
"""

from __future__ import annotations

import csv
import json
import statistics

from comun_bloque1 import (PROCESSED, RAW, coordenadas_osm, entidades_capital_ngmep, haversine_km, num,
                           ruta_unica)

UMBRAL_EXPLICAR_KM = 0.5

COLUMNAS = [
    "id", "capital", "provincia", "cod_prov", "codine_ign", "codine_ngmep", "codine_coincide",
    "nombre_ngmep", "tipo_ngmep", "origencoor_ngmep", "suprimida_ine", "discrepante_ine",
    "lat_ign", "lon_ign", "lat_ngmep", "lon_ngmep", "dist_km", "dist_osm_ign_km", "dist_osm_ngmep_km",
]


def leer_igr_por_codine() -> dict[str, dict]:
    consultas = json.loads(ruta_unica(RAW, "ign_nuc_capitales_provincia_*.json").read_text(encoding="utf-8"))
    return {f["properties"]["codine"]: f["properties"] for c in consultas for f in c["respuesta"]["features"]}


def validar() -> list[dict]:
    ngmep = entidades_capital_ngmep()
    igr = leer_igr_por_codine()
    with (PROCESSED / "cities.csv").open(encoding="utf-8", newline="") as fh:
        cities = {r["id"]: r for r in csv.DictReader(fh)}
    with (PROCESSED / "cities_verificacion.csv").open(encoding="utf-8", newline="") as fh:
        verificacion = list(csv.DictReader(fh))
    filas = []
    for fila_verif in verificacion:
        ciudad = cities[fila_verif["id"]]
        entidad_ngmep = ngmep[fila_verif["codigoine"][:2]]
        lat_n, lon_n = num(entidad_ngmep["LATITUD_ETRS89_REGCAN95"]), num(entidad_ngmep["LONGITUD_ETRS89_REGCAN95"])
        if (ciudad["lat"], ciudad["lon"]) != (f"{lat_n:.6f}", f"{lon_n:.6f}"):
            raise ValueError(f"{ciudad['capital']}: cities.csv no reproduce la coordenada NGMEP")
        capital_igr = igr[fila_verif["codine_ign"]]
        lat_i, lon_i = float(capital_igr["latitud"]), float(capital_igr["longitud"])
        lat_o, lon_o = coordenadas_osm(fila_verif)
        filas.append({
            "id": ciudad["id"], "capital": ciudad["capital"], "provincia": ciudad["provincia"],
            "cod_prov": entidad_ngmep["CODIGOINE"][:2], "codine_ign": capital_igr["codine"],
            "codine_ngmep": entidad_ngmep["CODIGOINE"],
            "codine_coincide": str(entidad_ngmep["CODIGOINE"] == capital_igr["codine"]).lower(),
            "nombre_ngmep": entidad_ngmep["NOMBRE"], "tipo_ngmep": entidad_ngmep["TIPO"],
            "origencoor_ngmep": entidad_ngmep["ORIGENCOOR"], "suprimida_ine": entidad_ngmep["SUPRIMIDA_INE"],
            "discrepante_ine": entidad_ngmep["DISCREPANTE_INE"],
            "lat_ign": f"{lat_i:.9f}", "lon_ign": f"{lon_i:.9f}", "lat_ngmep": f"{lat_n:.9f}",
            "lon_ngmep": f"{lon_n:.9f}",
            "dist_km": f"{haversine_km(lat_i, lon_i, lat_n, lon_n):.3f}",
            "dist_osm_ign_km": f"{haversine_km(lat_i, lon_i, lat_o, lon_o):.3f}",
            "dist_osm_ngmep_km": f"{haversine_km(lat_n, lon_n, lat_o, lon_o):.3f}",
        })
    return filas


def main() -> None:
    filas = validar()
    destino = PROCESSED / "cities_contraste_ngmep.csv"
    with destino.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)
    d = [float(f["dist_km"]) for f in filas]
    print(f"{len(filas)} capitales validadas contra el NGMEP -> {destino}")
    print(f"distancia IGR-NGMEP: max {max(d):.3f} km, mediana {statistics.median(d):.3f} km, "
          f"media {statistics.mean(d):.3f} km, idénticas (<1 m) {sum(x < 0.001 for x in d)}")
    print(f"códigos INE coincidentes: {sum(f['codine_coincide'] == 'true' for f in filas)}/{len(filas)}")
    for f in sorted(filas, key=lambda f: -float(f["dist_km"])):
        if float(f["dist_km"]) > UMBRAL_EXPLICAR_KM:
            print(f"> {UMBRAL_EXPLICAR_KM} km: {f['capital']} ({f['cod_prov']}) {f['dist_km']} km; "
                  f"OSM a {f['dist_osm_ign_km']} km del IGR y {f['dist_osm_ngmep_km']} km del NGMEP; "
                  f"origen NGMEP {f['origencoor_ngmep']}")


if __name__ == "__main__":
    main()
