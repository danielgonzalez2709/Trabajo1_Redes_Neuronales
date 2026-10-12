"""Mide sobre la geometría de OSM los km de los tramos de peaje sin longitud oficial (T2.4, Spec v1.9 §7.2 Bloque 3).

Sin red. Método: la longitud se mide A LO LARGO de la ruta de un crudo OSRM local de T2.3
(data/raw/osrm_2026-10-12/rutas/<i>_<j>_rapida.json.gz, extracto Geofabrik spain-261001, datos del
2026-10-01T20:22:06Z). Cada paso se decodifica (polyline, precisión 5) y su longitud geodésica se escala a la
`distance` que da OSRM para ese paso; cada extremo del tramo se proyecta sobre esa línea y el km es la diferencia
de distancias acumuladas. Los extremos son:
  - nodos `highway=motorway_junction` (con su `ref` de salida) del extracto spain-261001, leídos del PBF con
    pyosmium (fragmento y salida en data/raw/peajes_2026-10-12/extraer_nodos_osm_pyosmium.py y
    osm_motorway_junction_spain-261001.csv);
  - la `maneuver.location` de un paso del propio crudo (inicio de la autopista, cambio de vía), o
  - un p.k. oficial proyectado sobre la ruta desde un nodo de salida con p.k. oficial conocido (EXTREMOS_PK).
Para el tramo alavés de la AP-68 se mide la longitud de la ruta dentro del polígono provincial del IGN
(data/raw/ign_provincias_2026-10-07.geojson.gz).

Los crudos OSRM no se versionan (Spec §7.2 Bloque 2): este script solo se puede repetir en la máquina que ejecutó
T2.3. Por defecto escribe en el scratch del sistema; la evidencia versionada es
data/raw/peajes_2026-10-12/medicion_km_osm_2026-10-12.json (se actualiza solo con --salida explícita).

Uso:
    .venv/Scripts/python.exe scripts/medir_km_osm.py [--salida RUTA]
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
import tempfile
from pathlib import Path

from comun_bloque1 import RAW
from construir_rutas import decodificar_polyline

RUTAS = RAW / "osrm_2026-10-12" / "rutas"
PROVINCIAS_IGN = RAW / "ign_provincias_2026-10-07.geojson.gz"
EVIDENCIA = RAW / "peajes_2026-10-12" / "medicion_km_osm_2026-10-12.json"
NODOS_OSM = RAW / "peajes_2026-10-12" / "osm_motorway_junction_spain-261001.csv"
EXTRACTO = "Geofabrik spain-261001 (datos OSM del 2026-10-01T20:22:06Z)"
SEPARACION_MAX_M = 60.0          # un extremo debe caer a menos de esta distancia de la ruta
RADIO_TIERRA_M = 6371008.8       # radio medio de la Tierra (IUGG), para la distancia de haversine
M_POR_GRADO_LON_ECUADOR = 111320  # metros por grado de longitud en el ecuador (se multiplica por cos(lat))
M_POR_GRADO_LAT = 110540         # metros por grado de latitud (aprox. a latitudes medias): proyección local plana

# Extremos con coordenada: nombre -> (descripción, lon, lat). "nodo osm N" = nodo de NODOS_OSM.
EXTREMOS = {
    "bilbao": ("AP-68 Bilbao: inicio del paso AP-68 (bifurcación desde la A-8), nodo osm 99107204", -2.9182002, 43.2350521),
    "altube": ("AP-68 salida 5 (Altube), nodo osm 2449767107", -2.8776859, 42.9699517),
    "ap1": ("AP-68 salida 7 (enlace AP-1), nodo osm 1240215333", -2.9047558, 42.7128902),
    "zambrana": ("AP-68 salida 8 (Zambrana; 'salida 8' según el RD 730/2026), nodo osm 700911558", -2.889129, 42.6795054),
    "haro": ("AP-68 salida 9 (Haro), nodo osm 252456387", -2.8782105, 42.5619006),
    "logrono": ("AP-68 salida 12A (Logroño), nodo osm 30754525", -2.4687648, 42.4324533),
    "irurtzun": ("AP-15 inicio en Irurtzun (paso A-15 -> AP-15 del crudo)", -1.835623, 42.912253),
    "pamplona_oeste": ("AP-15 fin en Pamplona: paso a la variante oeste A-15 (libre) del crudo", -1.690396, 42.837116),
    "noain": ("AP-15 reincorporación en Noáin tras la variante oeste A-15 (paso del crudo)", -1.632362, 42.777002),
    "enlace_ap68": ("AP-15 fin: incorporación a la AP-68 (paso del crudo)", -1.718883, 42.090967),
    "urgoiti": ("AP-8 Bizkaia salida 105 (Urgoiti), nodo osm 30753673", -2.8202197, 43.2297021),
    "durango": ("AP-8 Bizkaia salida 88 (Durango, p.k. 88+300 de Interbiak), nodo osm 26386210", -2.6382038, 43.1792797),
    "eibar": ("AP-8 salida 71 (Eibar), nodo osm 26491757", -2.439412, 43.1926876),
    "donostia": ("AP-8 salida 27 (Donostia/Lasarte), nodo osm 1836402406", -2.0373387, 43.2903313),
    "vitoria": ("AP-1 Vitoria-Gasteiz (Etxabarri-Ibiña): incorporación a la AP-1 tras el peaje (paso del crudo)",
                -2.644658, 42.926175),
    "eskoriatza": ("AP-1 salida 123 (Eskoriatza), nodo osm 5168771925", -2.5202325, 43.0244655),
    "ap1_ap8": ("AP-1 salida 145 (enlace AP-8), nodo osm 26491535", -2.4314508, 43.1911686),
    "c32_44": ("C-32 salida 44 (Castelldefels Sud), nodo osm 211175134", 1.9669653, 41.2696287),
    "c32_31": ("C-32 salida 31 (Sitges), nodo osm 279746498", 1.8176482, 41.2453363),
    "c32_2": ("C-32 salida 2 (El Vendrell), nodo osm 279746562", 1.5293331, 41.193612),
}
# Extremos por p.k. oficial: nombre -> (descripción, ancla, p.k. de la ancla, p.k. buscado, ancla de sentido,
# p.k. de la ancla de sentido). Posición = posición(ancla) ± (p.k. buscado - p.k. ancla) a lo largo de la ruta; el
# signo sale de la segunda ancla (en qué sentido crece el p.k. sobre la ruta).
EXTREMOS_PK = {
    "ermua_pk": ("AP-8 Bizkaia Ermua, p.k. 75+580 de Interbiak proyectado sobre la ruta desde la salida 88 "
                 "(Durango, p.k. 88+300)", "durango", 88.3, 75.58, "urgoiti", 105.8),
}

# Filas de la tabla: id -> (crudo, extremo inicial, extremo final).
TRAMOS = {
    "AP68-01": ("44_46_rapida", "bilbao", "altube"),
    "AP68-02": ("44_46_rapida", "altube", "ap1"),
    "AP68-03": ("44_46_rapida", "ap1", "zambrana"),
    "AP68-04": ("44_46_rapida", "zambrana", "haro"),
    "AP15-01": ("18_46_rapida", "noain", "enlace_ap68"),
    "AP15-02": ("18_46_rapida", "irurtzun", "pamplona_oeste"),
    "AP8-02": ("18_44_rapida", "eibar", "ermua_pk"),
    "AP1-02": ("00_18_rapida", "vitoria", "eskoriatza"),
    "C32-01": ("06_39_rapida", "c32_44", "c32_31"),
    "C32-02": ("06_39_rapida", "c32_31", "c32_2"),
}
# Fila medida por provincia: id -> (crudo, extremo inicial, extremo final, provincia IGN).
TRAMOS_PROVINCIA = {"AP68-POST-VI": ("44_46_rapida", "bilbao", "haro", "Araba/Álava")}

# Contrastes del método con longitudes oficiales: nombre -> (crudo, ini, fin, km oficial, fuente).
CONTRASTES = {
    "AP-68 Haro-Logroño": ("44_46_rapida", "haro", "logrono", 40.06, "Catálogo RCE 2025, p.k. 87,0-126,9"),
    "AP-68 Bilbao-Haro (suma AP68-01..04)": ("44_46_rapida", "bilbao", "haro", 87.0,
                                             "Catálogo RCE 2025: Haro = p.k. 87+000 (origen del p.k. en Bilbao)"),
    "AP-8 Urgoiti-Ermua (fila AP8-01)": ("18_44_rapida", "ermua_pk", "urgoiti", 30.22,
                                         "Interbiak: p.k. 105+800 y 75+580"),
    "AP-8 Eibar-Donostia (fila AP8-03)": ("18_44_rapida", "donostia", "eibar", 43.3, "Bidegi: p.k. 71 y 27,7"),
    "AP-1 enlace AP-8-Eskoriatza (fila AP1-01)": ("00_18_rapida", "eskoriatza", "ap1_ap8", 22.3,
                                                  "Bidegi: p.k. 145,8 y 123,5"),
}
CONTRASTES_PROVINCIA = {
    "AP-68 tramo vizcaíno": ("44_46_rapida", "bilbao", "haro", "Bizkaia", 22.3, "Diputación Foral de Bizkaia, 22,3 km"),
    "AP-68 tramo alavés (fila AP68-POST-VI)": ("44_46_rapida", "bilbao", "haro", "Araba/Álava", round(77.597 - 22.3, 3),
                                               "Catálogo RCE p.k. 77+597 (L.P. Álava-Burgos) - 22,3 km de Bizkaia"),
    "AP-1 tramo guipuzcoano": ("00_18_rapida", "vitoria", "ap1_ap8", "Gipuzkoa", 31.9, "Bidegi: 31,9 km"),
}


def descripcion(extremo: str) -> str:
    return EXTREMOS[extremo][0] if extremo in EXTREMOS else EXTREMOS_PK[extremo][0]


def crudos_necesarios() -> list[Path]:
    nombres = {c for c, *_ in [*TRAMOS.values(), *TRAMOS_PROVINCIA.values(), *CONTRASTES.values(),
                               *CONTRASTES_PROVINCIA.values()]}
    return [RUTAS / f"{c}.json.gz" for c in sorted(nombres)]


def _haversine(a, b) -> float:
    la1, la2 = math.radians(a[1]), math.radians(b[1])
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2)
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(h))


def linea(crudo: str) -> tuple[list[tuple[tuple[float, float], float]], str]:
    """Puntos de la ruta con distancia acumulada en m (cada paso escalado a su `distance` de OSRM)."""
    with gzip.open(RUTAS / f"{crudo}.json.gz", "rt", encoding="utf-8") as f:
        datos = json.load(f)
    puntos, acum = [], 0.0
    for tramo in datos["respuesta"]["routes"][0]["legs"]:
        for paso in tramo["steps"]:
            g = decodificar_polyline(paso["geometry"])
            largo = sum(_haversine(g[k], g[k + 1]) for k in range(len(g) - 1))
            escala = paso["distance"] / largo if largo > 0 else 1.0
            for k, p in enumerate(g):
                if k > 0:
                    acum += _haversine(g[k - 1], p) * escala
                puntos.append((p, acum))
    return puntos, datos["url"]


def proyectar(puntos, q) -> tuple[float, float]:
    """(distancia acumulada en m del punto de la ruta más cercano a q, separación en m), en proyección local plana."""
    kx, ky = M_POR_GRADO_LON_ECUADOR * math.cos(math.radians(q[1])), M_POR_GRADO_LAT
    mejor = None
    for (a, da), (b, db) in zip(puntos, puntos[1:]):
        ax, ay = (a[0] - q[0]) * kx, (a[1] - q[1]) * ky
        bx, by = (b[0] - q[0]) * kx, (b[1] - q[1]) * ky
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, -(ax * vx + ay * vy) / l2))
        sep = math.hypot(ax + t * vx, ay + t * vy)
        if mejor is None or sep < mejor[1]:
            mejor = (da + t * (db - da), sep)
    return mejor


def posicion(puntos, extremo: str) -> tuple[float, float]:
    """(distancia acumulada en m, separación en m) de un extremo sobre la ruta."""
    if extremo in EXTREMOS:
        return proyectar(puntos, EXTREMOS[extremo][1:])
    _, ancla, pk_ancla, pk, ancla_sentido, pk_sentido = EXTREMOS_PK[extremo]
    (da, sa), (ds, ss) = proyectar(puntos, EXTREMOS[ancla][1:]), proyectar(puntos, EXTREMOS[ancla_sentido][1:])
    sentido = 1.0 if (ds - da) * (pk_sentido - pk_ancla) > 0 else -1.0
    return da + sentido * (pk - pk_ancla) * 1000, max(sa, ss)


def _dentro(pt, geometria) -> bool:
    poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
    x, y = pt
    for poligono in poligonos:
        dentro = False
        for anillo in poligono:
            j = len(anillo) - 1
            for i in range(len(anillo)):
                xi, yi = anillo[i][:2]
                xj, yj = anillo[j][:2]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    dentro = not dentro
                j = i
        if dentro:
            return True
    return False


def medir_tramo(lineas, crudo, ini, fin) -> dict:
    puntos, url = lineas[crudo]
    (da, sa), (db, sb) = posicion(puntos, ini), posicion(puntos, fin)
    if max(sa, sb) > SEPARACION_MAX_M:
        raise ValueError(f"{crudo}: extremo a más de {SEPARACION_MAX_M} m de la ruta ({sa:.1f}, {sb:.1f})")
    return {"crudo": f"osrm_2026-10-12/rutas/{crudo}.json.gz", "url": url, "desde": descripcion(ini),
            "hasta": descripcion(fin), "km_acumulado_desde": round(da / 1000, 3),
            "km_acumulado_hasta": round(db / 1000, 3), "separacion_m": [round(sa, 1), round(sb, 1)],
            "km": round(abs(db - da) / 1000, 3)}


def medir_provincia(lineas, provincias, crudo, ini, fin, provincia) -> dict:
    puntos, url = lineas[crudo]
    da, db = sorted((posicion(puntos, ini)[0], posicion(puntos, fin)[0]))
    total = 0.0
    for (a, xa), (b, xb) in zip(puntos, puntos[1:]):
        if da <= xa and xb <= db and _dentro(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), provincias[provincia]):
            total += xb - xa
    return {"crudo": f"osrm_2026-10-12/rutas/{crudo}.json.gz", "url": url, "desde": descripcion(ini),
            "hasta": descripcion(fin), "provincia_ign": provincia, "km": round(total / 1000, 3)}


def medir() -> dict:
    faltan = [p for p in crudos_necesarios() if not p.exists()]
    if faltan:
        raise FileNotFoundError(
            f"Faltan {len(faltan)} crudos OSRM de T2.3 (p. ej. {faltan[0]}). No se versionan (Spec §7.2 Bloque 2): "
            "solo existen en la máquina que ejecutó descargar_datos.py --bloque 2 --fecha 2026-10-12.")
    lineas = {p.name.removesuffix(".json.gz"): linea(p.name.removesuffix(".json.gz")) for p in crudos_necesarios()}
    with gzip.open(PROVINCIAS_IGN, "rt", encoding="utf-8") as f:
        ign = json.load(f)
    provincias = {ft["properties"].get("nameunit"): ft["geometry"] for ft in ign["features"]}
    salida = {"extracto": EXTRACTO, "metodo": __doc__.split("\n\n")[1].replace("\n", " "), "filas": {},
              "contrastes": {}}
    for ident, (c, a, b) in TRAMOS.items():
        salida["filas"][ident] = medir_tramo(lineas, c, a, b)
    for ident, (c, a, b, prov) in TRAMOS_PROVINCIA.items():
        salida["filas"][ident] = medir_provincia(lineas, provincias, c, a, b, prov)
    for nombre, (c, a, b, oficial, fuente) in CONTRASTES.items():
        m = medir_tramo(lineas, c, a, b)
        salida["contrastes"][nombre] = {**m, "km_oficial": oficial, "fuente_oficial": fuente,
                                        "diferencia_pct": round(100 * (m["km"] - oficial) / oficial, 2)}
    for nombre, (c, a, b, prov, oficial, fuente) in CONTRASTES_PROVINCIA.items():
        m = medir_provincia(lineas, provincias, c, a, b, prov)
        salida["contrastes"][nombre] = {**m, "km_oficial": oficial, "fuente_oficial": fuente,
                                        "diferencia_pct": round(100 * (m["km"] - oficial) / oficial, 2)}
    return salida


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--salida", type=Path, default=Path(tempfile.gettempdir()) / EVIDENCIA.name,
                        help=f"JSON de salida (por defecto, el temporal del sistema; la evidencia es {EVIDENCIA})")
    args = parser.parse_args(argv)
    try:
        resultado = medir()
    except FileNotFoundError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                           newline="\n")
    for ident, m in resultado["filas"].items():
        print(f"{ident:14} {m['km']:8.3f} km")
    for nombre, m in resultado["contrastes"].items():
        print(f"{nombre:45} OSM {m['km']:8.3f}  oficial {m['km_oficial']:8.3f}  {m['diferencia_pct']:+.2f} %")
    print(f"-> {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
