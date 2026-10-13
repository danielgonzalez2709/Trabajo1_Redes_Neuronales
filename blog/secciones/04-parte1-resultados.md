<!--
SECCIÓN: Parte 1 — resultados · RESPONSABLE: equipo Parte 1 · ESTADO: pendiente.
Figuras previstas (Spec §6.7): curvas de nivel; curvas de convergencia (mediana e IQR vs. evaluaciones equivalentes);
diagramas de caja; GIF de GD y de PSO (media/); interactivas (Plotly) opcionales.
Tablas: estadísticas por configuración desde results/data/part1/summary.json (las cifras se copian del JSON, no a mano).
Cómo agregar una figura:
  ::: figura convergencia-rastrigin-2d
  Título: Convergencia en Rastrigin 2D (mediana e intervalo intercuartílico de 30 corridas)
  Fuente: Elaboración propia a partir de results/data/part1/summary.json.
  ![Curvas de convergencia](figures/convergencia_rastrigin_2d.png)
  :::
y citarla en el texto con [[fig:convergencia-rastrigin-2d]] (si no se cita, el build falla).
-->

## Parte 1: resultados

*Pendiente (equipo Parte 1).*

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
