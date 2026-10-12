"""Integridad de los datos de la Parte 2 (T2.8; Spec §5.3 y §10). Solo lee archivos versionados y NO abre sockets.

Qué comprueba (solo lo que NO comprueban ya las pruebas por bloque):
  1. Correspondencia entre archivos: los ids de rutas.csv son los 47 de cities.csv; las coordenadas no se repiten.
  2. rutas.csv: matrices 47×47 de dist_km, tiempo_h y peaje_eur por alternativa (completas, finitas, positivas fuera de
     la diagonal), cota ortodrómica y asimetría medida en rutas_resumen.json frente a rutas.csv. La simetría y la
     diagonal 0 son por construcción (ver `matriz`).
  3. data/fuentes.md frente a los datos: la fuente_url de cada fila de peajes_tramos.csv consta en la columna URL de
     una fila con la MISMA fecha de consulta; la vigencia de cada fila coincide con la documentada; las filas con
     tarifa TODO están documentadas; combustible.json y vehiculo.yaml tienen fuente y fecha coherentes; cada descarga
     registrada en cabeceras_http.txt tiene su URL en la columna URL; el rango horario citado cubre las capturas.
  4. data/fuentes.md: tablas con el encabezado exigido y 5 columnas, fecha de consulta válida y no futura, sin TODO,
     y las dos zonas horarias del equipo (UTC−3 y UTC−5) en el encabezado.

Ya cubierto en otros archivos y por eso NO se repite aquí:
  - cities.csv (47 filas, ids, capitales y provincias únicas, caja peninsular, sin insulares, fuente y fecha):
    test_cities.py.
  - peajes_tramos.csv (columnas, fuente_url y fecha_consulta no vacías, tarifa numérica en las filas vigentes en el
    corte, filas no vigentes = NO_VIGENTES_EN_CORTE, AP-68, km, MANIFEST): test_peajes_tramos.py.
  - rutas.csv real con 2 162 filas y las tres columnas de peaje completas, y los pares sin peaje a 0 €:
    test_asignar_peajes.py; el contrato de columnas y los 1 081 pares de la construcción: test_rutas.py.

Los validadores son funciones puras (reciben los datos) para poder probarlos con copias rotas en memoria: cada
aserción relevante tiene una prueba de mutación al final del archivo. Los datos reales no se modifican.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
import socket
from pathlib import Path

import numpy as np
import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data" / "processed"
RAW = RAIZ / "data" / "raw"
FUENTES_MD = RAIZ / "data" / "fuentes.md"

N_CIUDADES = 47
CORTE = "2026-10-01"  # Spec §7.1 [DECIDIDO]
ALTERNATIVAS = ("rapida", "sin_peaje")
ENCABEZADO_FUENTES = ["dato", "fuente", "URL", "fecha de consulta", "notas"]  # Spec §5.3

RADIO_TIERRA_KM = 6371.0088  # radio medio (IUGG)
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FECHA_INICIAL = re.compile(r"\d{4}-\d{2}-\d{2}")
TODO = re.compile(r"\bTODO\b")
URL_RE = re.compile(r"https?://[^\s<>)`;]+")
VIGENCIA_RE = re.compile(r"desde (\d{4}-\d{2}-\d{2})(?: hasta (\d{4}-\d{2}-\d{2})| sin fecha de fin)")
PREFIJO_VIGENCIAS = "**Vigencia de las tarifas"
RANGO_RE = re.compile(r"entre las (\d{2}:\d{2}) y las (\d{2}:\d{2}) UTC")


def _hoy_utc() -> dt.date:
    """Cota superior de las fechas de consulta. Las fechas del equipo son locales (UTC−5 y UTC−3, siempre detrás o
    igual que UTC), así que ninguna válida supera la fecha UTC de hoy; usar la hora local daría falsos fallos."""
    return dt.datetime.now(dt.timezone.utc).date()


def _fecha_iso(texto: str) -> dt.date | None:
    if not ISO.match(texto):
        return None
    try:
        return dt.date.fromisoformat(texto)
    except ValueError:
        return None


def _fecha_inicial(celda: str) -> dt.date | None:
    """Fecha ISO con la que empieza una celda de `fecha de consulta` (puede llevar hora o texto después)."""
    m = FECHA_INICIAL.match(celda)
    return _fecha_iso(m.group(0)) if m else None


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def _id_en(ident: str, texto: str) -> bool:
    """El id aparece como palabra completa (`R2-01` no cuenta dentro de `R2-011` ni de `XR2-01`)."""
    return re.search(rf"(?<![\w-]){re.escape(ident)}(?![\w-])", texto) is not None


def _sin_tarifa_junto_al_id(ident: str, texto: str, ventana: int = 120) -> bool:
    """'sin tarifa' a menos de `ventana` caracteres de una aparición del id (misma frase, no cualquier parte de la
    fila): así 'AP-51/AP-61: sin tarifa general' no documenta a un id lejano de la misma fila."""
    for m in re.finditer(rf"(?<![\w-]){re.escape(ident)}(?![\w-])", texto):
        if "sin tarifa" in texto[max(0, m.start() - ventana):m.end() + ventana].lower():
            return True
    return False


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Las pruebas no usan internet (CLAUDE.md): cualquier intento de conexión falla de forma explícita."""

    def _bloqueado(*_a, **_k):
        raise RuntimeError("test_data_integrity no puede abrir sockets")

    monkeypatch.setattr(socket.socket, "connect", _bloqueado)
    monkeypatch.setattr(socket, "create_connection", _bloqueado)
    monkeypatch.setattr(socket, "getaddrinfo", _bloqueado)


# --- Carga -------------------------------------------------------------------------------------------------------


def _leer_csv(nombre: str) -> list[dict[str, str]]:
    with (PROC / nombre).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def ciudades() -> list[dict[str, str]]:
    return _leer_csv("cities.csv")


@pytest.fixture(scope="module")
def rutas() -> list[dict[str, str]]:
    return _leer_csv("rutas.csv")


@pytest.fixture(scope="module")
def tramos() -> list[dict[str, str]]:
    return _leer_csv("peajes_tramos.csv")


@pytest.fixture(scope="module")
def resumen() -> dict:
    return json.loads((PROC / "rutas_resumen.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def combustible() -> dict:
    return json.loads((PROC / "combustible.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def vehiculo() -> dict:
    return yaml.safe_load((PROC / "vehiculo.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def texto_fuentes() -> str:
    return FUENTES_MD.read_text(encoding="utf-8")


# --- fuentes.md: tablas ------------------------------------------------------------------------------------------


def filas_de_tablas(texto: str) -> tuple[list[list[str]], list[str]]:
    """Devuelve (filas de datos con sus 5 celdas, problemas). Una tabla es un bloque de líneas consecutivas que
    empiezan por `|`; su primera línea debe ser el encabezado exigido y el separador `|---|` se salta. Las celdas no
    pueden contener `|`: una celda con `|` aparece como columna de más."""
    filas: list[list[str]] = []
    problemas: list[str] = []
    en_tabla = False
    for n, linea in enumerate(texto.splitlines(), start=1):
        if not linea.startswith("|"):
            en_tabla = False
            continue
        celdas = _celdas(linea)
        if not en_tabla:
            en_tabla = True
            if celdas != ENCABEZADO_FUENTES:
                problemas.append(f"línea {n}: la tabla no empieza con el encabezado exigido")
            continue
        if all(re.fullmatch(r":?-{3,}:?", c) for c in celdas):
            continue
        if len(celdas) != len(ENCABEZADO_FUENTES):
            problemas.append(f"línea {n}: {len(celdas)} columnas en vez de {len(ENCABEZADO_FUENTES)}")
            continue
        filas.append(celdas)
    return filas, problemas


def problemas_fuentes_md(texto: str, hoy: dt.date) -> list[str]:
    """Tablas bien formadas, fecha de consulta válida y no futura, URL presente, sin TODO pendiente."""
    filas, problemas = filas_de_tablas(texto)
    if not filas:
        problemas.append("no hay filas de datos")
    for dato, fuente, url, fecha, _notas in filas:
        etiqueta = dato[:60]
        if not dato or not fuente:
            problemas.append(f"{etiqueta}: dato o fuente vacíos")
        d = _fecha_inicial(fecha)
        if d is None:
            problemas.append(f"{etiqueta}: fecha de consulta inválida: {fecha!r}")
        elif d > hoy:
            problemas.append(f"{etiqueta}: fecha de consulta posterior a hoy: {fecha!r}")
        if not (URL_RE.search(url) or url.startswith("—")):
            problemas.append(f"{etiqueta}: la columna URL no tiene URL ni es '—'")
    problemas += [f"línea {n}: TODO pendiente" for n, linea in enumerate(texto.splitlines(), start=1)
                  if TODO.search(linea)]
    return problemas


def test_fuentes_md_tablas_bien_formadas_con_fecha_y_sin_todo(texto_fuentes):
    assert problemas_fuentes_md(texto_fuentes, _hoy_utc()) == []


def test_fuentes_md_documenta_las_dos_zonas_horarias(texto_fuentes):
    """Decisión de Jose Miguel (12-oct): UTC−3 (equipo de Camila, T2.2/T2.0) y UTC−5 (resto)."""
    cabecera = texto_fuentes.split("\n| dato |", 1)[0]
    assert "UTC−5" in cabecera and "UTC−3" in cabecera


def urls_de_la_columna(celda: str) -> set[str]:
    """URL de una celda de la columna URL, como tokens completos (no por subcadena)."""
    return set(URL_RE.findall(celda))


def fechas_de_la_url(texto: str, url: str) -> set[str]:
    """Fechas de consulta (parte ISO inicial) de las filas cuya columna URL contiene exactamente `url`."""
    filas, _ = filas_de_tablas(texto)
    return {d.isoformat() for f in filas if url in urls_de_la_columna(f[2]) and (d := _fecha_inicial(f[3]))}


def problemas_url_con_fecha(texto: str, url: str, fecha: str, quien: str) -> list[str]:
    """La URL consta en la columna URL de alguna fila de fuentes.md y esa fila lleva la misma fecha de consulta."""
    fechas = fechas_de_la_url(texto, url)
    if not fechas:
        return [f"{quien}: la URL {url} no está en la columna URL de data/fuentes.md"]
    if fecha not in fechas:
        return [f"{quien}: fecha {fecha} distinta de la de fuentes.md {sorted(fechas)} para {url}"]
    return []


# --- 1. Correspondencia entre archivos ---------------------------------------------------------------------------


def test_los_ids_de_rutas_son_los_47_de_cities(rutas, ciudades):
    ids = {int(f["i"]) for f in rutas} | {int(f["j"]) for f in rutas}
    assert ids == {int(f["id"]) for f in ciudades} == set(range(N_CIUDADES))


def coordenadas_repetidas(filas: list[dict[str, str]]) -> list[str]:
    vistas: dict[tuple[str, str], str] = {}
    problemas = []
    for f in filas:
        clave = (f["lat"], f["lon"])
        if clave in vistas:
            problemas.append(f"{f['capital']} y {vistas[clave]} tienen las mismas coordenadas {clave}")
        vistas.setdefault(clave, f["capital"])
    return problemas


def test_ninguna_capital_comparte_coordenadas_con_otra(ciudades):
    assert coordenadas_repetidas(ciudades) == []


# --- 2. Matrices de rutas ----------------------------------------------------------------------------------------


def matriz(filas: list[dict[str, str]], columna: str, alternativa: str, n: int = N_CIUDADES) -> np.ndarray:
    """Matriz n×n de `columna` para una alternativa.

    SIMETRÍA Y DIAGONAL SON POR CONSTRUCCIÓN, no una propiedad medida: rutas.csv guarda cada par UNA vez (i < j) y
    Spec §7.2 Bloque 2 "asume c_ij = c_ji", así que la matriz se arma espejando y la diagonal se fija en 0 (distancia,
    tiempo y peaje de una ciudad a sí misma). La asimetría REAL de OSRM (j→i frente a i→j) no está en rutas.csv: se mide
    en rutas_resumen.json y la comprueba `problemas_asimetria`.
    Lo que sí puede fallar aquí: un hueco queda como NaN, y el espejo no puede sobrescribir una celda ya ocupada
    (ValueError), lo que detecta pares repetidos o dados en los dos sentidos con valores distintos."""
    m = np.full((n, n), np.nan)
    np.fill_diagonal(m, 0.0)
    for f in filas:
        if f["alternativa"] != alternativa:
            continue
        i, j = int(f["i"]), int(f["j"])
        if i == j or not (np.isnan(m[i, j]) and np.isnan(m[j, i])):
            raise ValueError(f"celda ya ocupada o diagonal: {i},{j},{alternativa}")
        m[i, j] = m[j, i] = float(f[columna]) if f[columna] != "" else np.nan
    return m


def problemas_rutas(filas: list[dict[str, str]], n: int = N_CIUDADES) -> list[str]:
    """Matrices completas, finitas y positivas (el peaje, no negativo), con fuente y extracto OSM no posterior al
    corte. No cuenta filas: un par que falte deja un NaN y uno de más queda fuera de orden o repetido."""
    p: list[str] = []
    claves = [(f["i"], f["j"], f["alternativa"]) for f in filas]
    if len(set(claves)) != len(claves):
        p.append("pares (i, j, alternativa) repetidos")
    p += [f"par fuera de orden o de rango: {f['i']},{f['j']}" for f in filas if not 0 <= int(f["i"]) < int(f["j"]) < n]
    for columna, positiva in (("dist_km", True), ("tiempo_h", True), ("peaje_eur", False)):
        for alt in ALTERNATIVAS:
            etiqueta = f"{columna}/{alt}"
            try:
                m = matriz(filas, columna, alt, n)
            except ValueError as e:
                p.append(f"{etiqueta}: el espejo sobrescribiría una celda ({e})")
                continue
            if np.isnan(m).any():
                p.append(f"{etiqueta}: {int(np.isnan(m).sum())} celdas vacías o NaN")
                continue
            if not np.isfinite(m).all():
                p.append(f"{etiqueta}: valores infinitos")
            fuera = m[~np.eye(n, dtype=bool)]
            if positiva and (fuera <= 0).any():
                p.append(f"{etiqueta}: valores no positivos fuera de la diagonal")
            if not positiva and (fuera < 0).any():
                p.append(f"{etiqueta}: valores negativos")
    p += [f"par {f['i']},{f['j']},{f['alternativa']}: sin fuente" for f in filas if not f["fuente"].strip()]
    p += [f"par {f['i']},{f['j']},{f['alternativa']}: extracto OSM posterior al corte o ilegible" for f in filas
          if (d := _fecha_iso(f["fecha_extracto_osm"][:10])) is None or d > dt.date.fromisoformat(CORTE)]
    return p


def test_matrices_47x47_completas_finitas_y_positivas(rutas):
    assert problemas_rutas(rutas) == []


def _haversine_km(a: dict[str, str], b: dict[str, str]) -> float:
    la1, lo1, la2, lo2 = (math.radians(float(v)) for v in (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(h))


def problemas_distancias_fisicas(filas: list[dict[str, str]], ciudades_: list[dict[str, str]]) -> list[str]:
    """Cota física sin tolerancia inventada: una ruta por carretera no puede ser más corta que la distancia
    ortodrómica entre las dos capitales. (Con los datos reales el cociente mínimo es 1,085; se exige >= 1.)"""
    por_id = {int(c["id"]): c for c in ciudades_}
    return [f"par {f['i']},{f['j']},{f['alternativa']}: {f['dist_km']} km < ortodrómica"
            for f in filas if float(f["dist_km"]) < _haversine_km(por_id[int(f["i"])], por_id[int(f["j"])])]


def test_ninguna_ruta_es_mas_corta_que_la_ortodromica(rutas, ciudades):
    assert problemas_distancias_fisicas(rutas, ciudades) == []


def test_rutas_resumen_cuadra_con_rutas_csv(rutas, resumen):
    """Cruce entre archivos (sin cifras fijas: los conteos los comprueban test_rutas y test_asignar_peajes)."""
    assert resumen["n_pares"] == len({(f["i"], f["j"]) for f in rutas})
    assert resumen["n_filas"] == len(rutas)
    assert resumen["parcial"] is False
    assert {f["fecha_extracto_osm"] for f in rutas} == {resumen["fecha_extracto_osm"]}
    assert CORTE <= resumen["fecha_consulta_utc"]["min"][:10] <= resumen["fecha_consulta_utc"]["max"][:10]
    assert resumen["fecha_consulta_utc"]["max"][:10] <= _hoy_utc().isoformat()
    crudos = resumen["crudos"].rsplit("/", 1)[-1]
    assert all(crudos in f["fuente"] for f in rutas)


def problemas_asimetria(resumen_: dict, filas: list[dict[str, str]]) -> list[str]:
    """La asimetría medida (20 pares consultados j→i) se compara con rutas.csv, no con lo que el resumen dice de
    sí mismo: cada `*_ij` del detalle debe ser el valor de rutas.csv y los máximos del resumen, los del detalle.

    Tolerancia de simetría: NO se fija un umbral propio. Spec §7.2 Bloque 2 asume c_ij = c_ji y pide REPORTAR la
    diferencia máxima; ese máximo medido (resumen['simetria'][alt]) es la cota de error de la suposición."""
    p: list[str] = []
    s = resumen_["simetria"]
    pares = {tuple(x) for x in s["pares"]}
    if len(pares) != 20:
        p.append(f"{len(pares)} pares de simetría, no 20")
    por_clave = {(int(f["i"]), int(f["j"]), f["alternativa"]): f for f in filas}
    for alt in ALTERNATIVAS:
        detalle = s[alt]["detalle"]
        if {(d["i"], d["j"]) for d in detalle} != pares:
            p.append(f"{alt}: el detalle no cubre los mismos pares")
        for d in detalle:
            f = por_clave[(d["i"], d["j"], alt)]
            # abs_tol = resolución del CSV: dist_km se guarda con 4 decimales y tiempo_h con 6 (el resumen guarda el
            # valor sin redondear). No son umbrales de simetría.
            if not (math.isclose(d["dist_km_ij"], float(f["dist_km"]), abs_tol=1e-4)
                    and math.isclose(d["tiempo_h_ij"], float(f["tiempo_h"]), abs_tol=1e-6)):
                p.append(f"{alt} {d['i']},{d['j']}: *_ij del resumen distinto de rutas.csv")
            if not (d["dist_km_ji"] > 0 and d["tiempo_h_ji"] > 0):
                p.append(f"{alt} {d['i']},{d['j']}: medida j→i no positiva")
        recalculado = {
            "max_abs_km": max(abs(d["dist_km_ji"] - d["dist_km_ij"]) for d in detalle),
            "max_abs_h": max(abs(d["tiempo_h_ji"] - d["tiempo_h_ij"]) for d in detalle),
            "max_rel_km": max(abs(d["dist_km_ji"] - d["dist_km_ij"]) / d["dist_km_ij"] for d in detalle),
            "max_rel_h": max(abs(d["tiempo_h_ji"] - d["tiempo_h_ij"]) / d["tiempo_h_ij"] for d in detalle),
        }
        for clave, valor in recalculado.items():
            # rel_tol/abs_tol solo absorben el error de coma flotante de recalcular el máximo (ambos salen de los
            # mismos datos sin redondear); no son un umbral de asimetría.
            if not math.isclose(s[alt][clave], valor, rel_tol=1e-9, abs_tol=1e-12):
                p.append(f"{alt}.{clave}: resumen {s[alt][clave]} distinto del recalculado {valor}")
    return p


def test_asimetria_medida_es_la_de_rutas_csv_y_la_cota_del_resumen(rutas, resumen):
    assert problemas_asimetria(resumen, rutas) == []


# --- 3. Peajes: fuentes.md frente a peajes_tramos.csv ------------------------------------------------------------


def vigencias_documentadas(texto: str) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Vigencia por id (desde, hasta; hasta = "" si 'sin fecha de fin') leída de la fila "Vigencia de las tarifas" de
    fuentes.md. Cada segmento (separado por <br>) es `operador: `id`, `id`: desde AAAA-MM-DD hasta AAAA-MM-DD`."""
    filas, _ = filas_de_tablas(texto)
    candidatas = [f for f in filas if f[0].startswith(PREFIJO_VIGENCIAS)]
    if len(candidatas) != 1:
        return {}, [f"debe haber una única fila 'Vigencia de las tarifas' en fuentes.md y hay {len(candidatas)}"]
    docs: dict[str, tuple[str, str]] = {}
    problemas: list[str] = []
    for segmento in candidatas[0][4].split("<br>"):
        m = VIGENCIA_RE.search(segmento)
        if not m:
            continue
        for ident in re.findall(r"`([^`]+)`", segmento[:m.start()]):
            if ident in docs:
                problemas.append(f"{ident}: vigencia documentada dos veces")
            docs[ident] = (m.group(1), m.group(2) or "")
    return docs, problemas


def problemas_tramos_vs_fuentes(filas: list[dict[str, str]], texto: str) -> list[str]:
    """Lo que une peajes_tramos.csv con fuentes.md (el contenido propio del CSV lo cubre test_peajes_tramos.py):
    1) la fuente_url consta en la columna URL de una fila con la misma fecha de consulta;
    2) la vigencia de cada fila es la documentada en su segmento de la fila de vigencias (y no hay ids de más);
    3) toda fila con tarifa TODO tiene, en una fila de fuentes.md DISTINTA de la de vigencias (que lista todos los ids),
       su id con la expresión "sin tarifa" a menos de 120 caracteres (por qué falta la tarifa)."""
    p: list[str] = []
    filas_md = [r for r in filas_de_tablas(texto)[0] if not r[0].startswith(PREFIJO_VIGENCIAS)]
    for f in filas:
        p += problemas_url_con_fecha(texto, f["fuente_url"], f["fecha_consulta"], f["id"])
        documentada = any(_sin_tarifa_junto_al_id(f["id"], " ".join(r)) for r in filas_md)
        if f["tarifa_ligeros_eur"] == "TODO(dato-faltante)" and not documentada:
            p.append(f"{f['id']}: tarifa TODO sin documentar ('sin tarifa' junto al id) fuera de la fila de vigencias")
    docs, problemas = vigencias_documentadas(texto)
    p += problemas
    for f in filas:
        esperada = (f["vigente_desde"], f["vigente_hasta"])
        if f["id"] not in docs:
            p.append(f"{f['id']}: sin vigencia documentada en fuentes.md")
        elif docs[f["id"]] != esperada:
            p.append(f"{f['id']}: vigencia {esperada} del CSV distinta de la de fuentes.md {docs[f['id']]}")
    p += [f"{ident}: vigencia documentada de una fila que no existe en el CSV" for ident in docs
          if ident not in {f["id"] for f in filas}]
    return p


def test_peajes_fuente_url_con_su_fecha_y_vigencias_coinciden_con_fuentes_md(tramos, texto_fuentes):
    assert problemas_tramos_vs_fuentes(tramos, texto_fuentes) == []


# --- 4. Combustible y vehículo -----------------------------------------------------------------------------------


def problemas_combustible(c: dict, texto: str, raiz: Path) -> list[str]:
    p: list[str] = []
    d = _fecha_iso(str(c.get("fecha", "")))
    if d is None:
        p.append("combustible.json: fecha inválida")
    elif d.isoformat() != CORTE:
        p.append(f"combustible.json: fecha {d} distinta de la fecha de corte {CORTE}")
    if not str(c.get("fuente_url", "")).startswith("https://"):
        p.append("combustible.json: sin fuente_url")
    else:
        # La fecha de consulta (descarga) es posterior o igual al precio del día; basta que la fila exista y que
        # su fecha no sea anterior a la del dato.
        fechas = fechas_de_la_url(texto, c["fuente_url"])
        if not fechas:
            p.append("combustible.json: fuente_url no está en la columna URL de fuentes.md")
        elif min(fechas) < str(c.get("fecha")):
            p.append(f"combustible.json: consulta {sorted(fechas)} anterior al día del precio {c['fecha']}")
    raw = str(c.get("archivo_raw", ""))
    if not raw or not (raiz / raw).is_file():
        p.append(f"combustible.json: archivo_raw inexistente: {raw!r}")
    elif raw not in texto:
        p.append("combustible.json: archivo_raw no citado en fuentes.md")
    for clave in ("precio_medio_eur_l", "precio_mediano_eur_l"):
        v = c.get(clave)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0:
            p.append(f"combustible.json: {clave} no es un número positivo")
    return p


def test_combustible_tiene_fuente_fecha_y_esta_en_fuentes_md(combustible, texto_fuentes):
    assert problemas_combustible(combustible, texto_fuentes, RAIZ) == []


def problemas_vehiculo(v: dict, texto: str) -> list[str]:
    p: list[str] = []
    d = _fecha_iso(str(v.get("fecha_consulta", "")))
    if d is None or d > _hoy_utc():
        p.append("vehiculo.yaml: fecha_consulta inválida o futura")
    for clave in ("fuente_url", "respaldo_url"):
        url = str(v.get(clave, ""))
        if not url.startswith("https://"):
            p.append(f"vehiculo.yaml: {clave} ausente")
        else:
            p += problemas_url_con_fecha(texto, url, str(v.get("fecha_consulta")), f"vehiculo.yaml {clave}")
    return p


def test_vehiculo_tiene_fuente_fecha_y_esta_en_fuentes_md(vehiculo, texto_fuentes):
    assert problemas_vehiculo(vehiculo, texto_fuentes) == []


# --- Crudos descargados frente a fuentes.md (sentido inverso al de test_peajes_tramos.py) ------------------------


def urls_de_cabeceras(texto: str) -> set[str]:
    """URL de cada descarga registrada: líneas `URL: <url>` (peajes) o `### <archivo> <- <url>` (vehículo)."""
    urls = {m.group(1).strip() for m in re.finditer(r"(?m)^URL: (\S+)\s*$", texto)}
    return urls | {m.group(1).strip() for m in re.finditer(r"(?m)^### \S+ <- (\S+)\s*$", texto)}


def problemas_descargas_vs_fuentes(urls: set[str], texto_md: str) -> list[str]:
    """Cada URL descargada debe estar en la columna URL de alguna fila de fuentes.md (no basta mencionarla en notas)."""
    filas, _ = filas_de_tablas(texto_md)
    citadas = set().union(*(urls_de_la_columna(f[2]) for f in filas)) if filas else set()
    return [f"descarga sin fila en fuentes.md: {u}" for u in sorted(urls - citadas)]


CABECERAS = sorted(RAW.glob("*/cabeceras_http.txt"))


def test_hay_registros_de_cabeceras_que_comprobar():
    """Si la carpeta cambiara de nombre, las pruebas parametrizadas de abajo no se ejecutarían en silencio."""
    assert CABECERAS


@pytest.mark.parametrize("ruta", CABECERAS, ids=lambda r: r.parent.name)
def test_toda_descarga_registrada_tiene_su_url_en_fuentes_md(ruta, texto_fuentes):
    urls = urls_de_cabeceras(ruta.read_text(encoding="utf-8", errors="replace"))
    assert urls, f"{ruta.parent.name}: ninguna URL reconocida (¿cambió el formato de cabeceras_http.txt?)"
    assert problemas_descargas_vs_fuentes(urls, texto_fuentes) == []


def horas_de_captura(texto: str) -> list[str]:
    """Líneas 'Fecha local de la captura (UTC): <ISO>' de cada descarga (la `Date` de CloudFront es la de la caché)."""
    bloques = re.split(r"(?m)^=== ", texto)[1:]
    capturas = [re.search(r"Fecha local de la captura \(UTC\): (\S+)", b) for b in bloques]
    if not bloques or not all(capturas):
        return []
    return [m.group(1) for m in capturas]


def problemas_rango_citado(horas: list[str], texto_md: str) -> list[str]:
    """El rango 'entre las HH:MM y las HH:MM UTC' de fuentes.md es el medido redondeado hacia fuera: el inicio se
    trunca al minuto y el final se sube al minuto siguiente. Es decir, 0 <= medida_min - inicio < 1 min y
    0 <= fin - medida_max < 1 min."""
    if not horas:
        return ["no se pudo leer la hora de captura de todas las descargas"]
    m = RANGO_RE.search(texto_md)
    if not m:
        return ["fuentes.md no cita el rango horario de las capturas ('entre las HH:MM y las HH:MM UTC')"]
    dias = {h[:10] for h in horas}
    if len(dias) != 1:
        return [f"las capturas son de varios días: {sorted(dias)}"]
    dia = dias.pop()
    cita_ini, cita_fin = (dt.datetime.fromisoformat(f"{dia}T{x}:00") for x in m.groups())
    medidas = [dt.datetime.fromisoformat(h.rstrip("Z")) for h in horas]
    p: list[str] = []
    minuto = dt.timedelta(minutes=1)
    medido = f"({min(medidas)} a {max(medidas)})"
    if min(medidas) < cita_ini or max(medidas) > cita_fin:
        p.append(f"el rango citado {m.group(0)!r} no contiene las capturas {medido}")
    if min(medidas) - cita_ini >= minuto or cita_fin - max(medidas) >= minuto:
        p.append(f"el rango citado {m.group(0)!r} se aleja un minuto o más de lo medido {medido}")
    if dia not in texto_md:
        p.append(f"fuentes.md no cita el día de las capturas ({dia})")
    return p


CABECERAS_CON_CAPTURA = [r for r in CABECERAS
                         if "Fecha local de la captura" in r.read_text(encoding="utf-8", errors="replace")]


def test_hay_cabeceras_con_hora_de_captura_que_comprobar():
    """Si cambiara el formato de la línea, la prueba parametrizada de abajo se omitiría en silencio."""
    assert CABECERAS_CON_CAPTURA
    assert all(horas_de_captura(r.read_text(encoding="utf-8", errors="replace")) for r in CABECERAS_CON_CAPTURA)


@pytest.mark.parametrize("ruta", CABECERAS_CON_CAPTURA, ids=lambda r: r.parent.name)
def test_el_rango_horario_citado_en_fuentes_md_es_el_de_las_capturas(ruta, texto_fuentes):
    horas = horas_de_captura(ruta.read_text(encoding="utf-8", errors="replace"))
    assert problemas_rango_citado(horas, texto_fuentes) == []


# --- Sin red -----------------------------------------------------------------------------------------------------


def test_la_prueba_no_puede_abrir_sockets():
    with pytest.raises(RuntimeError, match="sockets"):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(RuntimeError, match="sockets"):
        socket.socket().connect(("127.0.0.1", 9))


# --- Pruebas de mutación (copias rotas en memoria; los datos reales no se tocan) ---------------------------------


def _copia(filas):
    return [dict(f) for f in filas]


def _contiene(problemas: list[str], fragmento: str) -> bool:
    return any(fragmento in x for x in problemas)


def test_mutacion_coordenadas_repetidas(ciudades):
    m = _copia(ciudades)
    m[7]["lat"], m[7]["lon"] = m[2]["lat"], m[2]["lon"]
    assert _contiene(coordenadas_repetidas(m), "mismas coordenadas")


@pytest.mark.parametrize("cambio, fragmento", [
    (lambda fs: fs.pop(10), "celdas vacías"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "dist_km": ""}), "celdas vacías"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "tiempo_h": "nan"}), "celdas vacías o NaN"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "dist_km": "inf"}), "infinitos"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "dist_km": "0"}), "no positivos"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "dist_km": "-3"}), "no positivos"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "peaje_eur": "-0.5"}), "negativos"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "peaje_eur": ""}), "celdas vacías"),
    (lambda fs: fs.append(dict(fs[0])), "repetidos"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "i": "40", "j": "3"}), "fuera de orden"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "fuente": ""}), "sin fuente"),
    (lambda fs: fs.__setitem__(4, {**fs[4], "fecha_extracto_osm": "2026-10-08T20:21:06Z"}), "posterior al corte"),
])
def test_mutacion_rutas(rutas, cambio, fragmento):
    m = _copia(rutas)
    cambio(m)
    assert _contiene(problemas_rutas(m), fragmento)


def test_mutacion_rutas_par_en_los_dos_sentidos_o_en_la_diagonal(rutas):
    """La simetría y la diagonal son por construcción; lo que puede fallar es que el espejo sobrescriba una celda:
    un par dado también como j,i con otro valor, o una fila i == j."""
    inverso = {**rutas[0], "i": rutas[0]["j"], "j": rutas[0]["i"], "dist_km": "1.0"}
    assert _contiene(problemas_rutas(_copia(rutas) + [inverso]), "sobrescribiría")
    diagonal = {**rutas[0], "j": rutas[0]["i"]}
    assert _contiene(problemas_rutas(_copia(rutas) + [diagonal]), "sobrescribiría")
    m = matriz(rutas, "dist_km", "rapida")
    assert m.shape == (N_CIUDADES, N_CIUDADES) and np.diag(m).tolist() == [0.0] * N_CIUDADES
    assert np.array_equal(m, m.T)  # por construcción; la asimetría real la mide problemas_asimetria


def test_mutacion_rutas_fila_i_igual_j_fuera_de_orden():
    """Una fila i == j también la rechaza el orden i < j."""
    filas = [{"i": "0", "j": "0", "alternativa": "rapida", "dist_km": "5", "tiempo_h": "1", "km_peaje": "0",
              "peaje_eur": "0", "vias_peaje": "", "fuente": "x", "fecha_extracto_osm": "2026-10-01T20:22:06Z"}]
    assert _contiene(problemas_rutas(filas, n=2), "fuera de orden")


def test_mutacion_distancia_menor_que_la_ortodromica(rutas, ciudades):
    m = _copia(rutas)
    m[0]["dist_km"] = "1.0"
    assert _contiene(problemas_distancias_fisicas(m, ciudades), "< ortodrómica")


def test_mutacion_asimetria(rutas, resumen):
    r = json.loads(json.dumps(resumen))
    r["simetria"]["rapida"]["max_rel_km"] = 0.01
    assert _contiene(problemas_asimetria(r, rutas), "rapida.max_rel_km")
    r = json.loads(json.dumps(resumen))
    r["simetria"]["rapida"]["detalle"][0]["dist_km_ij"] += 1.0
    assert _contiene(problemas_asimetria(r, rutas), "distinto de rutas.csv")
    r = json.loads(json.dumps(resumen))
    r["simetria"]["pares"].pop()
    assert _contiene(problemas_asimetria(r, rutas), "pares de simetría")


@pytest.mark.parametrize("cambio, fragmento", [
    (lambda t: t.replace("| 2026-10-12 |", "| 2999-01-01 |", 1), "posterior a hoy"),
    (lambda t: t.replace("| 2026-10-12 |", "| ayer |", 1), "fecha de consulta inválida"),
    (lambda t: t.replace("| 2026-10-12 |", "| 2026-13-45 |", 1), "fecha de consulta inválida"),
    (lambda t: t + "\n\n| dato | fuente | URL | fecha de consulta | notas |\n|---|---|---|---|---|\n"
     "| solo | cuatro | celdas |\n", "columnas"),
    (lambda t: t + "\n\n| dato | fuente | URL | fecha de consulta | notas |\n|---|---|---|---|---|\n"
     "| a | b | c | d | e | f |\n", "columnas"),
    (lambda t: t + "\n\n| dato | fuente | URL | fecha de consulta | notas |\n|---|---|---|---|---|\n"
     "| x | y | texto sin url | 2026-10-12 | n |\n", "no tiene URL"),
    (lambda t: t + "\nTODO(dato-faltante) pendiente\n", "TODO pendiente"),
    (lambda t: t + "\nTODO: revisar\n", "TODO pendiente"),
    (lambda t: t + "\n\n| dato | fuente |\n|---|---|\n| a | b |\n", "no empieza con el encabezado"),
])
def test_mutacion_fuentes_md(texto_fuentes, cambio, fragmento):
    mutado = cambio(texto_fuentes)
    assert mutado != texto_fuentes
    assert _contiene(problemas_fuentes_md(mutado, _hoy_utc()), fragmento)


def test_mutacion_fuentes_md_sin_filas():
    assert _contiene(problemas_fuentes_md("# vacío\n", _hoy_utc()), "no hay filas")


def test_mutacion_id_con_limites_de_palabra():
    assert _id_en("R2-01", "filas R2-01..06") and _id_en("R2-01", "`R2-01`")
    assert not _id_en("R2-01", "R2-011") and not _id_en("R2-01", "XR2-01") and not _id_en("R2-01", "R2-01-b")


def test_mutacion_url_por_prefijo_no_cuenta(texto_fuentes):
    """Una URL que es prefijo de otra más larga de la tabla no debe darse por citada."""
    larga = next(u for f in filas_de_tablas(texto_fuentes)[0] for u in urls_de_la_columna(f[2]) if len(u) > 60)
    assert fechas_de_la_url(texto_fuentes, larga) and not fechas_de_la_url(texto_fuentes, larga[:-4])


def test_mutacion_tramos_vs_fuentes(tramos, texto_fuentes):
    m = _copia(tramos)
    m[0]["fuente_url"] = "https://ejemplo.invalid/no-citada.pdf"
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), "no está en la columna URL")
    m = _copia(tramos)
    m[0]["fecha_consulta"] = "2026-10-11"  # la fila de fuentes.md dice 2026-10-12
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), "distinta de la de fuentes.md")
    # Fila TODO que fuentes.md no menciona por id (ni como subcadena de otro id).
    m = _copia(tramos)
    m[0].update(id="ZZ-99", tarifa_ligeros_eur="TODO(dato-faltante)")
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), "tarifa TODO sin documentar")
    # Id que SÍ está en fuentes.md (en la fila de vigencias) pero sin documentación propia de la tarifa.
    m = _copia(tramos)
    sin_doc = next(f for f in m if f["id"] == "AP68-01")
    assert _id_en("AP68-01", texto_fuentes)
    sin_doc["tarifa_ligeros_eur"] = "TODO(dato-faltante)"
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), "AP68-01: tarifa TODO sin documentar")


def test_mutacion_vigencias(tramos, texto_fuentes):
    """2026-01-01 y 2026-11-10 SÍ existen en fuentes.md (otras filas), pero no en el segmento de esa fila."""
    assert "2026-01-01" in texto_fuentes and "2026-11-10" in texto_fuentes
    m = _copia(tramos)
    m[0]["vigente_hasta"] = "2026-01-01"
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), f"{m[0]['id']}: vigencia")
    m = _copia(tramos)
    ultimo = next(f for f in m if f["vigente_hasta"] == "")
    ultimo["vigente_hasta"] = "2026-11-10"
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes), f"{ultimo['id']}: vigencia")
    m = _copia(tramos)
    nuevo = {**m[0], "id": "ZZ-99"}
    assert _contiene(problemas_tramos_vs_fuentes(m + [nuevo], texto_fuentes), "ZZ-99: sin vigencia documentada")
    assert _contiene(problemas_tramos_vs_fuentes(m[1:], texto_fuentes), "no existe en el CSV")
    assert _contiene(problemas_tramos_vs_fuentes(m, texto_fuentes.replace("**Vigencia de las tarifas", "**Otra fila")),
                     "única fila 'Vigencia de las tarifas'")


def test_mutacion_combustible(combustible, texto_fuentes):
    assert problemas_combustible(combustible, texto_fuentes, RAIZ) == []
    assert _contiene(problemas_combustible({**combustible, "fecha": "2026-09-30"}, texto_fuentes, RAIZ),
                     "fecha de corte")
    assert _contiene(problemas_combustible({**combustible, "fecha": "ayer"}, texto_fuentes, RAIZ), "fecha inválida")
    assert _contiene(problemas_combustible({**combustible, "fuente_url": ""}, texto_fuentes, RAIZ), "sin fuente_url")
    assert _contiene(problemas_combustible({**combustible, "fuente_url": "https://ejemplo.invalid/x"}, texto_fuentes,
                                           RAIZ), "no está en la columna URL")
    assert _contiene(problemas_combustible({**combustible, "archivo_raw": "data/raw/no_existe.json.gz"}, texto_fuentes,
                                           RAIZ), "inexistente")
    assert _contiene(problemas_combustible({**combustible, "precio_medio_eur_l": float("nan")}, texto_fuentes, RAIZ),
                     "precio_medio_eur_l")
    assert _contiene(problemas_combustible({**combustible, "precio_mediano_eur_l": -1.0}, texto_fuentes, RAIZ),
                     "precio_mediano_eur_l")


def test_mutacion_vehiculo(vehiculo, texto_fuentes):
    assert _contiene(problemas_vehiculo({**vehiculo, "fecha_consulta": "2999-01-01"}, texto_fuentes), "futura")
    assert _contiene(problemas_vehiculo({**vehiculo, "fecha_consulta": "2026-10-10"}, texto_fuentes),
                     "distinta de la de fuentes.md")
    assert _contiene(problemas_vehiculo({**vehiculo, "respaldo_url": ""}, texto_fuentes), "respaldo_url ausente")
    assert _contiene(problemas_vehiculo({**vehiculo, "fuente_url": "https://ejemplo.invalid/ficha"}, texto_fuentes),
                     "no está en la columna URL")


def test_mutacion_descargas_vs_fuentes(texto_fuentes):
    """Los dos formatos de cabeceras se leen, y una URL real citada solo en notas (no en la columna URL) no vale."""
    urls = urls_de_cabeceras("=== a.pdf\nURL: https://ejemplo.invalid/a.pdf\n### b.html <- https://ejemplo.invalid/b\n")
    assert urls == {"https://ejemplo.invalid/a.pdf", "https://ejemplo.invalid/b"}
    assert len(problemas_descargas_vs_fuentes(urls, texto_fuentes)) == 2
    filas, _ = filas_de_tablas(texto_fuentes)
    una = sorted(urls_de_la_columna(filas[0][2]))[0]
    assert problemas_descargas_vs_fuentes({una}, texto_fuentes) == []
    nota = "| d | f | — | 2026-10-12 | ver https://ejemplo.invalid/solo-en-notas |"
    texto = f"| dato | fuente | URL | fecha de consulta | notas |\n|---|---|---|---|---|\n{nota}\n"
    assert _contiene(problemas_descargas_vs_fuentes({"https://ejemplo.invalid/solo-en-notas"}, texto), "sin fila")


def test_mutacion_rango_horario_citado():
    horas = ["2026-10-12T06:15:57Z", "2026-10-12T11:03:37Z"]
    ok = "Todas del 2026-10-12, entre las 06:15 y las 11:04 UTC (...)"
    assert problemas_rango_citado(horas, ok) == []
    assert _contiene(problemas_rango_citado(horas, ok.replace("11:04", "11:00")), "no contiene")
    assert _contiene(problemas_rango_citado(horas, ok.replace("06:15", "06:20")), "no contiene")
    assert _contiene(problemas_rango_citado(horas, ok.replace("06:15", "05:00")), "se aleja")
    assert _contiene(problemas_rango_citado(horas, "sin rango"), "no cita el rango")
    assert _contiene(problemas_rango_citado(horas, ok.replace("2026-10-12", "2026-10-11")), "no cita el día")
    assert _contiene(problemas_rango_citado([], ok), "no se pudo leer")
    assert _contiene(problemas_rango_citado(horas + ["2026-10-13T01:00:00Z"], ok), "varios días")


@pytest.mark.parametrize("horas, ok", [
    (["2026-10-12T06:15:00Z", "2026-10-12T11:04:00Z"], True),    # extremos exactos
    (["2026-10-12T06:15:59Z", "2026-10-12T11:03:01Z"], True),    # límites: trunc al inicio, ceil al final
    (["2026-10-12T06:16:00Z", "2026-10-12T11:03:30Z"], False),   # inicio: un minuto o más dentro
    (["2026-10-12T06:14:59Z", "2026-10-12T11:03:30Z"], False),   # inicio: antes de lo citado
    (["2026-10-12T06:15:30Z", "2026-10-12T11:03:00Z"], False),   # final: un minuto exacto de holgura
    (["2026-10-12T06:15:30Z", "2026-10-12T11:04:01Z"], False),   # final: un segundo después de lo citado
])
def test_rango_horario_limites_exactos_de_un_minuto(horas, ok):
    texto = "Todas del 2026-10-12, entre las 06:15 y las 11:04 UTC"
    assert (problemas_rango_citado(horas, texto) == []) is ok
