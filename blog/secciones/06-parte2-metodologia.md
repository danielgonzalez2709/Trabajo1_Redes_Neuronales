<!--
SECCIÓN: Parte 2 — metodología · RESPONSABLE: equipo Parte 2 · ESTADO: borrador completo (13-oct).
Contenido: matriz de costos con dos alternativas por par; ACO y GA (parámetros de configs/part2/base.yaml); comparación
justa por recorridos evaluados; barrido del valor de la hora y umbral por envolvente de candidatos (Spec v1.16; la
bisección y el exacto con PuLP quedaron fuera: T3.2 es opcional desde Spec v1.14 y no se implementó).
Citas disponibles: @dorigo1996, @dorigo1997, @stutzle2000, @dantzig1954.
-->

## Parte 2: metodología

### Matriz de costos

Para un valor de la hora $w$ dado, cada par de capitales tiene dos costos posibles, uno por alternativa (la ecuación del
costo está en la fundamentación), y la matriz $C(w)$ toma el menor. Si las dos cuestan lo mismo se elige la rápida. Así,
al subir $w$ cambian dos cosas: **qué alternativa se usa en cada tramo** y, como consecuencia, **qué orden de visita
resulta más barato**. La matriz es simétrica por construcción y se recalcula para cada $w$ sin volver a consultar OSRM.

### Algoritmos

Se comparan dos metaheurísticas, implementadas desde cero con NumPy (`src/part2/aco.py` y `src/part2/ga.py`), con los
parámetros de la [[tab:parametros-part2]].

**Colonia de hormigas.** La variante principal es MAX–MIN Ant System [MMAS, @stutzle2000] y, como comparación, el
Ant System original [@dorigo1996]. Los parámetros siguen los valores de referencia de las notas del curso. En MMAS
deposita una sola hormiga por iteración, alternando la mejor de la iteración y la mejor global, y la feromona se
mantiene entre $\tau_{\min}$ y $\tau_{\max}$. Las dos variantes parten del recorrido del vecino más cercano.

**Algoritmo genético.** Cada individuo es una permutación de las 47 capitales y su aptitud es directamente el costo del
recorrido cerrado. En cada generación pasan las 2 mejores sin cambios (elitismo); los demás hijos salen de dos torneos de
4 individuos, cruce de orden (OX) con probabilidad 0,9 y, con probabilidad 0,2, una mutación por inversión o por
intercambio (50/50). La población inicial incluye el mismo recorrido del vecino más cercano que usa ACO, de modo que
ambos métodos arrancan del mismo punto.

::: tabla parametros-part2
Título: Parámetros de los algoritmos de la Parte 2
Fuente: Elaboración propia a partir de configs/part2/base.yaml.
| Método | Parámetros | Recorridos evaluados por corrida |
|---|---|---|
| MMAS (principal) | $m = 47$ hormigas, $\alpha = 1$, $\beta = 3$, $\rho = 0{,}02$, $p_{\text{best}} = 0{,}05$, 1 099 iteraciones | $1 + 47 \cdot 1\,099 = 51\,654$ |
| Ant System (comparación) | $m = 47$, $\alpha = 1$, $\beta = 3$, $\rho = 0{,}5$, 1 099 iteraciones | $51\,654$ |
| GA | población 150, 348 generaciones, $p_c = 0{,}9$, $p_m = 0{,}2$, torneo $k = 4$, 2 élites | $150 + 148 \cdot 348 = 51\,654$ |
:::

**Comparación justa.** El enunciado no fija iteraciones, así que la regla es la misma que en la Parte 1: igual
presupuesto de evaluaciones. Cada método evalúa exactamente **51 654 recorridos** por corrida; el vecino más cercano
cuenta como uno. Con los valores por defecto originales ACO evaluaba 14 101 recorridos y el GA 148 150, lo que habría
favorecido al GA. Las curvas de convergencia usan los recorridos evaluados como eje horizontal.

### Experimento

- **Barrido del valor de la hora:** $w \in \{0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100\}$ €/h, más denso entre 0 y 50.
- **Corridas:** 10 por método y por $w$ (MMAS, AS y GA: 330 corridas). La semilla es `base_seed + run_id`, con un
  `run_id` distinto para cada combinación de $w$, método y corrida (Spec §7.5).
- **Métricas:** mejor, media y desviación estándar del costo, y el **gap** de la media y del mejor frente al
  **mejor costo conocido** en ese $w$. No se resolvió el óptimo exacto [la formulación de @dantzig1954 quedó como
  tarea opcional], así que el gap no se mide frente a un óptimo probado.

**Umbral del valor de la hora.** Para responder «¿a partir de qué valor cambia la ruta?» no se usa una bisección con
una heurística, porque mezclaría el azar del algoritmo con el efecto de $w$. Para un recorrido fijo $\pi$, cada tramo
cuesta el mínimo de dos rectas en $w$, de modo que su costo

$$
C_\pi(w) = \sum_{(i,j) \in \pi} \min\left(a^{\text{rápida}}_{ij} + b^{\text{rápida}}_{ij}\,w,\; a^{\text{sin peaje}}_{ij} + b^{\text{sin peaje}}_{ij}\,w\right),
\qquad a = P + d\,\tfrac{\text{consumo}}{100}\,p_{\text{comb}},\quad b = t,
$$

es lineal a trozos y se evalúa en cualquier $w$ sin optimizar. Se reúnen como candidatos los mejores recorridos de todas
las corridas del barrido (215 recorridos distintos) y se calcula de forma exacta su **envolvente inferior**
$\min_\pi C_\pi(w)$ en $[0, 100]$. Los umbrales son los valores de $w$ en que cambia el recorrido ganador; se reportan
como umbrales **entre las mejores rutas encontradas**, no del óptimo.

**Sensibilidad del consumo.** Se repiten el barrido con MMAS y la envolvente con 5,6 y 6,2 l/100 km en lugar de 4,6,
sin editar código (`configs/part2/sensibilidad_consumo.yaml`, y `--set costo.consumo_l100=6.2` para el segundo valor). La envolvente de cada consumo usa los candidatos del barrido base más
los nuevos, todos evaluados con el consumo nuevo, para que la diferencia venga del consumo y no del azar.

**Reproducción.** `python run.py part2 --config configs/part2/sweep_w.yaml` regenera el barrido (unos 18 minutos);
`python run.py part2 --config configs/part2/demo.yaml` corre la demo (MMAS, $w = 25$, 100 iteraciones, 10 corridas)
en pocos segundos.
