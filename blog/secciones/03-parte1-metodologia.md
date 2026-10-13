<!--
SECCIÓN: Parte 1 — metodología · RESPONSABLE: equipo Parte 1 · ESTADO: pendiente.
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

*Pendiente (T1.4, T1.5 y T1.6).*

### Optimización por enjambre de partículas

*Pendiente (T1.4, T1.5 y T1.6).*

### Evolución diferencial

*Pendiente (T1.4, T1.5 y T1.6).*
