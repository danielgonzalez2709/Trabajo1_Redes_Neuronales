# SPEC — Trabajo 1: Optimización numérica, metaheurística y combinatoria

| | |
|---|---|
| Curso | Redes neuronales y algoritmos bioinspirados — UNAL, Facultad de Minas, 2026-02 |
| Versión | **1.3** — 2026-10-09 (T0.1: `requirements.txt` con Python 3.12; solver exacto PuLP 4.0 + HiGHS; Design System = skill `apple-design`) · 1.2 — 2026-10-09 (§7.2 Bloque 1: NGMEP 202603 como fuente primaria con descarga manual, IGR como contraste, Mérida fuera de la lista de verificación) · 1.1 — 2026-10-01 (decisiones del equipo: fecha de corte, vehículo, dominio de Rosenbrock; propuesta de datos de Camila) |
| Repositorio | https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales |
| Entrega | **Martes 13-oct-2026, 23:59** · Sustentación (probable): jueves 15-oct-2026, 6 p. m. |
| Metodología | Subagent Driven Development (SDD) — ver §12 y `docs/spec/PLAN.md` |
| Estado de cada punto | **[DECIDIDO]** cerrado · **[PENDIENTE]** lo decide el equipo · **[VERIFICAR]** dato que debe confirmarse con fuente primaria antes de usarse |

---

## 0. Reglas de uso de este documento (humanos y subagentes)

1. **Este Spec es la fuente de verdad.** Si el código o un subagente contradice el Spec, gana el Spec (o se cambia el Spec explícitamente con un commit).
2. Los subagentes **no toman decisiones** marcadas como [DECIDIDO] ni resuelven por su cuenta las [PENDIENTE]: **escalan al orquestador**.
3. **Prohibido inventar datos, constantes, tarifas, referencias o resultados.** Si falta un dato: se deja `TODO(dato-faltante)` y se reporta. Un dato inventado es peor que un dato faltante (regla del enunciado para la cacería, aplicada a todo el proyecto).
4. Todo dato del mundo real lleva **fuente (URL) + fecha de consulta** en `data/fuentes.md`.
5. Todo prompt enviado a una IA (incluidos los de los subagentes) se guarda **literal** (§11).

---

## 1. Contexto y objetivo

Comparar métodos de optimización basados en gradiente con metaheurísticas:
- **Parte 1:** funciones de prueba continuas (2D y 3D): descenso por gradiente (GD) vs. algoritmo evolutivo (EA), PSO y evolución diferencial (DE), con **comparación justa** por número de evaluaciones.
- **Parte 2:** TSP cerrado sobre las **47 capitales de provincia de la España peninsular**, con colonias de hormigas (ACO) y algoritmo genético (GA), costo = valor de la hora × tiempo + peajes + combustible, y estudio de cómo cambia la ruta con el valor de la hora.

Entregables (pesos): reporte-blog 25 %, repositorio reproducible 10 %, ejecución y modificación en vivo 10 %, cacería de alucinaciones 15 %, video individual 10 %, sustentación individual 30 %.

### 1.1 Equipo
| Rol | Personas | Responsabilidad |
|---|---|---|
| Equipo Parte 1 | 2 | §6 |
| Equipo Parte 2 | 2 | §7 |
| Puente / Integración / Cacería | 1 | §4, §8, §9, §11, revisión de PR, entendimiento de todos |

---

## 2. Alcance

**Incluido:** todo lo exigido por el enunciado (§6–§11).
**No incluido (salvo que sobre tiempo):** laboratorio Streamlit, video Manim de portada, precio de combustible por provincia, escenario post-AP-68 (§7.1).
**Fuera de alcance:** CMA-ES, OSRM con perfiles personalizados, rutas para vehículos pesados.

---

## 3. Decisiones cerradas [DECIDIDO]

| Tema | Decisión |
|---|---|
| Lenguaje y entorno | Python 3.12, un solo `requirements.txt` con versiones fijas (generado con `pip freeze`, incluye dependencias transitivas). Incluye también las dependencias para **reconstruir datos y figuras** (`openpyxl`, `matplotlib`), aunque la demo no las necesite |
| Solver exacto | **PuLP 4.0 + HiGHS** (`pulp[highs]`). PuLP 4.0 **ya no incluye CBC** y cambió la API: las variables se crean con `problema.add_variable(nombre, cat="Binary")`, no con `LpVariable(..., cat=...)` (ver H-07) |
| Design System | Skill **`apple-design`** (https://github.com/emilkowalski/skills/tree/main/skills/apple-design) — ver §8 |
| Implementación | Algoritmos **desde cero con numpy**. Librerías de optimización (SciPy, pyswarms, DEAP, OR-Tools) **solo para contrastar**, nunca como solución |
| Funciones Parte 1 | **Rosenbrock + Rastrigin**, en 2D y 3D |
| Blog | **Material for MkDocs** (100 % Python), publicado en GitHub Pages |
| Figuras interactivas | **Plotly** con plantilla del Design System |
| GIF obligatorios | **matplotlib** con hoja de estilo del Design System |
| Arquitectura | Los algoritmos **no dibujan**: escriben JSON en `results/data/`; las figuras se construyen después |
| Datos Parte 2 | Cinco bloques (coordenadas, rutas, peajes, combustible, vehículo) — §7.2. Descarga en un **único script con internet**; el experimento solo lee archivos locales |
| Vehículo | **Toyota Corolla Sedán Hybrid 2026, motor 1.8 L (140H)**, híbrido autorrecargable de gasolina — acabado: [PENDIENTE] |
| Fecha de corte de datos | **1-oct-2026** (escenario base) |
| Dominio de Rosenbrock | **[−2.048, 2.048]ⁿ** (justificación en §6.1.1) |
| Combustible | **Gasolina 95 E5**, precio medio nacional en la fecha de corte |
| Git | Rama por equipo, Pull Request revisado por el puente, commits con la cuenta de cada autor |

---

## 4. Arquitectura y estructura del repositorio

```
trabajo1/
├── README.md                     # instalación, comandos, semillas, regeneración de figuras
├── requirements.txt              # versiones fijas
├── run.py                        # punto de entrada único
├── configs/
│   ├── part1/  base.yaml, demo.yaml, <metodo>_<funcion>_<dim>d.yaml
│   └── part2/  base.yaml, demo.yaml, sweep_w.yaml
├── src/
│   ├── common/   config.py, seeds.py, counter.py, results.py, cli.py
│   ├── part1/    functions.py, gd.py, ea.py, pso.py, de.py, experiment.py
│   ├── part2/    costos.py, aco.py, ga.py, local_search.py, exact.py, experiment.py
│   └── viz/      theme.py (Plotly DS), style.py (matplotlib DS), part1_figs.py, part2_figs.py, gifs.py
├── scripts/
│   ├── descargar_datos.py        # ÚNICO script que usa internet (Parte 2)
│   ├── construir_costos.py       # genera matrices procesadas / matriz de costos para un w
│   └── osrm/README.md            # cómo levantar OSRM local (Docker + extracto Geofabrik)
├── data/
│   ├── raw/                      # descargas originales con fecha en el nombre (evidencia)
│   ├── processed/                # cities.csv, rutas_*.csv/npz, peajes_tramos.csv, combustible.json, vehiculo.yaml
│   └── fuentes.md                # tabla: dato | fuente | URL | fecha de consulta | notas
├── results/  data/  tables/
├── media/                        # GIF finales
├── tests/
├── alucinaciones/  registro.md, evidencias/
├── blog/  mkdocs.yml, docs/, hooks/figures.py, references.bib, apa.csl
├── docs/spec/  SPEC.md, PLAN.md
└── .claude/agents/               # definiciones de subagentes (§12)
```

### 4.1 Comandos (contrato con el usuario final)
```bash
python run.py part1 --config configs/part1/demo.yaml            # demo Parte 1 (< 2 min)
python run.py part1 --config configs/part1/base.yaml            # experimento completo Parte 1
python run.py part2 --config configs/part2/demo.yaml --set costo.valor_hora=25
python run.py part2 --config configs/part2/sweep_w.yaml         # barrido del valor de la hora
python run.py figures                                           # figuras interactivas + GIF
mkdocs serve -f blog/mkdocs.yml                                 # blog local
python scripts/descargar_datos.py                               # SOLO para reconstruir datos (usa internet)
```
- Overrides: `--set clave.subclave=valor` (repetible). Nunca hay que editar código para cambiar parámetros.
- Semillas: `rng = np.random.default_rng(base_seed + run_id)`. Prohibido `np.random.seed` global y `random` sin semilla.

---

## 5. Contratos (interfaces)

### 5.1 Parte 1
```python
# src/part1/functions.py
class TestFunction:
    name: str
    dim: int
    bounds: np.ndarray            # shape (dim, 2)
    x_star: np.ndarray
    f_star: float
    def f(self, x: np.ndarray) -> float: ...
    def grad(self, x: np.ndarray) -> np.ndarray: ...

# src/common/counter.py
class CountedProblem:
    """Envuelve una TestFunction. ÚNICO lugar donde se cuentan evaluaciones."""
    n_f: int
    n_grad: int
    def f(self, x) -> float: ...          # n_f += 1
    def grad(self, x) -> np.ndarray: ...  # n_grad += 1
    def eval_equiv(self, k: float) -> float: ...   # n_f + k * n_grad
    def budget_exhausted(self) -> bool: ...

# todos los optimizadores de la Parte 1 (gd.py, ea.py, pso.py, de.py)
def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict
# retorno:
{ "x_best": list, "f_best": float, "n_f": int, "n_grad": int, "eval_equiv": float,
  "history": [{"eval_equiv": float, "f_best": float}],
  "frames":  [{"iter": int, "positions": [[x, y], ...], "best": [x, y]}] }   # solo si dim == 2 y cfg.record_frames
```

### 5.2 Parte 2
```python
# src/part2/costos.py
def cargar_componentes(path="data/processed") -> Componentes   # tiempos, distancias, peajes de ambas alternativas
def matriz_costos(comp: Componentes, valor_hora: float, vehiculo: dict, precio_l: float) -> tuple[np.ndarray, np.ndarray]
    # retorna (C[47,47] en €, alternativa_elegida[47,47] ∈ {"rapida", "sin_peaje"})

# todos los solvers (aco.py, ga.py, exact.py)
def solve(C: np.ndarray, cfg: dict, rng: np.random.Generator) -> dict
{ "tour": list[int],              # permutación de 0..46, sin repetir; el ciclo se cierra implícitamente
  "cost": float, "n_tour_evals": int,
  "history": [{"iter": int, "best_cost": float, "best_tour": list[int]}] }
```

### 5.3 Archivos de datos (Parte 2)
| Archivo | Columnas / contenido |
|---|---|
| `data/processed/cities.csv` | `id, capital, provincia, lat, lon, fuente, fecha_consulta, verificado_manual (bool), nota` |
| `data/processed/rutas.csv` | `i, j, alternativa (rapida/sin_peaje), dist_km, tiempo_h, km_peaje, peaje_eur, vias_peaje (lista), fuente, fecha_extracto_osm` |
| `data/processed/peajes_tramos.csv` | `id, via, desde, hasta, operador, ambito (estatal/SEITT/foral/autonomico), provincia, km, tarifa_ligeros_eur, eur_km, vigente_desde, vigente_hasta, fuente_url, fecha_consulta, nota` |
| `data/processed/combustible.json` | `{producto, precio_medio_eur_l, precio_mediano_eur_l, n_estaciones, fecha, fuente_url, archivo_raw}` |
| `data/processed/vehiculo.yaml` | `{marca, modelo, version, anio, combustible, consumo_wltp_comb_l100, fuente_url, respaldo_url, fecha_consulta}` |
| `data/fuentes.md` | Tabla `dato | fuente | URL | fecha de consulta | notas` (exigida por el enunciado) |

### 5.4 Resultados (para figuras y blog)
```text
results/data/part1/runs/{func}_{dim}d_{method}_seed{k}.json   # retorno de optimize() + config
results/data/part1/summary.json                               # estadísticas por configuración (§6.6)
results/data/part2/sweep_w.json     # [{w, tour, cost, desglose:{tiempo,peajes,combustible}, km_peaje, cambio_vs_anterior, gap_aco, gap_ga}]
results/data/part2/history_{aco|ga}_w{w}.json
results/data/part2/route_geometry.json   # opcional: geometría simplificada por par y alternativa
```

---

## 6. Parte 1 — Optimización numérica

### 6.1 Funciones [DECIDIDO] (constantes [VERIFICAR] contra fuente primaria, p. ej. Surjanovic & Bingham, SFU)
| | Rosenbrock | Rastrigin |
|---|---|---|
| f(x) | Σᵢ₌₁ⁿ⁻¹ [100(xᵢ₊₁ − xᵢ²)² + (1 − xᵢ)²] | 10n + Σᵢ₌₁ⁿ [xᵢ² − 10 cos(2πxᵢ)] |
| ∂f/∂xᵢ | −400xᵢ(xᵢ₊₁ − xᵢ²) − 2(1 − xᵢ) *[si i<n]* + 200(xᵢ − xᵢ₋₁²) *[si i>1]* | 2xᵢ + 20π sin(2πxᵢ) |
| Dominio | **[−2.048, 2.048]ⁿ** [DECIDIDO] | [−5.12, 5.12]ⁿ |
| x*, f* | (1,…,1), 0 | (0,…,0), 0 |

**Aceptación:** `tests/test_gradients.py` compara gradiente analítico vs. diferencias centrales en ≥100 puntos aleatorios por función y dimensión; error relativo < 1e-6. Verificar también f(x*) = f*.

#### 6.1.1 Por qué [−2.048, 2.048]ⁿ para Rosenbrock (experimento del 1-oct-2026)
Se compararon tres dominios usados en la literatura: [−2.048, 2.048]ⁿ (clásico de De Jong [VERIFICAR referencia]),
[−5, 10]ⁿ y [−30, 30]ⁿ. Script y salida en `alucinaciones/evidencias/H-03_rosenbrock_dominio.*`.

| Dominio | L = máx λ_max(∇²f) en el dominio (2D / 3D) | GD η=1e-3, 30 inicios, presupuesto 10 000n (2D) |
|---|---|---|
| **[−2.048, 2.048]ⁿ** | **≈ 5 971 / 6 838** | converge al valle: mediana f ≈ 1.8e-3, peor 1.1e-2 |
| [−5, 10]ⁿ | ≈ 122 133 / 124 267 | **diverge y queda pegado al borde**: mediana f ≈ 8.1e5 |
| [−30, 30]ⁿ | ≈ 1.09e6 / 1.10e6 | diverge: mediana f ≈ 7.6e7 |

Razones de la decisión:
1. **Comparación informativa:** en dominios grandes el GD de paso fijo explota (la curvatura crece como 1200xᵢ²), y la
   comparación mediría "qué tan mal elegimos η", no la geometría. En [−2.048, 2.048]ⁿ el GD llega al valle y se observa
   lo que la discusión debe mostrar: **lentitud por mal condicionamiento** (λ_max/λ_min ≈ 2 508 en x*).
2. **Óptimo interior y descentrado:** x* = (1,…,1) no coincide con el centro del dominio (0,…,0) → no favorece a
   metaheurísticas con sesgo hacia el centro.
3. **Visualización:** el valle en forma de banana se ve completo en las curvas de nivel y en el GIF.
4. **Comparabilidad:** dominio clásico de la literatura de algoritmos evolutivos.

⚠️ **Rastrigin y el sesgo al centro:** su óptimo (0,…,0) **sí** coincide con el centro de [−5.12, 5.12]ⁿ. Discutirlo en el
blog como amenaza a la validez (métodos con recorte a los bordes o inicialización simétrica pueden verse favorecidos).

### 6.2 Reglas de conteo [DECIDIDO]
- Toda evaluación pasa por `CountedProblem`. Los algoritmos **no cuentan a mano**.
- Cuenta la **población/enjambre inicial**. Cuenta cada evaluación en búsquedas lineales (Armijo).
- **Equivalencia:** 1 evaluación de ∇f = **k = 2n** evaluaciones de f (diferencias centrales) — principal. Sensibilidad: repetir la tabla con **k = 1**.
- **Presupuesto:** **10 000 · n** evaluaciones equivalentes por corrida, igual para todos los métodos [VERIFICAR la convención CEC antes de citarla].
- Un algoritmo **se detiene** al agotar el presupuesto (nunca lo excede en más de una generación; si la última generación lo excedería, se trunca).

### 6.3 Descenso por gradiente
- **GD paso fijo:** xₖ₊₁ = Π(xₖ − η∇f(xₖ)), Π = proyección al dominio (recorte).
- **GD + Armijo (backtracking):** η ← β·η hasta f(x − η∇f) ≤ f(x) − c·η‖∇f‖²; parámetros η₀ = 1, β = 0.5, c = 1e-4.
- **Elección de η (corregida el 1-oct-2026, ver H-03):**
  - Garantía global para funciones L-suaves (con proyección sobre un convexo): η ≤ 1/L asegura descenso monótono.
  - **Rastrigin:** ∇²f = diag(2 + 40π² cos 2πxᵢ) → L = 2 + 40π² ≈ 396.8 en todo ℝⁿ → η ≤ 2.52e-3. **η = 2e-3 tiene garantía global.**
  - **Rosenbrock en [−2.048, 2.048]ⁿ:** L ≈ 5 971 (2D) / 6 838 (3D) → η ≤ 1.7e-4 / 1.5e-4. En x*, λ_max ≈ 1 001.6 → η < 2/λ_max ≈ 2e-3
    solo garantiza estabilidad **local**. Experimentalmente η = 1e-3 converge mejor que η = 1/L (mediana 1.8e-3 vs 1.3e-1 en 2D)
    porque la trayectoria entra rápido al valle, donde la curvatura es menor. **Se usa η = 1e-3 declarando que no hay garantía
    global** y se reporta η = 1/L como análisis de sensibilidad. La variante Armijo resuelve la elección automáticamente.
- Punto inicial: uniforme en el dominio. Parada: ‖∇f‖ < 1e-8 o presupuesto agotado.

### 6.4 Metaheurísticas (parámetros por defecto, todos sobrescribibles por config)
| Algoritmo | Ecuaciones | Parámetros por defecto |
|---|---|---|
| **EA** (GA codificación real) | Torneo k=3; cruce BLX-α; mutación gaussiana N(0, σ²) por gen con prob. pm; elitismo | pop=40, pc=0.9, α=0.5, σ=0.1·rango, pm=1/n, élites=2 |
| **PSO** (gbest, inercia) | v ← w·v + c₁r₁(pbest − x) + c₂r₂(gbest − x); x ← x + v | N=30, w=0.7298, c₁=c₂=1.49618 [VERIFICAR Clerc & Kennedy, 2002], v_max=0.2·rango; fuera del dominio: recortar x y poner v=0 en esa componente |
| **DE/rand/1/bin** | v = x_r1 + F(x_r2 − x_r3); cruce binomial con CR y j_rand; selección codiciosa | NP=30, F=0.7, CR=0.9; fuera del dominio: reinicio aleatorio de la componente |

### 6.5 Diseño experimental
- 2 funciones × 2 dimensiones × 5 métodos (GD fijo, GD Armijo, EA, PSO, DE) = 20 configuraciones × **30 corridas** (semillas 0–29, mismas para todos los métodos).
- Umbral de éxito: **f − f* ≤ 1e-4** (principal); reportar también 1e-2 y 1e-6.

### 6.6 Métricas (`summary.json` y tablas del blog)
Por configuración: media, desviación estándar, mediana, mejor, peor de f_final; `n_f` y `n_grad` medios **por separado**; evaluaciones equivalentes (k=2n y k=1); tasa de éxito; evaluaciones hasta el éxito (media en corridas exitosas).

### 6.7 Figuras Parte 1
1. Curvas de nivel de cada función (2D) — Plotly.
2. Curvas de convergencia (mediana + rango intercuartílico) vs. evaluaciones equivalentes, escala log — Plotly.
3. Diagramas de caja de f_final por método — Plotly.
4. GIF de GD (Rosenbrock y Rastrigin, 2D) y GIF de PSO en Rastrigin 2D — matplotlib.
5. Interactiva: deslizador de η para GD en Rosenbrock; superficie 3D de Rastrigin con el enjambre (opcional).

### 6.8 Demo Parte 1 (< 2 min)
`configs/part1/demo.yaml`: Rastrigin 2D, PSO vs GD, 5 corridas → tabla en consola + figura de trayectoria.

---

## 7. Parte 2 — TSP por España

### 7.1 Escenario y fecha de corte [PENDIENTE: confirmar]
- **[DECIDIDO] Fecha de corte 1-oct-2026**, escenario **"base"** = red de peajes vigente en esa fecha (vigente también el día de la entrega y de la sustentación).
- ⚠️ **AP-68 (Bilbao–Zaragoza):** según el Ministerio de Transportes, deja de ser de peaje el **11-nov-2026** (la concesión vence el 10-nov). **No queda toda gratis:** los tramos de **Álava y Bizkaia seguirán cobrando** (gestionados por las diputaciones forales, con tarifas rebajadas); La Rioja, Navarra y Aragón quedan libres para turismos. Fuente de prensa reportó que Logroño–Bilbao pasaría de 19,60 € a 6,65 € [VERIFICAR con fuente oficial y la resolución del BOE núm. 225 de 11-sep-2026].
- **Extensión opcional:** `peajes.escenario: base | post_ap68` en la config → excelente para la modificación en vivo ("¿qué pasa con la ruta después del 11 de noviembre?").

### 7.2 Recolección de datos — cinco bloques

> Todo se descarga **una sola vez** con `scripts/descargar_datos.py` (o pasos manuales documentados) a `data/raw/` con fecha en el nombre; se procesa a `data/processed/`; se registra en `data/fuentes.md`.

#### Bloque 1 — Coordenadas de las 47 capitales
- **[DECIDIDO 8-oct-2026] Fuente primaria:** IGN, Nomenclátor Geográfico de Municipios y Entidades de Población (NGMEP), versión 202603: fila `TIPO = "Capital de municipio"` de `ENTIDADES.csv`. **Contraste:** IGN IGR Poblaciones (`api-features.ign.es`, colección `nuc`), umbral 2,5 km. OpenStreetMap / Nominatim **solo como control** (devuelve provincias y homónimos; no sirve como fuente de coordenadas).
- **Excepción a la descarga por script:** el Centro de Descargas del CNIG exige reCAPTCHA, así que el NGMEP se descarga **a mano** y se guarda en `data/raw/BD_Municipios-Entidades/` (carpeta sin fecha en el nombre; fecha y SHA-256 en `data/fuentes.md`). Se versionan los CSV y la Memoria; el `.mdb` (misma base en formato Access) no.
- Usar la coordenada de la **entidad de población** (núcleo urbano) de la capital, no el centroide del municipio.
- **Verificación manual obligatoria** (columna `verificado_manual`): nombres bilingües o ambiguos — Vitoria-Gasteiz, A Coruña, Ourense, Girona, Lleida, Castelló de la Plana, Donostia/San Sebastián, Pamplona/Iruña — y homónimos fuera de España (Córdoba, León, Valencia, Guadalajara). *(v1.2: se retira Mérida, que es capital autonómica de Extremadura pero no de provincia; la de Badajoz es Badajoz.)* Confirmada por Jose Miguel Pulgarin el 8-oct-2026.
- **Aceptación:** 47 filas; mapa de control con los 47 puntos, cada uno dentro de su provincia; excluidas Palma, Las Palmas de G.C., Santa Cruz de Tenerife, Ceuta y Melilla.

#### Bloque 2 — Distancias y tiempos (OSRM)
- **Motor:** OSRM con datos de OpenStreetMap.
- ⚠️ **El servidor público de demostración NO admite `exclude=toll`**: responde `"Exclude flag combination is not supported."` (verificado el 29-sep-2026). Por tanto:
  - 🟢 **OSRM local con Docker** + extracto de España de **Geofabrik** (documentar fecha del extracto). El perfil de coche por defecto declara `excludable = {toll}, {motorway}, {ferry}` y la clase `toll` (verificado en `profiles/car.lua`, 1-oct-2026). Instrucciones en `scripts/osrm/README.md`. [PENDIENTE: ¿quién tiene Docker y RAM suficiente?]
  - **Respaldo:** openrouteservice *Directions* con `avoid_features: ["tollways"]` (API key gratuita; 2 000 peticiones/día, 40/min).
- **Para cada par (i, j), i < j (1 081 pares) y cada alternativa:**
  - `rapida`: ruta sin restricciones.
  - `sin_peaje`: ruta con `exclude=toll`.
  - Guardar: distancia, duración, pasos (`ref`, distancia, clases, coordenadas) y geometría simplificada.
- **Simetría:** se asume c_ij = c_ji (se consulta i→j). **Comprobación:** consultar j→i para 20 pares aleatorios y reportar la diferencia máxima en el blog.
- **Aceptación:** 1 081 × 2 rutas sin errores; si `sin_peaje` coincide con `rapida` (no hay peaje en la ruta), se marca y se reutiliza.

#### Bloque 3 — Peajes (el bloque más difícil)
- **Fuentes oficiales:**
  - Estatales en concesión y SEITT: listado y tarifas 2026 del **Ministerio de Transportes y Movilidad Sostenible**. Tarifas 2026: +3,64 % a +4,68 % (concesiones) y +2 % (SEITT: R-2, R-3/R-5, R-4, M-12, AP-7 Cartagena–Vera, AP-36, AP-41).
  - Forales/autonómicos: Bidegi (Gipuzkoa), Interbiak (Bizkaia), Diputación Foral de Álava; Galicia y otros operadores autonómicos [VERIFICAR la lista completa de tramos que afectan rutas entre capitales].
- **Tabla** `peajes_tramos.csv` (§5.3) con tarifa para **vehículos ligeros**, fuente y fecha.
- **Cálculo por ruta (aproximación documentada):**
  1. De los pasos de OSRM, tomar los que tienen clase `toll` [VERIFICAR que el OSRM local la marca] y su `ref` (nombre de vía) y ubicación.
  2. Asignar cada tramo recorrido a una fila de `peajes_tramos.csv` por vía **y** ubicación (provincia/tramo) — **no** por el prefijo del nombre: varias "AP-" ya son gratuitas (AP-1, AP-2, AP-4 y tramos de la AP-7) y conservan el nombre.
  3. Peaje del par = Σ km recorridos en cada tramo × €/km del tramo (o tarifa completa si se recorre el tramo entero).
- **Validación (obligatoria):** comparar con el listado oficial / calculadora del operador al menos estos pares: **Bilbao–Zaragoza (AP-68), Sevilla–Cádiz (AP-4, debe dar 0 €), Madrid–Toledo (AP-41 vs. A-42), Alicante–Murcia (AP-7), A Coruña–Pontevedra (AP-9)**. Reportar la diferencia en el blog. Las etiquetas `toll=yes` de OSM pueden estar desactualizadas: cualquier discrepancia se documenta (y es candidata a hallazgo).

#### Bloque 4 — Precio del combustible
- **Fuente:** Geoportal de Gasolineras / servicio REST del Ministerio para la Transición Ecológica (`sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/`; tiene endpoint histórico por fecha).
- **Producto:** Gasolina 95 E5. Descarga única en la fecha de corte; guardar el JSON crudo con la fecha en el nombre.
- **Modelo [DECIDIDO]:** precio **medio nacional** (reportar también la mediana y el nº de estaciones). Por provincia: fuera de alcance.

#### Bloque 5 — Vehículo
- **[DECIDIDO] Toyota Corolla Sedán Hybrid 2026, motor 1.8 L (140H)**, híbrido autorrecargable de gasolina. Acabado [PENDIENTE]:
  el consumo WLTP cambia por versión. Los valores de 4,4–4,7 l/100 km del documento del equipo Parte 2 corresponden a otras
  versiones/carrocerías → **tomar el dato de la ficha del Sedán** [VERIFICAR].
- Consumo **WLTP combinado** (l/100 km) de la **ficha técnica oficial de Toyota España**; **km77** como respaldo; fecha de consulta.
- **Sensibilidad:** usar también el consumo de la fase WLTP **"extra alta"** (autopista), si la ficha la publica.
- Por qué este vehículo (propuesta del equipo Parte 2): consumo homologado bajo, apto para viajes largos, información oficial
  abundante. **Descartados:** eléctricos (los tiempos de recarga distorsionan el costo del tiempo), híbridos enchufables (su
  WLTP supone batería cargada).
- ⚠️ No usar valores NEDC ni fichas de otros países (las versiones cambian entre mercados). Discutir en el blog que el consumo
  real en autopista puede superar el combinado homologado (simplificación declarada).

### 7.3 Modelo de costo [DECIDIDO]
Para cada par y alternativa a ∈ {rapida, sin_peaje}:

  **c_ij^a(w) = w · t_ij^a + P_ij^a + d_ij^a · (consumo / 100) · precio_l**

  **c_ij(w) = mín( c_ij^rapida(w), c_ij^sin_peaje(w) )**

- w = valor de la hora (€/h). Se guarda qué alternativa se eligió en cada par (para colorear el mapa).
- **Aceptación** (`tests/test_cost.py`): un par calculado a mano coincide; con w = 0 nunca se elige una alternativa con peaje si existe otra más barata en combustible; c es simétrica y de diagonal 0.

### 7.4 Algoritmos
| Algoritmo | Especificación | Parámetros por defecto |
|---|---|---|
| **Ant System → MMAS** | p_ij ∝ τ_ij^α · η_ij^β, η = 1/c; evaporación τ ← (1−ρ)τ + Δτ; MMAS: solo la mejor hormiga deposita, límites τ_min/τ_max | m=47, α=1, β=3, ρ=0.2, 300 iteraciones |
| **GA** | Permutación; torneo; cruce **OX**; mutación por **inversión** + intercambio; elitismo | pop=150, gen=1 000, pc=0.9, pm=0.2, torneo k=4, élites=2 |
| **2-opt** (opcional) | Mejora local sobre la mejor solución; reportar con y sin | — |
| **Exacto (referencia)** | Formulación DFJ con **PuLP 4.0 + HiGHS**, eliminación iterativa de subtours | — |

- **Aceptación:** `tests/test_tsp_operators.py` — 10 000 cruces/mutaciones aleatorias producen siempre permutaciones válidas; `tests/test_exact_small.py` — con 8 ciudades, el exacto coincide con fuerza bruta.
- **Comparación justa ACO vs GA:** mismo número de **recorridos evaluados**.

### 7.5 Experimentos Parte 2
- Barrido w ∈ {0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100} €/h (más denso en 0–50, rango sugerido por el equipo Parte 2). Para cada w: exacto + ACO (10 corridas) + GA (10 corridas) → mejor, media, desviación, **gap % vs. óptimo**.
- **Umbral:** donde el recorrido óptimo cambie entre dos w consecutivos, bisección con el solver exacto hasta resolución de 0,5 €/h → responde "¿a partir de qué valor cambia la ruta?".
- Referencias contextuales para w [VERIFICAR]: ganancia media por hora en España (INE) o salario de un comercial; valores del tiempo usados por el Ministerio de Transportes en la evaluación de proyectos de carreteras.

### 7.6 Figuras Parte 2
1. Mapa con las 47 capitales (control de coordenadas).
2. Mapa interactivo (Plotly) con deslizador de w: recorrido óptimo, tramos con peaje coloreados.
3. Costo total desglosado (tiempo / peajes / combustible) vs. w.
4. Convergencia ACO vs GA (gap vs. recorridos evaluados).
5. **GIF** (matplotlib) de la evolución de la mejor ruta sobre el mapa de España.

### 7.7 Demo Parte 2 (< 2 min)
`configs/part2/demo.yaml`: ACO, w=25, 100 iteraciones → costo, gap vs. óptimo precalculado, figura del recorrido.

---

## 8. Visualización y blog [DECIDIDO]
- **Material for MkDocs** (en modo mantenimiento con correcciones hasta 5-nov-2026: suficiente para el proyecto).
- Ecuaciones: `pymdownx.arithmatex` + KaTeX. Bibliografía: `mkdocs-bibtex` + `apa.csl` (APA 7) [VERIFICAR si requiere pandoc → `pypandoc_binary`].
- **Hook `blog/hooks/figures.py`:** numera figuras y tablas en orden, resuelve referencias `[[fig:id]]` → "Figura N", y **hace fallar el build** si una figura/tabla no se cita o una cita no existe.
- **Design System [DECIDIDO 9-oct-2026]:** skill **`apple-design`** de Emil Kowalski (basada en las charlas de diseño de Apple, WWDC):
  https://github.com/emilkowalski/skills/tree/main/skills/apple-design. **No se copia al repositorio** (no declara licencia):
  cada integrante la instala localmente en Claude Code. Se traduce a `src/viz/theme.py` (Plotly), `src/viz/style.py`
  (matplotlib) y `blog/docs/stylesheets/ds.css`. Qué tomamos de ella:
  - **Tipografía:** fuente del sistema (`system-ui`), interlineado mayor en texto (≈1.5) y apretado en títulos (≈1.05),
    tracking negativo en títulos grandes (≈ −0.02em) y ≈0 en el cuerpo; jerarquía por peso + tamaño + interlineado; unidades `rem`.
  - **Materiales:** barra superior translúcida (`backdrop-filter: blur()` + fondo semitransparente) con el contenido desplazándose
    debajo; difuminado en los bordes de desplazamiento en lugar de divisores duros.
  - **Interacción en figuras interactivas:** respuesta continua mientras se arrastra un deslizador (no solo al soltar), nada bloquea la
    entrada durante una transición, transiciones cortas y sin rebote.
  - **Accesibilidad:** respetar `prefers-reduced-motion` (sustituir animaciones por fundidos), `prefers-reduced-transparency` y
    `prefers-contrast: more`; evitar movimiento a pantalla completa y cambios bruscos de brillo (relevante en los GIF).
  - **Principios:** propósito, simplicidad (no minimalismo), etiquetas específicas, agrupación por proximidad.
  - ⚠️ La skill **no define paleta de colores**: la paleta (neutros + un color de acento + colores por método/algoritmo) se define en
    T4.1 y se verifica el contraste en modo claro y oscuro.
- **Secciones obligatorias del blog:** introducción; fundamentación matemática (funciones, dominio, mínimo; TSP; ecuaciones de cada algoritmo); metodología; datos y fuentes; resultados; discusión; uso de IA (prompts principales e impacto); cacería de la alucinación; referencias APA; enlace al repositorio.

---

## 9. Requisitos no funcionales y criterios de aceptación globales
| Requisito | Criterio verificable |
|---|---|
| Reproducibilidad | Misma semilla → mismos resultados bit a bit (`tests/test_reproducibility.py`) |
| Sin internet en experimentos | `run.py part1/part2/figures` pasan con red deshabilitada (prueba que bloquea `socket`) |
| Un comando por experimento | Comandos de §4.1 funcionan desde un clon limpio |
| Parámetros sin editar código | Todo parámetro de §6–§7 es sobrescribible con `--set` |
| Demo < 2 min | Medido en una máquina distinta a la de desarrollo |
| Figuras regenerables | `python run.py figures` reconstruye todas las figuras y GIF desde `results/data/` |
| Historial real | Commits frecuentes de las 5 cuentas |
| Clon limpio | Lun 12-oct: clonar, crear venv, instalar, correr demos, construir blog |

---

## 10. Pruebas mínimas
`test_gradients.py`, `test_counter.py` (PSO con N partículas y T iteraciones reporta exactamente N·(T+1) evaluaciones de f), `test_budget.py`, `test_reproducibility.py`, `test_no_network.py`, `test_cost.py`, `test_tsp_operators.py`, `test_exact_small.py`, `test_data_integrity.py` (47 ciudades, matrices 47×47 simétricas sin NaN, todas las tarifas con fuente y fecha).

---

## 11. Cacería de la alucinación (15 %)
- **Registro:** `alucinaciones/registro.md` (plantilla incluida) + `alucinaciones/evidencias/`.
- **Obligatorio:** guardar prompts literales — conversaciones con IA, este Spec, y los prompts que el orquestador envía a cada subagente (`alucinaciones/prompts/`).
- **Cada hallazgo:** prompt literal · respuesta relevante · cómo se sospechó · evidencia (derivación / experimento / fuente primaria) · corrección · lección aprendida.
- **Meta:** ≥5 hallazgos genuinos en ≥3 categorías (Matemáticas, Código, Datos, Bibliografía, Conceptos). **Nunca inventar.**
- **Verificaciones planificadas:** gradientes; constantes y dominios; conteo de evaluaciones; variante por defecto de DE en SciPy (`best1bin` + `polish=True`, verificado en su documentación); permutaciones válidas; peajes Bilbao–Zaragoza y Sevilla–Cádiz preguntados a una IA vs. Ministerio; estado AP-68; WLTP vs NEDC; coordenadas ambiguas; DOI de cada referencia; afirmaciones de convergencia ("¿PSO/ACO garantizan el óptimo?", "¿Rosenbrock es convexa?"); gap real vs. "óptimo" declarado.

---

## 12. Subagent Driven Development

### 12.1 Flujo por tarea (del `PLAN.md`)
```
Orquestador ──► Implementador ──► Revisor de cumplimiento del Spec ──► Revisor de calidad ──► (si toca) Verificador especializado ──► PR ──► Puente (humano) aprueba ──► merge
                    ▲                         │ falla                         │ falla
                    └─────────────────────────┴───────────────────────────────┘
```
- Una tarea = un subagente implementador **nuevo** con contexto mínimo y preciso: la sección del Spec, los contratos (§5) y la prueba de aceptación.
- **Primero la prueba, luego el código** (TDD) en todas las tareas de código.
- Ningún subagente modifica el Spec ni los contratos; si los cree incorrectos, **escala**.

### 12.2 Agentes (definiciones en `.claude/agents/`)
| Agente | Tipo | Cuándo interviene |
|---|---|---|
| **orquestador** | Núcleo (sesión principal) | Reparte tareas del PLAN, arma el contexto de cada subagente, guarda prompts, decide escalamientos |
| **implementador** | Núcleo | Escribe prueba + código de una tarea |
| **revisor-spec** | Núcleo | ¿Hace exactamente lo que dice el Spec (ni más ni menos)? ¿Respeta contratos y reglas de conteo? |
| **revisor-calidad** | Núcleo | Legibilidad, estructura, pruebas, rendimiento, estilo |
| **verificador-matematico** | Especializado | Toda tarea con fórmulas: funciones, gradientes, ecuaciones de actualización, modelo de costo, η justificada |
| **curador-datos** | Especializado | Bloques 1–5 de la Parte 2: descarga, procesamiento, `fuentes.md`; nunca inventa un número |
| **cazador-alucinaciones** | Especializado | Verificación adversarial de afirmaciones (datos, referencias, conceptos) contra fuentes primarias; alimenta el registro |
| **analista-experimentos** | Especializado | Corre experimentos, genera `summary.json`/tablas, vigila la justicia de la comparación |
| **auditor-reproducibilidad** | Especializado | Clon limpio, entorno nuevo, demos < 2 min, sin internet, semillas |
| **redactor-tecnico** | Especializado | Secciones del blog a partir de `results/` (sin inventar cifras), APA, figuras citadas |
| **tutor-sustentacion** | Especializado | Fichas de explicación, preguntas probables y predicciones para que **los 5** entiendan cada módulo |

---

## 13. Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| OSRM local no se logra montar a tiempo | Respaldo ORS (§7.2 bloque 2); decidir a más tardar el **sáb 3-oct** |
| Peajes incompletos o mal asignados | Tabla curada + validación de 5 pares + aproximación documentada |
| Conteo de evaluaciones inconsistente | Contador único + `test_counter.py` |
| Subagentes que "rellenan" datos o fórmulas | Regla §0.3, verificador matemático, curador de datos, cazador |
| Alguien no entiende un módulo en la sustentación | tutor-sustentacion + explicación de cada PR al puente + simulacro mié 14-oct |
| Demo > 2 min | Configs `demo.yaml` medidas en otra máquina |
| Design System llega tarde | Figuras de trabajo con estilo por defecto; tema final se aplica al final (las figuras se regeneran) |

---

## 14. Pendientes [PENDIENTE]
1. ~~Dominio de Rosenbrock~~ → [−2.048, 2.048]ⁿ ✅
2. ~~Fecha de corte~~ → 1-oct-2026 ✅ · ¿Se hace el escenario opcional `post_ap68`?
3. Quién monta OSRM local (Docker, RAM suficiente) o si se usa el respaldo ORS (decidir a más tardar sáb 3-oct).
4. ~~Carrocería~~ → Sedán ✅ · Acabado del Corolla Sedán 1.8 L (140H) (el curador lo propone según la ficha oficial).
5. ~~Design System~~ → skill `apple-design` ✅ (falta la paleta de colores, T4.1).
6. Fecha/hora confirmada de la sustentación.

---

## 15. Fuentes usadas para este Spec (consultadas 29-sep y 1-oct-2026)
- Gobierno de España — Peajes y viñetas: https://administracion.gob.es/pag_Home/Tu-espacio-europeo/derechos-obligaciones/ciudadanos/vehiculos/normas-trafico-viales/peajes-vinetas
- Bolsamanía — actualización de peajes 2026: https://www.bolsamania.com/noticias/empresas/economia--transportes-aprueba-la-actualizacion-de-los-peajes-de-las-autopistas-para-2026-con-un-alza-de-hasta-el-468--21439215.html
- Motorpasión — fin del peaje AP-68: https://www.motorpasion.com/industria/peajes-caros-este-2026-estas-dos-autopistas-pasan-a-ser-gratis-dejaremos-pagar-40-euros-para-ir-zaragoza-a-bilbao
- Xataka (7-ago-2026) — AP-68, tramos forales: https://www.xataka.com/movilidad/segundo-peaje-barreras-espana-llega-sorpresa-ap-68-bilbao-solo-tendra-descuento-20
- BOE núm. 225, 11-sep-2026, disposición 19039 (Ministerio de Transportes) [VERIFICAR contenido]: https://www.boe.es/boe/dias/2026/09/11/pdfs/BOE-A-2026-19039.pdf
- OSRM — API HTTP: https://project-osrm.org/docs/v26.6.1/http · perfil de coche: https://github.com/Project-OSRM/osrm-backend/blob/master/profiles/car.lua
- datos.gob.es — precio de carburantes: https://datos.gob.es/en/catalogo/e05068001-precio-de-carburantes-en-las-gasolineras-espanolas
- SciPy — `differential_evolution`: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html
- Material for MkDocs (modo mantenimiento): https://github.com/squidfunk/mkdocs-material/issues/8523 · mkdocs-bibtex: https://pypi.org/project/mkdocs-bibtex/2.16.1
- Propuesta de recolección de datos del equipo Parte 2 y documento "Trabajo 1 – Punto 2 (TSP por España): decisiones y fuentes de datos" (Camila, 1-oct-2026).
- km77 — Hyundai Tucson HEV 239 CV (citado por el equipo Parte 2 para la comparación de vehículos): https://www.km77.com/coches/hyundai/tucson/2024/estandar/hev/tucson-klass-16-t-gdi-hev-239-cv/datos
- Menorca.info — subida de peajes 2026 y fecha de la AP-68: https://www.menorca.info/actualidad/nacional/2026/01/11/2546999/subida-llega-2026-para-autopistas-peaje-dependientes-del-gobierno.html
