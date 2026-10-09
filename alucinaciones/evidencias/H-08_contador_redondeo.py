"""Evidencia H-08: la comprobación previa del presupuesto (versión de la ronda 1 de T0.4) no coincidía
con el estado posterior en punto flotante cuando k no es representable en binario.

Reproduce de forma independiente las dos expresiones (sin importar el código del proyecto):
  - versión ronda 1:  (n_f + k*n_grad) + k   > budget   -> comprobación
                      n_f + k*(n_grad+1)                 -> estado real después de aceptar
  - versión corregida: comprobar con la MISMA expresión que el estado posterior.
Reproducción encontrada por el subagente verificador-matematico (9-oct-2026).
"""
import math

def previa_ronda1(n_f, n_grad, k):
    return (n_f + k * n_grad) + k

def posterior(n_f, n_grad, k):
    return n_f + k * n_grad

casos = [
    ("k=1/3: se acepta y queda por encima", 1 / 3, 19.666666666666664, 18, 4),
    ("k=pi: se rechaza aunque cabe", math.pi, 53.982297150257104, 10, 13),
]
for nombre, k, budget, n_f, n_grad in casos:
    chk = previa_ronda1(n_f, n_grad, k)
    real = posterior(n_f, n_grad + 1, k)
    print(f"{nombre}: comprobacion_previa={chk!r} (> budget: {chk > budget}) | "
          f"estado_si_se_acepta={real!r} (> budget: {real > budget}) | budget={budget!r}")
print("k=inf: eval_equiv = n_f + inf*0 =", 0 + math.inf * 0, "-> toda comparación con NaN es False (el presupuesto se anula)")
