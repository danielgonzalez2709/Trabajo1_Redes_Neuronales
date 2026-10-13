# REFACTOR-PARTE1-COMUN — prompt literal (2026-10-12, sesión de Claude Code en modo plan, rama `parte1-optimizacion-numerica`)

## Prompt inicial

Aprovechando la suite de test actual me gustaría hacer un refactor del código de los algoritmos de pso, ea y ed, particularmente observo que tienen código repetido o se invocan entre ellos para llamar alguna función en concreto, me gustaría abstraer ese comportamiento repetitivo en otro archivo de utilidades. Pero antes evaluemos su factibilidad en base a la metodología actual (SPEC, PLAN y Memory). Recordemos que el principal objetivo es simplemente mejorar la legibilidad del código de ambas, así que acepto sugerencias que mejoren este objetivo sin realizar sobre-ingeniería

## Corrección del usuario (al presentar el plan de implementación)

Vamos a trabajar esto como una sugerencia de mejora a la spec y el plan, hacemos las modificaciones correspondientes para ello y daniel la validará cuando haga el PR de esto

## Precisión del usuario (antes del commit)

Necesito que a nivel de documentación, quede mejor definido que ese refactor comun es para la parte 1 y de las tareas T1.4, T1.5 y T1.6 antes de hacer el commit

## Resultado

Alcance: solo Parte 1, sobre lo entregado en T1.4 (`ea.py`), T1.5 (`pso.py`) y T1.6 (`de.py`).

Propuesta en `docs/spec/propuestas/REFACTOR-PARTE1-COMUN.md`; líneas `[PENDIENTE]` en `docs/spec/SPEC.md` (§4 y §5.1) y fila **T1.6b** en `docs/spec/PLAN.md`. No se modificó ningún `.py`. Nota: "ed" en el prompt = DE (evolución diferencial, `de.py`).
