<!--
SECCIÓN: Discusión y conclusiones · RESPONSABLES: ambos equipos + puente · ESTADO: Parte 1 redactada el 13-oct-2026;
Parte 2 y conclusiones generales pendientes de sus responsables.
Enunciado (Parte 1): "¿Qué aportaron los métodos de descenso por gradiente y qué aportaron los métodos heurísticos?
Respondan con base en el valor final de la función objetivo y el número de evaluaciones, apoyándose en la geometría de cada
función (convexidad local, número de mínimos locales, condicionamiento)". Incluir amenazas a la validez (p. ej. el óptimo
de Rastrigin en el centro del dominio; η empírica en Rosenbrock; aproximación de peajes por suma de tramos).
-->

## Discusión y conclusiones

Esta sección discute la Parte 1. La discusión del problema del viajero está en la sección de resultados de la
Parte 2.

### Parte 1: qué aportó el descenso por gradiente y qué aportaron los heurísticos

Las cifras de este apartado son las de la configuración por defecto, con 30 corridas por configuración y la regla
$k = 2n$, salvo donde se dice otra cosa. El éxito es $f - f^* \le 10^{-4}$, con $f^*$ el valor mínimo de la función.

**Rosenbrock: un solo mínimo, mal condicionado.** La función tiene un único mínimo en el fondo de un valle curvo y
estrecho ([[fig:contorno-rosenbrock]]), y la curvatura cambia mucho de un punto a otro del dominio: la constante de
Lipschitz del gradiente es $L \approx 5\,971$ en 2D (Spec §6.3). Los dos descensos por gradiente (GD) llegan al valle:
el paso fijo baja de $10^{-2}$ en 30 de 30 corridas en 2D y en 29 de 30 en 3D, y el GD con Armijo en 19 y en 30. Pero
casi ninguno llega a $10^{-4}$: 1 de 30 con paso fijo en cada dimensión, y 5 y 0 de 30 con Armijo. La sensibilidad con
$k = 1$ indica dónde está el límite. Con esa regla el paso fijo dispone de 20 000 y 30 000 gradientes en lugar de 5000,
y tiene éxito en 30 de 30 corridas en 2D y en 3D, con 8282 y 7424 gradientes medios hasta el éxito. Para el paso fijo
con $\eta = 10^{-3}$, entonces, lo que falta con $k = 2n$ son gradientes: la trayectoria es la misma y solo se alarga,
porque el avance a lo largo del valle es lento. No vale para todo GD: con $k = 1$ el GD con Armijo solo sube a 7 y 2
éxitos de 30, porque gasta casi todo su presupuesto en evaluaciones de $f$, que esa regla no abarata, y el paso fijo
afinado en 3D sigue en 0 de 30 con 30 000 gradientes. La optimización por enjambre de partículas (PSO) y la evolución
diferencial (DE), que no usan el gradiente, tienen éxito en las 30 corridas de cada dimensión. El DE lo hace con pocas
evaluaciones (985 de media hasta el éxito en 2D y 2213 en 3D, frente a 19220 y 25998 de la única corrida exitosa del
paso fijo) y termina en $f = 0$ exacto. El PSO es barato en 2D (1555) pero no en 3D, donde necesita 19103 evaluaciones
medias y solo 12 de 30 corridas bajan de $10^{-6}$. El algoritmo evolutivo (EA) no resuelve esta función con sus valores
por defecto: 3 éxitos de 30 en 2D y ninguno en 3D, donde su mediana (0.3269) es peor que la de los dos GD
($1.285\times10^{-3}$ y $1.338\times10^{-3}$). Ser un método de población no basta en un valle estrecho.

**Rastrigin: muchos mínimos locales.** La función es una rejilla regular de cuencas ([[fig:contorno-rastrigin]]),
convexa solo localmente alrededor de cada mínimo. El GD es un método local: baja al fondo de la cuenca en la que
empieza, o de una cercana, y se queda allí. El paso fijo termina en 15 valores distintos de $f$ en 2D y en 17 en 3D
(redondeados a tres decimales), entre 1.990 y 49.75, y nunca en el mínimo global. Todos esos valores son aproximadamente
$0.995\,m$ con $m$ entero (1.990, 4.975, 24.874...; el cociente se aparta de un entero menos de 0.003), lo que es
compatible con que cada corrida termine en un mínimo local distinto de la rejilla. El costo no es el problema: el paso
fijo se detiene por la tolerancia del gradiente tras unos 18 gradientes, y la regla $k = 1$ no cambia ningún valor
final. El GD con Armijo llega más abajo (mediana 2.985 frente a 16.42 en 2D, y 8.955 frente a 24.38 en 3D) y alcanza el
mínimo global en 5 de 30 corridas en 2D y en ninguna en 3D. Agota el presupuesto en 24 de 30 corridas en 2D y en 26 de
30 en 3D, pero su última mejora ocurre pronto, con mediana de 468 y 558 evaluaciones equivalentes sobre las 30 corridas:
el resto del presupuesto se gasta sin mejorar. Los métodos de población sí alcanzan el mínimo global en la mayoría de
las corridas, aunque no en todas. En 2D, el PSO y el DE lo hacen en 30 de 30 y el EA en 28. En 3D, el DE en 28, el PSO
en 26 y el EA en 14; las corridas que fallan terminan en 0.995 o en 1.990, los dos primeros múltiplos de esa misma
serie.

**Qué aporta cada familia.** El GD aporta rapidez para bajar dentro de una cuenca. En Rastrigin 2D, las 5 corridas
exitosas del GD con Armijo necesitan 160 evaluaciones equivalentes de media, frente a 1664 del PSO, 2175 del DE y
3256 del EA, y el paso fijo termina tras 73.5 evaluaciones equivalentes de media. Pero el resultado del GD depende
del punto inicial: en Rastrigin su valor final es el del mínimo local al que cae, y en Rosenbrock, donde no hay
mínimos locales que lo atrapen, depende de que el presupuesto alcance. Los métodos de población aportan
exploración: reparten sus evaluaciones entre muchos puntos y no dependen de un único punto inicial. A cambio pagan
más evaluaciones en una función multimodal, y tampoco aseguran el resultado (PSO 26 de 30 y DE 28 de 30 en
Rastrigin 3D). Dentro de la familia hay diferencias grandes: con los valores por defecto, la tasa de éxito del EA
queda por debajo de las del PSO y el DE en las cuatro configuraciones.

**Amenazas a la validez.**

- El mínimo de Rastrigin está en el centro del dominio. Eso puede favorecer a los métodos con algún sesgo hacia el
  centro, y no se probó con la función desplazada.
- El paso $\eta = 10^{-3}$ del GD en Rosenbrock es empírico y no tiene garantía global de descenso.
- La regla «un gradiente cuesta $2n$ evaluaciones» es una convención, no un costo medido, porque el gradiente es
  analítico. Por eso se reporta también $k = 1$, que cambia el resultado del paso fijo en Rosenbrock.
- El GD de paso fijo registra el valor de $f$ en cada iterado sin costo (método `observe`), así que su curva de
  convergencia y su mejor punto visto no le cuestan evaluaciones.
- Hay un solo presupuesto ($10\,000 \cdot n$) y solo dos dimensiones (2D y 3D): nada de lo anterior se puede
  extender a dimensiones mayores.
- El EA no logra ningún éxito en Rosenbrock 3D, ni con los valores por defecto ni con los afinados, de modo que en
  esa configuración no hay evaluaciones hasta el éxito que comparar.
- Con 30 corridas, la tasa de éxito cambia en pasos de 3.3 puntos porcentuales (una corrida): diferencias de una o
  dos corridas entre métodos no son concluyentes.

**Conclusiones de la Parte 1.**

- En Rosenbrock, el GD encuentra el valle pero no el mínimo con el presupuesto de $k = 2n$ (1 éxito de 30 con paso
  fijo); con $k = 1$ el paso fijo con $\eta = 10^{-3}$ llega en 30 de 30: a ese paso le faltan gradientes, no dirección.
- En Rastrigin, el GD termina en el mínimo local de su cuenca en pocas evaluaciones (unos 18 gradientes con paso
  fijo) y casi nunca en el global (0 de 30 con paso fijo; 5 de 30 con Armijo en 2D).
- El DE y el PSO resuelven las dos funciones en 2D en las 30 corridas; en Rastrigin 3D tienen 28 y 26 éxitos de 30:
  son los métodos más fiables del experimento, pero ninguno acierta en todas las corridas.
- El EA con el esquema visto en clase depende mucho de sus hiperparámetros: con los valores por defecto tiene 3
  éxitos de 30 en Rosenbrock 2D y con los afinados 28, como se discute a continuación.

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
