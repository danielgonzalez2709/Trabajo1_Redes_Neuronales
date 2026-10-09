# PLAN de tareas para Subagent Driven Development

> Derivado de `docs/spec/SPEC.md` v1.0. Cada tarea es **una unidad para un implementador nuevo**.
> Pipeline por defecto: **implementador → revisor-spec → revisor-calidad → PR → puente**.
> Las columnas "+ Verificador" indican el agente especializado que debe revisar además.
> Estado: ⬜ pendiente · 🟨 en curso · ✅ hecho · ⛔ bloqueado

**Reglas:** (1) prueba primero; (2) contexto del subagente = sección del Spec + contratos §5 + prueba de aceptación;
(3) guardar el prompt enviado en `alucinaciones/prompts/<ID>.md`; (4) el autor humano explica el PR al puente antes del merge.

---

## F0 — Fundaciones (Integración) · jue 1 – vie 2 oct

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T0.1 | Esqueleto del repo, `requirements.txt` fijado, `.gitignore`, README inicial | — | Estructura §4 | `pip install -r requirements.txt` en venv limpio | auditor-reproducibilidad | ⬜ |
| T0.2 | `src/common/config.py` + `cli.py`: YAML + `--set a.b=c` + `run.py` con subcomandos | T0.1 | `run.py part1/part2/figures` (vacíos) | Test de overrides anidados y tipos (int/float/bool/list) | — | ⬜ |
| T0.3 | `src/common/seeds.py` + `results.py` (escritura JSON con esquema §5.4) | T0.1 | Utilidades | Test de reproducibilidad con generador dummy | — | ⬜ |
| T0.4 | `src/common/counter.py` (`CountedProblem`, presupuesto, `eval_equiv`) | T0.1 | Contador | `test_counter.py`, `test_budget.py` | verificador-matematico | ⬜ |
| T0.5 | Prueba `test_no_network.py` (bloquea `socket` durante experimentos) | T0.2 | Test | Falla si algún experimento intenta conectarse | auditor-reproducibilidad | ⬜ |
| T0.6 | `alucinaciones/` (registro, evidencias, prompts) | — | Carpetas + plantilla | — | cazador-alucinaciones | ✅ (creado con el Spec) |
| T0.7 | Esqueleto del blog MkDocs + hook de figuras + bibtex APA | T0.1 | `mkdocs build` funciona | Build falla con figura no citada y con cita inexistente | revisor-calidad | ⬜ |

---

## F1 — Parte 1 (Equipo Parte 1) · vie 2 – mar 6 oct

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T1.1 | `functions.py`: Rosenbrock y Rastrigin (f, grad, dominio, x*, f*) | T0.4 | Clases §5.1 | `test_gradients.py` (error rel. < 1e-6 en ≥100 puntos), f(x*) = f* | **verificador-matematico** | ⬜ |
| T1.2 | `gd.py`: GD paso fijo con proyección | T1.1 | `optimize()` | Converge en una cuadrática de prueba; respeta presupuesto; registra frames en 2D | verificador-matematico | ⬜ |
| T1.3 | `gd.py`: variante Armijo | T1.2 | `optimize()` | Cuenta evaluaciones de f de la búsqueda lineal; condición de Armijo probada | verificador-matematico | ⬜ |
| T1.4 | `ea.py`: GA real (torneo, BLX-α, mutación gaussiana, elitismo) | T0.4 | `optimize()` | Conteo exacto por generación; individuos dentro del dominio | — | ⬜ |
| T1.5 | `pso.py`: PSO gbest con inercia y manejo de límites | T0.4 | `optimize()` | `test_counter` N·(T+1); partículas dentro del dominio; v_max respetada | verificador-matematico | ⬜ |
| T1.6 | `de.py`: DE/rand/1/bin | T0.4 | `optimize()` | r1≠r2≠r3≠i; j_rand garantiza ≥1 gen del mutante; conteo exacto | verificador-matematico | ⬜ |
| T1.7 | `experiment.py`: 20 configs × 30 semillas, `summary.json`, tablas | T1.2–T1.6 | Resultados | Métricas §6.6; k=2n y k=1 | **analista-experimentos** | ⬜ |
| T1.8 | `configs/part1/demo.yaml` + salida en consola | T1.7 | Demo | < 2 min medido | auditor-reproducibilidad | ⬜ |
| T1.9 | Contraste con SciPy/pyswarms (solo informativo) | T1.7 | Tabla de contraste | Documenta diferencias (`best1bin`, `polish`) | cazador-alucinaciones | ⬜ |

---

## F2 — Parte 2: datos (Equipo Parte 2) · jue 1 – lun 5 oct

> Tareas de **datos**: el implementador es el **curador-datos**; los humanos del equipo verifican a mano lo marcado.

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T2.0 | **Decisión** OSRM local vs. respaldo ORS (humanos) | — | Nota en Spec §14 | Decidido a más tardar **sáb 3-oct** | — | ⬜ |
| T2.1 | Bloque 1: `cities.csv` desde IGN (+ verificación manual de ambiguos) | — | `data/processed/cities.csv` | 47 filas; mapa de control; columna `verificado_manual` completa | **cazador-alucinaciones** | ✅ 2026-10-09 (NGMEP 202603; 39 pruebas; verificación manual: Jose Miguel) |
| T2.2 | `scripts/osrm/README.md` + levantar OSRM local con extracto Geofabrik | T2.0 | Servidor local + fecha del extracto | `exclude=toll` responde OK en Madrid→Barcelona | auditor-reproducibilidad | ⬜ |
| T2.3 | Bloque 2: `descargar_datos.py` rutas (1 081 pares × 2 alternativas) | T2.1, T2.2 | `data/raw/osrm_<fecha>/`, `rutas.csv` | Sin errores; pasos con `ref` y clases; chequeo de simetría en 20 pares | revisor-spec | ⬜ |
| T2.4 | Bloque 3a: `peajes_tramos.csv` (estatales, SEITT, forales/autonómicos) | — | Tabla con fuente y fecha por fila | Ninguna fila sin `fuente_url` y `fecha_consulta`; vigencias AP-68 correctas | **cazador-alucinaciones** | ⬜ |
| T2.5 | Bloque 3b: asignación de peajes a rutas | T2.3, T2.4 | `km_peaje`, `peaje_eur` en `rutas.csv` | Validación de 5 pares (Spec §7.2) documentada; Sevilla–Cádiz = 0 € | cazador-alucinaciones | ⬜ |
| T2.6 | Bloque 4: precio Gasolina 95 E5 (API Ministerio) | — | `combustible.json` + raw con fecha | Media, mediana, nº estaciones | revisor-spec | ⬜ |
| T2.7 | Bloque 5: `vehiculo.yaml` (Corolla Sedán Hybrid 2026 1.8 L 140H, WLTP) | — | Ficha oficial Toyota España + respaldo km77 | Sedán + acabado exacto, WLTP combinado (no NEDC) + fase extra alta si existe, fecha | cazador-alucinaciones | ⬜ |
| T2.8 | `data/fuentes.md` completo + `test_data_integrity.py` | T2.1–T2.7 | Tabla de fuentes | Test pasa | revisor-spec | ⬜ |

---

## F3 — Parte 2: algoritmos (Equipo Parte 2) · sáb 3 – mar 6 oct

> Se puede empezar **antes** de tener los datos reales usando una matriz sintética (distancias euclidianas entre las 47 coordenadas).

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T3.1 | `costos.py`: `matriz_costos(w)` con dos alternativas | T0.3 | Función §5.2 | `test_cost.py` | **verificador-matematico** | ⬜ |
| T3.2 | `exact.py`: DFJ con PuLP + subtours iterativos | T3.1 | `solve()` | `test_exact_small.py` (8 ciudades = fuerza bruta) | verificador-matematico | ⬜ |
| T3.3 | `aco.py`: Ant System + MMAS | T3.1 | `solve()` | Tours válidos; feromona dentro de [τ_min, τ_max] en MMAS; conteo de recorridos | revisor-spec | ⬜ |
| T3.4 | `ga.py`: OX + inversión + intercambio + torneo + elitismo | T3.1 | `solve()` | `test_tsp_operators.py` (10 000 operaciones válidas) | revisor-spec | ⬜ |
| T3.5 | `local_search.py`: 2-opt (opcional) | T3.1 | Función | Nunca empeora el recorrido; recorrido válido | — | ⬜ |
| T3.6 | `experiment.py`: barrido de w + bisección del umbral + gaps | T3.2–T3.4, T2.8 | `sweep_w.json`, historiales | Spec §7.5 | **analista-experimentos** | ⬜ |
| T3.7 | `configs/part2/demo.yaml` | T3.6 | Demo | < 2 min medido | auditor-reproducibilidad | ⬜ |

---

## F4 — Visualización y blog · mié 7 – dom 11 oct

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T4.1 | `src/viz/theme.py` + `style.py` desde el Design System | Design System | Tema Plotly + estilo matplotlib | Aplicado a una figura de muestra | revisor-calidad | ⬜ |
| T4.2 | Figuras Parte 1 (Spec §6.7) | T1.7, T4.1 | HTML/PNG en `blog/docs/figures/` | `run.py figures` regenera todo | revisor-spec | ⬜ |
| T4.3 | GIFs Parte 1 (GD, PSO) | T1.7, T4.1 | `media/*.gif` | Regenerables | — | ⬜ |
| T4.4 | Figuras Parte 2 + mapa interactivo con deslizador de w | T3.6, T4.1 | HTML | Muestra el cambio de ruta en el umbral | revisor-spec | ⬜ |
| T4.5 | GIF Parte 2 (evolución sobre el mapa) | T3.6, T4.1 | `media/tsp_*.gif` | Regenerable | — | ⬜ |
| T4.6 | Redacción de secciones del blog (cada equipo la suya) | T4.2–T4.5 | `blog/docs/*.md` | Hook sin errores; cifras = `summary.json` | **redactor-tecnico** + cazador | ⬜ |
| T4.7 | Bibliografía `references.bib` (cada DOI verificado) | — | `.bib` | Todo DOI resuelve en doi.org; todas citadas | **cazador-alucinaciones** | ⬜ |
| T4.8 | Sección "Uso de IA" + "Cacería de la alucinación" | T4.6 | Secciones | ≥5 hallazgos, ≥3 categorías, con evidencia | cazador-alucinaciones | ⬜ |

---

## F5 — Cierre · lun 12 – jue 15 oct

| ID | Tarea | Fecha | Entregable | Aceptación | Responsable | Estado |
|---|---|---|---|---|---|---|
| T5.1 | Auditoría en clon limpio en otra máquina | lun 12 | Informe | Todo el §9 del Spec en verde | auditor-reproducibilidad + puente | ⬜ |
| T5.2 | Videos individuales (2–3 min, primera persona, evidencia concreta) | lun 12 | 5 videos | Duración y evidencia | cada integrante | ⬜ |
| T5.3 | Publicar blog en GitHub Pages | lun 12 | URL | Enlace al repo incluido | puente | ⬜ |
| T5.4 | **Entrega** | **mar 13, 23:59** | — | — | todos | ⬜ |
| T5.5 | Fichas de estudio + preguntas probables + predicciones en vivo | dom 11 | `docs/sustentacion/` | Cubre todos los módulos | **tutor-sustentacion** | ⬜ |
| T5.6 | Simulacro de sustentación con preguntas al azar | mié 14 | — | Los 5 responden de cualquier módulo | todos | ⬜ |
