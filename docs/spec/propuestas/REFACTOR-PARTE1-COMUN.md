# Propuesta de cambio — Parte 1: refactor común de T1.4 (EA), T1.5 (PSO) y T1.6 (DE) hacia `src/part1/_comun.py`

| | |
|---|---|
| Estado | **Propuesta** (no aplicada; no se tocó ningún `.py`). El Spec y el PLAN los edita el equipo |
| Fecha | 2026-10-12 |
| Alcance | **Solo Parte 1 (F1)** y solo el código entregado por **T1.4** (`ea.py`), **T1.5** (`pso.py`) y **T1.6** (`de.py`), con sus pruebas (`tests/test_ea.py`, `test_pso.py`, `test_de.py`). Fuera: T1.1 (`functions.py`), T1.2–T1.3 (`gd.py`), `src/common/` (F0), Parte 2 y `viz/` |
| Tarea propuesta | **T1.6b** del PLAN (F1), depende de T1.4, T1.5 y T1.6 |
| Afecta | `docs/spec/SPEC.md` (§4 árbol y nota en §5.1), `docs/spec/PLAN.md` (nueva T1.6b; nota en T1.7), `src/part1/{ea,pso,de}.py`, `tests/` (nuevo `test_comun.py`) |
| Prompt | `alucinaciones/prompts/REFACTOR-PARTE1-COMUN.md` |
| Valida | Daniel (puente), en el PR de esta propuesta |
| Leyenda | **[V]** verificado leyendo el repo · **[S]** suposición · **[C]** cálculo |

## 1. Resumen
"Común" aquí significa **común a las tres metaheurísticas de la Parte 1** (EA de T1.4, PSO de T1.5, DE de T1.6); no tiene
relación con `src/common/` (F0, compartido por las dos partes), que no se toca.

| Tarea de origen | Módulo | Qué aporta hoy al problema |
|---|---|---|
| T1.4 | `ea.py` | Aloja utilidades genéricas (validaciones, población inicial, evaluación, frames) que no son del EA |
| T1.5 | `pso.py` | Importa esas utilidades de `ea.py` y duplica `_exigir_forma`, `_validar_real`, lectura del bloque y retorno §5.1 |
| T1.6 | `de.py` | Igual que PSO: importa de `ea.py` y duplica las mismas piezas |

PSO (T1.5) y DE (T1.6) se escribieron en sesiones distintas. Hoy importan utilidades **de `ea.py`** (acoplamiento
PSO→EA y DE→EA solo por utilidades) y **duplican** otras. El único objetivo es la **legibilidad**: mover lo repetido a un
único archivo `src/part1/_comun.py` y dejar en cada módulo solo lo propio del algoritmo. **Sin cambio de comportamiento**
ni de contratos (§5.1, §5.4, `base.yaml`).

Cierra los pendientes **M1** y **M8** de T1.6 (MEMORIA) y la "ronda de refactor" anunciada en la tabla de estado.

## 2. Qué se repite hoy [V]
| # | Duplicación / acoplamiento | Dónde | Destino en `_comun.py` |
|---|---|---|---|
| 1 | `_exigir_forma`, idéntica | `pso.py:227`, `de.py:205` | `exigir_forma` |
| 2 | Diccionario de retorno §5.1 (`x_best, f_best, n_f, n_grad, eval_equiv, history`, + `frames`), idéntico | `ea.py:851`, `pso.py:804`, `de.py:692` (y casi idéntico en `gd.py:205`, con `history` sin copiar) | `construir_resultado(problem, frames, guardar_frames)` |
| 3 | `DIMENSION_CON_FRAMES`, `leer_record_frames`, `construir_frame`: viven en `ea.py` y los importan PSO y DE | `ea.py:57,733,744` | mismo nombre |
| 4 | `validar_limites`, `validar_poblacion`, `evaluar_poblacion`, `generar_poblacion_inicial`: viven en `ea.py` y los importan PSO y DE | `ea.py:265,277,295,345` | mismo nombre |
| 5 | `_leer_bloque_ea/_pso/_de` y `_validar_claves_del_bloque` (ea, pso, de): solo cambian el nombre del bloque y la tupla de claves | `ea.py:96,725`, `pso.py:117,682`, `de.py:118,579` | `leer_bloque(cfg, nombre)` y `validar_claves_exactas(bloque, claves, nombre)` |
| 6 | Validación de real finito con `TypeError` (tipo/bool) y `ValueError` (NaN/inf/rango): `_validar_fraccion` (ea), `_validar_real` (pso y de, con firmas distintas) | `ea.py:79`, `pso.py:87`, `de.py:89` | `validar_real(valor, nombre, minimo, minimo_incluido, maximo=None)` |

## 3. Diseño propuesto
- **Un solo archivo nuevo** `src/part1/_comun.py`, con el mismo estilo que los módulos actuales (celdas `# %%`,
  docstrings numpy, ≤ 100 caracteres, sin `random` ni siembra global, funciones puras).
- `ea.py`, `pso.py` y `de.py` importan de `_comun`, **no entre sí**. Cada uno conserva sus componentes propios y su `optimize`.
- Los mensajes de error, el orden de llamadas al rng y las firmas públicas de `optimize` y de los componentes **no cambian**.
- Si alguna prueba importa un nombre movido (p. ej. `evaluar_poblacion` desde `src.part1.ea`), se prefiere actualizar el
  import de la prueba a dejar re-exportaciones; decide el implementador por menor diff y lo reporta.

## 4. Fuera de alcance (explícito)
- Sin clase base `Optimizador`, sin `Protocol`, sin paquete `utils/` con subcarpetas.
- **No** unificar `ResultadoCruce` de `ea.py` y `de.py` (campos distintos; son contrato probado).
- **No** extraer el `try/except BudgetExhausted` de `optimize`: cada bucle es distinto y ocultarlo (plantilla) dificulta
  explicar el flujo en la sustentación.
- **No** tocar `gd.py` (su estructura es otra: `_descenso` + reglas de paso). Usar `construir_resultado` en GD es opcional
  y exige decidir antes la semántica de `history` (copia vs. referencia): se deja para después.
- **No** añadir la guarda de NaN / `best_x is None` (pendiente de MEMORIA): es cambio de comportamiento.
- **No** tocar `configs/`, `base.yaml` ni la lógica de los algoritmos.

## 5. Opciones consideradas
| Opción | Ventajas | Riesgos |
|---|---|---|
| **A) `_comun.py` único** (elegida) | Corta el acoplamiento PSO/DE→EA; un lugar para validaciones y retorno | Archivo nuevo en el árbol del Spec (decide Daniel) |
| B) Dejar las utilidades en `ea.py` y solo deduplicar `_exigir_forma` | Diff mínimo | PSO/DE siguen dependiendo de EA; "módulo del EA" mezcla algoritmo y utilidades |
| C) Paquete `src/part1/utils/` con varios archivos | Orden fino | Sobre-ingeniería para ~10 funciones |

## 6. Riesgos conocidos en las pruebas [V]
- `tests/test_ea.py::_espiar` hace `monkeypatch.setattr(ea_mod, nombre, …)` solo sobre `seleccionar_elite`,
  `mutar_individuos`, `cruzar_individuos` y `ensamblar_nueva_generacion`: **se quedan en `ea.py`**, no hay problema.
- Hay pruebas estáticas que leen el texto de cada archivo (`RUTA_EA`, `RUTA_PSO`, `RUTA_DE`): líneas ≤ 100, todo código
  dentro de celdas `# %%`, cabecera con tabla de componentes y LaTeX, sin `random`. Hay que **replicarlas para `_comun.py`**
  y quitar de las cabeceras los componentes movidos.
- Las pruebas de validación de tipos/forma están repetidas en los tres archivos de prueba (M8): al mover el código se
  consolidan en `tests/test_comun.py` y se borran las repetidas, sin bajar la cobertura de mutantes.

## 7. Criterios de aceptación de T1.6b
1. **Prueba primero:** `tests/test_comun.py` (formas, tipos, NaN/inf, claves exactas, retorno §5.1, frame) escrita y en rojo antes de mover código.
2. Salidas **idénticas bit a bit** antes y después (`x_best`, `f_best`, `n_f`, `history`, `frames`) para EA, PSO y DE ×
   Rosenbrock/Rastrigin × 2D/3D × 30 semillas.
3. Suite completa sin fallos; número de pruebas ± las movidas (explicado en el informe).
4. `grep -n "from src.part1.ea import" src/part1/pso.py src/part1/de.py` vacío.
5. Diff neto negativo (estimado −150 a −250 líneas entre los tres módulos) [S].
6. Pruebas estáticas (línea ≤ 100, celdas, sin `random`) también sobre `_comun.py`.

## 8. Secuencia SDD sugerida
implementador → revisor-spec (contratos §5.1 y mensajes de error intactos) → revisor-calidad →
verificador-matematico (reimplementación bit a bit ya existente de T1.4–T1.6). Prompt literal en
`alucinaciones/prompts/T1.6b.md` al despachar. Rama sugerida: `feat/parte1/T1.6b-comun`, **antes de T1.7**
(para que `experiment.py` ya importe los módulos limpios); si el plazo (entrega mar 13-oct, 23:59) aprieta, T1.7 va primero
y T1.6b queda como mejora posterior: no bloquea ninguna entrega.
