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
| Última actualización | 2026-10-01 |
| Fase | **F0 — Fundaciones** (aún no hay código) |
| Próxima tarea | T0.1 Esqueleto del repo → T0.2 config/CLI → T0.4 contador de evaluaciones |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 12) |
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
- Algoritmos Parte 2: AS → MMAS, GA (OX + inversión), 2-opt opcional, óptimo exacto con PuLP como referencia.
- Front: **Material for MkDocs** + Plotly (interactivas) + matplotlib con estilo DS (GIF). Todo Python.
- Desarrollo con **Subagent Driven Development**: 10 agentes en `.claude/agents/`, protocolo en `CLAUDE.md`.

## ⏳ Pendientes / bloqueos
- [ ] Quién monta **OSRM local** (Docker) — decidir a más tardar **sáb 3-oct**; si no, respaldo openrouteservice.
- [ ] **Acabado** del Corolla Sedán 140H (de la ficha oficial de Toyota España).
- [ ] **Design System** (Daniel lo trae como skill).
- [ ] ¿Escenario opcional `post_ap68`?
- [ ] Confirmar fecha/hora de la sustentación.
- [ ] Prompts literales para la cacería: H-01 y H-03 (Daniel), H-02 (Camila).

## 🎯 Cacería de alucinaciones
Candidatos: **3** (H-01 OSRM público · H-02 AP-68 · H-03 paso de GD) — confirmados: **0** — categorías cubiertas: Datos, Matemáticas.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-01 | Daniel + Claude | README temporal, esta memoria (cargada desde `CLAUDE.md`) y ramas `parte1-optimizacion-numerica` / `parte2-tsp-espana`. Primer push (`2cd005b`): Spec v1.1, PLAN, agentes, registro. |
| 2026-10-01 | Equipo | Decidido: fecha de corte 1-oct, Corolla Sedán 140H, dominio Rosenbrock [−2.048, 2.048]ⁿ (respaldado con experimento). |
| 2026-10-01 | Equipo Parte 2 | Propuesta de datos en 5 bloques (documento de Camila) incorporada al Spec. |
| 2026-09-29 | Equipo | División: Parte 1 (2), Parte 2 (2), Daniel puente. Funciones Rosenbrock + Rastrigin. Front 100 % Python. |
