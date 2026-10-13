"""Manejador de `python run.py figures` (Spec §4.1): regenera las figuras del blog desde results/data/ sin internet.

- Parte 2 (T4.4): `part2_interactivas.generar_part2()` → blog/docs/figures/part2_*.html.
- Parte 1 (T4.2): pendiente. Punto de extensión: añadir su generador a `GENERADORES` cuando exista.
- GIF (T4.5): pendiente; mismo punto de extensión.
"""

from __future__ import annotations

from src.viz import part2_interactivas

PENDIENTES = {"Parte 1": "T4.2", "GIF": "T4.5"}  # se quitan de aquí al añadir su generador


def _parte2() -> list:
    return part2_interactivas.generar_part2()


GENERADORES = {"Parte 2": _parte2}


def main(cfg: dict | None = None) -> int:  # noqa: ARG001 - firma de los manejadores de la CLI
    for nombre, generar in GENERADORES.items():
        rutas = generar()
        print(f"{nombre}: {len(rutas)} figuras")
        for ruta in rutas:
            print(f"  {ruta}")
    for nombre, tarea in PENDIENTES.items():
        print(f"{nombre}: figuras pendientes ({tarea})")
    return 0
