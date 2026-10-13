# Auditoría de T1.11 (blog, Parte 1): cifras y afirmaciones contra los archivos fuente

Alcance: todo el texto nuevo o cambiado de `git diff -- blog/` en `blog/secciones/03-parte1-metodologia.md`,
`04-parte1-resultados.md`, `08-discusion.md` y `11-reproducibilidad.md`. Sin internet. Cada cifra se contrastó con el
archivo fuente (no solo con `H-T1.11_cifras.txt`) mediante un script propio del cazador, fuera del repo (scratchpad,
`aud111.py`), que lee `results/tables/part1_tuned/comparacion.csv`, `results/data/part1_hpo/seleccion.json`,
`results/data/part1_hpo/regla_v1/{seleccion.json,comparacion.csv}`, los seis `ensayos_*.json` (recalcula medianas
recortadas, rangos promedio, puntajes y éxitos a 1e-6 sin importar `hpo.py`), `results/data/part1/summary.json`,
`results/data/part1_eta_1l/summary.json` (y sus 60 JSON de `runs/`, para confirmar el η usado), `base.yaml` y
`tuned.yaml`. Las afirmaciones sobre el código se contrastaron con `src/part1/experiment.py`, `metricas.py`, `hpo.py`,
`hpo_experimento.py`, `ea.py`, `pso.py`, `de.py` y `gd.py`; las de la Spec con `docs/spec/SPEC.md` §6.2, §6.3 y §6.9;
los tiempos con las secciones "Resultado" de `alucinaciones/prompts/T1.10.md` y `T1.10b.md`; lo versionado con
`.gitignore` y `git ls-files`.

Clave de "coincide": **sí**; **no** (discrepancia); **imprecisa** (el valor es correcto pero la formulación dice más o
menos de lo que respalda la fuente); **n/v** (no verificable localmente).

## Sección 03 (metodología)

| # | Afirmación (sección y línea) | Archivo y campo fuente | Valor fuente | Coincide |
|---|---|---|---|---|
| 1 | 03:33-34 En la sensibilidad solo los dos GD se re-ejecutan con k = 1, mismas semillas y presupuesto, corridas guardadas aparte | `experiment.py` `ejecutar_experimento` (`configuraciones_gd`, `k=K_SENSIBILIDAD`, carpeta `k1/runs`) | solo `METODOS_GD`; `<salida>/k1/runs/` | sí |
| 2 | 03:35-36 EA, PSO y DE no usan gradientes: n_grad = 0 | `results/data/part1/summary.json` `configuraciones[*].n_grad_medio` (ea, pso, de) | 0.0 en las 12 filas | sí |
| 3 | 03:36-38 En la tabla de sensibilidad se reutilizan sus filas principales, que conservan k = 2n | `experiment.py` `_tabla_de_sensibilidad` (copia); `summary.json` `sensibilidad_k1[*].k` | ea/pso/de: entrada idéntica a la principal, k = 4 (2D) / 6 (3D); gdfijo/gdarmijo: k = 1 | sí |
| 4 | 03:40-44 Recosteo = mismas corridas con n_f + n_grad; re-ejecución = correr de nuevo con k = 1; la tabla de sensibilidad usa la re-ejecución y el recosteo es un campo de cada fila | `metricas.py` tabla de la celda (l. 173-177); `summary.json` `sensibilidad_k1` (gdfijo 2D: `eval_equiv_medio` 20000, `_k2n` 80000, `_k1` 20000) | concuerda | sí |
| 5 | 03:43 Con k = 1 el mismo presupuesto alcanza para más gradientes y la trayectoria se alarga | `summary.json` gdfijo 2D: principal `eval_equiv_medio_k1` 5000 (5 000 gradientes) vs `sensibilidad_k1` 20000 con k = 1 | 5 000 → 20 000 gradientes | sí |
| 6 | 03:54-56 Tres campos: `eval_equiv_medio` (k de la corrida), `_k2n` (n_f + 2n·n_grad), `_k1` (n_f + n_grad) | `metricas.py` l. 173-175 y `resumir_configuracion` l. 243-245 | idéntico | sí |
| 7 | 03:58 Evaluaciones hasta el éxito medidas con la k de la corrida, sin recostear | `metricas.py` l. 177 (`history`, `eval_equiv` con la k de la corrida) | idéntico | sí |
| 8 | 03:46-50 20 configuraciones, 30 corridas, semillas 0-29, base_seed 0 (texto previo reubicado; se añade "f* el valor mínimo") | `summary.json` `meta.runs`, `meta.semillas`; `functions.py` `f_star` | 30; 0..29; f* = 0 | sí |
| 9 | 03:60-62 / 65 Tabla `parametros-gd` rotulada como valores por defecto | `base.yaml` bloque `gd` | 1e-3, 2e-3, 1.0, 0.5, 1e-4 | sí |
| 10 | 03:122-124 L ≈ 5 971 (2D), 6 838 (3D) → η ≤ 1/L = 1.67e-4 (2D) y 1.46e-4 (3D) | Spec §6.3 l. 326; cálculo propio 1/5971, 1/6838 | 1.6748e-4; 1.4624e-4 | sí |
| 11 | 03:130-131 GD fijo en Rosenbrock re-ejecutado con η = 1.5e-4, mismas 30 semillas, mismo presupuesto, k = 2n | `part1_eta_1l/summary.json` `meta` (runs 30, semillas 0..29, presupuesto 10000, k_regla 2n); `part1_eta_1l/runs/*.json` `config.gd.eta.rosenbrock` | 0.00015 en las 60 corridas (30 por dimensión) | sí |
| 12 | 03:131-132 "Ese valor es el que la sección 6.3 del Spec da, redondeado, para η = 1/L" | Spec §6.3 l. 326 "η ≤ 1.7e-4 / 1.5e-4" | la Spec da 1.7e-4 en 2D y 1.5e-4 en 3D; 1.5e-4 es solo la cota redondeada de 3D | **imprecisa** |
| 13 | 03:132-133 Cumple η ≤ 1/L en 2D; en 3D supera a 1/L en un 2.6 % | cálculo propio: 1.5e-4·5971 = 0.896; 1.5e-4·6838 = 1.0257 | 2D cumple; 3D +2.57 % | sí |
| 14 | 03:135 Mediana de f_final 0.147 (2D) y 0.219 (3D) con η = 1.5e-4 | `part1_eta_1l/summary.json` gdfijo `f_final.mediana` | 0.14706; 0.21888 | sí |
| 15 | 03:135-136 Solo el 6.7 % llega a 1e-2 en cada dimensión; ninguna a 1e-4 | ídem `tasa_exito` | 1e-2: 0.0667 / 0.0667; 1e-4: 0 / 0 | sí |
| 16 | 03:136-137 Con η = 1e-3: mediana 1.905e-3 (2D) y 1.285e-3 (3D); a 1e-2 llegan 100 % y 96.7 % | `part1/summary.json` gdfijo rosenbrock `f_final.mediana`, `tasa_exito.1e-02` | 1.90549e-3, 1.28510e-3; 1.0, 0.9667 | sí |
| 17 | 03:137-138 Con el paso pequeño las corridas consumen los 5 000 gradientes | `part1_eta_1l/summary.json` `n_grad_medio` | 5000.0 (2D y 3D) | sí |
| 18 | 03:138-141 Mal condicionamiento del valle presentado como "explicación esperada", no probada | — (afirmación causal) | redactada como hipótesis | sí (hipótesis) |
| 19 | 03:149 Tabla `sensibilidad-eta`, 2D η = 1e-3: media 1.962e-03, mediana 1.905e-03, 100.0 %, 3.3 % | `part1/summary.json` gdfijo rosenbrock 2D | 1.96234e-3; 1.90549e-3; 1.0; 0.0333 | sí |
| 20 | 03:150 2D η = 1.5e-4: 3.581e-01, 1.471e-01, 6.7 %, 0.0 % | `part1_eta_1l/summary.json` 2D | 0.35805; 0.14706; 0.0667; 0 | sí |
| 21 | 03:151 3D η = 1e-3: 1.663e-03, 1.285e-03, 96.7 %, 3.3 % | `part1/summary.json` 3D | 1.66330e-3; 1.28510e-3; 0.9667; 0.0333 | sí |
| 22 | 03:152 3D η = 1.5e-4: 3.910e-01, 2.189e-01, 6.7 %, 0.0 % | `part1_eta_1l/summary.json` 3D | 0.39098; 0.21888; 0.0667; 0 | sí |
| 23 | 03:227-229 Hiperparámetros afinables: η; η0, β, c; N y fracciones del EA; inercia y coeficientes del PSO; NP, F, CR | `base.yaml` `hpo.espacios` | coincide (el PSO incluye además N y `vmax_frac`, que la tabla sí lista) | sí |
| 24 | 03:230-231 Lazo externo de búsqueda aleatoria; se conserva la mejor | Spec §6.9 l. 380; `hpo.py` `_sortear_valor` | coincide | sí |
| 25 | 03:234-236 Dos versiones sobre semillas 0-29, mismo presupuesto y k; `comparacion.csv` lado a lado; el afinado va a `results/data/part1_tuned/` (R8) | `part1/summary.json` `meta` == `part1_tuned/summary.json` `meta` (comparación propia); Spec R8 l. 388; `tuned.yaml` `salida` | metas idénticas; `results/data/part1_tuned` | sí |
| 26 | 03:240-241 R1: 30 ensayos, 5 semillas, presupuesto 10 000·n, k = 2n | `base.yaml` `hpo.ensayos`, `hpo.semillas`, `presupuesto_por_dim`; `ensayos_*.json` `meta.k_regla` | 30; 5; 10000; "2n" | sí |
| 27 | 03:241-242 600 corridas de ajuste por método (30 × 5 × 4); gdfijo en dos unidades de 300 | `seleccion.json` `unidades[*].corridas_de_ajuste` | 300, 300, 600, 600, 600, 600 | sí |
| 28 | 03:243-244 R2: semillas de ajuste 1000-1004 (`hpo.base_seed = 1000`), disjuntas de 0-29; si se solaparan, config inválida | `seleccion.json` `meta.semillas_de_ajuste`; `hpo.py` `_validar_semillas` (ValueError) | [1000..1004]; lanza ValueError | sí |
| 29 | 03:245-246 R3: ensayo 0 = defecto, mismas semillas | `ensayos_pso.json` `ensayos[0].parametros` == `meta.bloque_base`; Spec R3 | coincide | sí |
| 30 | 03:247-249 R4: `uniforme`, `log`, `entero` (extremos incluidos); inválida se vuelve a sortear y no cuenta | `hpo.py` l. 555-566, `rng.integers(..., endpoint=True)`; Spec R4 | coincide (hasta 200 intentos) | sí |
| 31 | 03:250-252 R5: un conjunto por método salvo `gd.eta.{func}`; 6 unidades; 3 000 corridas | Spec R5; `seleccion.json` `meta.corridas_de_ajuste_total` | 6 unidades; 3000 | sí |
| 32 | 03:254-255 No se afinan generaciones, iteraciones, esquema, reevaluar_elite ni tol_grad | `base.yaml` comentario de `hpo.espacios`; Spec R7 | coincide | sí |
| 33 | 03:262-277 Tabla `espacios-hpo`: los 16 intervalos, tipos y defectos | `base.yaml` `hpo.espacios` y bloques `gd`, `ea`, `pso`, `de` | los 16 coinciden | sí |
| 34 | 03:263-265 Significados de η0, β, c | `gd.py` l. 86, 96, 101-103 | "η₀ inicial"; "cada búsqueda lineal arranca en η = η₀"; "η ← β·η"; "constante c de Armijo" | sí |
| 35 | 03:266-268 Significados de N, f_e, f_m del EA | `ea.py` `ParametrosEA` (N: "número de individuos por generación"; fracciones: solo "fracciones de N"); markdown del módulo (`seleccionar_elite` "copia los n_e mejores"); comentarios de `base.yaml` | el docstring de `ParametrosEA` no da el significado de cada fracción; sale del markdown del módulo y de `base.yaml` | sí (fuente parcial) |
| 36 | 03:269 f_c = "fracción de N que se cruza" | `ea.py` `_calcular_tamanos_de_grupos` l. 155-157 (`n_cruzantes = max(par(int(N·frac_c)), par(N − n_e − n_m))`) | el relleno puede anular `frac_c`: con los valores afinados (N 117, frac_c 0.4854) da 78 cruzantes (0.667 N), no 56 (0.485 N) | **imprecisa** |
| 37 | 03:270-274 Significados de N, w, c1, c2, vmax_frac del PSO | `pso.py` `ParametrosPSO` | "número de partículas"; "factor que amortigua la velocidad anterior"; "peso de la atracción hacia el mejor personal / global"; "v_max = fraccion_vmax·(ub − lb)" | sí |
| 38 | 03:275-277 Significados de NP, F, CR del DE | `de.py` `ParametrosDE` | "número de individuos"; "escala de la diferencia x_{r2} − x_{r3}"; "probabilidad de que cada gen del hijo venga del mutante" | sí |
| 39 | 03:283-285 Recorte: mediana de max(f_best − f*, 1e-6); 1e-6 = umbral más estricto | `hpo.py` `UMBRAL_HPO = min(UMBRALES)`, l. 822; `summary.json` `meta.umbrales` | 1e-6 = mín(1e-4, 1e-2, 1e-6) | sí |
| 40 | 03:285 "por debajo de 1e-6 las diferencias entre ensayos son ruido numérico" | Spec R6 ("evita elegir por ruido numérico"); `ensayos_pso.json` medianas sin recortar 7.7e-25 frente a 0.0 | es la justificación de diseño de la Spec; no está medido que sean ruido (son diferencias reales, irrelevantes frente al umbral) | imprecisa (heredada de la Spec, leve) |
| 41 | 03:286-288 Rangos con empates = rango promedio, 1 = mejor; por escalas distintas | `hpo.py` `_rango_promedio` (l. 836-840); Spec R6 | coincide | sí |
| 42 | 03:289 Puntaje = promedio de rangos sobre las celdas | `hpo.py` `_claves_exactas` l. 860-862 | coincide | sí |
| 43 | 03:290-294 Reemplazo estricto; desempates (mayor tasa a 1e-6, menos evaluaciones con +∞, menor índice) solo entre empatados si r* < r0; nunca contra el ensayo 0; aritmética exacta | `hpo.py` `elegir_ganador`, `_clave_de_orden`; Spec R3/R6 | coincide | sí |
| 44 | 03:296-298 PSO: ensayos 0 y 3 con mediana recortada 1e-6 en las 4 celdas, rangos 14, 2, 14, 12 y puntaje 10.5 | `ensayos_pso.json` (recalculado); `seleccion.json` `pso.puntaje_defecto.rango`; `regla_v1/seleccion.json` `pso.puntaje_ganador.rango` | medianas 1e-6 ×4 en ambos; rangos {14, 2, 14, 12}; 10.5; únicos empatados en el mínimo: [0, 3] | sí |
| 45 | 03:298-299 Ensayo 3: 19 de 20 éxitos a 1e-6 frente a 18 de 20 | recálculo propio; `regla_v1/seleccion.json` `exitos_1e-06_por_celda` | ensayo 0: 5+3+5+5 = 18; ensayo 3: 5+5+5+4 = 19 | sí |
| 46 | 03:302-305 Regla anterior: el ensayo 3 reemplazaba al defecto en el PSO y el 6 en el DE (20/20 frente a 19/20) | `regla_v1/seleccion.json` `pso.ganador`, `de.ganador`, `exitos_1e-06_por_celda` | 3; 6; DE ensayo 6: 20, ensayo 0: 5+5+5+4 = 19 | sí |
| 47 | 03:305 El problema se notó al comparar contra las semillas de reporte | `alucinaciones/prompts/T1.11.md` ("lo que motivó mirarla fue comparar contra las semillas de reporte") | según el prompt; no hay otra evidencia en archivos | sí (según el prompt) |
| 48 | 03:306-307 Regla anterior, éxito a 1e-4: PSO Rastrigin 2D 100 → 93.3 %, 3D 86.7 → 50.0 %; DE 2D 100 → 86.7 %, 3D 93.3 → 80.0 % | `regla_v1/comparacion.csv` `tasa_exito_1e-04_*` | 1.0→0.933; 0.867→0.5; 1.0→0.867; 0.933→0.8 | sí |
| 49 | 03:307-308 En tasa de éxito solo el PSO en Rosenbrock 3D mejoraba, 40 → 100 % a 1e-6 | `regla_v1/comparacion.csv` filas pso/de, `tasa_exito_1e-04_*` y `tasa_exito_1e-06_*` | ninguna otra fila pso/de sube; pso Rosenbrock 3D 1e-6: 0.4 → 1.0 | sí |
| 50 | 03:309 Evidencia en `results/data/part1_hpo/regla_v1/` | `git ls-files` | 4 archivos versionados | sí |
| 51 | 03:309-310 Las otras cuatro unidades eligen el mismo ensayo con las dos versiones | `seleccion.json` vs `regla_v1/seleccion.json` `ganador` | 26, 0, 10, 13 en ambas | sí |
| 52 | 03:310-311 La corrección no es independiente de las semillas de reporte (limitación declarada) | — | afirmación de método, honesta | sí |
| 53 | 03:311-313 Puntaje principal idéntico al del defecto: 10.5 (PSO) y 14.625 (DE) | `regla_v1/seleccion.json` `puntaje_defecto.rango_medio` y `puntaje_ganador.rango_medio` | 10.5 = 10.5; 14.625 = 14.625 | sí |
| 54 | 03:232-233 Dos `TODO(cita)` (Bergstra y Bengio 2012; Eiben y Smit 2011), sin cita en el texto | `blog/references.bib` (12 claves; ninguna de las dos) | no hay cita nueva `[@...]` en el diff | sí (contenido de las obras: n/v) |

## Sección 04 (resultados)

| # | Afirmación (sección y línea) | Archivo y campo fuente | Valor fuente | Coincide |
|---|---|---|---|---|
| 55 | 04:21-26 Cambiaron 3 de 6 unidades (gdfijo/rosenbrock, gdarmijo con 3 parámetros, ea con 4); gdfijo/rastrigin, pso y de conservaron el defecto | `seleccion.json` `ganador`, `elegido` | 26, 0, 10, 13, 0, 0 | sí |
| 56 | 04:25-26 En esas tres unidades ningún ensayo superó al defecto | recálculo propio de puntajes (`ensayos_*.json`) | mínimo = puntaje del 0: 10.0, 10.5, 14.625 | sí |
| 57 | 04:33 η 0.001 → 0.001494 | `seleccion.json` gdfijo_rosenbrock `defecto`, `elegido`; `tuned.yaml` | 0.001 → 0.0014940661 | sí |
| 58 | 04:34-36 η0 1.0 → 3.520; β 0.5 → 0.1243; c 0.0001 → 0.006728 | `seleccion.json` gdarmijo | 3.5200920; 0.1242768; 0.0067276 | sí |
| 59 | 04:37-40 N 50 → 117; f_e 0.15 → 0.1650; f_m 0.1 → 0.1766; f_c 0.75 → 0.4854 | `seleccion.json` ea | 117; 0.1649790; 0.1766353; 0.4853649 | sí (ver #36: f_c es inerte en el punto afinado) |
| 60 | 04:43-46 30 semillas de reporte, mismo presupuesto, k = 2n | `part1_tuned/summary.json` `meta` == `part1/summary.json` `meta` | idénticos | sí |
| 61 | 04:53 Ros 2D gdfijo 1.905e-03 → 2.402e-04; 3.3 → 23.3 %; 19220 → 16759 | `part1_tuned/comparacion.csv` | 1.90549e-3 → 2.40187e-4; 0.0333 → 0.2333; 19220.0 → 16759.43 | sí |
| 62 | 04:54 Ros 2D gdarmijo 2.326e-03 → 1.259e-06; 16.7 → 100 %; 9976 → 10140 | ídem | 2.32604e-3 → 1.25897e-6; 0.1667 → 1.0; 9976.4 → 10140.4 | sí |
| 63 | 04:55 Ros 2D ea 9.329e-03 → 3.182e-07; 10 → 93.3 %; 2613 → 8702 | ídem | 9.32924e-3 → 3.18177e-7; 0.1 → 0.9333; 2612.67 → 8702.5 | sí (8702.5 redondeado al par) |
| 64 | 04:56 Ros 2D pso 3.320e-24; 100 %; 1555 | ídem | 3.32001e-24; 1.0; 1555.47 | sí |
| 65 | 04:57 Ros 2D de 0; 100 %; 984 | ídem | 0.0; 1.0; 984.5 | sí (984.5 redondeado al par; con redondeo convencional, 985) |
| 66 | 04:58 Ros 3D gdfijo 1.285e-03 → 4.777e-04; 3.3 → 0 %; 25998 → — | ídem | 1.28510e-3 → 4.77689e-4; 0.0333 → 0; 25998.0 → vacío | sí |
| 67 | 04:59 Ros 3D gdarmijo 1.338e-03 → 2.428e-05; 0 → 63.3 %; — → 22558 | ídem | 1.338e-3 → 2.428e-5; 0 → 0.6333; vacío → 22558.21 | sí |
| 68 | 04:60 Ros 3D ea 3.269e-01 → 1.100e-01; 0 → 0 %; — → — | ídem | 0.3269 → 0.1100; 0 → 0 | sí |
| 69 | 04:61 Ros 3D pso 3.846e-06; 100 %; 19103 | ídem | 3.846e-6; 1.0; 19102.57 | sí |
| 70 | 04:62 Ros 3D de 0; 100 %; 2213 | ídem | 0.0; 1.0; 2212.67 | sí |
| 71 | 04:70 Ras 2D gdfijo 1.642e+01; 0 %; — | ídem | 16.42; 0; vacío | sí |
| 72 | 04:71 Ras 2D gdarmijo 2.985 → 4.975; 16.7 → 6.7 %; 160 → 142 | ídem | 2.985 → 4.975; 0.1667 → 0.0667; 160.2 → 142.0 | sí |
| 73 | 04:72 Ras 2D ea 0 → 1.089e-10; 93.3 → 100 %; 3256 → 7915 | ídem | 0 → 1.089e-10; 0.9333 → 1.0; 3255.86 → 7915.4 | sí |
| 74 | 04:73 Ras 2D pso 0; 100 %; 1664 | ídem | 0; 1.0; 1663.9 | sí |
| 75 | 04:74 Ras 2D de 0; 100 %; 2174 | ídem | 0; 1.0; 2174.5 | sí (2174.5 redondeado al par; convencional, 2175) |
| 76 | 04:75 Ras 3D gdfijo 2.438e+01; 0 %; — | ídem | 24.38; 0 | sí |
| 77 | 04:76 Ras 3D gdarmijo 8.955 → 17.41; 0 %; — | ídem | 8.955 → 17.41; 0 → 0 | sí |
| 78 | 04:77 Ras 3D ea 0.995 → 0; 46.7 → 96.7 %; 3677 → 8492 | ídem | 0.9950 → 0; 0.4667 → 0.9667; 3676.57 → 8492.17 | sí |
| 79 | 04:78 Ras 3D pso 0; 86.7 %; 3332 | ídem | 0; 0.8667; 3332.42 | sí |
| 80 | 04:79 Ras 3D de 0; 93.3 %; 4981 | ídem | 0; 0.9333; 4981.29 | sí |
| 81 | 04:82-83 gdarmijo Rosenbrock: 16.7 → 100 % (2D), 0 → 63.3 % (3D); mediana 2.33e-3 → 1.26e-6 (2D) | ídem | coincide | sí |
| 82 | 04:83-85 EA: Ros 2D 10 → 93.3 %; Ras 2D 93.3 → 100 %; Ras 3D 46.7 → 96.7 %; Ros 3D sin éxitos, mediana 0.327 → 0.110 | ídem | coincide | sí |
| 83 | 04:85-86 gdfijo Ros 2D 3.3 → 23.3 % | ídem | coincide | sí |
| 84 | 04:86-88 Donde el EA gana en éxito, sus evaluaciones hasta el éxito suben (2613 → 8702); medias sobre conjuntos distintos | ídem (Ros 2D, Ras 2D, Ras 3D) | 2613 → 8702; 3256 → 7915; 3677 → 8492 (suben en las tres) | sí |
| 85 | 04:90-91 gdarmijo Rastrigin: mediana 2.985 → 4.975 (2D), 8.955 → 17.41 (3D); éxito 2D 16.7 → 6.7 % | ídem | coincide | sí |
| 86 | 04:91-92 gdfijo Ros 3D: éxito 3.3 → 0 %, mediana 1.285e-3 → 4.777e-4 | ídem | coincide | sí |
| 87 | 04:94-95 gdfijo Rastrigin, PSO y DE idénticos porque conservaron el defecto | ídem (todas sus columnas defecto = afinado) | idénticas | sí |

## Sección 08 (discusión)

| # | Afirmación (sección y línea) | Archivo y campo fuente | Valor fuente | Coincide |
|---|---|---|---|---|
| 88 | 08:16-18 PSO y DE por defecto, a 1e-4: 100 % en Ros 2D, Ros 3D y Ras 2D; Ras 3D: PSO 86.7 %, DE 93.3 % | `part1/summary.json` `tasa_exito.1e-04` | coincide | sí |
| 89 | 08:18 A 1e-6, mismas tasas salvo PSO Ros 3D (40 %) | ídem `tasa_exito.1e-06` | todas iguales salvo pso Ros 3D 0.4 | sí |
| 90 | 08:19-20 En el ajuste, el defecto de ambos tiene mediana recortada 1e-6 en las 4 celdas; el mejor ensayo empató en puntaje (10.5 y 14.625) | recálculo propio (`ensayos_pso.json`, `ensayos_de.json`) | medianas 1e-6 ×4 (ambos); mínimo = puntaje del 0 | sí |
| 91 | 08:20-22 "Ningún ensayo los superó con claridad" | ídem | ningún ensayo los superó en absoluto (r* = r0) | sí (el texto es más débil que el dato) |
| 92 | 08:26-27 gdarmijo: rango Ros 2D 22 → 4; Ras 3D 6.5 → 9.5 | `seleccion.json` gdarmijo `puntaje_defecto.rango`, `puntaje_ganador.rango` | 22 → 4; 6.5 → 9.5 | sí |
| 93 | 08:27-28 Con reporte, gdarmijo afinado mejora en Rosenbrock y empeora en Rastrigin | `part1_tuned/comparacion.csv` | Ros: medianas bajan, éxito sube; Ras: medianas suben, éxito 2D baja | sí |
| 94 | 08:29-31 gdfijo Ros: rango 4 → 3 (2D) y 2 → 1 (3D); reporte 3.3 → 23.3 % (2D) y 3.3 → 0 % (3D) | `seleccion.json` gdfijo_rosenbrock; `comparacion.csv` | coincide | sí |
| 95 | 08:33-35 gdarmijo Ras 2D, ajuste 4.975 → 1.99, reporte 2.985 → 4.975; 3D ajuste 5.97 → 7.96, reporte 8.955 → 17.41 | `seleccion.json` `mediana_recortada` (ensayo 0 y 10); `comparacion.csv` | 4.9748 → 1.9899; 5.9697 → 7.9597; reporte coincide | sí |
| 96 | 08:35-36 Diferencia "compatible con ruido de muestreo", no probada | — (causal) | redactada como hipótesis | sí (hipótesis) |
| 97 | 08:38-39 30 ensayos por unidad, "pocos para espacios de hasta cinco hiperparámetros" | `base.yaml` `hpo.ensayos` 30; PSO tiene 5 hiperparámetros | 30; máx. 5 | cifras sí; el juicio "pocos" es n/v (valoración sin cita) |
| 98 | 08:39 Los espacios se eligieron a mano | `alucinaciones/prompts/T1.10.md` (intervalos de R7 fijados en el prompt) | intervalos fijados a mano | sí |
| 99 | 08:39-41 Presupuesto del ajuste = el del reporte; todo el ajuste usa k = 2n; con k = 1 la mejor configuración "podría" ser otra | `ensayos_*.json` `meta.presupuesto_por_dim` 10000, `meta.k_regla` "2n" | coincide; la consecuencia está como posibilidad | sí |
| 100 | 08:46-49 η = 1.5e-4 "que el Spec da para η = 1/L" (supera 1/L en 3D en 2.6 %); mediana 0.147 / 0.219 frente a 1.905e-3 / 1.285e-3 | como #12, #13, #14, #16 | cifras coinciden; atribución a la Spec, imprecisa como en #12 | cifras sí; atribución **imprecisa** |
| 101 | 08:49-51 1/L con la curvatura máxima en todo el dominio; en el valle la curvatura es menor | Spec §6.3 (L = máx. valor propio en el dominio; λ_max(x*) ≈ 1 001.6); comprobación propia en 2D sobre y = x² dentro del dominio | λ_max en el valle (2D) entre 200 y ≈ 1 840 < 5 971 | sí (2D verificado; 3D no verificado) |
| 102 | 08:51-52 Paso "demasiado corto" como explicación esperada; el experimento solo muestra que no llega con 5 000 gradientes | `part1_eta_1l/summary.json` `n_grad_medio` 5000 | hipótesis bien marcada | sí |
| 103 | 08:52-53 La HPO eligió η ≈ 1.494e-3, mayor que 1e-3 y sin garantía global | `tuned.yaml` `gd.eta.rosenbrock`; 1.494e-3 > 1/L | 0.0014941 | sí |

## Sección 11 (reproducibilidad)

| # | Afirmación (sección y línea) | Archivo y campo fuente | Valor fuente | Coincide |
|---|---|---|---|---|
| 104 | 11:2 Cabecera sin nombre ("RESPONSABLE: puente") | diff | sin nombre | sí |
| 105 | 11:28-29 Demo de unos 7 s; pocos ensayos y semillas; solo escribe en carpetas `*_hpo_demo`, ignoradas | `T1.10.md` Resultado ("Demo ... 7 s"); `hpo_demo.yaml` (6 ensayos, 3 semillas; salidas bajo `*_hpo_demo`); `.gitignore` | 7 s; todas las rutas bajo `part1_hpo_demo`; ignoradas | sí |
| 106 | 11:31-33 HPO completa: 406 s (~7 min) con 6 procesos | `T1.10.md` Resultado ("HPO completa `--set workers=6` (8 núcleos): 406 s") | 406 s = 6,8 min | sí |
| 107 | 11:35-36 Reanudación 110 s, sin repetir corridas de ajuste | `T1.10b.md` Resultado ("Reanudación ...: 110 s; 3 000 corridas de ajuste") | 110 s (`T1.10.md` registra otra reanudación de 123 s) | sí |
| 108 | 11:38-39 `python run.py part1 --config configs/part1/tuned.yaml` | `T1.11.md` notas del orquestador (exit 0 con `--set runs=2` a carpetas ignoradas) | arranca | sí (según el orquestador; no lo volví a ejecutar) |
| 109 | 11:42-44 La HPO escribe `ensayos_<unidad>.json` y `seleccion.json`, `tuned.yaml`, `part1_tuned/` y `comparacion.csv`; no reescribe `results/data/part1/` | `hpo_experimento.py` tabla de salidas (l. 33-43), `_validar_summary_por_defecto` (exige el summary por defecto; no lo genera fuera del demo); Spec R8 | coincide | sí |
| 110 | 11:44-45 `tuned.yaml` hereda de `base.yaml` y "solo trae los valores que cambiaron"; no se edita a mano | `configs/part1/tuned.yaml` (cabecera y contenido) | hereda de `base.yaml`; trae lo que cambió **más `salida` y `tablas`** | **imprecisa** (leve) |
| 111 | 11:47-49 Se versionan `results/data/part1_hpo/` (con `regla_v1/`), `tuned.yaml`, los `summary.json` y los CSV de `results/tables/` | `git ls-files results/ configs/part1` | los 3 `summary.json`, los 7 CSV de tablas, `part1_hpo/` completo y `tuned.yaml` versionados | sí |
| 112 | 11:49-51 No se versionan `runs/` ni `k1/runs/` ni las carpetas `*_demo`; decisión provisional | `.gitignore` (bloques "Provisional"); `git ls-files` (0 archivos bajo `/runs/`) | coincide | sí |

## Resumen

**Total auditadas: 112 afirmaciones** (54 en la sección 03, 33 en la 04, 16 en la 08 y 9 en la 11; cada fila de tabla
cuenta como una afirmación), contrastadas una a una contra el archivo fuente. Ninguna cifra es falsa: todos los valores
de las tablas `sensibilidad-eta`, `espacios-hpo`, `hpo-parametros`, `hpo-rosenbrock` y `hpo-rastrigin` coinciden con su
fuente, y los rangos, puntajes y conteos de éxitos de la HPO se reprodujeron con un recálculo independiente desde los
`ensayos_*.json` (los ganadores 26, 0, 10, 13, 0 y 0 salen igual).

**Discrepancias: 0 "no"; 4 "imprecisa" con corrección propuesta.**

1. **#12 y #100. "Ese valor es el que la sección 6.3 del Spec da, redondeado, para η = 1/L"** (03:131-132; 08:46-47). La
   Spec §6.3 (l. 326) da dos cotas, 1.7e-4 (2D) y 1.5e-4 (3D); 1.5e-4 es solo la de 3D, y se usó en las dos dimensiones.
   Propuesta para 03: "Ese valor es la cota redondeada que la sección 6.3 del Spec da para 3D (para 2D da 1.7e-4); se
   usó el mismo valor en las dos dimensiones." En 08, "el paso que el Spec da para η = 1/L" → "el paso η = 1.5e-4, la
   cota redondeada del Spec para 3D, …".
2. **#36. Significado de `frac_c`: "fracción de N que se cruza"** (03:269). En `ea.py` el número de cruzantes es
   `max(par(int(N·frac_c)), par(N − n_e − n_m))`, así que el relleno puede anular `frac_c`. Con los valores afinados
   (N 117, n_e 19, n_m 20) salen 78 cruzantes (0.667·N), no 56 (0.485·N); con los de defecto salen 38 (0.76·N). En el
   punto afinado, `frac_c` = 0.4854 es inerte: cualquier valor ≤ 0.666 da el mismo EA. La tabla `hpo-parametros`
   (04:40) muestra "0.75 → 0.4854", que sugiere menos cruce, cuando la fracción efectiva pasa de 0.76 a 0.667. Propuesta:
   en `espacios-hpo`, "fracción mínima de N que se cruza (el relleno hasta N puede aumentarla)"; en 04, una nota: "con
   N = 117, f_e y f_m afinados, el relleno fija 78 cruzantes (0.667·N) y el valor de f_c no influye". Es el pendiente
   T1.4 (d) de `docs/MEMORIA.md`, que no se había llevado al blog.
3. **#110. "`tuned.yaml` … solo trae los valores que cambiaron"** (11:45). El archivo también trae `salida` y `tablas`.
   Propuesta: "solo trae los valores que cambiaron y sus carpetas de salida (`salida`, `tablas`)".
4. **#40. "por debajo de 1e-6 las diferencias entre ensayos son ruido numérico"** (03:285). Es la justificación de la
   Spec R6 escrita como un hecho. Las diferencias (por ejemplo, 7.7e-25 frente a 0.0 en PSO Rosenbrock 2D) son reales,
   aunque irrelevantes frente al umbral más estricto. Propuesta (leve): "por debajo de ese umbral las diferencias se
   tratan como empate, para no elegir por diferencias del orden del ruido numérico".

**Observaciones menores (no son discrepancias):**

- #63, #65 y #75: las evaluaciones medias 8702.5, 984.5 y 2174.5 se escriben 8702, 984 y 2174, redondeadas al par (el
  `round` de Python). Con el redondeo convencional serían 8703, 985 y 2175. Conviene decidir una convención o escribir
  un decimal.
- #35: el docstring de `ParametrosEA` no explica qué es cada fracción; el significado de f_e y f_m sale del markdown de
  `ea.py` y de los comentarios de `base.yaml` (la fuente de la tabla dice "docstrings").
- La sección 03 presenta R1-R8 como reglas del Spec sin decir que la Spec §6.9 sigue `[PENDIENTE: aprobación de Daniel]`.
- Spec §6.3 l. 327 (no es texto del blog): "mediana 1.8e-3 vs 1.3e-1 en 2D". Las medidas actuales con las semillas 0-29
  son 1.905e-3 y 1.471e-1. La Spec queda desactualizada o redondeada frente al resultado medido; y su "η ≤ 1.7e-4 /
  1.5e-4" está redondeada hacia arriba en 3D (H-41). Para Daniel; no se edita.

**No verificables localmente:**

- El contenido de Bergstra y Bengio (2012) y de Eiben y Smit (2011): solo están en comentarios `TODO(cita)`, no se citan
  y no están en `references.bib`, que es lo correcto.
- El juicio "30 ensayos son pocos para hasta cinco hiperparámetros" (08:38-39): valoración sin cita; cabría un
  `TODO(cita)` (Bergstra y Bengio).
- "El problema se notó al comparar contra las semillas de reporte" (03:305): solo lo respalda el prompt T1.11; en los
  archivos no hay registro independiente del orden de los hechos.
- La afirmación de curvatura del valle (08:50), verificada en 2D; en 3D no se comprobó.
- El arranque de `run.py part1 --config configs/part1/tuned.yaml` (11:39): este auditor no lo volvió a ejecutar (lo
  hicieron el orquestador y el auditor de reproducibilidad).

## Correcciones aplicadas después de esta auditoría (ronda 2 de T1.11)

| Imprecisión | Corrección en el blog |
|---|---|
| 1. "1,5e-4 es el 1/L redondeado de la Spec" | Es la cota redondeada que la Spec (6.3) da para 3D (para 2D da 1,7e-4); mismo valor en las dos dimensiones (secciones 03 y 08). Variante de H-41. |
| 2. frac_c = "fracción de N que se cruza" | "Fracción mínima de N que se cruza"; la sección 04 explica con `H-T1.11_cifras.txt` §13 que por defecto se cruzan 38 de 50 (0,760) y con los afinados 78 de 117 (0,667), por el relleno. H-42. |
| 3. "tuned.yaml solo trae los valores que cambiaron" | Trae `hereda`, `salida`, `tablas` y los hiperparámetros que cambiaron (sección 11). |
| 4. "por debajo de 1e-6 las diferencias son ruido numérico" (como hecho) | Presentado como decisión de diseño: se tratan como empate (sección 03). |
| Observación: redondeo de medias al par (8702, 984, 2174) | El script usa redondeo convencional: 8703, 985, 2175 (tablas de la sección 04). |
| revisor-spec: 6 líneas nuevas > 120 caracteres | Partidas o acortadas; 0 líneas nuevas > 120. |
| auditor-reproducibilidad: tiempos 406 s y 110 s dependen del equipo (medidos 377 s y 136 s) | Sección 11: "unos 6-7 min" y "unos 2 min"; aviso de que la HPO exige `results/data/part1/summary.json`. |
