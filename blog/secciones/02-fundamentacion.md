<!--
SECCIÓN: Fundamentación matemática · RESPONSABLES: equipo Parte 1 (funciones y algoritmos continuos) y equipo Parte 2 (TSP,
ACO, GA) · ESTADO: borrador con las ecuaciones del Spec (§6.1, §6.3, §6.4, §7.1, §7.3, §7.4) — cada equipo debe revisar que
coincidan EXACTAMENTE con su código y marcar aquí "revisado por <nombre>".
Enunciado: "definición de cada función de prueba, su dominio y su mínimo global; formulación del problema del viajero;
descripción de cada algoritmo con sus ecuaciones de actualización".
-->

## Fundamentación matemática

### Funciones de prueba

Se eligieron dos funciones con geometrías opuestas, resumidas en la [[tab:funciones]]. La función de Rosenbrock
[@rosenbrock1960] tiene un único mínimo en el fondo de un valle curvo y estrecho, lo que la hace mal condicionada. La
función de Rastrigin tiene una cantidad de mínimos locales que crece exponencialmente con la dimensión.
<!-- TODO(cita): referencia original de la función de Rastrigin, pendiente de verificar antes de citarla. -->

::: tabla funciones
Título: Funciones de prueba, dominio de búsqueda y mínimo global
Fuente: Elaboración propia a partir de la definición de cada función (Spec §6.1); gradientes verificados por diferencias centrales en tests/.
| Función | $f(\mathbf{x})$ | Dominio | Mínimo global |
|---|---|---|---|
| Rosenbrock | $\sum_{i=1}^{n-1}\left[100\,(x_{i+1}-x_i^2)^2 + (1-x_i)^2\right]$ | $[-2.048,\,2.048]^n$ | $f(\mathbf{1}) = 0$ |
| Rastrigin | $10n + \sum_{i=1}^{n}\left[x_i^2 - 10\cos(2\pi x_i)\right]$ | $[-5.12,\,5.12]^n$ | $f(\mathbf{0}) = 0$ |
:::

Los gradientes, usados por el descenso por gradiente, son:

$$
\frac{\partial f_{\text{Ros}}}{\partial x_i} = -400\,x_i\,(x_{i+1}-x_i^2) - 2\,(1-x_i)\;[\,i<n\,] \;+\; 200\,(x_i - x_{i-1}^2)\;[\,i>1\,],
\qquad
\frac{\partial f_{\text{Ras}}}{\partial x_i} = 2x_i + 20\pi\,\sin(2\pi x_i).
$$

### Algoritmos para la Parte 1

<!-- TODO equipo Parte 1: revisar contra el código final (nombres de parámetros y valores por defecto de configs/part1/base.yaml). -->

**Descenso por gradiente.** Con tasa de aprendizaje $\eta$ y proyección $\Pi$ sobre el dominio:
$\mathbf{x}_{k+1} = \Pi\!\left(\mathbf{x}_k - \eta\,\nabla f(\mathbf{x}_k)\right)$.
La variante opcional con búsqueda lineal de Armijo [@armijo1966] reduce $\eta$ a la mitad hasta que
$f(\mathbf{x}-\eta\nabla f) \le f(\mathbf{x}) - c\,\eta\,\lVert\nabla f\rVert^2$.

**Optimización por enjambre de partículas** [@kennedy1995], con peso de inercia $w$ [@shi1998]:

$$
\mathbf{v}_i \leftarrow w\,\mathbf{v}_i + c_1 r_1\,(\mathbf{p}_i - \mathbf{x}_i) + c_2 r_2\,(\mathbf{g} - \mathbf{x}_i),
\qquad \mathbf{x}_i \leftarrow \mathbf{x}_i + \mathbf{v}_i,
$$

donde $\mathbf{p}_i$ es la mejor posición de la partícula, $\mathbf{g}$ la mejor del enjambre y $r_1, r_2 \sim U(0,1)$.
Los valores $w = 0.7298$ y $c_1 = c_2 = 1.49618$ equivalen al factor de constricción de @clerc2002.

**Evolución diferencial** (DE/rand/1/bin) [@storn1997]: mutación $\mathbf{v}_i = \mathbf{x}_{r_1} + F\,(\mathbf{x}_{r_2} - \mathbf{x}_{r_3})$,
cruce binomial con probabilidad $CR$ (con al menos una componente del mutante) y selección codiciosa.

**Algoritmo evolutivo** de codificación real: selección por torneo, cruce BLX-$\alpha$, mutación gaussiana y elitismo.
<!-- TODO equipo Parte 1: ecuación del cruce BLX-α y de la mutación tal como quedaron implementadas. -->

### Problema del viajero (Parte 2)

<!-- TODO equipo Parte 2: revisar contra src/part2/ cuando exista. -->

Dado el conjunto $V$ de las 47 capitales, se busca la permutación $\pi$ que minimiza el costo del recorrido cerrado
$C(\pi) = \sum_{k=1}^{46} c_{\pi_k \pi_{k+1}} + c_{\pi_{47} \pi_1}$. El costo de cada tramo combina el valor de la hora $w$,
el tiempo $t$, los peajes $P$ y el combustible:

$$
c^{a}_{ij}(w) = w\,t^{a}_{ij} + P^{a}_{ij} + d^{a}_{ij}\,\frac{\text{consumo}}{100}\,p_{\text{comb}},
\qquad
c_{ij}(w) = \min\left(c^{\text{rápida}}_{ij}(w),\; c^{\text{sin peaje}}_{ij}(w)\right).
$$

El óptimo de referencia se obtiene con la formulación de @dantzig1954.

**Colonia de hormigas.** Cada hormiga elige la siguiente ciudad con probabilidad
$p_{ij} \propto \tau_{ij}^{\alpha}\,\eta_{ij}^{\beta}$, con $\eta_{ij} = 1/c_{ij}$, y la feromona se actualiza como
$\tau_{ij} \leftarrow (1-\rho)\,\tau_{ij} + \Delta\tau_{ij}$ [@dorigo1996].

**Algoritmo genético para permutaciones:** cruce de orden (OX), mutación por inversión e intercambio, torneo y elitismo.
<!-- TODO equipo Parte 2: ecuaciones y parámetros finales. -->
