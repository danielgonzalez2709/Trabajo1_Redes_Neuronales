<!--
SECCIÓN: Parte 1 — metodología · RESPONSABLE: equipo Parte 1 · ESTADO: borrador (13-oct-2026): protocolo, GD, EA, PSO y DE
redactados; falta la subsección "Ajuste de hiperparámetros".
Enunciado (regla de comparación justa): contar por separado las evaluaciones de f y de ∇f; proponer y justificar la
equivalencia (1 ∇f = 2n evaluaciones de f, diferencias centrales; sensibilidad k = 1 — cita sugerida: @berahas2022);
≥30 corridas independientes por configuración; reportar media, desviación estándar, mejor, peor y tasa de éxito con un
umbral definido (f − f* ≤ 1e-4). Explicar el presupuesto (10 000·n evaluaciones equivalentes), las semillas (0–29) y la
elección de η (Spec §6.3: garantía global solo en Rastrigin; en Rosenbrock η = 1e-3 es empírica).
Fuente de datos: configs/part1/base.yaml y src/common/counter.py.
-->

## Parte 1: metodología

### Protocolo experimental común

Cada corrida dispone del mismo presupuesto de $10\,000 \cdot n$ evaluaciones equivalentes, con $n$ la dimensión: 20 000 en
2D y 30 000 en 3D. Ningún algoritmo cuenta sus evaluaciones a mano. Todos evalúan $f$ y $\nabla f$ a través de un contador
único (`CountedProblem`, en `src/common/counter.py`) que lleva por separado el número de evaluaciones de la función, $n_f$,
y el de gradientes, $n_{\text{grad}}$, y las combina como

$$
\text{eval\_equiv} = n_f + k\,n_{\text{grad}}.
$$

El contador rechaza, antes de hacerla, cualquier evaluación tras la cual se excedería el presupuesto. Esa evaluación no se
hace ni se cuenta, y el algoritmo devuelve el mejor punto visto hasta ese momento.

La equivalencia principal es $k = 2n$. Es lo que costaría aproximar el gradiente por diferencias centrales, que
necesitan dos evaluaciones de $f$ por coordenada, $f(\mathbf{x} + h\,\mathbf{e}_i)$ y $f(\mathbf{x} - h\,\mathbf{e}_i)$. Así,
el descenso por gradiente y las metaheurísticas, que solo usan valores de $f$, se comparan en la misma moneda. El costo de
aproximar gradientes con evaluaciones de la función es justamente lo que estudian @berahas2022. Pero en este trabajo el
gradiente es analítico y no se calcula por diferencias finitas, así que $k = 2n$ es una convención y no un costo medido.
Por eso se añade un análisis de sensibilidad con $k = 1$, la más favorable al descenso por gradiente de las dos
equivalencias: la tabla de resultados se repite con ese valor (Spec §6.2).

Cada una de las 20 configuraciones (2 funciones × 2 dimensiones × 5 métodos: GD de paso fijo, GD con Armijo, EA, PSO y DE)
se ejecuta 30 veces de forma independiente. La corrida `run_id` usa el generador `np.random.default_rng(base_seed + run_id)`
con `base_seed = 0`, es decir, las semillas 0 a 29, las mismas para todos los métodos. Una corrida tiene éxito si
$f - f^* \le 10^{-4}$, que es el umbral principal; también se reportan los umbrales $10^{-2}$ y $10^{-6}$. Por cada
configuración se reportan:

- media, desviación estándar, mediana, mejor y peor valor de $f_{\text{final}}$;
- $n_f$ y $n_{\text{grad}}$ medios, por separado;
- evaluaciones equivalentes con $k = 2n$ y con $k = 1$;
- tasa de éxito;
- evaluaciones hasta el éxito (media sobre las corridas exitosas).

Los parámetros de los dos descensos por gradiente están en la [[tab:parametros-gd]].

::: tabla parametros-gd
Título: Parámetros del descenso por gradiente (paso fijo y Armijo)
Fuente: Elaboración propia a partir de configs/part1/base.yaml
| Parámetro | Clave en `base.yaml` | Variante | Valor |
|---|---|---|---|
| Paso fijo $\eta$ en Rosenbrock | `gd.eta.rosenbrock` | paso fijo | `1e-3` |
| Paso fijo $\eta$ en Rastrigin | `gd.eta.rastrigin` | paso fijo | `2e-3` |
| Paso inicial $\eta_0$ | `gd.armijo.eta0` | Armijo | `1.0` |
| Factor de retroceso $\beta$ | `gd.armijo.beta` | Armijo | `0.5` |
| Constante de Armijo $c$ | `gd.armijo.c` | Armijo | `1e-4` |
| Tolerancia de parada sobre la norma de $\nabla f$ | `gd.tol_grad` | ambas | `1e-8` |
:::

### Descenso por gradiente de paso fijo

La iteración es

$$
\mathbf{x}_{k+1} = \Pi\!\left(\mathbf{x}_k - \eta\,\nabla f(\mathbf{x}_k)\right),
$$

donde $\Pi$ recorta cada coordenada a los límites del dominio. El punto inicial $\mathbf{x}_0$ se sortea uniformemente en
el dominio con una sola llamada `rng.uniform(lo, hi)`. Es el único uso del generador aleatorio, así que el resto de la
corrida es determinista. En cada iteración se calcula $\nabla f(\mathbf{x}_k)$. Si
$\lVert\nabla f(\mathbf{x}_k)\rVert < 10^{-8}$ (`gd.tol_grad`), la corrida termina sin dar el paso. Si no, se aplica la
iteración. La otra forma de terminar es que el contador rechace el siguiente gradiente porque agotaría el presupuesto.

Esta variante nunca usa el valor de $f$ para decidir. El punto inicial y cada iterado se registran sin costo (método
`observe` del contador) solo para construir la curva de convergencia y conocer el mejor punto visto. Por eso $n_f = 0$, y
cada gradiente cuesta $k$ evaluaciones equivalentes. Con $k = 2n$ el presupuesto alcanza para
$\lfloor 10\,000\,n / 2n \rfloor = 5\,000$ gradientes en ambas dimensiones. La corrida devuelve el mejor punto visto, que
no tiene por qué ser el último iterado.

**Elección de $\eta$ en Rastrigin ($\eta = 2\times10^{-3}$, con garantía global).** Para una función cuyo gradiente es
$L$-Lipschitz, proyectada sobre un convexo (el dominio es una caja), $\eta \le 1/L$ asegura descenso monótono (Spec
§6.3). <!-- TODO(cita): resultado de descenso para gradiente proyectado con paso 1/L; nocedal2006 está en references.bib pero no se ha verificado la página o sección que lo respalda. -->
La Hessiana de Rastrigin es diagonal, porque cada término de la suma depende de una sola coordenada:

$$
\frac{\partial^2 f_{\text{Ras}}}{\partial x_i^2} = 2 + 40\pi^2\cos(2\pi x_i),
\qquad
\frac{\partial^2 f_{\text{Ras}}}{\partial x_i\,\partial x_j} = 0 \quad (i \ne j).
$$

Sus valores propios son los elementos de la diagonal y están en $[\,2 - 40\pi^2,\; 2 + 40\pi^2\,]$. El de mayor valor
absoluto da $L = 2 + 40\pi^2 \approx 396.8$, válido en todo $\mathbb{R}^n$ y en cualquier dimensión. Entonces
$1/L \approx 2.52\times10^{-3}$ y el paso $\eta = 2\times10^{-3}$ cumple la condición. La garantía es de descenso
monótono, no de llegar al mínimo global: en una función con tantos mínimos locales, el descenso puede quedar atrapado en
cualquiera de ellos.

**Elección de $\eta$ en Rosenbrock ($\eta = 10^{-3}$, empírica y sin garantía global).** La curvatura de Rosenbrock crece
como $1200\,x_i^2$. En 2D, la Hessiana es

$$
\nabla^2 f_{\text{Ros}}(\mathbf{x}) =
\begin{pmatrix} 1200\,x_1^2 - 400\,x_2 + 2 & -400\,x_1 \\ -400\,x_1 & 200 \end{pmatrix}.
$$

Según el Spec (§6.3 y §6.1.1), su mayor valor propio en $[-2.048,\,2.048]^n$ da $L \approx 5\,971$ en 2D y
$L \approx 6\,838$ en 3D, de modo que la garantía global exigiría $\eta \le 1.7\times10^{-4}$ y $\eta \le 1.5\times10^{-4}$.
El paso elegido, $\eta = 10^{-3}$, supera esas cotas. **No hay garantía global de descenso.** En el mínimo
$\mathbf{x}^* = (1, 1)$, la Hessiana vale $\begin{pmatrix} 802 & -400 \\ -400 & 200 \end{pmatrix}$, con
$\lambda_{\max} \approx 1\,001.6$. Por eso $\eta < 2/\lambda_{\max} \approx 2\times10^{-3}$ solo asegura estabilidad
**local**, cerca de $\mathbf{x}^*$. Según el experimento registrado en el Spec, $\eta = 10^{-3}$ converge mejor que
$\eta = 1/L$: la trayectoria entra rápido al valle, donde la curvatura es menor, y desde ahí avanza despacio por el mal
condicionamiento. Por eso se usa $\eta = 10^{-3}$, declarando que no tiene garantía global, y $\eta = 1/L$ se reporta como
análisis de sensibilidad (Spec §6.3).

### Descenso por gradiente con búsqueda de Armijo

Esta variante usa el mismo bucle que la de paso fijo, con el mismo punto inicial, el mismo criterio
$\lVert\nabla f\rVert < 10^{-8}$ y el mismo corte por presupuesto. Lo que cambia es la regla del paso. Dados el punto actual
$\mathbf{x}$, su gradiente $\mathbf{g} = \nabla f(\mathbf{x})$ y el valor $f(\mathbf{x})$, la búsqueda con retroceso
[@armijo1966] hace lo siguiente:

1. Si todavía no se conoce $f(\mathbf{x}_0)$, la evalúa. Esto ocurre una sola vez por corrida.
2. Toma $\eta \leftarrow \eta_0$.
3. Construye el ensayo proyectado $\mathbf{x}_\eta = \Pi(\mathbf{x} - \eta\,\mathbf{g})$ y evalúa $f(\mathbf{x}_\eta)$.
4. Si $f(\mathbf{x}_\eta) \le f(\mathbf{x}) - c\,\langle \mathbf{g},\, \mathbf{x} - \mathbf{x}_\eta \rangle$, acepta el
   ensayo. Si no, hace $\eta \leftarrow \beta\,\eta$ y vuelve al paso 3.
5. Pasa al punto aceptado, $\mathbf{x} \leftarrow \mathbf{x}_\eta$, y guarda $f(\mathbf{x}_\eta)$ como el $f(\mathbf{x})$ de
   la siguiente iteración.

**Por qué la condición usa el punto proyectado.** Sin recorte, $\mathbf{x} - \mathbf{x}_\eta = \eta\,\mathbf{g}$ y el término
$c\,\langle \mathbf{g},\, \mathbf{x} - \mathbf{x}_\eta \rangle$ coincide con el $c\,\eta\,\lVert\mathbf{g}\rVert^2$ de la
forma clásica (Spec §6.3). La diferencia aparece en el borde. Si $\mathbf{x}$ está pegado al borde y el gradiente apunta
hacia afuera, el ensayo proyectado no se mueve: $\mathbf{x}_\eta = \mathbf{x}$ para todo $\eta$. Con la forma clásica,
se exigiría $f(\mathbf{x}) \le f(\mathbf{x}) - c\,\eta\,\lVert\mathbf{g}\rVert^2$. En aritmética exacta esto no se cumple
para ningún $\eta > 0$. En coma flotante solo se cumple cuando $c\,\eta\,\lVert\mathbf{g}\rVert^2$ queda por debajo de la
resolución de $f(\mathbf{x})$, lo que exige decenas de retrocesos, y eso se repetiría en cada iteración sin mover el punto.
Con la forma proyectada, el término de la derecha mide el descenso que la proyección realmente permite, que en ese caso es cero, y el ensayo se acepta.

**Conteo.** Cada ensayo $f(\mathbf{x}_\eta)$ cuesta una evaluación de $f$, como exige el Spec (§6.2) para las búsquedas
lineales. El valor $f(\mathbf{x})$ no se vuelve a evaluar, porque es el del ensayo aceptado en la iteración anterior.
$f(\mathbf{x}_0)$ se paga una sola vez y de forma perezosa: solo cuando se necesita por primera vez. Si el primer
gradiente ya cumple la tolerancia, $n_f = 0$. En cualquier otro caso, $n_f$ es 1 más el número total de ensayos. Cada
gradiente cuesta $k$, como en la variante de paso fijo. No hay un tope en el número de retrocesos: el presupuesto termina
cualquier búsqueda. Como los ensayos rechazados también se registran, el mejor punto visto que se devuelve puede ser uno
de ellos.

**Límite numérico en Rastrigin.** La mejora que exige la condición es $c\,\langle \mathbf{g},\, \mathbf{x} - \mathbf{x}_\eta \rangle$,
que sin recorte vale $c\,\eta\,\lVert\nabla f\rVert^2$ y, como $\eta \le \eta_0 = 1$ y $c = 10^{-4}$, nunca supera
$10^{-4}\lVert\nabla f\rVert^2$. Por otro lado, $f$ se calcula como $10n + \sum_i [x_i^2 - 10\cos(2\pi x_i)]$, una suma de
términos de magnitud cercana a 10. Su error de redondeo absoluto es, por tanto, del orden de $10n\,\varepsilon$, con
$\varepsilon \approx 2.2\times10^{-16}$ la precisión de la doble precisión, aunque $f$ esté cerca de 0. Cuando el término
$c\,\langle \mathbf{g},\, \mathbf{x} - \mathbf{x}_\eta \rangle$ se vuelve despreciable frente a esa resolución, la prueba
queda en la práctica como $f(\mathbf{x}_\eta) \le f(\mathbf{x})$. Esa comparación todavía se decide bien, porque la
diferencia entre los dos valores sigue siendo mayor que el error de redondeo.

El redondeo pasa a decidir más tarde. Cerca de un mínimo, con curvatura $\lambda \approx 2 + 40\pi^2$ en cada coordenada,
el mejor paso reduce $f$ en aproximadamente

$$
f(\mathbf{x}) - f(\mathbf{x}_\eta) \approx \frac{\lVert\nabla f\rVert^2}{2\lambda}.
$$

Esa diferencia cae por debajo de la resolución $10n\,\varepsilon$ cuando
$\lVert\nabla f\rVert \lesssim \sqrt{2\lambda \cdot 10n\,\varepsilon}$, es decir, para $\lVert\nabla f\rVert$ de unos $10^{-6}$.
Desde ahí la búsqueda acepta o rechaza ensayos por ruido numérico. Si rechaza todos los ensayos, sigue multiplicando
$\eta$ por $\beta$ hasta que $\eta\,\nabla f$ queda por debajo de la resolución de $\mathbf{x}$. Entonces
$\mathbf{x}_\eta = \mathbf{x}$, la condición queda $0 \le 0$ y el ensayo se acepta, pero la iteración siguiente repite la
misma búsqueda en el mismo punto. Por eso $\lVert\nabla f\rVert < 10^{-8}$ solo se alcanza a veces, y en Rastrigin muchas
corridas con Armijo terminan por presupuesto. Los conteos $n_f$ y $n_{\text{grad}}$ dependen del redondeo de cos/sin en
cada plataforma. Por eso las pruebas de `tests/test_gd.py` no los fijan para Armijo en Rastrigin, aunque sí lo hacen en
Rosenbrock.

### Algoritmo evolutivo

El algoritmo evolutivo sigue el esquema visto en clase: no hay selección de padres por aptitud, y cada generación se arma
con una élite, un grupo de mutantes y un grupo de hijos de cruce. Sus parámetros están en la [[tab:parametros-ea]]. En lo
que sigue, $N$ es el tamaño de la población, $d$ la dimensión y $[l_j, u_j]$ el intervalo del dominio en la coordenada $j$.

**Tamaños de los grupos.** Se calculan una vez, a partir de $N$ y de las fracciones $f_e$, $f_m$ y $f_c$:

$$
n_e = \operatorname{round}(N f_e), \qquad n_m = \lfloor N f_m \rfloor, \qquad
n_c = \max\!\Big(\operatorname{par}(\lfloor N f_c \rfloor),\ \operatorname{par}(N - n_e - n_m)\Big),
\qquad \operatorname{par}(n) = n + (n \bmod 2).
$$

`round` es el de Python, que lleva las mitades al entero par. El número de cruzantes $n_c$ es siempre par, porque se
cruzan parejas. El segundo término del máximo sube $n_c$ cuando los tres grupos no alcanzan a sumar $N$. Con los valores
de la tabla, $n_e = \operatorname{round}(7.5) = 8$, $n_m = \lfloor 5 \rfloor = 5$ y
$n_c = \max(\operatorname{par}(37),\ \operatorname{par}(37)) = 38$. Como $8 + 5 + 38 = 51 > 50$, sobra un hijo.

El algoritmo hace lo siguiente:

1. Sortea la población inicial, $N$ puntos uniformes en el dominio, con una sola llamada `rng.uniform`, y los evalúa.
2. **Élite.** Ordena la población actual por su valor de $f$ (orden estable: en un empate va primero el índice menor) y
   copia sin cambios los $n_e$ mejores.
3. **Mutación.** Elige $n_m$ individuos de toda la población, sin repetir y sin mirar su aptitud. En la copia de cada uno
   cambia un solo gen $g$, elegido al azar:
   $x'_{g} = \operatorname{clip}\big(x_{g} + \sigma_{g}\,z,\ l_{g},\ u_{g}\big)$, con $z \sim \mathcal{N}(0, 1)$ y
   $\sigma_j$ la desviación estándar poblacional (divisor $N$) del gen $j$ en la población actual.
4. **Cruce.** Elige $n_c$ individuos de toda la población, otra vez sin repetir y sin mirar su aptitud. Con $m = n_c/2$,
   la pareja $k$ la forman el cruzante $k$ ($\mathbf{p}$) y el cruzante $k + m$ ($\mathbf{q}$). Cada pareja sortea un
   corte $c \in \{1, \dots, d-1\}$ y produce dos hijos: $\mathbf{h}^{(1)} = (p_1, \dots, p_c,\ q_{c+1}, \dots, q_d)$ y
   $\mathbf{h}^{(2)} = (q_1, \dots, q_c,\ p_{c+1}, \dots, p_d)$.
5. **Ensamble.** Apila élite, mutantes e hijos, en ese orden, y conserva las primeras $N$ filas. Lo que sobra son los
   últimos hijos: la élite y los mutantes nunca se recortan.
6. Evalúa las filas que no son élite y vuelve al paso 2 con la nueva población.

Los pasos 3 y 4 parten los dos de la población del inicio de la generación: los hijos no se mutan y los mutantes no entran
al cruce en esa misma generación. El generador aleatorio se consume en un orden fijo: primero la mutación (individuos,
genes, ruido) y después el cruce (cruzantes, cortes).

**Parada.** Con `ea.generaciones: null`, la corrida solo termina cuando el contador rechaza una evaluación por
presupuesto. La clave admite un entero, pero un número fijo de generaciones solo puede acortar la corrida: el método se
detendría sin haber gastado las $10\,000 \cdot n$ evaluaciones de que disponen los demás, y la comparación dejaría de
hacerse a igual presupuesto (Spec §6.2).

**Conteo.** La población inicial cuesta $N$ evaluaciones. En las generaciones siguientes la élite ocupa las primeras
$n_e$ filas y conserva el valor de $f$ que ya tenía (`reevaluar_elite: false`), así que solo se evalúan las otras
$N - n_e$ filas. Con $T$ generaciones completas,

$$
n_f = N + T\,(N - n_e) + r, \qquad n_{\text{grad}} = 0,
$$

donde $r$, con $0 \le r < N - n_e$, son las evaluaciones de la generación que el presupuesto corta. Con los valores de la
tabla, $n_f = 50 + 42\,T + r$. En 2D, $(20\,000 - 50)/42 = 475$ exacto: caben 475 generaciones y $r = 0$. En 3D,
$50 + 42 \cdot 713 = 29\,996$: caben 713 generaciones y $r = 4$. Con `reevaluar_elite: true` cada generación costaría $N$.
La generación cortada se descarta y no registra cuadro para la animación, pero sus $r$ evaluaciones sí se hicieron y se
contaron. La corrida devuelve el mejor punto visto por el contador, que por eso puede ser un individuo de esa generación
incompleta.

::: tabla parametros-ea
Título: Parámetros del algoritmo evolutivo
Fuente: Elaboración propia a partir de configs/part1/base.yaml
| Parámetro | Clave en `base.yaml` | Valor |
|---|---|---|
| Esquema | `ea.esquema` | `clase` |
| Tamaño de la población $N$ | `ea.N` | `50` |
| Fracción de élite $f_e$ | `ea.frac_e` | `0.15` |
| Fracción de mutantes $f_m$ | `ea.frac_m` | `0.10` |
| Fracción que se cruza $f_c$ | `ea.frac_c` | `0.75` |
| Volver a evaluar la élite | `ea.reevaluar_elite` | `false` |
| Número de generaciones | `ea.generaciones` | `null` (parar solo por presupuesto) |
:::

**Qué no garantiza.** Tres rasgos del esquema limitan la búsqueda, y ninguno asegura llegar al mínimo global:

- **En 2D el cruce solo intercambia coordenadas.** Con $d = 2$ el único corte posible es $c = 1$, y los hijos de
  $(p_1, p_2)$ y $(q_1, q_2)$ son $(p_1, q_2)$ y $(q_1, p_2)$: las otras dos esquinas del rectángulo que definen los
  padres. El cruce no crea ningún valor de coordenada que no estuviera ya en la población, en ninguna dimensión. Los
  valores nuevos solo los aporta la mutación.
- **La única presión de selección es la élite.** Mutantes y cruzantes se eligen sin mirar la aptitud, de modo que un
  individuo malo tiene la misma probabilidad de reproducirse que uno bueno. Lo único que el algoritmo conserva a propósito
  son los $n_e$ mejores.
- **Colapso prematuro de la población.** El tamaño del salto de la mutación es $\sigma_j$, la dispersión de la propia
  población. Si la población se concentra, $\sigma_j \to 0$ y la mutación se apaga. En el límite, cuando todos los
  individuos comparten el valor de una coordenada, ni la mutación ($\sigma_j = 0$) ni el cruce (que solo intercambia
  valores existentes) pueden cambiarla, y la búsqueda se detiene en esa coordenada aunque no se haya llegado a un óptimo.
  Nada en el esquema obliga a que la población se concentre en un mínimo.

### Optimización por enjambre de partículas

Se usa la versión de mejor global con peso de inercia [@kennedy1995; @shi1998]: todas las partículas comparten la misma
$\mathbf{g}$. Los parámetros están en la [[tab:parametros-pso]]. Con $N$ partículas, el algoritmo hace lo siguiente:

1. Sortea las $N$ posiciones iniciales, uniformes en el dominio, con una sola llamada `rng.uniform`. Las velocidades
   iniciales son cero.
2. Evalúa el enjambre, toma $\mathbf{p}_i = \mathbf{x}_i$ como memoria inicial de cada partícula y elige $\mathbf{g}$
   como la $\mathbf{p}_i$ de menor $f$ (en un empate, la de índice menor).
3. En cada iteración sortea dos matrices de números uniformes en $[0, 1)$, $R_1$ y después $R_2$, con un número por
   partícula y por componente.
4. Calcula la velocidad, con $\odot$ el producto componente a componente:
   $\mathbf{v}_i \leftarrow w\,\mathbf{v}_i + c_1\,R_{1,i} \odot (\mathbf{p}_i - \mathbf{x}_i) + c_2\,R_{2,i} \odot (\mathbf{g} - \mathbf{x}_i)$.
5. Recorta cada componente de la velocidad a $[-v_{\max,j},\, v_{\max,j}]$, con $v_{\max,j} = \gamma\,(u_j - l_j)$ y
   $\gamma$ el parámetro `vmax_frac`. El límite se calcula una vez, por coordenada, a partir del ancho del dominio.
6. Mueve: $\mathbf{x}_i \leftarrow \mathbf{x}_i + \mathbf{v}_i$. Si una componente sale de $[l_j, u_j]$, la recorta a la
   frontera y pone en 0 la velocidad de esa componente, y solo de esa.
7. Evalúa las $N$ posiciones nuevas. Actualiza $\mathbf{p}_i \leftarrow \mathbf{x}_i$ solo si
   $f(\mathbf{x}_i) < f(\mathbf{p}_i)$ (mejora estricta), vuelve a elegir $\mathbf{g}$ entre las $\mathbf{p}_i$ y regresa
   al paso 3.

Ninguna posición evaluada queda fuera del dominio. Con `vmax_frac: null` no habría límite de velocidad y el paso 5 no
haría nada. Un valor $w \ge 1$ no se rechaza, pero produce un aviso, porque la inercia dejaría de amortiguar la velocidad.

**Constantes.** Los valores $w = 0.7298$ y $c_1 = c_2 = 1.49618$ no se ajustaron para este trabajo: son las cifras
redondeadas del factor de constricción con $\varphi = 4.1$, es decir, $\chi \approx 0.7298$, $w = \chi$ y
$c_1 = c_2 = \chi\,\varphi/2 \approx 1.49618$ (derivación en la fundamentación).
<!-- TODO(cita): verificar Clerc & Kennedy (2002) antes de citarlo -->

**Parada.** Con `pso.iteraciones: null`, la corrida solo termina por presupuesto. Igual que en el algoritmo evolutivo, un
número fijo de iteraciones solo podría acortarla y dejaría al método con menos evaluaciones que a los demás (el presupuesto
es igual para todos los métodos, Spec §6.2).

**Conteo.** El enjambre inicial cuesta $N$ evaluaciones y cada iteración otras $N$, una por partícula. Con $T$
iteraciones completas,

$$
n_f = N\,(T + 1) + r, \qquad n_{\text{grad}} = 0,
$$

donde $r$, con $0 \le r < N$, son las evaluaciones de la iteración que el presupuesto corta. Con $N = 30$, en 2D
$30 \cdot 666 = 19\,980$: caben 665 iteraciones y $r = 20$. En 3D, $30 \cdot 1\,000 = 30\,000$: caben 999 iteraciones y
$r = 0$. La iteración cortada se descarta: no actualiza las memorias ni $\mathbf{g}$ y no registra cuadro para la
animación. Sus $r$ evaluaciones sí se contaron, y la corrida devuelve el mejor punto visto por el contador, que puede ser
una de esas $r$ posiciones.

::: tabla parametros-pso
Título: Parámetros de la optimización por enjambre de partículas
Fuente: Elaboración propia a partir de configs/part1/base.yaml
| Parámetro | Clave en `base.yaml` | Valor |
|---|---|---|
| Tamaño del enjambre $N$ | `pso.N` | `30` |
| Peso de inercia $w$ | `pso.w` | `0.7298` |
| Coeficiente cognitivo $c_1$ | `pso.c1` | `1.49618` |
| Coeficiente social $c_2$ | `pso.c2` | `1.49618` |
| Fracción del ancho del dominio para $v_{\max}$ | `pso.vmax_frac` | `0.2` |
| Número de iteraciones | `pso.iteraciones` | `null` (parar solo por presupuesto) |
:::

**Qué no garantiza.** El método no garantiza el mínimo global. La ecuación de la velocidad no tiene ningún término que
mueva a una partícula con $\mathbf{v}_i = \mathbf{0}$ y $\mathbf{x}_i = \mathbf{p}_i = \mathbf{g}$. Un enjambre que se
concentra en un mínimo local y pierde su velocidad no tiene, por tanto, nada que lo saque de ahí.

El arranque en reposo tiene además una consecuencia directa. En la primera iteración $\mathbf{v}_i = \mathbf{0}$ y
$\mathbf{p}_i = \mathbf{x}_i$, así que la inercia y el término cognitivo valen cero y el primer movimiento es puramente
social: la velocidad de cada partícula es $c_2\,R_{2,i} \odot (\mathbf{g} - \mathbf{x}_i)$, sujeta después al límite
$v_{\max}$ (paso 5) y a la frontera (paso 6). Para la partícula que es $\mathbf{g}$ ese término también vale cero. El líder no se mueve, ni en la primera iteración ni en las siguientes, hasta
que $\mathbf{g}$ cambia porque otra partícula la releva.

### Evolución diferencial

Se usa la variante DE/rand/1/bin [@storn1997], con los parámetros de la [[tab:parametros-de]]. Con $NP$ individuos, el
algoritmo hace lo siguiente:

1. Sortea la población inicial, $NP$ puntos uniformes en el dominio, con una sola llamada `rng.uniform`, y los evalúa.
2. **Padres.** Para cada individuo $i$ elige tres índices $r_1$, $r_2$ y $r_3$, distintos entre sí y distintos de $i$.
   Por eso se exige $NP \ge 4$.
3. **Mutación.** Construye el mutante $\mathbf{v}_i = \mathbf{x}_{r_1} + F\,(\mathbf{x}_{r_2} - \mathbf{x}_{r_3})$.
4. **Reinicio.** Cada componente del mutante con $v_{ij} < l_j$ o $v_{ij} > u_j$ se reemplaza por un sorteo
   $U(l_j, u_j)$. Un valor igual al límite se conserva. La componente no se recorta a la frontera.
5. **Cruce binomial.** Con $U_{ij} \sim U(0,1)$ y una coordenada $j_{\text{rand},i}$ sorteada por individuo, el hijo
   toma $u_{ij} = v_{ij}$ si $U_{ij} \le CR$ o $j = j_{\text{rand},i}$, y $u_{ij} = x_{ij}$ en otro caso.
6. **Evaluación.** Evalúa los $NP$ hijos.
7. **Selección.** El hijo reemplaza a su padre si $f(\mathbf{u}_i) \le f(\mathbf{x}_i)$: gana el empate. Cada hijo
   compite solo con el individuo de su mismo puesto. Después vuelve al paso 2.

El esquema es síncrono: los pasos 2 a 5 usan, para todos los individuos, la población que había al inicio de la
generación, y la población solo cambia en el paso 7. El reinicio se aplica al mutante y antes del cruce, de modo que todos
los hijos evaluados están dentro del dominio. La coordenada $j_{\text{rand},i}$ asegura que cada hijo tome al menos una
componente del mutante. El consumo del generador aleatorio es el mismo en todas las generaciones (padres, reinicio, cruce
y $j_{\text{rand}}$, en ese orden) y no depende de los datos: el sorteo del reinicio se hace siempre completo, aunque
ninguna componente haya salido.

**Parada.** Con `de.generaciones: null`, la corrida solo termina por presupuesto. Como en los otros dos métodos, un número
fijo de generaciones solo podría acortarla y rompería la comparación a igual presupuesto (Spec §6.2).

**Conteo.** La población inicial cuesta $NP$ evaluaciones y cada generación otras $NP$, una por hijo. Con $T$
generaciones completas,

$$
n_f = NP\,(T + 1) + r, \qquad n_{\text{grad}} = 0,
$$

donde $r$, con $0 \le r < NP$, son las evaluaciones de la generación que el presupuesto corta. Con $NP = 30$ las cuentas
son las mismas que en el enjambre: 665 generaciones y $r = 20$ en 2D, 999 generaciones y $r = 0$ en 3D. La generación
cortada se descarta: no hay selección, la población no cambia y no se registra cuadro para la animación. Sus $r$ hijos sí
se evaluaron y se contaron, y la corrida devuelve el mejor punto visto por el contador. Por eso el punto devuelto puede
ser un hijo de esa generación incompleta que nunca llegó a entrar en la población.

::: tabla parametros-de
Título: Parámetros de la evolución diferencial
Fuente: Elaboración propia a partir de configs/part1/base.yaml
| Parámetro | Clave en `base.yaml` | Valor |
|---|---|---|
| Tamaño de la población $NP$ | `de.NP` | `30` |
| Factor de mutación $F$ | `de.F` | `0.7` |
| Probabilidad de cruce $CR$ | `de.CR` | `0.9` |
| Número de generaciones | `de.generaciones` | `null` (parar solo por presupuesto) |
:::

**Qué no garantiza.** El método no garantiza el mínimo global. El tamaño del paso lo da la diferencia
$\mathbf{x}_{r_2} - \mathbf{x}_{r_3}$, que sale de la propia población: es grande mientras los individuos están dispersos
y solo se encoge si la población se concentra. Esa concentración puede ocurrir en un mínimo local. Si la población
colapsa ahí, las diferencias se anulan, cada mutante coincide con $\mathbf{x}_{r_1}$ y la búsqueda se estanca. La
selección tampoco protege contra eso: conserva el mejor valor de $f$ de la población, que nunca empeora, pero no la
diversidad.

### Ajuste de hiperparámetros

*Pendiente: se redacta cuando se cierre el método de búsqueda de hiperparámetros (método, rangos, presupuesto, semillas y criterio de selección).*
