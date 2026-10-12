"""T2.5 (Spec §7.2 Bloque 3, "Cálculo por ruta"): asigna los peajes de peajes_tramos.csv a cada ruta de rutas.csv. Sin red.

Entradas (todas versionadas en data/processed/):
  rutas.csv                 filas de T2.3 con km_peaje, peaje_eur y vias_peaje vacías (se rellenan; es la salida).
  rutas_pasos_peaje.csv     pasos de OSRM con al menos una intersección de clase `toll` (T2.3): ref, dist_m, extremos.
  peajes_tramos.csv         56 filas de T2.4 (tarifa de ligeros y km por tramo).
  peajes_cadenas.csv        T2.5: a qué cadena pertenece cada tramo, en qué orden y con qué `ref` de OSRM se nombra.
  peajes_anclas.csv         T2.5: coordenadas de puntos conocidos de cada cadena y su km acumulado.

Una CADENA es una sucesión de tramos contiguos de una misma autopista, medida en km desde su primer extremo
(Σ km de peajes_tramos.csv). Los ANCLAS (lon, lat, km_cadena) permiten saber en qué km de la cadena está un punto.

Método (documentado en docs/validacion_peajes_T2.5.md y en el Spec v1.10):
  1. De cada ruta (i, j, alternativa) se toman los pasos de rutas_pasos_peaje.csv. Un paso sin `ref` es un enlace
     (rampa) y no se cobra: la tarifa va por tramo, no por enlace.
  2. Cada paso con `ref` se asigna a una cadena cuya lista `refs_osrm` lo contiene (no por prefijo: la AP-7 de Málaga y la de
     Alicante tienen la misma `ref`); si varias cadenas la comparten, gana la más cercana a los dos extremos del paso.
  3. Cada extremo del paso se sitúa en el km de la cadena: ajuste a un ancla si hay una a <= 1,5 km; si no, proyección
     sobre la poligonal de anclas (interpolación lineal del km entre anclas). Fuera de los extremos de la cadena, se
     recorta al primer o último ancla. No se usa n_intersecciones_toll/n_intersecciones: sobrestima o subestima los km
     de peaje en un paso parcial hasta un 25 % (p. ej. AP-6 en Villalba) y no dice dónde está el tramo.
  4. Por ruta y cadena se toma el RECORRIDO [mín, máx] de todos sus pasos (OSM deja sin la clase `toll` algunos
     trozos de autopista, como en la AP-7 de Málaga; el coche no sale de la autopista).
  5. Peaje = Σ tarifa_tramo x (km recorridos en el tramo / km del tramo); desde 95 % de recorrido se cobra la
     tarifa completa. La suma de tramos es la decisión del Spec v1.9 para el peaje cerrado.
  6. Las filas `sin_peaje` con clase `toll` (M-12, AP-15, AP-68) se cobran igual que cualquier otra.

Salidas: rutas.csv (se reescribe), rutas_peajes_detalle.csv (una fila por ruta y tramo recorrido),
peajes_avisos.csv (pasos que no se cobraron o son incoherentes) y peajes_resumen.json. Es idempotente.

Constantes (parámetros ELEGIDOS por el curador de T2.5; no salen de ninguna fuente oficial ni del Spec):
  Alteran importes:  SNAP_M (1,5 km) y FRACCION_COMPLETA (95 %).
    - SNAP_M: no tiene origen documentado. Es un radio elegido para absorber la diferencia entre la coordenada de un
      paso de OSRM y la del ancla del mismo enlace. No se derivó del Noáin a 1,25 km de tests/test_peajes_anclas.py: ese
      dato solo comprueba que los anclas `paso_osrm` están a < 1,5 km de un extremo de paso. Efecto medido
      (docs/validacion_peajes_T2.5.md, sec. 5): 1,0 km cambia 33 rutas, 2,0 km cambia 15 y sin ajuste cambia 110,
      con cambios de hasta 0,25 EUR en una ruta.
    - FRACCION_COMPLETA: tampoco tiene origen documentado; es el umbral elegido para no cobrar el 94 % de un tramo
      cuando el paso termina antes del enlace. Efecto medido: 90 % cambia 15 rutas (hasta 0,25 EUR); 100 % cambia 0.
  Solo diagnostican en los datos actuales: DIST_MAX_INTERIOR_M, DIST_MAX_EXTERIOR_M, SOLAPE_MIN_KM (ruido de
    proyección, < 50 m), COHERENCIA_REL y COHERENCIA_ABS_KM. COHERENCIA_* solo genera avisos. DIST_MAX_* descarta un paso
    (aviso `lejos_de_la_cadena`, no se cobra) y SOLAPE_MIN_KM omite solapes < 50 m; medido: anular DIST_MAX_* o
    SOLAPE_MIN_KM deja 0 rutas con otro importe, pero en otros datos podrían cambiarlo.
    M_POR_GRADO_* son los de scripts/medir_km_osm.py.

Uso:
    .venv/Scripts/python.exe scripts/asignar_peajes.py [--fecha-corte 2026-10-01]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from comun_bloque1 import PROCESSED, DatoFaltanteError

__all__ = ["DatoFaltanteError", "asignar", "leer_cadenas", "main", "peaje_de_ruta", "proyectar"]

FECHA_CORTE = "2026-10-01"  # Spec §7.1
SNAP_M = 1500.0                  # un extremo a menos de esto de un ancla se ajusta a ella
DIST_MAX_INTERIOR_M = 5000.0     # distancia máxima a la poligonal de un extremo que cae dentro de la cadena
DIST_MAX_EXTERIOR_M = 20000.0    # ídem si el extremo queda más allá del primer o último ancla (trozo libre previo)
FRACCION_COMPLETA = 0.95         # desde este recorrido del tramo se cobra la tarifa completa
SOLAPE_MIN_KM = 0.05             # por debajo de esto un solape es ruido de la proyección
COHERENCIA_REL = 0.20            # un paso 100 % toll entre anclas debe medir lo mismo que su tramo de cadena, +-20 %
COHERENCIA_ABS_KM = 2.5          # ... y al menos esto de margen
M_POR_GRADO_LON_ECUADOR = 111320  # los mismos del script de T2.4 (medir_km_osm.py)
M_POR_GRADO_LAT = 110540

TRAMOS_CSV = PROCESSED / "peajes_tramos.csv"
CADENAS_CSV = PROCESSED / "peajes_cadenas.csv"
ANCLAS_CSV = PROCESSED / "peajes_anclas.csv"
RUTAS_CSV = PROCESSED / "rutas.csv"
PASOS_CSV = PROCESSED / "rutas_pasos_peaje.csv"
COLS_DETALLE = ["i", "j", "alternativa", "cadena", "tramo_id", "via", "km_cubiertos", "fraccion", "tarifa_eur",
                "importe_eur"]
COLS_AVISOS = ["i", "j", "alternativa", "paso", "ref", "motivo", "detalle"]


@dataclass(frozen=True)
class Tramo:
    id: str
    via: str
    km: float
    tarifa: float
    inicio_km: float
    fin_km: float


@dataclass(frozen=True)
class Ancla:
    km: float
    lon: float
    lat: float
    etiqueta: str = ""


@dataclass
class Cadena:
    id: str
    refs: frozenset
    tramos: list = field(default_factory=list)   # solo los vigentes, en orden
    longitud_km: float = 0.0                    # incluye tramos no vigentes, para que los km de los anclas no se muevan
    anclas: list = field(default_factory=list)

    @property
    def proyectable(self) -> bool:
        return len(self.anclas) >= 2


@dataclass(frozen=True)
class Proyeccion:
    km: float
    dist_m: float
    extremo: str | None  # "ini" / "fin" si el punto cae más allá del primer / último ancla


class Asignado(NamedTuple):
    cadena: Cadena
    inicio: Proyeccion
    fin: Proyeccion


class NoAsignado(NamedTuple):
    motivo: str
    detalle: str


@dataclass
class Recorrido:
    """Tramo [lo, hi] de una cadena recorrido por los pasos de una ruta; `primero` = índice del primer paso."""
    lo: float
    hi: float
    primero: int


@dataclass
class ResultadoRuta:
    km_peaje: float = 0.0
    peaje_eur: float = 0.0
    vias: list = field(default_factory=list)
    detalle: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    pasos_sin_ref: int = 0
    km_sin_ref: float = 0.0          # km OSRM de los pasos sin ref (enlaces)
    pasos_asignados: int = 0
    no_asignados: list = field(default_factory=list)  # (motivo, km OSRM del paso) de los pasos con ref no cobrados


# ------------------------------------------------------------------------------------------------ lectura

def _leer_csv(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _vigente(fila: dict, corte: str) -> bool:
    desde, hasta = fila["vigente_desde"], fila["vigente_hasta"]
    return desde <= corte and (hasta == "" or hasta >= corte)


def leer_cadenas(tramos_csv: Path, cadenas_csv: Path, anclas_csv: Path, fecha_corte: str) -> dict[str, Cadena]:
    """Cadenas con sus tramos vigentes en `fecha_corte` y sus anclas. Falla (DatoFaltanteError) si falta algo."""
    tramos = {f["id"]: f for f in _leer_csv(tramos_csv)}
    filas = _leer_csv(cadenas_csv)
    por_cadena: dict[str, list[dict]] = defaultdict(list)
    for f in filas:
        if f["id_tramo"] not in tramos:
            raise DatoFaltanteError(f"{cadenas_csv.name}: el tramo {f['id_tramo']} no está en {tramos_csv.name}")
        por_cadena[f["cadena"]].append(f)
    listados = {f["id_tramo"] for f in filas}
    for id_, f in tramos.items():
        if _vigente(f, fecha_corte) and id_ not in listados:
            raise DatoFaltanteError(
                f"{id_}: tramo vigente el {fecha_corte} sin cadena en {cadenas_csv.name} (TODO(dato-faltante))")
    cadenas: dict[str, Cadena] = {}
    for cid, fs in por_cadena.items():
        fs.sort(key=lambda f: int(f["orden"]))
        refs = {r for f in fs for r in f["refs_osrm"].split("|") if r}
        cad = Cadena(cid, frozenset(refs))
        km = 0.0
        for f in fs:
            t = tramos[f["id_tramo"]]
            largo = float(t["km"])
            if _vigente(t, fecha_corte):
                if t["tarifa_ligeros_eur"].startswith("TODO"):
                    raise DatoFaltanteError(f"{t['id']}: tarifa vigente el {fecha_corte} es {t['tarifa_ligeros_eur']}")
                cad.tramos.append(Tramo(t["id"], t["via"], largo, float(t["tarifa_ligeros_eur"]), km, km + largo))
            km += largo
        cad.longitud_km = km
        cadenas[cid] = cad
    for f in _leer_csv(anclas_csv):
        cad = cadenas.get(f["cadena"])
        if cad is None:
            raise DatoFaltanteError(f"{anclas_csv.name}: la cadena {f['cadena']} no existe en {cadenas_csv.name}")
        km = float(f["km_cadena"])
        if not -1e-6 <= km <= cad.longitud_km + 1e-6:
            raise DatoFaltanteError(
                f"{anclas_csv.name}: ancla {f['etiqueta']!r} en km {km} fuera de la cadena {cad.id} "
                f"(0 a {cad.longitud_km:.3f})")
        cad.anclas.append(Ancla(km, float(f["lon"]), float(f["lat"]), f["etiqueta"]))
    for cad in cadenas.values():
        cad.anclas.sort(key=lambda a: a.km)  # estable: los anclas con el mismo km conservan el orden del archivo
    return cadenas


# ------------------------------------------------------------------------------------------------ geometría

def _vector_m(lon0: float, lat0: float, lon1: float, lat1: float) -> tuple[float, float]:
    """Desplazamiento (x, y) en metros de (lon0, lat0) a (lon1, lat1), en proyección local plana."""
    return ((lon1 - lon0) * M_POR_GRADO_LON_ECUADOR * math.cos(math.radians(lat0)), (lat1 - lat0) * M_POR_GRADO_LAT)


def proyectar(cadena: Cadena, lon: float, lat: float) -> Proyeccion:
    """Km de la cadena más cercano al punto, con la distancia que lo separa de ella."""
    anclas = cadena.anclas
    cercano, d_cercano = None, math.inf
    for a in anclas:
        d = math.hypot(*_vector_m(lon, lat, a.lon, a.lat))
        if d < d_cercano:
            cercano, d_cercano = a, d
    if d_cercano <= SNAP_M:
        return Proyeccion(cercano.km, d_cercano, None)
    mejor = None
    for k, (a, b) in enumerate(zip(anclas, anclas[1:])):
        ax, ay = _vector_m(lon, lat, a.lon, a.lat)
        bx, by = _vector_m(lon, lat, b.lon, b.lat)
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy
        t_raw = 0.0 if l2 == 0 else -(ax * vx + ay * vy) / l2
        t = max(0.0, min(1.0, t_raw))
        d = math.hypot(ax + t * vx, ay + t * vy)
        if mejor is None or d < mejor[0]:
            extremo = "ini" if (k == 0 and t_raw < 0) else "fin" if (k == len(anclas) - 2 and t_raw > 1) else None
            mejor = (d, a.km + t * (b.km - a.km), extremo)
    return Proyeccion(mejor[1], mejor[0], mejor[2])


def _valida(p: Proyeccion) -> bool:
    return p.dist_m <= (DIST_MAX_INTERIOR_M if p.extremo is None else DIST_MAX_EXTERIOR_M)


# ------------------------------------------------------------------------------------------------ cálculo por ruta

def _texto(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return None if s in ("", "nan", "NaN", "None") else s


def _aviso(p: dict, motivo: str, detalle: str) -> dict:
    return {"i": p["i"], "j": p["j"], "alternativa": p["alternativa"], "paso": p["paso"], "ref": _texto(p["ref"]) or "",
            "motivo": motivo, "detalle": detalle}


def _asignar_paso(cadenas: dict[str, Cadena], p: dict) -> Asignado | NoAsignado:
    """`Asignado` (cadena y proyección de cada extremo) o `NoAsignado` (motivo y detalle) si el paso no se puede asignar."""
    ref = _texto(p["ref"])
    candidatas = [c for c in cadenas.values() if ref in c.refs]
    if not candidatas:
        return NoAsignado("ref_sin_cadena", f"ninguna cadena de peajes_cadenas.csv se llama {ref!r}")
    proyectables = [c for c in candidatas if c.proyectable]
    if not proyectables:
        return NoAsignado("cadena_sin_anclas",
                          f"cadenas {sorted(c.id for c in candidatas)} sin 2 anclas en peajes_anclas.csv")
    lon0, lat0, lon1, lat1 = (float(p[k]) for k in ("lon_ini", "lat_ini", "lon_fin", "lat_fin"))
    mejor = None
    for c in proyectables:
        a, b = proyectar(c, lon0, lat0), proyectar(c, lon1, lat1)
        if _valida(a) and _valida(b) and (mejor is None or a.dist_m + b.dist_m < mejor[3]):
            mejor = (c, a, b, a.dist_m + b.dist_m)
    if mejor is None:
        return NoAsignado("lejos_de_la_cadena", (
            f"a más de {DIST_MAX_INTERIOR_M / 1000:.0f} km (o {DIST_MAX_EXTERIOR_M / 1000:.0f} km más allá de un extremo) "
            f"de las cadenas {sorted(c.id for c in proyectables)}"))
    return Asignado(*mejor[:3])


def peaje_de_ruta(cadenas: dict[str, Cadena], pasos: list[dict]) -> ResultadoRuta:
    """Peaje de una ruta a partir de sus pasos con clase toll (dicts con las columnas de rutas_pasos_peaje.csv)."""
    res = ResultadoRuta()
    recorrido: dict[str, Recorrido] = {}  # cadena -> tramo recorrido
    for k, p in enumerate(pasos):
        if _texto(p["ref"]) is None:
            res.pasos_sin_ref += 1
            res.km_sin_ref += float(p["dist_m"]) / 1000
            continue
        asig = _asignar_paso(cadenas, p)
        if isinstance(asig, NoAsignado):
            res.avisos.append(_aviso(p, asig.motivo, asig.detalle))
            res.no_asignados.append((asig.motivo, float(p["dist_m"]) / 1000))
            continue
        cad, a, b = asig
        res.pasos_asignados += 1
        lo, hi = sorted((a.km, b.km))
        r = recorrido.setdefault(cad.id, Recorrido(lo, hi, k))
        r.lo, r.hi = min(r.lo, lo), max(r.hi, hi)
        if int(p["n_intersecciones_toll"]) == int(p["n_intersecciones"]) and a.extremo is None and b.extremo is None:
            esperado, osrm = hi - lo, float(p["dist_m"]) / 1000
            if abs(esperado - osrm) > max(COHERENCIA_ABS_KM, COHERENCIA_REL * osrm):
                res.avisos.append(_aviso(p, "km_incoherente",
                                         f"OSRM mide {osrm:.2f} km y la cadena {cad.id} {esperado:.2f} km entre sus extremos"))
    total = 0.0
    for cid, rec in sorted(recorrido.items(), key=lambda kv: kv[1].primero):
        for t in cadenas[cid].tramos:
            solape = min(rec.hi, t.fin_km) - max(rec.lo, t.inicio_km)
            if solape < SOLAPE_MIN_KM:
                continue
            fraccion = solape / t.km
            if fraccion >= FRACCION_COMPLETA:
                fraccion, solape = 1.0, t.km
            importe = t.tarifa * fraccion
            res.detalle.append({"cadena": cid, "tramo_id": t.id, "via": t.via, "km_cubiertos": solape,
                                "fraccion": fraccion, "tarifa_eur": t.tarifa, "importe_eur": importe})
            total += importe
            if t.tarifa > 0:
                res.km_peaje += solape
                if t.via not in res.vias:
                    res.vias.append(t.via)
    res.peaje_eur = total
    return res


# ------------------------------------------------------------------------------------------------ archivos

def _clave(f: dict) -> tuple[int, int, str]:
    return int(f["i"]), int(f["j"]), f["alternativa"]


def _escribir_csv(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def asignar(rutas_csv: Path, pasos_csv: Path, tramos_csv: Path, cadenas_csv: Path, anclas_csv: Path, salida_dir: Path,
            fecha_corte: str) -> dict:
    cadenas = leer_cadenas(tramos_csv, cadenas_csv, anclas_csv, fecha_corte)
    with rutas_csv.open(encoding="utf-8", newline="") as f:
        lector = csv.DictReader(f)
        columnas = list(lector.fieldnames)
        rutas = list(lector)
    pasos_por_ruta: dict[tuple, list[dict]] = defaultdict(list)
    for p in _leer_csv(pasos_csv):
        pasos_por_ruta[_clave(p)].append(p)
    conocidas = {_clave(f) for f in rutas}
    desconocidas = sorted(set(pasos_por_ruta) - conocidas)
    if desconocidas:
        raise DatoFaltanteError(
            f"{pasos_csv.name} tiene pasos de rutas que no están en {rutas_csv.name}: {desconocidas[:5]} "
            "(¿corridas distintas de T2.3?)")
    detalle, avisos = [], []
    n_sin_ref = {"n": 0, "km_osrm": 0.0}
    no_asignados: dict[str, dict] = defaultdict(lambda: {"n": 0, "km_osrm": 0.0})
    por_via: dict[str, int] = defaultdict(int)
    con_peaje = 0
    for f in rutas:
        pasos = pasos_por_ruta.get(_clave(f), [])
        r = peaje_de_ruta(cadenas, pasos)
        f["km_peaje"], f["peaje_eur"], f["vias_peaje"] = f"{r.km_peaje:.4f}", f"{r.peaje_eur:.2f}", ";".join(r.vias)
        con_peaje += r.peaje_eur > 0
        for v in r.vias:
            por_via[v] += 1
        for d in r.detalle:
            detalle.append({"i": f["i"], "j": f["j"], "alternativa": f["alternativa"],
                            **{k: (f"{v:.3f}" if k == "km_cubiertos" else f"{v:.4f}" if k in ("fraccion", "tarifa_eur", "importe_eur") else v)
                               for k, v in d.items()}})
        avisos.extend(r.avisos)
        n_sin_ref["n"] += r.pasos_sin_ref
        n_sin_ref["km_osrm"] += r.km_sin_ref
        for motivo, km in r.no_asignados:
            no_asignados[motivo]["n"] += 1
            no_asignados[motivo]["km_osrm"] += km
    with rutas_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas, lineterminator="\n")
        w.writeheader()
        w.writerows(rutas)
    _escribir_csv(salida_dir / "rutas_peajes_detalle.csv", COLS_DETALLE, detalle)
    _escribir_csv(salida_dir / "peajes_avisos.csv", COLS_AVISOS, avisos)
    resumen = {
        "generado_por": "scripts/asignar_peajes.py (T2.5)",
        "fecha_corte": fecha_corte,
        "parametros": {"snap_m": SNAP_M, "dist_max_interior_m": DIST_MAX_INTERIOR_M,
                       "dist_max_exterior_m": DIST_MAX_EXTERIOR_M, "fraccion_completa": FRACCION_COMPLETA,
                       "solape_min_km": SOLAPE_MIN_KM},
        "n_filas": len(rutas),
        "n_filas_con_peaje": con_peaje,
        "n_avisos": len(avisos),
        "avisos_por_motivo": {m: sum(1 for a in avisos if a["motivo"] == m) for m in sorted({a["motivo"] for a in avisos})},
        "pasos_sin_ref": {"n": n_sin_ref["n"], "km_osrm": round(n_sin_ref["km_osrm"], 3)},
        "pasos_no_asignados": {m: {"n": v["n"], "km_osrm": round(v["km_osrm"], 3)} for m, v in sorted(no_asignados.items())},
        "filas_por_via": dict(sorted(por_via.items())),
    }
    (salida_dir / "peajes_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + "\n",
                                                    encoding="utf-8")
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--rutas", type=Path, default=RUTAS_CSV, help="rutas.csv (se reescribe)")
    parser.add_argument("--pasos", type=Path, default=PASOS_CSV)
    parser.add_argument("--tramos", type=Path, default=TRAMOS_CSV)
    parser.add_argument("--cadenas", type=Path, default=CADENAS_CSV)
    parser.add_argument("--anclas", type=Path, default=ANCLAS_CSV)
    parser.add_argument("--salida-dir", type=Path, default=PROCESSED, help="detalle, avisos y resumen")
    parser.add_argument("--fecha-corte", default=FECHA_CORTE)
    args = parser.parse_args(argv)
    try:
        r = asignar(args.rutas, args.pasos, args.tramos, args.cadenas, args.anclas, args.salida_dir, args.fecha_corte)
    except DatoFaltanteError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"{r['n_filas']} filas, {r['n_filas_con_peaje']} con peaje, {r['n_avisos']} avisos "
          f"({r['avisos_por_motivo']}); pasos sin ref: {r['pasos_sin_ref']['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
