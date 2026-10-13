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

**Descenso por gradiente.** Con tasa de aprendizaje $\eta$ y $\Pi$ la proyección sobre el dominio (recorte de cada
coordenada a sus límites), la iteración de paso fijo es
$\mathbf{x}_{k+1} = \Pi\!\left(\mathbf{x}_k - \eta\,\nabla f(\mathbf{x}_k)\right)$.
La variante con búsqueda lineal de Armijo [@armijo1966], uno de los cinco métodos comparados, elige $\eta$ en cada
iteración por retroceso: parte de $\eta_0 = 1$ y aplica $\eta \leftarrow \beta\,\eta$ con $\beta = 0.5$ hasta que el punto
proyectado $\mathbf{x}_\eta = \Pi\!\left(\mathbf{x} - \eta\,\nabla f(\mathbf{x})\right)$ cumple

$$
f(\mathbf{x}_\eta) \le f(\mathbf{x}) - c\,\langle \nabla f(\mathbf{x}),\, \mathbf{x} - \mathbf{x}_\eta \rangle,
\qquad c = 10^{-4}.
$$

Cuando el recorte no actúa, $\mathbf{x} - \mathbf{x}_\eta = \eta\,\nabla f(\mathbf{x})$ y la condición se reduce a la forma
clásica $f(\mathbf{x}-\eta\nabla f) \le f(\mathbf{x}) - c\,\eta\,\lVert\nabla f\rVert^2$.

**Optimización por enjambre de partículas** [@kennedy1995], con peso de inercia $w$ [@shi1998]:

$$
\mathbf{v}_i \leftarrow w\,\mathbf{v}_i + c_1 r_1\,(\mathbf{p}_i - \mathbf{x}_i) + c_2 r_2\,(\mathbf{g} - \mathbf{x}_i),
\qquad \mathbf{x}_i \leftarrow \mathbf{x}_i + \mathbf{v}_i,
$$

donde $\mathbf{p}_i$ es la mejor posición visitada por la partícula y $\mathbf{g}$ la mejor del enjambre (la mejor de
las $\mathbf{p}_i$). Los números $r_1, r_2 \sim U(0,1)$ se sortean de nuevo en cada iteración, por partícula y por
componente, así que los productos $r_1\,(\mathbf{p}_i - \mathbf{x}_i)$ y $r_2\,(\mathbf{g} - \mathbf{x}_i)$ son componente
a componente. Las partículas parten en reposo: $\mathbf{v}_i = \mathbf{0}$ y $\mathbf{p}_i = \mathbf{x}_i$. Con
$[l_j, u_j]$ el intervalo del dominio en la coordenada $j$, cada componente de la velocidad se recorta a
$[-v_{\max,j},\, v_{\max,j}]$ antes de mover, con $v_{\max,j} = \gamma\,(u_j - l_j)$ y $\gamma$ el parámetro `vmax_frac`.
Si una componente de la nueva posición sale del dominio, se recorta a la frontera y la velocidad pasa a 0 solo en esa
componente.

Los valores $w = 0.7298$ y $c_1 = c_2 = 1.49618$ son las cifras redondeadas de la forma con factor de constricción para
$\varphi = 4.1$ (derivación propia):
<!-- TODO(cita): verificar Clerc & Kennedy (2002) antes de citarlo -->

$$
\chi = \frac{2}{\left\lvert\, 2 - \varphi - \sqrt{\varphi^2 - 4\varphi}\,\right\rvert} \approx 0.7298,
\qquad w = \chi,
\qquad c_1 = c_2 = \frac{\chi\,\varphi}{2} \approx 1.49618.
$$

**Evolución diferencial** (DE/rand/1/bin) [@storn1997]. Para cada individuo $\mathbf{x}_i$ se eligen tres padres
$r_1, r_2, r_3$ distintos entre sí y distintos de $i$, y se construye el mutante

$$
\mathbf{v}_i = \mathbf{x}_{r_1} + F\,(\mathbf{x}_{r_2} - \mathbf{x}_{r_3}).
$$

Cada componente del mutante que queda fuera de $[l_j, u_j]$ se vuelve a sortear con $U(l_j, u_j)$, antes del cruce. El
cruce binomial y la selección son

$$
u_{ij} = \begin{cases} v_{ij} & \text{si } U_{ij} \le CR \ \text{o}\ j = j_{\text{rand},i} \\ x_{ij} & \text{en otro caso,} \end{cases}
\qquad
\mathbf{x}_i \leftarrow \begin{cases} \mathbf{u}_i & \text{si } f(\mathbf{u}_i) \le f(\mathbf{x}_i) \\ \mathbf{x}_i & \text{en otro caso,} \end{cases}
$$

con $U_{ij} \sim U(0,1)$ y $j_{\text{rand},i}$ una coordenada sorteada por individuo, que asegura que el hijo toma al
menos una componente del mutante. En la selección el hijo gana el empate. El esquema es síncrono: todos los hijos de una
generación se construyen con la población que había al inicio de esa generación.

**Algoritmo evolutivo** de codificación real, con el esquema visto en clase.
<!-- TODO(cita): el esquema sale del material de clase IRNA202602 ("intro algoritmos evolutivos", Spec §6.4); no hay entrada en references.bib. -->
No hay selección de padres por aptitud. Cada generación forma la población siguiente apilando tres grupos y conservando
las primeras $N$ filas:

$$
P_{t+1} = \big[\ \text{élite}\ ;\ \text{mutantes}\ ;\ \text{hijos de cruce}\ \big]_{1:N}.
$$

Con $N$ individuos y las fracciones $f_e$, $f_m$ y $f_c$, los tamaños de los grupos son

$$
n_e = \operatorname{round}(N f_e), \qquad n_m = \lfloor N f_m \rfloor, \qquad
n_c = \max\!\Big(\operatorname{par}(\lfloor N f_c \rfloor),\ \operatorname{par}(N - n_e - n_m)\Big),
\qquad \operatorname{par}(n) = n + (n \bmod 2).
$$

El segundo término del máximo rellena la población cuando los tres grupos no suman $N$; si suman más, sobran hijos y se
quitan los últimos. La élite son los $n_e$ individuos de menor $f$, copiados sin cambio. Cada mutante es la copia de un
individuo elegido al azar en la que cambia un solo gen $g$, también elegido al azar:

$$
x'_{g} = \operatorname{clip}\big(x_{g} + \sigma_{g}\,z,\ l_{g},\ u_{g}\big), \qquad z \sim \mathcal{N}(0, 1),
\qquad \sigma_j = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\big(x_{ij} - \bar{x}_j\big)^2},
$$

donde $\sigma_j$ es la desviación estándar poblacional del gen $j$ en la población actual. El cruce es de un punto: para
una pareja $(\mathbf{p}, \mathbf{q})$ elegida al azar y un corte $c \in \{1, \dots, d-1\}$, con $d$ la dimensión, los dos
hijos son

$$
\mathbf{h}^{(1)} = (p_1, \dots, p_c,\ q_{c+1}, \dots, q_d), \qquad
\mathbf{h}^{(2)} = (q_1, \dots, q_c,\ p_{c+1}, \dots, p_d).
$$

### Problema del viajero (Parte 2)

Dado el conjunto $V$ de las 47 capitales, se busca la permutación $\pi$ que minimiza el costo del recorrido cerrado
$C(\pi) = \sum_{k=1}^{46} c_{\pi_k \pi_{k+1}} + c_{\pi_{47} \pi_1}$. El costo de cada tramo combina el valor de la hora $w$,
el tiempo $t$, los peajes $P$ y el combustible:

$$
c^{a}_{ij}(w) = w\,t^{a}_{ij} + P^{a}_{ij} + d^{a}_{ij}\,\frac{\text{consumo}}{100}\,p_{\text{comb}},
\qquad
c_{ij}(w) = \min\left(c^{\text{rápida}}_{ij}(w),\; c^{\text{sin peaje}}_{ij}(w)\right).
$$

Con 47 ciudades hay $46!/2 \approx 2{,}8 \times 10^{57}$ recorridos distintos, así que la búsqueda exhaustiva es
imposible. La formulación entera de @dantzig1954 daría el óptimo, pero quedó como tarea opcional y no se implementó: los
resultados se comparan contra el mejor recorrido encontrado.

**Colonia de hormigas.** Cada hormiga parte de una ciudad al azar y elige la siguiente, entre las no visitadas, con
probabilidad $p_{ij} \propto \tau_{ij}^{\alpha}\,\eta_{ij}^{\beta}$, con $\eta_{ij} = 1/c_{ij}$. Después de cada iteración
la feromona se actualiza como $\tau_{ij} \leftarrow (1-\rho)\,\tau_{ij} + \Delta\tau_{ij}$. En Ant System depositan
todas las hormigas, $\Delta\tau_{ij} = \sum_k 1/L_k$ sobre los arcos de cada recorrido $k$ de costo $L_k$ [@dorigo1996].
En MAX–MIN Ant System deposita una sola, $\Delta\tau_{ij} = 1/L^{\text{best}}$, y la feromona se recorta al intervalo
$[\tau_{\min}, \tau_{\max}]$ [@stutzle2000]:

$$
\tau_{\max} = \frac{1}{\rho\,L^{\text{bs}}},
\qquad
\tau_{\min} = \frac{\tau_{\max}\left(1 - p_{\text{best}}^{1/n}\right)}{\left(n/2 - 1\right)\,p_{\text{best}}^{1/n}},
$$

donde $L^{\text{bs}}$ es el costo del mejor recorrido encontrado hasta el momento y $n = 47$.

**Algoritmo genético para permutaciones.** Cada individuo es un orden de visita $\pi$ y se minimiza directamente
$C(\pi)$. Los padres se eligen por torneo, se cruzan con el cruce de orden (OX: el hijo copia un tramo de un padre y
completa el resto en el orden en que las ciudades aparecen en el otro), y los hijos mutan por inversión de un tramo o
intercambio de dos ciudades. Los mejores individuos pasan sin cambios a la generación siguiente (elitismo).
