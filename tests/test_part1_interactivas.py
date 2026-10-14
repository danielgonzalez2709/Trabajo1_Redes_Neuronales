"""Pruebas de las figuras de la Parte 1 (T4.2; Spec §6.7) con corridas sintéticas (tests/sinteticos_part1.py).

Solo la última prueba usa los datos reales y se salta si no existen (`runs/` está ignorada por git).
"""
import math
import re

import numpy as np
import pytest

from src.common import cli
from src.common.results import save_json
from src.part1.functions import get_function
from src.part1.metricas import UMBRAL_PRINCIPAL
from src.viz import figuras, part1_datos as pd1, part1_interactivas as p1, paleta as p
from tests.sinteticos_part1 import (DIMENSIONES, FUNCIONES, METODOS, SEMILLAS, config_afinada, escribir_experimento,
                                    eta_json, experimento)

CELDAS = [(f, d) for f in FUNCIONES for d in DIMENSIONES]
AFINADOS = {("rosenbrock", 2): ["gdfijo", "ea"], ("rosenbrock", 3): ["gdfijo", "ea"],
            ("rastrigin", 2): ["ea"], ("rastrigin", 3): ["ea"]}
SIN_CORRIDAS = {"part1_contorno_rosenbrock.html", "part1_contorno_rastrigin.html"}
CON_DEFECTO = {"part1_convergencia.html", "part1_cajas.html", "part1_enjambre_rastrigin.html"}
CON_AFINADO = {"part1_convergencia_afinado.html", "part1_cajas_afinado.html"}
CON_ETA = {"part1_eta_rosenbrock.html"}


@pytest.fixture(scope="module")
def defecto():
    return experimento()


@pytest.fixture(scope="module")
def afinado():
    return experimento(config=config_afinada(), escala=0.5)


def _trazas(fig, prefijo):
    return [tr for tr in fig.data if isinstance(tr.meta, str) and tr.meta.startswith(prefijo + ":")]


# ------------------------------------------------------------------------------------------ catálogo


def test_el_titulo_de_convergencia_no_fija_el_numero_de_metodos():
    assert "cinco" not in p1.FIGURAS["convergencia"].titulo and "de los métodos" in p1.FIGURAS["convergencia"].titulo


def test_catalogo_ids_y_archivos_fijos_y_unicos():
    ids = [f.id for f in p1.FIGURAS.values()]
    archivos = [f.archivo for f in p1.FIGURAS.values()]
    assert ids == ["contorno-rosenbrock", "contorno-rastrigin", "convergencia-part1", "cajas-part1",
                   "convergencia-afinado-part1", "cajas-afinado-part1", "eta-rosenbrock", "enjambre-rastrigin"]
    assert set(archivos) == SIN_CORRIDAS | CON_DEFECTO | CON_AFINADO | CON_ETA and len(set(archivos)) == 8
    for f in p1.FIGURAS.values():
        assert re.fullmatch(r"[a-z0-9-]+", f.id)  # patrón del hook blog/hooks/reporte.py
        assert f.titulo.strip() and f.fuente.strip() and "\n" not in f.titulo + f.fuente


def test_bloque_del_blog_tiene_el_formato_del_hook():
    f = p1.FIGURAS["convergencia"]
    assert p1.bloque_blog(f) == (f"::: figura convergencia-part1\nTítulo: {f.titulo}\nFuente: {f.fuente}\n"
                                 "incluir: figures/part1_convergencia.html\n:::")


def test_las_figuras_con_piso_lo_declaran_en_la_fuente():
    for clave in ("convergencia", "cajas", "convergencia_afinado", "cajas_afinado"):
        assert p1.TEXTO_PISO in p1.FIGURAS[clave].fuente
    assert "1e-16" in p1.TEXTO_PISO and p1.PISO_LOG == 1e-16


# ----------------------------------------------------------------------------------------- contornos


@pytest.mark.parametrize("nombre", FUNCIONES)
def test_contorno_cubre_el_dominio_y_marca_el_optimo(nombre):
    func = get_function(nombre, 2)
    fig = p1.figura_contorno(nombre)
    contorno = next(tr for tr in fig.data if tr.meta == "contorno")
    assert (contorno.x[0], contorno.x[-1]) == pytest.approx(tuple(func.bounds[0]))
    assert len(contorno.z) == len(contorno.y) == p1.MALLA[nombre]
    optimo = next(tr for tr in fig.data if tr.meta == "x_star")
    assert [optimo.x[0], optimo.y[0]] == list(func.x_star)


def test_contorno_de_rosenbrock_usa_niveles_logaritmicos():
    fig = p1.figura_contorno("rosenbrock")
    contorno = next(tr for tr in fig.data if tr.meta == "contorno")
    _, _, z = pd1.malla("rosenbrock", p1.MALLA["rosenbrock"])
    assert np.array(contorno.z) == pytest.approx(np.log10(z), abs=1e-3)  # se dibuja log10 f
    assert "log" in contorno.colorbar.title.text.lower()


def test_contorno_de_rastrigin_resuelve_los_periodos():
    lb, ub = get_function("rastrigin", 2).bounds[0]
    periodos = (ub - lb) / 1.0  # cos(2πx) tiene período 1: el dominio real mide 10,24 períodos por eje
    intervalos_por_periodo = (p1.MALLA["rastrigin"] - 1) / periodos
    assert periodos == pytest.approx(10.24)
    assert intervalos_por_periodo == pytest.approx(19.53, abs=0.01) and intervalos_por_periodo >= 16


# -------------------------------------------------------------------------------------- convergencia


def test_convergencia_colores_de_la_paleta_y_cinco_metodos_por_celda(defecto):
    fig = p1.figura_convergencia(defecto)
    medianas = _trazas(fig, "mediana")
    assert len(medianas) == len(CELDAS) * len(METODOS)
    for tr in medianas:
        _, func, dim, method, variante = tr.meta.split(":")
        assert tr.line.color == p.COLOR_METODO[method] and tr.line.dash == "solid" and variante == "defecto"
        assert tr.name == p.NOMBRE_METODO[method]
    assert len(_trazas(fig, "q25")) == len(_trazas(fig, "q75")) == len(medianas)
    assert all(tr.fill == "tonexty" for tr in _trazas(fig, "q75"))


def test_convergencia_selector_con_una_opcion_por_celda(defecto):
    fig = p1.figura_convergencia(defecto)
    (menu,) = fig.layout.updatemenus
    assert [b.label for b in menu.buttons] == ["Rosenbrock 2D", "Rosenbrock 3D", "Rastrigin 2D", "Rastrigin 3D"]
    for k, boton in enumerate(menu.buttons):
        visibles = [tr.meta for tr, v in zip(fig.data, boton.args[0]["visible"]) if v]
        func, dim = CELDAS[k]
        assert len(visibles) == 3 * len(METODOS) and all(f":{func}:{dim}:" in m for m in visibles)
    iniciales = [tr.meta for tr in fig.data if tr.visible]
    assert all(":rosenbrock:2:" in m for m in iniciales) and len(iniciales) == 3 * len(METODOS)


def test_convergencia_valores_ejes_log_y_umbral(defecto):
    fig = p1.figura_convergencia(defecto)
    assert fig.layout.xaxis.type == "log" and fig.layout.yaxis.type == "log"
    tr = next(t for t in fig.data if t.meta == "mediana:rosenbrock:2:pso:defecto")
    assert tr.x[0] == 1 and tr.x[-1] == 100  # rejilla de 1 al presupuesto
    assert tr.y[-1] == pytest.approx(np.median([4 * 10.0 ** (-s) for s in SEMILLAS]))  # método i = 3
    (linea,) = fig.layout.shapes
    assert linea.y0 == linea.y1 == UMBRAL_PRINCIPAL
    assert any("umbral" in a.text.lower() and a.y == pytest.approx(math.log10(UMBRAL_PRINCIPAL))
               for a in fig.layout.annotations)
    assert "evaluaciones equivalentes" in fig.layout.xaxis.title.text.lower()


def test_convergencia_la_banda_dibuja_los_cuartiles_25_y_75(defecto):
    # pso es el método i = 3 de los sintéticos: historial de la semilla s = (1, 50 + s), (10 + s, 5), (40, 4·10^−s)
    fig = p1.figura_convergencia(defecto)
    banda = {q: next(t for t in fig.data if t.meta == f"{q}:rosenbrock:2:pso:defecto") for q in ("q25", "q75")}
    a_mano = {  # x: (q25, q75) con interpolación lineal sobre las 3 corridas
        1: (50.5, 51.5),    # 50, 51, 52
        11: (5.0, 28.5),    # 5, 5, 52 (la semilla 2 mejora en x = 12)
        100: (0.22, 2.2),   # 0,04; 0,4; 4
    }
    for x, (q25, q75) in a_mano.items():
        i = list(banda["q25"].x).index(x)
        assert list(banda["q75"].x)[i] == x
        assert banda["q25"].y[i] == pytest.approx(q25) and banda["q75"].y[i] == pytest.approx(q75)


def test_convergencia_aplica_el_piso_y_lo_declara(defecto):
    fig = p1.figura_convergencia(defecto)
    de = next(t for t in fig.data if t.meta == "mediana:rastrigin:3:de:defecto")
    assert de.y[-1] == p1.PISO_LOG  # f − f* = 0 exacto no cabe en un eje log
    for prefijo in ("mediana", "q25", "q75"):
        for tr in _trazas(fig, prefijo):
            assert all(v is None or v >= p1.PISO_LOG for v in tr.y)
    assert "1e-16" in fig.layout.yaxis.title.text and p1.TEXTO_PISO in fig.layout.title.subtitle.text


def test_convergencia_sin_registro_deja_hueco(defecto):
    fig = p1.figura_convergencia(defecto)
    gd = next(t for t in fig.data if t.meta == "mediana:rosenbrock:2:gdfijo:defecto")
    assert gd.y[0] is not None  # GD registra en eval_equiv = 0
    tardio = {("rosenbrock", 2, "pso"): [dict(c, result=dict(c["result"], history=c["result"]["history"][1:]))
                                         for c in defecto[("rosenbrock", 2, "pso")]]}
    tr = next(t for t in p1.figura_convergencia(tardio).data if t.meta.startswith("mediana"))
    assert tr.y[0] is None and tr.y[-1] is not None


def test_convergencia_afinada_solo_metodos_que_cambiaron_y_distingue_por_trazo(defecto, afinado):
    fig = p1.figura_convergencia(defecto, afinado, AFINADOS)
    medianas = _trazas(fig, "mediana")
    vistos = {}
    for tr in medianas:
        _, func, dim, method, variante = tr.meta.split(":")
        vistos.setdefault((func, int(dim)), []).append((method, variante))
        assert tr.line.color == p.COLOR_METODO[method]  # el color sigue al método, no a la variante
        assert tr.line.dash == {"defecto": "solid", "afinado": "dash"}[variante]
        assert tr.name == f"{p.NOMBRE_METODO[method]} · {p1.NOMBRE_VARIANTE[variante]}"
    assert vistos == {c: [(m, v) for m in ms for v in ("defecto", "afinado")] for c, ms in AFINADOS.items()}
    ea_d = next(t for t in medianas if t.meta == "mediana:rastrigin:2:ea:defecto")
    ea_a = next(t for t in medianas if t.meta == "mediana:rastrigin:2:ea:afinado")
    assert ea_a.y[-1] == pytest.approx(0.5 * ea_d.y[-1])
    (menu,) = fig.layout.updatemenus
    assert len(menu.buttons) == len(CELDAS)


def test_figuras_afinadas_omiten_las_celdas_sin_cambios(defecto, afinado):
    cambios = {**AFINADOS, ("rastrigin", 3): []}
    for fig in (p1.figura_convergencia(defecto, afinado, cambios), p1.figura_cajas(defecto, afinado, cambios)):
        (menu,) = fig.layout.updatemenus
        assert [b.label for b in menu.buttons] == ["Rosenbrock 2D", "Rosenbrock 3D", "Rastrigin 2D"]
        assert not any(":rastrigin:3:" in tr.meta for tr in fig.data)


# --------------------------------------------------------------------------------------------- cajas


def test_cajas_por_metodo_con_todos_los_puntos_y_eje_log(defecto):
    fig = p1.figura_cajas(defecto)
    cajas = _trazas(fig, "caja")
    assert len(cajas) == len(CELDAS) * len(METODOS)
    for tr in cajas:
        _, func, dim, method, variante = tr.meta.split(":")
        assert tr.type == "box" and tr.boxpoints == "all" and len(tr.y) == len(SEMILLAS)
        assert tr.line.color == tr.marker.color == p.COLOR_METODO[method]
        assert set(tr.x) == {p.NOMBRE_METODO[method]}
    assert fig.layout.yaxis.type == "log" and "1e-16" in fig.layout.yaxis.title.text
    assert p1.TEXTO_PISO in fig.layout.title.subtitle.text
    de = next(t for t in cajas if t.meta == "caja:rosenbrock:2:de:defecto")
    assert list(de.y) == [p1.PISO_LOG] * len(SEMILLAS)
    pso = next(t for t in cajas if t.meta == "caja:rosenbrock:2:pso:defecto")
    assert sorted(pso.y) == pytest.approx(sorted(4 * 10.0 ** (-s) for s in SEMILLAS))
    (menu,) = fig.layout.updatemenus
    assert [b.label for b in menu.buttons] == ["Rosenbrock 2D", "Rosenbrock 3D", "Rastrigin 2D", "Rastrigin 3D"]
    assert sum(menu.buttons[2].args[0]["visible"]) == len(METODOS)


def test_cajas_afinadas_emparejadas_y_distinguidas_por_relleno(defecto, afinado):
    fig = p1.figura_cajas(defecto, afinado, AFINADOS)
    cajas = _trazas(fig, "caja")
    assert [tr.meta for tr in cajas if ":rastrigin:2:" in tr.meta] == ["caja:rastrigin:2:ea:defecto",
                                                                      "caja:rastrigin:2:ea:afinado"]
    por_variante = {}
    for tr in cajas:
        _, func, dim, method, variante = tr.meta.split(":")
        assert tr.line.color == p.COLOR_METODO[method]
        assert p1.NOMBRE_VARIANTE[variante] in tr.x[0] and p.NOMBRE_METODO[method] in tr.x[0]
        por_variante.setdefault(variante, set()).add((tr.fillcolor == p.SUPERFICIE, tr.marker.symbol))
    assert por_variante["defecto"] == {(False, "circle")} and por_variante["afinado"] == {(True, "circle-open")}


# ----------------------------------------------------------------------------------- deslizador de η


def test_eta_un_paso_por_eta_y_marcas():
    datos = eta_json()
    fig = p1.figura_eta(datos)
    trayectorias = _trazas(fig, "eta")
    assert len(trayectorias) == len(datos["etas"])
    (slider,) = fig.layout.sliders
    assert len(slider.steps) == len(datos["etas"])
    assert slider.active == 1  # arranca en el η por defecto
    assert [tr.visible for tr in trayectorias] == [False, True, False, False]
    for k, (paso, e) in enumerate(zip(slider.steps, datos["etas"])):
        visibles = [tr.meta for tr, v in zip(fig.data, paso.args[0]["visible"]) if v]
        assert visibles == ["contorno", f"eta:{k}", "x0", "x_star"]
        titulo = paso.args[1]["title.text"] + paso.args[1]["title.subtitle.text"]
        assert str(e["n_iter"]) in titulo and "η" in titulo
        # el valor mostrado es f_best − f* de la entrada (sintético: f_best = 2·η), rotulado como "mejor visto"
        mostrado = ["2e-5", "2e-3", "3e-3", "2e-2"][k]
        subtitulo = paso.args[1]["title.subtitle.text"]
        assert f"Mejor f − f* visto = {mostrado} ·" in subtitulo and "f final" not in titulo
        assert ("por defecto" in paso.label) == (e["marca"] == "defecto")
        assert ("afinado" in paso.label) == (e["marca"] == "afinado")
        assert ("por defecto" in paso.args[1]["title.text"]) == (e["marca"] == "defecto")
        assert ("afinado" in paso.args[1]["title.text"]) == (e["marca"] == "afinado")
    assert fig.layout.title.text == slider.steps[1].args[1]["title.text"]


def test_eta_trayectoria_puntos_color_y_marcadores():
    datos = eta_json()
    fig = p1.figura_eta(datos)
    tr = next(t for t in fig.data if t.meta == "eta:2")
    assert tr.line.color == p.COLOR_METODO["gdfijo"]
    assert np.column_stack([tr.x, tr.y]) == pytest.approx(np.array(datos["etas"][2]["puntos"]), abs=1e-5)
    assert list(tr.customdata) == datos["etas"][2]["iteraciones"]
    x0 = next(t for t in fig.data if t.meta == "x0")
    assert [x0.x[0], x0.y[0]] == datos["meta"]["x0"]
    optimo = next(t for t in fig.data if t.meta == "x_star")
    assert [optimo.x[0], optimo.y[0]] == [1.0, 1.0]


def test_eta_sin_marca_por_defecto_arranca_en_el_primero():
    datos = eta_json()
    datos["etas"] = [e for e in datos["etas"] if e["marca"] is None]
    assert p1.figura_eta(datos).layout.sliders[0].active == 0


# ------------------------------------------------------------------------------------------ enjambre


def test_enjambre_superficie_particulas_y_deslizador(defecto):
    corrida = defecto[("rastrigin", 2, "pso")][0]
    frames = corrida["result"]["frames"]
    fig = p1.figura_enjambre(corrida)
    assert next(tr for tr in fig.data if tr.meta == "superficie").type == "surface"
    enjambres = _trazas(fig, "enjambre")
    (slider,) = fig.layout.sliders
    assert len(slider.steps) == len(enjambres) == len(frames)  # 6 frames < pasos máximos: se muestran todos
    assert [s.label for s in slider.steps][0] == "0" and slider.steps[-1].label == str(frames[-1]["iter"])
    f = get_function("rastrigin", 2).f
    for tr, frame in zip(enjambres, frames):
        assert tr.marker.color == p.COLOR_METODO["pso"]
        assert np.column_stack([tr.x, tr.y]) == pytest.approx(np.array(frame["positions"]), abs=1e-5)
        assert list(tr.z) == pytest.approx([f(q) for q in frame["positions"]], rel=1e-5)
    assert [tr.visible for tr in enjambres] == [True] + [False] * (len(frames) - 1)


def test_muestreo_geometrico_incluye_el_primero_y_el_ultimo():
    idx = p1.muestreo(666, p1.PASOS_ENJAMBRE)
    assert idx[0] == 0 and idx[-1] == 665 and np.all(np.diff(idx) > 0)
    assert 20 <= idx.size <= p1.PASOS_ENJAMBRE
    assert list(p1.muestreo(3, p1.PASOS_ENJAMBRE)) == [0, 1, 2]


# ---------------------------------------------------------------------------------------------- humo


@pytest.fixture
def carpetas(tmp_path, defecto, afinado):
    d, a = tmp_path / "part1", tmp_path / "part1_tuned"
    escribir_experimento(d, defecto)
    escribir_experimento(a, afinado)
    save_json(d / "eta_deslizador.json", eta_json())
    return d, a, tmp_path / "figuras"


def _nombres(rutas):
    return {r.name for r in rutas}


def test_humo_genera_las_8_figuras(carpetas, capsys):
    d, a, salida = carpetas
    rutas = p1.generar_part1(d, a, salida=salida)
    assert [r.name for r in rutas] == [f.archivo for f in p1.FIGURAS.values()]
    for r in rutas:
        texto = r.read_text(encoding="utf-8")
        assert r.parent == salida and "Plotly.newPlot" in texto and "<html" not in texto
        assert r.stat().st_size < p1.TAMANO_MAX
    assert "AVISO" not in capsys.readouterr().out
    # determinista: regenerar da los mismos bytes
    otra = p1.generar_part1(d, a, salida=salida.parent / "otra")
    assert {r.name: r.read_bytes() for r in rutas} == {r.name: r.read_bytes() for r in otra}


def test_humo_detecta_los_metodos_afinados_desde_los_json(carpetas):
    d, a, salida = carpetas
    p1.generar_part1(d, a, salida=salida)
    texto = (salida / "part1_cajas_afinado.html").read_text(encoding="utf-8")
    assert "caja:rosenbrock:2:gdfijo:afinado" in texto and "caja:rosenbrock:2:ea:afinado" in texto
    assert "caja:rastrigin:2:gdfijo:" not in texto and ":pso:" not in texto and ":gdarmijo:" not in texto


def test_faltan_las_corridas_por_defecto_solo_contornos(tmp_path, capsys):
    rutas = p1.generar_part1(tmp_path / "nada", tmp_path / "nada_tuned", salida=tmp_path / "figuras")
    assert _nombres(rutas) == SIN_CORRIDAS
    salida = capsys.readouterr().out
    assert "AVISO" in salida and "python run.py part1 --config configs/part1/base.yaml" in salida
    assert "python scripts/part1_eta_deslizador.py" in salida


def test_corridas_por_defecto_incompletas_no_lanza(carpetas, defecto, capsys):
    d, a, salida = carpetas
    (d / "runs" / "rastrigin_3d_de_seed2.json").unlink()
    rutas = p1.generar_part1(d, a, salida=salida)
    assert _nombres(rutas) == SIN_CORRIDAS | CON_ETA  # el JSON de η no depende de runs/
    assert "faltan 1 de" in capsys.readouterr().out


def test_faltan_las_afinadas(carpetas, capsys):
    d, _, salida = carpetas
    rutas = p1.generar_part1(d, salida.parent / "no_hay", salida=salida)
    assert _nombres(rutas) == SIN_CORRIDAS | CON_DEFECTO | CON_ETA
    salida_txt = capsys.readouterr().out
    assert "python run.py part1 --config configs/part1/tuned.yaml" in salida_txt
    assert "part1_convergencia_afinado.html" in salida_txt and "part1_cajas_afinado.html" in salida_txt


def test_falta_el_json_de_eta(carpetas, capsys):
    d, a, salida = carpetas
    (d / "eta_deslizador.json").unlink()
    rutas = p1.generar_part1(d, a, salida=salida)
    assert _nombres(rutas) == SIN_CORRIDAS | CON_DEFECTO | CON_AFINADO
    salida_txt = capsys.readouterr().out
    assert "python scripts/part1_eta_deslizador.py" in salida_txt and "part1_eta_rosenbrock.html" in salida_txt


def test_afinado_no_comparable_es_un_error(carpetas, defecto):
    d, a, salida = carpetas
    escribir_experimento(a, experimento(config=config_afinada(), semillas=(5, 6, 7)), semillas=(5, 6, 7))
    with pytest.raises(ValueError, match="semillas"):
        p1.generar_part1(d, a, salida=salida)


def test_sin_metodos_afinados_avisa_y_no_genera_la_comparacion(carpetas, defecto, capsys):
    d, a, salida = carpetas
    escribir_experimento(a, defecto)
    rutas = p1.generar_part1(d, a, salida=salida)
    assert _nombres(rutas) == SIN_CORRIDAS | CON_DEFECTO | CON_ETA
    assert "ningún método" in capsys.readouterr().out


# ------------------------------------------------------------------------------------- run.py figures


def test_run_py_figures_genera_la_parte_1_e_imprime_los_bloques(carpetas, tmp_path, monkeypatch, capsys):
    d, a, salida = carpetas
    monkeypatch.setattr(p1, "RES_DEFECTO", d)
    monkeypatch.setattr(p1, "RES_AFINADO", a)
    monkeypatch.setattr(p1, "SALIDA", salida)
    monkeypatch.setattr(figuras, "GENERADORES", {"Parte 1": figuras.GENERADORES["Parte 1"]})
    assert cli.main(["figures"]) == 0
    texto = capsys.readouterr().out
    assert "Parte 1: 8 figuras" in texto
    assert not [linea for linea in texto.splitlines() if "pendientes" in linea]  # T4.3: ya no queda nada pendiente
    for f in p1.FIGURAS.values():
        assert p1.bloque_blog(f) in texto and (salida / f.archivo).is_file()
    assert texto.index(str(salida / "part1_cajas.html")) < texto.index("::: figura contorno-rosenbrock")


def test_run_py_figures_sin_corridas_devuelve_0_y_solo_bloques_de_lo_generado(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(p1, "RES_DEFECTO", tmp_path / "nada")
    monkeypatch.setattr(p1, "RES_AFINADO", tmp_path / "nada_tuned")
    monkeypatch.setattr(p1, "SALIDA", tmp_path / "figuras")
    monkeypatch.setattr(figuras, "GENERADORES", {"Parte 1": figuras.GENERADORES["Parte 1"]})
    assert cli.main(["figures"]) == 0
    texto = capsys.readouterr().out
    assert "::: figura contorno-rastrigin" in texto and "::: figura convergencia-part1" not in texto


def test_generadores_y_pendientes():
    assert list(figuras.GENERADORES) == ["Parte 2", "GIF Parte 2", "Parte 1", "GIF Parte 1"]
    assert figuras.PENDIENTES == {}


# ------------------------------------------------------------------------------------- datos reales


@pytest.mark.parametrize("carpeta, variante", [(p1.RES_DEFECTO, "defecto"), (p1.RES_AFINADO, "afinado")])
def test_datos_reales_la_mediana_final_coincide_con_summary(carpeta, variante):
    try:
        exp = pd1.cargar_experimento(carpeta)
    except pd1.DatosFaltantes as e:
        pytest.skip(f"sin corridas reales: {e}")
    corridas = exp["corridas"]
    esperado = {(c["func"], c["dim"], c["method"]): c["f_final"]["mediana"] for c in exp["resumen"]["configuraciones"]}
    assert set(esperado) == set(corridas)
    if variante == "defecto":
        conv, cajas = p1.figura_convergencia(corridas), p1.figura_cajas(corridas)
    else:  # las corridas afinadas en el papel de "afinado"; como "por defecto" se pasan ellas mismas
        todos = {celda: pd1.metodos_de(corridas, *celda) for celda in pd1.celdas(corridas)}
        conv, cajas = p1.figura_convergencia(corridas, corridas, todos), p1.figura_cajas(corridas, corridas, todos)
    vistas = 0
    for prefijo, fig in (("mediana", conv), ("caja", cajas)):
        for tr in _trazas(fig, prefijo):
            _, func, dim, method, var = tr.meta.split(":")
            if var != variante:
                continue
            mediana = tr.y[-1] if prefijo == "mediana" else float(np.median(tr.y))
            f_star = get_function(func, int(dim)).f_star  # summary guarda f; la figura, f − f*
            assert mediana == pytest.approx(max(esperado[(func, int(dim), method)] - f_star, p1.PISO_LOG), rel=1e-5)
            vistas += 1
    assert vistas == 2 * len(esperado)
