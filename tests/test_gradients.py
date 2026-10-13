"""Pruebas de las funciones de prueba de la Parte 1 (T1.1; Spec §5.1 y §6.1).

- Gradiente analítico vs. diferencias centrales en 200 puntos aleatorios (semilla fija) por función
  y dimensión: error relativo < 1e-6 en cada punto.
- f(x*) = f* y ∇f(x*) = 0.
- Anclas calculadas a mano para f y ∇f.
- Atributos (name, dim, bounds, x_star, f_star) y contrato de tipos/formas.
- Validaciones del constructor y de la fábrica get_function.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.part1.functions import FUNCIONES, Rastrigin, Rosenbrock, get_function

NOMBRES = ["rosenbrock", "rastrigin"]
DIMS = [2, 3]
CASOS = [(nombre, dim) for nombre in NOMBRES for dim in DIMS]

N_PUNTOS = 200
SEMILLA = 12345
H = 1e-5
TOL_GRAD = 1e-6
TOL_OPTIMO = 1e-12

LIMITE = {"rosenbrock": 2.048, "rastrigin": 5.12}
X_STAR = {"rosenbrock": 1.0, "rastrigin": 0.0}


def gradiente_numerico(func, x: np.ndarray, h: float = H) -> np.ndarray:
    """Diferencias centrales: g[i] = (f(x + h e_i) - f(x - h e_i)) / (2h)."""
    g = np.empty(x.size)
    for i in range(x.size):
        e = np.zeros(x.size)
        e[i] = h
        g[i] = (func.f(x + e) - func.f(x - e)) / (2.0 * h)
    return g


# ---------------------------------------------------------------- gradiente vs. diferencias

# ∇f analítico = diferencias centrales en 200 puntos (error relativo < 1e-6): aceptación de §6.1;
# es la prueba que cubre todo el dominio: un gradiente mal derivado arruinaría el GD.
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_gradiente_coincide_con_diferencias_centrales(nombre, dim):
    # Preparación: puntos uniformes en el dominio con semilla fija (reproducible).
    func = get_function(nombre, dim)
    rng = np.random.default_rng(SEMILLA)
    puntos = rng.uniform(func.bounds[:, 0], func.bounds[:, 1], size=(N_PUNTOS, dim))
    peor = 0.0
    # Ejecución y aserciones: compara punto a punto y guarda el peor error relativo.
    for x in puntos:
        g = func.grad(x)
        g_num = gradiente_numerico(func, x)
        error = np.linalg.norm(g - g_num) / max(1.0, np.linalg.norm(g))
        assert error < TOL_GRAD, (
            f"{nombre} {dim}D: error relativo {error:.3e} en x={x.tolist()} "
            f"(analítico={g.tolist()}, numérico={g_num.tolist()})"
        )
        peor = max(peor, error)
    assert peor < TOL_GRAD


# ---------------------------------------------------------------- óptimo

# f(x*) = f* y ∇f(x*) = 0: confirma las constantes x*, f* que usa el umbral de éxito f − f* ≤ 1e-4.
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_f_en_x_star_es_f_star_y_gradiente_nulo(nombre, dim):
    func = get_function(nombre, dim)
    valor = func.f(func.x_star)
    assert abs(valor - func.f_star) <= TOL_OPTIMO, f"{nombre} {dim}D: f(x*)={valor}"
    g = func.grad(func.x_star)
    assert np.all(np.abs(g) <= TOL_OPTIMO), f"{nombre} {dim}D: grad(x*)={g.tolist()}"


# ---------------------------------------------------------------- anclas a mano

ANCLAS = [
    ("rosenbrock", [0.0, 0.0], 1.0, [-2.0, 0.0]),
    ("rosenbrock", [-1.0, 1.0], 4.0, [-4.0, 0.0]),
    ("rosenbrock", [2.0, 1.0], 901.0, [2402.0, -600.0]),
    ("rosenbrock", [0.0, 0.0, 0.0], 2.0, [-2.0, -2.0, 0.0]),
    ("rosenbrock", [1.0, 2.0, 3.0], 201.0, [-400.0, 1002.0, -200.0]),
    ("rastrigin", [1.0, 1.0], 2.0, [2.0, 2.0]),
    ("rastrigin", [0.5, 0.5], 40.5, [1.0, 1.0]),
    ("rastrigin", [1.0, 2.0, 3.0], 14.0, [2.0, 4.0, 6.0]),
    ("rastrigin", [0.25, 0.25, 0.25], 30.1875, [2 * 0.25 + 20 * math.pi] * 3),
]


# f y ∇f coinciden con valores calculados a mano: detecta errores de fórmula que las diferencias
# centrales no verían (p. ej. f y ∇f equivocadas de forma coherente).
@pytest.mark.parametrize("nombre,x,f_esperado,g_esperado", ANCLAS)
def test_anclas_calculadas_a_mano(nombre, x, f_esperado, g_esperado):
    func = get_function(nombre, len(x))
    valor = func.f(np.array(x))
    assert np.isclose(valor, f_esperado, rtol=1e-12, atol=1e-12), (
        f"{nombre}: f({x})={valor!r}, esperado {f_esperado!r}"
    )
    g = func.grad(np.array(x))
    assert np.allclose(g, g_esperado, rtol=1e-12, atol=1e-12), (
        f"{nombre}: grad({x})={g.tolist()}, esperado {g_esperado}"
    )


# ---------------------------------------------------------------- atributos

# Atributos del contrato §5.1 (name, dim, bounds, x*, f*) con forma, tipo y solo lectura: los
# optimizadores leen el dominio de bounds y no deben poder alterarlo.
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_atributos(nombre, dim):
    func = get_function(nombre, dim)
    # name y dim
    assert func.name == nombre
    assert func.dim == dim
    # bounds: forma (n, 2), float64, valores del dominio y no escribible
    assert func.bounds.shape == (dim, 2)
    assert func.bounds.dtype == np.float64
    esperado = np.tile([-LIMITE[nombre], LIMITE[nombre]], (dim, 1))
    assert np.array_equal(func.bounds, esperado), f"bounds={func.bounds.tolist()}"
    assert not func.bounds.flags.writeable
    with pytest.raises(ValueError):
        func.bounds[0, 0] = 0.0
    # x* y f*: forma, tipo, valor y solo lectura
    assert func.x_star.shape == (dim,)
    assert func.x_star.dtype == np.float64
    assert np.array_equal(func.x_star, np.full(dim, X_STAR[nombre]))
    assert not func.x_star.flags.writeable
    assert func.f_star == 0.0
    assert type(func.f_star) is float


# FUNCIONES y get_function devuelven la clase correcta para cada nombre (lo usa el runner).
@pytest.mark.parametrize("nombre,clase", [("rosenbrock", Rosenbrock), ("rastrigin", Rastrigin)])
def test_fabrica_y_diccionario(nombre, clase):
    assert FUNCIONES[nombre] is clase
    assert type(get_function(nombre, 2)) is clase
    assert clase(3).name == nombre


# ---------------------------------------------------------------- contrato de f y grad

# f devuelve float nativo de Python: el resultado debe serializarse a JSON sin tipos de numpy.
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_f_devuelve_float_de_python(nombre, dim):
    func = get_function(nombre, dim)
    valor = func.f(np.full(dim, 0.3))
    assert type(valor) is float, f"type(f(x)) = {type(valor)}"


# ∇f es un arreglo nuevo float64 de forma (n,) y ni f ni ∇f modifican x: un optimizador que
# reutiliza x no puede verse alterado por efectos secundarios.
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_grad_devuelve_arreglo_nuevo_y_no_modifica_entrada(nombre, dim):
    # Preparación: punto de prueba y copia para comparar después.
    func = get_function(nombre, dim)
    x = np.linspace(-0.7, 0.9, dim)
    antes = x.copy()
    # Ejecución y aserciones sobre ∇f: tipo, forma, sin memoria compartida, x intacto.
    g = func.grad(x)
    assert isinstance(g, np.ndarray)
    assert g.shape == (dim,)
    assert g.dtype == np.float64
    assert g is not x and not np.shares_memory(g, x)
    assert np.array_equal(x, antes), f"grad modificó la entrada: {antes.tolist()} -> {x.tolist()}"
    # f tampoco modifica x
    func.f(x)
    assert np.array_equal(x, antes), f"f modificó la entrada: {antes.tolist()} -> {x.tolist()}"


# f y ∇f aceptan una lista y dan lo mismo que con un arreglo (entradas desde JSON o config).
@pytest.mark.parametrize("nombre,dim", CASOS)
def test_entrada_como_lista(nombre, dim):
    func = get_function(nombre, dim)
    x = [0.2] * dim
    assert func.f(x) == func.f(np.array(x))
    assert np.array_equal(func.grad(x), func.grad(np.array(x)))


# Una x de forma distinta de (n,) lanza ValueError en f y ∇f: evita que numpy difunda (broadcast)
# un vector mal formado y devuelva un valor sin sentido en silencio.
@pytest.mark.parametrize("nombre,dim", CASOS)
@pytest.mark.parametrize("forma", ["corta", "larga", "matriz", "escalar"])
def test_forma_incorrecta_lanza_valueerror(nombre, dim, forma):
    # Preparación: entrada con la forma incorrecta indicada.
    func = get_function(nombre, dim)
    x = {
        "corta": np.zeros(dim - 1),
        "larga": np.zeros(dim + 1),
        "matriz": np.zeros((1, dim)),
        "escalar": np.float64(0.0),
    }[forma]
    # Aserciones: tanto f como ∇f la rechazan.
    with pytest.raises(ValueError):
        func.f(x)
    with pytest.raises(ValueError):
        func.grad(x)


# f se evalúa fuera del dominio sin recortar: la proyección Π es tarea del optimizador, no de f.
def test_funciones_definidas_fuera_del_dominio():
    """El dominio no se aplica dentro de f ni de grad (la proyección es de los optimizadores)."""
    ros = Rosenbrock(2)
    assert ros.f([3.0, 0.0]) == 100.0 * 81.0 + 4.0
    ras = Rastrigin(1)
    assert np.isclose(ras.f([6.0]), 36.0, rtol=1e-12, atol=1e-12)


# ---------------------------------------------------------------- validaciones

# Una dimensión menor que la mínima (Rosenbrock n < 2, Rastrigin n < 1) se rechaza con ValueError.
@pytest.mark.parametrize("clase,dim", [(Rosenbrock, 1), (Rosenbrock, 0), (Rastrigin, 0),
                                       (Rastrigin, -2)])
def test_dim_menor_al_minimo_lanza_valueerror(clase, dim):
    with pytest.raises(ValueError):
        clase(dim)


# dim no entero (float, bool, texto o None) lanza TypeError: ni 2.0 ni True cuentan como enteros.
@pytest.mark.parametrize("clase", [Rosenbrock, Rastrigin])
@pytest.mark.parametrize("dim", [2.5, 2.0, True, "2", None])
def test_dim_no_entero_lanza_typeerror(clase, dim):
    with pytest.raises(TypeError):
        clase(dim)


# Un entero de numpy (np.int64) se acepta y se guarda como int de Python (JSON y comparaciones).
@pytest.mark.parametrize("clase", [Rosenbrock, Rastrigin])
def test_dim_numpy_entero_aceptado(clase):
    func = clase(np.int64(3))
    assert func.dim == 3
    assert type(func.dim) is int
    assert func.bounds.shape == (3, 2)


# Rastrigin admite n = 1 (su dimensión mínima), a diferencia de Rosenbrock.
def test_rastrigin_admite_dim_1():
    assert Rastrigin(1).dim == 1


# Un nombre desconocido (incluidas mayúsculas o guion bajo) lanza ValueError que lista los válidos.
@pytest.mark.parametrize("nombre", ["sphere", "Rosenbrock", "", "rastrigin_"])
def test_nombre_desconocido_lanza_valueerror(nombre):
    with pytest.raises(ValueError, match="rastrigin") as info:
        get_function(nombre, 2)
    assert "rosenbrock" in str(info.value)
