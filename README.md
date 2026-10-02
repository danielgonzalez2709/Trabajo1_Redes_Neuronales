# Trabajo 1 — Optimización numérica, metaheurística y combinatoria

> 🚧 **README temporal.** El proyecto está en construcción; este archivo se reemplaza en la tarea T0.1 / T5.1 por el README
> definitivo con instalación, comandos y semillas.

**Curso:** Redes neuronales y algoritmos bioinspirados — Universidad Nacional de Colombia, Facultad de Minas, 2026-02
**Entrega:** martes 13 de octubre de 2026, 23:59

## ¿De qué trata?
- **Parte 1:** descenso por gradiente vs. algoritmo evolutivo, PSO y evolución diferencial sobre las funciones de
  **Rosenbrock** y **Rastrigin** (2D y 3D), con comparación justa por número de evaluaciones.
- **Parte 2:** recorrido de menor costo por las **47 capitales de provincia de la España peninsular** con colonias de
  hormigas y algoritmo genético; costo = valor de la hora × tiempo + peajes + combustible.

## Dónde está cada cosa
| Archivo | Contenido |
|---|---|
| [`docs/MEMORIA.md`](docs/MEMORIA.md) | **Empieza aquí:** estado actual, decisiones vigentes, pendientes y bitácora |
| [`docs/spec/SPEC.md`](docs/spec/SPEC.md) | Especificación completa (fuente de verdad) |
| [`docs/spec/PLAN.md`](docs/spec/PLAN.md) | Tareas para Subagent Driven Development |
| [`CLAUDE.md`](CLAUDE.md) | Reglas del proyecto y protocolo del orquestador |
| [`.claude/agents/`](.claude/agents/) | Definiciones de los subagentes |
| [`alucinaciones/`](alucinaciones/) | Registro de la Cacería de la alucinación, prompts y evidencias |

## Cómo trabajamos
- Ramas de equipo: **`parte1-optimizacion-numerica`** y **`parte2-tsp-espana`** (salen de `main`). Cada equipo trabaja en la suya (o en ramas que salgan de ella) y abre **Pull Request** hacia `main`, revisado por el puente.
- Cada integrante hace commits con **su propia cuenta**.
- Toda conversación con IA usada en el trabajo se guarda literal en `alucinaciones/prompts/`.
- Al cerrar una tarea o tomar una decisión, se actualiza **`docs/MEMORIA.md`**.

## Próximamente
Instalación (`pip install -r requirements.txt`), comandos de un solo paso (`python run.py part1|part2|figures`),
semillas documentadas y enlace al blog.
