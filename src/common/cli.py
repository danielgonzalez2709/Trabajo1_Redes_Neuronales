"""Interfaz de línea de comandos de `run.py` (Spec §4.1).

    python run.py part1   --config configs/part1/demo.yaml [--set clave.subclave=valor ...]
    python run.py part2   --config configs/part2/demo.yaml [--set clave.subclave=valor ...]
    python run.py figures

Para conectar un subcomando, cambiar el `manejador` de su entrada en `SUBCOMANDOS` por una
función `(cfg: dict | None) -> int` (recibe la config final, o None si el subcomando no la usa).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import NamedTuple

import yaml

from src.common.config import apply_overrides, load_config

Manejador = Callable[[dict | None], int]

CABECERA_CONFIG = "Configuración final resuelta:"
DESTINO_PARSER = "parser_subcomando"
# §4.1: tildes y "ñ" intactas aunque se redirija la salida (en Windows sería cp1252).
CODIFICACION_SALIDA = "utf-8"
AYUDA_SET = (
    "Sobrescribe un parámetro existente; el valor se interpreta como YAML (repetible).\n"
    "Ej.: --set pso.w=0.9 --set runs=5\n"
    'En PowerShell, los valores con espacios van entre comillas: --set "methods=[pso, gdfijo]"'
)


class Subcomando(NamedTuple):
    ayuda: str
    usa_config: bool  # True: --config obligatorio y --set repetible
    manejador: Manejador


def _pendiente(nombre: str, tarea: str) -> Manejador:
    """Manejador provisional: avisa qué tarea del PLAN implementará el subcomando."""

    def manejador(cfg: dict | None) -> int:
        print(f"Subcomando {nombre}: pendiente ({tarea})")
        return 0

    return manejador


# Registro único nombre -> (ayuda, usa_config, manejador).
# Completar al cerrar T1.7 (part1), T3.6 (part2) y T4.x (figures).
SUBCOMANDOS: dict[str, Subcomando] = {
    "part1": Subcomando(
        "Parte 1: optimización numérica (GD, EA, PSO, DE)", True, _pendiente("part1", "T1.7")
    ),
    "part2": Subcomando(
        "Parte 2: TSP por España (ACO, GA, exacto)", True, _pendiente("part2", "T3.6")
    ),
    "figures": Subcomando(
        "Regenera las figuras interactivas y los GIF desde results/data/",
        False,
        _pendiente("figures", "T4.x"),
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="Punto de entrada único del Trabajo 1 (Spec §4.1).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    for nombre, (ayuda, usa_config, _) in SUBCOMANDOS.items():
        p = sub.add_parser(
            nombre, help=ayuda, description=ayuda, formatter_class=argparse.RawTextHelpFormatter
        )
        if not usa_config:
            continue
        # Se guarda el parser del subcomando en el Namespace para que main() pueda emitir los
        # errores de configuración con el uso de ESTE subcomando (y no el del parser raíz).
        p.set_defaults(**{DESTINO_PARSER: p})
        p.add_argument("--config", required=True, help="Ruta al archivo YAML de configuración")
        p.add_argument(
            "--set",
            dest="overrides",
            action="append",
            default=[],
            metavar="CLAVE.SUBCLAVE=VALOR",
            help=AYUDA_SET,
        )
    return parser


def _imprimir_config(cfg: dict) -> None:
    print(CABECERA_CONFIG)
    texto = yaml.safe_dump(
        cfg, sort_keys=False, allow_unicode=True, explicit_start=True, explicit_end=True
    )
    print(texto, end="")


def _forzar_utf8() -> None:
    """Al redirigir en Windows Python usa la codificación local (cp1252); se fuerza UTF-8."""
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding=CODIFICACION_SALIDA)


def main(argv: list[str] | None = None) -> int:
    _forzar_utf8()
    args = build_parser().parse_args(argv)
    subcomando = SUBCOMANDOS[args.comando]
    cfg: dict | None = None
    if subcomando.usa_config:
        try:
            cfg = apply_overrides(load_config(args.config), args.overrides)
        except (FileNotFoundError, ValueError) as exc:
            # Truco de DESTINO_PARSER (ver build_parser): el Namespace trae el parser del
            # subcomando; su .error() imprime "usage: run.py part2 ..." y sale con código 2.
            getattr(args, DESTINO_PARSER).error(str(exc))
        _imprimir_config(cfg)
    return subcomando.manejador(cfg)
