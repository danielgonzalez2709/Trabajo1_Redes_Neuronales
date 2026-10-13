"""Pruebas de T4.3 (Spec §6.7): GIF de la Parte 1 (trayectorias del GD y enjambre del PSO en 2D).

Datos sintéticos pequeños (contrato de results/data/part1/gif_trayectorias.json) en tmp_path; solo
`test_archivo_real_*` usa el JSON versionado.
"""

import json

import numpy as np
import pytest
from matplotlib.contour import ContourSet
from PIL import Image

from src.common import cli
from src.part1.functions import get_function
from src.viz import figuras
from src.viz import paleta as p
from src.viz import part1_gifs as g

METODOS_GD = ("gdfijo", "gdarmijo")


def _rgb(hex_color: str) -> np.ndarray:
    return np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def _variante(n_iter, x, f):
    return {"n_iter": n_iter, "f_best": f[-1], "n_f": 4 * n_iter, "n_grad": n_iter, "x": x, "f": f}


def _datos(base_seed=0):
    """Rosenbrock: gdarmijo termina en la iteración 3 (marcas 5 y 20 la sostienen). Rastrigin: marca 1 234.
    Las variantes terminan en puntos alejados entre sí y de x*, x0 y el resto de los trazos."""
    rng = np.random.default_rng(0)
    enjambre = [[[4.5, -4.5]] + rng.uniform(-3.0, 3.0, size=(29, 2)).tolist() for _ in range(3)]
    return {
        "meta": {"config": "configs/part1/base.yaml", "base_seed": base_seed, "run_id": 0, "dim": 2, "k": 4.0,
                 "budget": 20000.0, "marcas_max": 4},
        "gd": {
            "rosenbrock": {"iteraciones": [0, 1, 5, 20], "metodos": {
                "gdfijo": _variante(20, [[-1.2, 1.0], [-1.0, 0.6], [-0.8, 0.4], [-0.5, 0.25]],
                                    [24.2, 4.97, 3.3, 2.25]),
                "gdarmijo": _variante(3, [[-1.2, 1.0], [0.0, 1.5], [0.6, 0.36], [0.6, 0.36]],
                                      [24.2, 12.3, 0.16, 0.16]),
            }},
            "rastrigin": {"iteraciones": [0, 2, 1234], "metodos": {
                "gdfijo": _variante(2000, [[3.0, -3.5], [2.5, -1.0], [-2.0, -3.0]], [40.0, 30.0, 0.00188]),
                "gdarmijo": _variante(2, [[3.0, -3.5], [2.0, 3.0], [2.0, 3.0]], [40.0, 17.0, 17.0]),
            }},
        },
        "pso": {"rastrigin": {"iteraciones": [0, 1, 2], "n_iter": 2, "f_best": 0.00188, "n_f": 90,
                              "enjambre": enjambre, "mejor": [[1.0, 1.0], [1.5, 1.5], [1.0, 1.5]],
                              "f_mejor": [12.3, 4.97, 0.00188]}},
    }


def _escribir(carpeta, datos=None):
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "gif_trayectorias.json"
    ruta.write_text(json.dumps(_datos() if datos is None else datos), encoding="utf-8")
    return ruta


def _por_gid(fig, gid):
    return [a for ax in fig.axes for a in [*ax.lines, *ax.collections] if a.get_gid() == gid]


def _textos(fig):
    return {t.get_gid(): t.get_text() for t in fig.texts}


def _pixel(img: Image.Image, fig, xy) -> np.ndarray:
    """Color medio de una vecindad 3×3 en la posición de datos `xy` (el fotograma ya rasterizado de `fig`)."""
    ax = fig.axes[0]
    px, py = ax.transData.transform(xy)
    arr = np.asarray(img.convert("RGB"), dtype=float)
    fila, col = int(round(arr.shape[0] - py)), int(round(px))
    return arr[fila - 1:fila + 2, col - 1:col + 2].reshape(-1, 3).mean(axis=0)


def _fotograma_gif(ruta, j) -> Image.Image:
    with Image.open(ruta) as im:
        im.seek(j)
        return im.convert("RGB")


# ------------------------------------------------------------------------------------------ formato


@pytest.mark.parametrize("valor, texto", [
    (0.0, "0"), (-0.0, "0"), (4.97, "4,97"), (5.0, "5,00"), (12.34, "12,3"), (123.4, "123"), (0.0188, "0,0188"),
    (0.01, "0,0100"), (0.00188, "1,88e-3"), (1e-16, "1,00e-16"), (1234.5, "1,23e3"), (999.7, "1,00e3"),
    (-4.97, "-4,97"), (-0.00188, "-1,88e-3"), (0.009996, "0,0100"),
])
def test_formateador_de_f_con_tres_cifras_y_coma(valor, texto):
    assert g._cifras3(valor) == texto


# ------------------------------------------------------------------------------------------ constantes


def test_constantes_y_paleta():
    assert g.MS_FOTOGRAMA == 200 and g.MS_FINAL == 3000 and g.TAMANO == (6.4, 6.2) and g.DPI == 100
    assert g.COLORES_GIF <= 128
    assert g.COLOR_GDFIJO == p.COLOR_METODO["gdfijo"]
    assert g.COLOR_GDARMIJO == p.COLOR_METODO["gdarmijo"]
    assert g.COLOR_PSO == p.COLOR_METODO["pso"]
    assert list(g.ARCHIVOS.values()) == ["gd_rosenbrock_2d.gif", "gd_rastrigin_2d.gif", "pso_rastrigin_2d.gif"]
    assert g.DATOS == g.RAIZ / "results" / "data" / "part1" / "gif_trayectorias.json"
    assert g.SALIDA == g.RAIZ / "media"


# ------------------------------------------------------------------------------------------ figura del GD


@pytest.mark.parametrize("func", ["rosenbrock", "rastrigin"])
def test_figura_gd_series_con_su_color_estilo_y_leyenda(func):
    d = _datos()
    fig = g.figura_gd(d, func, 1)
    ax = fig.axes[0]
    estilo = {"gdfijo": ("-", "o"), "gdarmijo": ("--", "s")}
    for m in METODOS_GD:
        (camino,), (marca,) = _por_gid(fig, f"camino:{m}"), _por_gid(fig, f"marca:{m}")
        assert camino.get_color() == p.COLOR_METODO[m] and camino.get_linestyle() == estilo[m][0]
        assert marca.get_markerfacecolor() == p.COLOR_METODO[m] and marca.get_marker() == estilo[m][1]
    leyenda = {t.get_text(): h for t, h in zip(ax.get_legend().get_texts(), ax.get_legend().legend_handles)}
    for m in METODOS_GD:
        h = leyenda[p.NOMBRE_METODO[m]]
        assert h.get_color() == p.COLOR_METODO[m] and h.get_marker() == estilo[m][1]
    assert "Punto inicial" in leyenda and any(t.startswith("Mínimo global") for t in leyenda)
    for t in fig.texts:
        assert t.get_color() in (p.TINTA, p.TINTA_SECUNDARIA)


@pytest.mark.parametrize("func", ["rosenbrock", "rastrigin"])
def test_figura_gd_fondo_ejes_x0_y_optimo(func):
    d = _datos()
    fig = g.figura_gd(d, func, 2)
    ax = fig.axes[0]
    f = get_function(func, 2)
    assert ax.get_xlim() == tuple(f.bounds[0]) and ax.get_ylim() == tuple(f.bounds[1])
    assert ax.get_aspect() == 1.0
    assert sum(isinstance(c, ContourSet) for c in ax.collections) == 1
    (x0,) = _por_gid(fig, "x0")
    assert np.allclose(x0.get_xydata(), [d["gd"][func]["metodos"]["gdfijo"]["x"][0]])
    (estrella,) = _por_gid(fig, "x_star")
    assert np.allclose(estrella.get_xydata(), [f.x_star]) and estrella.get_markerfacecolor() == p.TINTA


def test_camino_del_fotograma_j_termina_en_x_j():
    d = _datos()
    for j in range(4):
        fig = g.figura_gd(d, "rosenbrock", j)
        for m in METODOS_GD:
            x = d["gd"]["rosenbrock"]["metodos"][m]["x"]
            (camino,), (marca,) = _por_gid(fig, f"camino:{m}"), _por_gid(fig, f"marca:{m}")
            assert np.allclose(camino.get_xydata(), x[:j + 1])
            assert np.allclose(marca.get_xydata(), [x[j]])


def test_rotulos_terminado_solo_si_la_marca_supera_n_iter_y_titulo_con_la_semilla():
    d = _datos()
    t1 = _textos(g.figura_gd(d, "rosenbrock", 1))
    assert t1["rotulo:gdfijo"] == "GD (paso fijo): iteración 1 · f = 4,97"
    assert t1["rotulo:gdarmijo"] == "GD (Armijo): iteración 1 · f = 12,3"
    t2 = _textos(g.figura_gd(d, "rosenbrock", 2))
    assert "terminó" not in t2["rotulo:gdfijo"]
    assert t2["rotulo:gdarmijo"] == "GD (Armijo): iteración 3, terminó · f = 0,160"
    assert t2["titulo"] == "Descenso por gradiente en Rosenbrock 2D · semilla 0 · configuración por defecto"
    assert t2["nota"] == ("Una sola corrida (semilla 0): ilustra la trayectoria, no el comportamiento medio.")
    t3 = _textos(g.figura_gd(d, "rastrigin", 2))
    assert t3["rotulo:gdfijo"] == "GD (paso fijo): iteración 1 234 · f = 1,88e-3"
    assert t3["rotulo:gdarmijo"] == "GD (Armijo): iteración 2, terminó · f = 17,0"
    # marca = n_iter (2): la variante aún no "supera" su última iteración
    assert _textos(g.figura_gd(d, "rastrigin", 1))["rotulo:gdarmijo"] == "GD (Armijo): iteración 2 · f = 17,0"
    otra = _datos(base_seed=3)
    otra["meta"]["run_id"] = 2  # semilla = base_seed + run_id
    t4 = _textos(g.figura_gd(otra, "rastrigin", 0))
    assert t4["titulo"] == "Descenso por gradiente en Rastrigin 2D · semilla 5 · configuración por defecto"
    assert "(semilla 5)" in t4["nota"]


# ------------------------------------------------------------------------------------------ figura del PSO


def test_figura_pso_particulas_mejor_y_textos():
    d = _datos()
    fig = g.figura_pso(d, 2)
    ax = fig.axes[0]
    (part,) = _por_gid(fig, "enjambre")
    assert np.allclose(part.get_xydata(), d["pso"]["rastrigin"]["enjambre"][2])
    assert part.get_markerfacecolor() == p.COLOR_METODO["pso"] and part.get_markeredgecolor() == p.TINTA
    (mejor,) = _por_gid(fig, "mejor")
    (estrella,) = _por_gid(fig, "x_star")
    assert np.allclose(mejor.get_xydata(), [d["pso"]["rastrigin"]["mejor"][2]])
    assert (mejor.get_markerfacecolor(), mejor.get_markersize()) != (estrella.get_markerfacecolor(),
                                                                      estrella.get_markersize())
    textos = {t.get_text() for t in ax.get_legend().get_texts()}
    assert {"Mejor del enjambre", "Partículas (30)"} <= textos
    t = _textos(fig)
    assert t["titulo"] == "PSO en Rastrigin 2D · semilla 0 · configuración por defecto"
    assert t["rotulo"] == "Iteración 2 · mejor f = 1,88e-3"
    # en la marca 0 el rótulo usa f_mejor[0], no f_best de la corrida
    assert _textos(g.figura_pso(d, 0))["rotulo"] == "Iteración 0 · mejor f = 12,3"
    assert t["nota"] == "Una sola corrida (semilla 0): ilustra la trayectoria, no el comportamiento medio."
    assert ax.get_aspect() == 1.0 and ax.get_xlim() == (-5.12, 5.12)


# ------------------------------------------------------------------------------------------ GIF


@pytest.fixture(scope="module")
def generados(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("generados")
    ruta = _escribir(carpeta / "datos")
    return ruta, g.generar_gifs(datos=ruta, salida=carpeta / "gif")


def test_nombres_orden_y_fotogramas(generados):
    ruta, rutas = generados
    assert [r.name for r in rutas] == ["gd_rosenbrock_2d.gif", "gd_rastrigin_2d.gif", "pso_rastrigin_2d.gif"]
    d = _datos()
    esperados = [len(d["gd"]["rosenbrock"]["iteraciones"]), len(d["gd"]["rastrigin"]["iteraciones"]),
                 len(d["pso"]["rastrigin"]["iteraciones"])]
    for r, n in zip(rutas, esperados):
        with Image.open(r) as im:
            assert im.n_frames == n
            duraciones = []
            for i in range(im.n_frames):
                im.seek(i)
                duraciones.append(im.info["duration"])
            assert im.info["loop"] == 0
        assert duraciones[:-1] == [g.MS_FOTOGRAMA] * (n - 1) and duraciones[-1] > g.MS_FOTOGRAMA


def test_pixel_del_marcador_de_cada_serie_tiene_su_color(generados):
    _, rutas = generados
    d = _datos()
    for ruta, func in zip(rutas[:2], ("rosenbrock", "rastrigin")):
        j = len(d["gd"][func]["iteraciones"]) - 1
        fig = g.figura_gd(d, func, j)
        g.imagen(fig)  # fija la geometría de los ejes (aspecto 1:1) como en el GIF
        img = _fotograma_gif(ruta, j)
        for m in METODOS_GD:
            xy = d["gd"][func]["metodos"][m]["x"][j]
            assert np.linalg.norm(_pixel(img, fig, xy) - _rgb(p.COLOR_METODO[m])) < 30, (func, m)
    # fondo estático: una esquina sin trazos es igual en el primer y el último fotograma
    fig = g.figura_gd(d, "rosenbrock", 0)
    g.imagen(fig)
    primero, ultimo = _fotograma_gif(rutas[0], 0), _fotograma_gif(rutas[0], 3)
    assert np.array_equal(_pixel(primero, fig, (1.9, -1.9)), _pixel(ultimo, fig, (1.9, -1.9)))
    fig = g.figura_pso(d, 2)
    g.imagen(fig)
    img = _fotograma_gif(rutas[2], 2)
    assert np.linalg.norm(_pixel(img, fig, (4.5, -4.5)) - _rgb(p.COLOR_METODO["pso"])) < 30


def _datos_colapso():
    """PSO como en la corrida real: enjambre disperso al principio y las 30 partículas en x* al final."""
    d = _datos()
    rng = np.random.default_rng(1)
    pso = d["pso"]["rastrigin"]
    pso["iteraciones"] = [0, 1, 2, 3]
    pso["enjambre"] = [rng.uniform(-5.0, 5.0, size=(30, 2)).tolist(), rng.uniform(-2.0, 2.0, size=(30, 2)).tolist(),
                       [[0.01, -0.01]] * 30, [[0.0, 0.0]] * 30]
    pso["mejor"] = [[1.0, 1.0], [0.5, 0.5], [0.0, 0.0], [0.0, 0.0]]
    pso["f_mejor"] = [12.3, 4.97, 0.0188, 0.0]
    return d


def _pixel_display(img: Image.Image, xy_display) -> np.ndarray:
    arr = np.asarray(img.convert("RGB"), dtype=float)
    fila, col = int(round(arr.shape[0] - xy_display[1])), int(round(xy_display[0]))
    return arr[fila, col]


def _centro_leyenda(fig, etiqueta):
    """Posición (píxeles) del marcador de la leyenda con texto `etiqueta`."""
    leyenda = fig.axes[0].get_legend()
    for texto, h in zip(leyenda.get_texts(), leyenda.legend_handles):
        if texto.get_text() == etiqueta:
            puntos = h.get_transform().transform(h.get_xydata())
            return puntos.mean(axis=0)
    raise KeyError(etiqueta)


def test_paleta_comun_colores_de_la_leyenda_y_fondo_estables(tmp_path):
    d = _datos_colapso()
    ruta = _escribir(tmp_path / "datos", d)
    rutas = g.generar_gifs(datos=ruta, salida=tmp_path / "gif")
    casos = [(rutas[0], g.figura_gd(d, "rosenbrock", 0), [p.NOMBRE_METODO[m] for m in METODOS_GD], (1.9, -1.9)),
             (rutas[2], g.figura_pso(d, 0), ["Partículas (30)"], (4.9, 4.9))]
    for ruta_gif, fig, etiquetas, esquina in casos:
        g.imagen(fig)
        with Image.open(ruta_gif) as im:
            n = im.n_frames
        fotos = [_fotograma_gif(ruta_gif, j) for j in range(n)]
        for etiqueta in etiquetas:
            pos = _centro_leyenda(fig, etiqueta)
            colores = [_pixel_display(f, pos) for f in fotos]
            metodo = next((m for m in METODOS_GD if p.NOMBRE_METODO[m] == etiqueta), "pso")
            for c in colores:
                assert np.array_equal(c, colores[0]), (ruta_gif.name, etiqueta, colores)
            assert np.linalg.norm(colores[0] - _rgb(p.COLOR_METODO[metodo])) < 30, (etiqueta, colores[0])
        fondo = [_pixel(f, fig, esquina) for f in fotos]
        assert all(np.array_equal(c, fondo[0]) for c in fondo), (ruta_gif.name, fondo)


def test_el_mejor_del_enjambre_no_tapa_las_particulas():
    fig = g.figura_pso(_datos_colapso(), 3)
    (mejor,) = _por_gid(fig, "mejor")
    (part,) = _por_gid(fig, "enjambre")
    assert mejor.get_markerfacecolor() == "none" and mejor.get_markeredgecolor() == p.TINTA
    leyenda = {t.get_text(): h for t, h in zip(fig.axes[0].get_legend().get_texts(),
                                               fig.axes[0].get_legend().legend_handles)}
    assert leyenda["Mejor del enjambre"].get_markerfacecolor() == "none"


def test_mismos_datos_mismos_bytes(generados, tmp_path):
    ruta, a = generados
    b = g.generar_gifs(datos=ruta, salida=tmp_path / "b")  # otra carpeta, otra generación
    assert [x.parent for x in a] != [y.parent for y in b]
    for x, y in zip(a, b):
        assert x.read_bytes() == y.read_bytes()


def test_solo_lee_el_json_de_trayectorias(tmp_path, monkeypatch):
    ruta = _escribir(tmp_path / "solo")
    assert sorted(q.name for q in ruta.parent.iterdir()) == ["gif_trayectorias.json"]
    leidos = []
    original = g.load_json

    def espia(r):
        leidos.append(r)
        return original(r)

    monkeypatch.setattr(g, "load_json", espia)
    rutas = g.generar_gifs(datos=ruta, salida=tmp_path / "salida")
    assert len(rutas) == 3 and all(r.is_file() and r.parent == tmp_path / "salida" for r in rutas)
    assert [str(r) for r in leidos] == [str(ruta)]


def test_salida_none_usa_salida_del_modulo(tmp_path, monkeypatch):
    ruta = _escribir(tmp_path / "datos")
    monkeypatch.setattr(g, "SALIDA", tmp_path / "media")
    rutas = g.generar_gifs(datos=ruta)
    assert all(r.parent == tmp_path / "media" for r in rutas)


# ------------------------------------------------------------------------------------------ blog


def test_bloques_blog_formato_e_ids(generados):
    _, rutas = generados
    texto = g.bloques_blog(rutas)
    bloques = texto.split("\n\n")
    assert len(bloques) == 3
    ids = ["gif-gd-rosenbrock", "gif-gd-rastrigin", "gif-pso-rastrigin"]
    for bloque, id_, archivo in zip(bloques, ids, g.ARCHIVOS.values()):
        lineas = bloque.split("\n")
        assert lineas[0] == f"::: figura {id_}" and lineas[-1] == ":::" and len(lineas) == 5
        assert lineas[1].startswith("Título: ") and len(lineas[1]) > len("Título: ") + 10
        assert lineas[2] == ("Fuente: Elaboración propia a partir de results/data/part1/gif_trayectorias.json "
                             "(python run.py figures). Corrida con la semilla 0, configuración por defecto.")
        alt, img = lineas[3].removeprefix("![").split("](")
        assert alt.strip() and img == f"figures/{archivo})"
        for prohibido in ("converge", "atrapad", "óptimo global"):
            assert prohibido not in alt.lower()


def test_bloques_blog_solo_de_las_rutas_recibidas(generados):
    _, rutas = generados
    texto = g.bloques_blog([rutas[2], rutas[2]])
    assert texto.count("::: figura") == 1 and "gif-pso-rastrigin" in texto
    assert g.bloques_blog([]) == ""


# ------------------------------------------------------------------------------------------ figuras.py


def test_generador_sin_json_devuelve_vacio_y_avisa(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g, "DATOS", tmp_path / "no_existe.json")
    monkeypatch.setattr(g, "SALIDA", tmp_path / "media")
    monkeypatch.setattr(figuras, "FIGURAS_BLOG", tmp_path / "blog")
    assert figuras.GENERADORES["GIF Parte 1"]() == []
    assert "python scripts/part1_gif_trayectorias.py" in capsys.readouterr().out
    monkeypatch.setattr(figuras, "GENERADORES", {"GIF Parte 1": figuras.GENERADORES["GIF Parte 1"]})
    assert cli.main(["figures"]) == 0
    salida = capsys.readouterr().out
    assert "python scripts/part1_gif_trayectorias.py" in salida and "GIF Parte 1: 0 figuras" in salida
    assert not (tmp_path / "media").exists()


def test_generador_con_json_escribe_y_copia_al_blog(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g, "DATOS", _escribir(tmp_path / "datos"))
    monkeypatch.setattr(g, "SALIDA", tmp_path / "media")
    monkeypatch.setattr(figuras, "FIGURAS_BLOG", tmp_path / "blog")
    rutas = figuras.GENERADORES["GIF Parte 1"]()
    assert [r.parent for r in rutas] == [tmp_path / "media"] * 3 + [tmp_path / "blog"] * 3
    assert [r.name for r in rutas[3:]] == list(g.ARCHIVOS.values())
    assert figuras.BLOQUES_BLOG["GIF Parte 1"] is g.bloques_blog
    monkeypatch.setattr(figuras, "GENERADORES", {"GIF Parte 1": figuras.GENERADORES["GIF Parte 1"]})
    assert cli.main(["figures"]) == 0
    salida = capsys.readouterr().out
    assert salida.count("::: figura gif-") == 3


# ------------------------------------------------------------------------------------------ archivo real


def test_archivo_real_tres_gif_pequenos(tmp_path):
    rutas = g.generar_gifs(salida=tmp_path)
    assert [r.name for r in rutas] == list(g.ARCHIVOS.values())
    for r in rutas:
        with Image.open(r) as im:
            assert im.n_frames >= 2
        assert r.stat().st_size <= 1_500_000, (r.name, r.stat().st_size)
