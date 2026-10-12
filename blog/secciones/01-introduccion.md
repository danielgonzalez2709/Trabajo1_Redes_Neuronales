<!--
SECCIÓN: Introducción · RESPONSABLE: puente (Daniel) · ESTADO: borrador inicial (revisar al final).
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

<!-- TODO (al final): un párrafo con los resultados principales y la estructura del reporte. -->
