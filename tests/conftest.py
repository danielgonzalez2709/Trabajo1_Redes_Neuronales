"""Configuración común de pytest: hace importables los módulos de scripts/ (p. ej. comun_bloque1)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
