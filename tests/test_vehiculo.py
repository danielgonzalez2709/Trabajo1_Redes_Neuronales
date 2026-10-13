"""Pruebas del Bloque 5 (T2.7): data/processed/vehiculo.yaml.

Contrato v1.7 (Spec §5.3), claves exactas:
    {marca, modelo, version, anio, anio_modelo, combustible, consumo_wltp_comb_l100, fuente_url, respaldo_url,
     fecha_consulta}
    `anio` = año de compra (2026); `anio_modelo` = año de modelo del fabricante ("MY27").

Decisión v1.7 (Spec §7.2 Bloque 5): Toyota Corolla Sedán Hybrid 1.8 L, acabado Style Plus 140H e-CVT, MY27,
WLTP combinado 4,6 l/100 km (ficha oficial de Toyota España; km77 como respaldo). Sin fase "extra alta": la ficha MY27 y km77 no la publican (el catálogo 09/2023 da un rango, sin usar; Spec v1.7).

Reglas del proyecto que se comprueban:
    - Un dato que falta se escribe como ``TODO(...)``; nunca se rellena con un número inventado.
    - Consumo WLTP (no NEDC): ninguna clave ni valor menciona NEDC.
    - `combustible` es igual a `producto` de data/processed/combustible.json (Bloque 4).

No usa internet: solo lee archivos versionados.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pytest

from src.common.config import cargar_yaml

RAIZ = Path(__file__).resolve().parents[1]
VEHICULO = RAIZ / "data" / "processed" / "vehiculo.yaml"
COMBUSTIBLE = RAIZ / "data" / "processed" / "combustible.json"

CLAVES_CONTRATO = frozenset(
    {
        "marca",
        "modelo",
        "version",
        "anio",
        "anio_modelo",
        "combustible",
        "consumo_wltp_comb_l100",
        "fuente_url",
        "respaldo_url",
        "fecha_consulta",
    }
)

# Control de plausibilidad (no es un dato): un turismo híbrido 1.8 L homologa en WLTP entre ~3 y ~8 l/100 km.
# Sirve para detectar errores de unidad (km/l, l/km, g/km) o de coma decimal (46 en vez de 4,6).
CONSUMO_MIN_L100, CONSUMO_MAX_L100 = 3.0, 8.0

PATRON_TODO = re.compile(r"^TODO\([a-z0-9-]+\)$")
PATRON_ANIO_MODELO = re.compile(r"^MY\d{2}$")
DOMINIO_OFICIAL = "toyota.es"
DOMINIO_RESPALDO = "km77.com"


def es_todo(valor) -> bool:
    return isinstance(valor, str) and PATRON_TODO.match(valor) is not None


def _dominio(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def _es_fecha_iso(valor) -> bool:
    """Texto AAAA-MM-DD (un `date` de YAML sin comillas no vale: el contrato guarda texto)."""
    if not isinstance(valor, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", valor):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


def _validar_url(valor, campo: str, dominio: str, errores: list[str]) -> None:
    if not isinstance(valor, str) or urlparse(valor).scheme != "https":
        errores.append(f"{campo}: debe ser una URL https, es {valor!r}")
        return
    if _dominio(valor) != dominio:
        errores.append(f"{campo}: se esperaba el dominio {dominio}, es {_dominio(valor)}")


def _menciones_nedc(nodo, ruta: str = "") -> list[str]:
    """Rutas de las claves o valores de texto que mencionan NEDC (en cualquier nivel)."""
    halladas: list[str] = []
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            sub = f"{ruta}.{clave}" if ruta else str(clave)
            if "nedc" in str(clave).lower():
                halladas.append(sub)
            halladas += _menciones_nedc(valor, sub)
    elif isinstance(nodo, list):
        for i, valor in enumerate(nodo):
            halladas += _menciones_nedc(valor, f"{ruta}[{i}]")
    elif isinstance(nodo, str) and "nedc" in nodo.lower():
        halladas.append(ruta)
    return halladas


def validar_vehiculo(v: dict, producto_combustible: str) -> list[str]:
    """Devuelve la lista de incumplimientos del contrato v1.7 (vacía si todo está bien)."""
    if not isinstance(v, dict):
        return [f"el documento debe ser un mapeo, es {type(v).__name__}"]
    errores: list[str] = []

    faltan, sobran = sorted(CLAVES_CONTRATO - set(v)), sorted(set(v) - CLAVES_CONTRATO)
    if faltan:
        errores.append(f"faltan claves del contrato: {faltan}")
    if sobran:
        errores.append(f"claves fuera del contrato v1.7: {sobran}")

    for campo in ("marca", "modelo", "version"):
        if campo in v and (not isinstance(v[campo], str) or not v[campo].strip() or es_todo(v[campo])):
            errores.append(f"{campo}: texto no vacío y sin TODO, es {v[campo]!r}")
    if isinstance(v.get("marca"), str) and v["marca"] != "Toyota":
        errores.append(f"marca: se esperaba Toyota (Spec §7.2), es {v['marca']!r}")
    if isinstance(v.get("modelo"), str) and not re.search(r"sed[aá]n", v["modelo"], re.IGNORECASE):
        errores.append(f"modelo: la carrocería decidida es Sedán (Spec §7.2), es {v['modelo']!r}")

    if "anio" in v and (isinstance(v["anio"], bool) or not isinstance(v["anio"], int)):
        errores.append(f"anio: entero (año de compra), es {v['anio']!r}")
    if "anio_modelo" in v and not (isinstance(v["anio_modelo"], str) and PATRON_ANIO_MODELO.match(v["anio_modelo"])):
        errores.append(f"anio_modelo: texto 'MYnn', es {v['anio_modelo']!r}")

    if "combustible" in v and v["combustible"] != producto_combustible:
        errores.append(
            f"combustible: debe coincidir con combustible.json ({producto_combustible!r}), es {v['combustible']!r}"
        )

    if "consumo_wltp_comb_l100" in v:
        c = v["consumo_wltp_comb_l100"]
        if isinstance(c, bool) or not isinstance(c, (int, float)):
            errores.append(f"consumo_wltp_comb_l100: debe ser número (l/100 km), es {c!r}")
        elif not CONSUMO_MIN_L100 <= float(c) <= CONSUMO_MAX_L100:
            errores.append(f"consumo_wltp_comb_l100: {c} fuera del rango plausible [{CONSUMO_MIN_L100}, {CONSUMO_MAX_L100}]")

    if "fuente_url" in v:
        _validar_url(v["fuente_url"], "fuente_url", DOMINIO_OFICIAL, errores)
    if "respaldo_url" in v:
        _validar_url(v["respaldo_url"], "respaldo_url", DOMINIO_RESPALDO, errores)

    if "fecha_consulta" in v and not _es_fecha_iso(v["fecha_consulta"]):
        errores.append(f"fecha_consulta: texto ISO AAAA-MM-DD, es {v['fecha_consulta']!r}")

    for ruta in _menciones_nedc(v):
        errores.append(f"{ruta}: menciona NEDC; el Spec §7.2 exige WLTP")
    return errores


# ------------------------------------------------------------------------------------------------
# Archivo real


@pytest.fixture(scope="module")
def producto() -> str:
    assert COMBUSTIBLE.exists(), f"falta {COMBUSTIBLE.relative_to(RAIZ)}"
    return json.loads(COMBUSTIBLE.read_text(encoding="utf-8"))["producto"]


@pytest.fixture(scope="module")
def vehiculo() -> dict:
    assert VEHICULO.exists(), f"falta {VEHICULO.relative_to(RAIZ)}"
    return cargar_yaml(VEHICULO.read_text(encoding="utf-8"))


def test_vehiculo_cumple_el_contrato(vehiculo, producto):
    assert validar_vehiculo(vehiculo, producto) == []


def test_claves_exactas_del_contrato_v17(vehiculo):
    assert set(vehiculo) == CLAVES_CONTRATO


def test_sin_bloque_de_acabados_ni_fase_extra_alta(vehiculo):
    """v1.7: la comparación de acabados vive en fuentes.md y en los crudos; la ficha MY27 no publica la fase extra alta."""
    assert "acabados_disponibles" not in vehiculo
    assert "consumo_wltp_extra_alta_l100" not in vehiculo


def test_vehiculo_decidido_en_el_spec(vehiculo):
    """Toyota Corolla Sedán Hybrid 140H, Style Plus, MY27, comprado en 2026 (Spec §3 y §7.2, v1.7)."""
    assert vehiculo["marca"] == "Toyota"
    assert re.search(r"corolla", vehiculo["modelo"], re.IGNORECASE)
    assert re.search(r"sed[aá]n", vehiculo["modelo"], re.IGNORECASE)
    assert vehiculo["version"] == "Style Plus 140H e-CVT"
    assert vehiculo["anio"] == 2026
    assert vehiculo["anio_modelo"] == "MY27"


def test_consumo_wltp_combinado_de_la_ficha_oficial(vehiculo):
    """4,6 l/100 km: FUELCOMBINEDWLTP del configurador de Toyota España (no el máximo de 4,8)."""
    assert vehiculo["consumo_wltp_comb_l100"] == pytest.approx(4.6)


def test_fuentes_oficial_y_respaldo(vehiculo):
    assert vehiculo["fuente_url"] == "https://www.toyota.es/coches/corolla-sedan/build"
    assert _dominio(vehiculo["respaldo_url"]) == DOMINIO_RESPALDO
    assert "corolla-sedan-140h-style" in vehiculo["respaldo_url"]


def test_combustible_coherente_con_bloque_4(vehiculo, producto):
    """Igual a `producto` de combustible.json: el catálogo oficial del Corolla Sedan (09/2023, motor 2ZR-FXE, el
    mismo del MY27) exige "Gasolina de 95 o más octanos"; el precio usado es el de la Gasolina 95 E5."""
    assert vehiculo["combustible"] == producto == "Gasolina 95 E5"


def test_no_hay_menciones_nedc(vehiculo):
    assert _menciones_nedc(vehiculo) == []


def test_fecha_de_consulta_posterior_al_corte(vehiculo):
    """La consulta se hizo después del corte (1-oct-2026); la vigencia en el corte se documenta en fuentes.md."""
    assert date.fromisoformat(vehiculo["fecha_consulta"]) >= date(2026, 10, 1)


# ------------------------------------------------------------------------------------------------
# Pruebas de mutación: el validador debe rechazar estos errores típicos.

PRODUCTO = "Gasolina 95 E5"
VALIDO = {
    "marca": "Toyota",
    "modelo": "Corolla Sedan Hybrid",
    "version": "Style Plus 140H e-CVT",
    "anio": 2026,
    "anio_modelo": "MY27",
    "combustible": PRODUCTO,
    "consumo_wltp_comb_l100": 4.6,
    "fuente_url": "https://www.toyota.es/coches/corolla-sedan/build",
    "respaldo_url": "https://www.km77.com/coches/toyota/corolla/2023/sedan/estandar/corolla-sedan-140h-style/datos",
    "fecha_consulta": "2026-10-11",
}


def test_el_ejemplo_valido_pasa():
    assert validar_vehiculo(VALIDO, PRODUCTO) == []


def _mutar(**cambios):
    v = copy.deepcopy(VALIDO)
    for clave, valor in cambios.items():
        if valor is KeyError:
            v.pop(clave)
        else:
            v[clave] = valor
    return v


@pytest.mark.parametrize(
    ("mutado", "fragmento"),
    [
        (_mutar(marca=KeyError), "faltan claves"),
        (_mutar(anio_modelo=KeyError), "faltan claves"),
        (_mutar(fecha_consulta=KeyError), "faltan claves"),
        (_mutar(acabados_disponibles=[]), "fuera del contrato"),
        (_mutar(consumo_wltp_extra_alta_l100=4.8), "fuera del contrato"),
        (_mutar(modelo="Corolla Touring Sports Hybrid"), "Sedán"),
        (_mutar(modelo="Corolla Hatchback"), "Sedán"),
        (_mutar(version="TODO(acabado-pendiente)"), "sin TODO"),
        (_mutar(consumo_wltp_comb_l100=46), "fuera del rango"),           # coma decimal perdida
        (_mutar(consumo_wltp_comb_l100=0.046), "fuera del rango"),        # l/km
        (_mutar(consumo_wltp_comb_l100=105), "fuera del rango"),          # g CO2/km
        (_mutar(consumo_wltp_comb_l100="4,6"), "debe ser número"),        # texto con coma
        (_mutar(consumo_wltp_comb_l100=True), "debe ser número"),
        (_mutar(consumo_wltp_comb_l100="TODO(dato-faltante)"), "debe ser número"),
        (_mutar(anio="2026"), "anio"),
        (_mutar(anio_modelo=2027), "anio_modelo"),
        (_mutar(anio_modelo="2027"), "anio_modelo"),
        (_mutar(combustible="Gasolina 98"), "combustible.json"),
        (_mutar(combustible="gasolina"), "combustible.json"),
        (_mutar(combustible="TODO(dato-faltante)"), "combustible.json"),
        (_mutar(combustible="Gasolina 95 E10"), "combustible.json"),
        (_mutar(fecha_consulta="11/10/2026"), "fecha_consulta"),
        (_mutar(fuente_url="https://www.km77.com/x"), "toyota.es"),
        (_mutar(fuente_url="http://www.toyota.es/coches/corolla-sedan"), "https"),
        (_mutar(fuente_url="TODO(acabado-pendiente)"), "https"),
        (_mutar(respaldo_url="https://www.motor.es/toyota/corolla"), "km77.com"),
        (_mutar(version="ciclo NEDC"), "NEDC"),
    ],
)
def test_el_validador_rechaza_mutaciones(mutado, fragmento):
    errores = validar_vehiculo(mutado, PRODUCTO)
    assert any(fragmento in e for e in errores), errores
