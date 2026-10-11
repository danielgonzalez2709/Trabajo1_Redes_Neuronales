"""Pruebas de T2.3 (Spec §7.2 Bloque 2, contrato §5.3: rutas.csv, rutas_resumen.json, rutas_pasos_peaje.csv). Sin red.

El servidor OSRM está en otra máquina, así que la descarga se prueba con un doble (`ServidorFalso`) que responde
con las 6 respuestas reales de T2.2 (data/raw/osrm_2026-10-10/) para Madrid–Barcelona, Bilbao–Zaragoza y
A Coruña–Pontevedra, y con respuestas sintéticas mínimas (mismo esquema que OSRM, valores derivados de los índices,
NO son datos reales) para el resto de pares. Solo dos pruebas usan HTTP de verdad, contra un servidor en 127.0.0.1
levantado en un hilo de la propia prueba. Las pruebas que modifican crudos trabajan sobre una copia en tmp_path.
"""

from __future__ import annotations

import csv
import gzip
import http.server
import json
import shutil
import socket
import threading
from pathlib import Path

import pytest

import comun_bloque2 as cb2
import construir_rutas
import descargar_datos

RAIZ = Path(__file__).resolve().parents[1]
CITIES = RAIZ / "data" / "processed" / "cities.csv"
FIXTURES = RAIZ / "data" / "raw" / "osrm_2026-10-10"
DV = "2026-10-01T20:22:06Z"
COLUMNAS = ["i", "j", "alternativa", "dist_km", "tiempo_h", "km_peaje", "peaje_eur", "vias_peaje", "fuente",
            "fecha_extracto_osm"]
COLUMNAS_PASOS = ["i", "j", "alternativa", "paso", "ref", "nombre", "dist_m", "n_intersecciones",
                  "n_intersecciones_toll", "lon_ini", "lat_ini", "lon_fin", "lat_fin"]
CLAVES_RESUMEN = {"fuente", "fecha_extracto_osm", "n_pares", "n_filas", "fecha_consulta_utc", "pares_sin_peaje",
                  "avisos", "control_pasos", "simetria"}  # Spec §5.3
CLAVES_RESUMEN_OPCIONALES = {"generado_por", "crudos", "parcial"}
INTERRUMPIDO = "Interrumpido. Para continuar, relance el MISMO comando (se reanuda)."


def _id(capital: str) -> int:
    with CITIES.open(encoding="utf-8", newline="") as fh:
        return next(int(f["id"]) for f in csv.DictReader(fh) if f["capital"] == capital)


BCN, MAD = _id("Barcelona"), _id("Madrid")
BIO, ZGZ = _id("Bilbao"), _id("Zaragoza")
COR, PON = _id("A Coruña"), _id("Pontevedra")
REALES = {
    frozenset((BCN, MAD)): "madrid_barcelona",
    frozenset((BIO, ZGZ)): "bilbao_zaragoza",
    frozenset((COR, PON)): "a_coruna_pontevedra",
}
# Pares sintéticos: (a + b) impar -> la rápida pasa por 'toll' y sin_peaje es otra ruta; par -> sin peaje.
PAR_SIN_PEAJE_MAS_RAPIDA = (0, 1)  # impar: sin_peaje dura 60 s menos que rapida
PAR_SOLO_DURACION_DISTINTA = (0, 2)  # par (marcado): OSRM da 1 s más en sin_peaje -> aviso, se reutiliza la rapida
PAR_SOLO_DISTANCIA_DISTINTA = (0, 4)  # par (marcado): 1 m más en sin_peaje -> aviso
PAR_SIN_REF = (1, 2)  # impar: el paso con 'toll' no trae `ref` ni `name`
GEOM_SINTETICA = [(-3.0, 40.0), (-2.5, 40.5)]  # (lon, lat) del paso sintético


def _real(nombre: str, alternativa: str) -> dict:
    return json.loads((FIXTURES / f"{nombre}_{alternativa}.json").read_text(encoding="utf-8"))


def _codificar(puntos: list[tuple[float, float]]) -> str:
    """Polyline de Google (precisión 5) de [(lon, lat)]; solo para construir respuestas sintéticas."""
    salida, previo = [], (0, 0)
    for lon, lat in puntos:
        actual = (round(lat * 1e5), round(lon * 1e5))
        for delta in (actual[0] - previo[0], actual[1] - previo[1]):
            v = ~(delta << 1) if delta < 0 else delta << 1
            while v >= 0x20:
                salida.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            salida.append(chr(v + 63))
        previo = actual
    return "".join(salida)


def _sintetica(dist_m: float, dur_s: float, data_version: str = DV, peaje: bool = False, ref: bool = True) -> dict:
    """Respuesta mínima con el esquema de OSRM (doble de prueba; valores no reales): un paso y la llegada."""
    clases = ["toll", "motorway"] if peaje else ["motorway"]
    paso = {"distance": dist_m, "duration": dur_s, "weight": dur_s, "name": "Vía X" if ref else "",
            "mode": "driving", "geometry": _codificar(GEOM_SINTETICA),
            "maneuver": {"type": "depart", "location": list(GEOM_SINTETICA[0])},
            "intersections": [{"location": list(GEOM_SINTETICA[0]), "classes": clases, "out": 0, "entry": [True]},
                              {"location": [-2.75, 40.25], "out": 0, "entry": [True]}]}
    if ref:
        paso["ref"] = "X-1"
    llegada = {"distance": 0.0, "duration": 0.0, "weight": 0.0, "name": "", "mode": "driving",
               "geometry": _codificar(GEOM_SINTETICA[-1:] * 2),
               "maneuver": {"type": "arrive", "location": list(GEOM_SINTETICA[-1])},
               "intersections": [{"location": list(GEOM_SINTETICA[-1]), "in": 0, "entry": [True]}]}
    ruta = {"distance": dist_m, "duration": dur_s, "weight": dur_s, "weight_name": "routability",
            "legs": [{"steps": [paso, llegada], "distance": dist_m, "duration": dur_s, "weight": dur_s,
                      "summary": ""}]}
    return {"code": "Ok", "data_version": data_version, "routes": [ruta], "waypoints": []}


class ServidorFalso:
    """Doble de OSRM: resuelve origen/destino a partir de las coordenadas lon,lat de la URL (si el orden fuera
    lat,lon no encontraría la capital y fallaría) y registra cada URL pedida."""

    def __init__(self, data_version: str = DV, fallos: set | None = None, toll_en_sin_peaje: set | None = None,
                 interrumpir_tras: int | None = None):
        self.urls: list[str] = []
        self.data_version = data_version
        self.fallos = fallos or set()  # {(origen, destino, alternativa)} que responden NoRoute
        self.toll_en_sin_peaje = toll_en_sin_peaje or set()  # {(a, b)} cuya sin_peaje pasa por 'toll'
        self.interrumpir_tras = interrumpir_tras  # Ctrl+C simulado tras N peticiones
        with CITIES.open(encoding="utf-8", newline="") as fh:
            self.por_coord = {f"{float(f['lon']):.6f},{float(f['lat']):.6f}": int(f["id"])
                              for f in csv.DictReader(fh)}

    def __call__(self, url: str) -> dict:
        if self.interrumpir_tras is not None and len(self.urls) >= self.interrumpir_tras:
            raise KeyboardInterrupt
        self.urls.append(url)
        ruta, _, consulta = url.partition("?")
        o_txt, d_txt = ruta.rsplit("/", 1)[1].split(";")
        o, d = self.por_coord[o_txt], self.por_coord[d_txt]
        alt = "sin_peaje" if "exclude=toll" in consulta else "rapida"
        if (o, d, alt) in self.fallos:  # con data_version: el caso que exige mirar `code` para no reutilizarlo
            return {"code": "NoRoute", "message": "Impossible route between points", "data_version": self.data_version}
        nombre = REALES.get(frozenset((o, d)))
        if nombre is not None:
            resp = _real(nombre, alt)
            resp["data_version"] = self.data_version
            return resp
        a, b = min(o, d), max(o, d)
        dist, dur = 100_000.0 + 1000 * a + b, 3600.0 + 10 * a + b
        impar = (a + b) % 2 == 1
        if alt == "sin_peaje" and impar:
            dist, dur = dist + 5000, dur + 600
        if alt == "sin_peaje" and (a, b) == PAR_SIN_PEAJE_MAS_RAPIDA:
            dur = 3600.0 + 10 * a + b - 60
        if alt == "sin_peaje" and (a, b) == PAR_SOLO_DURACION_DISTINTA:
            dur += 1
        if alt == "sin_peaje" and (a, b) == PAR_SOLO_DISTANCIA_DISTINTA:
            dist += 1
        if o > d:  # consulta inversa (simetría): ligeramente distinta
            dist, dur = dist + 100, dur + 36
        peaje = (alt == "rapida" and impar) or (alt == "sin_peaje" and (a, b) in self.toll_en_sin_peaje)
        return _sintetica(dist, dur, self.data_version, peaje=peaje, ref=(a, b) != PAR_SIN_REF)


def _descargar(destino: Path, servidor, limite=None, base="http://127.0.0.1:5001"):
    return descargar_datos.descargar_rutas_osrm(CITIES, destino, base, limite=limite, consultar=servidor)


def _leer_gz(ruta: Path) -> tuple[bytes, dict]:
    contenido = gzip.decompress(ruta.read_bytes())
    return contenido, json.loads(contenido)


def _leer_csv(ruta: Path) -> tuple[list[str], list[dict]]:
    with ruta.open(encoding="utf-8", newline="") as fh:
        cabecera = next(csv.reader(fh))
    with ruta.open(encoding="utf-8", newline="") as fh:
        return cabecera, list(csv.DictReader(fh))


# --------------------------------------------------------------------------------------------- pares


def test_pares_son_1081_con_i_menor_j():
    pares = cb2.pares(47)
    assert len(pares) == 1081 == len(set(pares))
    assert all(0 <= i < j <= 46 for i, j in pares)
    assert pares == sorted(pares)


def test_pares_simetria_son_20_deterministas_y_fijos():
    """np.random.default_rng(0 + 0) (Spec §4.1: base_seed 0, run_id 0). Lista fijada el 2026-10-11 con numpy 2.5.3;
    si cambia, cambió el generador o la regla: los crudos de simetría ya descargados dejarían de cuadrar."""
    p1, p2 = cb2.pares_simetria(47), cb2.pares_simetria(47)
    assert p1 == p2
    assert p1 == [(0, 18), (0, 44), (1, 36), (4, 14), (6, 33), (7, 35), (13, 34), (13, 37), (15, 17), (15, 35),
                  (17, 24), (18, 21), (18, 25), (18, 40), (22, 27), (26, 27), (27, 40), (32, 36), (34, 42), (37, 46)]
    assert set(p1) <= set(cb2.pares(47))


# --------------------------------------------------------------------------------------------- URL


def test_url_lleva_lon_lat_en_orden_origen_destino():
    ciudades = cb2.leer_ciudades(CITIES)
    url = cb2.url_ruta("http://127.0.0.1:5001", ciudades[BCN], ciudades[MAD], "rapida")
    assert url.startswith("http://127.0.0.1:5001/route/v1/driving/2.177440,41.382290;-3.691978,40.419026?")


def test_exclude_toll_solo_en_sin_peaje():
    ciudades = cb2.leer_ciudades(CITIES)
    rapida = cb2.url_ruta("http://h:1", ciudades[0], ciudades[1], "rapida")
    sin_peaje = cb2.url_ruta("http://h:1", ciudades[0], ciudades[1], "sin_peaje")
    assert "exclude" not in rapida
    assert sin_peaje.endswith("&exclude=toll") and sin_peaje.count("exclude") == 1
    assert sin_peaje.removesuffix("&exclude=toll") == rapida
    with pytest.raises(ValueError):
        cb2.url_ruta("http://h:1", ciudades[0], ciudades[1], "otra")


def test_url_pide_pasos_y_geometria_simplificada():
    consulta = cb2.url_ruta("http://h:1/", cb2.leer_ciudades(CITIES)[0], cb2.leer_ciudades(CITIES)[1],
                            "rapida").split("?")[1]
    assert set(consulta.split("&")) == {"alternatives=false", "steps=true", "geometries=polyline",
                                        "overview=simplified"}


def test_leer_ciudades_exige_ids_consecutivos(tmp_path):
    malo = tmp_path / "cities.csv"
    malo.write_text("id,capital,lat,lon\n0,A,40.0,-3.0\n2,B,41.0,2.0\n", encoding="utf-8")
    with pytest.raises(cb2.DatoFaltanteError):
        cb2.leer_ciudades(malo)


# --------------------------------------------------------------------------------------------- validador único


def _crudo_bilbao(alt: str = "rapida", base: str = "http://127.0.0.1:5001") -> tuple[dict, str]:
    ciudades = cb2.leer_ciudades(CITIES)
    url = cb2.url_ruta(base, ciudades[BIO], ciudades[ZGZ], alt)
    crudo = {"url": url, "fecha_consulta_utc": "2026-10-12T00:00:00Z", "origen": BIO, "destino": ZGZ,
             "alternativa": alt, "respuesta": _real("bilbao_zaragoza", alt)}
    return crudo, url


def test_problema_crudo_acepta_un_crudo_real_valido():
    crudo, url = _crudo_bilbao()
    assert cb2.problema_crudo(crudo, url) is None


def test_problema_crudo_compara_ruta_y_consulta_no_el_servidor():
    """Decisión T2.3: cambiar de puerto (--osrm-url) no invalida lo descargado; cambiar la consulta sí."""
    crudo, _ = _crudo_bilbao(base="http://127.0.0.1:5001")
    _, url_otro_puerto = _crudo_bilbao(base="http://localhost:5002/")
    assert cb2.problema_crudo(crudo, url_otro_puerto) is None
    _, url_sin_peaje = _crudo_bilbao("sin_peaje")
    assert "URL" in cb2.problema_crudo(crudo, url_sin_peaje)
    ciudades = cb2.leer_ciudades(CITIES)
    url_otras = cb2.url_ruta("http://127.0.0.1:5001", ciudades[ZGZ], ciudades[BIO], "rapida")
    assert "coordenadas" in cb2.problema_crudo(crudo, url_otras)


@pytest.mark.parametrize("cambio, motivo", [
    (lambda c: c["respuesta"].update(code="NoRoute"), "NoRoute"),
    (lambda c: c["respuesta"].update(data_version="2026-10-08T20:21:06Z"), "data_version"),
    (lambda c: c["respuesta"].pop("data_version"), "data_version"),
    (lambda c: c["respuesta"]["routes"][0]["legs"][0].update(steps=[]), "pasos"),
    (lambda c: c["respuesta"].update(routes=[]), "pasos"),
    (lambda c: c.pop("respuesta"), "estructura"),
    (lambda c: c.pop("fecha_consulta_utc"), "estructura"),
])
def test_problema_crudo_rechaza(cambio, motivo):
    crudo, url = _crudo_bilbao()
    cambio(crudo)
    assert motivo in cb2.problema_crudo(crudo, url)


def test_cargar_crudo_ilegible_o_inexistente(tmp_path):
    crudo, url = _crudo_bilbao()
    archivo = tmp_path / "x.json.gz"
    assert cb2.cargar_crudo(archivo, url)[1] is not None  # no existe
    datos = gzip.compress(json.dumps(crudo).encode())
    archivo.write_bytes(datos[: len(datos) // 2])  # truncado
    leido, motivo = cb2.cargar_crudo(archivo, url)
    assert leido is None and "ilegible" in motivo
    archivo.write_bytes(datos)
    assert cb2.cargar_crudo(archivo, url) == (crudo, None)


# --------------------------------------------------------------------------------------------- descarga


def test_crudo_es_gzip_json_compacto_con_url_fecha_y_respuesta(tmp_path):
    servidor = ServidorFalso()
    _descargar(tmp_path, servidor, limite=1)
    archivo = tmp_path / "rutas" / "00_01_sin_peaje.json.gz"
    contenido, crudo = _leer_gz(archivo)
    assert set(crudo) == {"url", "fecha_consulta_utc", "origen", "destino", "alternativa", "respuesta"}
    assert crudo["url"] in servidor.urls and crudo["url"].endswith("exclude=toll")
    assert (crudo["origen"], crudo["destino"], crudo["alternativa"]) == (0, 1, "sin_peaje")
    assert crudo["respuesta"]["code"] == "Ok"
    assert len(crudo["fecha_consulta_utc"]) == 20 and crudo["fecha_consulta_utc"].endswith("Z")
    assert b"\n" not in contenido and b", " not in contenido and b'": ' not in contenido  # JSON compacto


def test_limite_descarga_solo_los_primeros_pares_y_simetria(tmp_path):
    servidor = ServidorFalso()
    res = _descargar(tmp_path, servidor, limite=3)
    # los 3 primeros pares + el sentido i -> j de los 3 primeros pares de simetría (0-18, 0-44, 1-36)
    assert sorted(p.name.removesuffix(".json.gz") for p in (tmp_path / "rutas").iterdir()) == [
        f"{par}_{alt}" for par in ("00_01", "00_02", "00_03", "00_18", "00_44", "01_36")
        for alt in ("rapida", "sin_peaje")]
    # simetría: los 3 primeros pares de la lista fija, consultados j -> i
    assert sorted(p.name for p in (tmp_path / "simetria").iterdir()) == [
        "18_00_rapida.json.gz", "18_00_sin_peaje.json.gz", "36_01_rapida.json.gz", "36_01_sin_peaje.json.gz",
        "44_00_rapida.json.gz", "44_00_sin_peaje.json.gz"]
    assert len(servidor.urls) == 18 and res.n_descargadas == 18 and res.n_reutilizadas == 0 and not res.fallos
    assert res.n_pares == res.pares_ok == 6


def test_no_escribe_registro_jsonl(tmp_path):
    _descargar(tmp_path, ServidorFalso(), limite=1)
    assert not list(tmp_path.glob("*.jsonl"))


def test_reanudacion_no_repite_peticiones_validas(tmp_path):
    _descargar(tmp_path, ServidorFalso(), limite=2)
    segundo = ServidorFalso()
    res = _descargar(tmp_path, segundo, limite=3)
    assert len(segundo.urls) == 6  # solo el par 0-3 y el 3.er par de simetría (1-36 y 36-1)
    assert res.n_reutilizadas == 12 and res.n_descargadas == 6


def test_reanudacion_repite_crudos_corruptos_o_fallidos(tmp_path):
    _descargar(tmp_path, ServidorFalso(fallos={(0, 1, "rapida")}), limite=1)
    (tmp_path / "rutas" / "00_01_sin_peaje.json.gz").write_bytes(b"cortado a medias")
    segundo = ServidorFalso()
    res = _descargar(tmp_path, segundo, limite=1)
    assert sorted(u.endswith("exclude=toll") for u in segundo.urls) == [False, True]
    assert not res.fallos
    assert _leer_gz(tmp_path / "rutas" / "00_01_rapida.json.gz")[1]["respuesta"]["code"] == "Ok"


def test_reanudacion_tras_aborto_a_mitad(tmp_path):
    """Ctrl+C tras 7 peticiones; luego un crudo truncado y un .tmp suelto: ninguno de los dos cuenta como hecho."""
    with pytest.raises(KeyboardInterrupt):
        _descargar(tmp_path, ServidorFalso(interrumpir_tras=7), limite=3)
    hechos = sorted((tmp_path / "rutas").glob("*.json.gz"))
    assert len(hechos) == 7 and not list(tmp_path.rglob("*.tmp"))
    hechos[0].write_bytes(hechos[0].read_bytes()[:20])
    (tmp_path / "rutas" / "00_44_rapida.json.gz.tmp").write_bytes(b"escritura cortada")
    segundo = ServidorFalso()
    res = _descargar(tmp_path, segundo, limite=3)
    assert len(segundo.urls) == 18 - 7 + 1 and res.n_reutilizadas == 6 and res.n_descargadas == 12
    assert any(u.split("?")[0].endswith(cb2.leer_ciudades(CITIES)[44].coord_url) and "exclude" not in u
               for u in segundo.urls)


def test_corte_durante_la_escritura_no_deja_un_json_gz_a_medias(tmp_path, monkeypatch):
    def cortar(origen, destino):
        raise KeyboardInterrupt

    monkeypatch.setattr("os.replace", cortar)
    with pytest.raises(KeyboardInterrupt):
        _descargar(tmp_path, ServidorFalso(), limite=1)
    monkeypatch.undo()
    assert not list((tmp_path / "rutas").glob("*.json.gz"))
    assert [p.name for p in (tmp_path / "rutas").iterdir()] == ["00_01_rapida.json.gz.tmp"]
    res = _descargar(tmp_path, ServidorFalso(), limite=1)
    assert res.n_descargadas == res.n_pedidas and not list(tmp_path.rglob("*.tmp"))


def test_cambio_de_puerto_no_invalida_los_crudos(tmp_path):
    _descargar(tmp_path, ServidorFalso(), limite=2)
    segundo = ServidorFalso()
    res = _descargar(tmp_path, segundo, limite=2, base="http://127.0.0.1:5002")
    assert segundo.urls == [] and res.n_reutilizadas == res.n_pedidas


def test_aborta_si_data_version_distinta(tmp_path):
    with pytest.raises(descargar_datos.DataVersionError, match="2026-10-08T20:21:06Z"):
        _descargar(tmp_path, ServidorFalso(data_version="2026-10-08T20:21:06Z"), limite=1)
    assert not list((tmp_path / "rutas").glob("*.gz"))  # no se guarda nada con otra fecha de datos


def test_code_no_ok_se_registra_y_la_corrida_sigue(tmp_path):
    servidor = ServidorFalso(fallos={(0, 2, "sin_peaje")})
    res = _descargar(tmp_path, servidor, limite=3)
    assert len(servidor.urls) == 18  # no se detuvo
    assert [(f["origen"], f["destino"], f["alternativa"], f["code"]) for f in res.fallos] == [
        (0, 2, "sin_peaje", "NoRoute")]
    assert res.pares_ok == res.n_pares - 1


def _main_bloque2(monkeypatch, tmp_path, servidor, *extra):
    monkeypatch.setattr(descargar_datos, "_consultar_osrm", servidor)
    monkeypatch.setattr(descargar_datos, "RAW", tmp_path)
    monkeypatch.setattr(descargar_datos, "CITIES_CSV", CITIES)
    return descargar_datos.main(["--bloque", "2", "--limite", "1", "--fecha", "2026-10-12", *extra])


def test_main_sale_con_codigo_distinto_de_cero_si_hay_fallos(tmp_path, monkeypatch, capsys):
    assert _main_bloque2(monkeypatch, tmp_path, ServidorFalso(fallos={(0, 1, "rapida")})) == 1
    salida = capsys.readouterr().out
    assert "00_01_rapida" in salida and "NoRoute" in salida
    assert (tmp_path / "osrm_2026-10-12" / "rutas" / "00_01_sin_peaje.json.gz").exists()
    assert _main_bloque2(monkeypatch, tmp_path, ServidorFalso()) == 0


def test_main_ctrl_c_mensaje_corto_sin_traceback(tmp_path, monkeypatch, capsys):
    codigo = _main_bloque2(monkeypatch, tmp_path, ServidorFalso(interrumpir_tras=3))
    err = capsys.readouterr().err
    assert codigo != 0
    assert INTERRUMPIDO in err and "Traceback" not in err
    assert len(list((tmp_path / "osrm_2026-10-12" / "rutas").glob("*.json.gz"))) == 3


def test_fecha_obligatoria_con_bloque_2(monkeypatch, capsys):
    monkeypatch.setattr(descargar_datos, "_consultar_osrm", ServidorFalso(interrumpir_tras=0))
    with pytest.raises(SystemExit) as exc:
        descargar_datos.main(["--bloque", "2", "--limite", "1"])
    assert exc.value.code == 2
    assert "--fecha" in capsys.readouterr().err


def test_bloque_1_avisa_si_recibe_opciones_del_bloque_2(monkeypatch, capsys):
    llamadas = []
    monkeypatch.setattr(descargar_datos, "bloque1", llamadas.append)
    assert descargar_datos.main(["--bloque", "1", "--osrm-url", "http://127.0.0.1:5002", "--limite", "3"]) == 0
    err = capsys.readouterr().err
    assert "--osrm-url" in err and "--limite" in err and len(llamadas) == 1


# --------------------------------------------------------------------------------------------- HTTP real (local)


class _Manejador(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (nombre impuesto por http.server)
        if "fallo" in self.path:
            cuerpo, estado = {"code": "NoRoute", "message": "Impossible route between points"}, 400
        else:
            cuerpo, estado = {"code": "Ok", "data_version": DV, "ruta": self.path}, 200
        datos = json.dumps(cuerpo).encode()
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def log_message(self, *args):  # silencio
        pass


def test_consultar_osrm_devuelve_cuerpo_json_tambien_en_error_http():
    """OSRM responde 400 con JSON {"code": "NoRoute", ...}: es una respuesta, no un fallo de red."""
    servidor = http.server.HTTPServer(("127.0.0.1", 0), _Manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        base = f"http://127.0.0.1:{servidor.server_port}"
        assert descargar_datos._consultar_osrm(f"{base}/route/v1/driving/1,2;3,4?steps=true")["code"] == "Ok"
        assert descargar_datos._consultar_osrm(f"{base}/fallo")["code"] == "NoRoute"
    finally:
        servidor.shutdown()
        servidor.server_close()


def test_consultar_osrm_aborta_si_el_servidor_no_responde():
    with socket.socket() as s:  # puerto libre que nadie escucha
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    with pytest.raises(descargar_datos.ServidorNoDisponibleError, match="osrm.sh arrancar"):
        descargar_datos._consultar_osrm(f"http://127.0.0.1:{puerto}/route", reintentos=1, pausa_s=0)


# --------------------------------------------------------------------------------------------- criterio y polyline


def test_par_sin_peaje_por_clase_toll_de_la_rapida():
    """Spec §7.2 Bloque 2 (v1.5): marcado si ninguna intersección de la rápida tiene 'toll'."""
    principal = lambda nombre, alt: cb2.ruta_principal(_real(nombre, alt))  # noqa: E731
    assert construir_rutas._par_sin_peaje(principal("madrid_barcelona", "rapida")) is True  # AP-2/AP-7 gratuitas
    assert construir_rutas._par_sin_peaje(principal("bilbao_zaragoza", "rapida")) is False  # AP-68
    assert construir_rutas._par_sin_peaje(principal("a_coruna_pontevedra", "rapida")) is False  # AP-9
    assert construir_rutas._par_sin_peaje(cb2.ruta_principal(_sintetica(1.0, 1.0, peaje=False))) is True
    assert construir_rutas._par_sin_peaje(cb2.ruta_principal(_sintetica(1.0, 1.0, peaje=True))) is False


def test_decodificar_polyline_ejemplo_de_referencia():
    """Ejemplo de la documentación del algoritmo (Google Encoded Polyline): (38.5, -120.2), (40.7, -120.95),
    (43.252, -126.453) en (lat, lon); la función devuelve (lon, lat)."""
    puntos = construir_rutas.decodificar_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
    assert puntos == pytest.approx([(-120.2, 38.5), (-120.95, 40.7), (-126.453, 43.252)])
    assert construir_rutas.decodificar_polyline("") == []


def test_decodificar_polyline_cuadra_con_la_maniobra_siguiente_en_las_fixtures():
    """El último punto de la geometría de cada paso es la maniobra del siguiente (6 decimales vs 5)."""
    for nombre in REALES.values():
        for alt in cb2.ALTERNATIVAS:
            pasos = cb2.ruta_principal(_real(nombre, alt))["legs"][0]["steps"]
            for paso, siguiente in zip(pasos, pasos[1:]):
                fin = construir_rutas.decodificar_polyline(paso["geometry"])[-1]
                assert fin == pytest.approx(tuple(siguiente["maneuver"]["location"]), abs=1e-5)


# --------------------------------------------------------------------------------------------- construir_rutas


@pytest.fixture(scope="module")
def corrida_completa(tmp_path_factory):
    """Descarga completa (1 081 pares + 20 de simetría) contra el doble y construcción. NO modificar `raw`."""
    raw = tmp_path_factory.mktemp("osrm_2026-10-12")
    res = _descargar(raw, ServidorFalso())
    salida = tmp_path_factory.mktemp("processed")
    construir_rutas.construir(CITIES, raw, salida)
    cabecera, filas = _leer_csv(salida / "rutas.csv")
    cabecera_pasos, pasos = _leer_csv(salida / "rutas_pasos_peaje.csv")
    resumen = json.loads((salida / "rutas_resumen.json").read_text(encoding="utf-8"))
    return {"res": res, "raw": raw, "filas": filas, "cabecera": cabecera, "resumen": resumen, "pasos": pasos,
            "cabecera_pasos": cabecera_pasos, "salida": salida}


@pytest.fixture
def raw_copia(corrida_completa, tmp_path):
    """Copia de los crudos de la corrida completa para las pruebas que los modifican."""
    return Path(shutil.copytree(corrida_completa["raw"], tmp_path / "raw"))


def _fila(filas, i, j, alt):
    return next(f for f in filas if (int(f["i"]), int(f["j"]), f["alternativa"]) == (i, j, alt))


def _impares_sinteticos() -> set[tuple[int, int]]:
    return {(a, b) for a, b in cb2.pares(47) if frozenset((a, b)) not in REALES and (a + b) % 2 == 1}


def test_descarga_completa_pide_2162_rutas_mas_40_de_simetria(corrida_completa):
    res = corrida_completa["res"]
    assert res.n_pedidas == 2 * 1081 + 2 * 20 and not res.fallos
    assert len(list((corrida_completa["raw"] / "rutas").glob("*.json.gz"))) == 2162
    assert len(list((corrida_completa["raw"] / "simetria").glob("*.json.gz"))) == 40


def test_rutas_csv_columnas_exactas_y_2162_filas_ordenadas(corrida_completa):
    filas = corrida_completa["filas"]
    assert corrida_completa["cabecera"] == COLUMNAS
    assert len(filas) == 2162
    claves = [(int(f["i"]), int(f["j"]), f["alternativa"]) for f in filas]
    assert claves == sorted(claves) and len(set(claves)) == 2162
    assert {(i, j) for i, j, _ in claves} == set(cb2.pares(47))
    assert {a for _, _, a in claves} == {"rapida", "sin_peaje"}


def test_rutas_csv_unidades_km_y_horas(corrida_completa):
    """Madrid–Barcelona (respuesta real de T2.2): 617 044,8 m y 24 561,5 s."""
    f = _fila(corrida_completa["filas"], BCN, MAD, "rapida")
    assert float(f["dist_km"]) == pytest.approx(617044.8 / 1000, abs=1e-9)
    assert float(f["tiempo_h"]) == pytest.approx(24561.5 / 3600, abs=1e-6)
    b = _fila(corrida_completa["filas"], BIO, ZGZ, "sin_peaje")
    assert float(b["dist_km"]) == pytest.approx(294.2625) and float(b["tiempo_h"]) == pytest.approx(15688.9 / 3600,
                                                                                                    abs=1e-6)


def test_rutas_csv_peajes_vacios_fuente_y_fecha_extracto(corrida_completa):
    marcados = {tuple(p) for p in corrida_completa["resumen"]["pares_sin_peaje"]["pares"]}
    for f in corrida_completa["filas"]:
        i, j = int(f["i"]), int(f["j"])
        assert f["km_peaje"] == f["peaje_eur"] == f["vias_peaje"] == ""  # se completan en T2.5
        assert f["fecha_extracto_osm"] == DV
        assert "OSRM v26.10.0" in f["fuente"] and "spain-261001" in f["fuente"]
        alt_crudo = "rapida" if (i, j) in marcados else f["alternativa"]
        assert f"rutas/{i:02d}_{j:02d}_{alt_crudo}.json.gz" in f["fuente"]


def test_par_marcado_reutiliza_la_rapida_y_el_no_marcado_no(corrida_completa):
    filas = corrida_completa["filas"]
    for i, j in [(BCN, MAD), PAR_SOLO_DURACION_DISTINTA, PAR_SOLO_DISTANCIA_DISTINTA]:
        r, s = _fila(filas, i, j, "rapida"), _fila(filas, i, j, "sin_peaje")
        assert (s["dist_km"], s["tiempo_h"]) == (r["dist_km"], r["tiempo_h"])
        assert "reutiliza" in s["fuente"]
    r, s = _fila(filas, BIO, ZGZ, "rapida"), _fila(filas, BIO, ZGZ, "sin_peaje")
    assert r["dist_km"] == "305.5188" and s["dist_km"] == "294.2625" and "reutiliza" not in s["fuente"]


def test_resumen_claves_de_primer_nivel_del_contrato(corrida_completa):
    claves = set(corrida_completa["resumen"])
    assert CLAVES_RESUMEN <= claves <= CLAVES_RESUMEN | CLAVES_RESUMEN_OPCIONALES
    r = corrida_completa["resumen"]
    assert r["n_pares"] == 1081 and r["n_filas"] == 2162 and r["fecha_extracto_osm"] == DV
    assert set(r["fecha_consulta_utc"]) == {"min", "max"} and set(r["pares_sin_peaje"]) == {"criterio", "n", "pares"}


def test_resumen_pares_sin_peaje_por_clase_toll(corrida_completa):
    p = corrida_completa["resumen"]["pares_sin_peaje"]
    marcados = {tuple(x) for x in p["pares"]}
    assert (BCN, MAD) in marcados  # sin 'toll' en la rápida (AP-2/AP-7 ya gratuitas)
    assert (BIO, ZGZ) not in marcados and (COR, PON) not in marcados  # AP-68 y AP-9
    pares_sinteticos = {(a, b) for a, b in cb2.pares(47) if frozenset((a, b)) not in REALES and (a + b) % 2 == 0}
    assert marcados == pares_sinteticos | {(BCN, MAD)}  # incluye los marcados con valores distintos
    assert p["n"] == len(marcados) and "toll" in p["criterio"]


def test_resumen_avisa_par_marcado_con_valores_distintos(corrida_completa):
    avisos = corrida_completa["resumen"]["avisos"]["par_sin_peaje_con_valores_distintos"]
    assert [(a["i"], a["j"]) for a in avisos["pares"]] == [PAR_SOLO_DURACION_DISTINTA, PAR_SOLO_DISTANCIA_DISTINTA]
    assert avisos["n"] == 2 and avisos["nota"]


def test_resumen_avisa_sin_peaje_mas_rapida(corrida_completa):
    avisos = corrida_completa["resumen"]["avisos"]["sin_peaje_mas_rapida"]["pares"]
    assert [(a["i"], a["j"]) for a in avisos] == [PAR_SIN_PEAJE_MAS_RAPIDA]
    assert avisos[0]["diferencia_h"] == pytest.approx(-60 / 3600)


def test_resumen_control_pasos(corrida_completa):
    r = corrida_completa["resumen"]
    cp = r["control_pasos"]
    assert r["avisos"]["sin_peaje_con_clase_toll"]["pares"] == [] and cp["sin_peaje_con_clase_toll"] == 0
    assert cp["rutas_con_ref"] == 2162 - 2  # PAR_SIN_REF no trae ref en ninguna alternativa
    assert cp["rapida_con_clase_toll"] == 1081 - r["pares_sin_peaje"]["n"]
    assert cp["filas_rutas_pasos_peaje"] == len(corrida_completa["pasos"])


def test_resumen_simetria_diferencias_maximas(corrida_completa):
    s = corrida_completa["resumen"]["simetria"]
    assert [tuple(p) for p in s["pares"]] == cb2.pares_simetria(47)
    for alt in ("rapida", "sin_peaje"):
        assert s[alt]["max_abs_km"] == pytest.approx(0.1)  # el doble suma 100 m y 36 s en j -> i
        assert s[alt]["max_abs_h"] == pytest.approx(0.01)
        assert s[alt]["max_rel_km"] > 0 and s[alt]["max_rel_h"] > 0
        assert len(s[alt]["detalle"]) == 20


def test_pasos_peaje_columnas_exactas_y_solo_pasos_con_toll(corrida_completa):
    pasos = corrida_completa["pasos"]
    assert corrida_completa["cabecera_pasos"] == COLUMNAS_PASOS
    assert all(int(p["n_intersecciones_toll"]) >= 1 for p in pasos)
    assert all(int(p["n_intersecciones_toll"]) <= int(p["n_intersecciones"]) for p in pasos)
    claves = [(int(p["i"]), int(p["j"]), p["alternativa"], int(p["paso"])) for p in pasos]
    assert claves == sorted(claves) and len(set(claves)) == len(claves)
    assert {a for *_, a, _ in claves} == {"rapida"}  # sin_peaje nunca pasa por 'toll' en el doble
    marcados = {tuple(x) for x in corrida_completa["resumen"]["pares_sin_peaje"]["pares"]}
    assert not {(i, j) for i, j, *_ in claves} & marcados
    # 1 paso con 'toll' por par sintético impar + Bilbao–Zaragoza (1) + A Coruña–Pontevedra (2)
    assert len(pasos) == len(_impares_sinteticos()) + 3


def test_pasos_peaje_bilbao_zaragoza_ap68(corrida_completa):
    """Fixture real de T2.2 (mirada el 2026-10-11): paso 14, ref AP-68 sin `name`, 293 175,4 m, 94/96 'toll'."""
    filas = [p for p in corrida_completa["pasos"] if (int(p["i"]), int(p["j"])) == (BIO, ZGZ)]
    assert [(p["paso"], p["ref"], p["nombre"], p["dist_m"], p["n_intersecciones"], p["n_intersecciones_toll"])
            for p in filas] == [("14", "AP-68", "", "293175.4", "96", "94")]
    pasos = cb2.ruta_principal(_real("bilbao_zaragoza", "rapida"))["legs"][0]["steps"]
    assert (float(filas[0]["lon_ini"]), float(filas[0]["lat_ini"])) == tuple(pasos[14]["maneuver"]["location"])
    assert (float(filas[0]["lon_fin"]), float(filas[0]["lat_fin"])) == pytest.approx(
        tuple(pasos[15]["maneuver"]["location"]), abs=1e-5)


def test_pasos_peaje_a_coruna_pontevedra_ap9(corrida_completa):
    filas = [p for p in corrida_completa["pasos"] if (int(p["i"]), int(p["j"])) == (COR, PON)]
    assert [(p["paso"], p["ref"], p["n_intersecciones"], p["n_intersecciones_toll"]) for p in filas] == [
        ("5", "AP-9", "12", "3"), ("6", "AP-9", "38", "30")]


def test_pasos_peaje_par_sintetico_sin_ref(corrida_completa):
    filas = [p for p in corrida_completa["pasos"] if (int(p["i"]), int(p["j"])) == PAR_SIN_REF]
    assert len(filas) == 1 and filas[0]["ref"] == "" and filas[0]["nombre"] == ""
    assert (filas[0]["lon_ini"], filas[0]["lat_ini"], filas[0]["lon_fin"], filas[0]["lat_fin"]) == (
        "-3.000000", "40.000000", "-2.50000", "40.50000")


def test_aviso_y_pasos_si_sin_peaje_pasa_por_toll(tmp_path):
    raw = tmp_path / "osrm"
    _descargar(raw, ServidorFalso(toll_en_sin_peaje={(0, 2)}), limite=3)
    resumen = construir_rutas.construir(CITIES, raw, tmp_path / "out", parcial=True)
    assert resumen["avisos"]["sin_peaje_con_clase_toll"]["pares"] == [[0, 2]]
    assert resumen["control_pasos"]["sin_peaje_con_clase_toll"] == 1
    _, pasos = _leer_csv(tmp_path / "out" / "rutas_pasos_peaje.csv")
    assert [(p["i"], p["j"], p["alternativa"]) for p in pasos if p["alternativa"] == "sin_peaje"] == [
        ("0", "2", "sin_peaje")]


def test_construir_falla_si_falta_un_par(raw_copia, tmp_path):
    (raw_copia / "rutas" / "05_09_rapida.json.gz").unlink()
    with pytest.raises(cb2.DatoFaltanteError, match="05_09_rapida"):
        construir_rutas.construir(CITIES, raw_copia, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.fixture
def raw_pequeno(tmp_path):
    """Descarga con --limite 1 (6 crudos) para las pruebas de crudos malos, que fallan también con parcial=True."""
    raw = tmp_path / "osrm"
    _descargar(raw, ServidorFalso(), limite=1)
    return raw


def test_construir_falla_si_un_crudo_no_es_ok_aunque_sea_parcial(raw_pequeno, tmp_path):
    archivo = raw_pequeno / "rutas" / "00_01_rapida.json.gz"
    crudo = cb2.leer_crudo(archivo)
    crudo["respuesta"] = {"code": "NoRoute", "message": "x"}
    archivo.write_bytes(gzip.compress(json.dumps(crudo).encode()))
    with pytest.raises(cb2.DatoFaltanteError, match="00_01_rapida.*NoRoute"):
        construir_rutas.construir(CITIES, raw_pequeno, tmp_path / "out", parcial=True)
    assert not (tmp_path / "out").exists()


def test_construir_falla_si_una_ruta_no_tiene_pasos(raw_pequeno, tmp_path):
    """Spec §7.2: hay que guardar los pasos (ref, clases); una respuesta sin pasos no sirve para T2.5."""
    archivo = raw_pequeno / "rutas" / "00_01_sin_peaje.json.gz"
    crudo = cb2.leer_crudo(archivo)
    crudo["respuesta"]["routes"][0]["legs"][0]["steps"] = []
    archivo.write_bytes(gzip.compress(json.dumps(crudo).encode()))
    with pytest.raises(cb2.DatoFaltanteError, match="00_01_sin_peaje.*pasos"):
        construir_rutas.construir(CITIES, raw_pequeno, tmp_path / "out", parcial=True)


def test_construir_falla_si_la_url_no_cuadra_con_cities(corrida_completa, tmp_path):
    """Si cities.csv cambiara después de descargar, las rutas ya no corresponderían a sus coordenadas."""
    otras = tmp_path / "cities.csv"
    texto = CITIES.read_text(encoding="utf-8").replace("2.177440", "2.177441")  # Barcelona, lon
    otras.write_text(texto, encoding="utf-8")
    with pytest.raises(cb2.DatoFaltanteError, match="coordenadas"):
        construir_rutas.construir(otras, corrida_completa["raw"], tmp_path / "salida")


def test_construir_acepta_crudos_de_otro_puerto(tmp_path):
    raw = tmp_path / "osrm"
    _descargar(raw, ServidorFalso(), limite=2, base="http://127.0.0.1:5002")
    assert construir_rutas.construir(CITIES, raw, tmp_path / "out", parcial=True)["n_pares"] == 4


def test_construir_parcial_tras_prueba_con_limite(tmp_path):
    raw = tmp_path / "osrm"
    _descargar(raw, ServidorFalso(), limite=3)
    with pytest.raises(cb2.DatoFaltanteError):
        construir_rutas.construir(CITIES, raw, tmp_path / "out")
    construir_rutas.construir(CITIES, raw, tmp_path / "out", parcial=True)
    assert len(_leer_csv(tmp_path / "out" / "rutas.csv")[1]) == 12
    assert (tmp_path / "out" / "rutas_pasos_peaje.csv").exists()
    resumen = json.loads((tmp_path / "out" / "rutas_resumen.json").read_text(encoding="utf-8"))
    assert resumen["parcial"] is True and resumen["n_pares"] == 6
    assert len(resumen["simetria"]["pares"]) == 3


def test_construir_parcial_no_puede_escribir_en_processed(tmp_path):
    with pytest.raises(SystemExit, match="--parcial"):
        construir_rutas.main(["--fecha", "2026-10-12", "--parcial"])
