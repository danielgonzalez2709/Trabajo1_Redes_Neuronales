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
| Última actualización | 2026-10-09 |
| Fase | **F0 — Fundaciones** T0.1–T0.4 ✅ (PR de `integracion/f0-fundaciones` → `main`; faltan T0.5 sin-red y T0.7 blog) · **F2 — Datos Parte 2** en curso (T2.1 ✅, PR #1) |
| Próxima tarea | Ambos equipos: **traer `main` a su rama** tras fusionar el PR de F0. Parte 1: **arrancar T1.1** (rama sin commits). Parte 2: **T2.0 OSRM (bloqueo crítico)** → T2.2; en paralelo T2.4 peajes, T2.6 combustible, T2.7 vehículo. Integración: T0.5 (prueba sin red), T0.7 (blog MkDocs) |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 4) |
| Sustentación | jue 15-oct-2026, 6 p. m. (por confirmar) |

## 👥 Equipo
| Rol | Quién |
|---|---|
| Parte 1 — Optimización numérica | 2 integrantes (nombres: por completar) |
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
- [ ] `revisor-spec` y `revisor-calidad` no cargaban como tipo de agente en la sesión de la Parte 2: reiniciar Claude Code desde la raíz del repo (en la sesión del puente sí cargan).

## 🎯 Cacería de alucinaciones
Candidatos: **10** (H-01 OSRM público · H-02 AP-68 · H-03 paso de GD · H-04 ORIGENCOOR · H-05 capital = municipio · H-06 Mérida ·
H-07 PuLP 4 sin CBC · H-08 contador y redondeo · H-09 np.float64 · H-10 prueba que no falla) — confirmados: **2** (H-04, H-05) —
categorías: Datos (5), Matemáticas (1), **Código (4)**. Faltan Bibliografía/Conceptos para tener margen. Técnica útil: **prueba de mutación**.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-09 | Daniel + Claude (SDD) | **T0.2, T0.3, T0.4 ✅** con subagentes: implementador → revisor-spec → revisor-calidad (+ verificador-matemático en T0.4), 2–4 rondas cada una; 274 pruebas en total. Spec §4.1/§5.1/§5.4 ampliado (YAML 1.2, herencia, regla de bloques, identificadores, semilla efectiva, BudgetExhausted). Hallazgos **H-08**, **H-09**, **H-10** (Código). |
| 2026-10-09 | Daniel + Claude | PR #1 revisado (39/39 pruebas, regeneración byte a byte) y fusionado (merge commit). **T0.1 ✅**: `requirements.txt` (Python 3.12.6, `pip freeze`), esqueleto `src/`, `configs/`, `results/`, `media/`. Hallazgos nuevos **H-06** (Mérida) y **H-07** (PuLP 4 sin CBC y API nueva). Design System = skill `apple-design`. Spec v1.3. |
| 2026-10-09 | Jose Miguel + Claude | **T2.1 ✅**: `cities.csv` (47 capitales, NGMEP 202603), 39 pruebas, mapa de control; revisor-spec ✅, revisor-calidad ✅ (2.ª ronda), cazador ✅. Verificación manual: Jose Miguel (8-oct). Spec v1.2. H-04 y H-05 confirmados. |
| 2026-10-01 | Daniel + Claude | README temporal, esta memoria (cargada desde `CLAUDE.md`) y ramas `parte1-optimizacion-numerica` / `parte2-tsp-espana`. Primer push (`2cd005b`): Spec v1.1, PLAN, agentes, registro. |
| 2026-10-01 | Equipo | Decidido: fecha de corte 1-oct, Corolla Sedán 140H, dominio Rosenbrock [−2.048, 2.048]ⁿ (respaldado con experimento). |
| 2026-10-01 | Equipo Parte 2 | Propuesta de datos en 5 bloques (documento de Camila) incorporada al Spec. |
| 2026-09-29 | Equipo | División: Parte 1 (2), Parte 2 (2), Daniel puente. Funciones Rosenbrock + Rastrigin. Front 100 % Python. |
