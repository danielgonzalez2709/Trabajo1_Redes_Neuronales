<!--
SECCIÓN: Parte 2 — datos y fuentes · RESPONSABLES: equipo Parte 2 (Jose Miguel, Camila) · ESTADO: borrador completo (13-oct).
Enunciado: "Documenten las fuentes de todos los datos (distancias, tiempos, peajes, precios de combustible) con su fecha de
consulta" y el vehículo "con fuente citada". Fuente única de verdad: data/fuentes.md (copiar de ahí, no reescribir de
memoria). Cifras: data/processed/*.json y *.csv. Incluir: fecha de corte 1-oct-2026, OSRM local (por qué no el servidor
público), simetría por construcción y asimetría real medida, peajes por suma de tramos y su validación, AP-68.
-->

## Parte 2: datos del problema

Todos los datos describen la **misma fecha de corte, el 1 de octubre de 2026**: red viaria, tarifas de peaje y precio
del combustible vigentes ese día. Se descargaron una sola vez (`scripts/descargar_datos.py` o pasos manuales
documentados) y los experimentos no usan internet. La [[tab:fuentes-part2]] resume las fuentes; el registro completo,
con todas las URL, sumas SHA-256 y notas, está en `data/fuentes.md`.

::: tabla fuentes-part2
Título: Fuentes de los datos de la Parte 2 y fecha de consulta
Fuente: Elaboración propia a partir de data/fuentes.md (las fechas son la hora local de quien descargó; ver su encabezado).
| Dato | Fuente | Fecha de consulta | Archivo procesado |
|---|---|---|---|
| Coordenadas de las 47 capitales | IGN, Nomenclátor Geográfico de Municipios y Entidades de Población (NGMEP) 202603, entidad «Capital de municipio» (<https://centrodedescargas.cnig.es/CentroDescargas/catalogo.do?Serie=NGMEN>); contraste con IGN IGR Poblaciones | 2026-10-07 | `cities.csv` |
| Red viaria | Extracto de OpenStreetMap de Geofabrik `spain-261001` (datos del 2026-10-01 20:22 UTC; <https://download.geofabrik.de/europe/spain-261001.osm.pbf>) | 2026-10-10 | — |
| Distancias y tiempos (1 081 pares × 2 alternativas) | OSRM v26.10.0, perfil `car.lua`, servidor local con Docker | 2026-10-12 | `rutas.csv` |
| Tarifas de peaje 2026 (56 tramos) | Ministerio de Transportes (autopistas estatales y SEITT), Gobierno de Navarra/Audenasa, Interbiak, Bidegi, Audasa y Aucat | 2026-10-12 | `peajes_tramos.csv` |
| Longitud de los tramos de peaje | Catálogo de la Red de Carreteras del Estado 2025 (Ministerio de Transportes); 11 tramos forales o autonómicos medidos sobre OSM | 2026-10-12 | `peajes_tramos.csv` |
| Precio de la Gasolina 95 E5 | Ministerio para la Transición Ecológica, Geoportal de Gasolineras, endpoint histórico del 01-10-2026 (<https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestresHist/01-10-2026>) | 2026-10-11 | `combustible.json` |
| Vehículo y consumo | Toyota España, configurador y ficha técnica del Corolla Sedán (<https://www.toyota.es/coches/corolla-sedan/build>); respaldo km77 | 2026-10-11 | `vehiculo.yaml` |
:::

### Capitales

Las coordenadas de las 47 capitales de provincia peninsulares provienen del NGMEP del Instituto Geográfico Nacional
(versión 202603). Se toma la entidad «Capital de municipio» (el núcleo urbano), no el centroide del municipio, y se
contrastan con IGR Poblaciones del mismo instituto (diferencia máxima admitida: 2,5 km). Los nombres bilingües y los
homónimos (Córdoba, León, Valencia, Guadalajara) se verificaron a mano. La [[fig:capitales]] muestra el mapa de control
usado para comprobar que cada punto cae dentro de su provincia.

::: figura capitales
Título: Las 47 capitales de provincia de la España peninsular usadas en el problema del viajero
Fuente: Elaboración propia a partir del NGMEP 202603 del IGN (data/processed/cities.csv; detalle de fuentes en data/fuentes.md).
![Mapa de control de las 47 capitales](figures/capitales_control.png)
:::

### Distancias y tiempos

Para cada uno de los $\binom{47}{2} = 1\,081$ pares se piden dos rutas a OSRM: la **rápida** (sin restricciones) y la
**sin peaje** (`exclude=toll`). El servidor público de demostración de OSRM no admite `exclude=toll` (responde
*"Exclude flag combination is not supported"*), así que se montó un servidor propio con Docker sobre el extracto de
España del 1 de octubre.

Dos detalles del motor condicionan la reproducibilidad:

- Con varios hilos, la misma consulta devolvía rutas distintas; con `--threads 1` la respuesta se repite (20 de 20).
- La respuesta depende además del historial de consultas del proceso. Por eso la corrida vigente se hace con el servidor
  recién arrancado y en un orden fijo, lo que la reproduce exactamente (0 de 2 202 rutas distintas).

En esa corrida, 547 pares no tocan ninguna vía de peaje en su ruta rápida, y la alternativa sin peaje coincide con ella.
Hay 26 rutas «sin peaje» que aun así pasan por un tramo de pago (18 por la M-12, 7 por la AP-15 y 1 por la AP-68); no
se descartan: se cobran como cualquier otra.

**Simetría.** El modelo supone $c_{ij} = c_{ji}$ y solo consulta $i \to j$ con $i < j$. Para medir cuánto se aleja la
red real de ese supuesto se consultaron también 20 pares al azar en sentido $j \to i$. La mayor diferencia es la de
Burgos–Santander: 153,2 km frente a 181,5 km (18,4 % en distancia, 6,9 % en tiempo); en los otros 19 pares la diferencia
en distancia no pasa del 2,1 %.

### Peajes

Este es el bloque más difícil, porque OSRM marca las vías de pago pero no da importes. La tabla `peajes_tramos.csv`
tiene 56 tramos encadenados, cada uno con su tarifa para vehículos ligeros vigente el 1 de octubre, su longitud y su
fuente. Cuando el operador publica varias tarifas se fija una: nivel normal en la AP-51 y la AP-61, diurna en la AP-71,
pago en efectivo en las autopistas de SEITT y temporada baja en la AP-7. Los km de 11 tramos forales o autonómicos, que
el Catálogo de la Red de Carreteras del Estado no mide, se midieron sobre la geometría de OSM; son una aproximación.

El peaje de una ruta se calcula como la **suma de tramos**: cada tramo recorrido aporta su tarifa en proporción a los
km recorridos, y la tarifa completa desde el 95 % de su longitud. En autopistas de peaje cerrado esto no siempre
coincide con la tarifa publicada para el recorrido completo, y se decidió no construir una tabla origen–destino. Sobre
15 recorridos de contraste el sesgo va de −18 % a +4 %, y los tres casos fuera de ±5 % usan la AP-6
(A Coruña–Madrid −18,0 %, Madrid–Valladolid −15,6 % y Madrid–Ávila −10,5 %). La [[tab:validacion-peajes]] muestra la
validación de los cinco pares obligatorios.

::: tabla validacion-peajes
Título: Validación del peaje calculado en cinco pares frente al importe oficial (ligeros, 1-oct-2026)
Fuente: Elaboración propia a partir de docs/validacion_peajes_T2.5.md; importes oficiales del Ministerio de Transportes y de la calculadora de Audasa (ver data/fuentes.md).
| Par | Vía de la ruta rápida | Calculado | Oficial | Diferencia |
|---|---|---|---|---|
| Bilbao–Zaragoza | AP-68 (293 km) | 41,50 € | 39,90 € | +1,60 € (+4,0 %) |
| Sevilla–Cádiz | AP-4, libre desde 2020 | 0,00 € | 0,00 € | 0 |
| Madrid–Toledo | A-42 (la AP-41 de pago no se usa) | 0,00 € | 0,00 € | 0 |
| Alicante–Murcia | A-7, A-70 y A-31 | 0,00 € | 0,00 € | 0 |
| A Coruña–Pontevedra | AP-9 (127 km) | 16,35 € | 16,35 € | 0 |
:::

La concesión estatal de la AP-68 vence el 10 de noviembre de 2026. Después de esa fecha cambian sus tarifas (los
tramos de La Rioja y Aragón quedan libres), pero en la fecha de corte toda la autopista cobra, y así se modela.

### Combustible y vehículo

El precio es la **media peninsular de la Gasolina 95 E5** el 1 de octubre de 2026: **1,8318 €/l** sobre 10 171
estaciones (mediana 1,829 €/l). Se excluyen Baleares, Canarias, Ceuta y Melilla porque el recorrido no pasa por ellas.
La media nacional (1,82 €/l, 10 905 estaciones) es más baja porque incluye Canarias.

El vehículo es un **Toyota Corolla Sedán Hybrid 140H (Style Plus e-CVT, año de modelo 2027)**, el único acabado que
Toyota España ofrecía a particulares en la fecha de corte. Su consumo **WLTP combinado** es de **4,6 l/100 km** según
la ficha técnica oficial, y km77 da la misma cifra. Como el consumo real en autopista puede superar el homologado, se
repite el experimento con 5,6 y 6,2 l/100 km, el rango de la fase «extra alta» del WLTP que publica el catálogo de
Toyota de 2023 para el mismo motor.
