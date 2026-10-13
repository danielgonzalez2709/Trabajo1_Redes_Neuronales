<!--
SECCIÓN: Discusión y conclusiones · RESPONSABLES: ambos equipos + puente · ESTADO: pendiente.
Enunciado (Parte 1): "¿Qué aportaron los métodos de descenso por gradiente y qué aportaron los métodos heurísticos?
Respondan con base en el valor final de la función objetivo y el número de evaluaciones, apoyándose en la geometría de cada
función (convexidad local, número de mínimos locales, condicionamiento)". Incluir amenazas a la validez (p. ej. el óptimo
de Rastrigin en el centro del dominio; η empírica en Rosenbrock; aproximación de peajes por suma de tramos).
-->

## Discusión y conclusiones

*Pendiente.*

### Parte 1: lo que enseña la afinación de hiperparámetros

**Efecto techo.** La optimización por enjambre de partículas (PSO) y la evolución diferencial (DE) ya resuelven casi
todas las corridas con sus valores por defecto. Con el umbral $f - f^* \le 10^{-4}$, donde $f^*$ es el valor mínimo de
la función, las dos llegan al 100 % en Rosenbrock 2D y 3D y en Rastrigin 2D; en Rastrigin 3D, el PSO llega al 86.7 % y
el DE al 93.3 %. A $10^{-6}$ las tasas son las mismas, salvo la del PSO en Rosenbrock 3D, que baja al 40 %. Así
queda poco margen: en el ajuste, el defecto de ambos métodos tiene la mediana recortada en $10^{-6}$ en las cuatro
celdas, y el mejor ensayo de cada uno empató en puntaje con el defecto (10.5 en el PSO y 14.625 en el DE). Ningún
ensayo los superó con claridad y la optimización de hiperparámetros (HPO, Hyperparameter Optimization) conservó sus
valores por defecto.

**Un conjunto por método.** Cada método comparte un solo conjunto de hiperparámetros para las dos funciones y las dos
dimensiones, y el puntaje promedia rangos entre celdas. Una mejora grande en una celda puede compensar una pérdida en
otra. En el descenso por gradiente (GD) con Armijo, el rango en Rosenbrock 2D bajó de 22 a 4 en el ajuste, mientras
que en Rastrigin 3D subió de 6.5 a 9.5; el promedio favoreció al ensayo nuevo, y con las semillas de reporte el GD con
Armijo afinado mejora en Rosenbrock y empeora en Rastrigin. El paso fijo se afina por función, pero se comparte entre
dimensiones: en el ajuste, el ensayo elegido para Rosenbrock mejoró el rango en las dos dimensiones (de 4 a 3 en 2D y
de 2 a 1 en 3D), y con las semillas de reporte su éxito sube en 2D (del 3.3 % al 23.3 %) y baja en 3D (del 3.3 % al
0 %).

**Cinco semillas son pocas.** En el ajuste, con 5 semillas, la mediana del GD con Armijo en Rastrigin 2D mejoró con los
valores nuevos (de 4.975 a 1.99), pero con las 30 semillas de reporte empeoró (de 2.985 a 4.975). En 3D empeoró en los
dos casos (de 5.97 a 7.96 en el ajuste y de 8.955 a 17.41 en reporte). Esa diferencia entre ajuste y reporte es
compatible con ruido de muestreo en las 5 semillas, pero el experimento no prueba que esa sea la causa.

**Amenazas a la validez de la HPO.** Los 30 ensayos de búsqueda aleatoria por unidad cubren de forma dispersa
espacios de hasta cinco dimensiones.
<!-- TODO(cita): cobertura de la búsqueda aleatoria en espacios de varias dimensiones con pocos ensayos
(candidato sin verificar para T4.7: Bergstra y Bengio 2012). -->
Los espacios de búsqueda se eligieron a mano. El presupuesto del ajuste es el mismo del
reporte, así que los valores afinados valen para ese presupuesto y no necesariamente para otro. Todo el ajuste usa
$k = 2n$: con $k = 1$ los descensos por gradiente disponen de más gradientes y su mejor configuración podría ser otra.
Por último, la corrección de la regla de selección, contada en la metodología, se decidió después de mirar las semillas
de reporte.
<!-- TODO(cita): el ajuste de parámetros de algoritmos evolutivos depende del problema y del presupuesto
(candidato sin verificar para T4.7: Eiben y Smit 2011). -->

**El paso $\eta = 1/L$ frente a $\eta = 10^{-3}$.** La [[tab:sensibilidad-eta]] muestra que, en Rosenbrock, el paso
$\eta = 1.5\times10^{-4}$ (la cota redondeada que la sección 6.3 de la Spec da para 3D, usada en las dos dimensiones;
en 3D supera a $1/L$ en un 2.6 %) termina lejos del mínimo con el presupuesto disponible: mediana de 0.147 en 2D y
0.219 en 3D, frente a $1.905\times10^{-3}$ y $1.285\times10^{-3}$ con $\eta = 10^{-3}$. La cota $1/L$ se fija con la
curvatura máxima en todo el dominio, mientras que en el valle, por donde avanza la trayectoria, la curvatura es
menor; la explicación esperada, por el mal condicionamiento del valle, es que un paso pensado para el peor caso
resulta demasiado corto allí. El experimento solo muestra que con 5 000 gradientes ese paso no llega. La HPO apunta en
la misma dirección: para el paso fijo en Rosenbrock eligió $\eta \approx 1.494\times10^{-3}$, todavía mayor que
$10^{-3}$ y sin garantía global.
