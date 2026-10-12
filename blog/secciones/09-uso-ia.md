<!--
SECCIÓN: Uso de IA · RESPONSABLE: puente (Daniel) · ESTADO: borrador completo (12-oct-2026).
Enunciado: "los principales prompts utilizados y una discusión de su impacto en el resultado final".
Fuentes: alucinaciones/prompts/ (prompts literales), alucinaciones/registro.md, docs/MEMORIA.md (bitácora), docs/spec/PLAN.md.
TODO equipo Parte 1: cuando se fusione su rama, agregar a la Tabla de prompts las filas de T1.x (archivo alucinaciones/prompts/T1.x.md,
agente y propósito) y, si aplica, una línea en "Qué errores introdujo" con lo que detectaron sus revisores.
-->

## Uso de inteligencia artificial

### Herramientas y metodología

Todo el trabajo se desarrolló con Claude Code (modelo Claude Opus 5.5) siguiendo una metodología de *Subagent Driven
Development*. Una sesión orquestadora leía la especificación del proyecto (el *Spec*), tomaba la siguiente tarea del plan
y la encargaba a un subagente con un contexto mínimo: la sección del Spec, las interfaces que debía respetar y la prueba de
aceptación. El resultado no se aceptaba hasta pasar por revisores independientes, también subagentes, cada uno con un
rol definido en el repositorio (`.claude/agents/`):

- **Revisor de cumplimiento del Spec:** ¿hace exactamente lo pedido, ni más ni menos?
- **Revisor de calidad:** ¿el código se puede explicar y modificar en vivo?
- **Verificador matemático** (en tareas con fórmulas) y **curador de datos** (en la Parte 2), con la regla de no inventar ningún número.
- **Cazador de alucinaciones:** contrasta afirmaciones con fuentes primarias o experimentos.

Las personas del equipo tomaron las decisiones de diseño, que quedaron escritas en el Spec, y revisaron cada Pull Request
antes de fusionarlo. Además, cada prompt enviado a la IA se guardó **literal** en `alucinaciones/prompts/`, lo que permitió
rastrear de dónde salió cada error.

### Prompts principales

La [[tab:prompts]] resume los prompts que más influyeron en el resultado. El texto completo de cada uno, con todas sus
rondas de corrección, está en el archivo enlazado.

::: tabla prompts
Título: Prompts principales usados en el trabajo
Fuente: Elaboración propia a partir de alucinaciones/prompts/ del repositorio (texto literal de cada prompt).
| Fase | Prompt (archivo literal) | Enviado a | Propósito |
|---|---|---|---|
| Planeación | [Asesoría al puente, prompts A–D](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/asesoria_puente_claude.md) | Claude (conversación) | Entender el enunciado, comparar soluciones, escribir el Spec, el plan y los agentes, y armar el blog |
| Fundaciones | [T0.2](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T0.2.md) | implementador | Configuración YAML, cambios de parámetros con `--set` y `run.py` |
| Fundaciones | [T0.3](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T0.3.md) | implementador | Semillas reproducibles y guardado de resultados |
| Fundaciones | [T0.4](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T0.4.md) | implementador | Contador de evaluaciones de $f$ y $\nabla f$ con presupuesto |
| Datos (Parte 2) | [T2.1](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.1.md) | curador de datos | Coordenadas de las 47 capitales desde el IGN |
| Datos (Parte 2) | [T2.2](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.2.md), [T2.3](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.3.md) | curador de datos | OSRM local y las 2 162 rutas (rápida y sin peaje) |
| Datos (Parte 2) | [T2.4](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.4.md), [T2.5](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.5.md) | curador de datos | Tabla de tramos de peaje y su asignación a cada ruta |
| Datos (Parte 2) | [T2.6](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.6.md), [T2.7](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.7.md) | curador de datos | Precio del combustible y consumo del vehículo |
| Datos (Parte 2) | [T2.8](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.8.md) | curador de datos | Tabla de fuentes y pruebas de integridad de los datos |
| Algoritmos (Parte 2) | [T3.1](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T3.1.md) | implementador | Matriz de costos del problema del viajero |
:::

### Impacto en el resultado final

**Qué aceleró.** La IA permitió pasar del enunciado a una especificación completa, con plan de tareas e interfaces entre
módulos, en un par de días, y luego desarrollar en paralelo. Sin ella habría sido difícil construir en pocos días la base
común del código (con varios cientos de pruebas automáticas) o el conjunto de datos de la Parte 2: 47 coordenadas
oficiales, 2 162 rutas calculadas con OSRM, una tabla de tramos de peaje con tarifas oficiales y el precio del combustible,
cada dato con su fuente y su fecha de consulta.

**Qué errores introdujo.** El registro de la cacería reunió 23 candidatos, de los que se confirmaron nueve en cuatro
categorías (sección *Cacería de la alucinación*). Ninguno era absurdo: todos eran afirmaciones plausibles, como una
librería que «trae» un solucionador que ya no incluye, un contador que «nunca» se pasa del presupuesto o una prueba que
«verifica» algo que en realidad no puede fallar. También se observaron patrones repetidos:

- Cuando el Spec dejaba un hueco, la IA lo rellenaba por su cuenta. Por ejemplo, no se había definido cómo nombrar los
  métodos, y un nombre con guion bajo habría hecho que dos corridas distintas se guardaran en el mismo archivo. La respuesta
  fue cerrar cada hueco en el Spec antes de seguir.
- Al resumir, la IA a veces cambiaba el sentido de lo que había leído: «no encontré la ficha» terminaba como «la ficha no
  existe», o una tabla de un PDF se transcribía con los importes corridos una fila.
- Las afirmaciones sobre herramientas y datos caducan: versiones de librerías y autopistas que dejaron de cobrar peaje.

**Cómo se controlaron.** Casi todos los errores se detectaron **antes de llegar a la rama principal**, gracias a los
revisores independientes. Las tareas de la base común necesitaron entre dos y cuatro rondas de corrección cada una:
el revisor del Spec rechazó una entrega, el revisor de calidad encontró una conversión de tipos que no ocurría y una
prueba que no podía fallar, y el verificador matemático encontró un error de redondeo en el contador de evaluaciones.
Tres técnicas resultaron especialmente útiles y se volvieron reglas del proyecto: la **prueba de mutación** (romper el
código a propósito y comprobar que alguna prueba falla), contrastar toda referencia con el registro oficial de DOI y
repetir los experimentos cambiando las condiciones antes de aceptar una explicación.

**Lo que no se delegó.** Las decisiones de diseño (funciones de prueba, dominio, fecha de corte de los datos, vehículo,
modelo de costo) las tomó el equipo y quedaron registradas en el Spec. La verificación manual de las coordenadas y la
revisión de cada Pull Request también fueron humanas. La conclusión práctica es que la IA multiplicó la velocidad de
trabajo, pero solo fue confiable dentro de un proceso que asumía que podía equivocarse y estaba diseñado para detectarlo.
