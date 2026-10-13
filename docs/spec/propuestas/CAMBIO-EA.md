# Propuesta de cambio de especificación — EA de la Parte 1 (esquema de clase)

| | |
|---|---|
| Estado | **Propuesta** (no aplicada). El Spec y el PLAN los edita el equipo |
| Fecha | 2026-10-12 |
| Afecta | `docs/spec/SPEC.md` (§6.4 y notas), `docs/spec/PLAN.md` (T1.4, T1.7), `configs/part1/base.yaml` (lo hace T1.4) |
| Prompt | `alucinaciones/prompts/CAMBIO-EA.md` |
| Leyenda | **[V]** verificado leyendo el repo · **[S]** suposición · **[C]** cálculo |

## 1. Resumen
El EA de §6.4 (torneo k=3 + BLX-α, pop=40) se reemplaza por el esquema de clase (élite + mutantes + cruce de un punto, N=50), manteniendo el contrato `optimize()` (§5.1), el contador `CountedProblem` y los 20 configs × 30 semillas. El torneo/BLX-α queda como extensión opcional bajo `ea.esquema`; **solo se implementa `clase`** por el plazo (entrega mar 13-oct-2026, 23:59).

## 2. Decisiones tomadas
- Esquema de clase como único esquema implementado y **valor por defecto**.
- Cruce: número de individuos forzado a par **hacia arriba**; si la suma de grupos excede N, se recorta por el final.
- La élite **no se reevalúa** (`ea.reevaluar_elite: false`): conserva su aptitud guardada.
- Parada por presupuesto (§6.2), no por número fijo de generaciones.
- Fuente: material de clase IRNA202602, "intro algoritmos evolutivos" (cuaderno `.ipynb`): https://colab.research.google.com/drive/1QvaXDJAPgiuQOuKcvZB-lpiRbPGqLHne

## 3. Comparación Spec actual vs. propuesta
| Aspecto | Spec §6.4 / PLAN T1.4 [V] | Esquema de clase |
|---|---|---|
| Población | pop = 40 | N = 50 |
| Selección | Torneo k=3 | Sin selección por aptitud: individuos al azar sin repetir para mutar y para cruzar |
| Cruce | BLX-α (α=0.5), pc=0.9 | Un punto, punto ∈ {1,…,d−1}; 2 hijos por pareja |
| Mutación | Gaussiana por gen con prob. pm=1/n, σ=0.1·rango | **Un** gen por mutante, N(0, σ²), σ = desv. estándar poblacional (ddof=0) de ese gen; recorte al dominio |
| Élite | 2 individuos | `round(N·0.15)` = 8 |
| Reemplazo | Generacional con elitismo | Élite + mutantes + hijos, recortada a N |
| Parada | Presupuesto §6.2 | Presupuesto §6.2 (`ea.generaciones: null`) |
| Parámetros | pop, pc, α, σ, pm, élites | N, `frac_e`=0.15, `frac_m`=0.10, `frac_c`=0.75 |

`frac_*` es la fracción de la población (0.15 = 15 %).

## 4. Opciones consideradas
| Opción | Ventajas | Riesgos | Conteo y comparación justa |
|---|---|---|---|
| A) `esquema: spec \| clase` con ambos implementados | Conserva torneo/BLX-α; permite compararlos | Duplica pruebas y rondas de revisión; si ambos corren, hay que añadir un identificador (§5.4 es [DECIDIDO]) y 24 configs | Cumple (ambos pasan por `CountedProblem`) |
| B) Reemplazar el Spec por clase | Menos código | Se pierde el torneo/BLX-α sin puerta de vuelta | Cumple |
| **A') Solo clase implementado, `ea.esquema` reservado** (elegida) | Menos código que A, deja la puerta abierta | `ea.esquema: spec` debe fallar con mensaje claro hasta que exista | Cumple |

## 5. Impacto archivo por archivo
| Archivo | ¿Cambia? | Dónde / por qué |
|---|---|---|
| `docs/spec/SPEC.md` | **Sí** | §6.4 fila EA; §6.2 nota de parada/conteo del EA; §10 añadir `test_ea.py`; §11 verificaciones del EA; §13 fila de riesgo; encabezado v1.4. §3, §5.1, §5.4, §6.5, §6.6, §6.7 **no** cambian |
| `docs/spec/PLAN.md` | **Sí** | T1.4: título, aceptación y verificador (+ verificador-matematico). T1.7: leer bloque `ea:`. T1.8, T1.9, T4.2, T4.3 **no cambian** (demo = `pso`+`gdfijo`; GIF solo GD y PSO) |
| `configs/part1/base.yaml` | **Sí (lo hace T1.4)** | Hoy solo tiene claves de nivel superior [V]; T1.4 añade el bloque `ea:` completo (regla de §4.1) |
| `configs/part1/demo.yaml` | No | `methods: [pso, gdfijo]` [V] |
| `optimize()` §5.1 | No | Misma firma y retorno |
| `frames` / `history` | No | `frames`: una entrada por generación completada, `positions` N×2 (solo dim=2) [S]; `history` lo llena `CountedProblem` [V] |
| `src/common/counter.py`, `config.py`, `seeds.py` | No | — |
| `tests/test_counter.py`, `tests/test_budget.py` | No se rompen | Usan un bucle juguete (`conftest.py`), no `ea.py` [V] |
| `docs/MEMORIA.md` | Sí, al aprobar el cambio | Decisión vigente + línea de bitácora (CLAUDE.md) |

## 6. Conteo de evaluaciones
Toda evaluación pasa por `problem.f(x_i)` en un bucle por individuo (`CountedProblem.f` recibe un solo `x`) [V]. No se cuenta a mano.

| | Reevaluar toda la población | Élite en caché (**por defecto**) |
|---|---|---|
| Generación 0 | 50 | 50 |
| Cada generación siguiente | 50 | 42 [C] (50 − 8 élites; se recorta antes de evaluar) |
| 2D, presupuesto 20 000 [C] | T=399, exacto | 50 + 42·475 = 20 000, exacto |
| 3D, presupuesto 30 000 [C] | T=599, exacto | T=713 y 4 evaluaciones de la generación 714 (truncada) |

- Presupuesto agotado a mitad de generación: `CountedProblem` lanza `BudgetExhausted` antes de exceder; `ea.py` lo captura y devuelve el mejor punto visto (patrón [DECIDIDO 9-oct, T0.4]). La generación truncada no registra frame [S].
- `n_grad = 0`; `eval_equiv = n_f`.
- Fórmula para el EA con caché: `n_f = N + T·(N − n_élite)`; con reevaluación, `N·(T+1)`.
- Los 20 configs × 30 semillas no cambian (el EA es 1 de 5 métodos): 120 corridas de EA, ~20–30 mil llamadas a `f` cada una [C].

## 7. Reproducibilidad
- Una sola `rng = make_rng(base_seed, run_id)` pasada a `optimize()`; todo el azar sale de ella (inicialización, `rng.choice(..., replace=False)`, gen a mutar, `rng.normal`, punto de cruce). Nada de `random` ni `np.random.seed` (§4.1).
- Orden de consumo del RNG fijo y documentado.
- `np.argsort(kind="stable")` para empates.
- Misma semilla → mismo JSON (patrón de `tests/test_reproducibility.py`).

## 8. Defectos del cuaderno que no se heredan
| Defecto | Prueba |
|---|---|
| (a) ranking con aptitudes iniciales | La élite es el top-k por f **actual** |
| (b) evaluación en bucle y globales | `llamadas_f` de la función de prueba = `problem.n_f`; sin estado global |
| (c) punto de cruce 0 | Punto ∈ {1,…,d−1} siempre (en 2D solo vale 1: los hijos intercambian coordenadas) |
| (d) función de prueba no estándar | Cubierto por T1.1 (Rastrigin verificada contra SFU) |

## 9. Decisiones del Spec
- **[DECIDIDO], no se toca sin escalar** [V]: funciones, dimensiones y dominios; algoritmos desde cero con numpy; reglas de conteo §6.2 (población inicial cuenta, k=2n, presupuesto 10 000·n, truncar); contrato `optimize()` §5.1; identificadores y forma del JSON §5.4 (`ea` se mantiene); semillas; 20 configs × 30 corridas y umbral 1e-4 (§6.5).
- **Sobrescribible**: la tabla de §6.4 ("todos sobrescribibles por config"). Ahí vive el cambio.
- **Conflicto resuelto**: "generaciones fijas" del cuaderno vs. presupuesto igual para todos (§6.2): `ea.generaciones: null` por defecto; un número solo acorta la corrida y el blog debe advertir que rompe la comparación justa.

## 10. Riesgos
| Riesgo | Mitigación |
|---|---|
| Suma de grupos ≠ N: N=50 da 51 (se recorta); **N=30 da 29** [C] | Si falta, el cruce sube (par) hasta cubrir N; `ValueError` si las fracciones son inválidas |
| Convergencia floja en 2D (cruce de 1 punto solo intercambia coordenadas; sin presión de selección salvo la élite) | Reportarlo en la discusión; no ajustar parámetros para "ganar" |
| σ poblacional → 0 al converger: la mutación se apaga | Documentarlo como comportamiento observable |
| El cuaderno no es una referencia bibliográfica formal | Citar el material de clase por nombre y URL; no inventar cita |
| Plazo: T1.2–T1.6 y T1.7 siguen pendientes [V PLAN] | Solo esquema de clase; torneo/BLX-α solo si sobra tiempo |
| Cambio de Spec sin trazabilidad (cacería) | Prompt guardado en `alucinaciones/prompts/CAMBIO-EA.md` y registro del cambio |

## 11. Borrador de texto para el Spec (§6.4, fila EA)
> **EA (esquema de clase, codificación real).** Población N×d. Cada generación: evaluar los individuos nuevos (la élite conserva su aptitud), ordenar de mejor a peor y construir la siguiente población como élite + mutantes + hijos de cruce, recortada a N filas.
> - **Élite:** primeras `round(N·frac_e)` filas, copiadas sin cambio.
> - **Mutación:** `int(N·frac_m)` individuos elegidos al azar sin repetir; a cada copia se le suma N(0, σ²) a **un** gen elegido al azar, con σ = desviación estándar poblacional (ddof=0) de ese gen en la generación actual; se recorta al dominio.
> - **Cruce:** `int(N·frac_c)` individuos (forzado a par hacia arriba) elegidos al azar sin repetir, sin considerar la aptitud; se parten en dos mitades y cada pareja produce 2 hijos por cruce de un punto con punto ∈ {1,…,d−1}. Si la suma de grupos no alcanza N, el cruce aumenta (par) hasta cubrirlo; si excede, se recorta por el final.
> - **Parada:** presupuesto §6.2; `ea.generaciones: null`.
> - **Por defecto:** N=50, `frac_e`=0.15, `frac_m`=0.10, `frac_c`=0.75, `reevaluar_elite`=false, `esquema`=clase. Fuente del esquema: material de clase IRNA202602, "intro algoritmos evolutivos" (https://colab.research.google.com/drive/1QvaXDJAPgiuQOuKcvZB-lpiRbPGqLHne).
>
> *Reemplaza la fila EA (torneo k=3, BLX-α, pop=40). El esquema anterior queda reservado como `ea.esquema: spec` y no está implementado.*

## 12. Pruebas propuestas para T1.4 (`tests/test_ea.py`)
Marco [V]: CLAUDE.md "Prueba primero, luego código"; Spec §12.1 TDD; PLAN T1.4 solo pide "conteo exacto por generación; individuos dentro del dominio"; Spec §10 no lista `test_ea.py` (se propone añadirlo).

| # | Prueba | Qué garantiza |
|---|---|---|
| 1 | Tamaños de grupos: `n_elite=round(N·frac_e)`, mutantes, cruce par; población siempre N×d (N=50: 8/5/38 recortado a 42 nuevos; N=30: rama de relleno) | Aritmética |
| 2 | Dentro del dominio tras mutar y cruzar (2D y 3D) | Dominio |
| 3 | Mutación cambia **exactamente un** gen por mutante; σ = `np.std(axis=0)` (ddof=0) | Definición |
| 4 | Cruce: punto ∈ {1,…,d−1}; hijos = prefijo de un padre + sufijo del otro | Defecto (c) |
| 5 | Sin repetición dentro del grupo de mutantes y del de cruce | "sin repetir" |
| 6 | Élite = top-k por f de la generación actual | Defecto (a) |
| 7 | `n_f = N + T·(N − n_elite)`; con `reevaluar_elite=true`, `N·(T+1)`; `n_grad = 0`; `llamadas_f` = `n_f` | Defecto (b), §6.2 |
| 8 | Presupuesto no múltiplo: `n_f == budget`, `eval_equiv ≤ budget`, devuelve el mejor visto | §6.2 truncar |
| 9 | `f_best` por generación nunca empeora | Elitismo |
| 10 | Misma semilla → mismo JSON; semillas distintas → distinto | §9 |
| 11 | `frames` solo si `dim==2` y `record_frames`; `positions` N×2 | §5.1 |
| 12 | Cuadrática 2D llega a f ≤ 1e-4 con presupuesto 10 000·n | Humo |
| 13 | `esquema: spec` → error claro; fracciones inválidas → `ValueError` | Validación |

Prueba de mutación (técnica registrada en MEMORIA): romper a propósito (punto de cruce 0, ranking con f inicial, σ con ddof=1) y comprobar que alguna prueba falla.

## 13. Pasos y entregables
1. `alucinaciones/prompts/CAMBIO-EA.md` (hecho).
2. Esta propuesta (hecha).
3. Equipo: revisar, editar SPEC.md y PLAN.md (§5), actualizar MEMORIA.md y fusionar.
4. Equipo: T1.4 con el flujo SDD (implementador → revisor-spec → revisor-calidad → verificador-matematico).
5. Equipo: registrar en `alucinaciones/registro.md` si el cambio revela un candidato.

## 14. Pendientes
- `TODO(dato-faltante)`: `tutoria/03_prompt_T1.4_algoritmo_evolutivo.md` (sección B) no existe en el repo [V]; esta propuesta se basó en el resumen del algoritmo del prompt.
- Nota: el enlace de Classroom es de acceso restringido; no lleva fecha por decisión del equipo (es material de curso, no un dato del mundo real de `data/fuentes.md`).
