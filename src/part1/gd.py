"""Descenso por gradiente de la Parte 1 (Spec §5.1, §6.2 y §6.3).

Dos variantes con el mismo bucle (`_descenso`) y distinta regla de paso:
  - "fijo" (T1.2): x_{t+1} = Π(x_t − η ∇f(x_t)), con Π el recorte a `problem.func.bounds`.
  - "armijo" (T1.3): búsqueda de paso con retroceso de Armijo sobre el ensayo proyectado.

Todas las evaluaciones pasan por `CountedProblem` (§6.2): el GD no cuenta nada a mano.
"""

from __future__ import annotations  # las anotaciones de tipo se evalúan de forma diferida

import math  # math.inf para validar que los parámetros sean finitos
from numbers import Real  # tipo abstracto de los números reales (int, float, np.float64, ...)

import numpy as np  # álgebra vectorial: recorte Π, producto interno y norma de ∇f

from src.common.counter import BudgetExhausted, CountedProblem  # contador único de evaluaciones

VARIANTE_FIJO = "fijo"  # valor de cfg["variante"] para el GD de paso fijo (T1.2)
VARIANTE_ARMIJO = "armijo"  # valor de cfg["variante"] para el GD con Armijo (T1.3)
VARIANTES = (VARIANTE_FIJO, VARIANTE_ARMIJO)  # variantes admitidas
CLAVES_ARMIJO = ("eta0", "beta", "c")  # claves obligatorias de cfg["gd"]["armijo"]: η₀, β, c


def _real(nombre: str, valor) -> float:  # validador base de los parámetros numéricos
    """Devuelve `valor` como float si es un número real (no bool); si no, lanza ValueError."""
    # bool es subclase de int, por eso se rechaza aparte; texto o None no son Real
    if isinstance(valor, (bool, np.bool_)) or not isinstance(valor, Real):
        # no es número real (o es bool)
        raise ValueError(f"{nombre} debe ser un número real (recibido {valor!r})")
    return float(valor)  # número real convertido a float de Python


def _positivo_finito(nombre: str, valor) -> float:  # valida η, η₀ y tol_grad
    """Devuelve `valor` como float si es un número real finito y > 0 (no bool).

    Si no, lanza ValueError.
    """
    numero = _real(nombre, valor)  # primero exige que sea un número real
    if not (0 < numero < math.inf):  # también rechaza NaN y ±inf
        raise ValueError(f"{nombre} debe ser finito y > 0 (recibido {valor!r})")  # fuera de rango
    return numero  # valor válido como float


def _entre_cero_y_uno(nombre: str, valor) -> float:  # valida β y c de Armijo
    """Devuelve `valor` como float si es un número real (no bool) con 0 < valor < 1."""
    numero = _real(nombre, valor)  # primero exige que sea un número real
    if not (0 < numero < 1):  # también rechaza NaN
        # fuera del intervalo abierto (0, 1)
        raise ValueError(f"{nombre} debe cumplir 0 < {nombre} < 1 (recibido {valor!r})")
    return numero  # valor válido como float


def _frame(iteracion: int, x: np.ndarray, problem: CountedProblem) -> dict:  # un frame del GIF
    """Frame de la animación (§5.1): una sola posición y el mejor punto visto hasta ahora."""
    # iteración, posición actual (lista de una) y mejor punto visto, como listas JSON
    return {"iter": iteracion, "positions": [x.tolist()], "best": problem.best_x.tolist()}


class _PasoFijo:  # regla de paso de la variante "fijo"
    """Regla de paso fijo: x' = Π(x − η g), registrado con `observe` (no cuesta; n_f = 0)."""

    def __init__(self, problem: CountedProblem, eta: float):  # guarda η y los límites de Π
        self.problem = problem  # problema contado donde se registran los iterados
        self.eta = eta  # paso fijo η, ya validado
        # límites inferior y superior del dominio, para la proyección Π
        self.lo, self.hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]

    def __call__(self, x: np.ndarray, g: np.ndarray) -> np.ndarray:  # un paso x → Π(x − η ∇f)
        x_nuevo = np.clip(x - self.eta * g, self.lo, self.hi)   # proyección Π al dominio
        # registra el iterado en best/history sin cobrar: el paso fijo no usa f para decidir
        self.problem.observe(x_nuevo)
        return x_nuevo  # nuevo punto aceptado


class _PasoArmijo:  # regla de paso de la variante "armijo"
    """Regla de Armijo con retroceso sobre el ensayo proyectado; guarda fx = f(x actual).

    Cada ensayo se evalúa con `problem.f` (cobrado y registrado en best/history). f(x0) se cobra
    una sola vez, en la primera llamada; después fx es el f del ensayo aceptado.
    """

    # guarda η₀, β, c y los límites de Π
    def __init__(self, problem: CountedProblem, eta0: float, beta: float, c: float):
        self.problem = problem  # problema contado: cada ensayo se cobra con problem.f
        # η₀ inicial, factor β de retroceso y constante c de Armijo
        self.eta0, self.beta, self.c = eta0, beta, c
        # límites inferior y superior del dominio, para la proyección Π
        self.lo, self.hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]
        self.fx: float | None = None              # f en el punto actual (perezoso)

    # búsqueda con retroceso sobre el arco proyectado Π(x − η ∇f) (sin recorte, la recta en −∇f)
    def __call__(self, x: np.ndarray, g: np.ndarray) -> np.ndarray:
        if self.fx is None:  # primera llamada: aún no se conoce f(x0)
            self.fx = self.problem.f(x)           # f(x0): cobrada una sola vez
        eta = self.eta0  # cada búsqueda lineal arranca en η = η₀
        while True:                               # sin tope: el presupuesto corta la búsqueda
            x_nuevo = np.clip(x - eta * g, self.lo, self.hi)  # ensayo proyectado x' = Π(x − η ∇f)
            f_nuevo = self.problem.f(x_nuevo)     # 1 evaluación por ensayo
            descenso = float(np.dot(g, x - x_nuevo))   # >= 0; sin recorte vale eta·‖g‖²
            if f_nuevo <= self.fx - self.c * descenso:  # condición de Armijo sobre el ensayo x'
                break  # ensayo aceptado
            eta *= self.beta  # retroceso: η ← β·η
        # f(x') aceptado se reutiliza como f(x) en la siguiente iteración (no se vuelve a evaluar)
        self.fx = f_nuevo
        return x_nuevo  # nuevo punto aceptado


def _descenso(problem: CountedProblem, siguiente_x, tol_grad: float, grabar: bool,  # bucle GD
              rng: np.random.Generator) -> list[dict]:  # rng solo para x0; devuelve los frames
    """Bucle común a ambas variantes; devuelve los frames (vacío si no se graban).

    `siguiente_x(x, g)` devuelve el nuevo punto aceptado y puede lanzar BudgetExhausted.
    """
    lo, hi = problem.func.bounds[:, 0], problem.func.bounds[:, 1]  # límites del dominio
    x = rng.uniform(lo, hi)                     # única llamada al rng
    problem.observe(x)                          # el punto inicial no cuesta
    frames = [_frame(0, x, problem)] if grabar else []  # frame 0 = x0 (solo si se graba)
    iteracion = 0  # contador de pasos aceptados (numera los frames)
    try:  # BudgetExhausted puede salir de grad o de la regla de paso
        while True:  # itera hasta ‖∇f‖ < tol_grad o hasta agotar el presupuesto
            g = problem.grad(x)                 # cuesta k evaluaciones equivalentes
            if np.linalg.norm(g) < tol_grad:    # convergió: no se da ese paso
                break  # criterio de parada ‖∇f‖ < tol_grad (§6.3)
            x = siguiente_x(x, g)  # aplica la regla de paso (fijo o Armijo)
            iteracion += 1  # un paso aceptado más
            if grabar:  # solo en 2D con record_frames
                frames.append(_frame(iteracion, x, problem))  # un frame por punto aceptado
    except BudgetExhausted:  # el contador rechazó una evaluación que excedería el presupuesto
        pass                                    # presupuesto agotado: se devuelve lo visto
    return frames  # lista vacía si no se graba


def _eta_fijo(problem: CountedProblem, gd_cfg: dict) -> float:  # η del paso fijo según la función
    """eta validado; se elige por el nombre de la función (cfg["gd"]["eta"])."""
    etas = gd_cfg["eta"]  # mapa función → η (rosenbrock 1e-3, rastrigin 2e-3 en base.yaml)
    nombre = problem.func.name  # nombre de la función que se optimiza
    if not isinstance(etas, dict):  # gd.eta debe ser un mapa, no un número suelto
        # gd.eta mal formado
        raise ValueError(f"gd.eta debe ser un mapa {{función: paso}} (recibido {etas!r})")
    if nombre not in etas:  # no hay η configurado para esta función
        disponibles = ", ".join(sorted(map(str, etas))) or "(ninguna)"  # nombres para el mensaje
        raise ValueError(  # falta el η de esta función
            # el mensaje lista las funciones que sí tienen η
            f"gd.eta no tiene paso para la función {nombre!r}; funciones disponibles: {disponibles}"
        )
    return _positivo_finito(f"gd.eta.{nombre}", etas[nombre])  # η validado (finito y > 0)


def _parametros_armijo(gd_cfg: dict) -> tuple[float, float, float]:  # lee y valida η₀, β, c
    """(eta0, beta, c) validados desde cfg["gd"]["armijo"]."""
    bloque = gd_cfg.get("armijo")  # bloque gd.armijo (None si falta)
    if not isinstance(bloque, dict):  # ausente o no es un mapa
        raise ValueError(  # gd.armijo ausente o mal formado
            f"gd.armijo debe ser un mapa con claves {', '.join(CLAVES_ARMIJO)} "  # claves esperadas
            f"(recibido {bloque!r})"  # valor recibido
        )
    for clave in CLAVES_ARMIJO:  # recorre eta0, beta y c
        if clave not in bloque:  # clave obligatoria ausente
            raise ValueError(f"falta la clave gd.armijo.{clave}")  # indica qué clave falta
    eta0 = _positivo_finito("gd.armijo.eta0", bloque["eta0"])  # η₀ finito y > 0
    beta = _entre_cero_y_uno("gd.armijo.beta", bloque["beta"])  # 0 < β < 1
    c = _entre_cero_y_uno("gd.armijo.c", bloque["c"])  # 0 < c < 1
    return eta0, beta, c  # parámetros de la búsqueda de Armijo


# punto de entrada común de los optimizadores de la Parte 1 (contrato §5.1)
def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict:
    """Descenso por gradiente con proyección (Spec §6.3); contrato de §5.1.

    `cfg` es la configuración resuelta. Claves: `variante` ("fijo" o "armijo", la fija el runner),
    `gd.tol_grad`, `record_frames` (opcional, por defecto False) y, según la variante,
    `gd.eta` (fijo: mapa función → paso, se elige con `problem.func.name`) o
    `gd.armijo.{eta0, beta, c}` (armijo; `gd.eta` no se lee ni se exige).

    Bucle común, en este orden:
      1. x_0 ~ U(dominio) con UNA sola llamada `rng.uniform(lo, hi)`; el rng no se usa para nada
         más.
      2. `problem.observe(x_0)`: registra x_0 en best/history sin cobrarlo (eval_equiv = 0), para
         que haya un resultado válido aunque el presupuesto no alcance para nada.
      3. Bucle: g = `problem.grad(x)` (cuesta k); si ||g|| < tol_grad se termina sin dar el paso;
         si no, x ← regla de paso(x, g). BudgetExhausted (de grad o de f) termina el bucle y
         nunca sale de esta función.

    Regla "fijo": x ← Π(x − η g), Π = recorte al dominio, y `problem.observe(x)`. Nunca necesita
    el valor de f para decidir: usa `observe` (actualiza las curvas sin contar) y n_f = 0; solo
    paga k por cada ∇f (§5.1).

    Regla "armijo" (backtracking): la primera vez se cobra fx = f(x_0) (perezoso: si el primer
    gradiente ya cumple la tolerancia, n_f = 0). Luego, desde η = eta0, ensayo x' = Π(x − η g) con
    `problem.f(x')` (1 evaluación cobrada por ensayo); se acepta si
        f(x') ≤ fx − c·<g, x − x'>,
    y si no, η ← β·η (producto repetido) sin tope de retrocesos: el presupuesto corta la búsqueda.
    El término <g, x − x'> es el descenso del ensayo proyectado: sin recorte vale η‖g‖² (la
    condición de §6.3); con recorte evita exigir un descenso que la proyección no permite. Tras
    aceptar, x ← x' y fx ← f(x'), que se reutiliza en la siguiente iteración (f(x) no se vuelve a
    evaluar). Así n_f = 1 + (número total de ensayos). Los ensayos ya quedan registrados por
    `problem.f`, por eso los iterados aceptados no se vuelven a observar.

    El resultado es el mejor punto VISTO (problem.best_x), no el último; en Armijo puede ser un
    ensayo rechazado. Con dim == 2 y record_frames, "frames" tiene un frame por punto aceptado
    (iter 0, 1, 2, ...); si no, la clave no existe.
    """
    variante = cfg.get("variante")  # "fijo" o "armijo" (la fija el runner); None si falta
    if variante not in VARIANTES:  # variante ausente o desconocida
        raise ValueError(  # error que lista las variantes válidas
            # variante recibida
            f"variante de GD desconocida o ausente: {variante!r}; valores válidos: "
            f"{', '.join(VARIANTES)}"  # valores admitidos
        )
    gd_cfg = cfg["gd"]  # bloque gd compartido por ambas variantes
    # toda la validación ocurre antes de evaluar f/∇f o usar el rng
    if variante == VARIANTE_FIJO:  # paso fijo: η elegido por el nombre de la función
        siguiente_x = _PasoFijo(problem, _eta_fijo(problem, gd_cfg))  # regla x ← Π(x − η ∇f)
    else:  # variante "armijo": gd.eta no se lee ni se exige
        siguiente_x = _PasoArmijo(problem, *_parametros_armijo(gd_cfg))  # regla con retroceso
    tol_grad = _positivo_finito("gd.tol_grad", gd_cfg["tol_grad"])  # tolerancia de ‖∇f‖ validada
    # frames solo en 2D y si record_frames está activo (ausente = False)
    grabar = problem.func.dim == 2 and bool(cfg.get("record_frames", False))
    frames = _descenso(problem, siguiente_x, tol_grad, grabar, rng)  # ejecuta el bucle común

    resultado = {  # retorno con el contrato de §5.1, en tipos nativos serializables a JSON
        "x_best": problem.best_x.tolist(),  # mejor punto VISTO (no el último iterado)
        "f_best": float(problem.best_f),  # f en el mejor punto visto
        "n_f": int(problem.n_f),  # evaluaciones de f cobradas (0 en paso fijo)
        "n_grad": int(problem.n_grad),  # evaluaciones de ∇f cobradas
        "eval_equiv": float(problem.eval_equiv()),  # n_f + k·n_grad
        "history": problem.history,  # curva de convergencia [{eval_equiv, f_best}]
    }
    if grabar:  # la clave "frames" solo existe si se grabó
        resultado["frames"] = frames  # un frame por punto aceptado
    return resultado  # resultado de la corrida
