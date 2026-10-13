"""Genera los datos del deslizador de η (GD de paso fijo en Rosenbrock 2D; T4.2, Spec §6.7 punto 5).

Uso, desde la raíz del repositorio:

    python scripts/part1_eta_deslizador.py
    python scripts/part1_eta_deslizador.py --config configs/part1/base.yaml \
        --afinada configs/part1/tuned.yaml --salida results/data/part1/eta_deslizador.json

No usa internet. La lógica está en `src/part1/eta_deslizador.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.part1.eta_deslizador import generar  # noqa: E402

CONFIG_DEFECTO = "configs/part1/base.yaml"
AFINADA_DEFECTO = "configs/part1/tuned.yaml"


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=CONFIG_DEFECTO, help=f"config base (por defecto {CONFIG_DEFECTO})")
    parser.add_argument("--afinada", default=AFINADA_DEFECTO,
                        help=f"config afinada; si no existe, no hay marca 'afinado' (por defecto {AFINADA_DEFECTO})")
    parser.add_argument("--salida", default=None, help="archivo JSON (por defecto <cfg.salida>/eta_deslizador.json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    ruta = generar(args.config, args.afinada, args.salida)
    print(ruta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
