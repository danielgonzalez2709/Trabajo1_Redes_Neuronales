"""Paleta única de las figuras (T4.1; Spec §8). La usan src/viz/theme.py (Plotly) y src/viz/style.py (matplotlib).

Origen: paleta de referencia validada de la guía de visualización de datos (categórica de 8 tonos en orden fijo,
rampa secuencial azul, tinta y superficie). Validación del 12-oct-2026 (validate_palette.js, superficie #fcfcfb):
los 5 tonos de los métodos de la Parte 1 pasan banda de luminosidad, croma, separación para daltonismo
(ΔE mínimo adyacente 9,1 ≥ 8) y visión normal (19,6 ≥ 15). AVISO de contraste < 3:1 en aqua, amarillo y magenta:
toda figura con esos tonos lleva leyenda y el reporte incluye la tabla con los valores (regla de alivio).

Reglas:
- El color sigue a la ENTIDAD (método, algoritmo), nunca a su posición: COLOR_METODO no se reordena.
- Un solo eje y; texto siempre en tinta (TINTA*), nunca en el color de la serie.
- Las figuras se dibujan siempre sobre SUPERFICIE clara (también en el modo oscuro del blog, dentro de una tarjeta).
"""

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_TENUE = "#898781"  # ejes y etiquetas
CUADRICULA = "#e1e0d9"  # línea fina, sólida
EJE = "#c3c2b7"

# Categórica, en el orden fijo de la paleta de referencia.
CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Parte 1 — identificadores del Spec §5.4 → color fijo (aunque un método no aparezca en una figura).
COLOR_METODO = {
    "gdfijo": CATEGORICA[0],
    "gdarmijo": CATEGORICA[1],
    "ea": CATEGORICA[2],
    "pso": CATEGORICA[3],
    "de": CATEGORICA[4],
}
NOMBRE_METODO = {
    "gdfijo": "GD (paso fijo)",
    "gdarmijo": "GD (Armijo)",
    "ea": "Algoritmo evolutivo",
    "pso": "PSO",
    "de": "Evolución diferencial",
}

# Parte 2 — algoritmos; el óptimo exacto es una referencia y se dibuja en tinta secundaria.
COLOR_ALGORITMO = {"aco": CATEGORICA[0], "ga": CATEGORICA[1], "exacto": TINTA_SECUNDARIA}
NOMBRE_ALGORITMO = {"aco": "Colonia de hormigas", "ga": "Algoritmo genético", "exacto": "Óptimo exacto"}

# Mapa de la Parte 2: recorrido y tramos con peaje (colores de la paleta, no de estado).
COLOR_RECORRIDO = CATEGORICA[0]
COLOR_PEAJE = CATEGORICA[1]
COLOR_CIUDAD = TINTA

# Parte 2 — variantes del barrido (convergencia, T4.4). MMAS y AS son ACO: MMAS lleva el color de ACO y AS otro tono
# (además se dibuja con trazo discontinuo para no depender solo del color).
COLOR_SOLVER = {"mmas": COLOR_ALGORITMO["aco"], "as": CATEGORICA[6], "ga": COLOR_ALGORITMO["ga"]}
NOMBRE_SOLVER = {"mmas": "MMAS (colonia de hormigas)", "as": "AS (colonia de hormigas)", "ga": "Algoritmo genético"}

# Parte 2 — componentes del costo (Spec §7.3): los tres primeros tonos de la categórica, en su orden validado;
# peajes coincide con COLOR_PEAJE del mapa.
COLOR_COMPONENTE = {"tiempo": CATEGORICA[0], "peajes": COLOR_PEAJE, "combustible": CATEGORICA[2]}
NOMBRE_COMPONENTE = {"tiempo": "Tiempo (w · horas)", "peajes": "Peajes", "combustible": "Combustible"}

# Secuencial (magnitud: curvas de nivel, mapas de calor): un solo tono, claro → oscuro.
SECUENCIAL_AZUL = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
                   "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

FUENTES = ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]  # sans del sistema (skill apple-design)
ANCHO_LINEA = 2
TAMANO_MARCADOR = 8
