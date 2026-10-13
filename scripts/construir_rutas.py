"""Paso 2 del pipeline del Bloque 2 (orden completo en scripts/comun_bloque2.py). Sin red.

Lee los crudos de OSRM de data/raw/osrm_<fecha>/ (los escribe `descargar_datos.py --bloque 2`; no se versionan) y
escribe en data/processed/ (contrato Spec §5.3):

  - rutas.csv: i, j, alternativa, dist_km, tiempo_h, km_peaje, peaje_eur, vias_peaje, fuente, fecha_extracto_osm.
    2 x 1 081 filas ordenadas por (i, j, alternativa).
    dist_km = distance (m) / 1000, redondeado a 4 decimales (0,1 m: la resolución de OSRM);
    tiempo_h = duration (s) / 3600, redondeado a 6 decimales (< 0,002 s).
    Par "sin peaje" (Spec §7.2 Bloque 2, v1.5): NINGUNA intersección de su ruta rapida tiene la clase toll. En
    ese par la fila sin_peaje reutiliza dist_km y tiempo_h de la rapida.
    km_peaje, peaje_eur y vias_peaje quedan VACÍAS: se completan en T2.5 (Bloque 3).
  - rutas_resumen.json: pares sin peaje, avisos, control de pasos (ref y clase toll) y simetría (20 pares j -> i).
  - rutas_pasos_peaje.csv: una fila por paso (step) de OSRM con al menos una intersección de clase toll, en las
    dos alternativas. Entrada de T2.5. ini = maneuver.location (6 decimales, tal cual OSRM); fin = último punto de
    la geometría del paso, polyline de precisión 5 (5 decimales; coincide con la maniobra del paso siguiente con
    error <= 1e-5 grados, comprobado en las fixtures de T2.2).

Cualquier crudo que falte o no sea válido (comun_bloque2.problema_crudo: code, data_version, URL, pasos) detiene el
proceso sin escribir nada (DatoFaltanteError).

Uso:
    python scripts/construir_rutas.py --fecha AAAA-MM-DD
    python scripts/construir_rutas.py --fecha AAAA-MM-DD --parcial --salida /tmp/rutas_prueba   # tras --limite N
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import comun_bloque2 as cb2
from comun_bloque2 import CITIES_CSV, PROCESSED, RAIZ, RAW, DatoFaltanteError

COLUMNAS = ["i", "j", "alternativa", "dist_km", "tiempo_h", "km_peaje", "peaje_eur", "vias_peaje", "fuente",
            "fecha_extracto_osm"]
COLUMNAS_PASOS = ["i", "j", "alternativa", "paso", "ref", "nombre", "dist_m", "n_intersecciones",
                  "n_intersecciones_toll", "lon_ini", "lat_ini", "lon_fin", "lat_fin"]
CLASE_PEAJE = "toll"
MAX_LISTADO = 15  # crudos con problema que se citan en el mensaje de error

CRITERIO_SIN_PEAJE = ("ninguna intersección (steps[].intersections[].classes) de la ruta rapida tiene la clase "
                      "'toll' (Spec §7.2 Bloque 2); en rutas.csv la fila sin_peaje reutiliza la rapida")
AVISOS = {
    "sin_peaje_mas_rapida": "solo pares no marcados: sin_peaje dura menos que rapida. No es un error: OSRM minimiza "
                            "weight (routability), no exactamente la duración",
    "par_sin_peaje_con_valores_distintos": "par marcado (rapida sin 'toll') en el que OSRM devolvió para sin_peaje "
                                           "otra distancia o duración; rutas.csv reutiliza la rapida",
    "sin_peaje_con_clase_toll": "la ruta exclude=toll pasa por intersecciones 'toll'. Se observó que depende del "
                                "historial de consultas del proceso osrm-routed cuando recibe consultas rapida y "
                                "exclude=toll mezcladas (mecanismo no confirmado). Según el Spec v1.8 §7.2 Bloque 2 se "
                                "reporta aquí; sus pasos están en rutas_pasos_peaje.csv y T2.5 cobra ese peaje",
}


def _legible(ruta: Path) -> str:
    try:
        return ruta.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return ruta.as_posix()


def decodificar_polyline(texto: str) -> list[tuple[float, float]]:
    """Polyline codificada de Google, precisión 5 (la de OSRM con geometries=polyline) -> [(lon, lat)]."""
    puntos, indice, lat, lon = [], 0, 0, 0
    while indice < len(texto):
        deltas = []
        for _ in range(2):  # primero la latitud, luego la longitud
            resultado, desplazamiento = 0, 0
            while True:
                byte = ord(texto[indice]) - 63
                indice += 1
                resultado |= (byte & 0x1F) << desplazamiento
                desplazamiento += 5
                if byte < 0x20:
                    break
            deltas.append(~(resultado >> 1) if resultado & 1 else resultado >> 1)
        lat, lon = lat + deltas[0], lon + deltas[1]
        puntos.append((lon / 1e5, lat / 1e5))
    return puntos


# ------------------------------------------------------------------------------------------------ crudos


def _cargar(directorio: Path, pares: list[tuple[int, int]], ciudades: list[cb2.Ciudad], parcial: bool,
            inverso: bool = False) -> tuple[dict[tuple[int, int, str], tuple[dict, Path]], list[tuple[int, int]]]:
    """Crudos válidos de las dos alternativas de `pares` (consultados j -> i si `inverso`), con clave (i, j, alt),
    y los pares que tienen las dos. Falta o crudo no válido -> DatoFaltanteError (las faltas se toleran si parcial)."""
    cargados, faltan, malos = {}, [], []
    for i, j in pares:
        origen, destino = (j, i) if inverso else (i, j)
        for alt in cb2.ALTERNATIVAS:
            archivo = directorio / cb2.nombre_crudo(origen, destino, alt)
            if not archivo.exists():
                faltan.append(archivo.name)
                continue
            url = cb2.url_ruta(cb2.OSRM_URL_LOCAL, ciudades[origen], ciudades[destino], alt)
            crudo, motivo = cb2.cargar_crudo(archivo, url)
            if motivo:
                malos.append(f"{archivo.name}: {motivo}")
            else:
                cargados[(i, j, alt)] = (crudo, archivo)
    _exigir_completos(directorio, faltan, malos, parcial)
    completos = [(i, j) for i, j in pares if all((i, j, a) in cargados for a in cb2.ALTERNATIVAS)]
    return cargados, completos


def _exigir_completos(directorio: Path, faltan: list[str], malos: list[str], parcial: bool) -> None:
    errores = []
    if malos:
        errores.append(f"{len(malos)} crudos no válidos en {_legible(directorio)}: {malos[:MAX_LISTADO]}")
    if faltan and not parcial:
        errores.append(f"TODO(dato-faltante): faltan {len(faltan)} crudos en {_legible(directorio)} "
                       f"(p. ej. {faltan[:MAX_LISTADO]}); relance descargar_datos.py --bloque 2 con la misma --fecha")
    if errores:
        raise DatoFaltanteError("; ".join(errores))


# ------------------------------------------------------------------------------------------------ pasos y criterio


def _pasos(ruta: dict) -> list[dict]:
    return [paso for leg in ruta["legs"] for paso in leg["steps"]]


def _n_toll(paso: dict) -> int:
    return sum(CLASE_PEAJE in inter.get("classes", []) for inter in paso.get("intersections", []))


def _tiene_toll(ruta: dict) -> bool:
    return any(_n_toll(paso) for paso in _pasos(ruta))


def _par_sin_peaje(ruta_rapida: dict) -> bool:
    """Spec §7.2 Bloque 2: el par no tiene peaje si NINGUNA intersección de su ruta rápida tiene la clase toll.
    (La clase va por intersección, no por paso; el nombre "AP-" no cuenta: varias AP ya son gratuitas.)"""
    return not _tiene_toll(ruta_rapida)


def _tiene_ref(ruta: dict) -> bool:
    return any(paso.get("ref") for paso in _pasos(ruta))


def _fila_paso(i: int, j: int, alt: str, k: int, paso: dict, n_toll: int) -> dict:
    puntos = decodificar_polyline(paso.get("geometry") or "")
    if not puntos:
        raise DatoFaltanteError(f"par ({i}, {j}) {alt}, paso {k}: sin geometría (se pidió geometries=polyline)")
    lon_ini, lat_ini = paso["maneuver"]["location"]
    lon_fin, lat_fin = puntos[-1]
    return {"i": i, "j": j, "alternativa": alt, "paso": k, "ref": paso.get("ref") or "",
            "nombre": paso.get("name") or "", "dist_m": f"{paso['distance']:.1f}",
            "n_intersecciones": len(paso["intersections"]), "n_intersecciones_toll": n_toll,
            "lon_ini": f"{lon_ini:.6f}", "lat_ini": f"{lat_ini:.6f}",
            "lon_fin": f"{lon_fin:.5f}", "lat_fin": f"{lat_fin:.5f}"}


def _pasos_peaje(i: int, j: int, alt: str, ruta: dict) -> list[dict]:
    """Filas de rutas_pasos_peaje.csv: pasos con al menos una intersección 'toll'; `paso` = índice en la ruta."""
    return [_fila_paso(i, j, alt, k, paso, n) for k, paso in enumerate(_pasos(ruta)) if (n := _n_toll(paso))]


# ------------------------------------------------------------------------------------------------ filas y resumen


def _fila(i: int, j: int, alt: str, ruta: dict, crudo: dict, archivo: Path, reutiliza: bool = False) -> dict:
    fuente = f"{cb2.FUENTE}; crudo {_legible(archivo)}"
    if reutiliza:
        fuente += "; par sin peaje: reutiliza la rapida"
    return {"i": i, "j": j, "alternativa": alt,
            "dist_km": f"{ruta['distance'] / 1000:.4f}", "tiempo_h": f"{ruta['duration'] / 3600:.6f}",
            "km_peaje": "", "peaje_eur": "", "vias_peaje": "",
            "fuente": fuente, "fecha_extracto_osm": crudo["respuesta"]["data_version"]}


def _comparacion(i: int, j: int, r: dict, s: dict) -> dict:
    return {"i": i, "j": j, "dist_km_rapida": r["distance"] / 1000, "dist_km_sin_peaje": s["distance"] / 1000,
            "tiempo_h_rapida": r["duration"] / 3600, "tiempo_h_sin_peaje": s["duration"] / 3600,
            "diferencia_h": (s["duration"] - r["duration"]) / 3600,
            "weight_rapida": r.get("weight"), "weight_sin_peaje": s.get("weight")}


@dataclass
class _Salida:
    """Lo que se acumula al recorrer los pares."""

    filas: list[dict] = field(default_factory=list)
    pasos: list[dict] = field(default_factory=list)
    marcados: list[list[int]] = field(default_factory=list)
    avisos: dict[str, list] = field(default_factory=lambda: {clave: [] for clave in AVISOS})
    fechas: list[str] = field(default_factory=list)
    con_ref: int = 0


def _procesar_par(sal: _Salida, i: int, j: int, principales: dict) -> None:
    (crudo_r, archivo_r), (crudo_s, archivo_s) = (principales[(i, j, alt)] for alt in cb2.ALTERNATIVAS)
    r, s = cb2.ruta_principal(crudo_r["respuesta"]), cb2.ruta_principal(crudo_s["respuesta"])
    marcado = _par_sin_peaje(r)
    sal.filas.append(_fila(i, j, "rapida", r, crudo_r, archivo_r))
    if marcado:
        sal.marcados.append([i, j])
        sal.filas.append(_fila(i, j, "sin_peaje", r, crudo_r, archivo_r, reutiliza=True))
    else:
        sal.filas.append(_fila(i, j, "sin_peaje", s, crudo_s, archivo_s))
    sal.pasos += _pasos_peaje(i, j, "rapida", r) + _pasos_peaje(i, j, "sin_peaje", s)
    sal.fechas += [crudo_r["fecha_consulta_utc"], crudo_s["fecha_consulta_utc"]]
    sal.con_ref += _tiene_ref(r) + _tiene_ref(s)
    if marcado and (r["distance"], r["duration"]) != (s["distance"], s["duration"]):
        sal.avisos["par_sin_peaje_con_valores_distintos"].append(_comparacion(i, j, r, s))
    if not marcado and s["duration"] < r["duration"]:
        sal.avisos["sin_peaje_mas_rapida"].append(_comparacion(i, j, r, s))
    if _tiene_toll(s):
        sal.avisos["sin_peaje_con_clase_toll"].append([i, j])


def _simetria(principales: dict, inversas: dict, pares_sim: list[tuple[int, int]]) -> dict:
    out: dict = {"criterio": "respuesta de OSRM j -> i (simetria/) frente a i -> j (rutas/), sin reutilizar; "
                             "relativa = |ji - ij| / ij",
                 "pares": [list(p) for p in pares_sim]}
    for alt in cb2.ALTERNATIVAS:
        detalle = []
        for i, j in pares_sim:
            ij = cb2.ruta_principal(principales[(i, j, alt)][0]["respuesta"])
            ji = cb2.ruta_principal(inversas[(i, j, alt)][0]["respuesta"])
            detalle.append({"i": i, "j": j, "dist_km_ij": ij["distance"] / 1000, "dist_km_ji": ji["distance"] / 1000,
                            "tiempo_h_ij": ij["duration"] / 3600, "tiempo_h_ji": ji["duration"] / 3600,
                            "abs_km": abs(ji["distance"] - ij["distance"]) / 1000,
                            "abs_h": abs(ji["duration"] - ij["duration"]) / 3600,
                            "rel_km": abs(ji["distance"] - ij["distance"]) / ij["distance"],
                            "rel_h": abs(ji["duration"] - ij["duration"]) / ij["duration"]})
        out[alt] = {f"max_{m}": max((d[m] for d in detalle), default=None)
                    for m in ("abs_km", "rel_km", "abs_h", "rel_h")}
        out[alt]["detalle"] = detalle
    return out


def _resumen(sal: _Salida, raw_dir: Path, parcial: bool, n_pares: int, simetria: dict) -> dict:
    return {
        "generado_por": "scripts/construir_rutas.py",
        "fuente": cb2.FUENTE,
        "fecha_extracto_osm": cb2.DATA_VERSION_ESPERADA,
        "crudos": _legible(raw_dir),
        "parcial": parcial,
        "n_pares": n_pares,
        "n_filas": len(sal.filas),
        "fecha_consulta_utc": {"min": min(sal.fechas, default=None), "max": max(sal.fechas, default=None)},
        "pares_sin_peaje": {"criterio": CRITERIO_SIN_PEAJE, "n": len(sal.marcados), "pares": sal.marcados},
        "avisos": {clave: {"nota": nota, "n": len(sal.avisos[clave]), "pares": sal.avisos[clave]}
                   for clave, nota in AVISOS.items()},
        "control_pasos": {
            "rutas": 2 * n_pares,
            "rutas_con_ref": sal.con_ref,
            "rapida_con_clase_toll": n_pares - len(sal.marcados),
            "sin_peaje_con_clase_toll": len(sal.avisos["sin_peaje_con_clase_toll"]),
            "filas_rutas_pasos_peaje": len(sal.pasos),
            "nota": "respuestas de OSRM de rutas/ (las dos alternativas de cada par, antes de reutilizar)"},
        "simetria": simetria,
    }


def _escribir_csv(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=columnas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def _escribir(salida_dir: Path, sal: _Salida, resumen: dict) -> None:
    salida_dir.mkdir(parents=True, exist_ok=True)
    _escribir_csv(salida_dir / "rutas.csv", COLUMNAS, sal.filas)
    _escribir_csv(salida_dir / "rutas_pasos_peaje.csv", COLUMNAS_PASOS, sal.pasos)
    (salida_dir / "rutas_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")


def construir(cities_csv: Path, raw_dir: Path, salida_dir: Path, parcial: bool = False) -> dict:
    """Valida los crudos de `raw_dir` y escribe rutas.csv, rutas_pasos_peaje.csv y rutas_resumen.json en
    `salida_dir`. Devuelve el resumen. Las filas salen ya ordenadas: pares en orden lexicográfico, alternativas en
    el orden de cb2.ALTERNATIVAS (alfabético) y pasos en orden de la ruta.

    `parcial=True` (solo tras una prueba con --limite) omite los pares sin descargar; nunca tolera crudos malos.
    """
    ciudades = cb2.leer_ciudades(cities_csv)
    n = len(ciudades)
    principales, pares_ok = _cargar(raw_dir / cb2.SUBDIR_RUTAS, cb2.pares(n), ciudades, parcial)
    completos = set(pares_ok)
    inversas, pares_sim = _cargar(raw_dir / cb2.SUBDIR_SIMETRIA,
                                  [p for p in cb2.pares_simetria(n) if p in completos], ciudades, parcial, inverso=True)
    sal = _Salida()
    for i, j in pares_ok:
        _procesar_par(sal, i, j, principales)
    resumen = _resumen(sal, raw_dir, parcial, len(pares_ok), _simetria(principales, inversas, pares_sim))
    _escribir(salida_dir, sal, resumen)
    return resumen


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fecha", required=True, help="fecha de la carpeta data/raw/osrm_<fecha>/ (AAAA-MM-DD)")
    parser.add_argument("--salida", type=Path, default=PROCESSED,
                        help="directorio de salida (por defecto data/processed)")
    parser.add_argument("--parcial", action="store_true",
                        help="omitir los pares sin descargar (prueba tras --limite); exige --salida fuera de "
                             "data/processed")
    return parser


def _imprimir(r: dict, salida: Path) -> None:
    cp, av = r["control_pasos"], r["avisos"]
    print(f"rutas.csv: {r['n_filas']} filas ({r['n_pares']} pares) -> {_legible(salida / 'rutas.csv')}")
    print(f"pares sin peaje (rapida sin clase toll): {r['pares_sin_peaje']['n']}")
    print(f"rutas con ref: {cp['rutas_con_ref']}/{cp['rutas']}; rapida con clase toll: {cp['rapida_con_clase_toll']}; "
          f"sin_peaje con clase toll: {cp['sin_peaje_con_clase_toll']}")
    print(f"rutas_pasos_peaje.csv: {cp['filas_rutas_pasos_peaje']} pasos con clase toll")
    print("avisos: " + "; ".join(f"{clave} {a['n']}" for clave, a in av.items()))
    for alt in cb2.ALTERNATIVAS:
        s = r["simetria"][alt]
        print(f"simetría {alt} ({len(r['simetria']['pares'])} pares): máx |dif| {s['max_abs_km']} km "
              f"(rel {s['max_rel_km']}), {s['max_abs_h']} h (rel {s['max_rel_h']})")
    if cp["sin_peaje_con_clase_toll"]:
        print("AVISO: hay rutas sin_peaje con la clase 'toll' (ver avisos en rutas_resumen.json). Según el Spec v1.8 "
              "§7.2 Bloque 2 se reportan y T2.5 cobra su peaje (pasos en rutas_pasos_peaje.csv).")


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    if args.parcial and args.salida.resolve() == PROCESSED.resolve():
        raise SystemExit("ERROR: --parcial no puede escribir en data/processed (rutas.csv quedaría incompleto); "
                         "use --salida DIR")
    raw_dir = RAW / f"osrm_{args.fecha}"
    if not (raw_dir / cb2.SUBDIR_RUTAS).is_dir():
        raise SystemExit(f"ERROR: no existe {_legible(raw_dir / cb2.SUBDIR_RUTAS)}; ¿se ejecutó "
                         f"descargar_datos.py --bloque 2 --fecha {args.fecha}?")
    try:
        resumen = construir(CITIES_CSV, raw_dir, args.salida, parcial=args.parcial)
    except DatoFaltanteError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    _imprimir(resumen, args.salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
