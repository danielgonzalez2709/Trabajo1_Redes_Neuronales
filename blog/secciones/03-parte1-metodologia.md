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
equivalencias (Spec §6.2). En ese análisis solo los dos descensos por gradiente se vuelven a ejecutar con $k = 1$, con
las mismas semillas y el mismo presupuesto, y sus corridas se guardan aparte. El algoritmo evolutivo (EA), la
optimización por enjambre de partículas (PSO, Particle Swarm Optimization) y la evolución diferencial (DE, Differential
Evolution) no usan gradientes: su $n_{\text{grad}}$ es 0, su costo $n_f + k\,n_{\text{grad}} = n_f$ no depende de $k$ y
en la tabla de sensibilidad se reutilizan sus filas de la tabla principal, que conservan el valor $k = 2n$ con el que
se ejecutaron.

Conviene distinguir dos lecturas del costo con $k = 1$. El **recosteo** toma las mismas corridas, ejecutadas con una
$k$ dada, y vuelve a sumar su costo como $n_f + n_{\text{grad}}$: la trayectoria no cambia, solo el precio de cada
gradiente. La **re-ejecución** corre de nuevo el descenso con $k = 1$: como cada gradiente cuesta menos, el mismo
presupuesto alcanza para más gradientes, la trayectoria se alarga y $f_{\text{final}}$ también puede cambiar. La tabla
de sensibilidad usa la re-ejecución; el recosteo aparece como un campo más de cada fila.

Cada una de las 20 configuraciones (2 funciones × 2 dimensiones × 5 métodos: descenso por gradiente (GD) de paso fijo,
GD con Armijo, EA, PSO y DE) se ejecuta 30 veces de forma independiente. La corrida `run_id` usa el generador
`np.random.default_rng(base_seed + run_id)` con `base_seed = 0`, es decir, las semillas 0 a 29, las mismas para todos
los métodos. Una corrida tiene éxito si $f - f^* \le 10^{-4}$, con $f^*$ el valor mínimo de la función; es el umbral
principal, y también se reportan los umbrales $10^{-2}$ y $10^{-6}$. Por cada configuración se reportan:

- media, desviación estándar, mediana, mejor y peor valor de $f_{\text{final}}$;
- $n_f$ y $n_{\text{grad}}$ medios, por separado;
- tres medias de evaluaciones equivalentes: `eval_equiv_medio`, con la $k$ con la que se ejecutó la corrida;
  `eval_equiv_medio_k2n`, las mismas corridas recosteadas como $n_f + 2n\,n_{\text{grad}}$; y `eval_equiv_medio_k1`,
  recosteadas como $n_f + n_{\text{grad}}$;
- tasa de éxito;
- evaluaciones hasta el éxito (media sobre las corridas exitosas), medidas con la $k$ de la corrida y sin recostear.

Los valores por defecto de los parámetros de los dos descensos por gradiente están en la [[tab:parametros-gd]]. Los
valores que eligió la optimización de hiperparámetros (HPO, Hyperparameter Optimization) se describen en la subsección
«Optimización de hiperparámetros», al final de esta sección.

::: tabla parametros-gd
Título: Valores por defecto de los parámetros del descenso por gradiente (paso fijo y Armijo)
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
$L \approx 6\,838$ en 3D, de modo que la garantía global exigiría $\eta \le 1/L$, es decir,
$\eta \le 1.67\times10^{-4}$ en 2D y $\eta \le 1.46\times10^{-4}$ en 3D. El paso elegido, $\eta = 10^{-3}$, supera esas
cotas. **No hay garantía global de descenso.** En el mínimo
$\mathbf{x}^* = (1, 1)$, la Hessiana vale $\begin{pmatrix} 802 & -400 \\ -400 & 200 \end{pmatrix}$, con
$\lambda_{\max} \approx 1\,001.6$. Por eso $\eta < 2/\lambda_{\max} \approx 2\times10^{-3}$ solo asegura estabilidad
**local**, cerca de $\mathbf{x}^*$.

Para medir qué se pierde con el paso pequeño, el GD de paso fijo en Rosenbrock se ejecutó también con
$\eta = 1.5\times10^{-4}$, con las mismas 30 semillas, el mismo presupuesto y $k = 2n$ ([[tab:sensibilidad-eta]]). Ese
valor es la cota redondeada que la sección 6.3 de la Spec da para 3D (para 2D da $1.7\times10^{-4}$), y se usó el mismo
en las dos dimensiones. Cumple $\eta \le 1/L$ en 2D, pero en 3D supera a $1/L$ en un 2.6 %: el redondeo a dos cifras
lo ocultaba. La diferencia es pequeña y no cambia la conclusión,
pero en 3D el experimento no corresponde estrictamente al paso con garantía. Con $\eta = 1.5\times10^{-4}$, la mediana
de $f_{\text{final}}$ es 0.147 en 2D y 0.219 en 3D, solo el 6.7 % de las corridas llega a $10^{-2}$ en cada dimensión y
ninguna llega a $10^{-4}$. Con $\eta = 10^{-3}$, la mediana es $1.905\times10^{-3}$ en 2D y $1.285\times10^{-3}$ en 3D,
y llegan a $10^{-2}$ el 100 % y el 96.7 % de las corridas. Con el paso pequeño, las corridas consumen los 5 000
gradientes del presupuesto sin acercarse tanto al mínimo. La explicación esperada es el mal condicionamiento del valle:
con un paso grande la trayectoria entra rápido al valle, donde la curvatura es menor, mientras que con $\eta \le 1/L$
cada paso a lo largo del fondo del valle es muy corto. El experimento no prueba esa causa; solo muestra que con 5 000
gradientes el paso $\eta = 1.5\times10^{-4}$ no llega. Por eso se usa $\eta = 10^{-3}$, declarando que no tiene
garantía global.

::: tabla sensibilidad-eta
Título: GD de paso fijo en Rosenbrock con $\eta = 10^{-3}$ y con $\eta = 1.5\times10^{-4}$ (30 corridas, $k = 2n$)
Fuente: Elaboración propia a partir de results/data/part1/summary.json y results/data/part1_eta_1l/summary.json
| Dimensión | $\eta$ | Media de $f_{\text{final}}$ | Mediana | Éxito a $10^{-2}$ | Éxito a $10^{-4}$ |
|---|---|---|---|---|---|
| 2D | `1e-3` | 1.962e-03 | 1.905e-03 | 100.0 % | 3.3 % |
| 2D | `1.5e-4` | 3.581e-01 | 1.471e-01 | 6.7 % | 0.0 % |
| 3D | `1e-3` | 1.663e-03 | 1.285e-03 | 96.7 % | 3.3 % |
| 3D | `1.5e-4` | 3.910e-01 | 2.189e-01 | 6.7 % | 0.0 % |
:::

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

### Optimización de hiperparámetros

Cada método tiene hiperparámetros con valores por defecto tomados de la literatura o del Spec (secciones 6.3 y 6.4):
el paso $\eta$ del GD de paso fijo, los parámetros $\eta_0$, $\beta$ y $c$ de la búsqueda de Armijo, el tamaño de
población y las fracciones de los grupos del EA, la inercia y los coeficientes del PSO, y $NP$, $F$ y $CR$ del DE. La
HPO prueba si afinarlos mejora los resultados. Es un lazo externo de búsqueda aleatoria: se sortean combinaciones de
valores, cada combinación (un *ensayo*) se ejecuta con el método y se conserva la mejor (sección 6.9 del Spec).
<!-- TODO(cita): la búsqueda aleatoria es una alternativa razonable a la búsqueda en rejilla para ajustar
hiperparámetros (candidato sin verificar para T4.7: Bergstra y Bengio 2012). -->
<!-- TODO(cita): el ajuste de parámetros como práctica habitual en algoritmos evolutivos
(candidato sin verificar para T4.7: Eiben y Smit 2011). -->
El experimento de esta sección se conserva así en dos versiones, por defecto y afinada, sobre las mismas semillas 0 a
29, con el mismo presupuesto y la misma $k$; la tabla `comparacion.csv` las pone lado a lado. Los resultados por defecto
nunca se reescriben: el experimento afinado se guarda en otra carpeta, `results/data/part1_tuned/` (regla R8).

**Protocolo.** Las reglas R1 a R5 del Spec fijan cómo se reparte el esfuerzo:

- *Igual esfuerzo (R1).* Cada unidad de búsqueda recibe 30 ensayos, y cada ensayo se ejecuta con 5 semillas, el
  presupuesto de $10\,000 \cdot n$ evaluaciones equivalentes y $k = 2n$. Por método, eso da 600 corridas de ajuste
  (30 ensayos × 5 semillas × 4 celdas); el GD de paso fijo las reparte en dos unidades de 300.
- *Semillas disjuntas (R2).* Las semillas de ajuste son 1000 a 1004 (`hpo.base_seed = 1000`) y no se solapan con las de
  reporte, 0 a 29; si se solaparan, la configuración sería inválida.
- *Ensayo 0 = valores por defecto (R3).* El primer ensayo de cada unidad es siempre la configuración por defecto, de
  modo que la búsqueda compite contra ella con las mismas semillas.
- *Muestreo aleatorio (R4).* Cada valor se sortea según su tipo: `uniforme`, `log` (uniforme en el logaritmo, para
  parámetros que varían en órdenes de magnitud) o `entero` (extremos incluidos). Una combinación inválida se vuelve a
  sortear y no cuenta como ensayo.
- *Unidades (R5).* Un método comparte un solo conjunto de hiperparámetros para las dos funciones y las dos dimensiones.
  La excepción es $\eta$ del paso fijo, que se afina por función (`gd.eta.{func}`). Hay así 6 unidades:
  gdfijo/rosenbrock, gdfijo/rastrigin, gdarmijo, ea, pso y de, con 3 000 corridas de ajuste en total.

Los espacios de búsqueda (regla R7) están en la [[tab:espacios-hpo]]. No se afinan el número de generaciones o
iteraciones, el esquema del EA, la reevaluación de la élite ni la tolerancia del gradiente. En el EA, $f_c$ es una
fracción mínima: el número de cruzantes es el par hacia arriba de $\lfloor N f_c \rfloor$, y sube si élite, mutantes y
cruzantes no llegan a $N$ (relleno), de modo que el relleno puede aumentar la fracción que se cruza.

::: tabla espacios-hpo
Título: Espacios de búsqueda de la HPO (intervalos cerrados) y valores por defecto
Fuente: Elaboración propia a partir de configs/part1/base.yaml y de docstrings y comentarios de src/part1/*.py
| Método | Hiperparámetro | Clave | Tipo | Intervalo | Por defecto | Significado |
|---|---|---|---|---|---|---|
| gdfijo | $\eta$ | `gd.eta.{func}` | log | [1e-05, 0.01] | rosenbrock: 0.001, rastrigin: 0.002 | paso fijo |
| gdarmijo | $\eta_0$ | `gd.armijo.eta0` | log | [0.1, 10.0] | 1.0 | paso inicial de cada búsqueda |
| gdarmijo | $\beta$ | `gd.armijo.beta` | uniforme | [0.1, 0.9] | 0.5 | retroceso $\eta \leftarrow \beta\eta$ |
| gdarmijo | $c$ | `gd.armijo.c` | log | [1e-05, 0.1] | 0.0001 | constante de Armijo |
| ea | $N$ | `ea.N` | entero | [20, 200] | 50 | individuos por generación |
| ea | $f_e$ | `ea.frac_e` | uniforme | [0.05, 0.3] | 0.15 | fracción de $N$ copiada como élite |
| ea | $f_m$ | `ea.frac_m` | uniforme | [0.05, 0.4] | 0.1 | fracción de $N$ que se muta |
| ea | $f_c$ | `ea.frac_c` | uniforme | [0.4, 0.9] | 0.75 | fracción mínima de $N$ que se cruza |
| pso | $N$ | `pso.N` | entero | [10, 100] | 30 | número de partículas |
| pso | $w$ | `pso.w` | uniforme | [0.3, 0.95] | 0.7298 | inercia de la velocidad |
| pso | $c_1$ | `pso.c1` | uniforme | [0.5, 2.5] | 1.49618 | atracción al mejor personal |
| pso | $c_2$ | `pso.c2` | uniforme | [0.5, 2.5] | 1.49618 | atracción al mejor global |
| pso | `vmax_frac` | `pso.vmax_frac` | uniforme | [0.05, 0.5] | 0.2 | $v_{\max}$ / ancho del dominio |
| de | $NP$ | `de.NP` | entero | [10, 100] | 30 | número de individuos |
| de | $F$ | `de.F` | uniforme | [0.3, 1.2] | 0.7 | escala de $x_{r_2} - x_{r_3}$ |
| de | $CR$ | `de.CR` | uniforme | [0.1, 1.0] | 0.9 | prob. de que un gen venga del mutante |
:::

**Regla de selección (R6).** Cada ensayo deja, en cada *celda* (un par función-dimensión, como Rosenbrock 2D), un
valor de $f_{\text{best}} - f^*$ por semilla. La regla los resume en cuatro pasos:

1. *Recorte y mediana.* En cada celda se toma la mediana, sobre las semillas, de
   $\max(f_{\text{best}} - f^*,\; 10^{-6})$. El recorte es una decisión de diseño: por debajo de $10^{-6}$, el umbral
   de éxito más estricto, las diferencias entre ensayos se tratan como empate, porque no cambian el éxito y pueden
   deberse al redondeo.
2. *Rangos en lugar de valores.* En cada celda los ensayos se ordenan por esa mediana y reciben un rango (1 = el mejor;
   los empates reciben el rango promedio). Se usan rangos porque Rosenbrock y Rastrigin tienen escalas distintas: un
   promedio de valores de $f$ quedaría dominado por la celda con valores más grandes.
3. *Puntaje.* El puntaje de un ensayo es el promedio de sus rangos sobre las celdas de la unidad. Menor es mejor.
4. *Reemplazo estricto del defecto.* El ensayo 0 solo se reemplaza si el mejor puntaje es **estrictamente menor** que el
   suyo; si empata, gana el defecto. Solo cuando algún ensayo lo supera, y varios empatan en ese mejor puntaje, se
   desempata entre ellos por mayor tasa de éxito a $10^{-6}$, luego por menos evaluaciones medias hasta el éxito a
   $10^{-6}$ (una celda sin éxitos cuenta como $+\infty$) y, por último, por menor índice. Los desempates nunca deciden
   contra el ensayo 0. Las tres claves se comparan con aritmética exacta a partir de conteos enteros.

Un ejemplo real es el PSO. El ensayo 0 (defecto) y el ensayo 3 tienen la misma mediana recortada, $10^{-6}$, en las
cuatro celdas, los mismos rangos (14, 2, 14 y 12 en Rosenbrock 2D, Rosenbrock 3D, Rastrigin 2D y Rastrigin 3D) y,
por tanto, el mismo puntaje, 10.5. El ensayo 3 tuvo un éxito más a
$10^{-6}$ (19 de 20 corridas frente a 18 de 20), pero ese desempate no se mira, porque su puntaje no es estrictamente
menor: gana el defecto.

**Corrección de la regla.** La primera versión de la regla ordenaba los ensayos por la clave completa (puntaje y
desempates) y elegía el primero, de modo que un desempate podía decidir contra el defecto. Con ella, en el PSO y en el
DE un ensayo con el mismo puntaje que el defecto lo reemplazaba: el ensayo 3 del ejemplo en el PSO y el ensayo 6 en el
DE (20 de 20 éxitos a $10^{-6}$ frente a 19 de 20). El problema se notó al comparar contra las semillas de reporte. Con
esos valores, la tasa de éxito a $10^{-4}$ del PSO bajaba del 100 % al 93.3 % en Rastrigin 2D y del 86.7 % al 50.0 % en
Rastrigin 3D, y la del DE, del 100 % al 86.7 % en Rastrigin 2D y del 93.3 % al 80.0 % en Rastrigin 3D. En tasa de
éxito, solo el PSO en Rosenbrock 3D mejoraba, del 40 % al 100 % a $10^{-6}$. La regla se corrigió a la forma descrita
arriba, y la evidencia de la versión anterior se conserva en `results/data/part1_hpo/regla_v1/`. Las otras cuatro
unidades eligen el mismo ensayo con las dos versiones. La corrección tiene una limitación: como el problema se vio en
las semillas de reporte, no es independiente de ellas. Se justifica, sin embargo, con los datos de ajuste solos: el
puntaje principal del ensayo que reemplazaba al defecto era idéntico al suyo (10.5 en el PSO y 14.625 en el DE), así
que el cambio dependía solo de un desempate sobre 5 semillas.
