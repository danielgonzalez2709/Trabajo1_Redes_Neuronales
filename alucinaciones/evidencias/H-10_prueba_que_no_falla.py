"""Evidencia H-10: prueba de mutación sobre las pruebas de herencia de T0.2 (ronda 3).

Reemplaza _fusionar por una versión deliberadamente defectuosa (muta la base y comparte objetos)
y corre las pruebas de herencia. Si todas pasan, ninguna prueba verifica "No muta las entradas".
Ejecutar desde la raíz del repo, sobre la versión de la ronda 3 de src/common/config.py:
    .venv\Scripts\python.exe alucinaciones/evidencias/H-10_prueba_que_no_falla.py
"""
import sys

import pytest

sys.path.insert(0, ".")
import src.common.config as config  # noqa: E402


def fusion_mutante(base, hija):
    """Versión defectuosa a propósito: muta la base y comparte objetos (sin copias)."""
    for clave, valor in hija.items():
        if isinstance(valor, dict) and isinstance(base.get(clave), dict):
            fusion_mutante(base[clave], valor)
        else:
            base[clave] = valor
    return base


config._fusionar = fusion_mutante
sys.exit(pytest.main(["-q", "tests/test_config.py", "-k", "herencia or hereda", "-p", "no:cacheprovider"]))
