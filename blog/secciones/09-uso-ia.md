<!--
SECCIÓN: Uso de IA · RESPONSABLE: puente (Daniel) · ESTADO: borrador de estructura.
Enunciado: "los principales prompts utilizados y una discusión de su impacto en el resultado final".
Fuentes: alucinaciones/prompts/ (prompts literales: asesoría al puente, T0.x, T2.x, T1.x) y docs/spec/PLAN.md.
-->

## Uso de inteligencia artificial

El desarrollo siguió una metodología de *Subagent Driven Development*: una sesión orquestadora repartió cada tarea del plan
a un subagente implementador y luego la sometió a revisores independientes (cumplimiento del Spec, calidad del código y,
cuando había fórmulas, verificación matemática). Los prompts literales de cada tarea se conservan en
`alucinaciones/prompts/` del repositorio.

<!-- TODO (puente): tabla de los prompts principales (fase, herramienta y modelo, propósito, enlace al archivo literal) y
discusión del impacto: qué aceleró, qué errores introdujo y cómo los detectaron los revisores (enlazar con la Cacería). -->
