"""Datos del deslizador de η para el GD de paso fijo en Rosenbrock 2D (T4.2; Spec §6.7 punto 5).

Este módulo no dibuja: ejecuta el GD de paso fijo con varios η desde el mismo x0 y escribe un JSON
que la figura interactiva solo lee (Spec §4). Toda evaluación pasa por `ejecutar_corrida`
(`CountedProblem`); aquí no se llama a f ni a ∇f.

- `rejilla_eta`: rejilla logarítmica de `PUNTOS_POR_DECADA` puntos por década, extremos incluidos.
- `valores_eta`: rejilla + valores marcados (`defecto`, `afinado`), ordenados y sin duplicados.
- `indices_submuestreo`: a lo sumo `puntos_max` índices espaciados geométricamente.
- `construir_datos`: el diccionario del contrato {"meta", "etas"}.
- `guardar` / `generar`: escritura del JSON (lo usa `scripts/part1_eta_deslizador.py`).
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np

from src.common.config import load_config
from src.common.results import save_json
from src.part1.corrida import ejecutar_corrida

FUNC = "rosenbrock"            # Spec §6.7 punto 5: deslizador de η para GD en Rosenbrock
DIM = 2                        # los frames solo existen en 2D (§5.1)
METHOD = "gdfijo"
RUN_ID = 0                     # mismo x0 que la corrida rosenbrock_2d_gdfijo_seed<base_seed>
PUNTOS_POR_DECADA = 4          # densidad de la rejilla logarítmica de η
TOLERANCIA_RELATIVA = 1e-9     # dos η más cercanos que esto son el mismo punto
PUNTOS_MAX = 150               # máximo de puntos guardados por trayectoria
PUNTOS_MIN = 2                 # el primero (x0) y el último siempre se guardan
MARCA_DEFECTO = "defecto"
MARCA_AFINADO = "afinado"
NOMBRE_ARCHIVO = "eta_deslizador.json"


def _iguales(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=TOLERANCIA_RELATIVA, abs_tol=0.0)


def rejilla_eta(minimo: float, maximo: float) -> list[float]:
    """Rejilla logarítmica en [minimo, maximo] con los dos extremos exactos.

    El número de intervalos es `PUNTOS_POR_DECADA · log10(maximo/minimo)`; si ese producto no es
    entero se redondea hacia arriba (los puntos quedan algo más juntos, nunca más separados).
    Lanza ValueError si no se cumple 0 < minimo < maximo < inf.
    """
    minimo, maximo = float(minimo), float(maximo)
    if not (math.isfinite(minimo) and math.isfinite(maximo) and 0.0 < minimo < maximo):
        raise ValueError(f"se necesita 0 < min < max finitos; se recibió min={minimo!r}, max={maximo!r}")
    intervalos_exactos = PUNTOS_POR_DECADA * math.log10(maximo / minimo)
    intervalos = max(1, math.ceil(intervalos_exactos - TOLERANCIA_RELATIVA))
    valores = [minimo * (maximo / minimo) ** (i / intervalos) for i in range(intervalos + 1)]
    valores[0], valores[-1] = minimo, maximo
    return valores


def valores_eta(minimo: float, maximo: float, defecto: float,
                afinado: float | None = None) -> list[tuple[float, str | None]]:
    """Lista ordenada de (η, marca): la rejilla más los valores marcados.

    Un marcado que coincide con un punto de la rejilla (tolerancia relativa
    `TOLERANCIA_RELATIVA`) no se duplica: ese punto toma el valor exacto del marcado y su marca.
    `afinado` se ignora si es None o si coincide con `defecto` (misma tolerancia).
    """
    valores: list[tuple[float, str | None]] = [(eta, None) for eta in rejilla_eta(minimo, maximo)]
    marcados = [(float(defecto), MARCA_DEFECTO)]
    if afinado is not None and not _iguales(float(afinado), float(defecto)):
        marcados.append((float(afinado), MARCA_AFINADO))
    for eta, marca in marcados:
        coincide = [i for i, (valor, _) in enumerate(valores) if _iguales(valor, eta)]
        if coincide:
            valores[coincide[0]] = (eta, marca)
        else:
            valores.append((eta, marca))
    return sorted(valores, key=lambda par: par[0])


def indices_submuestreo(n_iter: int, puntos_max: int = PUNTOS_MAX) -> list[int]:
    """Índices crecientes de 0 a `n_iter` (ambos incluidos), a lo sumo `puntos_max`.

    Si la trayectoria cabe entera se devuelven todos. Si no, 0 más `puntos_max − 1` valores
    espaciados geométricamente entre 1 y `n_iter`, redondeados al entero y sin repetidos (por eso
    pueden salir menos de `puntos_max`).
    """
    if n_iter < 0:
        raise ValueError(f"n_iter debe ser >= 0; se recibió {n_iter!r}")
    if puntos_max < PUNTOS_MIN:
        raise ValueError(f"puntos_max debe ser >= {PUNTOS_MIN}; se recibió {puntos_max!r}")
    if n_iter + 1 <= puntos_max:
        return list(range(n_iter + 1))
    geometricos = np.geomspace(1, n_iter, puntos_max - 1)
    # el último valor geométrico es n_iter (se fija exacto); con puntos_max = 2 no hay interiores
    indices = {0, n_iter, *(int(round(float(v))) for v in geometricos[:-1])}
    return sorted(i for i in indices if 0 <= i <= n_iter)


def _corrida(cfg: dict, eta: float) -> dict:
    """Corrida de `ejecutar_corrida` con una copia de `cfg` en la que solo cambia el η."""
    config = copy.deepcopy(cfg)
    config["gd"]["eta"][FUNC] = eta
    return ejecutar_corrida(FUNC, DIM, METHOD, cfg["base_seed"], RUN_ID, config,
                            presupuesto_por_dim=cfg["presupuesto_por_dim"], grabar_frames=True)


def _entrada(corrida: dict, eta: float, marca: str | None, puntos_max: int) -> dict:
    resultado = corrida["result"]
    frames = resultado["frames"]
    n_iter = int(frames[-1]["iter"])
    por_iteracion = {int(frame["iter"]): frame["positions"][0] for frame in frames}
    iteraciones = indices_submuestreo(n_iter, puntos_max)
    return {
        "eta": float(eta),
        "marca": marca,
        "f_best": float(resultado["f_best"]),
        "n_grad": int(resultado["n_grad"]),
        "n_iter": n_iter,
        "iteraciones": iteraciones,
        "puntos": [[float(c) for c in por_iteracion[i]] for i in iteraciones],
    }


def construir_datos(cfg: dict, cfg_afinada: dict | None = None, puntos_max: int = PUNTOS_MAX) -> dict:
    """Diccionario {"meta", "etas"} del deslizador. No modifica `cfg` ni `cfg_afinada`.

    El intervalo de η es el de `cfg["hpo"]["espacios"]["gdfijo"]["eta"]`; `defecto` es
    `cfg["gd"]["eta"]["rosenbrock"]` y `afinado` el mismo valor de `cfg_afinada` (si se pasa y
    difiere). Semilla `base_seed` con `run_id = 0`, presupuesto `presupuesto_por_dim` y k = 2n.
    """
    espacio = cfg["hpo"]["espacios"][METHOD]["eta"]
    afinado = None if cfg_afinada is None else cfg_afinada["gd"]["eta"][FUNC]
    valores = valores_eta(espacio["min"], espacio["max"], cfg["gd"]["eta"][FUNC], afinado)

    etas, meta = [], None
    for eta, marca in valores:
        corrida = _corrida(cfg, eta)
        entrada = _entrada(corrida, eta, marca, puntos_max)
        if meta is None:
            meta = {"func": corrida["func"], "dim": corrida["dim"], "method": corrida["method"],
                    "seed": corrida["seed"], "k": corrida["k"], "budget": corrida["budget"],
                    "x0": entrada["puntos"][0], "puntos_max": int(puntos_max)}
        elif entrada["puntos"][0] != meta["x0"]:
            raise RuntimeError(f"el x0 de η = {eta!r} difiere del común {meta['x0']!r}")
        etas.append(entrada)
    return {"meta": meta, "etas": etas}


def guardar(datos: dict, ruta: str | Path) -> Path:
    """Escribe `datos` como JSON compacto (sin sangría, para el tamaño) y devuelve la ruta."""
    return save_json(ruta, datos, sangria=None)


def generar(ruta_config: str | Path, ruta_afinada: str | Path | None = None,
            salida: str | Path | None = None) -> Path:
    """Carga las configs, construye los datos y los guarda.

    `ruta_afinada` inexistente o None = sin marca `afinado`. `salida` None =
    `<cfg["salida"]>/eta_deslizador.json`.
    """
    cfg = load_config(ruta_config)
    cfg_afinada = None
    if ruta_afinada is not None and Path(ruta_afinada).exists():
        cfg_afinada = load_config(ruta_afinada)
    destino = Path(cfg["salida"]) / NOMBRE_ARCHIVO if salida is None else Path(salida)
    return guardar(construir_datos(cfg, cfg_afinada), destino)
