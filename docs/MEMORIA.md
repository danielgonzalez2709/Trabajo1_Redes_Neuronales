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
| Última actualización | 2026-10-11 |
| Fase | **F0 — Fundaciones** T0.1–T0.4 ✅ (en `main`; faltan T0.5 sin-red y T0.7 blog) · **F2 — Datos Parte 2** en curso (T2.0–T2.2 ✅, T2.3 🟡 ejecutada, T2.6 ✅, T2.7 🟡 falta acabado) |
| Próxima tarea | Parte 2: **T2.7** (elegir acabado) · **T2.3** (decidir los 5 pares `sin_peaje` con clase `toll`) · T3.1 costos, T3.3 ACO, T3.4 GA · T2.4 peajes. Integración: T0.5, T0.7. **Las tareas de Camila (T2.3 ejecución, T2.6, T2.7) las asumió Jose Miguel el 11-oct.** |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 2) |
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
- Parte 2: fecha de corte **1-oct-2026**; OSRM **local con Docker** (T2.0, 10-oct; el servidor público no admite `exclude=toll`; ORS solo contingencia); dos alternativas por par
  (rápida / sin peaje); par sin peaje = la rápida no pasa por ninguna intersección `toll` (Spec v1.5); crudos de rutas NO se versionan,
  T2.5 usa `rutas_pasos_peaje.csv`; peajes oficiales + forales; Gasolina 95 E5 **media peninsular** (v1.6; la nacional queda como sensibilidad); **Toyota Corolla Sedán Hybrid 2026 1.8 L (140H)**.
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
- [ ] T2.2: ¿`osrm.sh descargar` como paso manual documentado o vía `descargar_datos.py`? (CLAUDE.md: solo ese script usa internet).
- [ ] Spec §7.2 Bloque 3: la clase `toll` va por intersección, no por paso → precisar antes de T2.5. Aceptación T2.2 Madrid–Barcelona no tiene peaje.
- [ ] Zona horaria del equipo: `fuentes.md` dice UTC−5, máquina de Parte 2 en UTC−3.
- [ ] **Acabado** del Corolla Sedán 140H: Toyota España tiene Style Plus (particulares, 4,6 l/100 km) y ECO (flotas, cifras contradictorias). Sin fase WLTP extra alta publicada.
- [ ] **T2.3:** 5 pares `sin_peaje` pasan por intersecciones `toll` pese a `exclude=toll` ([16,18], [16,35], [16,44], [27,35] por M-12; [26,29] por AP-15). Decidir tratamiento antes de T2.5.
- [x] **Design System:** skill `apple-design` (Emil Kowalski). Falta la **paleta de colores** (T4.1); la skill no la define.
- [ ] ¿Escenario opcional `post_ap68`?
- [ ] Confirmar fecha/hora de la sustentación.
- [ ] Prompts literales para la cacería: ~~H-01, H-03 (Daniel)~~ ✅ en `alucinaciones/prompts/asesoria_puente_claude.md`; H-02 (Camila) pendiente.
- [x] `revisor-spec` y `revisor-calidad` no cargaban como agentes: su `description` llevaba `": "` sin comillas (YAML inválido, verificado con PyYAML el 11-oct). Corregido con comillas; reiniciar Claude Code para que carguen.

## 🎯 Cacería de alucinaciones
Candidatos: **11** (H-01 OSRM público · H-02 AP-68 · H-03 paso de GD · H-04 ORIGENCOOR · H-05 capital = municipio · H-06 Mérida ·
H-07 PuLP 4 sin CBC · H-08 contador y redondeo · H-09 np.float64 · H-10 prueba que no falla · H-11 campos PBF) — confirmados: **2** (H-04, H-05) —
categorías: Datos (5), Matemáticas (1), **Código (5)**. Faltan Bibliografía/Conceptos para tener margen. Técnica útil: **prueba de mutación**.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-11 | Jose Miguel + Claude | Asumimos las tareas de Camila. **T2.6 ✅** (media peninsular 1,8318 €/l; 3 rondas; 418 pruebas). **T2.3 ejecutada** en Windows (Docker Desktop, `.wslconfig` 16 GB; 1081/1081 pares; `osrm.sh` admite Git Bash). **Spec v1.6**: enunciado y rúbrica literales (§1.2–1.3), combustible peninsular. T2.7 a la espera del acabado. |
| 2026-10-11 | Jose Miguel + Claude | **T2.3 código listo** (curador-datos, 2 rondas): `descargar_datos.py --bloque 2`, `construir_rutas.py`, 58 pruebas nuevas (332 en total). revisor-spec ✅, revisor-calidad ✅. Spec v1.5: criterio de par sin peaje, `rutas_resumen.json` y `rutas_pasos_peaje.csv` en §5.3, crudos de rutas sin versionar. Falta que Camila lo ejecute. |
| 2026-10-11 | Daniel + Claude | Integración de la rama de Parte 2 (T2.0/T2.2 de Camila) con `main` (F0). Conflictos resueltos: Spec → v1.4; el H-06 de Camila (campos PBF) pasa a **H-11** porque H-06 ya era Mérida. Reparto: nosotros escribimos T2.3, T3.1, T3.3, T3.4, T2.4; Camila ejecuta T2.3 y hace T2.6 y T2.7. |
| 2026-10-10 | Equipo Parte 2 + Claude | **T2.2 ✅**: Colima + Docker; OSRM v26.10.0 (arm64, digest fijo), extracto `spain-261001` (datos 1-oct 20:22Z, md5 ok); `toll` verificado (AP-68, AP-9). Auditor ✅ (8 menores). H-11 (Código) candidato. |
| 2026-10-10 | Equipo Parte 2 + Claude | **T2.0 ✅**: OSRM local con Docker (máquina M4, 16 GB). ORS queda como contingencia. |
| 2026-10-09 | Daniel + Claude (SDD) | **T0.2, T0.3, T0.4 ✅** con subagentes: implementador → revisor-spec → revisor-calidad (+ verificador-matemático en T0.4), 2–4 rondas cada una; 274 pruebas en total. Spec §4.1/§5.1/§5.4 ampliado (YAML 1.2, herencia, regla de bloques, identificadores, semilla efectiva, BudgetExhausted). Hallazgos **H-08**, **H-09**, **H-10** (Código). |
| 2026-10-09 | Daniel + Claude | PR #1 revisado (39/39 pruebas, regeneración byte a byte) y fusionado (merge commit). **T0.1 ✅**: `requirements.txt` (Python 3.12.6, `pip freeze`), esqueleto `src/`, `configs/`, `results/`, `media/`. Hallazgos nuevos **H-06** (Mérida) y **H-07** (PuLP 4 sin CBC y API nueva). Design System = skill `apple-design`. Spec v1.3. |
| 2026-10-09 | Jose Miguel + Claude | **T2.1 ✅**: `cities.csv` (47 capitales, NGMEP 202603), 39 pruebas, mapa de control; revisor-spec ✅, revisor-calidad ✅ (2.ª ronda), cazador ✅. Verificación manual: Jose Miguel (8-oct). Spec v1.2. H-04 y H-05 confirmados. |
| 2026-10-01 | Daniel + Claude | README temporal, esta memoria (cargada desde `CLAUDE.md`) y ramas `parte1-optimizacion-numerica` / `parte2-tsp-espana`. Primer push (`2cd005b`): Spec v1.1, PLAN, agentes, registro. |
| 2026-10-01 | Equipo | Decidido: fecha de corte 1-oct, Corolla Sedán 140H, dominio Rosenbrock [−2.048, 2.048]ⁿ (respaldado con experimento). |
| 2026-10-01 | Equipo Parte 2 | Propuesta de datos en 5 bloques (documento de Camila) incorporada al Spec. |
| 2026-09-29 | Equipo | División: Parte 1 (2), Parte 2 (2), Daniel puente. Funciones Rosenbrock + Rastrigin. Front 100 % Python. |
