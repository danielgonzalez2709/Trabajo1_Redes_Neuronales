<!--
SECCIÓN: Parte 2 — resultados · RESPONSABLE: equipo Parte 2 · ESTADO: borrador completo (13-oct).
Enunciado: "¿cambia la ruta óptima al variarlo? ¿a partir de qué valor?" + GIF de la evolución de la mejor solución sobre el
mapa de España. Figuras (Spec §7.6): mapa con deslizador de w, costo desglosado vs. w, convergencia ACO vs. GA (gap), GIF.
Cifras: results/data/part2/sweep_w.json, umbrales_w.json y sensibilidad/consumo{5.6,6.2}/comparacion_base.json
(barrido del 13-oct); umbrales, recorridos óptimos por tramo y sensibilidad: results/data/part2/umbrales_exactos.json
(verificación exacta, scripts/umbrales_exactos.py). Las cifras por recorrido (km, h, tramos con peaje, ventaja frente al segundo candidato) se
calcularon con src/part2/costos.py y src/part2/envolvente.py sobre esos archivos.
-->

## Parte 2: resultados

### ¿Cambia la ruta al variar el valor de la hora?

**Sí, en tres valores de $w$: 10,02, 14,53 y 42,19 €/h.** Con el óptimo exacto, el intervalo $[0, 100]$ €/h se
divide en cuatro tramos, cada uno con un recorrido óptimo distinto ([[tab:umbrales-part2]]). La [[fig:mapa-w]] permite
recorrer los valores de $w$ con un deslizador y ver qué arcos cambian y cuáles pasan a pagar peaje.

La envolvente de los recorridos que hallaron las heurísticas ponía los dos primeros umbrales en 10,75 y 13,81 €/h. El
recorrido óptimo entre 10,02 y 14,53 €/h (el 215) no estaba entre sus 215 candidatos: ningún valor del barrido cae en
ese tramo, que salta de 10 a 15 €/h, así que MMAS, AS y GA nunca lo buscaron. En su lugar ganaba el recorrido 139, que
en ese tramo cuesta como mucho 0,38 € más que el óptimo (1 499,23 € frente a 1 498,90 € en $w = 12$). El tercer
umbral, 42,19 €/h, es el mismo en los dos cálculos.

::: tabla umbrales-part2
Título: Recorrido óptimo en cada tramo del valor de la hora
Fuente: Elaboración propia a partir de results/data/part2/umbrales_exactos.json (óptimo exacto con PuLP + HiGHS); km, horas y peajes evaluados en un valor representativo de cada tramo.
| Tramo de $w$ (€/h) | Recorrido (candidato) | $w$ evaluado | Distancia | Tiempo | Peajes | Arcos con peaje | Ventaja máxima sobre el 2.º mejor recorrido conocido |
|---|---|---|---|---|---|---|---|
| 0 – 10,02 | 128 | 5 | 6 158,2 km | 81,66 h | 1,05 € | 1 de 47 | 1,42 € |
| 10,02 – 14,53 | 215 (solo exacto) | 12 | 6 216,8 km | 81,17 h | 1,05 € | 1 de 47 | 0,36 € |
| 14,53 – 42,19 | 138 | 25 | 6 283,7 km | 79,64 h | 24,25 € | 3 de 47 | 0,95 € |
| 42,19 – 100 | 140 | 100 | 6 284,9 km | 78,83 h | 64,81 € | 8 de 47 | 10,65 € |
:::

Los cambios de recorrido no siempre son locales. Al cruzar 10,02 €/h cambian 13 de los 47 arcos y al cruzar
14,53 €/h cambian 10, repartidos por toda la península: en el primer umbral, por ejemplo, Burgos–Santander y
Soria–Zaragoza dejan su lugar a Burgos–Soria y Oviedo/Uviéu–Santander. Al cruzar 42,19 €/h solo cambian 5, en el oeste
y el noroeste (salen León–Zamora y Ourense–Zamora y entran Salamanca–Zamora y Lugo–Ourense, entre otros). Además, las
rutas compiten muy de cerca. Hasta $w = 50$ €/h la ruta óptima supera a la segunda mejor conocida por menos de 1,50 €,
en viajes que cuestan entre 520 € y 4 530 €, y en el tramo de 10,02 a 14,53 €/h por solo 0,36 €. Los dos primeros umbrales son reales en el modelo, pero en la práctica las rutas son
**casi indiferentes**: un error de pocos céntimos en un peaje o en un tiempo podría moverlos.

::: figura mapa-w
Título: Recorrido de menor costo encontrado según el valor de la hora, con los tramos de peaje resaltados
Fuente: Elaboración propia a partir de results/data/part2/sweep_w.json y umbrales_exactos.json (python run.py figures). Los arcos son segmentos rectos entre capitales, no el trazado de la carretera.
incluir: figures/part2_mapa_w.html
:::

Hay un segundo efecto, que no cambia el orden de visita: **qué alternativa se toma en cada arco**. El recorrido 138
gana en todo el tramo de 14,53 a 42,19 €/h, pero paga 1,05 € de peaje en $w = 15$, 24,25 € en $w = 25$ y 37,95 € en
$w = 40$, porque cada arco se pasa a la autopista de pago cuando el tiempo ahorrado vale más que el peaje.

### ¿Cuánto pesa cada componente?

El tiempo domina el costo en cuanto $w > 0$ ([[fig:desglose-w]]). En $w = 25$ €/h el recorrido cuesta 2 544,76 €: 78,2 %
de tiempo (79,6 h), 20,8 % de combustible (529,48 €) y menos del 1 % de peajes (24,25 €). Incluso en $w = 100$ €/h los
peajes son el 0,8 % del total: solo 8 de los 47 arcos pagan. El techo está en la red, no en el modelo: en el recorrido
ganador de ese tramo solo 11 arcos tienen peaje en su ruta rápida, y en el conjunto de los 1 081 pares 534 lo tienen. Pasar
de $w = 0$ a $w = 100$ ahorra 2,9 h (81,77 h frente a 78,83 h) a cambio de 64,81 € de peaje y 117 km más.

::: figura desglose-w
Título: Costo del recorrido de menor costo encontrado, desglosado en tiempo, peajes y combustible, según el valor de la hora
Fuente: Elaboración propia a partir de results/data/part2/sweep_w.json (python run.py figures).
incluir: figures/part2_desglose_w.html
:::

### Comparación de los algoritmos

MMAS es el mejor método en los 11 valores de $w$ ([[tab:metodos-part2]]). Encuentra el mejor recorrido conocido en 10 de
ellos, y su media queda entre 0,24 % y 0,75 % por encima. El GA queda entre 2,3 % y 4,1 % por encima en media, con una
dispersión entre corridas mucho mayor (desviación de 11 € en $w = 0$ y de 175 € en $w = 100$), y Ant System entre 3,2 %
y 5,4 %. En $w = 20$ ninguna corrida encontró el mejor conocido: lo aporta la envolvente, con el recorrido 138, que MMAS
había encontrado en otros valores de $w$.

::: tabla metodos-part2
Título: Costo de los recorridos por método y valor de la hora (10 corridas de 51 654 recorridos evaluados cada una)
Fuente: Elaboración propia a partir de results/data/part2/sweep_w.json. Gap = 100 · (media − mejor conocido) / mejor conocido; el mejor conocido es el óptimo en los 11 valores de $w$ (verificado con PuLP + HiGHS).
| $w$ (€/h) | Mejor conocido (€) | MMAS media ± desv. (€) | Gap MMAS | AS media (€) | Gap AS | GA media ± desv. (€) | Gap GA |
|---|---|---|---|---|---|---|---|
| 0 | 519,71 | 523,52 ± 4,13 | 0,73 % | 547,98 | 5,44 % | 540,86 ± 11,11 | 4,07 % |
| 5 | 928,25 | 935,21 ± 3,77 | 0,75 % | 966,63 | 4,13 % | 960,10 ± 15,86 | 3,43 % |
| 10 | 1 336,55 | 1 340,87 ± 8,05 | 0,32 % | 1 384,33 | 3,57 % | 1 380,06 ± 27,96 | 3,25 % |
| 15 | 1 742,22 | 1 746,40 ± 4,74 | 0,24 % | 1 798,24 | 3,22 % | 1 809,51 ± 39,51 | 3,86 % |
| 20 | 2 144,84 | 2 159,40 ± 10,12 | 0,68 % | 2 222,00 | 3,60 % | 2 232,12 ± 29,14 | 4,07 % |
| 25 | 2 544,76 | 2 555,23 ± 7,35 | 0,41 % | 2 640,16 | 3,75 % | 2 603,79 ± 37,79 | 2,32 % |
| 30 | 2 942,97 | 2 954,49 ± 9,77 | 0,39 % | 3 053,74 | 3,76 % | 3 041,45 ± 46,16 | 3,35 % |
| 40 | 3 736,60 | 3 747,34 ± 10,67 | 0,29 % | 3 875,89 | 3,73 % | 3 856,34 ± 60,41 | 3,20 % |
| 50 | 4 527,45 | 4 540,31 ± 11,19 | 0,28 % | 4 707,02 | 3,97 % | 4 654,58 ± 53,32 | 2,81 % |
| 75 | 6 502,96 | 6 519,37 ± 17,61 | 0,25 % | 6 728,79 | 3,47 % | 6 691,42 ± 111,46 | 2,90 % |
| 100 | 8 477,20 | 8 513,76 ± 21,99 | 0,43 % | 8 748,35 | 3,20 % | 8 773,81 ± 175,27 | 3,50 % |
:::

La [[fig:convergencia-part2]] muestra por qué. El GA mejora rápido al principio y se estanca: su población colapsa a unas
pocas decenas de recorridos distintos y el cruce deja de producir novedades. MMAS, con una evaporación lenta
($\rho = 0{,}02$), explora más tiempo y sigue mejorando en la segunda mitad del presupuesto. Ant System, con $\rho = 0{,}5$
y depósito de todas las hormigas, se estanca lejos del mejor conocido: su media queda por detrás de la del GA en 8 de
los 11 valores de $w$, aunque varía menos entre corridas.

::: figura convergencia-part2
Título: Convergencia de MMAS, Ant System y GA: gap frente al mejor conocido según los recorridos evaluados
Fuente: Elaboración propia a partir de los historiales results/data/part2/history_{aco,ga}_w*.json (python run.py figures). Media y banda mínimo–máximo de 10 corridas; selector de w.
incluir: figures/part2_convergencia.html
:::

La [[fig:gif-mmas]] y la [[fig:gif-ga]] muestran cómo evoluciona la mejor solución de cada método sobre el mapa en
$w = 25$ €/h, con un fotograma por mejora. El recorrido final de MMAS es el mejor conocido en ese $w$: 6 283,7 km,
79,6 h y 24,25 € de peaje (AP-68 y AP-9).

::: figura gif-mmas
Título: Evolución de la mejor ruta de MMAS sobre el mapa de España (w = 25 €/h, mejor de 10 corridas)
Fuente: Elaboración propia a partir de results/data/part2/history_aco_w25.json (python run.py figures). Tramos con peaje en naranja; contorno provincial del IGN.
![Animación de la evolución de la mejor ruta de MMAS](figures/tsp_mmas_w25.gif)
:::

::: figura gif-ga
Título: Evolución de la mejor ruta del GA sobre el mapa de España (w = 25 €/h, mejor de 10 corridas)
Fuente: Elaboración propia a partir de results/data/part2/history_ga_w25.json (python run.py figures). Tramos con peaje en naranja; contorno provincial del IGN.
![Animación de la evolución de la mejor ruta del GA](figures/tsp_ga_w25.gif)
:::

### Sensibilidad al consumo

Con un consumo de autopista mayor que el homologado, el combustible pesa más y la autopista de pago compensa más tarde:
los tres umbrales suben ([[tab:sensibilidad-part2]]). El combustible del recorrido en $w = 25$ €/h pasa de 529,48 € a
644,58 € (+21,7 %) con 5,6 l/100 km y a 713,65 € (+34,8 %) con 6,2 l/100 km. Con el óptimo exacto, los cuatro
recorridos óptimos son los mismos que en la base con los dos consumos: solo cambian los valores de $w$ en que se
alternan. (La envolvente de las heurísticas mostraba otro ganador en el segundo tramo con 5,6 l/100 km: era el recorrido
óptimo que el barrido base no había encontrado.) En los dos casos el recorrido de $w = 15$ €/h deja de ser el mismo, porque ese valor queda ahora por debajo del
segundo umbral.

::: tabla sensibilidad-part2
Título: Umbrales del valor de la hora según el consumo del vehículo
Fuente: Elaboración propia a partir de results/data/part2/umbrales_exactos.json (óptimo exacto con PuLP + HiGHS).
| Consumo (l/100 km) | Umbral 1 (€/h) | Umbral 2 (€/h) | Umbral 3 (€/h) | Mismos recorridos óptimos que la base |
|---|---|---|---|---|
| 4,6 (WLTP combinado, base) | 10,02 | 14,53 | 42,19 | — |
| 5,6 (extra alta, mínimo) | 12,20 | 17,69 | 43,57 | Sí |
| 6,2 (extra alta, máximo) | 13,51 | 19,59 | 44,39 | Sí |
:::

### Demo

La demo (`configs/part2/demo.yaml`: MMAS, $w = 25$ €/h, 1 000 iteraciones, 10 corridas) tarda unos 18 segundos en esta
máquina. Su mejor recorrido cuesta 2 544,76 €, igual al mejor conocido (0,00 %); la media de las 10 corridas
queda un 0,36 % por encima. Con 100 iteraciones, la versión previa de la demo quedaba un 8,97 % (mejor) y un 15,71 %
(media) por encima, porque con $\rho = 0{,}02$ la feromona apenas empieza a concentrarse. Con 1 000 iteraciones evalúa
47 001 recorridos por corrida, el 91 % de los 51 654 del barrido.
