<!--
SECCIÓN: Parte 1 — resultados · RESPONSABLE: equipo Parte 1 · ESTADO: redactado (13-oct-2026).
Figuras (Spec §6.7): convergencia y cajas (por defecto y por defecto contra afinado), GIF de GD y de PSO, enjambre 3D y
deslizador de η. Las curvas de nivel están en la sección 02.
Tablas: estadísticas por configuración desde results/data/part1/summary.json y results/data/part1_tuned/summary.json
(las cifras se copian de los JSON, no a mano; ver alucinaciones/evidencias/T4.6-parte1_cifras.txt).
-->

## Parte 1: resultados

Se ejecutaron los cinco métodos (descenso por gradiente, GD, de paso fijo, `gdfijo`; GD con búsqueda de Armijo,
`gdarmijo`; algoritmo evolutivo, EA, `ea`; optimización por enjambre de partículas, PSO, `pso`; y evolución
diferencial, DE, `de`) sobre las dos funciones, Rosenbrock y Rastrigin, en 2D y 3D. Son 20 configuraciones, cada una
con 30 corridas independientes (semillas 0 a 29) y un presupuesto de $10\,000 \cdot n$ evaluaciones equivalentes:
20 000 en 2D y 30 000 en 3D. Las tablas principales usan la regla $k = 2n$ (un gradiente cuesta 4 evaluaciones en 2D y
6 en 3D). En las dos funciones el valor mínimo es $f^* = 0$, así que las columnas de $f_{\text{final}}$ son también la
distancia $f - f^*$. Una corrida tiene éxito si $f - f^* \le 10^{-4}$ (umbral principal); también se reportan los
umbrales $10^{-2}$ y $10^{-6}$. Las evaluaciones hasta el éxito son la media sobre las corridas exitosas («—» si no
hay ninguna), así que las de dos métodos con tasas distintas se toman sobre conjuntos distintos de corridas.

### Resultados con la configuración por defecto

La [[tab:resultados-rosenbrock]] y la [[tab:resultados-rastrigin]] reúnen las estadísticas de $f_{\text{final}}$ y el
éxito al umbral principal; la [[tab:exito-umbrales]] da la tasa de éxito en los tres umbrales.

::: tabla resultados-rosenbrock
Título: Rosenbrock con la configuración por defecto: estadísticas de $f_{\text{final}}$ en 30 corridas ($k = 2n$)
Fuente: Elaboración propia a partir de results/data/part1/summary.json
| Dim. | Método | Media | Desv. estándar | Mediana | Mejor | Peor | Éxito a $10^{-4}$ | Evaluaciones hasta el éxito |
|---|---|---|---|---|---|---|---|---|
| 2D | gdfijo | 1.962e-03 | 1.232e-03 | 1.905e-03 | 8.572e-05 | 5.355e-03 | 3.3 % (1/30) | 19220 |
| 2D | gdarmijo | 2.615e-02 | 3.464e-02 | 2.326e-03 | 2.004e-05 | 7.669e-02 | 16.7 % (5/30) | 9976 |
| 2D | ea | 3.049e-02 | 4.071e-02 | 9.329e-03 | 4.221e-07 | 1.379e-01 | 10.0 % (3/30) | 2613 |
| 2D | pso | 1.019e-20 | 5.444e-20 | 3.320e-24 | 3.386e-28 | 2.984e-19 | 100.0 % (30/30) | 1555 |
| 2D | de | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 100.0 % (30/30) | 985 |
| 3D | gdfijo | 1.663e-03 | 2.200e-03 | 1.285e-03 | 5.257e-05 | 1.199e-02 | 3.3 % (1/30) | 25998 |
| 3D | gdarmijo | 2.022e-03 | 1.783e-03 | 1.338e-03 | 2.531e-04 | 6.249e-03 | 0.0 % (0/30) | — |
| 3D | ea | 3.867e-01 | 2.964e-01 | 3.269e-01 | 2.272e-03 | 1.059e+00 | 0.0 % (0/30) | — |
| 3D | pso | 9.317e-06 | 1.392e-05 | 3.846e-06 | 5.765e-08 | 6.832e-05 | 100.0 % (30/30) | 19103 |
| 3D | de | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 100.0 % (30/30) | 2213 |
:::

::: tabla resultados-rastrigin
Título: Rastrigin con la configuración por defecto: estadísticas de $f_{\text{final}}$ en 30 corridas ($k = 2n$)
Fuente: Elaboración propia a partir de results/data/part1/summary.json
| Dim. | Método | Media | Desv. estándar | Mediana | Mejor | Peor | Éxito a $10^{-4}$ | Evaluaciones hasta el éxito |
|---|---|---|---|---|---|---|---|---|
| 2D | gdfijo | 1.678e+01 | 1.064e+01 | 1.642e+01 | 1.990e+00 | 3.383e+01 | 0.0 % (0/30) | — |
| 2D | gdarmijo | 4.875e+00 | 5.526e+00 | 2.985e+00 | 0.000e+00 | 1.990e+01 | 16.7 % (5/30) | 160 |
| 2D | ea | 6.633e-02 | 2.524e-01 | 0.000e+00 | 0.000e+00 | 9.950e-01 | 93.3 % (28/30) | 3256 |
| 2D | pso | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 100.0 % (30/30) | 1664 |
| 2D | de | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | 100.0 % (30/30) | 2175 |
| 3D | gdfijo | 2.550e+01 | 1.190e+01 | 2.438e+01 | 4.975e+00 | 4.975e+01 | 0.0 % (0/30) | — |
| 3D | gdarmijo | 1.373e+01 | 1.137e+01 | 8.955e+00 | 9.950e-01 | 4.079e+01 | 0.0 % (0/30) | — |
| 3D | ea | 6.633e-01 | 7.076e-01 | 9.950e-01 | 0.000e+00 | 1.990e+00 | 46.7 % (14/30) | 3677 |
| 3D | pso | 1.327e-01 | 3.440e-01 | 0.000e+00 | 0.000e+00 | 9.950e-01 | 86.7 % (26/30) | 3332 |
| 3D | de | 6.633e-02 | 2.524e-01 | 0.000e+00 | 0.000e+00 | 9.950e-01 | 93.3 % (28/30) | 4981 |
:::

::: tabla exito-umbrales
Título: Tasa de éxito con la configuración por defecto en los tres umbrales de $f - f^*$ (30 corridas, $k = 2n$)
Fuente: Elaboración propia a partir de results/data/part1/summary.json
| Función | Dim. | Método | Éxito a $10^{-2}$ | Éxito a $10^{-4}$ | Éxito a $10^{-6}$ |
|---|---|---|---|---|---|
| Rosenbrock | 2D | gdfijo | 100.0 % (30/30) | 3.3 % (1/30) | 0.0 % (0/30) |
| Rosenbrock | 2D | gdarmijo | 63.3 % (19/30) | 16.7 % (5/30) | 0.0 % (0/30) |
| Rosenbrock | 2D | ea | 53.3 % (16/30) | 10.0 % (3/30) | 3.3 % (1/30) |
| Rosenbrock | 2D | pso | 100.0 % (30/30) | 100.0 % (30/30) | 100.0 % (30/30) |
| Rosenbrock | 2D | de | 100.0 % (30/30) | 100.0 % (30/30) | 100.0 % (30/30) |
| Rosenbrock | 3D | gdfijo | 96.7 % (29/30) | 3.3 % (1/30) | 0.0 % (0/30) |
| Rosenbrock | 3D | gdarmijo | 100.0 % (30/30) | 0.0 % (0/30) | 0.0 % (0/30) |
| Rosenbrock | 3D | ea | 3.3 % (1/30) | 0.0 % (0/30) | 0.0 % (0/30) |
| Rosenbrock | 3D | pso | 100.0 % (30/30) | 100.0 % (30/30) | 40.0 % (12/30) |
| Rosenbrock | 3D | de | 100.0 % (30/30) | 100.0 % (30/30) | 100.0 % (30/30) |
| Rastrigin | 2D | gdfijo | 0.0 % (0/30) | 0.0 % (0/30) | 0.0 % (0/30) |
| Rastrigin | 2D | gdarmijo | 16.7 % (5/30) | 16.7 % (5/30) | 16.7 % (5/30) |
| Rastrigin | 2D | ea | 93.3 % (28/30) | 93.3 % (28/30) | 93.3 % (28/30) |
| Rastrigin | 2D | pso | 100.0 % (30/30) | 100.0 % (30/30) | 100.0 % (30/30) |
| Rastrigin | 2D | de | 100.0 % (30/30) | 100.0 % (30/30) | 100.0 % (30/30) |
| Rastrigin | 3D | gdfijo | 0.0 % (0/30) | 0.0 % (0/30) | 0.0 % (0/30) |
| Rastrigin | 3D | gdarmijo | 0.0 % (0/30) | 0.0 % (0/30) | 0.0 % (0/30) |
| Rastrigin | 3D | ea | 46.7 % (14/30) | 46.7 % (14/30) | 46.7 % (14/30) |
| Rastrigin | 3D | pso | 86.7 % (26/30) | 86.7 % (26/30) | 86.7 % (26/30) |
| Rastrigin | 3D | de | 93.3 % (28/30) | 93.3 % (28/30) | 93.3 % (28/30) |
:::

**Rosenbrock.** Los dos descensos por gradiente se acercan al mínimo sin alcanzar el umbral principal. El paso fijo
llega a $10^{-2}$ en 30 de 30 corridas en 2D y en 29 de 30 en 3D, pero solo una corrida por dimensión llega a
$10^{-4}$; su mediana es $1.905\times10^{-3}$ en 2D y $1.285\times10^{-3}$ en 3D. El GD con Armijo tiene medianas del
mismo orden ($2.326\times10^{-3}$ y $1.338\times10^{-3}$), con 5 éxitos de 30 en 2D y ninguno en 3D; en 2D es más
disperso que el paso fijo (peor valor $7.669\times10^{-2}$ frente a $5.355\times10^{-3}$) y solo 19 de 30 corridas
bajan de $10^{-2}$. Las 30 corridas de cada GD terminan por presupuesto. El DE termina en $f = 0$ exacto en las 30
corridas de las dos dimensiones, con 985 evaluaciones medias hasta el éxito en 2D y 2213 en 3D. El PSO también tiene
éxito en las 30 corridas de cada dimensión, pero con un costo que cambia mucho con la dimensión: 1555 evaluaciones
medias hasta el éxito en 2D y 19103 en 3D, donde su mediana final es $3.846\times10^{-6}$ y solo 12 de 30 corridas
bajan de $10^{-6}$. El EA es el método con peores resultados en esta función: 3 éxitos de 30 en 2D y ninguno en 3D,
con mediana 0.3269 en 3D, donde una sola corrida baja de $10^{-2}$.

**Rastrigin.** El GD de paso fijo no tiene ningún éxito en ningún umbral: su mediana es 16.42 en 2D y 24.38 en 3D,
y su mejor corrida queda en 1.990 y 4.975. Usa
en promedio 18.4 gradientes en 2D y 18.5 en 3D (73.5 y 111.0 evaluaciones equivalentes) y ninguna de sus corridas
llega al final del presupuesto: se detiene antes por la tolerancia sobre la norma del gradiente. El GD con Armijo
mejora esas cifras (mediana 2.985 en 2D y 8.955 en 3D) y en 2D alcanza $f = 0$ exacto en 5 de 30 corridas, con 160
evaluaciones medias hasta el éxito; en 3D no tiene éxitos. En 2D, el PSO y el DE terminan en $f = 0$ en las 30
corridas, y el EA en 28. En 3D ninguno de los tres llega al 100 %: el DE tiene éxito en 28 corridas, el PSO en 26 y
el EA en 14. En esta función la tasa de éxito es la misma en los tres umbrales para todos los métodos: las corridas
terminan en el mínimo global o en un valor mucho mayor que $10^{-2}$ (el peor valor de EA, PSO y DE en 3D es 1.990,
0.9950 y 0.9950).

La [[fig:convergencia-part1]] muestra la mediana y el rango intercuartílico de $f - f^*$ frente a las evaluaciones
equivalentes, y la [[fig:cajas-part1]] la distribución de $f_{\text{final}} - f^*$ por método; las dos tienen un
selector de función y dimensión. El eje vertical es logarítmico y no puede mostrar el 0: los valores menores que
$10^{-16}$, incluido el 0 exacto, se dibujan en $10^{-16}$. Por eso en Rosenbrock 2D las cajas del PSO y del DE quedan
enteras en ese piso (el peor valor del PSO es $2.984\times10^{-19}$ y el DE da 0 en las 30 corridas); lo mismo ocurre
con el DE en Rosenbrock 3D y con el PSO y el DE en Rastrigin 2D. Una caja en el piso significa «menor que $10^{-16}$»,
no un valor medido de $10^{-16}$.

::: figura convergencia-part1
Título: Convergencia de los métodos con la configuración por defecto: mediana y rango intercuartílico de f − f* frente a las evaluaciones equivalentes
Fuente: Elaboración propia a partir de las corridas de results/data/part1/runs/; en el eje logarítmico los valores menores que 1e-16 (incluido el 0 exacto) se dibujan en 1e-16.
incluir: figures/part1_convergencia.html
:::

::: figura cajas-part1
Título: Distribución de f final − f* por método con la configuración por defecto
Fuente: Elaboración propia a partir de las corridas de results/data/part1/runs/; en el eje logarítmico los valores menores que 1e-16 (incluido el 0 exacto) se dibujan en 1e-16.
incluir: figures/part1_cajas.html
:::

El experimento emite un aviso cuando una configuración tiene 100 % de éxito en los tres umbrales, porque en ese caso
el umbral no distingue entre métodos. Ocurre en cinco configuraciones de la tabla principal: PSO y DE en Rosenbrock
2D, DE en Rosenbrock 3D, y PSO y DE en Rastrigin 2D. Entre esas configuraciones la comparación se apoya en las
evaluaciones hasta el éxito, no en la tasa.

### Cómo se mueven los métodos

Las animaciones de este apartado muestran **una sola corrida** cada una (semilla 0, configuración por defecto, 2D).
Ilustran cómo se mueve cada método, pero no resumen las 30 corridas: las cifras que siguen son de esa corrida y no
sustituyen a las de las tablas.

En Rosenbrock ([[fig:gif-gd-rosenbrock]]) las dos variantes del GD parten del mismo punto,
$\mathbf{x}_0 = (0.5610, -0.9430)$, con $f = 158.3659$. El paso fijo da 5000 iteraciones y termina en
$(0.9567, 0.9150)$ con $f = 1.8811\times10^{-3}$. El GD con Armijo solo alcanza a dar 1416 iteraciones con el mismo
presupuesto, porque además de 1417 gradientes gasta 14332 evaluaciones de $f$ en la búsqueda de paso, y termina en
$(1.0982, 1.2069)$ con $f = 9.7153\times10^{-3}$. Los dos puntos finales están en el valle, a lados distintos del
mínimo $(1, 1)$, y ninguno alcanza el umbral de $10^{-4}$.

::: figura gif-gd-rosenbrock
Título: Trayectorias del descenso por gradiente de paso fijo y con Armijo sobre las curvas de nivel de Rosenbrock 2D
Fuente: Elaboración propia a partir de results/data/part1/gif_trayectorias.json (python run.py figures). Corrida con la semilla 0, configuración por defecto.
![Animación de las iteraciones del descenso por gradiente de paso fijo y con búsqueda de Armijo, desde un mismo punto inicial, sobre las curvas de nivel de la función de Rosenbrock en dos dimensiones](figures/gd_rosenbrock_2d.gif)
:::

En Rastrigin ([[fig:gif-gd-rastrigin]]) las dos variantes parten de $\mathbf{x}_0 = (1.4025, -2.3574)$, con
$f = 41.9520$, y terminan en mínimos locales distintos. El paso fijo se detiene tras 18 iteraciones (19 gradientes)
en $(0.9950, -1.9899)$, con $f = 4.9748$. El GD con Armijo da 89 iteraciones (90 gradientes y 982 evaluaciones de
$f$) y termina en $(-0.9950, 0.9950)$, con $f = 1.9899$: sale de la cuenca en la que empezó, lo que es compatible
con que su paso inicial ($\eta_0 = 1$) sea mucho mayor que el paso fijo ($2\times10^{-3}$), pero tampoco llega al
mínimo global.

::: figura gif-gd-rastrigin
Título: Trayectorias del descenso por gradiente de paso fijo y con Armijo sobre las curvas de nivel de Rastrigin 2D
Fuente: Elaboración propia a partir de results/data/part1/gif_trayectorias.json (python run.py figures). Corrida con la semilla 0, configuración por defecto.
![Animación de las iteraciones del descenso por gradiente de paso fijo y con búsqueda de Armijo, desde un mismo punto inicial, sobre las curvas de nivel de la función de Rastrigin en dos dimensiones](figures/gd_rastrigin_2d.gif)
:::

El PSO en Rastrigin ([[fig:gif-pso-rastrigin]]) usa 30 partículas durante 665 iteraciones (20000 evaluaciones de
$f$). El mejor valor del enjambre es 9.48 al inicio y 1.026 en el fotograma siguiente; el primer fotograma en el que
ya está por debajo de $10^{-4}$ es el de la iteración 59, y la corrida termina con $f = 0$. La animación tiene 38
fotogramas, así que no muestra todas las iteraciones. La [[fig:enjambre-rastrigin]] presenta la misma configuración
(PSO en Rastrigin 2D, primera semilla) sobre la superficie de la función, con un deslizador para recorrer las
iteraciones y seguir cómo cambia la dispersión del enjambre, que empieza sorteado de manera uniforme en el dominio.

::: figura gif-pso-rastrigin
Título: Movimiento del enjambre del PSO sobre las curvas de nivel de Rastrigin 2D
Fuente: Elaboración propia a partir de results/data/part1/gif_trayectorias.json (python run.py figures). Corrida con la semilla 0, configuración por defecto.
![Animación de las iteraciones del PSO: las 30 partículas y la mejor posición del enjambre sobre las curvas de nivel de la función de Rastrigin en dos dimensiones](figures/pso_rastrigin_2d.gif)
:::

::: figura enjambre-rastrigin
Título: Enjambre del PSO sobre la superficie de Rastrigin 2D a lo largo de las iteraciones
Fuente: Elaboración propia a partir de las corridas de results/data/part1/runs/ (PSO en Rastrigin 2D, primera semilla).
incluir: figures/part1_enjambre_rastrigin.html
:::

### Sensibilidad a la regla de conteo (k = 1)

La regla $k = 2n$ es una convención. Para medir cuánto pesa, los dos GD se ejecutaron de nuevo con $k = 1$ (un
gradiente cuesta una evaluación), con las mismas semillas, el mismo presupuesto y la configuración por defecto. Solo
se re-ejecutan los GD: el EA, el PSO y el DE no usan gradientes, su costo no depende de $k$ y sus filas son las de la
tabla principal. La [[tab:sensibilidad-k1]] compara las dos reglas; cada celda muestra «$k = 2n$ → $k = 1$». Las
evaluaciones hasta el éxito se miden con la $k$ de cada ejecución, así que con $k = 1$ en el paso fijo coinciden con
el número de gradientes.

::: tabla sensibilidad-k1
Título: Descenso por gradiente con $k = 2n$ → $k = 1$, configuración por defecto (30 corridas por celda)
Fuente: Elaboración propia a partir de results/data/part1/summary.json (bloques `configuraciones` y `sensibilidad_k1`)
| Función | Dim. | Método | Mediana de $f_{\text{final}}$ | Éxito a $10^{-4}$ | Gradientes medios | Evaluaciones hasta el éxito |
|---|---|---|---|---|---|---|
| Rosenbrock | 2D | gdfijo | 1.905e-03 → 1.047e-08 | 3.3 % (1/30) → 100.0 % (30/30) | 5000.0 → 20000.0 | 19220 → 8282 |
| Rosenbrock | 2D | gdarmijo | 2.326e-03 → 8.596e-04 | 16.7 % (5/30) → 23.3 % (7/30) | 1424.4 → 1813.5 | 9976 → 10781 |
| Rosenbrock | 3D | gdfijo | 1.285e-03 → 5.517e-14 | 3.3 % (1/30) → 100.0 % (30/30) | 5000.0 → 30000.0 | 25998 → 7424 |
| Rosenbrock | 3D | gdarmijo | 1.338e-03 → 3.036e-04 | 0.0 % (0/30) → 6.7 % (2/30) | 1867.8 → 2695.0 | — → 28173 |
| Rastrigin | 2D | gdfijo | 1.642e+01 → 1.642e+01 | 0.0 % (0/30) → 0.0 % (0/30) | 18.4 → 18.4 | — → — |
| Rastrigin | 2D | gdarmijo | 2.985e+00 → 2.985e+00 | 16.7 % (5/30) → 16.7 % (5/30) | 653.1 → 777.7 | 160 → 118 |
| Rastrigin | 3D | gdfijo | 2.438e+01 → 2.438e+01 | 0.0 % (0/30) → 0.0 % (0/30) | 18.5 → 18.5 | — → — |
| Rastrigin | 3D | gdarmijo | 8.955e+00 → 8.955e+00 | 0.0 % (0/30) → 0.0 % (0/30) | 1222.7 → 1617.3 | — → — |
:::

El resultado central está en Rosenbrock: el GD de paso fijo pasa de 1 éxito de 30 a 30 de 30, en 2D y en 3D, y con
$k = 1$ tiene además 100 % de éxito en los tres umbrales. Con $k = 1$ dispone de 20 000 gradientes en 2D y 30 000 en
3D, en lugar de 5000, y sus corridas exitosas necesitan en promedio 8282 gradientes en 2D y 7424 en 3D: más de los
5000 que permite $k = 2n$. Es decir, con la regla principal el paso fijo no fracasa por la dirección que sigue, sino
porque el presupuesto se acaba antes. El GD con Armijo mejora menos (de 5 a 7 éxitos en 2D y de 0 a 2 en 3D), porque
gasta la mayor parte de su presupuesto en evaluaciones de $f$ durante los retrocesos, que cuestan lo mismo con las
dos reglas.

En Rastrigin, en cambio, la regla de conteo no cambia ninguna estadística de $f_{\text{final}}$. El paso fijo se
detiene por la tolerancia del gradiente tras unos 18 gradientes, mucho antes de agotar el presupuesto con cualquiera
de las dos reglas, y el GD con Armijo termina en los mismos valores aunque disponga de más gradientes. Solo cambian
los contadores, por ejemplo el costo medio de las corridas exitosas del GD con Armijo en 2D (de 160 a 118
evaluaciones equivalentes).

### Efecto de afinar los hiperparámetros

La optimización de hiperparámetros (HPO, Hyperparameter Optimization), descrita en la sección de metodología, eligió
valores nuevos en tres de sus seis unidades: el paso $\eta$ del descenso por gradiente (GD) de paso fijo en Rosenbrock
(`gdfijo`), los tres parámetros del GD con búsqueda de Armijo (`gdarmijo`) y los cuatro del algoritmo evolutivo (EA,
`ea`). La [[tab:hpo-parametros]] los compara con los valores por defecto; los afinados se redondean a 4 cifras
significativas y su valor completo está en `configs/part1/tuned.yaml`. En las otras tres unidades, el paso fijo en
Rastrigin, la optimización por enjambre de partículas (PSO, `pso`) y la evolución diferencial (DE, `de`), ningún ensayo
superó al de los valores por defecto, que se conservaron.

::: tabla hpo-parametros
Título: Hiperparámetros por defecto y afinados (4 cifras significativas) en las unidades que cambiaron
Fuente: Elaboración propia a partir de results/data/part1_hpo/seleccion.json
| Unidad | Ensayo ganador | Hiperparámetro | Por defecto | Afinado |
|---|---|---|---|---|
| gdfijo (Rosenbrock) | 26 | $\eta$ (`gd.eta.rosenbrock`) | 0.001 | 0.001494 |
| gdarmijo | 10 | $\eta_0$ (`gd.armijo.eta0`) | 1.0 | 3.520 |
| gdarmijo | 10 | $\beta$ (`gd.armijo.beta`) | 0.5 | 0.1243 |
| gdarmijo | 10 | $c$ (`gd.armijo.c`) | 0.0001 | 0.006728 |
| ea | 13 | $N$ (`ea.N`) | 50 | 117 |
| ea | 13 | $f_e$ (`ea.frac_e`) | 0.15 | 0.1650 |
| ea | 13 | $f_m$ (`ea.frac_m`) | 0.1 | 0.1766 |
| ea | 13 | $f_c$ (`ea.frac_c`) | 0.75 | 0.4854 |
:::

En el EA, $f_c$ es la fracción mínima de $N$ que se cruza: el número de cruzantes es el par hacia arriba de
$\lfloor N f_c \rfloor$, y sube si élite, mutantes y cruzantes no llegan a $N$ (relleno). Con los valores por defecto se
cruzan 38 de 50 individuos (fracción efectiva 0.760). Con los afinados, $\lfloor 117 f_c \rfloor = 56$ no alcanza a
cubrir la población junto con 19 individuos de élite y 20 mutantes, y el relleno sube el cruce a 78 de 117 (fracción
efectiva 0.667). Por eso el valor afinado de $f_c$ no determina el cruce: cualquier valor que dé menos de 78 cruzantes
produce el mismo EA.

La [[tab:hpo-rosenbrock]] y la [[tab:hpo-rastrigin]] comparan las dos versiones del experimento con las 30 semillas de
reporte, el mismo presupuesto y $k = 2n$. Cada celda muestra «por defecto → afinado»; el éxito es $f - f^* \le 10^{-4}$,
con $f^*$ el valor mínimo de la función, y las evaluaciones hasta el éxito son la media sobre las corridas exitosas
(«—» si no hay ninguna).

::: tabla hpo-rosenbrock
Título: Rosenbrock: resultados por defecto → afinados (30 corridas, semillas 0–29, $k = 2n$)
Fuente: Elaboración propia a partir de results/tables/part1_tuned/comparacion.csv
| Dim. | Método | Mediana de $f_{\text{final}}$ | Éxito a $10^{-4}$ | Evaluaciones hasta el éxito |
|---|---|---|---|---|
| 2D | gdfijo | 1.905e-03 → 2.402e-04 | 3.3 % → 23.3 % | 19220 → 16759 |
| 2D | gdarmijo | 2.326e-03 → 1.259e-06 | 16.7 % → 100.0 % | 9976 → 10140 |
| 2D | ea | 9.329e-03 → 3.182e-07 | 10.0 % → 93.3 % | 2613 → 8703 |
| 2D | pso | 3.320e-24 → 3.320e-24 | 100.0 % → 100.0 % | 1555 → 1555 |
| 2D | de | 0.000e+00 → 0.000e+00 | 100.0 % → 100.0 % | 985 → 985 |
| 3D | gdfijo | 1.285e-03 → 4.777e-04 | 3.3 % → 0.0 % | 25998 → — |
| 3D | gdarmijo | 1.338e-03 → 2.428e-05 | 0.0 % → 63.3 % | — → 22558 |
| 3D | ea | 3.269e-01 → 1.100e-01 | 0.0 % → 0.0 % | — → — |
| 3D | pso | 3.846e-06 → 3.846e-06 | 100.0 % → 100.0 % | 19103 → 19103 |
| 3D | de | 0.000e+00 → 0.000e+00 | 100.0 % → 100.0 % | 2213 → 2213 |
:::

::: tabla hpo-rastrigin
Título: Rastrigin: resultados por defecto → afinados (30 corridas, semillas 0–29, $k = 2n$)
Fuente: Elaboración propia a partir de results/tables/part1_tuned/comparacion.csv
| Dim. | Método | Mediana de $f_{\text{final}}$ | Éxito a $10^{-4}$ | Evaluaciones hasta el éxito |
|---|---|---|---|---|
| 2D | gdfijo | 1.642e+01 → 1.642e+01 | 0.0 % → 0.0 % | — → — |
| 2D | gdarmijo | 2.985e+00 → 4.975e+00 | 16.7 % → 6.7 % | 160 → 142 |
| 2D | ea | 0.000e+00 → 1.089e-10 | 93.3 % → 100.0 % | 3256 → 7915 |
| 2D | pso | 0.000e+00 → 0.000e+00 | 100.0 % → 100.0 % | 1664 → 1664 |
| 2D | de | 0.000e+00 → 0.000e+00 | 100.0 % → 100.0 % | 2175 → 2175 |
| 3D | gdfijo | 2.438e+01 → 2.438e+01 | 0.0 % → 0.0 % | — → — |
| 3D | gdarmijo | 8.955e+00 → 1.741e+01 | 0.0 % → 0.0 % | — → — |
| 3D | ea | 9.950e-01 → 0.000e+00 | 46.7 % → 96.7 % | 3677 → 8492 |
| 3D | pso | 0.000e+00 → 0.000e+00 | 86.7 % → 86.7 % | 3332 → 3332 |
| 3D | de | 0.000e+00 → 0.000e+00 | 93.3 % → 93.3 % | 4981 → 4981 |
:::

**Dónde mejora.** En Rosenbrock, el GD con Armijo pasa del 16.7 % al 100 % de éxito en 2D y del 0 % al 63.3 % en 3D,
y su mediana baja de $2.33\times10^{-3}$ a $1.26\times10^{-6}$ en 2D. El EA pasa del 10 % al 93.3 % en Rosenbrock 2D,
del 93.3 % al 100 % en Rastrigin 2D y del 46.7 % al 96.7 % en Rastrigin 3D; en Rastrigin 2D su mediana pasa de 0 a
$1.089\times10^{-10}$, todavía por debajo de $10^{-6}$. En Rosenbrock 3D el EA no logra ningún éxito con ninguna de
las dos versiones, aunque su mediana baja de 0.327 a 0.110. El GD de paso fijo en Rosenbrock 2D pasa del 3.3 % al
23.3 %. Donde el EA afinado gana en tasa de éxito, sus evaluaciones medias hasta el éxito suben
(por ejemplo, de 2613 a 8703 en Rosenbrock 2D); esas medias se toman sobre conjuntos distintos de corridas exitosas,
así que no se comparan una a una.

**Dónde empeora.** El GD con Armijo afinado empeora en Rastrigin: su mediana sube de 2.985 a 4.975 en 2D y de 8.955 a
17.41 en 3D, y su éxito en 2D baja del 16.7 % al 6.7 %. El GD de paso fijo en Rosenbrock 3D baja del 3.3 % al 0 % de
éxito, aunque su mediana baja de $1.285\times10^{-3}$ a $4.777\times10^{-4}$.

**Dónde no cambia.** El GD de paso fijo en Rastrigin, el PSO y el DE tienen resultados idénticos en las dos versiones,
porque conservaron los valores por defecto: en esas unidades ningún ensayo superó al defecto con la regla de selección.

La [[fig:convergencia-afinado-part1]] y la [[fig:cajas-afinado-part1]] muestran lo mismo de forma gráfica, solo para
los métodos cuyos hiperparámetros cambiaron (los dos GD y el EA), con el mismo piso de dibujo de $10^{-16}$ que las
figuras de la configuración por defecto.

::: figura convergencia-afinado-part1
Título: Convergencia por defecto (trazo continuo) frente a afinada (trazo discontinuo) de los métodos cuyos hiperparámetros cambiaron con el ajuste
Fuente: Elaboración propia a partir de las corridas de results/data/part1/runs/ (por defecto) y results/data/part1_tuned/runs/ (afinado); en el eje logarítmico los valores menores que 1e-16 (incluido el 0 exacto) se dibujan en 1e-16.
incluir: figures/part1_convergencia_afinado.html
:::

::: figura cajas-afinado-part1
Título: Distribución de f final − f* por defecto (caja rellena) y afinada (caja hueca) de los métodos cuyos hiperparámetros cambiaron con el ajuste
Fuente: Elaboración propia a partir de las corridas de results/data/part1/runs/ (por defecto) y results/data/part1_tuned/runs/ (afinado); en el eje logarítmico los valores menores que 1e-16 (incluido el 0 exacto) se dibujan en 1e-16.
incluir: figures/part1_cajas_afinado.html
:::

**Sensibilidad $k = 1$ de la versión afinada.** Los dos GD afinados también se re-ejecutaron con $k = 1$. En
Rosenbrock, el GD con Armijo afinado llega a 30 éxitos de 30 en 2D y en 3D (con $k = 2n$ tenía 30 y 19), con medianas
de $3.531\times10^{-10}$ y $1.362\times10^{-8}$, y el paso fijo afinado llega a 30 de 30 en 2D. En Rosenbrock 3D, el
paso fijo afinado se queda en 0 éxitos de 30 también con $k = 1$, aunque dispone de 30 000 gradientes en lugar de
5000: su mejor valor es $4.375\times10^{-4}$ con las dos reglas y su mediana apenas cambia (de $4.777\times10^{-4}$ a
$4.770\times10^{-4}$). Se estanca por encima del umbral, así que no es un problema de presupuesto; con el paso por
defecto y $k = 1$, la misma configuración tiene 30 éxitos de 30. Una causa compatible, no probada: en 3D el paso
afinado $1.494\times10^{-3}$ supera a $2/\lambda_{\max} \approx 1.427\times10^{-3}$, con $\lambda_{\max} \approx
1401.9$ el mayor valor propio de la Hessiana en el mínimo $(1, 1, 1)$. En Rastrigin, igual que con los valores por
defecto, la regla de conteo no cambia las estadísticas de $f_{\text{final}}$ de ninguno de los dos GD afinados.

**El efecto de $\eta$ en una corrida.** La [[fig:eta-rosenbrock]] muestra la trayectoria del GD de paso fijo en
Rosenbrock 2D para 14 valores de $\eta$ entre $10^{-5}$ y $10^{-2}$, todos desde el mismo punto inicial (semilla 0)
y con 5000 gradientes. El valor que acompaña a cada trayectoria es el mejor valor de $f$ visto, que con pasos grandes
no coincide con el del último punto dibujado. En esa corrida, el mejor valor visto baja al crecer el paso, desde
0.7119 con $\eta = 10^{-5}$ hasta $1.881\times10^{-3}$ con el valor por defecto ($10^{-3}$), $2.414\times10^{-4}$ con
el afinado ($1.494\times10^{-3}$) y $7.644\times10^{-5}$ con $\eta = 1.778\times10^{-3}$. Con pasos mayores empeora
de golpe: 0.03448 con $\eta = 3.162\times10^{-3}$, 36.70 con $5.623\times10^{-3}$ y 158.4 con $10^{-2}$, que es el
valor de $f$ en el punto inicial (158.3659): con ese paso la corrida nunca mejora el punto de partida. Es una sola
semilla y una sola dimensión, así que la figura ilustra la forma de la dependencia, con un intervalo útil estrecho
justo por debajo del límite de estabilidad local $2/\lambda_{\max} \approx 2\times10^{-3}$ descrito en la
metodología, pero no sirve para elegir $\eta$. Que $\eta = 1.778\times10^{-3}$ supere aquí al afinado no lo hace
mejor elección: la HPO eligió con 5 semillas de ajuste y un mismo $\eta$ para 2D y 3D, y en 3D ese límite es más
bajo ($2/\lambda_{\max} \approx 1.427\times10^{-3}$), de modo que un paso que en 2D queda por debajo del límite en 3D
lo supera.

::: figura eta-rosenbrock
Título: Trayectoria del descenso de gradiente de paso fijo en Rosenbrock 2D según el tamaño de paso η
Fuente: Elaboración propia a partir de results/data/part1/eta_deslizador.json.
incluir: figures/part1_eta_rosenbrock.html
:::
