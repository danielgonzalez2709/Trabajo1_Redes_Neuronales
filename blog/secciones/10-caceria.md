<!--
SECCIÓN: Cacería de la alucinación · RESPONSABLE: puente (Daniel) · ESTADO: borrador completo (12-oct-2026); los 7 hallazgos
seleccionados figuran en el registro como confirmados por el puente (12-oct-2026).
Fuente única: alucinaciones/registro.md (estado, prompts literales y evidencias). No escribir aquí nada que no esté en el registro.
Enunciado: ≥5 hallazgos en ≥3 categorías; para cada uno: prompt literal, respuesta relevante, cómo se sospechó, evidencia,
corrección y lección. Un hallazgo inventado o sin evidencia se penaliza más que uno faltante.
-->

## Cacería de la alucinación

Durante todo el trabajo se llevó un registro de las afirmaciones de la IA que resultaron incorrectas, imprecisas,
desactualizadas o subóptimas: el [registro de la cacería](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/registro.md).
Cada entrada guarda el prompt literal que la originó (en `alucinaciones/prompts/`), la respuesta, cómo se sospechó, la
evidencia reproducible (en `alucinaciones/evidencias/`), la corrección y la lección. El registro reúne 38 candidatos;
aquí se presentan siete, elegidos porque cubren cuatro categorías y cada uno tiene prompt literal y evidencia que
cualquiera puede volver a ejecutar ([[tab:caceria]]). El registro también documenta las verificaciones que resultaron
correctas, porque comprobar y no encontrar un error también es información.

::: tabla caceria
Título: Hallazgos seleccionados de la cacería de la alucinación
Fuente: Elaboración propia a partir de alucinaciones/registro.md (evidencias en alucinaciones/evidencias/).
| Hallazgo | Categoría | Dónde apareció | Quién lo detectó |
|---|---|---|---|
| H-03: paso del descenso por gradiente "justificado" solo en el mínimo | Matemáticas | Asesoría del plan (29-sep) | El propio orquestador, al comparar dominios |
| H-07: "PuLP trae CBC" | Código | Asesoría del plan (29-sep) | El orquestador, al instalar el entorno |
| H-08: "el contador nunca supera el presupuesto" | Código | Subagente implementador (T0.4) | Subagente verificador matemático |
| H-10: una prueba que no puede fallar | Código | Subagente implementador (T0.2) | Subagente revisor de calidad |
| H-04: una generalización sin contar los otros casos | Datos del mundo real | Subagente curador de datos (T2.1) | El propio curador y el cazador |
| H-17: tarifas de la AP-9 desplazadas una fila | Datos del mundo real | Subagente curador de datos (T2.4) | El curador siguiente y el cazador |
| H-22: la revista de Dantzig, Fulkerson y Johnson | Bibliografía | Orquestador (T0.7) | El orquestador, contra Crossref |
:::

### H-03 · Matemáticas: un paso de descenso "justificado" que solo vale cerca del mínimo

- **Prompt literal** (29-sep-2026, [archivo completo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/asesoria_puente_claude.md), Prompt B): «Dame soluciones viables para cada parte con todos sus detalles, yo lo leo, evaluo, te consulto dudas si tengo alguna».
- **Respuesta de la IA:** calculó la Hessiana de Rosenbrock en el mínimo ($\lambda_{\max} \approx 1001.6$), concluyó «η < ≈0.002» y el Spec fijó $\eta = 10^{-3}$ como valor «justificado».
- **Cómo se sospechó:** al elegir el dominio de Rosenbrock se calculó la curvatura en **todo** el dominio, no solo en el mínimo.
- **Evidencia:** en $[-2.048, 2.048]^2$ la constante de Lipschitz del gradiente es $L \approx 5\,971$, así que la garantía de descenso exige $\eta \le 1/L \approx 1.7\times10^{-4}$; en $[-5, 10]^2$ ($L \approx 122\,133$) el mismo $\eta$ diverge ([script y salida](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-03_rosenbrock_dominio.txt)).
- **Corrección:** el Spec declara $\eta = 10^{-3}$ como elección **empírica**, sin garantía global, y usa $\eta = 1/L$ como análisis de sensibilidad. En Rastrigin sí hay garantía global ($L = 2 + 40\pi^2$).
- **Lección:** una cota de estabilidad local no justifica un paso fijo desde puntos iniciales lejanos.

### H-07 · Código: «PuLP trae CBC»

- **Prompt literal:** el mismo Prompt B (29-sep-2026).
- **Respuesta de la IA:** «Solver exacto TSP: PuLP (trae CBC)… `pip install` y listo, también en Windows».
- **Cómo se sospechó:** al construir el entorno con versiones fijas, `pulp.listSolvers(onlyAvailable=True)` devolvió una lista vacía.
- **Evidencia:** con PuLP 4.0.0 no hay ningún solver instalado, `PULP_CBC_CMD` ya no existe y la forma clásica `LpVariable(..., cat="Binary")` lanza `TypeError`; la página oficial de PuLP en PyPI confirma que CBC dejó de incluirse ([script y salida](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-07_pulp4.txt)).
- **Corrección:** se instala `pulp[highs]` y se usa la API nueva (`problema.add_variable`); el script de evidencia resuelve un problema del viajero de 6 ciudades y coincide con la fuerza bruta.
- **Lección:** lo que una IA sabe de una librería caduca con cada versión mayor; hay que fijar versiones y comprobar la instalación real.

### H-08 · Código: «el contador nunca supera el presupuesto»

- **Prompt literal** (T0.4, [archivo completo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T0.4.md)): «BudgetExhausted se lanza ANTES de exceder: el contador nunca supera el presupuesto, incluso con grad de costo k».
- **Respuesta de la IA:** un contador que comprobaba `eval_equiv() + k > budget` y una prueba «aleatoria» que lo declaraba correcto.
- **Cómo se sospechó:** el subagente verificador matemático probó a propósito valores de $k$ que no se representan exactamente en binario.
- **Evidencia:** con $k = 1/3$ y un presupuesto de 19.666666666666664, la comprobación aceptaba una llamada que dejaba el contador en 19.666666666666668, por encima del presupuesto; con $k = \pi$ rechazaba una que sí cabía; con $k = \infty$ el presupuesto dejaba de funcionar. La prueba original solo usaba $k \in \{1, 4, 6, 2.5\}$, todos exactos en binario ([reproducción](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-08_contador_redondeo.txt)).
- **Corrección:** la comprobación previa usa exactamente la misma expresión que el estado posterior; tras la corrección, 0 anomalías en unos 9 millones de llamadas.
- **Lección:** una prueba aleatoria no cubre lo que no varía. Si todos los valores de prueba son exactos en binario, el redondeo nunca aparece.

### H-10 · Código: una prueba que no puede fallar

- **Prompt literal** (T0.2, ronda 3, [archivo completo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T0.2.md)): «fusiona en profundidad (la hija gana; las listas se reemplazan, no se concatenan)».
- **Respuesta de la IA:** una fusión de configuraciones que prometía «no muta las entradas» y una prueba llamada `test_herencia_no_comparte_objetos_con_la_base` que decía verificarlo.
- **Cómo se sospechó:** el subagente revisor de calidad sustituyó la fusión por una versión rota a propósito.
- **Evidencia:** con una fusión que muta la base y comparte objetos, **las 14 pruebas de herencia seguían pasando**: la prueba leía el archivo dos veces del disco, así que nunca podía detectar el error ([prueba de mutación](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-10_prueba_que_no_falla.py)).
- **Corrección:** se eliminó la prueba engañosa y se documentó el comportamiento real; en la revisión final, 10 de 10 mutantes ponen alguna prueba en rojo.
- **Lección:** una prueba que no puede fallar es una afirmación disfrazada. La prueba de mutación (romper el código a propósito y ver si algo se pone rojo) se adoptó como práctica del proyecto.

### H-04 · Datos del mundo real: una generalización sin contar los demás casos

- **Prompt literal** (T2.1, Prompt 2, [archivo completo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.1.md)): «Señala cualquier diferencia > 0,5 km y explícala».
- **Respuesta de la IA:** «La contra es que en esas 9 capitales el NGMEP marca el origen de la coordenada como "Detección automática", que parece un proceso menos cuidado que el de IGR».
- **Cómo se sospechó:** al escribir la caracterización, el subagente contó los valores del campo `ORIGENCOOR` en lugar de repetir la frase.
- **Evidencia:** 38 de las 47 capitales tienen «Detección automática», no solo las 9 que difieren, así que ese valor no distingue nada; además, Valladolid, una de las 9, tiene otro origen ([verificación desde el archivo crudo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-04_origencoor_ngmep.txt)).
- **Corrección:** se retiró el argumento de la decisión entre las dos fuentes de coordenadas y la caracterización documenta las cifras reales.
- **Lección:** afirmar que «todos los casos X tienen la propiedad Y» exige contar Y también en los casos que no son X.

### H-17 · Datos del mundo real: tarifas de la AP-9 desplazadas una fila

- **Prompt literal** (T2.4, ronda 2, [archivo completo](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/prompts/T2.4.md)): «Si una tarifa no aparece en un crudo oficial, pon `TODO(dato-faltante)` … NUNCA la deduzcas».
- **Respuesta de la IA:** una tabla con Caldas de Reis–Curro a 2,85 €, Caldas de Reis–Pontevedra a 1,80 €, Curro–Pontevedra a 1,45 €…
- **Cómo se sospechó:** el curador que rehízo la tabla releyó el PDF del Ministerio y los importes no cuadraban.
- **Evidencia:** el PDF oficial da 1,65 €, 2,85 € y 1,80 € para esos tramos, y la calculadora oficial de Audasa confirma los mismos importes; la tabla de descuento del 50 % del mismo PDF confirma la alineación. Cada importe se había corrido una fila hacia arriba al emparejar nombres e importes extraídos del PDF ([verificación](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/T2.4_verificacion.txt)).
- **Corrección:** la tabla final usa los importes verificados por el cazador.
- **Lección:** en tablas extraídas de un PDF hay que comprobar la alineación con una segunda columna o tabla relacionada. Un desplazamiento de una fila produce importes plausibles e invisibles a simple vista.

### H-22 · Bibliografía: la revista de Dantzig, Fulkerson y Johnson (1954)

- **Prompt literal** (12-oct-2026, Prompt D): «Avancemos con el esqueleto del blog».
- **Respuesta de la IA:** antes de consultar ninguna fuente, la IA escribió de memoria una lista de 11 referencias con su DOI; atribuyó el artículo de @dantzig1954 a la revista *Operations Research*.
- **Cómo se sospechó:** la regla del proyecto es que ninguna referencia se escribe de memoria: todas se contrastan con el registro oficial de DOI.
- **Evidencia:** Crossref registra la revista como *Journal of the Operations Research Society of America*, el nombre que tenía en 1954; el DOI usa el nombre actual (`opre`), lo que facilita la confusión. Las otras diez referencias coincidieron en autor y año ([verificación contra Crossref](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales/blob/main/alucinaciones/evidencias/H-bib_verificacion_doi.txt)).
- **Corrección:** la bibliografía usa el BibTeX oficial de cada DOI, con el nombre de la revista registrado en 1954.
- **Lección:** APA cita la revista con el nombre que tenía al publicarse el artículo, y el DOI no sirve para deducirlo. Además, copiar del registro a ciegas tampoco basta: Crossref traía dañado el título del artículo de @stutzle2000.

### Lecciones transversales

Los siete hallazgos comparten un patrón: la IA no inventó nada absurdo, sino afirmaciones **plausibles** que nadie habría
cuestionado sin comprobarlas. Las verificaciones que los detectaron fueron sencillas y se volvieron reglas del proyecto:
contar la propiedad en todos los casos y no solo en los que se quieren explicar (H-04), probar valores que no sean exactos
en binario (H-08), romper el código a propósito para comprobar que las pruebas fallan (H-10), fijar versiones y comprobar la
instalación real (H-07) y no citar nada que no venga del registro oficial (H-22). La mayoría se detectaron gracias a que
cada tarea pasó por revisores independientes (cumplimiento del Spec, calidad del código, verificación matemática y
cazador de alucinaciones), como se describe en la sección *Uso de inteligencia artificial*.
