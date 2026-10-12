<!--
SECCIÓN: Parte 2 — datos y fuentes · RESPONSABLES: equipo Parte 2 (Jose Miguel, Camila) · ESTADO: borrador inicial.
Enunciado: "Documenten las fuentes de todos los datos (distancias, tiempos, peajes, precios de combustible) con su fecha de
consulta" y el vehículo "con fuente citada". Fuente única de verdad: data/fuentes.md (copiar de ahí, no reescribir de
memoria). Cifras: data/processed/*.json y *.csv. Incluir: fecha de corte 1-oct-2026, OSRM local (por qué no el servidor
público), simetría por construcción y asimetría real medida, peajes por suma de tramos y su validación, AP-68.
-->

## Parte 2: datos del problema

Las coordenadas de las 47 capitales provienen del Nomenclátor Geográfico de Municipios y Entidades de Población del
Instituto Geográfico Nacional (versión 202603), tomando la entidad «Capital de municipio» de cada capital de provincia.
La [[fig:capitales]] muestra el mapa de control usado para verificar que cada punto cae dentro de su provincia.

::: figura capitales
Título: Las 47 capitales de provincia de la España peninsular usadas en el problema del viajero
Fuente: Elaboración propia a partir del NGMEP 202603 del IGN (data/processed/cities.csv; detalle de fuentes en data/fuentes.md).
![Mapa de control de las 47 capitales](figures/capitales_control.png)
:::

<!-- TODO equipo Parte 2: rutas (OSRM local, extracto del 1-oct-2026), peajes (tabla de tramos y validación de los 5 pares),
combustible (Gasolina 95 E5, media peninsular de 10 171 estaciones) y vehículo (Corolla Sedán 140H, WLTP), con una tabla de
fuentes y fechas extraída de data/fuentes.md. -->
