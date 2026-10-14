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
| T0.1 | Esqueleto del repo, `requirements.txt` fijado, `.gitignore`, README inicial | — | Estructura §4 | `pip install -r requirements.txt` en venv limpio | auditor-reproducibilidad | ✅ 2026-10-09 (Python 3.12.6; 39 pruebas de T2.1 pasan) |
| T0.2 | `src/common/config.py` + `cli.py`: YAML + `--set a.b=c` + `run.py` con subcomandos | T0.1 | `run.py part1/part2/figures` (vacíos) | Test de overrides anidados y tipos (int/float/bool/list) | — | ✅ 2026-10-09 (4 rondas; YAML 1.2, herencia, regla de bloques; 10/10 mutantes detectados) |
| T0.3 | `src/common/seeds.py` + `results.py` (escritura JSON genérica: UTF-8, sin NaN/inf, atómica; nombres de archivo §5.4) | T0.1 | Utilidades | Test de reproducibilidad con generador dummy | — | ✅ 2026-10-09 (4 rondas; H-09) |
| T0.4 | `src/common/counter.py` (`CountedProblem`, presupuesto, `eval_equiv`) | T0.1 | Contador | `test_counter.py`, `test_budget.py` | verificador-matematico | ✅ 2026-10-09 (4 rondas; 0 anomalías en ~9 M llamadas; H-08) |
| T0.5 | Prueba `test_no_network.py` (bloquea `socket` durante experimentos) | T0.2 | Test | Falla si algún experimento intenta conectarse | auditor-reproducibilidad | ✅ 2026-10-12 (run.py con red bloqueada + ningún módulo de src/ importa red; mutante detectado) |
| T0.6 | `alucinaciones/` (registro, evidencias, prompts) | — | Carpetas + plantilla | — | cazador-alucinaciones | ✅ (creado con el Spec) |
| T0.7 | Esqueleto del blog MkDocs + hook de figuras + bibliografía APA | T0.1 | `mkdocs build` funciona | Build falla con figura no citada y con cita inexistente | revisor-calidad | ✅ 2026-10-12 (hook `reporte.py` + pandoc citeproc APA 7; 15 pruebas; 12 referencias verificadas contra Crossref; H-22, H-23) |

---

## F1 — Parte 1 (Equipo Parte 1) · vie 2 – mar 6 oct

> **Condiciones heredadas de F0 (9-oct):** cada tarea de método (T1.2–T1.6) añade su bloque (`gd:`, `ea:`, `pso:`, `de:`) con **todos** sus parámetros por defecto del Spec a `configs/part1/base.yaml` (si no, `--set pso.c1=…` falla por clave inexistente). T1.7 valida la config **antes** de correr: valores finitos (nada de `.inf`/`.nan`; "sin límite" = `null`) y tipos (`record_frames` bool, `runs`/`base_seed` enteros). Usar `CountedProblem` (`src/common/counter.py`), `make_rng`/`seeds_for_runs` (`src/common/seeds.py`) y `save_json`/`run_filename` (`src/common/results.py`).

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T1.1 | `functions.py`: Rosenbrock y Rastrigin (f, grad, dominio, x*, f*) | T0.4 | Clases §5.1 | `test_gradients.py` (error rel. < 1e-6 en ≥100 puntos), f(x*) = f* | **verificador-matematico** | ✅ |
| T1.2 | `gd.py`: GD paso fijo con proyección | T1.1 | `optimize()` | Converge en una cuadrática de prueba; respeta presupuesto; registra frames en 2D | verificador-matematico | ✅ (gd.py fijo; Armijo en T1.3) |
| T1.3 | `gd.py`: variante Armijo | T1.2 | `optimize()` | Cuenta evaluaciones de f de la búsqueda lineal; condición de Armijo probada | verificador-matematico | ✅ (gd.py armijo; bucle común con fijo) |
| T1.4 | `ea.py`: EA esquema de clase (élite + mutantes + cruce de un punto, N=50; Spec §6.4 v1.4; bloque `ea:` en `base.yaml`) | T0.4 | `optimize()` + `tests/test_ea.py` | Conteo N + T·(N − n_élite) con élite en caché (N·(T+1) si `reevaluar_elite`); truncado §6.2; dominio; un gen mutado con σ poblacional; punto de cruce ∈ {1,…,d−1}; élite por f actual; reproducible; `esquema` ≠ `clase` falla. Pruebas: ver `docs/spec/propuestas/CAMBIO-EA.md` §12 | verificador-matematico | ✅ |
| T1.5 | `pso.py`: PSO gbest con inercia y manejo de límites | T0.4 | `optimize()` | `test_counter` N·(T+1); partículas dentro del dominio; v_max respetada | verificador-matematico | ✅ 2026-10-12 (`pso.py` + `tests/test_pso.py`, 163 pruebas; suite 677 passed; revisor-spec ✅, revisor-calidad ✅, verificador ✅ 34/36 mutantes muertos, cazador ✅; H-29, H-30, H-31) |
| T1.6 | `de.py`: DE/rand/1/bin | T0.4 | `optimize()` | r1≠r2≠r3≠i; j_rand garantiza ≥1 gen del mutante; conteo exacto | verificador-matematico | ✅ 2026-10-12 (`de.py` + `tests/test_de.py`, 119 pruebas; suite 981 passed; revisor-spec ✅, revisor-calidad ✅ (M2–M7 aplicadas), verificador ✅ reimplementación bit a bit y 25/26 mutantes muertos (M11 equivalente); H-32) |
| T1.6b | **[PROPUESTA — pendiente de Daniel]** Refactor común de la Parte 1 sobre lo entregado en **T1.4 (EA), T1.5 (PSO) y T1.6 (DE)**; solo legibilidad, no toca `gd.py` (T1.2–T1.3), `functions.py` (T1.1) ni `src/common/`: `src/part1/_comun.py` con las utilidades compartidas; `ea.py`, `pso.py` y `de.py` sin código duplicado y sin importarse entre sí (`docs/spec/propuestas/REFACTOR-PARTE1-COMUN.md`) | T1.4–T1.6 | `_comun.py` + `tests/test_comun.py` | Salidas idénticas bit a bit antes/después (EA, PSO, DE × 2 funciones × 2D/3D × 30 semillas); suite completa sin fallos; `pso.py` y `de.py` no importan de `ea.py`; sin cambios en contratos §5.1, mensajes de error ni `base.yaml`; pruebas estáticas (≤ 100 caracteres, celdas `# %%`) también sobre `_comun.py` | verificador-matematico | ✅ 2026-10-12 implementado, **pendiente de la aprobación de Daniel** (`_comun.py` 324 líneas + `tests/test_comun.py` 111 casos; ea/pso/de −275 líneas; huella de 360 corridas idéntica; suite 1496 passed, mismos 2 fallos previos de la Parte 2; revisor-spec ✅, revisor-calidad ✅ 8 mejoras opcionales, verificador ✅ 18 960 corridas y 750 casos de `validar_real` sin diferencias; cierra M1, **no** M8; sin candidatos) |
| T1.7 | `experiment.py`: 20 configs × 30 semillas, `summary.json`, tablas (el EA lee su bloque `ea:`; `n_grad = 0`) | T1.2–T1.6 (T1.6b recomendada antes, no bloquea) | Resultados | Métricas §6.6; k=2n y k=1; cada JSON de corrida con las claves exactas de §5.4 (`func, dim, method, seed, k, budget, config, result`) usando `run_filename` y la semilla efectiva | **analista-experimentos** | ✅ 2026-10-13 (`corrida.py`, `metricas.py`, `experiment.py` + 463 pruebas; `run.py part1` conectado; suite 2143 passed y los 2 fallos previos de la Parte 2; experimento real 9 min 39 s, 600 + 240 JSON, 193 MB; revisor-spec ✅, revisor-calidad ✅ ronda 2, analista ✅ comparación justa y 7 avisos legítimos, verificador ✅ 40 configuraciones recalculadas sin discrepancias; H-36, H-37; pendiente de Daniel) |
| T1.8 | `configs/part1/demo.yaml` + salida en consola | T1.7 | Demo | < 2 min medido | auditor-reproducibilidad | ✅ 2026-10-13 (clave `figura_trayectoria`, `src/viz/part1_demo.py` + `tests/test_part1_demo.py`; el demo escribe `results/data/part1_demo/trayectoria_rastrigin_2d.png` e imprime la ruta y el tiempo; auditor: 3,71–3,82 s en 3 repeticiones en la máquina de desarrollo, determinista byte a byte, `--set` y sin red ✅; falta medir en otra máquina (§9, T5.1); implementador 2 rondas, revisor-spec ✅, revisor-calidad ✅; H-51, H-52, H-53; pendiente de Daniel) |
| T1.9 | Contraste con SciPy/pyswarms (solo informativo) | T1.7 | Tabla de contraste | Documenta diferencias (`best1bin`, `polish`) | cazador-alucinaciones | ⬜ |
| T1.10 | Optimización de hiperparámetros (Spec §6.9): búsqueda aleatoria con igual esfuerzo por método, experimento afinado y comparación contra los valores por defecto | T1.7 | `hpo.py`, `hpo_experimento.py`, `run.py hpo`, `configs/part1/tuned.yaml`, `results/data/part1_hpo/`, `results/data/part1_tuned/`, `comparacion.csv` | R1–R8 de §6.9 (mismos ensayos y semillas por unidad, semillas de ajuste disjuntas de 0–29, ensayo 0 = defecto, selección por rangos con recorte a 1e-6, `tuned.yaml` solo con lo que cambió, resultados por defecto intactos) | analista-experimentos | ✅ 2026-10-13 (`hpo.py`, `hpo_experimento.py` + 222 pruebas; `run.py hpo`; demo 7 s; HPO real 406 s con 6 procesos, 3 000 corridas de ajuste (600 por método), 732 KB; revisor-spec ✅ y revisor-calidad ✅ en ronda 2; verificador 6/6 ganadores; analista: mejoras claras en EA y gdarmijo Rosenbrock, retrocesos en PSO/DE Rastrigin compatibles con sobreajuste a 5 semillas; H-38; pendiente de Daniel). **Corrección T1.10b (13-oct):** el defecto solo se reemplaza con un rango medio estrictamente menor (antes un desempate de una corrida bastaba); reanudación en 110 s sin repetir corridas (3 000); pso y de vuelven al defecto; evidencia de la regla anterior en `results/data/part1_hpo/regla_v1/`; H-39, H-40 |
| T1.11 | Blog: sección 03 al día con T1.7 (sensibilidad k = 1, métricas, sensibilidad η = 1/L) y documentación de la HPO en las secciones 03, 04, 08 y 11 | T1.7, T1.10 | `blog/secciones/03`, `04`, `08`, `11` | Cifras solo desde los archivos de resultados (`evidencias/H-T1.11_cifras.txt`); citas solo de `references.bib`; `mkdocs --strict` sin errores | cazador-alucinaciones, auditor-reproducibilidad | ✅ 2026-10-13 (redactor 2 rondas; cazador 112 afirmaciones, 0 cifras erróneas, 4 imprecisiones corregidas; auditor 4 comandos exit 0 y HPO regenerada idéntica byte a byte; revisor-spec: 6 líneas > 120 corregidas; build OK; suite 2369 passed y los 5 fallos LF previos; H-42, H-43; 4 TODO(cita) para T4.7) |

---

## F2 — Parte 2: datos (Equipo Parte 2) · jue 1 – lun 5 oct

> Tareas de **datos**: el implementador es el **curador-datos**; los humanos del equipo verifican a mano lo marcado.

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T2.0 | **Decisión** OSRM local vs. respaldo ORS (humanos) | — | Nota en Spec §14 | Decidido a más tardar **sáb 3-oct** | — | ✅ 2026-10-10 (OSRM local con Docker; Spec v1.3) |
| T2.1 | Bloque 1: `cities.csv` desde IGN (+ verificación manual de ambiguos) | — | `data/processed/cities.csv` | 47 filas; mapa de control; columna `verificado_manual` completa | **cazador-alucinaciones** | ✅ 2026-10-09 (NGMEP 202603; 39 pruebas; verificación manual: Jose Miguel) |
| T2.2 | `scripts/osrm/README.md` + levantar OSRM local con extracto Geofabrik | T2.0 | Servidor local + fecha del extracto | `exclude=toll` responde OK en Madrid→Barcelona | auditor-reproducibilidad | ✅ 2026-10-10 (OSRM v26.10.0 arm64, extracto `spain-261001` = datos 1-oct 20:22Z; puerto 5001; auditor ✅ con 8 menores) |
| T2.3 | Bloque 2: `descargar_datos.py` rutas (1 081 pares × 2 alternativas) | T2.1, T2.2 | `data/raw/osrm_<fecha>/` (no versionado), `rutas.csv`, `rutas_resumen.json`, `rutas_pasos_peaje.csv` (Spec v1.5) | Sin errores; pasos con `ref` y clases; chequeo de simetría en 20 pares | revisor-spec | 🟡 2026-10-11 código listo (revisor-spec ✅, revisor-calidad ✅ en 2.ª ronda; 332 pruebas); ✅ 2026-10-12: ejecutada por Jose Miguel en Windows; corrida vigente `osrm_2026-10-12` con `--threads 1`, arranque limpio y una sola corrida (Spec v1.8). Resultados: 1081/1081 pares, 547 sin peaje y 26 `sin_peaje` con clase `toll` que cobra T2.5; el contraste con T2.2 es exacto. Diagnóstico y H-16 en `alucinaciones/` |
| T2.4 | Bloque 3a: `peajes_tramos.csv` (estatales, SEITT, forales/autonómicos) | — | Tabla con fuente y fecha por fila | Ninguna fila sin `fuente_url` y `fecha_consulta`; vigencias AP-68 correctas | **cazador-alucinaciones** | ✅ 2026-10-12 (asumida por Jose Miguel; 56 tramos, km del Catálogo RCE + 11 aproximados en OSM; Spec v1.9; revisor-spec ✅, revisor-calidad ✅ (6 rondas), cazador ✅ CONFORME; H-17, H-18; 512 pruebas) |
| T2.5 | Bloque 3b: asignación de peajes a rutas | T2.3, T2.4 | `vias_peaje`, `km_peaje`, `peaje_eur` en `rutas.csv` (desde `rutas_pasos_peaje.csv`) | Validación de 5 pares (Spec §7.2) documentada; Sevilla–Cádiz = 0 € | cazador-alucinaciones | ✅ 2026-10-12 (asumida por Jose Miguel; suma de tramos [DECIDIDO]; 5 pares validados, Bilbao–Zaragoza 41,50 € frente a 39,90 € publicado; revisor-spec ✅, revisor-calidad ✅, cazador ✅ CONFORME; sin hallazgos factuales nuevos, H-20 débil; Spec v1.10) |
| T2.6 | Bloque 4: precio Gasolina 95 E5 (API Ministerio) | — | `combustible.json` + raw con fecha | Media, mediana, nº estaciones | revisor-spec | ✅ 2026-10-11 (asumida por Jose Miguel; media **peninsular** 1,8318 €/l, 10 171 estaciones, Spec v1.6; revisor-spec ✅ 2.ª ronda, revisor-calidad ✅ + pulido; 418 pruebas) |
| T2.7 | Bloque 5: `vehiculo.yaml` (Corolla Sedán Hybrid 2026 1.8 L 140H, WLTP) | — | Ficha oficial Toyota España + respaldo km77 | Sedán + acabado exacto, WLTP combinado (no NEDC) + fase extra alta si existe, fecha | cazador-alucinaciones | ✅ 2026-10-11 (asumida por Jose Miguel; Style Plus 140H e-CVT MY27, 4,6 l/100 km, Gasolina 95 E5 según el catálogo 09/2023; extra alta 5,6–6,2 como sensibilidad; Spec v1.7; revisor-spec ✅, cazador ✅; 425 pruebas) |
| T2.8 | `data/fuentes.md` completo + `test_data_integrity.py` | T2.1–T2.7 | Tabla de fuentes | Test pasa | revisor-spec | ✅ 2026-10-12 (curador-datos, 3 rondas; revisor-spec ✅ 2.ª ronda, revisor-calidad ✅ 2.ª ronda; 51 pruebas nuevas, 627 en total; `AP68-POST-VI` sin tarifa publicada, pendiente de decisión humana) |

---

## F3 — Parte 2: algoritmos (Equipo Parte 2) · sáb 3 – mar 6 oct

> **Condiciones heredadas de F0 (9-oct):** T3.3/T3.4 añaden los bloques `aco:` (incl. `iteraciones`, §7.4; desde v1.16, 1 099 ACO / 348 GA = presupuesto común), `ga:` y `peajes:` con **todos** sus parámetros a `configs/part2/base.yaml`. T3.6 valida la config antes de correr (finita y con tipos correctos) y decide si la prueba de humo de `run.py part2` (tests/test_config.py) se marca como lenta al conectar el manejador real. Solver exacto: PuLP 4.0 + HiGHS con `problema.add_variable(...)` (H-07).

> Se puede empezar **antes** de tener los datos reales usando una matriz sintética (distancias euclidianas entre las 47 coordenadas).

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T3.1 | `costos.py`: `matriz_costos(w)` con dos alternativas | T0.3 | Función §5.2 | `test_cost.py` | **verificador-matematico** | ✅ |
| T3.2 | `exact.py`: DFJ con PuLP + subtours iterativos | T3.1 | `solve()` | `test_exact.py` (5–8 ciudades = fuerza bruta) | verificador-matematico | ✅ 13-oct (puente): verificación de umbrales y gap, Spec v1.20 |
| T3.3 | `aco.py`: Ant System + MMAS | T3.1 | `solve()` | Tours válidos; feromona dentro de [τ_min, τ_max] en MMAS; conteo de recorridos; 8 ciudades = fuerza bruta (Spec §7.4.1) | revisor-spec + verificador-matematico | ✅ |
| T3.4 | `ga.py`: OX + inversión + intercambio + torneo + elitismo | T3.1 | `solve()` | `test_tsp_operators.py` (10 000 operaciones válidas) | revisor-spec | ✅ |
| T3.5 | `local_search.py`: 2-opt (opcional) | T3.1 | Función | Nunca empeora el recorrido; recorrido válido | — | ⬜ **opcional** (no está en el enunciado; solo si sobra tiempo) |
| T3.6 | `experiment.py`: barrido de w + umbral por envolvente de candidatos (Spec v1.16) + gaps + sensibilidad de consumo con MMAS; claves `consumo_l100`/`precio_l` en `configs/part2/base.yaml` | T3.3–T3.4, T2.8 | `sweep_w.json`, historiales | Spec §7.5 | **analista-experimentos** | ✅ |
| T3.7 | `configs/part2/demo.yaml` (Spec v1.17: MMAS, 10 corridas; v1.19: 1 000 iteraciones, gap frente al mejor conocido, figura del recorrido) | T3.6 | Demo | < 2 min medido (~18 s con 1 000 iteraciones; falta medir en otra máquina, §9) | auditor-reproducibilidad | ✅ |

---

## F4 — Visualización y blog · mié 7 – dom 11 oct

| ID | Tarea | Depende | Entregable | Aceptación | + Verificador | Estado |
|---|---|---|---|---|---|---|
| T4.1 | `src/viz/theme.py` + `style.py` + `ds.css` desde la skill `apple-design` (tipografía, materiales, accesibilidad) + **paleta de colores propia** | Skill `apple-design` | Tema Plotly + estilo matplotlib + CSS | Aplicado a una figura de muestra; contraste verificado en claro/oscuro | revisor-calidad | ✅ 2026-10-12 (src/viz/paleta.py fuente única; tema Plotly + estilo matplotlib; paleta validada con validate_palette.js; 5 pruebas) |
| T4.2 | Figuras Parte 1 (Spec §6.7) | T1.7, T4.1 | HTML/PNG en `blog/docs/figures/` | `run.py figures` regenera todo | revisor-spec | ✅ 2026-10-13 (8 HTML `part1_*.html` con ids fijos, tabla en `blog/README.md`: 2 contornos, convergencia y cajas por defecto y por defecto contra afinado, deslizador de η y superficie 3D con el enjambre; `src/viz/part1_datos.py`, `part1_interactivas.py`, `src/part1/eta_deslizador.py`, `scripts/part1_eta_deslizador.py`, `results/data/part1/eta_deslizador.json`; implementador A + B (B en 2 rondas), revisor-spec ✅ (600 comparaciones de curvas y 40 cajas recalculadas, 15 mutantes), revisor-calidad ✅; la superficie 3D no se pudo ver renderizada sin pantalla; en un clon limpio solo se regeneran 3 de 8 porque `runs/` no se versiona; H-45, H-46; pendiente de Daniel) |
| T4.3 | GIFs Parte 1 (GD, PSO) | T1.7, T4.1 | `media/*.gif` | Regenerables | — | ✅ 2026-10-13 (3 GIF en `media/` copiados a `blog/docs/figures/`, ids en `blog/README.md`: `gd_rosenbrock_2d.gif` 41 fotogramas, 274 KB, y `gd_rastrigin_2d.gif` 32, 109 KB, con gdfijo y gdarmijo superpuestos; `pso_rastrigin_2d.gif` 38, 389 KB; semilla 0, config por defecto, marcas geométricas de iteración ≤ 45, paleta común por GIF; datos en `results/data/part1/gif_trayectorias.json` (61 KB, versionado, `python scripts/part1_gif_trayectorias.py`), dibujo con `python run.py figures`; `src/part1/gif_trayectorias.py`, `src/viz/part1_gifs.py`; implementador A + B (B en 2 rondas: paleta por fotograma cambiaba los colores y la estrella del mejor tapaba el enjambre), revisor-spec ✅ y revisor-calidad ✅ (opcionales aplicados), 5/5 mutantes del prompt muertos; regenerable en un clon limpio; pendiente de Daniel) |
| T4.4 | Figuras Parte 2 + mapa interactivo con deslizador de w | T3.6, T4.1 | HTML | Muestra el cambio de ruta en el umbral | revisor-spec | ✅ 2026-10-13 (3 HTML en `blog/docs/figures/part2_*.html`; deslizador 11 w + w≈12,28 cruza los 3 umbrales; `run.py figures`; revisión hecha por el orquestador, sin revisor-spec, a pedido del equipo) |
| T4.5 | GIF Parte 2 (evolución sobre el mapa) | T3.6, T4.1 | `media/tsp_*.gif` | Regenerable | — | ✅ 2026-10-13 (`media/tsp_mmas_w25.gif` 15 fotogramas, `tsp_ga_w25.gif` 24; mejor corrida en w = 25, un fotograma por mejora, contorno IGN; `run.py figures`, bytes idénticos al regenerar) |
| T4.6 | Redacción de secciones del blog (cada equipo la suya) | T4.2–T4.5 | `blog/docs/*.md` | Hook sin errores; cifras = `summary.json` | **redactor-tecnico** + cazador | ⬜ Parte 1 ✅ 2026-10-13 (secciones 02, 03, 04, 08, 09 y 11; redactor 1 ronda; cazador: 424 celdas de tabla recalculadas, 0 erróneas, 1 errónea y 8 imprecisas en prosa corregidas; H-49, H-50; build OK; sin commit) · Parte 2 en borrador · faltan 00 y 01 (puente) |
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
