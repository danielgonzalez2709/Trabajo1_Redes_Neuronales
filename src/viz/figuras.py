"""Manejador de `python run.py figures` (Spec §4.1): regenera las figuras del blog desde results/data/ sin internet.

- Parte 2 (T4.4): `part2_interactivas.generar_part2()` → blog/docs/figures/part2_*.html.
- Parte 1 (T4.2): `part1_interactivas.generar_part1()` → blog/docs/figures/part1_*.html; tras sus rutas se imprime el
  bloque `::: figura` de cada una, listo para pegar en blog/secciones/ (`BLOQUES_BLOG`).
- GIF Parte 2 (T4.5): `gifs.generar_gifs()` → media/tsp_{mmas|ga}_w25.gif, copiados a blog/docs/figures/ (MkDocs solo
  publica lo que está dentro de blog/docs/).
- GIF Parte 1 (T4.3): `part1_gifs.generar_gifs()` → media/{gd_rosenbrock,gd_rastrigin,pso_rastrigin}_2d.gif desde
  results/data/part1/gif_trayectorias.json, copiados a blog/docs/figures/ y con su bloque `::: figura`. Si falta el
  JSON se avisa con el comando que lo genera y no se escribe nada.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.viz import gifs, part1_gifs, part1_interactivas, part2_interactivas

FIGURAS_BLOG = Path(__file__).resolve().parents[2] / "blog" / "docs" / "figures"

PENDIENTES: dict[str, str] = {}  # nombre → tarea de las figuras que aún no tienen generador


def _parte2() -> list:
    return part2_interactivas.generar_part2()


def _gif_parte2() -> list:
    rutas = gifs.generar_gifs()
    FIGURAS_BLOG.mkdir(parents=True, exist_ok=True)
    return rutas + [Path(shutil.copy2(r, FIGURAS_BLOG / r.name)) for r in rutas]


def _parte1() -> list:
    return part1_interactivas.generar_part1()


def _gif_parte1() -> list:
    if not part1_gifs.DATOS.is_file():
        print(f"AVISO GIF Parte 1: no existe {part1_gifs.DATOS}. No se generan: "
              f"{', '.join(part1_gifs.ARCHIVOS.values())}. Para generarlo: {part1_gifs.COMANDO}")
        return []
    rutas = part1_gifs.generar_gifs(datos=part1_gifs.DATOS)
    FIGURAS_BLOG.mkdir(parents=True, exist_ok=True)
    return rutas + [Path(shutil.copy2(r, FIGURAS_BLOG / r.name)) for r in rutas]


GENERADORES = {"Parte 2": _parte2, "GIF Parte 2": _gif_parte2, "Parte 1": _parte1, "GIF Parte 1": _gif_parte1}
# Generadores cuyas figuras se acompañan del bloque del blog: nombre → función(rutas) → texto.
BLOQUES_BLOG = {"Parte 1": part1_interactivas.bloques_blog, "GIF Parte 1": part1_gifs.bloques_blog}


def main(cfg: dict | None = None) -> int:  # noqa: ARG001 - firma de los manejadores de la CLI
    for nombre, generar in GENERADORES.items():
        rutas = generar()
        print(f"{nombre}: {len(rutas)} figuras")
        for ruta in rutas:
            print(f"  {ruta}")
        if nombre in BLOQUES_BLOG and rutas:
            print(f"{nombre}: bloques para pegar en blog/secciones/\n")
            print(BLOQUES_BLOG[nombre](rutas) + "\n")
    for nombre, tarea in PENDIENTES.items():
        print(f"{nombre}: figuras pendientes ({tarea})")
    return 0
