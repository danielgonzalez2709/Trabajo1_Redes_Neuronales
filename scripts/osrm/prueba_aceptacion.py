"""Prueba de aceptación de T2.2 en el OSRM local: rutas sin restricciones y con exclude=toll.

Lee las coordenadas de data/processed/cities.csv (no hay coordenadas escritas en el código), consulta el servidor
local con steps=true y guarda las respuestas crudas en data/raw/osrm_<AAAA-MM-DD>/.

Criterios:
  A. (PLAN T2.2) Madrid -> Barcelona: ambas alternativas responden code == "Ok" y la ruta exclude=toll no tiene
     ninguna intersección con la clase "toll". Se informa si la ruta rápida tiene peaje (no es requisito: la ruta
     va por A-2/AP-2/AP-7, tramos gratuitos desde 2021).
  B. (Spec §7.2 Bloque 3, paso 1: "[VERIFICAR que el OSRM local la marca]") en pares de control del Spec con peaje
     vigente (Bilbao-Zaragoza por AP-68, A Coruña-Pontevedra por AP-9): la ruta rápida debe tener al menos una
     intersección con la clase "toll" y la ruta exclude=toll ninguna.

Solo usa la biblioteca estándar y solo habla con el servidor local (no con internet).
Uso: python3 -I scripts/osrm/prueba_aceptacion.py --raiz <repo> [--url http://127.0.0.1:5001]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import unicodedata
import urllib.request
from pathlib import Path

CLASE_PEAJE = "toll"
# (origen, destino, exige_peaje_en_rapida). Los nombres son los de la columna "capital" de cities.csv.
PARES = [
    ("Madrid", "Barcelona", False),  # criterio A (PLAN)
    ("Bilbao", "Zaragoza", True),  # criterio B (AP-68, par de validación del Spec §7.2 Bloque 3)
    ("A Coruña", "Pontevedra", True),  # criterio B (AP-9, par de validación del Spec §7.2 Bloque 3)
]


def slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().replace(" ", "_")


def coordenadas(cities_csv: Path, capital: str) -> tuple[float, float]:
    """Devuelve (lon, lat) de la capital según cities.csv; falla si no hay exactamente una fila."""
    with cities_csv.open(encoding="utf-8", newline="") as fh:
        filas = [f for f in csv.DictReader(fh) if f["capital"] == capital]
    if len(filas) != 1:
        raise SystemExit(f"ERROR: se esperaba 1 fila para {capital!r} en {cities_csv}, hay {len(filas)}")
    return float(filas[0]["lon"]), float(filas[0]["lat"])


def consultar(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 (solo localhost)
        return json.load(resp)


def pasos_con_peaje(respuesta: dict) -> list[dict]:
    """Pasos con alguna intersección de clase 'toll' (ref, nombre y distancia del paso)."""
    encontrados = []
    for ruta in respuesta.get("routes", [])[:1]:
        for i_leg, leg in enumerate(ruta["legs"]):
            for i_paso, paso in enumerate(leg["steps"]):
                if any(CLASE_PEAJE in inter.get("classes", []) for inter in paso.get("intersections", [])):
                    encontrados.append(
                        {
                            "leg": i_leg,
                            "paso": i_paso,
                            "ref": paso.get("ref", ""),
                            "name": paso.get("name", ""),
                            "distancia_m": paso["distance"],
                        }
                    )
    return encontrados


def km_por_ref(respuesta: dict) -> dict[str, float]:
    """Km recorridos por cada 'ref' (solo los que superan 5 km), en orden de aparición."""
    acumulado: dict[str, float] = {}
    for leg in respuesta["routes"][0]["legs"]:
        for paso in leg["steps"]:
            ref = paso.get("ref", "") or "(sin ref)"
            acumulado[ref] = acumulado.get(ref, 0.0) + paso["distance"]
    return {k: round(v / 1000, 1) for k, v in acumulado.items() if v > 5000}


def resumir(resp: dict, url: str, archivo: str) -> dict:
    info = {"url": url, "archivo": archivo, "code": resp.get("code"), "message": resp.get("message"),
            "data_version": resp.get("data_version")}
    if resp.get("code") == "Ok":
        ruta = resp["routes"][0]
        peaje = pasos_con_peaje(resp)
        info.update(
            distancia_km=round(ruta["distance"] / 1000, 3),
            duracion_h=round(ruta["duration"] / 3600, 3),
            n_pasos=sum(len(leg["steps"]) for leg in ruta["legs"]),
            km_por_ref=km_por_ref(resp),
            n_pasos_con_clase_toll=len(peaje),
            distancia_pasos_con_clase_toll_km=round(sum(p["distancia_m"] for p in peaje) / 1000, 3),
            refs_con_clase_toll=sorted({p["ref"] for p in peaje if p["ref"]}),
            pasos_con_clase_toll=peaje,
        )
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", type=Path, required=True, help="raíz del repositorio")
    ap.add_argument("--url", default="http://127.0.0.1:5001", help="URL base del OSRM local")
    args = ap.parse_args()

    cities = args.raiz / "data" / "processed" / "cities.csv"
    destino_raw = args.raiz / "data" / "raw" / f"osrm_{dt.date.today().isoformat()}"
    destino_raw.mkdir(parents=True, exist_ok=True)

    resumen: dict = {
        "fecha_consulta_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "servidor": args.url,
        "coordenadas": "data/processed/cities.csv (lon, lat)",
        "pares": [],
    }
    errores: list[str] = []
    for origen, destino, exige_peaje in PARES:
        lon_o, lat_o = coordenadas(cities, origen)
        lon_d, lat_d = coordenadas(cities, destino)
        base = (f"{args.url}/route/v1/driving/{lon_o:.6f},{lat_o:.6f};{lon_d:.6f},{lat_d:.6f}"
                "?steps=true&overview=false")
        par = {"origen": origen, "destino": destino, "origen_lonlat": [lon_o, lat_o],
               "destino_lonlat": [lon_d, lat_d], "exige_toll_en_rapida": exige_peaje, "alternativas": {}}
        for nombre, url in {"rapida": base, "sin_peaje": base + "&exclude=toll"}.items():
            resp = consultar(url)
            archivo = destino_raw / f"{slug(origen)}_{slug(destino)}_{nombre}.json"
            archivo.write_text(json.dumps(resp, ensure_ascii=False, indent=1), encoding="utf-8")
            par["alternativas"][nombre] = resumir(resp, url, str(archivo.relative_to(args.raiz)))
            if resp.get("code") != "Ok":
                errores.append(f"{origen}-{destino} {nombre}: code={resp.get('code')!r} {resp.get('message')!r}")
        r, s = par["alternativas"]["rapida"], par["alternativas"]["sin_peaje"]
        if r["code"] == "Ok" and s["code"] == "Ok":
            par["sin_peaje_coincide_con_rapida"] = (r["distancia_km"], r["duracion_h"]) == (
                s["distancia_km"], s["duracion_h"])
            if s["n_pasos_con_clase_toll"] != 0:
                errores.append(f"{origen}-{destino}: la ruta exclude=toll contiene la clase 'toll'")
            if exige_peaje and r["n_pasos_con_clase_toll"] == 0:
                errores.append(f"{origen}-{destino}: la ruta rápida no tiene ninguna intersección con 'toll'")
        resumen["pares"].append(par)

    resumen["aceptacion"] = "OK" if not errores else "FALLA"
    resumen["errores"] = errores
    (destino_raw / "resumen_aceptacion.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")

    for par in resumen["pares"]:
        for nombre, a in par["alternativas"].items():
            etiqueta = f"{par['origen']}->{par['destino']} {nombre}"
            if a["code"] == "Ok":
                print(f"{etiqueta:34s} code=Ok {a['distancia_km']:7.1f} km {a['duracion_h']:5.2f} h "
                      f"pasos_toll={a['n_pasos_con_clase_toll']:3d} refs_toll={a['refs_con_clase_toll']}")
            else:
                print(f"{etiqueta:34s} code={a['code']} {a['message']}")
    print(f"Evidencia en {destino_raw.relative_to(args.raiz)}/ — aceptación: {resumen['aceptacion']}")
    for e in errores:
        print(f"ERROR: {e}")
    return 0 if not errores else 1


if __name__ == "__main__":
    sys.exit(main())
