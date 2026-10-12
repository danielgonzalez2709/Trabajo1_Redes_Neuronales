"""T0.5 — Los experimentos no usan internet (enunciado: "que la ejecución no dependa de conexión a internet ni de APIs
externas"; Spec §9). Corre los comandos de run.py con la red bloqueada y revisa que el código de src/ no importe
bibliotecas de red. Solo scripts/descargar_datos.py (fuera de src/) puede usar internet.

Hoy los subcomandos de run.py pueden estar sin implementar; la prueba gana fuerza sola cuando T1.7, T3.6 y T4.x conecten
sus manejadores reales, sin cambiar nada aquí.
"""
import ast
import socket
import urllib.request
from pathlib import Path

import pytest

from src.common import cli

RAIZ = Path(__file__).resolve().parents[1]
MODULOS_DE_RED = {"socket", "urllib", "http", "requests", "httpx", "aiohttp", "ftplib", "smtplib"}


class RedBloqueada(RuntimeError):
    pass


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier intento de abrir una conexión (o de resolver un nombre) lanza RedBloqueada."""

    def _bloqueado(*args, **kwargs):
        raise RedBloqueada("intento de usar la red durante un experimento")

    monkeypatch.setattr(socket.socket, "connect", _bloqueado)
    monkeypatch.setattr(socket.socket, "connect_ex", _bloqueado)
    monkeypatch.setattr(socket, "create_connection", _bloqueado)
    monkeypatch.setattr(socket, "getaddrinfo", _bloqueado)


def test_el_bloqueo_si_detecta_un_acceso_a_la_red(sin_red):
    """Control de la propia prueba: si el bloqueo no funcionara, las demás pasarían sin probar nada."""
    with pytest.raises(RedBloqueada):
        urllib.request.urlopen("https://example.org", timeout=5)


@pytest.mark.parametrize(
    "argv",
    [
        ["part1", "--config", "configs/part1/demo.yaml"],
        ["part2", "--config", "configs/part2/demo.yaml", "--set", "costo.valor_hora=25"],
        ["figures"],
    ],
    ids=["part1-demo", "part2-demo", "figures"],
)
def test_comandos_de_run_py_corren_sin_red(sin_red, monkeypatch, argv):
    monkeypatch.chdir(RAIZ)
    assert cli.main(argv) == 0


def _modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module.split(".")[0])
    return nombres


@pytest.mark.parametrize("archivo", sorted((RAIZ / "src").rglob("*.py")) + [RAIZ / "run.py"],
                         ids=lambda p: p.relative_to(RAIZ).as_posix())
def test_el_codigo_de_los_experimentos_no_importa_bibliotecas_de_red(archivo):
    prohibidos = _modulos_importados(archivo) & MODULOS_DE_RED
    assert not prohibidos, f"{archivo.name} importa {prohibidos}: solo scripts/descargar_datos.py puede usar internet"
