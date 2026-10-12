# CAMBIO-EA — prompt literal (2026-10-12, sesión de Claude Code en modo plan, rama `feat/parte1/t1.4-ea`)

## Prompt inicial

Estás en modo plan: NO modifiques ni crees archivos todavía. Idioma: español. Responde breve y claro; soy nuevo usando Claude Code.

OBJETIVO
Evaluar el impacto de incorporar a la Parte 1 el algoritmo evolutivo visto en clase y proponerme un plan de cambio de
especificación. NO es la tarea T1.4: aquí solo decidimos qué cambia en documentos y contratos. No escribas código de producción.

LEE PRIMERO (en este orden)
docs/MEMORIA.md, CLAUDE.md, docs/spec/SPEC.md (§0, §3, §5.1, §5.4, §6.2, §6.4, §6.5, §6.6, §6.7, §12, §14), docs/spec/PLAN.md (T1.4, T1.7, T1.8, T1.9, T4.2, T4.3),
configs/part1/base.yaml, src/common/counter.py, src/common/config.py, tests/test_budget.py, tests/test_counter.py, tutoria/03_prompt_T1.4_algoritmo_evolutivo.md (sección B).

ALGORITMO (resumen; población = matriz N×d, cada fila un individuo)
1. Población inicial uniforme en [lb, ub] con semilla.
2. Cada generación: evaluar todos; ordenar de mejor a peor.
3. Nueva población = élite (primeras round(N·frac_e) filas) + mutantes + hijos de cruce, recortada a N filas.
   - Mutantes: int(N·frac_m) individuos elegidos al azar sin repetir; a cada uno se le muta UN solo gen sumando N(0, σ²) con σ = desviación
     estándar poblacional de ese gen; se recorta al dominio.
   - Cruce: int(N·frac_c) individuos (se fuerza número par) elegidos al azar sin repetir, sin considerar su aptitud; se parten en dos mitades;
     cada pareja produce 2 hijos por cruce de un punto con punto aleatorio.
   - Parámetros: frac_e=0.15, frac_m=0.10, frac_c=0.75, N=50. (Particularmente los nombramos frac pq recuerdo en clase que su uso viene de que si quiero 4 elites uso 4/población total y en ese sentido lo bautizamos frac, pero en la práctica terminamos usando el porcentaje directo)
4. Parada: número fijo de generaciones.
Defectos CONOCIDOS del cuaderno que NO deben heredarse: (a) el ranking usaba las aptitudes de la población inicial en lugar de las actuales;
(b) la evaluación recalculaba la población dentro de un bucle y usaba variables globales; (c) el punto de cruce podía ser 0 y producir copias de los padres;
(d) la función de prueba no era la Rastrigin estándar.

QUÉ NECESITO QUE ANALICES
1. Tabla comparativa propuesta vs. lo que dice hoy el Spec §6.4/PLAN T1.4 (selección, cruce, mutación, élite, reemplazo, parámetros, conteo de evaluaciones).
2. Opciones de cambio, al menos estas dos y las que veas:
   A) Un solo algoritmo con operadores y esquema de generación configurables (`esquema: spec | clase`), con el Spec como valor por defecto en `base.yaml`.
   B) Reemplazar el Spec por el esquema de clase.
   Para cada opción: ventajas, riesgos, y si se puede cumplir la regla "los algoritmos no cuentan a mano" y la comparación justa por evaluaciones (§6.2).
3. Impacto archivo por archivo, indicando para cada uno: cambia / no cambia, qué línea o sección, y por qué:
   SPEC.md (secciones), PLAN.md (T1.4, T1.7, T1.8, T1.9 y tareas de figuras/GIF), configs/part1/base.yaml y demo.yaml, contrato `optimize()` de §5.1,
   forma de `frames`/`history`, tests existentes que podrían romperse, y MEMORIA.md.
4. Conteo de evaluaciones: ¿cuántas evaluaciones por generación cuesta cada esquema con `CountedProblem`? ¿Se reevalúa la élite? ¿Qué ocurre cuando el presupuesto
   se agota a mitad de generación (regla de truncar, §6.2)? ¿Cómo afecta a los 20 configs × 30 semillas de §6.5?
5. Reproducibilidad: el proyecto exige `np.random.default_rng(base_seed + run_id)`. ¿Qué cambia se debe hacer para que el la propuesta de algoritmo se adapte al flujo de trabajo??
6. Riesgos para la nota (rúbrica, cacería de alucinaciones, sustentación) y para el cronograma (entrega mar 13-oct-2026 23:59).
7. Qué decisiones son [DECIDIDO] en el Spec y no se pueden tocar sin escalar, y cuáles son parámetros sobrescribibles.

CÓMO QUIERO EL PLAN
- Primero HAZME PREGUNTAS sobre lo que no puedas decidir con el repo. Espera mis respuestas.
- Luego entrega un plan en este orden: resumen de una frase, opción recomendada con su razón, tabla de impacto, riesgos, pasos con sus entregables, y qué texto concreto propondrías añadir al Spec (como borrador, sin editarlo).
- Marca claramente lo que verificaste leyendo el repo y lo que supones.
- No inventes parámetros, referencias ni cifras. Si falta algo: TODO(dato-faltante).
- Cuando yo apruebe el plan, el único archivo que podrás crear es docs/spec/propuestas/CAMBIO-EA.md y el archivo con este prompt
  literal en alucinaciones/prompts/CAMBIO-EA.md. No toques SPEC.md, PLAN.md ni código: los cambios al Spec los hacemos el equipo.
- NUNCA hagas commit, push, merge ni cambies de rama.

## Respuestas del usuario durante el plan

**Ronda 1 (preguntas de Claude: opción, valor por defecto, tamaño N, élite):**
- Opción: "Me gusta mucho la propuesta de solo esquema de clase, tendríamos que modificar la spec y el plan, pero genuinamente no me desagradó el torneo/Blx, optaría por implementarlo si es que da tiempo, dado el pazo de entrega es muy posible que no, pero no estaría mal"
- Valor por defecto: "El de clase"
- Tamaño N: "Par hacia arriba y recortar (Recomendada)"
- Élite: "No termino de entender esto del todo, pq tendria que evaluar la elite nuevamente en una misma generación?, se supone que simplemente la evaluo toda una vez para determinar la elite y ya, todo lo demás ocurre con la población(i), es decir con esa genero mutantes y cruces, luego uno todo en la población(i+1) y chao generación pasamos a la siguiente iteración y tenemos que evaluar todo de nuevo pq si en la mutación o el cruzamiento se generaron mejores individuos que la elite los tengro que reemplazar. Esto es lo que entiendo de esto, podrias ayudarme a clarificarlo aunque también puede que sea un error tuyo"

**Ronda 2:**
- "Creo que ya entiendo el problema, entonces la primera generación haria 50 (por población inicial) eval de la función, pero posteriormente las próximas generaciones harían de a 42 (con elitismo 0.2 obviamente) pq las otras 8 ya las hicieron de antes y se guardaron el vector de aptitudes. Si lo entendí bien, entonces estoy de acuerdo con la idea y te agradezco que me hayas ayudado a comprenderla."

**Ronda 3:**
- "Puedes borrar lo de aclaración sobre la elite (pregunta del usuario) del plan. Ahora respecto a las preguntas 1. reevaluar_elite queda en false por defecto, 2. Se descartan, las conservaré en local simplemente, no quiero que hagas relación a ella en el spec 3. Es material de clase: IRNA202602 intro algoritmos evolutivos.ipynb 4. La verdad es que no sé que indica la spec o el plan o claude.md respecto a los tests, pero quizás sea útil definirlo también en el plan, qué opinas?"

**Ronda 4:**
- "Pendiente: no pongamos fecha / https://colab.research.google.com/drive/1QvaXDJAPgiuQOuKcvZB-lpiRbPGqLHne?authuser=1&usp=classroom_web#scrollTo=OlrNA-1QkE1Y"
