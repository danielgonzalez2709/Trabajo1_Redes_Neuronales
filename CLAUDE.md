# Trabajo 1 — Optimización numérica, metaheurística y combinatoria

Fuente de verdad: `docs/spec/SPEC.md`. Plan de tareas: `docs/spec/PLAN.md`. Idioma del proyecto: español.

## Reglas para cualquier sesión o subagente
- No contradecir el Spec. Lo marcado [DECIDIDO] no se cambia; lo [PENDIENTE] se escala a los humanos.
- **Prohibido inventar** datos, constantes, tarifas, referencias o resultados. Si falta algo: `TODO(dato-faltante)` y reportarlo.
- Todo dato del mundo real lleva URL + fecha de consulta en `data/fuentes.md`.
- Los experimentos nunca usan internet; solo `scripts/descargar_datos.py` puede hacerlo.
- Toda evaluación de funciones de la Parte 1 pasa por `CountedProblem`; nadie cuenta evaluaciones a mano.
- Semillas con `np.random.default_rng(base_seed + run_id)`.
- Prueba primero, luego código.

## Protocolo del orquestador (sesión principal)
1. Tomar la siguiente tarea ⬜ del `PLAN.md` cuyas dependencias estén ✅.
2. Armar el contexto del implementador: texto de la tarea + sección del Spec + contratos §5 + prueba de aceptación. Nada más.
3. **Guardar el prompt literal** en `alucinaciones/prompts/<ID>.md` antes de enviarlo.
4. Despachar `implementador` (o `curador-datos` en tareas de datos de F2).
5. Despachar `revisor-spec`; si falla, devolver al implementador con los hallazgos.
6. Despachar `revisor-calidad`; si falla, ídem.
7. Despachar el verificador especializado indicado en la columna "+ Verificador".
8. Cualquier error de un subagente que haya sido detectado (fórmula, dato, referencia, conteo) → anotar candidato en `alucinaciones/registro.md`.
9. Marcar la tarea en `PLAN.md` y abrir el PR para revisión del puente (humano).
