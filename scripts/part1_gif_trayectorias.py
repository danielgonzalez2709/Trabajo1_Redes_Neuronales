"""Genera los datos del GIF de trayectorias de la Parte 1 en 2D (T4.3).

Uso, desde la raíz del repositorio:

    python scripts/part1_gif_trayectorias.py
    python scripts/part1_gif_trayectorias.py --config configs/part1/base.yaml \
        --salida results/data/part1/gif_trayectorias.json

No usa internet. La lógica está en `src/part1/gif_trayectorias.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.part1.gif_trayectorias import generar  # noqa: E402

CONFIG_DEFECTO = "configs/part1/base.yaml"
SALIDA_DEFECTO = "results/data/part1/gif_trayectorias.json"


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=CONFIG_DEFECTO, help=f"config (por defecto {CONFIG_DEFECTO})")
    parser.add_argument("--salida", default=SALIDA_DEFECTO, help=f"archivo JSON (por defecto {SALIDA_DEFECTO})")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    ruta = generar(args.config, args.salida)
    print(ruta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
