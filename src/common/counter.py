"""Contador de evaluaciones y presupuesto de la Parte 1 (Spec §5.1 y §6.2).

`CountedProblem` es el ÚNICO lugar donde se cuentan evaluaciones de f y de ∇f. Los optimizadores
no cuentan a mano: llaman a `f`/`grad`, capturan `BudgetExhausted` y devuelven el mejor resultado
([DECIDIDO 9-oct, T0.4]).

Garantía precisa: después de cualquier llamada ACEPTADA a `f` o `grad`, `eval_equiv() <= budget`
(en coma flotante). Para que sea exacta, la fórmula n_f + k·n_grad vive en un solo lugar
(`_equiv`) y la comprobación previa la evalúa sobre los contadores que quedarían tras la llamada:
`_equiv(n_f + 1, n_grad)` en `f` y `_equiv(n_f, n_grad + 1)` en `grad`, que es exactamente lo que
`eval_equiv()` devolverá después. Una llamada rechazada no evalúa, no cuenta y no toca best/history.
"""

from __future__ import annotations

import math

import numpy as np


class BudgetExhausted(Exception):
    """Se lanza ANTES de una evaluación tras la cual eval_equiv() > budget.

    Esa evaluación no se hace ni se cuenta.
    """


def _validar_positivo_finito(nombre: str, valor) -> None:
    """Exige un número real finito y > 0; rechaza bool (True/False no son costos ni
    presupuestos)."""
    if isinstance(valor, (bool, np.bool_)):
        raise TypeError(f"{nombre} no puede ser bool (recibido {valor!r})")
    if not (0 < valor < math.inf):  # también rechaza NaN y ±inf
        raise ValueError(f"{nombre} debe ser finito y > 0 (recibido {valor!r})")


class CountedProblem:
    """Envuelve una TestFunction (dim, bounds, x_star, f_star, f(x), grad(x)) y cuenta evaluaciones.

    Parámetros
    ----------
    func:   objeto con la interfaz de TestFunction (§5.1).
    k:      costo de una evaluación de ∇f en evaluaciones de f (principal k = 2n; sensibilidad
            k = 1, §6.2). Finito y > 0.
    budget: presupuesto en evaluaciones equivalentes (n_f + k·n_grad). Finito y > 0 (§5.1: el
            JSON no admite inf).
    """

    def __init__(self, func, k: float, budget: float):
        _validar_positivo_finito("k", k)
        _validar_positivo_finito("budget", budget)
        self.func = func
        # float de Python: con np.float32 la comparación se haría en float32 (NEP 50) y el contador
        # podría exceder el presupuesto por < 1 ulp.
        self.k = float(k)
        self.budget = float(budget)
        self.n_f: int = 0
        self.n_grad: int = 0
        self.best_x: np.ndarray | None = None
        self.best_f: float = math.inf
        self.history: list[dict] = []

    # ------------------------------------------------------------------ conteo
    def _equiv(self, n_f: int, n_grad: int) -> float:
        """Única definición de n_f + k·n_grad con el k del presupuesto (el del constructor).

        Todas las comprobaciones de presupuesto y eval_equiv() la usan; eval_equiv(k=otro) evalúa la
        misma suma con otro k solo para reportar sensibilidad (§6.2), sin afectar el presupuesto.
        """
        return n_f + self.k * n_grad

    def eval_equiv(self, k: float | None = None) -> float:
        """n_f + k·n_grad como float; k por defecto = el del constructor."""
        if k is None:
            return float(self._equiv(self.n_f, self.n_grad))
        return float(self.n_f + k * self.n_grad)

    def budget_exhausted(self) -> bool:
        """True si ya no cabe ni una evaluación de f (misma comprobación que `f`).

        Con k >= 1 (el caso del Spec: k = 2n o k = 1) equivale a "no cabe nada", porque un
        gradiente cuesta al menos lo mismo que una f. Con k < 1 podría devolver True y aún caber
        un gradiente.
        """
        return self._equiv(self.n_f + 1, self.n_grad) > self.budget

    # ------------------------------------------------------------ evaluaciones
    def f(self, x) -> float:
        """Evalúa f(x) contando 1 evaluación.

        Lanza BudgetExhausted (sin evaluar ni contar) si tras contarla eval_equiv() > budget.
        """
        if self.budget_exhausted():
            raise BudgetExhausted(
                f"f excedería el presupuesto: eval_equiv={self.eval_equiv()} + 1 "
                f"> budget={self.budget}"
            )
        valor = float(self.func.f(x))
        self.n_f += 1
        self._registrar(x, valor)
        return valor

    def grad(self, x) -> np.ndarray:
        """Evalúa ∇f(x) contando k evaluaciones equivalentes.

        Lanza BudgetExhausted (sin evaluar ni contar) si tras contarlo eval_equiv() > budget.
        """
        if self._equiv(self.n_f, self.n_grad + 1) > self.budget:
            raise BudgetExhausted(
                f"grad excedería el presupuesto: eval_equiv={self.eval_equiv()} + k={self.k} "
                f"> budget={self.budget}"
            )
        g = self.func.grad(x)
        self.n_grad += 1
        return g

    def observe(self, x) -> None:
        """Evalúa f(x) SIN contar, solo para actualizar best/history.

        Retorna None a propósito: el algoritmo no puede usar el valor (§5.1).
        """
        self._registrar(x, float(self.func.f(x)))

    # ---------------------------------------------------------------- interno
    def _registrar(self, x, valor: float) -> None:
        """Actualiza best_x/best_f (copia de x) y agrega a history solo si best_f mejora
        estrictamente. Un NaN nunca mejora (NaN < best_f es False)."""
        if valor < self.best_f:
            self.best_f = valor
            self.best_x = np.array(x, dtype=float, copy=True)
            self.history.append({"eval_equiv": self.eval_equiv(), "f_best": valor})
