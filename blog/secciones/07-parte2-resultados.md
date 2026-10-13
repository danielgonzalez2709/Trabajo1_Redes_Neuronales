<!--
SECCIÓN: Parte 2 — resultados · RESPONSABLE: equipo Parte 2 · ESTADO: borrador completo (13-oct).
Enunciado: "¿cambia la ruta óptima al variarlo? ¿a partir de qué valor?" + GIF de la evolución de la mejor solución sobre el
mapa de España. Figuras (Spec §7.6): mapa con deslizador de w, costo desglosado vs. w, convergencia ACO vs. GA (gap), GIF.
Cifras: results/data/part2/sweep_w.json, umbrales_w.json y sensibilidad/consumo{5.6,6.2}/comparacion_base.json
(barrido del 13-oct). Las cifras por recorrido (km, h, tramos con peaje, ventaja frente al segundo candidato) se
calcularon con src/part2/costos.py y src/part2/envolvente.py sobre esos archivos.
-->

## Parte 2: resultados

### ¿Cambia la ruta al variar el valor de la hora?

**Sí, en tres valores de $w$: 10,75, 13,81 y 42,19 €/h.** La envolvente de los candidatos divide el intervalo
$[0, 100]$ €/h en cuatro tramos, cada uno con un recorrido ganador distinto
([[tab:umbrales-part2]]). La [[fig:mapa-w]] permite recorrer los valores de $w$ con un deslizador y ver qué arcos
cambian y cuáles pasan a pagar peaje.

::: tabla umbrales-part2
Título: Recorrido de menor costo encontrado en cada tramo del valor de la hora
Fuente: Elaboración propia a partir de results/data/part2/umbrales_w.json; km, horas y peajes evaluados en un valor representativo de cada tramo.
| Tramo de $w$ (€/h) | Recorrido (candidato) | $w$ evaluado | Distancia | Tiempo | Peajes | Arcos con peaje | Ventaja máxima sobre el 2.º candidato |
|---|---|---|---|---|---|---|---|
| 0 – 10,75 | 128 | 5 | 6 158,2 km | 81,66 h | 1,05 € | 1 de 47 | 1,42 € |
| 10,75 – 13,81 | 139 | 12 | 6 224,3 km | 81,14 h | 1,05 € | 1 de 47 | 0,66 € |
| 13,81 – 42,19 | 138 | 25 | 6 283,7 km | 79,64 h | 24,25 € | 3 de 47 | 0,96 € |
| 42,19 – 100 | 140 | 100 | 6 284,9 km | 78,83 h | 64,81 € | 8 de 47 | 10,65 € |
:::

Los cambios de recorrido son locales: entre dos ganadores consecutivos cambian entre 4 y 6 de los 47 arcos, todos en el
centro y el noroeste peninsular. Al cruzar 10,75 €/h, por ejemplo, salen
Salamanca–Zamora y Valladolid–León y entran Cáceres–Salamanca y Palencia–León. Además, las rutas compiten muy de cerca.
Hasta $w = 50$ €/h la mejor ruta supera a la segunda por menos de 1,50 €, en viajes que cuestan entre 520 € y 4 530 €, y
la ruta 139 gana por 0,66 € como máximo. Los dos primeros umbrales son reales en el modelo, pero en la práctica las rutas son
**casi indiferentes**: un error de pocos céntimos en un peaje o en un tiempo podría moverlos.

::: figura mapa-w
Título: Recorrido de menor costo encontrado según el valor de la hora, con los tramos de peaje resaltados
Fuente: Elaboración propia a partir de results/data/part2/sweep_w.json y umbrales_w.json (python run.py figures). Los arcos son segmentos rectos entre capitales, no el trazado de la carretera.
incluir: figures/part2_mapa_w.html
:::

Hay un segundo efecto, que no cambia el orden de visita: **qué alternativa se toma en cada arco**. El recorrido 138
gana en todo el tramo de 13,81 a 42,19 €/h, pero paga 1,05 € de peaje en $w = 15$, 24,25 € en $w = 25$ y 37,95 € en
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
Fuente: Elaboración propia a partir de results/data/part2/sweep_w.json. Gap = 100 · (media − mejor conocido) / mejor conocido; el mejor conocido no es un óptimo probado.
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
644,58 € (+21,7 %) con 5,6 l/100 km y a 713,65 € (+34,8 %) con 6,2 l/100 km. Con 6,2 l/100 km los cuatro recorridos
ganadores son los mismos que en la base, solo que cambian en otros valores de $w$. Con 5,6 l/100 km cambia el ganador
del segundo tramo. En los dos casos el recorrido de $w = 15$ €/h deja de ser el mismo, porque ese valor queda ahora por debajo del
segundo umbral.

::: tabla sensibilidad-part2
Título: Umbrales del valor de la hora según el consumo del vehículo
Fuente: Elaboración propia a partir de results/data/part2/sensibilidad/consumo{5.6,6.2}/comparacion_base.json.
| Consumo (l/100 km) | Umbral 1 (€/h) | Umbral 2 (€/h) | Umbral 3 (€/h) | Mismos recorridos ganadores que la base |
|---|---|---|---|---|
| 4,6 (WLTP combinado, base) | 10,75 | 13,81 | 42,19 | — |
| 5,6 (extra alta, mínimo) | 12,20 | 17,69 | 43,57 | No |
| 6,2 (extra alta, máximo) | 14,49 | 18,62 | 44,39 | Sí |
:::

### Demo

La demo (`configs/part2/demo.yaml`: MMAS, $w = 25$ €/h, 100 iteraciones, 10 corridas) tarda menos de un segundo en esta
máquina. Su mejor recorrido cuesta 2 772,91 €, un 8,97 % por encima del mejor conocido (15,71 % en media). Es lo
esperable: con 100 iteraciones evalúa 4 701 recorridos por corrida, menos del 10 % del presupuesto del barrido, y
con $\rho = 0{,}02$ la feromona apenas se ha concentrado.
