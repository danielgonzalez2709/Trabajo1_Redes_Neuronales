"""Punto de entrada único (Spec §4.1). Uso: python run.py {part1,part2,figures} --help"""

import sys

from src.common.cli import main

if __name__ == "__main__":
    sys.exit(main())
