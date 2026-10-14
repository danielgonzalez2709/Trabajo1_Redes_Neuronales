<!--
SECCIÓN: Introducción · RESPONSABLE: puente (Daniel) · ESTADO: borrador completo (13-oct).
Enunciado: "el entendimiento desarrollado en el trabajo". Explicar el propósito, las dos partes y el papel de la IA.
-->

## Introducción

Este trabajo compara dos familias de métodos de optimización. Los métodos basados en gradiente usan la información local
de la pendiente de la función; las metaheurísticas bioinspiradas exploran el espacio con poblaciones de soluciones
candidatas, como la optimización por enjambre de partículas [@kennedy1995], la evolución diferencial [@storn1997] y los
algoritmos evolutivos.

La comparación se hace en dos escenarios. En la Parte 1 se optimizan dos funciones de prueba continuas, en dos y tres
dimensiones, contando de forma explícita las evaluaciones de la función y de su gradiente para que la comparación sea
justa. En la Parte 2 se resuelve un problema combinatorio real: recorrer las 47 capitales de provincia de la España
peninsular al menor costo, con colonias de hormigas [@dorigo1996] y algoritmos genéticos, usando datos reales de
tiempos, peajes y combustible.

El trabajo se desarrolló con apoyo de herramientas de inteligencia artificial. Como la IA se equivoca, a veces con total
seguridad, una parte del trabajo consistió en verificar sus afirmaciones; los errores encontrados se documentan en la
sección *Cacería de la alucinación*.

Dos preguntas guían el trabajo. ¿Cuándo compensa usar la información del gradiente en lugar de explorar con una
población, si ambos pagan lo mismo por cada evaluación? ¿Y cómo cambia la mejor ruta por España cuando el tiempo del
viajero vale más o menos dinero? Para que las respuestas se puedan defender, todos los métodos comparten presupuesto,
semillas y protocolo, y los recorridos que encuentran las heurísticas de la Parte 2 se contrastan con el óptimo exacto
de la formulación de @dantzig1954.

El reporte sigue este orden. La *Fundamentación matemática* presenta las funciones de prueba, los algoritmos y el
modelo de costo del recorrido. Las secciones de la Parte 1 describen el protocolo y los resultados de la optimización
continua, incluida la afinación de hiperparámetros; las de la Parte 2, los datos reales, la metodología y los resultados
del recorrido. La *Discusión y conclusiones* contrasta las dos partes. Cierran el reporte el *Uso de inteligencia
artificial*, la *Cacería de la alucinación* y la *Reproducibilidad*, que explica cómo regenerar cada cifra y cada figura
desde el repositorio.
