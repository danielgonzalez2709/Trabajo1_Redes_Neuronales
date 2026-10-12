# 🧠 Memoria del proyecto (contexto vivo)

> **Para qué:** que cualquier integrante (o sesión de Claude / subagente) sepa en 2 minutos **dónde estamos, qué se decidió
> y qué sigue**. Se carga automáticamente en cada sesión de Claude Code (vía `CLAUDE.md`).
>
> **Reglas de actualización:**
> 1. Actualizar al **cerrar una tarea del PLAN, fusionar un PR, terminar una reunión o tomar una decisión**.
> 2. Mantenerlo **corto** (≤ 150 líneas): aquí va el *estado*; el detalle vive en `docs/spec/SPEC.md` y `docs/spec/PLAN.md`.
> 3. La bitácora va **de lo más nuevo a lo más viejo**; cuando pase de ~20 entradas, resumir las antiguas en una línea.
> 4. Lo que sea decisión se copia también al Spec (el Spec manda).

---

## 📍 Estado actual
| | |
|---|---|
| Última actualización | 2026-10-12 |
| Fase | **F0 — Fundaciones** T0.1–T0.4 ✅ (PR de `integracion/f0-fundaciones` → `main`; faltan T0.5 sin-red y T0.7 blog) · **F1 — Parte 1** en curso (T1.1 ✅, T1.4 ✅, T1.5 ✅) · **F2 — Datos Parte 2** en curso (T2.1 ✅, PR #1) |
| Próxima tarea | Ambos equipos: **traer `main` a su rama** tras fusionar el PR de F0. Parte 1: **T1.2 GD de paso fijo**, luego **T1.3 Armijo**, T1.6 DE (adoptar la misma validación que `ea.py`/`pso.py`: clave desconocida y presupuesto < 1 → error claro; las funciones compartidas `validar_limites`, `validar_poblacion`, `leer_record_frames`, `construir_frame` viven hoy en `ea.py`). Revisión de Daniel a T1.5 y PR. Parte 2: **T2.0 OSRM (bloqueo crítico)** → T2.2; en paralelo T2.4 peajes, T2.6 combustible, T2.7 vehículo. Integración: T0.5 (prueba sin red), T0.7 (blog MkDocs) |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 1) |
| Sustentación | jue 15-oct-2026, 6 p. m. (por confirmar) |

## 👥 Equipo
| Rol | Quién |
|---|---|
| Parte 1 — Optimización numérica | 2 integrantes (nombres: Edinson y Juan Jose) |
| Parte 2 — TSP por España | 2 integrantes, incluida Camila |
| Puente: integración, repositorio, cacería de alucinaciones | Daniel |

## ✅ Decisiones vigentes (resumen — detalle en el Spec)
- Python 3.12, algoritmos desde cero con numpy; librerías de optimización solo para contrastar.
- Parte 1: **Rosenbrock [−2.048, 2.048]ⁿ + Rastrigin [−5.12, 5.12]ⁿ**, 2D y 3D; GD (fijo + Armijo), EA, PSO, DE.
- Conteo: 1 ∇f = 2n evaluaciones de f (sensibilidad k=1); presupuesto 10 000·n; 30 corridas; éxito f − f* ≤ 1e-4.
- η: Rastrigin 2e-3 (garantía global, L ≈ 396.8); Rosenbrock 1e-3 (empírico, sin garantía global; L ≈ 5 971 en 2D).
- Parte 2: fecha de corte **1-oct-2026**; OSRM **local** (el servidor público no admite `exclude=toll`); dos alternativas por par
  (rápida / sin peaje); peajes oficiales + forales; Gasolina 95 E5 media nacional; **Toyota Corolla Sedán Hybrid 2026 1.8 L (140H)**.
- Bloque 1 (Spec v1.2): coordenadas del **NGMEP 202603** (fila "Capital de municipio", descarga manual por reCAPTCHA);
  IGR Poblaciones = contraste (≤ 2,5 km); Nominatim solo control. Crudos versionados salvo el `.mdb`.
- **EA de la Parte 1 (Spec v1.4, 12-oct):** esquema de clase (IRNA202602), N=50, frac_e=0.15 / frac_m=0.10 / frac_c=0.75; mutación de un gen
  con σ poblacional; cruce de un punto ∈ {1,…,d−1}; élite **no se reevalúa** (50 + 42 por generación); parada por presupuesto §6.2;
  `ea.esquema` solo `clase` (torneo/BLX-α queda reservado, no implementado).
- **PSO de la Parte 1 (T1.5, 12-oct):** gbest con inercia; N=30, w=0.7298, c1=c2=1.49618 (cifras redondeadas de la constricción con φ = 4.1;
  **cita de Clerc & Kennedy sin verificar → no citar**), `vmax_frac`=0.2 (v_max = 0.2·(ub−lb)), **v inicial = 0**, frontera = recortar y v=0 solo en la
  componente que salió; n_f = N·(T+1); en 2D con 20 000: 666 frames; `pso.iteraciones: null` (parar por presupuesto), `vmax_frac: null` = sin límite; aviso si w ≥ 1.
- Algoritmos Parte 2: AS → MMAS, GA (OX + inversión), 2-opt opcional, óptimo exacto con PuLP como referencia.
- Front: **Material for MkDocs** + Plotly (interactivas) + matplotlib con estilo DS (GIF). Todo Python.
- Desarrollo con **Subagent Driven Development**: 10 agentes en `.claude/agents/`, protocolo en `CLAUDE.md`.
- **F0 disponible para los equipos** (Spec §4.1, §5.1, §5.4): `run.py part1|part2|figures --config … --set clave=valor`;
  configs con herencia (`hereda: base.yaml`; **cada método añade su bloque completo a `base.yaml`**); YAML 1.2 (`1e-3` es número,
  `010` es 10, `no` es texto); un bloque no se reemplaza por un valor; `CountedProblem(func, k, budget)` lanza `BudgetExhausted`
  antes de exceder y lee dominio/dimensión de `problem.func`; `make_rng(base_seed, run_id)`; `save_json` (sin NaN/inf) y
  `run_filename(func, dim, method, seed)` con identificadores `^[a-z0-9]+$` (`gdfijo`, `gdarmijo`, `ea`, `pso`, `de`).

## ⏳ Pendientes / bloqueos
- [ ] 🔴 **BLOQUEO CRÍTICO — OSRM:** sin decisión (venció el sáb 3-oct). Sin rutas no hay matriz de costos, ni ACO/GA con datos reales, ni barrido del valor de la hora. Decidir ya: OSRM local (Docker) o respaldo openrouteservice.
- [ ] **Acabado** del Corolla Sedán 140H (de la ficha oficial de Toyota España).
- [x] **Design System:** skill `apple-design` (Emil Kowalski). Falta la **paleta de colores** (T4.1); la skill no la define.
- [ ] ¿Escenario opcional `post_ap68`?
- [ ] Confirmar fecha/hora de la sustentación.
- [ ] Prompts literales para la cacería: ~~H-01, H-03 (Daniel)~~ ✅ en `alucinaciones/prompts/asesoria_puente_claude.md`; H-02 (Camila) pendiente.
- [ ] **T1.4 — cambios al Spec que decide Daniel (el Spec lo edita el equipo):** (a) "round de Python (mitades al par)" en §6.4; (b) añadir a la validación
  `n_cruzantes > N` → error (N=3 con defaults); (c) corregir "σ → 0 al converger" por "colapso prematuro" (H-14); (d) aclarar que `frac_c` bajo no reduce el cruce
  si el relleno lo anula; (e) comentario de cabecera de `base.yaml` desactualizado. Y la **revisión de Daniel al Spec v1.4** sigue pendiente.
- [ ] **T1.4 — 7 mejoras opcionales de revisor-calidad** (`alucinaciones/prompts/T1.4.md`, sección D) sin aplicar; no bloquean.
- [ ] **T1.5 — cambios al Spec que decide Daniel:** (a) en §6.4 PSO: v inicial = 0, claves `iteraciones` y `vmax_frac` (con `null` = sin límite) y aviso si w ≥ 1;
  (b) `SPEC.md:291`: 1.49618 es cifra derivada (χ·φ/2), no un valor del artículo (H-16). Y la **revisión de Daniel a T1.5** y el PR.
- [ ] **T1.5 — pendientes menores:** (a) verificar la cita primaria de Clerc & Kennedy (2002; DOI candidato verificado en Crossref, texto no accesible); (b) si todas las
  evaluaciones dan NaN o +inf, `problem.best_x` es None y `optimize` lanza `AttributeError` (`pso.py` y `ea.py`; no ocurre con Rosenbrock/Rastrigin) — decidir si se añade una guarda;
  (c) la prueba `test_la_particula_que_es_g…solo_se_mueve_por_inercia` conserva un nombre impreciso (opcional); (d) en el blog documentar: el líder no se mueve con v(0)=0 hasta que g cambie
  y "PSO garantiza el óptimo global" es falso (Rastrigin 3D: 26/30 éxitos).
- [ ] `revisor-spec` y `revisor-calidad` no cargaban como tipo de agente en la sesión de la Parte 2: reiniciar Claude Code desde la raíz del repo (en la sesión del puente sí cargan).

## 🎯 Cacería de alucinaciones
Candidatos: **17** (H-01 OSRM público · H-02 AP-68 · H-03 paso de GD · H-04 ORIGENCOOR · H-05 capital = municipio · H-06 Mérida ·
H-07 PuLP 4 sin CBC · H-08 contador y redondeo · H-09 np.float64 · H-10 prueba que no falla · H-12 .pyc obsoleto · H-13 TestFunction ·
**H-14** "σ→0 al converger" · **H-15** prompt 714 frames en 3D · **H-16** 1.49618 atribuido a Clerc & Kennedy (cifra derivada) ·
**H-17** línea base "513 passed, 1 skipped" falsa · **H-18** papel de b_i con v = 0 / "el líder solo se mueve por inercia") — confirmados: **2** (H-04, H-05) —
categorías: Datos (5), Matemáticas (1), Código (8), Bibliografía (1), Conceptos (2); H-16 y H-18 de severidad baja, pendientes de confirmar por el puente. Técnica útil: **prueba de mutación**.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-12 | Andrés (Parte 1) + Claude (SDD) | **T1.5 ✅** (`pso.py` + `tests/test_pso.py`, 163 pruebas; suite 677 passed): `optimize` orquestador + 9 componentes puros (SRP/DIP) con R1/R2 inyectadas, celdas `# %%` con LaTeX; en `ea.py` solo se quitó el `_` de 4 funciones compartidas (renombrado mecánico autorizado). Rondas: implementador ×5, revisor-spec ✅ (M1–M2 de pruebas corregidos), revisor-calidad ✅ (7 mejoras aplicadas), verificador-matematico ✅ (36 mutantes, 34 muertos, 2 equivalentes; w y c = constricción φ = 4.1 redondeada), cazador ✅ (fuente Clerc & Kennedy parcial). Candidatos **H-16**, **H-17**, **H-18**. Pendiente: guarda NaN (decidir), cita primaria, cambios al Spec, PR y revisión de Daniel. Planeación y prompts en `alucinaciones/prompts/T1.5.md`. |
| 2026-10-12 | Andrés (Parte 1) + Claude (SDD) | **T1.4 ✅** (`ea.py` + `tests/test_ea.py`, 165 pruebas; suite 513 passed): `optimize` orquestador + componentes puros (SRP/DIP), celdas `# %%` con LaTeX; revisor-spec ✅ ronda 1, revisor-calidad ✅ ronda 2 (B1 celdas), verificador-matematico ✅ (EA independiente bit a bit, 20 mutantes muertos). Candidatos **H-14** (Conceptos) y **H-15** (prompt). Pendiente: PR y revisión de Daniel. |
| 2026-10-12 | Andrés (Parte 1) + Claude | **T1.4 planeada** (aún sin código): `optimize` como orquestador + componentes puros (`ParametrosEA`, población inicial, evaluar, élite, mutación, cruce, ensamblar) con `rng` y evaluador inyectados (SRP/DIP), `ea.py` en celdas `# %%` con LaTeX y docstrings numpy; `frames` según §5.1 sin campos extra; `ea.generaciones` se conserva (null = presupuesto). Planeación y mensajes literales en `alucinaciones/prompts/T1.4.md`. Pendiente: revisión de Daniel del Spec v1.4 antes de despachar al implementador. |
| 2026-10-12 | Andrés (Parte 1) + Claude | **Spec v1.4**: EA pasa al esquema de clase (§6.2 y §6.4, notas, §10, §11, §13); PLAN T1.4 y T1.7 ajustados. Propuesta en `docs/spec/propuestas/CAMBIO-EA.md`; prompt en `alucinaciones/prompts/CAMBIO-EA.md`. Excepción única autorizada a "Claude no edita Spec/PLAN". Falta que Daniel (puente) revise el cambio. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **T1.1 ✅** (`functions.py`, 73 pruebas; suite 347 passed, 1 skipped): revisor-spec, revisor-calidad y verificador-matematico aprueban en ronda 1; fórmulas, x*, f* y dominio de Rastrigin verificados contra SFU (12-oct). Candidatos **H-12** y **H-13** (Código). |
| 2026-10-09 | Daniel + Claude (SDD) | **T0.2, T0.3, T0.4 ✅** con subagentes: implementador → revisor-spec → revisor-calidad (+ verificador-matemático en T0.4), 2–4 rondas cada una; 274 pruebas en total. Spec §4.1/§5.1/§5.4 ampliado (YAML 1.2, herencia, regla de bloques, identificadores, semilla efectiva, BudgetExhausted). Hallazgos **H-08**, **H-09**, **H-10** (Código). |
| 2026-10-09 | Daniel + Claude | PR #1 revisado (39/39 pruebas, regeneración byte a byte) y fusionado (merge commit). **T0.1 ✅**: `requirements.txt` (Python 3.12.6, `pip freeze`), esqueleto `src/`, `configs/`, `results/`, `media/`. Hallazgos nuevos **H-06** (Mérida) y **H-07** (PuLP 4 sin CBC y API nueva). Design System = skill `apple-design`. Spec v1.3. |
| 2026-10-09 | Jose Miguel + Claude | **T2.1 ✅**: `cities.csv` (47 capitales, NGMEP 202603), 39 pruebas, mapa de control; revisor-spec ✅, revisor-calidad ✅ (2.ª ronda), cazador ✅. Verificación manual: Jose Miguel (8-oct). Spec v1.2. H-04 y H-05 confirmados. |
| 2026-10-01 | Daniel + Claude | README temporal, esta memoria (cargada desde `CLAUDE.md`) y ramas `parte1-optimizacion-numerica` / `parte2-tsp-espana`. Primer push (`2cd005b`): Spec v1.1, PLAN, agentes, registro. |
| 2026-10-01 | Equipo | Decidido: fecha de corte 1-oct, Corolla Sedán 140H, dominio Rosenbrock [−2.048, 2.048]ⁿ (respaldado con experimento). |
| 2026-10-01 | Equipo Parte 2 | Propuesta de datos en 5 bloques (documento de Camila) incorporada al Spec. |
| 2026-09-29 | Equipo | División: Parte 1 (2), Parte 2 (2), Daniel puente. Funciones Rosenbrock + Rastrigin. Front 100 % Python. |
