<!--
SECCIÓN: Resumen · RESPONSABLE: puente (Daniel) · ESTADO: borrador completo (13-oct), revisar si cambian las cifras.
Cifras: Parte 1 desde results/data/part1/summary.json y results/data/part1_tuned/summary.json (éxitos a 1e-4 sumados
sobre las 4 configuraciones × 30 semillas = 120 corridas por método); Parte 2 desde results/data/part2/sweep_w.json
(gap de la media frente al mejor conocido, que es el óptimo en los 11 w) y results/data/part2/umbrales_exactos.json;
cacería desde alucinaciones/registro.md.
-->

## Resumen

Este trabajo compara métodos de optimización basados en gradiente con metaheurísticas bioinspiradas en dos escenarios.
En la Parte 1 se minimizan las funciones de Rosenbrock y Rastrigin en dos y tres dimensiones con descenso por gradiente
(paso fijo y búsqueda de Armijo), un algoritmo evolutivo (EA), optimización por enjambre de partículas (PSO) y evolución
diferencial (DE). Todos tienen el mismo presupuesto de evaluaciones equivalentes (un gradiente cuesta $2n$ evaluaciones
de la función) y 30 corridas por configuración. DE y PSO llegan a menos de $10^{-4}$ del mínimo global en 118 y 116 de
sus 120 corridas; el EA, en 45, y el descenso por gradiente, en 10 con Armijo y en 2 con paso fijo, porque se detiene en
los mínimos locales de Rastrigin y avanza despacio por el valle de Rosenbrock. Afinar los hiperparámetros con semillas
aparte sube el EA a 87 y Armijo a 51, sin cambiar el orden entre los métodos.

En la Parte 2 se busca el recorrido de menor costo por las 47 capitales de provincia de la España peninsular, con un
costo real que suma el tiempo valorado en $w$ €/h, los peajes y el combustible. Con el mismo número de recorridos
evaluados, la media de MAX–MIN Ant System queda entre 0,24 % y 0,75 % por encima del óptimo y la del algoritmo genético
entre 2,32 % y 4,07 %. La ruta óptima, verificada con un solver exacto, cambia en $w$ = 10,02, 14,53 y 42,19 €/h, aunque
las rutas que compiten difieren en pocos euros. Durante el trabajo se registraron más de 40 posibles errores de la
inteligencia artificial; 9 de ellos, en 4 categorías, quedaron confirmados.
