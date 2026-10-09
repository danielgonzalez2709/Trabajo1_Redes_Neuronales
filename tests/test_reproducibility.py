"""Reproducibilidad (Spec §4.1, §9) y escritura de resultados (Spec §5.4) — tarea T0.3.

Usa un "generador dummy" (sorteos directos de rng) en lugar de un optimizador real:
los optimizadores aún no existen y lo que se prueba aquí es la regla de semillas
`np.random.default_rng(base_seed + run_id)` y la ida y vuelta de los resultados a JSON.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pytest

from src.common import results as results_mod
from src.common.results import load_json, run_filename, save_json, to_jsonable
from src.common.seeds import make_rng, seeds_for_runs, validar_entero


def _dummy_run(rng: np.random.Generator) -> dict:
    """Imita la forma del retorno de optimize() (§5.1) con sorteos del generador."""
    x = rng.uniform(-2.048, 2.048, size=2)
    return {
        "x_best": x,
        "f_best": np.float64(rng.normal()),
        "n_f": np.int64(rng.integers(0, 1000)),
        "n_grad": 0,
        "eval_equiv": float(rng.random()),
        "history": [{"eval_equiv": np.float64(i), "f_best": np.float64(rng.random())} for i in range(3)],
    }


# ---------------------------------------------------------------- semillas

def test_misma_semilla_misma_secuencia_bit_a_bit():
    a = make_rng(0, 7).random(1000)
    b = make_rng(0, 7).random(1000)
    assert np.array_equal(a, b)
    assert a.tobytes() == b.tobytes()


def test_make_rng_equivale_a_default_rng_base_mas_run():
    """Regla §4.1: rng = np.random.default_rng(base_seed + run_id)."""
    a = make_rng(100, 5).random(50)
    b = np.random.default_rng(105).random(50)
    assert a.tobytes() == b.tobytes()


def test_make_rng_devuelve_generator():
    assert isinstance(make_rng(0, 0), np.random.Generator)


def test_misma_suma_misma_secuencia_por_diseno():
    """Por diseño (§4.1: default_rng(base_seed + run_id)) solo importa la suma: (0, 5) y (5, 0) coinciden.

    Por eso los resultados documentan la semilla efectiva (seeds_for_runs), no el par (base, run_id).
    """
    assert make_rng(0, 5).random(20).tobytes() == make_rng(5, 0).random(20).tobytes()


def test_semillas_distintas_secuencias_distintas():
    secuencias = [make_rng(0, run).random(20) for run in range(30)]
    for i in range(len(secuencias)):
        for j in range(i + 1, len(secuencias)):
            assert not np.array_equal(secuencias[i], secuencias[j])


def test_corrida_dummy_reproducible_en_json(tmp_path):
    """Misma semilla → mismo JSON byte a byte (criterio de §9 aplicado a la escritura)."""
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    save_json(p1, _dummy_run(make_rng(0, 3)))
    save_json(p2, _dummy_run(make_rng(0, 3)))
    assert p1.read_bytes() == p2.read_bytes()
    p3 = tmp_path / "c.json"
    save_json(p3, _dummy_run(make_rng(0, 4)))
    assert p1.read_bytes() != p3.read_bytes()


def test_no_depende_ni_altera_el_estado_global_de_numpy():
    """make_rng no usa np.random global: moverlo no cambia la secuencia y make_rng no lo toca."""
    a = make_rng(1, 2).random(10)
    np.random.random(5)  # mover el estado global no afecta
    antes = np.random.get_state()[1].copy()
    b = make_rng(1, 2).random(10)
    assert np.array_equal(np.random.get_state()[1], antes)
    assert a.tobytes() == b.tobytes()


def test_seeds_for_runs():
    assert seeds_for_runs(0, 30) == list(range(30))
    assert seeds_for_runs(100, 3) == [100, 101, 102]
    assert seeds_for_runs(5, 0) == []
    assert all(type(s) is int for s in seeds_for_runs(np.int64(2), 3))


def test_seeds_for_runs_coincide_con_make_rng():
    for run_id, semilla in enumerate(seeds_for_runs(10, 4)):
        assert make_rng(10, run_id).random(5).tobytes() == np.random.default_rng(semilla).random(5).tobytes()


@pytest.mark.parametrize(
    "base, run, error",
    [(-1, 0, ValueError), (0, -1, ValueError), (1.0, 0, TypeError), (0, 2.5, TypeError), ("0", 0, TypeError),
     (0, None, TypeError), (True, 0, TypeError), (0, False, TypeError), (np.bool_(True), 0, TypeError)],
)
def test_make_rng_valida_entradas(base, run, error):
    with pytest.raises(error):
        make_rng(base, run)


def test_make_rng_acepta_enteros_numpy():
    assert make_rng(np.int64(3), np.int32(1)).random(4).tobytes() == np.random.default_rng(4).random(4).tobytes()


@pytest.mark.parametrize(
    "base, n, error",
    [(-1, 3, ValueError), (0, -1, ValueError), (0.0, 3, TypeError), (0, 3.0, TypeError), (True, 3, TypeError)],
)
def test_seeds_for_runs_valida_entradas(base, n, error):
    with pytest.raises(error):
        seeds_for_runs(base, n)


@pytest.mark.parametrize(
    "valor, minimo, error",
    [(True, 0, TypeError), (np.bool_(False), 0, TypeError), (1.0, 0, TypeError), ("1", 0, TypeError),
     (None, 0, TypeError), (-1, 0, ValueError), (0, 1, ValueError), (np.int64(0), 1, ValueError)],
)
def test_validar_entero_rechaza(valor, minimo, error):
    with pytest.raises(error, match="x"):
        validar_entero(valor, "x", minimo)


def test_validar_entero_acepta_int_y_enteros_numpy():
    assert validar_entero(0, "x") == 0
    assert validar_entero(5, "x", minimo=5) == 5
    valor = validar_entero(np.int32(7), "x", minimo=1)
    assert valor == 7 and type(valor) is int


# ---------------------------------------------------------------- JSON

def test_to_jsonable_convierte_tipos_numpy_tuplas_y_path():
    obj = {
        "a": np.float32(1.5),
        "b": np.int64(7),
        "c": np.bool_(True),
        "d": np.array([[1.0, 2.0], [3.0, 4.0]]),
        "e": (1, np.int16(2), (3, 4)),
        "f": Path("results") / "data",
        "g": [np.array([1, 2], dtype=np.int32), None, "texto ñ"],
        "h": np.float64(0.1),
    }
    out = to_jsonable(obj)
    assert out == {
        "a": 1.5,
        "b": 7,
        "c": True,
        "d": [[1.0, 2.0], [3.0, 4.0]],
        "e": [1, 2, [3, 4]],
        "f": "results/data",
        "g": [[1, 2], None, "texto ñ"],
        "h": 0.1,
    }
    assert type(out["a"]) is float and type(out["b"]) is int and type(out["c"]) is bool
    assert type(out["d"][0][0]) is float and type(out["g"][0][0]) is int
    json.dumps(out, allow_nan=False)  # ya es JSON nativo


def test_to_jsonable_float64_y_str_numpy_quedan_nativos():
    """np.float64 es subclase de float y np.str_ de str: aun así deben salir como float/str nativos."""
    suelto = to_jsonable(np.float64(0.5))
    assert type(suelto) is float and suelto == 0.5
    en_lista = to_jsonable([np.float64(1.5), [np.float64(2.5)]])
    assert type(en_lista[0]) is float and type(en_lista[1][0]) is float
    en_dict = to_jsonable({"f": np.float64(3.5), "g": {"h": np.float64(4.5)}})
    assert type(en_dict["f"]) is float and type(en_dict["g"]["h"]) is float
    texto = to_jsonable({"s": np.str_("pso")})
    assert texto == {"s": "pso"} and type(texto["s"]) is str
    assert type(to_jsonable(np.str_("a"))) is str


def test_to_jsonable_rechaza_tipos_desconocidos():
    with pytest.raises(TypeError):
        to_jsonable({"x": object()})


def test_to_jsonable_claves_numpy_str_se_convierten_a_str():
    out = to_jsonable({np.str_("a"): 1, "b": {np.str_("c"): 2}})
    assert out == {"a": 1, "b": {"c": 2}}
    assert type(next(iter(out))) is str and type(next(iter(out["b"]))) is str


@pytest.mark.parametrize("clave", [None, 1, 1.5, True, np.int64(1), np.float64(2.0), np.bool_(True), (1, 2)])
def test_to_jsonable_rechaza_claves_no_textuales_con_ruta(clave):
    """Spec §5.4: claves solo str; el error indica dónde está la clave."""
    with pytest.raises(TypeError, match=r"\$\.config\.pso"):
        to_jsonable({"config": {"pso": {clave: 1}}})


def test_save_json_rechaza_claves_no_textuales(tmp_path):
    ruta = tmp_path / "r.json"
    with pytest.raises(TypeError):
        save_json(ruta, {1: "a"})
    assert list(tmp_path.iterdir()) == []


def test_ida_y_vuelta_json(tmp_path):
    datos = _dummy_run(make_rng(0, 0))
    ruta = tmp_path / "sub" / "carpeta" / "r.json"  # carpetas inexistentes
    save_json(ruta, datos)
    leido = load_json(ruta)
    assert leido == to_jsonable(datos)
    assert np.array_equal(np.asarray(leido["x_best"]), datos["x_best"])  # bit a bit (repr de float es exacto)
    assert leido["f_best"] == float(datos["f_best"])


def test_save_json_formato_utf8_indent2_sin_escapes(tmp_path):
    ruta = tmp_path / "r.json"
    save_json(ruta, {"ciudad": "A Coruña", "v": [1, 2]})
    texto = ruta.read_bytes().decode("utf-8")
    assert "A Coruña" in texto
    assert texto == json.dumps({"ciudad": "A Coruña", "v": [1, 2]}, indent=2, ensure_ascii=False) + "\n"


def test_save_json_acepta_str(tmp_path):
    ruta = str(tmp_path / "r.json")
    save_json(ruta, {"a": 1})
    assert load_json(ruta) == {"a": 1}


@pytest.mark.parametrize("malo", [float("nan"), float("inf"), -np.inf, np.float64("nan"), np.array([1.0, np.nan])])
def test_nan_o_inf_produce_error_claro(tmp_path, malo):
    ruta = tmp_path / "r.json"
    with pytest.raises(ValueError, match=r"(?i)nan|inf|finit"):
        save_json(ruta, {"f_best": malo})
    assert not ruta.exists()
    assert list(tmp_path.iterdir()) == []  # no quedan temporales


def test_nan_anidado_indica_la_ruta_exacta(tmp_path):
    ruta = tmp_path / "r.json"
    with pytest.raises(ValueError, match=re.escape("$.history[1].f:")):
        save_json(ruta, {"history": [{"f": 1.0}, {"f": np.float64("nan")}]})
    assert list(tmp_path.iterdir()) == []


def test_nan_no_corrompe_un_archivo_existente(tmp_path):
    ruta = tmp_path / "r.json"
    save_json(ruta, {"ok": 1})
    with pytest.raises(ValueError):
        save_json(ruta, {"ok": float("nan")})
    assert load_json(ruta) == {"ok": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["r.json"]


def test_escritura_atomica_deja_archivo_completo(tmp_path, monkeypatch):
    """Si la escritura falla a mitad, el archivo anterior queda intacto y no quedan temporales."""
    ruta = tmp_path / "r.json"
    save_json(ruta, {"version": 1})

    def replace_falla(src, dst):
        raise OSError("fallo simulado en os.replace")

    monkeypatch.setattr(results_mod.os, "replace", replace_falla)
    with pytest.raises(OSError, match="simulado"):
        save_json(ruta, {"version": 2, "grande": list(range(10000))})

    assert load_json(ruta) == {"version": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["r.json"]


def test_escritura_atomica_usa_os_replace_desde_la_misma_carpeta(tmp_path, monkeypatch):
    llamadas = []
    real = os.replace

    def espia(src, dst):
        llamadas.append((Path(src), Path(dst)))
        # en el momento del replace el temporal ya está completo y es JSON válido
        assert json.loads(Path(src).read_text(encoding="utf-8")) == {"a": list(range(1000))}
        return real(src, dst)

    monkeypatch.setattr(results_mod.os, "replace", espia)
    ruta = tmp_path / "d" / "r.json"
    save_json(ruta, {"a": list(range(1000))})
    assert len(llamadas) == 1
    origen, destino = llamadas[0]
    assert origen.parent == ruta.parent and origen != ruta
    assert destino == ruta
    assert load_json(ruta) == {"a": list(range(1000))}


def test_sobrescribe_archivo_existente(tmp_path):
    ruta = tmp_path / "r.json"
    save_json(ruta, {"v": 1})
    save_json(ruta, {"v": 2})
    assert load_json(ruta) == {"v": 2}


def test_load_json_rechaza_nan_literal(tmp_path):
    """Un archivo con NaN (JSON inválido) no se acepta en silencio."""
    ruta = tmp_path / "malo.json"
    ruta.write_text('{"f": NaN}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_json(ruta)


# ---------------------------------------------------------------- nombres de archivo

def test_run_filename_formato_exacto():
    assert run_filename("rosenbrock", 2, "pso", 0) == "rosenbrock_2d_pso_seed0.json"
    assert run_filename("rastrigin", 3, "de", 29) == "rastrigin_3d_de_seed29.json"
    assert run_filename("rastrigin", np.int64(3), "ea", np.int64(7)) == "rastrigin_3d_ea_seed7.json"
    assert run_filename("rastrigin", 1, "pso", 0) == "rastrigin_1d_pso_seed0.json"  # dim=1 es el mínimo aceptado


def test_run_filename_identificadores_del_spec():
    """Identificadores [DECIDIDO 9-oct, T0.3] de §5.4."""
    for func in ("rosenbrock", "rastrigin"):
        for method in ("gdfijo", "gdarmijo", "ea", "pso", "de"):
            assert run_filename(func, 2, method, 0) == f"{func}_2d_{method}_seed0.json"


@pytest.mark.parametrize(
    "func, dim, method, seed, error",
    [("rosenbrock", 0, "pso", 0, ValueError), ("rosenbrock", 2, "pso", -1, ValueError),
     ("rosenbrock", 2.0, "pso", 0, TypeError), ("rosenbrock", 2, "pso", 1.5, TypeError),
     ("rosenbrock", True, "pso", 0, TypeError), (None, 2, "pso", 0, TypeError), ("rosenbrock", 2, 3, 0, TypeError)],
)
def test_run_filename_valida_dim_seed_y_tipos(func, dim, method, seed, error):
    with pytest.raises(error):
        run_filename(func, dim, method, seed)


@pytest.mark.parametrize(
    "malo",
    ["", "gd_fijo", "Rosenbrock", "a\tb", "pso\n", "a\x00b", " pso", "ros/enbrock", "ros-enbrock", "rosenbröck", "pso.json"],
)
def test_run_filename_exige_identificador_minusculas_sin_guion_bajo(malo):
    """§5.4: func y method deben cumplir ^[a-z0-9]+$."""
    with pytest.raises(ValueError, match=r"\^\[a-z0-9\]\+\$"):
        run_filename(malo, 2, "pso", 0)
    with pytest.raises(ValueError, match=r"\^\[a-z0-9\]\+\$"):
        run_filename("rosenbrock", 2, malo, 0)


def test_run_filename_sin_colisiones():
    """Sin la regla, ("x_2d_y", 2, "z", 0) y ("x", 2, "y_2d_z", 0) darían ambos x_2d_y_2d_z_seed0.json."""
    with pytest.raises(ValueError):
        run_filename("x_2d_y", 2, "z", 0)
    with pytest.raises(ValueError):
        run_filename("x", 2, "y_2d_z", 0)
    nombres = {
        run_filename(f, d, m, s)
        for f in ("rosenbrock", "rastrigin")
        for d in (2, 3)
        for m in ("gdfijo", "gdarmijo", "ea", "pso", "de")
        for s in range(30)
    }
    assert len(nombres) == 2 * 2 * 5 * 30


def test_run_filename_usa_la_semilla_efectiva():
    """seed{k} es base_seed + run_id (§5.4), tal como lo devuelve seeds_for_runs."""
    semillas = seeds_for_runs(100, 3)
    assert [run_filename("rastrigin", 2, "pso", s) for s in semillas] == [
        "rastrigin_2d_pso_seed100.json", "rastrigin_2d_pso_seed101.json", "rastrigin_2d_pso_seed102.json"]


@pytest.mark.skipif(os.name == "nt", reason="los permisos POSIX no aplican en Windows")
def test_archivo_queda_con_permisos_644_nuevo_y_sobrescrito(tmp_path):
    """Nuevo o sobrescrito, el resultado queda en 0o644 (no en el 0o600 del temporal de mkstemp)."""
    ruta = tmp_path / "r.json"
    save_json(ruta, {"a": 1})
    assert (ruta.stat().st_mode & 0o777) == 0o644
    os.chmod(ruta, 0o600)  # simula un archivo existente con permisos restrictivos
    save_json(ruta, {"a": 2})
    assert (ruta.stat().st_mode & 0o777) == 0o644
    assert load_json(ruta) == {"a": 2}
