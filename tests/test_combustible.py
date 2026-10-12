"""Pruebas de T2.6 (Spec §7.2 Bloque 4, contrato §5.3: data/processed/combustible.json). Sin red.

Las estaciones de las pruebas son SINTÉTICAS (precios inventados para que las cuentas salgan a mano) pero con la
estructura real de la respuesta del servicio REST del Ministerio (mismas claves, textos con coma decimal, precio vacío
como cadena ""), copiada de la respuesta del 01-10-2026. La descarga se prueba con un doble de `consultar`.
La última sección comprueba que el combustible.json versionado se regenera igual desde el crudo versionado.
"""

from __future__ import annotations

import gzip
import json
from decimal import Decimal
from pathlib import Path

import pytest

import comun_bloque4 as cb4
import construir_combustible
import descargar_datos

RAIZ = Path(__file__).resolve().parents[1]
FECHA = "2026-10-01"
BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"
URL_HIST = f"{BASE}/EstacionesTerrestresHist/01-10-2026"
URL_HIST_PRODUCTO = f"{BASE}/EstacionesTerrestresHist/FiltroProducto/01-10-2026/1"
URL_PRODUCTOS = f"{BASE}/Listados/ProductosPetroliferos/"
URL_CCAA = f"{BASE}/Listados/ComunidadesAutonomas/"
CLAVES_CONTRATO = {"producto", "ambito", "precio_medio_eur_l", "precio_mediano_eur_l", "n_estaciones", "fecha",
                   "fuente_url", "archivo_raw"}  # Spec §5.3 v1.6, exactas
CLAVES_RESUMEN = {"producto", "id_producto", "campo_precio", "ambito", "fecha", "fecha_respuesta", "fecha_consulta_utc",
                  "fuente_url", "archivo_raw", "redondeo", "n_estaciones_respuesta", "n_sin_precio",
                  "criterio_sin_precio", "nacional", "peninsular", "no_peninsular", "ccaa_no_peninsulares",
                  "contraste_filtro_producto"}  # Spec §5.3 v1.6, exactas
CLAVES_ESTADISTICOS = {"n", "media", "mediana", "min", "max"}

# Claves reales de cada estación (respuesta del 01-10-2026).
CLAVES_COMUNES = ["C.P.", "Dirección", "Horario", "Latitud", "Localidad", "Longitud (WGS84)", "Margen", "Municipio",
                  "Provincia", "Remisión", "Rótulo", "Tipo Venta", "IDEESS", "IDMunicipio", "IDProvincia", "IDCCAA"]
PRECIOS_HIST = ["Precio Adblue", "Precio Amoniaco", "Precio Biodiesel", "Precio Bioetanol",
                "Precio Biogas Natural Comprimido", "Precio Biogas Natural Licuado", "Precio Diésel Renovable",
                "Precio Gas Natural Comprimido", "Precio Gas Natural Licuado", "Precio Gases licuados del petróleo",
                "Precio Gasoleo A", "Precio Gasoleo B", "Precio Gasoleo Premium", "Precio Gasolina 95 E10",
                "Precio Gasolina 95 E25", "Precio Gasolina 95 E5", "Precio Gasolina 95 E5 Premium",
                "Precio Gasolina 95 E85", "Precio Gasolina 98 E10", "Precio Gasolina 98 E5",
                "Precio Gasolina Renovable", "Precio Hidrogeno", "Precio Metanol"]
NOTA = ("Archivo de todos los productos en todas las estaciones de servicio. La actualización de precios se realiza "
        "cada media hora, con los precios en vigor en ese momento.")
CCAA = [("01", "Andalucia"), ("02", "Aragón"), ("03", "Asturias"), ("04", "Baleares"), ("05", "Canarias"),
        ("06", "Cantabria"), ("07", "Castilla la Mancha"), ("08", "Castilla y León"), ("09", "Cataluña"),
        ("10", "Comunidad Valenciana"), ("11", "Extremadura"), ("12", "Galicia"), ("13", "Madrid"), ("14", "Murcia"),
        ("15", "Navarra"), ("16", "País Vasco"), ("17", "Rioja (La)"), ("18", "Ceuta"), ("19", "Melilla")]
PRODUCTOS = [{"IDProducto": "1", "NombreProducto": "Gasolina 95 E5", "NombreProductoAbreviatura": "G95E5"},
             {"IDProducto": "23", "NombreProducto": "Gasolina 95 E10", "NombreProductoAbreviatura": "G95E10"}]

# (IDEESS, IDCCAA, precio E5): SINTÉTICOS. Peninsular (sin 04, 05, 18, 19; va a combustible.json): 1,5 / 1,6 / 1,7
# -> media 1,6, mediana 1,6. Nacional (sensibilidad) = 10,85 / 7 = 1,55; mediana 1,5. Dos estaciones sin precio.
ESTACIONES = [("1", "01", "1,500"), ("2", "09", "1,600"), ("3", "13", "1,700"), ("4", "04", "1,900"),
              ("5", "05", "1,300"), ("6", "18", "1,400"), ("7", "19", "1,450"), ("8", "12", ""), ("9", "05", "")]


def _comunes(ideess: str, ccaa: str) -> dict:
    e = {k: "" for k in CLAVES_COMUNES}
    e.update({"C.P.": "28001", "Latitud": "40,416775", "Longitud (WGS84)": "-3,703790", "Margen": "D",
              "Remisión": "dm", "Tipo Venta": "P", "IDEESS": ideess, "IDMunicipio": "1", "IDProvincia": "28",
              "IDCCAA": ccaa})
    return e


def _hist(estaciones=ESTACIONES, fecha="01/10/2026 0:00:00", resultado="OK") -> dict:
    lista = []
    for ideess, ccaa, precio in estaciones:
        e = _comunes(ideess, ccaa)
        e.update({k: "" for k in PRECIOS_HIST})
        e.update({"% BioEtanol": "0,0", "% Éster metílico": "0,0", "Precio Gasolina 95 E5": precio,
                  "Precio Gasoleo A": "1,600"})
        lista.append(e)
    return {"Fecha": fecha, "ListaEESSPrecio": lista, "Nota": NOTA, "ResultadoConsulta": resultado}


def _hist_producto(estaciones=ESTACIONES, fecha="01/10/2026 0:00:00", resultado="OK") -> dict:
    """El filtro por producto solo trae las estaciones con precio, en el campo PrecioProducto."""
    lista = []
    for ideess, ccaa, precio in estaciones:
        if precio:
            e = _comunes(ideess, ccaa)
            e["PrecioProducto"] = precio
            lista.append(e)
    return {"Fecha": fecha, "ListaEESSPrecio": lista, "Nota": NOTA, "ResultadoConsulta": resultado}


def _respuestas(**cambios) -> dict:
    r = {URL_HIST: _hist(), URL_HIST_PRODUCTO: _hist_producto(), URL_PRODUCTOS: PRODUCTOS,
         URL_CCAA: [{"IDCCAA": c, "CCAA": n} for c, n in CCAA]}
    r.update(cambios)
    return r


def _crudo(url_historico: str = URL_HIST, **cambios) -> dict:
    """Crudo con las 4 consultas. `url_historico` cambia solo la URL guardada del histórico (no su respuesta)."""
    r = _respuestas(**cambios)
    nombres = dict(zip([URL_HIST, URL_HIST_PRODUCTO, URL_PRODUCTOS, URL_CCAA], cb4.NOMBRES_CONSULTAS))
    guardadas = {URL_HIST: url_historico}
    return {"fecha_datos": FECHA, "fecha_consulta_utc": "2026-10-11T12:00:00Z",
            "consultas": [{"nombre": nombres[u], "url": guardadas.get(u, u),
                           "fecha_consulta_utc": "2026-10-11T12:00:00Z", "respuesta": r[u]} for u in nombres]}


def _escribir_crudo(tmp_path: Path, crudo: dict) -> Path:
    ruta = tmp_path / cb4.nombre_crudo(FECHA)
    ruta.write_bytes(gzip.compress(json.dumps(crudo, ensure_ascii=False).encode("utf-8")))
    return ruta


# ------------------------------------------------------------------------------------- comun_bloque4


def test_constantes_del_producto():
    assert cb4.PRODUCTO == "Gasolina 95 E5"
    assert cb4.ID_PRODUCTO == "1"
    assert cb4.CAMPO_PRECIO == "Precio Gasolina 95 E5"
    assert cb4.FECHA_CORTE == "2026-10-01"  # Spec §7.1
    assert set(cb4.CCAA_NO_PENINSULARES) == {"04", "05", "18", "19"}


def test_fecha_api_es_dd_mm_aaaa():
    """La API rechaza AAAA-MM-DD: 'Fecha ha de tener el formato dd-mm-aaaa' (respuesta real, 11-oct-2026)."""
    assert cb4.fecha_api("2026-10-01") == "01-10-2026"
    assert cb4.fecha_api("2025-01-31") == "31-01-2025"


def test_urls_de_las_consultas():
    assert cb4.urls_consultas(FECHA) == {
        "historico": URL_HIST, "historico_producto": URL_HIST_PRODUCTO, "productos": URL_PRODUCTOS, "ccaa": URL_CCAA}
    assert list(cb4.urls_consultas(FECHA)) == list(cb4.NOMBRES_CONSULTAS)


def test_nombre_del_crudo_lleva_la_fecha():
    assert cb4.nombre_crudo(FECHA) == "carburantes_minetur_hist_2026-10-01.json.gz"


@pytest.mark.parametrize("texto, esperado", [("1,749", Decimal("1.749")), ("2,299", Decimal("2.299")),
                                              ("0,5", Decimal("0.5"))])
def test_precio_con_coma_decimal(texto, esperado):
    assert cb4.precio(texto) == esperado


@pytest.mark.parametrize("texto", ["1.749", "1,749 ", "abc", "1,", ",5", "-1,2", "1,2,3"])
def test_precio_con_formato_inesperado_detiene(texto):
    with pytest.raises(cb4.DatoFaltanteError):
        cb4.precio(texto)


@pytest.mark.parametrize("valores, media, mediana, minimo, maximo", [
    (["1.700", "1.500", "1.600"], 1.6, 1.6, 1.5, 1.7),
    # 6,601 / 4 = 1,65025 -> 1,6502 (4 decimales, mitad al par); mediana par = (1,6 + 1,7) / 2
    (["1.500", "1.600", "1.700", "1.801"], 1.6502, 1.65, 1.5, 1.801),
    (["1.000", "1.001"], 1.0005, 1.0005, 1.0, 1.001),
])
def test_estadisticos_exactos_con_decimal(valores, media, mediana, minimo, maximo):
    est = cb4.estadisticos([Decimal(v) for v in valores])
    assert est == {"n": len(valores), "media": media, "mediana": mediana, "min": minimo, "max": maximo}


def test_estadisticos_vacio_detiene():
    with pytest.raises(cb4.DatoFaltanteError):
        cb4.estadisticos([])


# ------------------------------------------------------------------------------------- cálculo


def test_calcular_valores_a_mano():
    """Spec §7.2 Bloque 4 v1.6 (decisión humana 2026-10-11): combustible.json lleva la media PENINSULAR."""
    combustible, resumen = construir_combustible.calcular(_crudo(), "data/raw/x.json.gz")
    assert combustible == {
        "producto": "Gasolina 95 E5",
        "ambito": "peninsular",
        "precio_medio_eur_l": 1.6,
        "precio_mediano_eur_l": 1.6,
        "n_estaciones": 3,
        "fecha": "2026-10-01",
        "fuente_url": URL_HIST,
        "archivo_raw": "data/raw/x.json.gz",
    }
    assert resumen["n_estaciones_respuesta"] == 9
    assert resumen["n_sin_precio"] == 2
    assert resumen["nacional"] == {"n": 7, "media": 1.55, "mediana": 1.5, "min": 1.3, "max": 1.9}
    assert resumen["peninsular"] == {"n": 3, "media": 1.6, "mediana": 1.6, "min": 1.5, "max": 1.7}
    assert resumen["no_peninsular"]["Canarias"] == {"n": 1, "media": 1.3, "mediana": 1.3, "min": 1.3, "max": 1.3}
    assert set(resumen["no_peninsular"]) == {"Baleares", "Canarias", "Ceuta", "Melilla"}
    assert resumen["contraste_filtro_producto"] == {"url": URL_HIST_PRODUCTO, "n_estaciones": 7, "coincide": True}
    assert resumen["ambito"] == "peninsular"
    assert resumen["ccaa_no_peninsulares"] == {"04": "Baleares", "05": "Canarias", "18": "Ceuta", "19": "Melilla"}


def test_precio_de_combustible_es_el_peninsular_del_resumen():
    combustible, resumen = construir_combustible.calcular(_crudo(), "data/raw/x.json.gz")
    p = resumen["peninsular"]
    assert (combustible["precio_medio_eur_l"], combustible["precio_mediano_eur_l"], combustible["n_estaciones"]) == (
        p["media"], p["mediana"], p["n"])
    assert combustible["precio_medio_eur_l"] != resumen["nacional"]["media"]  # el fixture las distingue


def test_contrato_exacto():
    combustible, resumen = construir_combustible.calcular(_crudo(), "data/raw/x.json.gz")
    assert set(combustible) == CLAVES_CONTRATO
    assert set(resumen) == CLAVES_RESUMEN
    assert "cuestion_abierta" not in resumen
    assert set(resumen["nacional"]) == set(resumen["peninsular"]) == CLAVES_ESTADISTICOS
    assert all(set(v) == CLAVES_ESTADISTICOS for v in resumen["no_peninsular"].values())
    assert set(resumen["contraste_filtro_producto"]) == {"url", "n_estaciones", "coincide"}
    assert isinstance(combustible["n_estaciones"], int)
    assert isinstance(combustible["precio_medio_eur_l"], float)


@pytest.mark.parametrize("descripcion, cambios", [
    ("resultado no OK", {URL_HIST: _hist(resultado="Error")}),
    ("otra fecha", {URL_HIST: _hist(fecha="30/09/2026 0:00:00")}),
    ("lista vacía", {URL_HIST: _hist(estaciones=[])}),
    ("filtro con otra fecha", {URL_HIST_PRODUCTO: _hist_producto(fecha="02/10/2026 0:00:00")}),
    ("filtro con otro precio", {URL_HIST_PRODUCTO: _hist_producto(
        estaciones=[("1", "01", "1,501")] + ESTACIONES[1:])}),
    ("filtro sin una estación", {URL_HIST_PRODUCTO: _hist_producto(estaciones=ESTACIONES[1:])}),
    ("estación solo en el filtro", {URL_HIST_PRODUCTO: _hist_producto(
        estaciones=ESTACIONES + [("10", "01", "1,500")])}),
    ("IDEESS repetido en el filtro", {URL_HIST_PRODUCTO: _hist_producto(
        estaciones=ESTACIONES + [("1", "01", "1,500")])}),
    ("URL del histórico de otra fecha", {"url_historico": f"{BASE}/EstacionesTerrestresHist/30-09-2026"}),
    ("listado de productos no es una lista", {URL_PRODUCTOS: {"Mensaje": "error"}}),
    ("listado de productos con elementos no objeto", {URL_PRODUCTOS: ["Gasolina 95 E5"]}),
    ("listado de CCAA nulo", {URL_CCAA: None}),
    ("IDEESS duplicado", {URL_HIST: _hist(estaciones=ESTACIONES + [("1", "01", "1,500")])}),
    ("producto 1 no es E5", {URL_PRODUCTOS: [{"IDProducto": "1", "NombreProducto": "Gasolina 98 E5",
                                              "NombreProductoAbreviatura": "G98E5"}]}),
    ("CCAA 05 no es Canarias", {URL_CCAA: [{"IDCCAA": c, "CCAA": "Otra" if c == "05" else n} for c, n in CCAA]}),
    ("precio con punto", {URL_HIST: _hist(estaciones=[("1", "01", "1.500")] + ESTACIONES[1:])}),
])
def test_crudo_incoherente_detiene(descripcion, cambios):
    with pytest.raises(cb4.DatoFaltanteError):
        construir_combustible.calcular(_crudo(**cambios), "data/raw/x.json.gz")


def test_falta_el_campo_de_precio_detiene():
    hist = _hist()
    del hist["ListaEESSPrecio"][0]["Precio Gasolina 95 E5"]
    with pytest.raises(cb4.DatoFaltanteError, match="Precio Gasolina 95 E5"):
        construir_combustible.calcular(_crudo(**{URL_HIST: hist}), "data/raw/x.json.gz")


def test_precio_solo_espacios_cuenta_como_vacio():
    hist = _hist()
    hist["ListaEESSPrecio"][7]["Precio Gasolina 95 E5"] = "  "
    _, resumen = construir_combustible.calcular(_crudo(**{URL_HIST: hist}), "data/raw/x.json.gz")
    assert resumen["n_sin_precio"] == 2


def test_falta_una_consulta_detiene():
    crudo = _crudo()
    crudo["consultas"] = crudo["consultas"][:1]
    with pytest.raises(cb4.DatoFaltanteError):
        construir_combustible.calcular(crudo, "data/raw/x.json.gz")


def test_construir_escribe_los_dos_json(tmp_path):
    ruta = _escribir_crudo(tmp_path, _crudo())
    salida = tmp_path / "processed"
    combustible = construir_combustible.construir(ruta, salida)
    leido = json.loads((salida / "combustible.json").read_text(encoding="utf-8"))
    assert leido == combustible
    assert set(leido) == CLAVES_CONTRATO
    resumen = json.loads((salida / "combustible_resumen.json").read_text(encoding="utf-8"))
    assert set(resumen) == CLAVES_RESUMEN
    assert resumen["n_sin_precio"] == 2


def test_construir_crudo_inexistente_detiene(tmp_path):
    with pytest.raises(cb4.DatoFaltanteError, match="descargar_datos.py --bloque 4"):
        construir_combustible.construir(tmp_path / "no_existe.json.gz", tmp_path)


def test_construir_es_determinista(tmp_path):
    ruta = _escribir_crudo(tmp_path, _crudo())
    construir_combustible.construir(ruta, tmp_path / "a")
    construir_combustible.construir(ruta, tmp_path / "b")
    for nombre in ("combustible.json", "combustible_resumen.json"):
        assert (tmp_path / "a" / nombre).read_bytes() == (tmp_path / "b" / nombre).read_bytes()


# ------------------------------------------------------------------------------------- descarga (--bloque 4)


class ConsultarFalso:
    def __init__(self, respuestas: dict):
        self.respuestas = respuestas
        self.pedidas: list[str] = []

    def __call__(self, url: str):
        self.pedidas.append(url)
        return self.respuestas[url]


def test_descarga_guarda_las_cuatro_consultas(tmp_path):
    falso = ConsultarFalso(_respuestas())
    ruta = descargar_datos.descargar_carburantes(FECHA, tmp_path, consultar=falso)
    assert ruta == tmp_path / "carburantes_minetur_hist_2026-10-01.json.gz"
    assert falso.pedidas == [URL_HIST, URL_HIST_PRODUCTO, URL_PRODUCTOS, URL_CCAA]
    crudo = json.loads(gzip.decompress(ruta.read_bytes()))
    assert crudo["fecha_datos"] == FECHA
    assert [c["nombre"] for c in crudo["consultas"]] == list(cb4.NOMBRES_CONSULTAS)
    assert crudo["consultas"][0]["respuesta"] == _hist()
    assert all(c["fecha_consulta_utc"].endswith("Z") for c in crudo["consultas"])
    # El crudo descargado se procesa sin cambios.
    combustible = construir_combustible.construir(ruta, tmp_path / "processed")
    assert combustible["precio_medio_eur_l"] == 1.6


@pytest.mark.parametrize("cambios", [
    {URL_HIST: {"Fecha": None, "ListaEESSPrecio": [], "Nota": NOTA,
                "ResultadoConsulta": "Parametros de entrada incorrectos: Fecha ha de tener el formato dd-mm-aaaa"}},
    {URL_HIST: _hist(fecha="11/10/2026 0:00:00")},  # el servidor devolvió otro día: NO se sustituye en silencio
    {URL_HIST_PRODUCTO: _hist_producto(resultado="Error")},
])
def test_descarga_no_guarda_respuestas_de_otra_fecha_o_con_error(tmp_path, cambios):
    with pytest.raises(descargar_datos.DescargaError):
        descargar_datos.descargar_carburantes(FECHA, tmp_path, consultar=ConsultarFalso(_respuestas(**cambios)))
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("cambios", [
    {URL_PRODUCTOS: [{"IDProducto": "1", "NombreProducto": "Gasolina 98 E5", "NombreProductoAbreviatura": "G98E5"}]},
    {URL_PRODUCTOS: {"Mensaje": "error"}},
    {URL_CCAA: [{"IDCCAA": c, "CCAA": "Otra" if c == "18" else n} for c, n in CCAA]},
])
def test_descarga_no_guarda_listados_erroneos(tmp_path, cambios):
    """R2-004: los listados se validan ANTES de guardar el crudo (como cb2.problema_crudo en el Bloque 2)."""
    with pytest.raises(descargar_datos.DescargaError):
        descargar_datos.descargar_carburantes(FECHA, tmp_path, consultar=ConsultarFalso(_respuestas(**cambios)))
    assert list(tmp_path.iterdir()) == []


def test_get_json_usa_el_contexto_tls_minetur(monkeypatch):
    """R2-005: _get_json pasa a urlopen el contexto con el cifrado del Ministerio y decodifica el BOM."""
    import ssl

    recibido = {}

    class RespuestaFalsa:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return ("\ufeff" + json.dumps([{"IDCCAA": "01"}])).encode("utf-8")  # la API antepone BOM UTF-8

    def urlopen_falso(req, timeout=None, context=None):
        recibido.update(url=req.full_url, timeout=timeout, context=context, accept=req.get_header("Accept"))
        return RespuestaFalsa()

    monkeypatch.setattr(descargar_datos.urllib.request, "urlopen", urlopen_falso)
    assert descargar_datos._get_json(URL_CCAA) == [{"IDCCAA": "01"}]
    ctx = recibido["context"]
    assert isinstance(ctx, ssl.SSLContext)
    assert "AES256-GCM-SHA384" in {c["name"] for c in ctx.get_ciphers()}
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    assert recibido["url"] == URL_CCAA and recibido["accept"] == "application/json"


def test_descarga_no_sobrescribe(tmp_path):
    (tmp_path / cb4.nombre_crudo(FECHA)).write_bytes(b"previo")
    with pytest.raises(descargar_datos.DescargaError, match="ya existe"):
        descargar_datos.descargar_carburantes(FECHA, tmp_path, consultar=ConsultarFalso(_respuestas()))
    assert (tmp_path / cb4.nombre_crudo(FECHA)).read_bytes() == b"previo"


def test_contexto_tls_minetur_verifica_y_admite_el_cifrado_del_servidor():
    """El servidor solo negocia AES256-GCM-SHA384 (comprobado el 2026-10-11); no se relaja la verificación."""
    import ssl

    ctx = descargar_datos.contexto_tls_minetur()
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    assert "AES256-GCM-SHA384" in {c["name"] for c in ctx.get_ciphers()}
    por_defecto = {c["name"] for c in ssl.create_default_context().get_ciphers()}
    assert {c["name"] for c in ctx.get_ciphers()} - por_defecto == {"AES256-GCM-SHA384"}


def test_cli_bloque4_fecha_por_defecto_es_la_de_corte():
    args = descargar_datos.construir_parser().parse_args(["--bloque", "4"])
    assert args.bloque == 4
    assert descargar_datos.fecha_bloque4(args) == "2026-10-01"
    args = descargar_datos.construir_parser().parse_args(["--bloque", "4", "--fecha", "2026-09-30"])
    assert descargar_datos.fecha_bloque4(args) == "2026-09-30"


def test_cli_construir_combustible_fecha_por_defecto():
    args = construir_combustible.construir_parser().parse_args([])
    assert args.fecha == "2026-10-01"


# ------------------------------------------------------------------------------------- datos reales versionados

CRUDO_REAL = RAIZ / "data" / "raw" / "carburantes_minetur_hist_2026-10-01.json.gz"
PROCESADO_REAL = RAIZ / "data" / "processed" / "combustible.json"


@pytest.mark.skipif(not CRUDO_REAL.exists(), reason="crudo del Bloque 4 no descargado")
def test_combustible_real_se_regenera_igual(tmp_path):
    construir_combustible.construir(CRUDO_REAL, tmp_path)
    for nombre in ("combustible.json", "combustible_resumen.json"):
        assert (tmp_path / nombre).read_bytes() == (RAIZ / "data" / "processed" / nombre).read_bytes()
    real = json.loads(PROCESADO_REAL.read_text(encoding="utf-8"))
    resumen = json.loads((RAIZ / "data" / "processed" / "combustible_resumen.json").read_text(encoding="utf-8"))
    assert set(real) == CLAVES_CONTRATO
    assert set(resumen) == CLAVES_RESUMEN
    assert real["ambito"] == resumen["ambito"] == "peninsular"
    assert real["n_estaciones"] == resumen["peninsular"]["n"]
    assert real["precio_medio_eur_l"] == resumen["peninsular"]["media"]
    assert real["archivo_raw"] == "data/raw/carburantes_minetur_hist_2026-10-01.json.gz"
    assert real["fecha"] == FECHA
