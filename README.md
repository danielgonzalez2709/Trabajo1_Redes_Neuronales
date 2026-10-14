# Redes neuronales y algoritmos bioinspirados — Trabajo 1

**Optimización numérica, metaheurística y combinatoria** · Universidad Nacional de Colombia, Facultad de Minas · 2026-02
Profesor: Juan David Ospina Arango

**Autores:** Jose Miguel Pulgarin Agudelo, Maria Camila Agudelo Espinosa, Daniel Gonzalez Henao, Juan Jose Gonzalez
Morales y Edinson Andrés Ariza Mendoza.

**Reporte (blog):** <https://danielgonzalez2709.github.io/Trabajo1_Redes_Neuronales/> · fuente en [`blog/`](blog/).

## Qué se hizo

- **Parte 1 — optimización continua.** Descenso por gradiente (paso fijo y búsqueda de Armijo) frente a un algoritmo
  evolutivo (EA), optimización por enjambre de partículas (PSO) y evolución diferencial (DE) sobre las funciones de
  **Rosenbrock** y **Rastrigin** en 2D y 3D. La comparación es justa: todos los métodos tienen el mismo presupuesto de
  evaluaciones equivalentes (un gradiente cuesta $2n$ evaluaciones de la función) y 30 corridas por configuración.
- **Parte 2 — problema del viajero.** Recorrido de menor costo por las **47 capitales de provincia de la España
  peninsular** con colonias de hormigas (MAX–MIN Ant System y Ant System) y un algoritmo genético. El costo de cada
  tramo es real: valor de la hora × tiempo + peajes + combustible, con rutas de OSRM, peajes oficiales y el precio
  medio de la gasolina.

## Resultados principales

| | Resultado |
|---|---|
| Parte 1 | DE y PSO llegan a menos de $10^{-4}$ del mínimo en 118 y 116 de 120 corridas; el EA en 45, Armijo en 10 y el paso fijo en 2. Con hiperparámetros afinados: EA 87 y Armijo 51 |
| Parte 2 | Con el mismo número de recorridos evaluados, la media de MMAS queda a 0,24–0,75 % del óptimo y la del GA a 2,32–4,07 % |
| ¿Cambia la ruta con el valor de la hora? | Sí: la ruta óptima (verificada con un solver exacto) cambia en $w$ = **10,02, 14,53 y 42,19 €/h** |
| Cacería de la alucinación | Más de 40 posibles errores de la IA registrados; 9 confirmados en 4 categorías ([`alucinaciones/registro.md`](alucinaciones/registro.md)) |

## Instalación

Se necesita **Python 3.12** (probado con 3.12.6). Las versiones de todas las dependencias están fijas en
[`requirements.txt`](requirements.txt).

Windows:

```bash
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

macOS o Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

En los comandos de abajo, `python` es el del entorno (`.venv\Scripts\python` en Windows, `.venv/bin/python` en macOS
o Linux).

## Comandos

Todo se ejecuta desde la raíz del repositorio con un solo comando por experimento. Ningún comando usa internet. Los
tiempos se midieron en la máquina de desarrollo (Windows).

### Demos (para la sustentación en vivo)

| Comando | Qué hace | Tiempo |
|---|---|---|
| `python run.py part1 --config configs/part1/demo.yaml` | Rastrigin 2D, PSO contra descenso por gradiente, 5 corridas; tabla en consola y figura de trayectoria | ~3 s |
| `python run.py part2 --config configs/part2/demo.yaml` | MMAS en $w$ = 25 €/h, 1 000 iteraciones, 10 corridas; costo, gap y figura del recorrido | ~20 s |
| `python run.py hpo --config configs/part1/hpo_demo.yaml` | Afinación de hiperparámetros en pequeño (Rastrigin 2D, PSO y paso fijo) | ~9 s |

Cualquier parámetro se cambia sin editar el código con `--set clave=valor` (repetible), por ejemplo
`python run.py part1 --config configs/part1/demo.yaml --set pso.w=0.9 --set runs=10`.

### Experimentos completos

| Comando | Qué hace | Tiempo |
|---|---|---|
| `python run.py part1 --config configs/part1/base.yaml` | 5 métodos × 2 funciones × 2D/3D × 30 semillas, más la sensibilidad con $k = 1$ | ~10 min en serie |
| `python run.py part1 --config configs/part1/tuned.yaml` | El mismo experimento con los hiperparámetros afinados | ~10 min en serie |
| `python run.py hpo --config configs/part1/base.yaml` | Afinación de hiperparámetros (semillas 1000–1004, aparte de las de reporte); reescribe `configs/part1/tuned.yaml` | ~7 min con 6 procesos |
| `python run.py part2 --config configs/part2/sweep_w.yaml` | Barrido del valor de la hora (11 valores de $w$, MMAS, AS y GA, 10 corridas cada uno) | ~18 min |
| `python run.py part2 --config configs/part2/sensibilidad_consumo.yaml` | Sensibilidad al consumo (5,6 l/100 km; con `--set costo.consumo_l100=6.2`, el segundo valor) | no medido |
| `python scripts/umbrales_exactos.py` | Óptimo exacto (PuLP + HiGHS) y umbrales exactos del valor de la hora para los tres consumos | ~13 min |
| `python run.py figures` | Regenera las figuras interactivas y los GIF del blog desde `results/data/` | ~40 s |

En la Parte 1, `--set workers=N` reparte las corridas en `N` procesos sin cambiar el resultado.

### Pruebas y blog

| Comando | Qué hace |
|---|---|
| `python -m pytest -q` | Suite completa (~2 500 pruebas, 4–6 min). Una prueba consulta el sitio del Ministerio y necesita internet: se omite con `--deselect tests/test_combustible.py::test_contexto_tls_minetur_verifica_y_admite_el_cifrado_del_servidor` |
| `mkdocs build --strict -f blog/mkdocs.yml` | Construye el reporte en `blog/site/`; falla si una figura o tabla no se cita o si falta una referencia |
| `mkdocs serve -f blog/mkdocs.yml` | Abre el reporte en `http://127.0.0.1:8000/Trabajo1_Redes_Neuronales/` |

(`mkdocs` es el del entorno: `.venv\Scripts\mkdocs` en Windows.)

## Reproducibilidad

- **Semillas fijas:** cada corrida usa `base_seed + run_id`; las semillas de reporte de la Parte 1 son 0–29 y las de la
  afinación 1000–1004.
- **Datos guardados:** los datos del problema del viajero están en `data/processed/`, con su fuente y fecha de consulta
  en [`data/fuentes.md`](data/fuentes.md). Reconstruirlos desde las fuentes (`scripts/descargar_datos.py`) sí requiere
  internet y un servidor OSRM local.
- **Corridas de la Parte 1:** los JSON de cada corrida (`results/data/part1/runs/` y `part1_tuned/runs/`) no se
  versionan. Las figuras de convergencia y de cajas se regeneran después de correr los dos experimentos de la Parte 1.
- **Plataforma:** entre sistemas operativos, el número de evaluaciones del descenso con Armijo en Rastrigin puede
  variar (menos de 0,02 % en 2D y unos 5 % en 3D) por diferencias de la librería matemática en el último bit; los
  valores finales y las tasas de éxito son los mismos.

## Dónde está cada cosa

| Carpeta o archivo | Contenido |
|---|---|
| [`run.py`](run.py) | Punto de entrada único (`part1`, `hpo`, `part2`, `figures`) |
| [`src/`](src/) | Código: `common/` (configuración, semillas, contador de evaluaciones), `part1/`, `part2/` y `viz/` |
| [`configs/`](configs/) | Configuraciones YAML de cada experimento y demo |
| [`data/`](data/) | Datos del problema del viajero (`processed/`) y sus fuentes |
| [`results/`](results/) | Resultados de los experimentos (`data/`) y tablas (`tables/`) |
| [`blog/`](blog/) | Reporte técnico en MkDocs; guía para redactar en [`blog/README.md`](blog/README.md) |
| [`tests/`](tests/) | Pruebas |
| [`alucinaciones/`](alucinaciones/) | Cacería de la alucinación: registro, prompts literales y evidencias |
| [`docs/spec/SPEC.md`](docs/spec/SPEC.md) · [`docs/spec/PLAN.md`](docs/spec/PLAN.md) | Especificación (fuente de verdad) y plan de tareas |
| [`docs/MEMORIA.md`](docs/MEMORIA.md) | Estado del proyecto, decisiones y bitácora |
| [`CLAUDE.md`](CLAUDE.md) · [`.claude/agents/`](.claude/agents/) | Reglas para la IA y definiciones de los subagentes |

## Cómo se trabajó

El código se desarrolló con *Subagent Driven Development*: cada tarea del plan la implementa un subagente de IA a partir
de la especificación y la revisan subagentes independientes (cumplimiento del Spec, calidad y, cuando hay fórmulas,
verificación matemática). Cada parte trabajó en su propia rama y abrió Pull Requests hacia `main`, que revisó el
integrante encargado de la integración. Todos los prompts usados se guardan literales en
[`alucinaciones/prompts/`](alucinaciones/prompts/), y la sección *Uso de inteligencia artificial* del blog resume cómo
se usó la IA y qué no se le delegó.
