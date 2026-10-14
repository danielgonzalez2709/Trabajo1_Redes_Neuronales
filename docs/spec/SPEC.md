# SPEC — Trabajo 1: Optimización numérica, metaheurística y combinatoria

| | |
|---|---|
| Curso | Redes neuronales y algoritmos bioinspirados — UNAL, Facultad de Minas, 2026-02 |
| Versión | **1.21** — 2026-10-13 (Daniel aprueba las 23 líneas que esperaban su aprobación: T1.1–T1.8, refactor común, HPO, figuras y GIF de la Parte 1; pasan a [DECIDIDO v1.21]) · 1.20 — 2026-10-13 (T3.2 [DECIDIDO, Daniel]: el exacto se implementa como verificación (`src/part2/exact.py`, DFJ con PuLP 4 + HiGHS, gap 0) y los umbrales que se reportan son los del óptimo (`scripts/umbrales_exactos.py` → `results/data/part2/umbrales_exactos.json`); §7.4 y §7.5) · 1.19 — 2026-10-13 (T3.7b [DECIDIDO, Jose Miguel]: la demo de la Parte 2 sube de 100 a 1 000 iteraciones de MMAS, a partir de la revisión del PR #11, para mostrar un gap menor en vivo; §7.7) · 1.18 — 2026-10-13 (merge de la Parte 1: §6.4 con el EA en esquema de clase —propuesta en `docs/spec/propuestas/CAMBIO-EA.md`, que la llamaba "1.4"; en la rama de la Parte 1 figuró como "1.14" y luego "1.16"; `main` ya usaba 1.14 a 1.17— y §6.3 con la configuración del GD y la condición de Armijo sobre el punto proyectado, ambas [DECIDIDO v1.21, Daniel, 13-oct]; más las líneas [PENDIENTE] de §4 y §5.1 del refactor T1.6b) · 1.17 — 2026-10-13 (T3.7 [DECIDIDO, Jose Miguel]: el gap de la demo se mide contra el **mejor costo conocido** en w = 25 del barrido de T3.6, no contra un óptimo probado; clave `experimento.referencia_gap`; MMAS con 10 corridas; salida `demo.json` + figura sin versionar, §7.7 y §5.4) · 1.16 — 2026-10-12 (T3.6 [DECIDIDO, Jose Miguel]: presupuesto común de 51 654 recorridos, ACO 1 099 iteraciones y GA 348 generaciones, §7.4; umbral de w por envolvente de recorridos candidatos en lugar de bisección con el exacto, §7.5; claves opcionales `consumo_l100` y `precio_l` en `base.yaml`, §7.5) · 1.15 — 2026-10-12 (T3.4: GA con el esquema clásico de §7.4 [DECIDIDO], §7.4.2: mutación 50/50, conteo de recorridos, población inicial con el vecino más cercano; notebooks del profesor solo como referencia) · 1.14 — 2026-10-12 (T3.3: ACO según las notas del profesor [DECIDIDO], §7.4; T3.2 exacto pasa a opcional) · 1.13 — 2026-10-12 (T3.1: `Componentes` = dataclass `frozen` de seis matrices [DECIDIDO], §5.2) · 1.12 — 2026-10-12 (T3.1: desempate de §7.3 fijado en `rapida` [DECIDIDO]) · 1.11 — 2026-10-12 (T3.1: criterios de aceptación de §7.3 reformulados; con w = 0 se elige la alternativa de menor peaje + combustible, y la simetría se comprueba contra `rutas.csv` porque la matriz se arma por espejo) · 1.10 — 2026-10-12 (T2.5: asignación de peajes por suma de tramos [DECIDIDO]; cadenas y anclas como archivos laterales de `peajes_tramos.csv`; 5 archivos nuevos en §5.3) · 1.9 — 2026-10-12 (T2.4: AP-68 después del 10-nov corregida con fuentes oficiales y BOE núm. 225 recolocado en §7.1; en §7.2 Bloque 3: una tarifa por tramo, km de OSM como aproximación, peaje cerrado y Catálogo RCE sin versionar) · 1.8 — 2026-10-12 (OSRM con `--threads 1` por determinismo; `exclude=toll` no garantiza una ruta sin peaje: las `sin_peaje` con clase `toll` se reportan y T2.5 cobra el peaje; nueva corrida de T2.3) · 1.7 — 2026-10-11 (vehículo: acabado **Style Plus 140H e-CVT, año de modelo MY27** vigente en la fecha de corte; `anio_modelo` en el contrato de `vehiculo.yaml`) · 1.6 — 2026-10-11 (enunciado literal de la Parte 2 y punto "Todo debe correr en vivo" de la rúbrica en §1.2–§1.3; combustible: media **peninsular** en lugar de nacional, clave `ambito` y `combustible_resumen.json` en §5.3; endpoint histórico del Ministerio en §7.2 Bloque 4) · 1.5 — 2026-10-11 (T2.3: criterio de par sin peaje; `rutas_resumen.json` y `rutas_pasos_peaje.csv` en §5.3; los crudos de rutas OSRM no se versionan) · 1.4 — 2026-10-11 (integración de T2.0/T2.2: OSRM local con Docker [DECIDIDO]; ORS queda solo como contingencia) · 1.3 — 2026-10-09 (T0.1: `requirements.txt` con Python 3.12; solver exacto PuLP 4.0 + HiGHS; Design System = skill `apple-design`) · 1.2 — 2026-10-09 (§7.2 Bloque 1: NGMEP 202603 como fuente primaria con descarga manual, IGR como contraste, Mérida fuera de la lista de verificación) · 1.1 — 2026-10-01 (decisiones del equipo: fecha de corte, vehículo, dominio de Rosenbrock; propuesta de datos de Camila) |
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

### 1.2 Enunciado literal — Parte 2 (añadido en v1.6)

Texto del enunciado del curso, copiado sin cambios. Si este Spec lo contradice, gana el enunciado y se corrige el Spec.

> **Parte 2: Optimización combinatoria (¡y olé!)**
>
> Un vendedor debe recorrer las 47 capitales de provincia de la España peninsular (se excluyen Palma, Las Palmas de Gran Canaria y Santa Cruz de Tenerife por ser insulares, y Ceuta y Melilla por no ser provincias ni accesibles por carretera desde la península). El recorrido es cerrado: el vendedor vuelve a la ciudad de salida.
>
> 1. Encuentren el orden óptimo del recorrido usando colonias de hormigas y algoritmos genéticos.
> 2. El costo de desplazamiento entre dos ciudades es la suma de:
>    - el valor de la hora del vendedor multiplicado por el tiempo de viaje. Este valor es un parámetro que deben estudiar: ¿cambia la ruta óptima al variarlo? ¿a partir de qué valor?
>    - el costo de los peajes en el trayecto por carretera.
>    - el costo del combustible, según el vehículo que el equipo elija (modelo, consumo homologado y tipo de combustible, con fuente citada).
> 3. Documenten las fuentes de todos los datos (distancias, tiempos, peajes, precios de combustible) con su fecha de consulta. Tengan en cuenta que la red de autopistas de peaje en España ha cambiado mucho en los últimos años, por lo que la información desactualizada es un riesgo real.
> 4. Representen con un GIF animado o un video cómo evoluciona la mejor solución, dibujando el recorrido sobre el mapa de España.

### 1.3 Rúbrica literal — "Todo debe correr en vivo" (añadido en v1.6)

Punto de la rúbrica de evaluación, copiado sin cambios. Sus criterios verificables están en §9.

> **Todo debe correr en vivo**
>
> Durante la sustentación el equipo ejecutará su código frente al profesor. Por eso:
> - Cada experimento principal debe lanzarse con un solo comando.
> - Los parámetros (tasa de aprendizaje, tamaño de población, tasa de evaporación, valor de la hora, etc.) deben poder cambiarse desde la línea de comandos o un archivo de configuración, sin editar el código fuente.
> - Una corrida de demostración debe tardar menos de dos minutos.
> - Antes de la sustentación, prueben todo en un clon limpio del repositorio en una máquina distinta a la de desarrollo.

---

## 2. Alcance

**Incluido:** todo lo exigido por el enunciado (§6–§11).
**No incluido (salvo que sobre tiempo):** laboratorio Streamlit, video Manim de portada, precio de combustible por provincia, escenario post-AP-68 (§7.1).
**Fuera de alcance:** CMA-ES, OSRM con perfiles personalizados, rutas para vehículos pesados.

---

## 3. Decisiones cerradas [DECIDIDO]

| Tema | Decisión |
|---|---|
| Lenguaje y entorno | Python 3.12, un solo `requirements.txt` con versiones fijas (generado con `pip freeze`, incluye dependencias transitivas). Incluye también las dependencias para **reconstruir datos y figuras** (`openpyxl`, `matplotlib`); la demo de la Parte 2 usa `matplotlib` para la figura del recorrido (§7.7) |
| Solver exacto | **PuLP 4.0 + HiGHS** (`pulp[highs]`). PuLP 4.0 **ya no incluye CBC** y cambió la API: las variables se crean con `problema.add_variable(nombre, cat="Binary")`, no con `LpVariable(..., cat=...)` (ver H-07) |
| Design System | Skill **`apple-design`** (https://github.com/emilkowalski/skills/tree/main/skills/apple-design) — ver §8 |
| Implementación | Algoritmos **desde cero con numpy**. Librerías de optimización (SciPy, pyswarms, DEAP, OR-Tools) **solo para contrastar**, nunca como solución |
| Funciones Parte 1 | **Rosenbrock + Rastrigin**, en 2D y 3D |
| Blog | **Material for MkDocs** (100 % Python), publicado en GitHub Pages |
| Figuras interactivas | **Plotly** con plantilla del Design System |
| GIF obligatorios | **matplotlib** con hoja de estilo del Design System |
| Arquitectura | Los algoritmos **no dibujan**: escriben JSON en `results/data/`; las figuras se construyen después |
| Datos Parte 2 | Cinco bloques (coordenadas, rutas, peajes, combustible, vehículo) — §7.2. Descarga en un **único script con internet**; el experimento solo lee archivos locales |
| Vehículo | **Toyota Corolla Sedán Hybrid, motor 1.8 L (140H)**, híbrido autorrecargable de gasolina — acabado **Style Plus 140H e-CVT**, año de modelo **MY27** (el que vendía Toyota España en la fecha de corte; v1.7, ver §7.2 Bloque 5) |
| Fecha de corte de datos | **1-oct-2026** (escenario base) |
| Dominio de Rosenbrock | **[−2.048, 2.048]ⁿ** (justificación en §6.1.1) |
| Combustible | **Gasolina 95 E5**, precio medio **peninsular** en la fecha de corte (v1.6; antes, nacional — ver §7.2 Bloque 4) |
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
│   ├── processed/                # cities.csv, rutas_*.csv/npz, peajes_tramos.csv, combustible.json, combustible_resumen.json, vehiculo.yaml
│   └── fuentes.md                # tabla: dato | fuente | URL | fecha de consulta | notas
├── results/  data/  tables/
├── media/                        # GIF finales
├── tests/
├── alucinaciones/  registro.md, evidencias/
├── blog/  mkdocs.yml, docs/ (index.md, figures/, stylesheets/), secciones/, hooks/reporte.py, references.bib, apa.csl, README.md
├── docs/spec/  SPEC.md, PLAN.md
└── .claude/agents/               # definiciones de subagentes (§12)
```
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en REFACTOR-PARTE1-COMUN — Parte 1, refactor de T1.4/T1.5/T1.6] `src/part1/` añade `_comun.py`: utilidades compartidas **solo** por las tres metaheurísticas de la Parte 1, `ea.py` (T1.4), `pso.py` (T1.5) y `de.py` (T1.6); no es `src/common/` ni afecta a la Parte 2 (validaciones de forma, tipo y claves del bloque, población inicial y su evaluación, frames y retorno de §5.1), para que PSO y DE no importen de `ea.py` ni dupliquen código. Es un refactor sin cambio de comportamiento ni de contratos; `gd.py` no se toca. Detalle y criterios de aceptación en `docs/spec/propuestas/REFACTOR-PARTE1-COMUN.md` (tarea T1.6b del PLAN). **Implementado el 12-oct** (salidas idénticas bit a bit; revisor-spec, revisor-calidad y verificador-matematico aprueban); Daniel aprobó esta línea y la de §5.1 [DECIDIDO v1.21, 13-oct].

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
  - [DECIDIDO 9-oct, T0.2] El valor se interpreta como YAML (`--set pso.w=0.9` → float, `--set runs=5` → int, `--set gd.armijo=true` → bool,
    `--set w=[0,5,10]` → lista). **Una clave que no existe en la configuración cargada es un error** con mensaje claro
    (evita errores de tipeo durante la modificación en vivo).
  - El comando imprime la configuración final resuelta antes de ejecutar (sirve para la predicción en vivo).
  - [DECIDIDO 9-oct, T0.2] ⚠️ PyYAML sigue YAML 1.1: `yaml.safe_load("1e-3")` devuelve el **texto** `'1e-3'` (solo `1.0e-3` da 0.001).
    El proyecto usa un cargador propio (SafeLoader + regla de flotantes de YAML 1.2) tanto para los archivos `.yaml` como para `--set`,
    de modo que `1e-3`, `2E5` y `-1.5e-8` sean `float`.
  - La salida de los comandos se fuerza a UTF-8 (tildes y "ñ" en nombres de ciudades).
  - [DECIDIDO 9-oct] El cargador usa el **esquema core de YAML 1.2 completo** para bool/int/float: booleanos solo `true`/`false`
    (`yes`/`no`/`on`/`off` quedan como texto), enteros decimales (`010` → 10, no octal; octal solo con `0o`), sin sexagesimales.
  - [DECIDIDO 9-oct] **Herencia de valores por defecto:** `configs/part1/base.yaml` y `configs/part2/base.yaml` contienen **todos** los
    parámetros (valores por defecto del Spec). Cualquier otra config declara `hereda: base.yaml` (ruta relativa a su carpeta) y solo
    escribe lo que cambia; el cargador hace una fusión profunda (la config hija gana) y elimina la clave `hereda`. Así
    `--set pso.c1=2.0` funciona en cualquier config. Herencia de un solo nivel o encadenada, con detección de ciclos.
  - [DECIDIDO 9-oct] "Sin límite" se escribe `null`, nunca `.inf` (los JSON de resultados prohíben inf/NaN).
  - [DECIDIDO 9-oct] **Un bloque no se puede reemplazar por un valor:** si la base tiene un mapeo (p. ej. `pso:`), una config hija con
    `pso:` vacío/escalar o un `--set pso=3` es un **error** con mensaje claro ("usa pso.<clave>=valor"). Evita borrar sin querer todos los
    parámetros de un método durante la modificación en vivo. `--set` tampoco reemplaza un bloque por otro mapeo (`--set pso={w: 1}` es
    error): se cambian subclaves una a una. En la herencia, en cambio, un mapeo de la hija sí se fusiona. Las claves de las configs son
    siempre texto (sin claves numéricas).
  - En PowerShell, los valores con espacios van entre comillas: `--set "methods=[pso, gdfijo]"`.
  - Claves de nivel superior de las configs: Parte 1 `func`, `dim`, `methods`, `runs`, `base_seed`, `record_frames`
    (identificadores de §5.4); cada método añade su bloque (`pso:`, `de:`, `ea:`, `gd:`) con sus parámetros por defecto en su tarea.
    Parte 2 `methods` (lista ⊂ {`aco`, `ga`, `exacto`}), `runs`, `base_seed`, `costo:` (incl. `valor_hora`), `aco:`, `ga:`, `peajes:`.
    [DECIDIDO 9-oct] En la Parte 1 `func` y `dim` son **listas** (la `base.yaml` describe el experimento completo: 2 funciones × 2 dimensiones);
    `base_seed: 0` en ambas partes; `costo.valor_hora: 25` en la base de la Parte 2 (valor del demo §7.7; el barrido usa `sweep_w.yaml`).
- Semillas: `rng = np.random.default_rng(base_seed + run_id)`. Prohibido `np.random.seed` global y `random` sin semilla.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.7] La Parte 1 añade cuatro claves de nivel superior a `configs/part1/base.yaml`: `presupuesto_por_dim` (entero > 0, por defecto 10000; el presupuesto de §6.2 es `presupuesto_por_dim · dim`), `workers` (entero ≥ 1, por defecto 1; procesos en paralelo, el resultado es idéntico con cualquier valor), `salida` (carpeta de los JSON, por defecto `results/data/part1`) y `tablas` (carpeta de los CSV, por defecto `results/tables/part1`). `configs/part1/demo.yaml` usa `results/data/part1_demo` y `results/tables/part1_demo` (ignoradas por git) para no pisar el experimento completo. `run.py part1` valida la config antes de correr (`validar_config`: tipos de las claves de nivel superior, con `presupuesto_por_dim` y `workers` enteros; `func`, `dim` y `methods` listas no vacías, sin repetidos y de identificadores conocidos; dimensión admitida por cada función; ningún float no finito en toda la config); lo que esa validación rechaza termina con código 2 y sin escribir ningún archivo. Los parámetros de cada bloque de método (p. ej. `de.NP: 2`) los valida su optimizador al ejecutarse: ese error llega después, con los JSON de las configuraciones anteriores ya escritos. El experimento no borra archivos de ejecuciones anteriores en `salida`.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.8] Clave de nivel superior `figura_trayectoria` en `configs/part1/base.yaml` (bool; `false` en la base, `true` en `configs/part1/demo.yaml`): si es `true`, `run.py part1` escribe además la figura de trayectoria de §6.8. `validar_config` la exige bool y rechaza (código 2, sin escribir nada) `true` cuando no puede haber frames (`record_frames: false` o 2 fuera de `dim`). Como `workers`, no se guarda en el `config` de los JSON de corrida. `run.py part1` imprime siempre una línea «Tiempo de ejecución: X s» y, si hay figura, su ruta.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.10] Subcomando `python run.py hpo --config configs/part1/base.yaml [--set ...]`: optimización de hiperparámetros de la Parte 1 (§6.9). El CLI le pasa, además de la config resuelta, la ruta de `--config` y la lista de `--set`. `configs/part1/base.yaml` añade el bloque de nivel superior `hpo:` (`ensayos`, `semillas`, `base_seed`, `semilla_busqueda`, `reanudar`, `salida`, `salida_afinada`, `tablas_afinada`, `config_salida` y `espacios`: método → nombre corto → {`ruta`, `tipo`, `min`, `max`}); `run.py part1` no lo lee. Demo: `python run.py hpo --config configs/part1/hpo_demo.yaml` (escribe solo en `results/data/part1_hpo_demo/` y `results/tables/part1_hpo_demo/`, ignoradas por git).

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
class BudgetExhausted(Exception): ...   # se lanza ANTES de una evaluación que excedería el presupuesto

class CountedProblem:
    """Envuelve una TestFunction. ÚNICO lugar donde se cuentan evaluaciones."""
    def __init__(self, func, k: float, budget: float): ...   # k = costo de 1 ∇f en evaluaciones de f; budget en evaluaciones equivalentes
    func; k; budget                                     # [DECIDIDO 9-oct] públicos; budget debe ser FINITO (> 0); los optimizadores leen
                                                        # dominio y dimensión de problem.func.bounds y problem.func.dim
    n_f: int
    n_grad: int
    best_x: np.ndarray | None; best_f: float           # mejor punto visto (evaluado u observado)
    history: list[dict]                                 # [{"eval_equiv", "f_best"}], se agrega SOLO cuando mejora best_f
    def f(self, x) -> float: ...          # si eval_equiv()+1 > budget → BudgetExhausted; si no, n_f += 1
    def grad(self, x) -> np.ndarray: ...  # si eval_equiv()+k > budget → BudgetExhausted; si no, n_grad += 1
    def observe(self, x) -> None: ...     # evalúa f SIN contar, solo para registrar best/history (p. ej. GD de paso fijo,
                                          # que nunca llama a f). Retorna None a propósito: el algoritmo no puede usar el valor.
    def eval_equiv(self, k: float | None = None) -> float: ...   # n_f + k * n_grad (k por defecto = el del constructor)
    def budget_exhausted(self) -> bool: ...                      # True si ya no cabe ni una evaluación de f
# [DECIDIDO 9-oct, T0.4] Los optimizadores capturan BudgetExhausted y devuelven el mejor resultado:
# así el presupuesto NUNCA se excede (cumple la regla de truncar la última generación, §6.2).
# observe() existe para que las curvas de convergencia del GD de paso fijo no le cobren evaluaciones de f
# que el algoritmo no usa; las evaluaciones de f que un algoritmo SÍ usa para decidir (Armijo, metaheurísticas) se cuentan.

# todos los optimizadores de la Parte 1 (gd.py, ea.py, pso.py, de.py)
def optimize(problem: CountedProblem, cfg: dict, rng: np.random.Generator) -> dict
# retorno:
{ "x_best": list, "f_best": float, "n_f": int, "n_grad": int, "eval_equiv": float,
  "history": [{"eval_equiv": float, "f_best": float}],
  "frames":  [{"iter": int, "positions": [[x, y], ...], "best": [x, y]}] }   # solo si dim == 2 y cfg.record_frames
```
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.1] src/part1/functions.py expone además la fábrica get_function(name, dim) y el diccionario FUNCIONES; name coincide con los identificadores de la sección 5.4.
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en REFACTOR-PARTE1-COMUN — Parte 1, refactor de T1.4/T1.5/T1.6] El diccionario de retorno de `optimize` de `ea.py` (T1.4), `pso.py` (T1.5) y `de.py` (T1.6) lo armaría una sola función de `src/part1/_comun.py` (`construir_resultado`); las claves, los tipos y la regla de `frames` de este contrato no cambian.

### 5.2 Parte 2
```python
# src/part2/costos.py
@dataclass(frozen=True, eq=False)  # [DECIDIDO v1.13, Jose Miguel, 12-oct] seis matrices n×n: tiempo_h, dist_km, peaje_eur × {rapida, sin_peaje}
class Componentes: ...
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
| `data/processed/rutas_resumen.json` | `{fuente, fecha_extracto_osm, n_pares, n_filas, fecha_consulta_utc {min, max}, pares_sin_peaje {criterio, n, pares}, avisos, control_pasos, simetria}` — pares marcados (§7.2 Bloque 2), controles de la descarga y diferencia máxima de simetría (para el blog) |
| `data/processed/rutas_pasos_peaje.csv` | `i, j, alternativa, paso, ref, nombre, dist_m, n_intersecciones, n_intersecciones_toll, lon_ini, lat_ini, lon_fin, lat_fin` — una fila por paso de OSRM con al menos una intersección de clase `toll`; entrada de T2.5 (los crudos no se versionan) |
| `data/processed/peajes_tramos.csv` | `id, via, desde, hasta, operador, ambito (estatal/SEITT/foral/autonomico), provincia, km, tarifa_ligeros_eur, eur_km, vigente_desde, vigente_hasta, fuente_url, fecha_consulta, nota` |
| `data/processed/peajes_cadenas.csv` | **[DECIDIDO v1.10, Jose Miguel, 12-oct]** Los cinco archivos auxiliares de T2.5 (esta fila y las cuatro siguientes) se mantienen. `id_tramo, cadena, orden, refs_osrm` (refs separadas por `\|`) — agrupa los tramos contiguos de una autopista |
| `data/processed/peajes_anclas.csv` | *(v1.10)* `cadena, km_cadena, lon, lat, etiqueta, tipo_coord, origen_km, fuente_coord` — puntos con km y coordenadas conocidos; sitúan un paso de OSRM en una cadena. `peajes_tramos.csv` no tiene coordenadas |
| `data/processed/rutas_peajes_detalle.csv` | *(v1.10)* `i, j, alternativa, cadena, tramo_id, via, km_cubiertos, fraccion, tarifa_eur, importe_eur` — una fila por ruta y tramo cobrado |
| `data/processed/peajes_avisos.csv` | *(v1.10)* `i, j, alternativa, paso, ref, motivo, detalle` — pasos `toll` que no se cobraron |
| `data/processed/peajes_resumen.json` | *(v1.10)* `{generado_por, fecha_corte, parametros, n_filas, n_filas_con_peaje, n_avisos, avisos_por_motivo, pasos_sin_ref, pasos_no_asignados, filas_por_via}` |
| `data/processed/combustible.json` | `{producto, ambito, precio_medio_eur_l, precio_mediano_eur_l, n_estaciones, fecha, fuente_url, archivo_raw}` — `ambito = "peninsular"` (v1.6) |
| `data/processed/combustible_resumen.json` | `{producto, id_producto, campo_precio, ambito, fecha, fecha_respuesta, fecha_consulta_utc, fuente_url, archivo_raw, redondeo, n_estaciones_respuesta, n_sin_precio, criterio_sin_precio, nacional {n, media, mediana, min, max}, peninsular {n, media, mediana, min, max}, no_peninsular {<territorio>: {n, media, mediana, min, max}}, ccaa_no_peninsulares, contraste_filtro_producto {url, n_estaciones, coincide}}` — desglose y controles de la descarga; la media nacional queda como sensibilidad para el blog (v1.6) |
| `data/processed/vehiculo.yaml` | `{marca, modelo, version, anio, anio_modelo, combustible, consumo_wltp_comb_l100, fuente_url, respaldo_url, fecha_consulta}` — `anio` = año de compra (2026), `anio_modelo` = "MY27" (v1.7) |
| `data/fuentes.md` | Tabla `dato | fuente | URL | fecha de consulta | notas` (exigida por el enunciado) |

### 5.4 Resultados (para figuras y blog)
```text
results/data/part1/runs/{func}_{dim}d_{method}_seed{k}.json   # retorno de optimize() + config
results/data/part1/summary.json                               # estadísticas por configuración (§6.6)
results/data/part2/sweep_w.json     # [{w, tour, cost, desglose:{tiempo,peajes,combustible}, km_peaje, cambio_vs_anterior, gap_aco, gap_ga}]
results/data/part2/history_{aco|ga}_w{w}.json   # JSON compacto, sin sangría, versionado [DECIDIDO v1.16]: ~6,4 MB los 11 w (con sangría, ~16,3 MB)
results/data/part2/umbrales_w.json      # [implementado en T3.6, pendiente de confirmación] candidatos canónicos, intervalos y umbrales de la envolvente
results/data/part2/sensibilidad/<etiqueta>/   # [ídem] sweep_w.json, umbrales_w.json y comparacion_base.json de cada consumo/precio alternativo
results/data/part2/demo/demo.json         # [DECIDIDO v1.17] demo §7.7: {w, solvers, tour, cost, desglose, km_peaje, arcos_con_peaje, referencia, gap_mejor_conocido, metodos, n_tour_evals, figura, nota, semillas, config}; NO se versiona
results/data/part2/demo/recorrido_w{w}.png   # [DECIDIDO v1.17] figura del mejor recorrido de la demo; NO se versiona (se regenera en segundos)
results/data/part2/route_geometry.json   # opcional: geometría simplificada por par y alternativa
```
**[DECIDIDO 9-oct, T0.3] Identificadores y forma del JSON de cada corrida (Parte 1):**
- `func` ∈ {`rosenbrock`, `rastrigin`}; `method` ∈ {`gdfijo`, `gdarmijo`, `ea`, `pso`, `de`} — en minúsculas y **sin guion bajo**
  (el `_` separa los campos del nombre de archivo). Ej.: `rastrigin_2d_pso_seed7.json`. `run_filename` **exige** `^[a-z0-9]+$`
  en `func` y `method` (error si no), para que dos corridas nunca generen el mismo nombre.
- `seed{k}` y el campo `"seed"` son la **semilla efectiva** `base_seed + run_id` (la que devuelve `seeds_for_runs`), no el `run_id`.
- Claves de los diccionarios guardados: solo texto (`str`); una clave de otro tipo es un error al guardar.
- Contenido: `{"func", "dim", "method", "seed", "k", "budget", "config": {...}, "result": {<retorno de optimize() §5.1>}}`.
- JSON en UTF-8, sangría 2, sin escapar acentos; **NaN/inf prohibidos** (error al guardar).
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.7] Frames: el runner pide `frames` solo en la corrida `run_id = 0` de cada configuración con `dim == 2` (y solo si `record_frames: true`); los JSON de las demás semillas no llevan la clave `frames`. El campo `config` de cada JSON es la config usada en esa corrida, con `record_frames` ya resuelto para ella y, en `gdfijo`/`gdarmijo`, con `variante`; no incluye `workers` (no afecta al resultado y así los JSON son idénticos byte a byte con cualquier número de procesos).
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.7] Sensibilidad k = 1 (§6.2): `gdfijo` y `gdarmijo` se vuelven a ejecutar con k = 1 (mismo presupuesto, mismas semillas, sin frames) y se guardan en `<salida>/k1/runs/` con los mismos nombres de archivo y `"k": 1.0` (`k` y `budget` se guardan como float, §5.1). `ea`, `pso` y `de` no se vuelven a ejecutar: no evalúan gradientes (`n_grad = 0`), su trayectoria no depende de k y su fila de sensibilidad es la de la tabla principal. Los CSV van en `<tablas>/`.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T4.2] `results/data/part1/eta_deslizador.json` (versionado, ~70 KB; lo genera `python scripts/part1_eta_deslizador.py`, lógica en `src/part1/eta_deslizador.py`): GD de paso fijo en Rosenbrock 2D, semilla `base_seed + 0`, presupuesto y k de la config, una corrida por η con `ejecutar_corrida` (pasa por `CountedProblem`). Valores de η: rejilla logarítmica de 4 por década sobre el intervalo de `hpo.espacios.gdfijo.eta` más el valor por defecto y el afinado. Forma: `{"meta": {func, dim, method, seed, k, budget, x0, puntos_max}, "etas": [{eta, marca: null | "defecto" | "afinado", f_best, n_grad, n_iter, iteraciones, puntos}]}`, con la trayectoria submuestreada (a lo sumo 150 iterados, índices geométricos, siempre el primero y el último).
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.8] `<salida>/trayectoria_{func}_2d.png` (en el demo, `results/data/part1_demo/trayectoria_rastrigin_2d.png`; **no se versiona**, se regenera en segundos): figura de §6.8, una por función cuando `figura_trayectoria` es `true`. Se dibuja solo con los JSON de `<salida>/runs/` de la semilla `base_seed` en 2D (`src/viz/part1_demo.py`); no evalúa f sobre la trayectoria.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T4.3] `results/data/part1/gif_trayectorias.json` (versionado, ~61 KB;
  lo genera `python scripts/part1_gif_trayectorias.py`, lógica en `src/part1/gif_trayectorias.py`): datos de los GIF
  de §6.7 punto 4. Se versiona porque `runs/` no se versiona y el GIF debe poder regenerarse en un clon limpio. Cinco
  corridas con `ejecutar_corrida` (pasan por `CountedProblem`), semilla `base_seed + 0`, presupuesto y k de la config,
  con frames, todas en 2D: rosenbrock y rastrigin × {gdfijo, gdarmijo} y rastrigin × pso. Marcas de tiempo =
  iteraciones, `indices_submuestreo(·, 45)` (una lista común a las dos variantes de GD de cada función); en la marca t
  se toma el fotograma de `iter` = min(t, n_iter) (la variante que termina antes se sostiene). Forma:
  `{"meta": {config, base_seed, run_id, dim, k, budget, marcas_max}, "gd": {func: {iteraciones, metodos:
  {gdfijo|gdarmijo: {n_iter, f_best, n_f, n_grad, x, f}}}}, "pso": {"rastrigin": {iteraciones, n_iter, f_best, n_f,
  enjambre, mejor, f_mejor}}}`. `f` y `f_mejor` son f en el punto `best` del fotograma, calculada con
  `get_function(func, 2).f` solo para rotular: esas llamadas no forman parte del experimento y no se cuentan.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.10] Resultados de la optimización de hiperparámetros (§6.9): `results/data/part1_hpo/ensayos_<unidad>.json` (`meta` de la unidad —unidad, método, función, índice, celdas, ensayos, semillas, semillas de ajuste, presupuesto, `k_regla`, espacio, bloque del método en la config base y semilla de búsqueda; `reanudar` reutiliza un archivo solo si su `meta` coincide exactamente— y, por ensayo, `parametros`, un registro compacto por celda —`f_best`, `n_f`, `n_grad`, `eval_equiv` y `evals_hasta_exito_1e-06`, una entrada por semilla de ajuste, sin `history` ni `frames`— y su `puntaje`) y `results/data/part1_hpo/seleccion.json` (por unidad: ganador, valores por defecto y elegidos, puntajes y corridas de ajuste contadas); `configs/part1/tuned.yaml` (generado, no se edita a mano: hereda de la config de origen y solo trae `salida`, `tablas` y los hiperparámetros que cambiaron); `results/data/part1_tuned/` y `results/tables/part1_tuned/` con el mismo formato que el experimento por defecto; y `results/tables/part1_tuned/comparacion.csv`, una fila por (func, dim, method) con mediana y media de f_final, tasas de éxito a 1e-4 y 1e-6 y evaluaciones hasta el éxito a 1e-4, por defecto y afinadas, más la diferencia (afinada − por defecto) de la tasa a 1e-4.

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
- **EA (§6.4) [DECIDIDO 12-oct]:** la parada es por presupuesto, no por número fijo de generaciones (`ea.generaciones: null`; un número solo acorta la corrida y rompe la comparación justa). La élite **no se reevalúa** (conserva su aptitud): costo N en la generación 0 y N − n_élite en las siguientes, siempre con `problem.f(x_i)` individuo por individuo.

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
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.2] Configuración del GD: bloque `gd:` compartido por gdfijo y gdarmijo con `gd.eta.<función>` (rosenbrock 1e-3, rastrigin 2e-3), `gd.armijo.{eta0,beta,c}` (1.0, 0.5, 1e-4) y `gd.tol_grad` (1e-8); optimize recibe `cfg["variante"]` en {"fijo","armijo"} (lo fija el runner de T1.7) y elige eta con `problem.func.name`; el GD de paso fijo registra el punto inicial y cada iterado con `observe` (sin costo, n_f = 0) y un frame por iterado con una sola posición.
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.3] GD + Armijo con proyección: (1) la condición se evalúa sobre el punto proyectado x_η = Π(x − η∇f) como f(x_η) ≤ f(x) − c·⟨∇f(x), x − x_η⟩, que sin recorte coincide con la fórmula de esta sección (c·η‖∇f‖²); (2) cada ensayo cuenta 1 evaluación de f, f(x) se reutiliza del ensayo aceptado y f(x0) se paga una sola vez, cuando se necesita por primera vez (x0 se registra antes con `observe`, sin costo); (3) sin tope de retrocesos (lo limita el presupuesto).

### 6.4 Metaheurísticas (parámetros por defecto, todos sobrescribibles por config)
| Algoritmo | Ecuaciones | Parámetros por defecto |
|---|---|---|
| **EA** (esquema de clase, codificación real) [DECIDIDO 12-oct] | Población N×d. Cada generación: evaluar los individuos nuevos, ordenar de mejor a peor y formar la siguiente población como élite + mutantes + hijos de cruce, recortada a N. **Élite:** primeras `round(N·frac_e)` filas, copiadas. **Mutación:** `int(N·frac_m)` individuos al azar sin repetir; a cada copia se le suma N(0, σ²) a **un** gen al azar, σ = desv. estándar poblacional (ddof=0) de ese gen en la generación actual; recorte al dominio. **Cruce:** `int(N·frac_c)` individuos (par, hacia arriba) al azar sin repetir y sin considerar la aptitud; dos mitades; cada pareja da 2 hijos por cruce de un punto con punto ∈ {1,…,d−1}. Si la suma de grupos no alcanza N, el cruce sube (par) hasta cubrirlo; si excede, se recorta por el final | N=50, frac_e=0.15, frac_m=0.10, frac_c=0.75, `reevaluar_elite`=false, `generaciones`=null, `esquema`=clase |
| **PSO** (gbest, inercia) | v ← w·v + c₁r₁(pbest − x) + c₂r₂(gbest − x); x ← x + v | N=30, w=0.7298, c₁=c₂=1.49618 [VERIFICAR Clerc & Kennedy, 2002], v_max=0.2·rango; fuera del dominio: recortar x y poner v=0 en esa componente |
| **DE/rand/1/bin** | v = x_r1 + F(x_r2 − x_r3); cruce binomial con CR y j_rand; selección codiciosa | NP=30, F=0.7, CR=0.9; fuera del dominio: reinicio aleatorio de la componente |

**Notas del EA (v1.4):**
- `frac_*` es la fracción de la población (0.15 = 15 %). Fuente del esquema: material de clase IRNA202602, "intro algoritmos evolutivos" (https://colab.research.google.com/drive/1QvaXDJAPgiuQOuKcvZB-lpiRbPGqLHne).
- `ea.esquema` admite hoy solo `clase`; cualquier otro valor (p. ej. `spec`, el torneo k=3 + BLX-α de la v1.3) falla con mensaje claro hasta que se implemente. Un solo identificador `ea` en §5.4.
- Defectos del cuaderno que **no** se heredan: ranking con aptitudes de la población inicial; evaluación en bucle con globales; punto de cruce 0; función de prueba no estándar.
- Comportamiento a discutir en el blog: en 2D el cruce de un punto solo intercambia coordenadas; sin selección por aptitud la única presión es la élite; σ poblacional → 0 apaga la mutación al converger.
- Validación: `ValueError` si `frac_*` o N son inválidos (negativos, N < 2, `n_élite + n_mutantes > N`).

[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.6] Aclaraciones del DE/rand/1/bin (`src/part1/de.py`; no cambian la fila de la tabla, la precisan):
(1) **selección** `f(u) ≤ f(x)`: el hijo gana en empate; (2) **fuera del dominio**: cada componente del mutante v fuera de [lb, ub] se re-sortea U(lb, ub) **antes** del cruce
(cierre inclusivo; no se recorta); (3) **cruce** binomial con `U ≤ CR` o `j = j_rand` (j_rand ∈ {0,…,d−1} sorteado para todos los individuos); (4) **esquema síncrono**: todos los
hijos se construyen con la población del inicio de la generación; (5) **padres** r1, r2, r3 distintos entre sí y de i, sorteados con una sola llamada al rng (`argsort` de
uniformes), lo que exige NP ≥ 4; (6) bloque `de:` de `base.yaml` con claves `NP`, `F` (> 0), `CR` ∈ [0, 1] y `generaciones` (`null` = parar por presupuesto, §6.2; un entero rompe la
comparación justa), sin claves desconocidas; (7) **truncado**: la generación que no cabe en el presupuesto se descarta (población y frame sin actualizar), de modo que `f_best`/`x_best`
pueden provenir de un hijo evaluado en esa generación (mejor punto visto, §5.1); n_f = NP·(T+1) y, en 2D con 20 000 evaluaciones, 666 frames; (8) `best` de cada frame = mejor individuo de la
población actual (iter 0 = población inicial).
Comportamiento a discutir en el blog: "DE garantiza el óptimo global" es falso (Rastrigin 3D con los valores por defecto: 28/30 éxitos); la diferencia x_r2 − x_r3 solo se encoge cuando la
población se concentra, y si colapsa en un mínimo local el paso se anula.

### 6.5 Diseño experimental
- 2 funciones × 2 dimensiones × 5 métodos (GD fijo, GD Armijo, EA, PSO, DE) = 20 configuraciones × **30 corridas** (semillas 0–29, mismas para todos los métodos).
- Umbral de éxito: **f − f* ≤ 1e-4** (principal); reportar también 1e-2 y 1e-6.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.10] El diseño se repite con los hiperparámetros afinados de §6.9 (mismas semillas 0–29, mismo presupuesto y mismo k): la tabla de resultados tiene dos versiones, **por defecto** y **afinada**, y `comparacion.csv` (§5.4) las pone lado a lado.

### 6.6 Métricas (`summary.json` y tablas del blog)
Por configuración: media, desviación estándar, mediana, mejor, peor de f_final; `n_f` y `n_grad` medios **por separado**; evaluaciones equivalentes (k=2n y k=1); tasa de éxito; evaluaciones hasta el éxito (media en corridas exitosas).
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.7] Esquema de `summary.json`: `{"meta": {runs, base_seed, semillas, presupuesto_por_dim, umbrales, umbral_principal, k_regla: "2n", k_sensibilidad: 1, func, dim, methods}, "configuraciones": [...], "sensibilidad_k1": [...], "avisos": [...]}`, con una entrada por (func, dim, method) en el orden de la config. Cada entrada: `func`, `dim`, `method`, `k`, `n_corridas`, `f_final` = {`media`, `desv` (muestral, ddof = 1), `mediana`, `mejor`, `peor`}, `n_f_medio`, `n_grad_medio`, `eval_equiv_medio`, `eval_equiv_medio_k2n`, `eval_equiv_medio_k1`, `tasa_exito` y `evals_hasta_exito_medio`; estos dos últimos son diccionarios con las claves de texto `"1e-04"`, `"1e-02"` y `"1e-06"` (`f"{u:.0e}"`). Evaluaciones hasta el éxito = primer `eval_equiv` de `history` con `f_best − f* ≤ u`, promediado solo sobre las corridas exitosas. Lo indefinido es `null` (nunca NaN/inf). En `sensibilidad_k1`, las entradas de `gdfijo` y `gdarmijo` son las de la re-ejecución (`k` = 1.0) y las de `ea`, `pso` y `de` son copia literal de la entrada principal, por lo que conservan `k` = 2·dim. `avisos` lista resultados que hay que revisar (f por debajo de f*, 100 % de éxito en todos los umbrales, `n_grad > 0` en `ea`/`pso`/`de`, `n_f > 0` en `gdfijo`, presupuesto excedido), cada uno con el prefijo de la tabla de la que viene, y no detiene el experimento.
[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.7] Los tres campos de evaluaciones equivalentes significan lo mismo en `configuraciones` y en `sensibilidad_k1`: `eval_equiv_medio` es la media de `result["eval_equiv"]` (con el k con el que se ejecutó la corrida); `eval_equiv_medio_k2n` y `eval_equiv_medio_k1` son **recosteos** de esas mismas corridas (media de `n_f + 2·dim·n_grad` y de `n_f + n_grad`). El recosteo con k = 1 de la tabla principal no es la re-ejecución con k = 1: al re-ejecutar, el mismo presupuesto alcanza para más gradientes y la trayectoria del GD es más larga.

### 6.7 Figuras Parte 1
1. Curvas de nivel de cada función (2D) — Plotly.
2. Curvas de convergencia (mediana + rango intercuartílico) vs. evaluaciones equivalentes, escala log — Plotly.
3. Diagramas de caja de f_final por método — Plotly.
4. GIF de GD (Rosenbrock y Rastrigin, 2D) y GIF de PSO en Rastrigin 2D — matplotlib.
5. Interactiva: deslizador de η para GD en Rosenbrock; superficie 3D de Rastrigin con el enjambre (opcional).

[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T4.2] Implementación de las figuras 1, 2, 3 y 5 (`src/viz/part1_datos.py` y `src/viz/part1_interactivas.py`, en lugar del `part1_figs.py` del árbol de §4; `python run.py figures`): ocho fragmentos HTML en `blog/docs/figures/part1_*.html` con ids fijos (`contorno-rosenbrock`, `contorno-rastrigin`, `convergencia-part1`, `cajas-part1`, `convergencia-afinado-part1`, `cajas-afinado-part1`, `eta-rosenbrock`, `enjambre-rastrigin`; tabla en `blog/README.md`). (a) Las figuras 2 y 3 se hacen con la config por defecto y, aparte, por defecto contra afinado (§6.9) solo para los métodos cuyo bloque de hiperparámetros cambió, detectados al comparar el `config` de los JSON de corrida. (b) Convergencia: rejilla geométrica de 1 al presupuesto, f_best − f* en escalón (último registro de `history` con `eval_equiv` ≤ x), k = 2n. (c) Eje logarítmico: los valores menores que 1e-16, incluido el 0 exacto, se dibujan en 1e-16 (piso de dibujo, declarado en el eje y en la fuente). (d) Deslizador de η: las trayectorias salen de `results/data/part1/eta_deslizador.json` (§5.4), no se calculan al dibujar; el valor mostrado es `f_best` (mejor punto visto), no la f del último iterado. (e) Si faltan corridas (`runs/` no se versiona), `run.py figures` avisa del comando que las genera, omite esas figuras y devuelve 0; en un clon limpio solo se regeneran los dos contornos y el deslizador de η.

[DECIDIDO v1.21, Daniel, 13-oct; propuesto en T4.3] Implementación de la figura 4 (`src/viz/part1_gifs.py`,
matplotlib sin pyplot; `python run.py figures`): tres GIF, `media/gd_rosenbrock_2d.gif`, `media/gd_rastrigin_2d.gif`
y `media/pso_rastrigin_2d.gif`, copiados a `blog/docs/figures/` (ids `gif-gd-rosenbrock`, `gif-gd-rastrigin`,
`gif-pso-rastrigin`). (a) Cada GIF de GD superpone gdfijo y gdarmijo desde el mismo x0, con color, trazo y marcador
distintos. (b) Una sola corrida: semilla 0 y configuración por defecto (la única con frames, §5.4). (c) Tiempo =
iteración, con a lo sumo 45 marcas geométricas; un fotograma por marca (200 ms, el último 3 s) y bucle infinito, como
los GIF de la Parte 2. (d) Los rótulos de f se calculan con `get_function(...).f` y no se cuentan como evaluaciones.
(e) Los datos salen solo de `results/data/part1/gif_trayectorias.json` (§5.4), no de `runs/`; el fondo es estático y
todos los fotogramas de un GIF comparten una paleta de colores. (f) Si falta ese JSON, `run.py figures` avisa del
comando que lo genera, no escribe los GIF y devuelve 0.

### 6.8 Demo Parte 1 (< 2 min)
`configs/part1/demo.yaml`: Rastrigin 2D, PSO vs GD, 5 corridas → tabla en consola + figura de trayectoria.
- [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.8] «GD» = `gdfijo`. La figura (`figura_trayectoria: true`, §4.1 y §5.4) muestra, sobre las curvas de nivel, la corrida de semilla `base_seed` de cada método: en el GD el camino del punto; en un método de población, la población inicial (marcadores huecos), la final (rellenos) y el camino del mejor punto visto (`best` de cada frame); un rótulo por método con el mejor f (`result.f_best`) y las evaluaciones equivalentes. Es una sola corrida: ilustra la trayectoria, no el comportamiento medio. La consola imprime la tabla principal, la de sensibilidad k = 1, la ruta de la figura, el tiempo y los avisos.

### 6.9 Optimización de hiperparámetros [DECIDIDO v1.21, Daniel, 13-oct; propuesto en T1.10]
Lazo externo que prueba combinaciones de hiperparámetros de cada método y se queda con la mejor (`src/part1/hpo.py`, `src/part1/hpo_experimento.py`; `python run.py hpo`). Reglas:
- **R1 Igual esfuerzo:** cada unidad de búsqueda recibe `hpo.ensayos` ensayos (30); cada ensayo se evalúa con `hpo.semillas` semillas (5), el presupuesto de §6.2 y k = 2n. Todas las unidades reciben los mismos ensayos; como gdfijo tiene una unidad por función (R5), lo que se iguala por método son las corridas de ajuste (con la config por defecto, 600 por método: 30 ensayos × 5 semillas × 4 celdas).
- **R2 Semillas distintas:** semillas de ajuste `hpo.base_seed + 0 .. semillas − 1` (1000–1004), disjuntas de las de reporte (0–29); si se solapan, la config es inválida.
- **R3 Ensayo 0 = valores por defecto** (los de §6.3–§6.4); el ensayo 0 solo se reemplaza si el mejor ensayo tiene un puntaje principal de R6 **estrictamente menor** que el del ensayo 0; si no, gana el ensayo 0, sin mirar los desempates. Regla modificada el 13-oct (T1.10b): con la versión anterior (clave lexicográfica completa) un desempate de una sola corrida de 5 semillas reemplazaba al defecto con el mismo puntaje principal (pso y de); la evidencia está en `results/data/part1_hpo/regla_v1/`.
- **R4 Muestreo aleatorio:** generador `make_rng(hpo.semilla_busqueda, índice de la unidad)`; tipos `uniforme`, `log` (uniforme en el logaritmo) y `entero` (extremos incluidos); una combinación inválida se vuelve a sortear (hasta 200 veces) y no cuenta como ensayo.
- **R5 Unidades:** un método comparte un conjunto de hiperparámetros para todas las funciones y dimensiones, salvo las rutas con `{func}` (`gd.eta.{func}`), que forman una unidad por (método, función). Con la config por defecto hay 6 unidades: gdfijo/rosenbrock, gdfijo/rastrigin, gdarmijo, ea, pso, de.
- **R6 Selección** (por unidad; celdas = pares (func, dim)): por celda, mediana sobre las semillas de max(f_best − f*, 1e-6); rango entre ensayos (empates = rango promedio); puntaje = promedio de rangos sobre las celdas (rangos porque Rosenbrock y Rastrigin tienen escalas distintas; el recorte a 1e-6, el umbral más estricto de §6.5, evita elegir por ruido numérico); si el mejor puntaje es estrictamente menor que el del ensayo 0 (R3), entre los ensayos que empatan en ese puntaje deciden los desempates (nunca deciden contra el ensayo 0): mayor tasa de éxito a 1e-6, menos evaluaciones hasta el éxito a 1e-6 (por celda, media sobre las semillas exitosas como en §6.6; celda sin éxitos = +∞; luego promedio sobre las celdas), menor índice. Las tres claves se comparan con aritmética exacta a partir de conteos enteros (éxitos, semillas y suma de evaluaciones), no de fracciones ya redondeadas a float.
- **R7 Espacios** (intervalos cerrados, en `base.yaml`): gdfijo η log [1e-5, 1e-2]; gdarmijo η₀ log [0.1, 10], β [0.1, 0.9], c log [1e-5, 1e-1]; EA N entero [20, 200], frac_e [0.05, 0.30], frac_m [0.05, 0.40], frac_c [0.40, 0.90]; PSO N entero [10, 100], w [0.3, 0.95], c₁ y c₂ [0.5, 2.5], vmax_frac [0.05, 0.5]; DE NP entero [10, 100], F [0.3, 1.2], CR [0.1, 1.0]. No se afinan `generaciones`, `iteraciones`, `esquema`, `reevaluar_elite` ni `tol_grad`.
- **R8** La HPO no reescribe los resultados por defecto (`results/data/part1/`); el experimento afinado va a `results/data/part1_tuned/` (§5.4).

---

## 7. Parte 2 — TSP por España

### 7.1 Escenario y fecha de corte [PENDIENTE: confirmar]
- **[DECIDIDO] Fecha de corte 1-oct-2026**, escenario **"base"** = red de peajes vigente en esa fecha (vigente también el día de la entrega y de la sustentación).
- ⚠️ **AP-68 (Bilbao–Zaragoza):** la concesión estatal vence el **10-nov-2026**. *(v1.9, corregido el 12-oct con fuentes oficiales, T2.4)*
  - Desde el 11-nov, los tramos estatales de **La Rioja y Aragón** quedan libres (respuesta del Gobierno al Congreso, 23-feb-2026).
  - **Bizkaia** sigue cobrando con tarifa foral: ligeros 6,85 → **4,20 €** (nota oficial de la Diputación).
  - **Álava** y **Navarra** deciden sobre sus tramos. Ninguna fuente oficial consultada fija su régimen después del 10-nov; la gratuidad navarra para turismos solo aparece en prensa.
  - El **BOE núm. 225 de 11-sep-2026** (RD 730/2026, BOE-A-2026-19039) solo regula bonificaciones a vehículos pesados hasta el 10-nov. No respalda la rebaja de Logroño–Bilbao de 19,60 € a 6,65 € que publicó la prensa (candidato H-19).
  - Nada de esto cambia el escenario base: el 1-oct-2026 toda la AP-68 cobra.
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
  - 🟢 **OSRM local con Docker** + extracto de España de **Geofabrik** (documentar fecha del extracto). El perfil de coche por defecto declara `excludable = {toll}, {motorway}, {ferry}` y la clase `toll` (verificado en `profiles/car.lua`, 1-oct-2026). Instrucciones en `scripts/osrm/README.md`. **[DECIDIDO 10-oct-2026, T2.0]**: se monta en la máquina del equipo Parte 2 (Apple M4, 16 GB RAM, ~59 GB libres); Docker aún no está instalado → se instala en T2.2.
  - **Contingencia (solo si T2.2 falla):** openrouteservice *Directions* con `avoid_features: ["tollways"]` (API key gratuita; 2 000 peticiones/día, 40/min).
- **Para cada par (i, j), i < j (1 081 pares) y cada alternativa:**
  - `rapida`: ruta sin restricciones.
  - `sin_peaje`: ruta pedida con `exclude=toll`.
    *(v1.8, corregido el 12-oct)* Con un único proceso `osrm-routed` que recibe consultas `rapida` y `exclude=toll`
    mezcladas, algunas rutas `sin_peaje` pasan por la clase `toll`. Son 26 en la corrida vigente: 18 por la M-12, 7 por la
    AP-15 y 1 por la AP-68. Eso ocurre aunque exista una alternativa gratuita.
    - **Lo observado** (ronda 2 de T2.3; mecanismo interno de OSRM no confirmado):
      - la respuesta depende del **historial de consultas** del proceso;
      - con **un proceso por alternativa**, 0 rutas `sin_peaje` tienen `toll` y el resultado no depende del orden.
    - El diagnóstico previo atribuía el fallo a `exclude=toll`: quedó refutado (ver H-16).
    - **[DECIDIDO, Jose Miguel, 12-oct]:** por tiempo se usa la corrida de **un solo proceso**. Un proceso por
      alternativa queda como mejora opcional.
    - Una ruta `sin_peaje` que pase por la clase `toll` **se reporta** en `rutas_resumen.json` (`avisos.sin_peaje_con_clase_toll`).
    - Sus pasos con peaje van a `rutas_pasos_peaje.csv`, y **T2.5 cobra ese peaje**, como en cualquier otra fila.
    - Evidencia en `alucinaciones/evidencias/T2.3_toll_diagnostico/` y `alucinaciones/evidencias/T2.3_historial_osrm/`.
  - Guardar: distancia, duración, pasos (`ref`, distancia, clases, coordenadas) y geometría simplificada.
- **[DECIDIDO v1.8, Jose Miguel, 12-oct] Determinismo:** `osrm-routed` corre con **`--threads 1`**.
  - Con 16 hilos, la misma URL devolvía rutas distintas (p. ej., 18/12 en 30 repeticiones), a veces no óptimas.
  - Con eso, 2 pares quedaron mal marcados como "sin peaje": [3,35] y [21,35] pasaban por la M-12.
  - Con un hilo, la misma URL repetida da la misma respuesta (20/20).
  - Aun así, la respuesta depende de las consultas previas. Por eso la corrida se hace **con el servidor recién
    arrancado y en el orden de `descargar_datos.py`**: así se reproduce exactamente (0/2202 rutas distintas).
  - Se descartó un segundo grafo con un perfil que prohíba las vías de peaje: contradice §2 ("OSRM con perfiles personalizados" está fuera de alcance).
- **Simetría:** se asume c_ij = c_ji (se consulta i→j). **Comprobación:** consultar j→i para 20 pares aleatorios y reportar la diferencia máxima en el blog.
- **Aceptación:** 1 081 × 2 rutas sin errores; si `sin_peaje` coincide con `rapida` (no hay peaje en la ruta), se marca y se reutiliza.
  *(v1.8)*
  - Las rutas `sin_peaje` con clase `toll` **no** bloquean la tarea: se cuentan y se listan.
  - Es obligatorio comprobar el determinismo: varias consultas repetidas deben devolver la misma ruta.
- **[DECIDIDO 11-oct-2026, T2.3]**
  - **Criterio de marca:** un par es "sin peaje" si **ninguna intersección** de su ruta `rapida` tiene la clase `toll` (la clase va por intersección, no por paso). Se conservan las dos filas en `rutas.csv` (sin columna nueva): la fila `sin_peaje` reutiliza los valores de la `rapida`. Los pares marcados se listan en `rutas_resumen.json`; si OSRM devolvió para `sin_peaje` una distancia o duración distinta, se emite un aviso.
  - `vias_peaje`, `km_peaje` y `peaje_eur` quedan vacías en T2.3; *(v1.10)* las rellenó T2.5 a partir de `rutas_pasos_peaje.csv`.
  - **Crudos:** `data/raw/osrm_<fecha>/{rutas,simetria}/` **no se versionan** (peso). Se versionan `rutas.csv`, `rutas_resumen.json` y `rutas_pasos_peaje.csv`, y la evidencia de T2.2 (`data/raw/osrm_2026-10-10/`).

#### Bloque 3 — Peajes (el bloque más difícil)
- **Fuentes oficiales:**
  - Estatales en concesión y SEITT: listado y tarifas 2026 del **Ministerio de Transportes y Movilidad Sostenible**. Tarifas 2026: +3,64 % a +4,68 % (concesiones) y +2 % (SEITT: R-2, R-3/R-5, R-4, M-12, AP-7 Cartagena–Vera, AP-36, AP-41).
  - Forales/autonómicos: Bidegi (Gipuzkoa), Interbiak (Bizkaia), Diputación Foral de Álava; Galicia y otros operadores autonómicos [VERIFICAR la lista completa de tramos que afectan rutas entre capitales].
- **Tabla** `peajes_tramos.csv` (§5.3) con tarifa para **vehículos ligeros**, fuente y fecha.
- **[DECIDIDO v1.9, Jose Miguel, 12-oct] Una tarifa por tramo.** Cuando el operador publica varias tarifas para ligeros, se usa:
  - AP-51 y AP-61: nivel **normal**, no valle ni punta.
  - AP-71: tarifa **diurna**.
  - Autopistas SEITT (R-2, R-3, R-4, M-12, AP-41): pago en **efectivo/tarjeta**, sin telepeaje y sin la franja gratuita de 00:00 a 06:00.
  - AP-7: **temporada baja**, la vigente el 1-oct.
  - Los demás niveles quedan anotados en `nota`.
- **[DECIDIDO v1.9, Jose Miguel, 12-oct] Km sin longitud oficial.** Los tramos forales o autonómicos que el Catálogo RCE no mide se completan con la longitud medida sobre la geometría de OSM. Esos km son una **aproximación documentada** en `nota`.
- **[DECIDIDO v1.9, Jose Miguel, 12-oct] M-12:** el tramo de pago va de la M-40 a la M-13 e incluye los troncales de Barajas. De la M-13 a la A-1 es libre.
- *(v1.9)* **Peaje cerrado:** en autopistas de peaje cerrado la suma de tramos no siempre es igual a la tarifa del recorrido completo publicada (Bilbao–Zaragoza: 41,50 € frente a 39,90 €). T2.5 documenta cómo lo trata.
- **[DECIDIDO v1.10, Jose Miguel, 12-oct] Peaje cerrado = suma de tramos.** No se construye una tabla de tarifas origen–destino. Es una aproximación: Bilbao–Zaragoza 41,50 € frente a 39,90 € publicado (+4,0 %); AP-6 completa 13,50 € frente a 15,70 € (−14 %). Sobre 15 rutas de contraste el sesgo va de −18 % a +4 %, y los tres casos fuera de ±5 % usan la AP-6 (A Coruña–Madrid, Madrid–Valladolid, Madrid–Ávila). Se reporta en el blog.
- *(v1.9)* El Catálogo RCE 2025 (24 MB, `mitma_260306-catalogorce2025.zip`) **no se versiona**, igual que el `.mdb` del Bloque 1. Su URL está en `data/fuentes.md` y su SHA-256 en el MANIFEST.
- **Cálculo por ruta (`scripts/asignar_peajes.py`, sin red) — *(v1.10, T2.5)*:**
  1. Un paso de `rutas_pasos_peaje.csv` sin `ref` es un enlace y no se cobra.
  2. Un paso con `ref` se asigna a una **cadena** (`peajes_cadenas.csv`) cuya lista `refs_osrm` contenga esa `ref` y que esté más cerca de sus dos extremos; nunca por prefijo del nombre.
  3. Cada extremo se sitúa en el km de la cadena con `peajes_anclas.csv`: ajuste a un ancla a ≤ 1,5 km; si no, interpolación lineal sobre la poligonal de anclas. No se usa `n_intersecciones_toll / n_intersecciones` para medir km (falla hasta un 25 % en pasos parciales).
  4. Por ruta y cadena se cobra el recorrido [mín, máx] de sus pasos, porque OSM deja sin `toll` algunos trozos de autopista.
  5. Peaje = Σ tarifa del tramo × km recorridos / km del tramo; con ≥ 95 % del tramo se cobra la tarifa completa.
  6. Las filas `sin_peaje` con clase `toll` se cobran igual. Los pasos con `ref` sin cadena (`GI-20`, `N-622`, `PA-34`) no se cobran y se listan en `peajes_avisos.csv` (38 pasos).
  7. `km_peaje` = suma de km en tramos con tarifa > 0; `peaje_eur` con 2 decimales; `vias_peaje` = vías con importe > 0 separadas por `;`.
  - **Parámetros elegidos por el curador, sin fuente:** el ajuste a ancla de 1,5 km y el umbral del 95 %. Bajar el 95 % a 90 % cambia 15 rutas hasta 0,25 €.
  - **Limitación:** 63 de los 77 anclas salen de extremos de pasos de OSRM, no de una fuente externa; verificadas por muestreo contra el Catálogo RCE (5 de 6). Validación en `docs/validacion_peajes_T2.5.md`.
- **Cálculo por ruta, versión original (v1.0–v1.9, superada por la anterior):**
  1. De los pasos de OSRM, tomar los que tienen clase `toll` [VERIFICAR que el OSRM local la marca] y su `ref` (nombre de vía) y ubicación.
  2. Asignar cada tramo recorrido a una fila de `peajes_tramos.csv` por vía **y** ubicación (provincia/tramo) — **no** por el prefijo del nombre: varias "AP-" ya son gratuitas (AP-1, AP-2, AP-4 y tramos de la AP-7) y conservan el nombre.
  3. Peaje del par = Σ km recorridos en cada tramo × €/km del tramo (o tarifa completa si se recorre el tramo entero).
- **Validación (obligatoria):** comparar con el listado oficial / calculadora del operador al menos estos pares: **Bilbao–Zaragoza (AP-68), Sevilla–Cádiz (AP-4, debe dar 0 €), Madrid–Toledo (AP-41 vs. A-42), Alicante–Murcia (AP-7), A Coruña–Pontevedra (AP-9)**. Reportar la diferencia en el blog. Las etiquetas `toll=yes` de OSM pueden estar desactualizadas: cualquier discrepancia se documenta (y es candidata a hallazgo).

#### Bloque 4 — Precio del combustible
- **Fuente:** Geoportal de Gasolineras / servicio REST del Ministerio para la Transición Ecológica (`sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/`; tiene endpoint histórico por fecha).
  *(v1.6, T2.6)* Los datos de la fecha de corte salen del endpoint histórico `…/PreciosCarburantes/EstacionesTerrestresHist/{dd-mm-aaaa}`;
  `EstacionesTerrestres/` devuelve solo los precios del día de la consulta, y una fecha ISO (`aaaa-mm-dd`) da HTTP 400.
- **Producto:** Gasolina 95 E5. Descarga única en la fecha de corte; guardar el JSON crudo con la fecha en el nombre.
- **Modelo [DECIDIDO v1.6, Jose Miguel, 11-oct]:** precio **medio peninsular**. Se excluyen las estaciones de Baleares,
  Canarias, Ceuta y Melilla (IDCCAA 04, 05, 18, 19). Hay que reportar también la mediana y el nº de estaciones. Por provincia: fuera de alcance.
  - **Por qué:** el enunciado (§1.2) excluye esos territorios del recorrido, así que el vehículo nunca reposta allí.
    Canarias (precio más bajo) sesga la media nacional hacia abajo en la misma dirección siempre.
  - **Sensibilidad:** la media nacional se conserva en `combustible_resumen.json` para el blog.
  - *Antes de v1.6* el modelo era la media nacional.

#### Bloque 5 — Vehículo
- **[DECIDIDO] Toyota Corolla Sedán Hybrid, motor 1.8 L (140H)**, híbrido autorrecargable de gasolina.
- **Acabado [DECIDIDO v1.7, Jose Miguel, 11-oct]: Style Plus 140H e-CVT, año de modelo MY27.**
  - En la fecha de corte es el único acabado del configurador para particulares, y tiene ficha técnica oficial estructurada.
  - Se descarta el ECO (flotas, taxi y VTC): Toyota publica para él tres cifras WLTP distintas.
  - Toyota España pasó de MY26 a MY27 entre el 15 y el 23-sep-2026 (Wayback). El consumo combinado es el mismo (4,6 l/100 km); el CO2 pasa de 104 a 105 g/km.
  - Los 4,4–4,7 l/100 km del documento del equipo Parte 2 corresponden a otra carrocería (5 puertas), lo que confirma el [VERIFICAR] anterior.
- Consumo **WLTP combinado** (l/100 km) de la **ficha técnica oficial de Toyota España**; **km77** como respaldo; fecha de consulta.
- **Sensibilidad:** usar también el consumo de la fase WLTP **"extra alta"** (autopista), si la ficha la publica.
  *(v1.7)* La ficha actual de Toyota España (MY27) y km77 no la publican. El catálogo de Toyota España del Corolla Sedan,
  edición 09/2023 (`14764_CORS_48_ES_WEB_S.pdf`, pág. PDF 17), sí la da: "Ritmo extra alto (l/100km) 5,6-6,2". Es un
  rango de la gama de 2023, con el mismo motor 2ZR-FXE.
  - **[DECIDIDO v1.7, Jose Miguel, 11-oct]:** el valor base sigue siendo 4,6 l/100 km (WLTP combinado MY27).
  - 5,6 y 6,2 l/100 km son el **escenario de sensibilidad "autopista"** (§7.5), y se declaran como rango del catálogo de 2023.
  - Toyota publica además un "máximo" WLTP de 4,8 l/100 km (`FUELCOMBINEDWLTPMAX`). Es el **ciclo combinado**, no la fase de autopista, y no se usa.
    - En el crudo lleva `Type: "vehicleHigh"`, que según el Reglamento (UE) 2017/1151 (subanexo 4, §4.2.1) es el "vehículo H" de la familia de interpolación, el de mayor demanda de energía.
    - Toyota no documenta qué configuración concreta es (ver H-12).
  - La sensibilidad de consumo se hace con el parámetro de consumo sobrescribible (`--set`, §7.3 y §9) y se declara como supuesto.
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
- **Desempate** **[DECIDIDO v1.12, Jose Miguel, 12-oct]:** si ambas alternativas cuestan exactamente lo mismo, se elige `rapida`
  (comparación estricta: `sin_peaje` solo gana si cuesta menos). Esto aplica también a la diagonal de `alternativa_elegida`.
- **Aceptación** (`tests/test_cost.py`) **[DECIDIDO v1.11, Jose Miguel, 12-oct]:**
  - Un par calculado a mano coincide.
  - Con w = 0 se elige, en cada par, la alternativa de menor `peaje + combustible`. La redacción anterior ("nunca se elige
    una alternativa con peaje si existe otra más barata en combustible") no vale para los 26 pares cuya `sin_peaje` también
    paga peaje (§7.2 Bloque 2, v1.8).
  - c tiene diagonal 0 y es simétrica. La simetría sale por construcción (`rutas.csv` guarda solo i < j y la matriz se arma
    por espejo), así que la prueba no se limita a comparar c con su traspuesta: comprueba que cada celda (i, j) y (j, i)
    toma los valores de la fila correcta de `rutas.csv`.

### 7.4 Algoritmos
| Algoritmo | Especificación | Parámetros por defecto |
|---|---|---|
| **Ant System → MMAS** | p_ij ∝ τ_ij^α · η_ij^β, η = 1/c; evaporación τ ← (1−ρ)τ + Δτ; MMAS: solo la mejor hormiga deposita, límites τ_min/τ_max (detalle en §7.4.1) | MMAS (principal): m=47, α=1, β=3, ρ=0.02, p_best=0.05 · AS (comparación): m=47, α=1, β=3, ρ=0.5 · 1 099 iteraciones (presupuesto común, v1.16) |
| **GA** | Permutación; torneo; cruce **OX**; mutación por **inversión** o intercambio (50/50); elitismo (detalle en §7.4.2) | pop=150, gen=348 (presupuesto común, v1.16), pc=0.9, pm=0.2, torneo k=4, élites=2 |
| **2-opt** (opcional) | Mejora local sobre la mejor solución; reportar con y sin | — |
| **Exacto (referencia)** | Formulación DFJ con **PuLP 4.0 + HiGHS**, eliminación iterativa de subtours. **Implementado en T3.2 como verificación [DECIDIDO v1.20, Daniel, 13-oct]:** `resolver_exacto(C)` (gap 0, 1–3 s por w) y `solve()` con el contrato §5.2; no corre dentro del barrido | — |

- **Aceptación:** `tests/test_tsp_operators.py` — 10 000 cruces/mutaciones aleatorias producen siempre permutaciones válidas; `tests/test_exact.py` — con 5 a 8 ciudades, el exacto coincide con fuerza bruta.
- **Comparación justa ACO vs GA [DECIDIDO v1.16, Jose Miguel, 12-oct]:** mismo número de **recorridos evaluados**:
  **51 654** = ACO 1 + 47 × 1 099 = GA 150 + 148 × 348 (igualdad exacta más cercana a 50 000; las soluciones son
  iteraciones = 63 + 148k). Antes: ACO 14 101 vs. GA 148 150. El enunciado no fija iteraciones. T3.6 actualiza `base.yaml`.
  - Prueba previa (w = 25, semillas 0–4, `alucinaciones/prompts/T3.6-presupuesto.md`): MMAS 2 544,76–2 560,10 €
    (media 2 556,81, sigue mejorando tras el 67 % del presupuesto en 4 de 5 semillas); AS media 2 640,36 €; GA media
    2 636,69 € con desviación 78,9: con 348 generaciones da los mismos costos que con 1 000 (semillas 0–2) porque la
    población colapsa a 27–35 recorridos distintos. ~5,4 s por (w, corrida) para los tres métodos.
  - Se descartó 30 786 recorridos (655 iteraciones / 207 generaciones): 4 de 5 semillas de MMAS mejoraban después de
    30 000 y el GA casi no perdía, así que la comparación se habría corrido a favor del GA para ahorrar ~4 min.

#### 7.4.1 ACO (T3.3) [DECIDIDO v1.14, Jose Miguel, 12-oct]
**Fuente principal:** notas del profesor, `data/raw/ACO/notas_aco.html` (Ospina y Zapata, 2026-01), §4, §6, §7.2 y Tabla 3.
Ante una diferencia con este Spec priman las notas, y el cambio se trae aquí. **Referencia de estructura (sin copiar
código):** Berroa, J., *AntColonyOptimizer.py*, https://github.com/johnberroa/Ant-Colony-Optimization (repositorio sin
licencia, consultado el 12-oct-2026). Su algoritmo no es AS ni MMAS de las notas (depósito fijo, τ₀ = 1, arcos dirigidos,
regla tipo ACS sin actualización local); de él solo se toma calcular τ^α·η^β una vez por iteración y cerrar el recorrido.

- **Variantes:** `aco.variante ∈ {mmas, as}`; MMAS es la principal y AS la comparación.
- **Construcción (ambas):** cada hormiga arranca en una ciudad uniforme al azar (`rng`); elige la siguiente entre las no
  visitadas por ruleta con p_ij ∝ τ_ij^α · η_ij^β, η_ij = 1/c_ij (notas §4.1). El costo incluye el arco de cierre.
- **C^nn:** costo del recorrido del vecino más cercano desde la ciudad 0 (notas, Def. 8). Cuenta como 1 recorrido evaluado.
- **AS** (notas §4.2): τ₀ = m / C^nn; evaporación en todos los arcos; depositan las m hormigas Δτ = 1/L_k (Q = 1), en
  τ_ij y τ_ji.
- **MMAS** (notas §6, §6.1, Prop. 2):
  - τ_max = 1/(ρ · L^bs), recalculado cuando mejora L^bs (al inicio L^bs = C^nn).
  - τ_min = τ_max · (1 − p_best^(1/n)) / ((ā − 1) · p_best^(1/n)), con ā = n/2.
  - Inicialización τ = τ_max.
  - Actualización τ ← [(1−ρ)τ + Δτ^best] recortada a [τ_min, τ_max], simétrica. Deposita una sola hormiga, Δτ = 1/L^best:
    en la iteración t (desde 0) par, la mejor de la iteración (T^ib); en impar, la mejor global (T^bs). Las notas dicen que
    su código alterna sin fijar la frecuencia; la alternancia 1:1 es decisión del equipo.
  - Sin reinicio por estancamiento.
  - Si τ_min ≥ τ_max (con p_best = 0.05 ocurre para n ≤ 4), MMAS lanza `ValueError`; las notas exigen 0 < τ_min < τ_max.
- **Orden dentro de cada iteración** [DECIDIDO v1.14, Jose Miguel, 12-oct]: construir → evaluar → actualizar T^ib, T^bs y
  (en MMAS) τ_max/τ_min → evaporar y depositar. El esqueleto general de las notas (§3) actualiza s^bs después de la
  feromona; aquí va antes porque así lo pide §6.1 ("τ_max se actualiza cada vez que mejora T^bs"): en t impar deposita la
  mejor global incluida la iteración actual y τ queda en [τ_min, τ_max] sin que el recorte superior llegue a activarse
  (demostrado por verificador-matematico). Es el orden de ACOTSP (López-Ibáñez y Stützle, `aco.c`).
- **Recorrido inicial:** T^bs empieza en el recorrido del vecino más cercano (ambas variantes); si ninguna hormiga lo
  mejora, `solve` lo devuelve. En empates, T^ib es la primera hormiga de costo mínimo y T^bs cambia solo con mejora estricta.
- **Conteo:** `n_tour_evals = 1 + m · iteraciones` (C^nn + recorridos de las hormigas).
- **`history`:** una entrada por iteración con el mejor global hasta esa iteración.
- **API adicional:** además de `solve` (§5.2), `aco.py` expone `iterar(C, cfg, rng)`, que cede el estado de cada iteración
  (feromona, pesos W, límites de MMAS, mejores recorridos). La usan las pruebas y podrán usarla las figuras de F4;
  `solve` se apoya en ella (recomendación de revisor-calidad, ronda 3).
- **Configuración** (`base.yaml`): `aco: {variante, hormigas, alpha, beta, iteraciones, as: {rho}, mmas: {rho, p_best}}`.
- **Justificación de ρ:** se toman los valores de referencia de las notas (Tabla 3: AS 0.5, MMAS 0.02) en lugar del 0.2
  de v1.13. Las notas advierten (§10) que con ρ = 0.02 MMAS necesita más iteraciones: lo resuelve el presupuesto común.

#### 7.4.2 GA (T3.4) [DECIDIDO v1.15, Jose Miguel, 12-oct]
**Esquema:** el clásico de la tabla de §7.4 (torneo + OX + inversión/intercambio + elitismo). **Referencia general (sin
copiar código):** notebooks del profesor `data/raw/GA/IRNA202601_prep_Algoritmos_Evolutivos.ipynb` e
`IRNA202602_intro_algoritmos_evolutivos.ipynb` (Ospina y Zapata, 2026; versionados sin salidas). Trabajan con codificación
real (Rastrigin, mochila con PyGAD) y no cubren permutaciones; de ellos se toma el ciclo evaluar → ordenar → élites →
cruce → mutación. No se adopta su esquema por fracciones (padres al azar, sin torneo), porque sin torneo la única presión
de selección sería el elitismo.

- **Individuo:** permutación de 0..n−1. **Aptitud:** el costo del recorrido cerrado C(π) = Σ c[π_k, π_{k+1}] + c[π_n, π_1]
  sobre la misma matriz que ACO (se minimiza directamente; torneo y elitismo solo comparan, así que no se transforma a
  1/C ni a −C).
- **Matriz C:** mismas reglas de validación que ACO (§7.4.1). Las piezas comunes (validación, costo de recorridos,
  vecino más cercano) se reutilizan sin duplicar código y sin cambiar el comportamiento de `aco.py`.
- **Población inicial:** el recorrido del vecino más cercano desde la ciudad 0 (el mismo C^nn de §7.4.1) + `poblacion − 1`
  permutaciones uniformes al azar (`rng`). Así ACO y GA parten del mismo punto en la curva de convergencia de §7.5.
- **Generación:**
  1. Élites: los `elites` individuos de menor costo pasan sin cambios (empates: primer índice).
  2. Hasta completar `poblacion − elites` hijos: dos torneos eligen dos padres (cada torneo: `torneo_k` individuos
     distintos al azar, gana el de menor costo; empates: primero del sorteo). Con probabilidad `pc` se cruzan con OX y
     nacen dos hijos (OX(P1, P2) y OX(P2, P1)); si no, los hijos son copias de los padres. Si solo falta un hijo, el segundo
     se descarta sin evaluarlo.
  3. Mutación: cada hijo, de forma independiente, muta con probabilidad `pm`; si muta, recibe **un solo** operador,
     inversión o intercambio, elegido 50/50.
- **OX (Order Crossover):** dos posiciones distintas a < b al azar; el hijo copia el tramo P1[a..b] en las mismas
  posiciones y llena las libres, de izquierda a derecha, con las ciudades que faltan en el orden en que aparecen en P2.
- **Inversión:** dos posiciones distintas i < j al azar; invierte el tramo [i..j]. **Intercambio:** dos posiciones
  distintas al azar; intercambia sus ciudades.
- **Mejor global:** empieza en el mejor de la población inicial y cambia solo con mejora estricta.
- **Conteo:** `n_tour_evals = poblacion + (poblacion − elites) · generaciones` (51 654 con los valores por defecto de v1.16).
  Cada candidato generado cuenta 1, aunque sea una copia sin cruce ni mutación (como las hormigas que repiten recorrido en
  ACO); los élites que pasan no se vuelven a contar.
- **`history`:** una entrada por generación con el mejor global hasta ella (`iter` = número de generación, desde 0). La
  población inicial no tiene entrada propia (como en ACO, `generaciones` entradas).
- **Detalles fijados en T3.4** (conformes según revisor-spec): cada llamada a OX sortea sus propios cortes; los dos
  torneos son independientes (P1 puede ser igual a P2); el hijo sobrante no se genera; la nueva población guarda primero
  los élites y luego los hijos en orden de nacimiento; el 50/50 es u < 0,5 → inversión.
- **API adicional:** como `aco.py`, `ga.py` expone `iterar(C, cfg, rng)`, que cede el estado de cada generación
  (población, costos, mejor global); `solve` se apoya en ella.
- **Configuración** (`base.yaml`): `ga: {poblacion, generaciones, pc, pm, torneo_k, elites}` con los valores de §7.4.
  Validación: enteros `poblacion ≥ 2`, `generaciones ≥ 1`, `1 ≤ torneo_k ≤ poblacion`, `0 ≤ elites < poblacion`;
  reales `pc` y `pm` en [0, 1].

### 7.5 Experimentos Parte 2
- Barrido w ∈ {0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100} €/h (más denso en 0–50, rango sugerido por el equipo Parte 2). Para cada w: exacto + ACO (10 corridas) + GA (10 corridas) → mejor, media, desviación, **gap % vs. óptimo**.
- **Umbral [DECIDIDO v1.16, Jose Miguel, 12-oct]:** responde "¿a partir de qué valor cambia la ruta?" con la
  **envolvente inferior de recorridos candidatos**, no con bisección (el exacto es opcional desde v1.14 y la bisección
  con una heurística mezcla el azar con el efecto de w):
  - Candidatos: los mejores recorridos encontrados en todo el barrido (todos los w, métodos y corridas).
  - Para un recorrido fijo, el costo es función conocida de w: cada arco cuesta el mínimo entre dos rectas
    (rápida y sin peaje, `costos.py`), así que el costo del recorrido es lineal a trozos en w y se evalúa sin optimizar.
  - El umbral es el w donde cambia el recorrido de menor costo de la envolvente; se calcula de forma exacta (cruces entre
    funciones lineales a trozos), sin resolución fija (no depende de una bisección de 0,5 €/h). Los cruces de alternativa dentro de un arco (p. ej. pares (34,40) y (34,42) cerca de w = 30) entran en el cálculo del costo, pero solo producen un umbral si cambian el recorrido ganador; en el barrido real no lo hicieron.
  - Se reporta como "umbral entre las mejores rutas encontradas", no como umbral del óptimo probado (igual que el gap).
- **Umbrales del óptimo [DECIDIDO v1.20, Daniel, 13-oct]:** `scripts/umbrales_exactos.py` resuelve el exacto en cada
  w entero de [0, 100], ubica cada cambio por bisección (0,005 €/h) y recalcula la envolvente con los candidatos de T3.6
  más las rutas exactas que las heurísticas no hallaron (ids de T3.6 conservados; las nuevas al final, con
  `exacto_nuevo`). Comprueba que la envolvente coincide con la bisección y que cada ganador es el óptimo. Salida:
  `results/data/part2/umbrales_exactos.json` (consumos 4,6, 5,6 y 6,2). Resultado base: **10,02 / 14,53 / 42,19 €/h**
  (T3.6: 10,75 / 13,81 / 42,19; ningún w del barrido cae en el tramo 10,02–14,53). El blog y el mapa
  (`src/viz/part2_interactivas.py`) usan esta envolvente si existe. El mejor costo encontrado en el barrido es el
  óptimo en los 11 w (`tests/test_exact.py`), así que el gap resulta medido frente al óptimo.
- **Gap [DECIDIDO v1.16, Jose Miguel, 12-oct]:** `gap_aco` (MMAS) y `gap_ga` de `sweep_w.json` son el gap de la **media** de las
  10 corridas frente al mejor costo encontrado en ese w; el gap del mejor y la desviación (n − 1) van en el detalle por método.
- **Unión de candidatos en la sensibilidad [DECIDIDO v1.16, Jose Miguel, 12-oct]:** la envolvente de cada consumo alternativo se
  calcula con los candidatos del barrido base (MMAS, AS y GA) **más** los nuevos de MMAS, todos evaluados con el consumo nuevo; así
  base y sensibilidad se comparan contra el mismo conjunto de rutas y la diferencia viene del consumo, no del azar de los algoritmos.
- **Implementado en T3.6, pendiente de confirmación humana:** `costo.valor_hora` como número o lista creciente (rejilla de w);
  bloque `experimento: {variantes_aco, datos, salida}` en `base.yaml`; `run_id = (i_w · n_solvers + i_solver) · runs + r` (la
  sensibilidad reutiliza los de MMAS base); presupuesto común exigido solo si corren ACO y GA juntos; archivos `umbrales_w.json` y
  `comparacion_base.json`; salida de la demo en `results/data/part2/demo`.
- **Sensibilidad de consumo (v1.7):**
  - Se repite el barrido de w **con MMAS** (10 corridas; [DECIDIDO v1.16, Jose Miguel]: el exacto es opcional) y se
    recalcula la envolvente del umbral, con `consumo` = 5,6 y 6,2 l/100 km (fase "extra alta" del catálogo, §7.2 Bloque 5).
  - Se cambia solo con `--set`, sin editar código. Claves opcionales en `base.yaml` [DECIDIDO v1.16]: `consumo_l100`
    y `precio_l`; vacías = valores de `vehiculo.yaml` y `combustible.json` (una sola fuente de verdad); si se dan,
    deben ser números finitos > 0.
  - Se reporta, frente a la base de 4,6:
    - el costo total y el de combustible;
    - si cambian el recorrido óptimo y el umbral de w.
- Referencias contextuales para w [VERIFICAR]: ganancia media por hora en España (INE) o salario de un comercial; valores del tiempo usados por el Ministerio de Transportes en la evaluación de proyectos de carreteras.

### 7.6 Figuras Parte 2
1. Mapa con las 47 capitales (control de coordenadas).
2. Mapa interactivo (Plotly) con deslizador de w: recorrido óptimo, tramos con peaje coloreados.
3. Costo total desglosado (tiempo / peajes / combustible) vs. w.
4. Convergencia ACO vs GA (gap vs. recorridos evaluados).
5. **GIF** (matplotlib) de la evolución de la mejor ruta sobre el mapa de España.

### 7.7 Demo Parte 2 (< 2 min)
`configs/part2/demo.yaml`: ACO, w=25, 1 000 iteraciones → costo, gap vs. óptimo precalculado, figura del recorrido.
- **Referencia del gap [DECIDIDO v1.17, Jose Miguel, 12-oct]:** como el exacto (T3.2) es opcional, el "óptimo precalculado" es el
  **mejor costo conocido** en w = 25: el mejor encontrado en ese w por el barrido de T3.6 (`results/data/part2/sweep_w.json`).
  Se reporta como "gap frente al mejor conocido", no como gap frente al óptimo probado (igual que §7.5).
- **Configuración [DECIDIDO v1.17, Jose Miguel, 13-oct]:**
  - ACO = **MMAS** (variante principal, §7.4.1), `runs: 10` heredado de la base (igual que el barrido §7.5); se reporta el
    mejor de las 10 corridas con su desglose y el gap de la mejor y de la media.
  - Clave `experimento.referencia_gap` (ruta a `sweep_w.json`; `null` en `base.yaml`): si no es nula activa el modo demo
    (un solo w, sin envolvente ni historiales, salida solo en `experimento.salida`). Falla con código 2 si falta el archivo,
    la entrada de ese w o si el costo del recorrido de referencia recalculado con los datos actuales no coincide.
  - **Iteraciones [DECIDIDO v1.19, Jose Miguel, 13-oct]:** 1 000 en lugar de 100. Motivo: en la revisión del PR #11 (pendiente 4)
    se sugirió subirlas para mostrar un gap menor en vivo; con 100 iteraciones y ρ = 0,02 MMAS apenas empieza a converger
    (gap +8,97 % la mejor, +15,71 % la media). Medido en la máquina de desarrollo (Windows, 13-oct): 18,1 s de ejecución
    (18,7 s de pared con el arranque), muy por debajo de los 2 min; 47 001 recorridos por corrida (1 + 47 · 1 000). Falta medirlo
    en otra máquina (§9).
  - La salida (`results/data/part2/demo/`) **no se versiona** (`.gitignore`): se regenera en vivo (~18 s).

---

## 8. Visualización y blog [DECIDIDO]
- **Material for MkDocs** (en modo mantenimiento con correcciones hasta 5-nov-2026: suficiente para el proyecto).
- Ecuaciones: `pymdownx.arithmatex` + KaTeX.
- **[DECIDIDO 12-oct, T0.7] Bibliografía APA 7 con pandoc citeproc** (`pypandoc_binary` + `blog/apa.csl`, "APA Style 7th edition",
  lengua `es-ES`) dentro del hook. Se descartó `mkdocs-bibtex` 4.4: convierte las citas en notas al pie y APA exige citas
  autor–año en el texto. Solo se listan las obras citadas en el texto publicado (las citas dentro de comentarios no cuentan).
- **Hook `blog/hooks/reporte.py`** (pruebas en `tests/test_blog.py`; guía de uso en `blog/README.md`): une las secciones de
  `blog/secciones/` en una sola entrada de blog (`--8<-- "…"`), numera figuras y tablas en formato APA (número en negrita,
  título en cursiva, *Nota.* con la fuente), resuelve `[[fig:id]]`/`[[tab:id]]` y las citas `[@clave]`/`@clave`, y **hace
  fallar el build** si una figura/tabla no tiene título o fuente, se repite un id, una referencia no existe, una figura/tabla
  nunca se cita o una cita no está en `references.bib`.
- **[DECIDIDO 12-oct] `mkdocs` fijado en 1.6.x:** el equipo de Material for MkDocs advierte que MkDocs 2.0 elimina el sistema
  de plugins y hooks (y no ofrece migración); actualizar rompería el hook.
- **Bibliografía verificada:** toda entrada de `references.bib` viene del BibTeX oficial del DOI y se contrasta con Crossref
  (`alucinaciones/evidencias/H-bib_verificacion_doi.py`); nunca de memoria (H-22).
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
`test_gradients.py`, `test_counter.py` (PSO con N partículas y T iteraciones reporta exactamente N·(T+1) evaluaciones de f), `test_budget.py`, `test_ea.py` (tamaños de grupos, dominio, un gen mutado, punto de cruce ∈ {1,…,d−1}, élite por f actual, conteo N + T·(N − n_élite), truncado, reproducibilidad, frames), `test_reproducibility.py`, `test_no_network.py`, `test_cost.py`, `test_tsp_operators.py`, `test_exact_small.py`, `test_data_integrity.py` (47 ciudades, matrices 47×47 simétricas sin NaN, todas las tarifas con fuente y fecha).

---

## 11. Cacería de la alucinación (15 %)
- **Registro:** `alucinaciones/registro.md` (plantilla incluida) + `alucinaciones/evidencias/`.
- **Obligatorio:** guardar prompts literales — conversaciones con IA, este Spec, y los prompts que el orquestador envía a cada subagente (`alucinaciones/prompts/`).
- **Cada hallazgo:** prompt literal · respuesta relevante · cómo se sospechó · evidencia (derivación / experimento / fuente primaria) · corrección · lección aprendida.
- **Meta:** ≥5 hallazgos genuinos en ≥3 categorías (Matemáticas, Código, Datos, Bibliografía, Conceptos). **Nunca inventar.**
- **Verificaciones planificadas:** gradientes; constantes y dominios; conteo de evaluaciones; variante por defecto de DE en SciPy (`best1bin` + `polish=True`, verificado en su documentación); permutaciones válidas; EA: σ poblacional (ddof=0), punto de cruce y conteo con élite en caché (prueba de mutación); peajes Bilbao–Zaragoza y Sevilla–Cádiz preguntados a una IA vs. Ministerio; estado AP-68; WLTP vs NEDC; coordenadas ambiguas; DOI de cada referencia; afirmaciones de convergencia ("¿PSO/ACO garantizan el óptimo?", "¿Rosenbrock es convexa?"); gap real vs. "óptimo" declarado.

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
| OSRM local no se logra montar a tiempo | Decidido OSRM local (T2.0, 10-oct); si T2.2 falla, contingencia ORS (§7.2 bloque 2) |
| Peajes incompletos o mal asignados | Tabla curada + validación de 5 pares + aproximación documentada |
| Conteo de evaluaciones inconsistente | Contador único + `test_counter.py` |
| Subagentes que "rellenan" datos o fórmulas | Regla §0.3, verificador matemático, curador de datos, cazador |
| Alguien no entiende un módulo en la sustentación | tutor-sustentacion + explicación de cada PR al puente + simulacro mié 14-oct |
| Demo > 2 min | Configs `demo.yaml` medidas en otra máquina |
| EA: suma de grupos ≠ N (N=30 da 29) o convergencia floja en 2D | Regla de relleno del cruce (§6.4) + validación; reportar honestamente, sin ajustar parámetros para "ganar" |
| Design System llega tarde | Figuras de trabajo con estilo por defecto; tema final se aplica al final (las figuras se regeneran) |

---

## 14. Pendientes [PENDIENTE]
1. ~~Dominio de Rosenbrock~~ → [−2.048, 2.048]ⁿ ✅
2. ~~Fecha de corte~~ → 1-oct-2026 ✅ · ¿Se hace el escenario opcional `post_ap68`?
3. ~~OSRM local vs. ORS~~ → OSRM local con Docker en la máquina del equipo Parte 2 (decidido 10-oct-2026) ✅
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
- Material for MkDocs (modo mantenimiento): https://github.com/squidfunk/mkdocs-material/issues/8523 · aviso sobre MkDocs 2.0: https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
- Estilo APA 7 (CSL oficial): https://github.com/citation-style-language/styles/blob/master/apa.csl · Crossref REST API: https://api.crossref.org
- Propuesta de recolección de datos del equipo Parte 2 y documento "Trabajo 1 – Punto 2 (TSP por España): decisiones y fuentes de datos" (Camila, 1-oct-2026).
- km77 — Hyundai Tucson HEV 239 CV (citado por el equipo Parte 2 para la comparación de vehículos): https://www.km77.com/coches/hyundai/tucson/2024/estandar/hev/tucson-klass-16-t-gdi-hev-239-cv/datos
- Menorca.info — subida de peajes 2026 y fecha de la AP-68: https://www.menorca.info/actualidad/nacional/2026/01/11/2546999/subida-llega-2026-para-autopistas-peaje-dependientes-del-gobierno.html
