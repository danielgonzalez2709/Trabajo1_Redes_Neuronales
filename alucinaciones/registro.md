# 🎯 Registro de la Cacería de la alucinación

> Meta: ≥5 hallazgos **genuinos** en ≥3 categorías. **Nunca inventar.** Un candidato sin prompt literal o sin evidencia no cuenta.
> Evidencias en `alucinaciones/evidencias/`. Prompts literales en `alucinaciones/prompts/`.

## Cobertura actual
| Categoría | Candidatos | Confirmados |
|---|---|---|
| Matemáticas | 1 | 0 |
| Código | 4 (H-07, H-08, H-09, H-10) | 0 |
| Datos del mundo real | 5 (H-01, H-02, H-04, H-05, H-06) | 2 (H-04, H-05; revisados y aprobados por el puente en el PR #1, 9-oct-2026) |
| Bibliografía | 0 | 0 |
| Conceptos | 0 | 0 |

---

## Plantilla
```markdown
### H-XX — <título corto>
- **Estado:** candidato / confirmado / descartado
- **Categoría:** Matemáticas | Código | Datos | Bibliografía | Conceptos
- **Herramienta y modelo:** · **Fecha:** · **Quién lo cazó:**
1. **Prompt (literal):**
2. **Respuesta relevante de la IA (cita textual o captura):**
3. **Cómo sospechamos:**
4. **Evidencia:** (derivación / experimento / fuente primaria con URL y fecha)
5. **Corrección:**
6. **Lección aprendida — ¿qué verificación lo habría evitado?:**
```

---

## Candidatos

### H-01 — "OSRM permite excluir peajes" (el servidor público no lo permite)
- **Estado:** candidato — prompt literal disponible (9-oct-2026)
- **Categoría:** Datos del mundo real / Código
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente, 29-sep-2026). Nota: el documento de Camila (1-oct-2026) lo plantea **correctamente** (OSRM local con extracto de Geofabrik); el mensaje previo del equipo Parte 2 era ambiguo sobre el servidor público. El hallazgo se atribuye solo a la respuesta de Claude.
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt A** (29-sep-2026).
2. **Respuesta relevante:** guía personal, sección 3.3: "OSRM / openrouteservice (distancias y tiempos, permiten excluir peajes)". Propuesta Parte 2: "Permite excluir peajes (exclude=toll) … Si usan el servidor público de demostración … hagan las consultas una sola vez".
3. **Cómo sospechamos:** al planear la descarga se probó la petición real antes de construir sobre ella.
4. **Evidencia:** `GET https://router.project-osrm.org/route/v1/driving/-3.7038,40.4168;2.1734,41.3851?overview=false&exclude=toll` → `{"code":"InvalidValue","message":"Exclude flag combination is not supported."}` (29-sep-2026). Sin `exclude` responde 617,8 km / 6,87 h. El perfil `car.lua` de OSRM sí declara `excludable = {toll}` → funciona en una instalación **local**. Reproducido el 2-oct-2026 01:28 UTC: misma respuesta → `evidencias/H-01_osrm.json`.
5. **Corrección:** OSRM local (Docker + Geofabrik) o openrouteservice con `avoid_features: ["tollways"]`.
6. **Lección:** distinguir "el software permite X" de "este servicio público permite X"; probar el endpoint real antes de diseñar sobre él.

### H-02 — Fin del peaje de la AP-68: fecha y alcance incompletos
- **Estado:** candidato — verificar con la fuente oficial
- **Categoría:** Datos del mundo real
1. **Prompt (literal):** PENDIENTE — el documento de Camila ("Trabajo 1 – Punto 2…", 1-oct-2026) es la **salida** de su sesión con IA, pero no incluye los prompts: pedírselos.
2. **Respuestas relevantes:**
   - Documento de Camila / propuesta Parte 2: "según el Ministerio, deja de ser de peaje el 11 de noviembre de 2026. Conecta Bilbao, Vitoria, Logroño y Zaragoza". Omite que **Álava y Bizkaia mantienen peaje** (tramos forales) y la AP-68 no pasa por la ciudad de Vitoria [verificar].
   - Claude (chat, 29-sep): "la AP-68 deja de cobrar el 10 de noviembre" — la concesión vence el 10, pero el Ministerio fija el fin del peaje el **11**.
3. **Cómo sospechamos:** contraste entre varias fuentes de prensa con fechas distintas.
4. **Evidencia:** PENDIENTE — fuente oficial del Ministerio / BOE núm. 225 (11-sep-2026), diputaciones forales.
5. **Corrección:** escenario base con fecha de corte 1-oct-2026 (AP-68 con peaje); escenario `post_ap68` con tramos de Álava y Bizkaia aún de pago.
6. **Lección:** para datos con vigencia, siempre preguntar "¿desde cuándo, hasta cuándo y en qué tramos?".

### H-03 — Paso de GD "justificado" con la curvatura en el mínimo (garantía solo local)
- **Estado:** candidato — prompt literal disponible (9-oct-2026)
- **Categoría:** Matemáticas / Conceptos
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente, 29-sep-2026)
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt B** (29-sep-2026).
2. **Respuesta relevante:** "Rosenbrock 2D en el mínimo: Hessiana … λ_max ≈ 1001.6 → η < ≈0.002" y luego, en el Spec v1.0, "usar η = 1e-3" como valor "justificado".
3. **Cómo sospechamos:** al evaluar qué dominio usar, se calculó la curvatura en todo el dominio, no solo en x*.
4. **Evidencia:** `evidencias/H-03_rosenbrock_dominio.py` y `.txt`: en [−2.048, 2.048]² la constante de Lipschitz del gradiente es L ≈ 5 971 → la
   garantía global exige η ≤ 1/L ≈ 1.7e-4; η = 1e-3 la viola (aunque empíricamente converge). En [−5, 10]² (L ≈ 122 133) el mismo η diverge.
   Lo correcto de la afirmación original: λ_max(x*) = 1001.6 (verificado).
5. **Corrección:** Spec v1.1 §6.3: η = 1e-3 declarado como elección empírica sin garantía global; η = 1/L como sensibilidad; Armijo como variante adaptativa.
6. **Lección:** una cota de estabilidad local (en el óptimo) no justifica un paso fijo desde inicios aleatorios lejanos; calcular L en todo el dominio.

### H-04 — "Las 9 capitales que difieren tienen ORIGENCOOR = Detección automática" (generalización sin verificar)
- **Estado:** confirmado por el cazador (8-oct-2026, evidencia independiente desde el crudo) — pendiente de revisión del puente
- **Categoría:** Datos del mundo real
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos` y orquestador de Claude Code, T2.1) · **Fecha:** 7/8-oct-2026 · **Quién lo cazó:** subagente `curador-datos` al ejecutar la tarea; confirmado por el orquestador y por el cazador
1. **Prompt (literal):** `alucinaciones/prompts/T2.1.md`, **Prompt 2** (pide "Señala cualquier diferencia > 0,5 km y explícala"): es el prompt al que responde el informe del subagente donde nace la generalización. El orquestador la amplificó ante el equipo y la copió en el **Prompt 3**, punto 4 ("incluida la observación de que 9 capitales tienen ORIGENCOOR = "Detección automática" en el NGMEP"); el Prompt 3 es, por tanto, salida de la IA, no su entrada.
2. **Respuesta relevante de la IA (literal, `evidencias/T2.1_transcripcion_extractos.txt`):**
   - Subagente (2026-10-08T04:10:38Z UTC): "IGR da el centro de la zona residencial del núcleo; el NGMEP, en estos casos, coincide con sus propias coordenadas del municipio, con origen "Detección automática"."
   - Orquestador al equipo (2026-10-08T04:11:10Z UTC = 7-oct, 23:11 local): "La contra es que en esas 9 capitales el NGMEP marca el origen de la coordenada como "Detección automática", que parece un proceso menos cuidado que el de IGR." (Corrección del cazador: la versión anterior de este registro citaba una paráfrasis como si fuera literal.)
3. **Cómo sospechamos:** el subagente, al escribir la caracterización, contó los valores de `ORIGENCOOR` en lugar de copiar la frase del prompt.
4. **Evidencia:** `evidencias/H-04_origencoor_ngmep.txt` (generado desde `cities_verificacion.csv`) y, de forma independiente desde el crudo `ENTIDADES.csv`, `evidencias/T2.1_verificacion.py` → `.txt` §4–5: de las 9 capitales que difieren, 8 tienen "Detección automática" y Valladolid "Coordinado_IGR Poblaciones"; en total, 38 de las 47 capitales tienen "Detección automática", así que ese valor **no distingue** a las 9 ni sirve como argumento de calidad contra el NGMEP. Ironía adicional: Valladolid, la única de las 9 cuyo origen es "Coordinado_IGR Poblaciones", está a 0,444 km del punto IGR.
5. **Corrección:** `data/caracterizacion_bloque1.md` documenta las cifras reales; el argumento usado para la decisión (NGMEP vs. IGR) se retira.
6. **Lección:** una afirmación del tipo "todos los casos X tienen la propiedad Y" exige contar también Y en los casos que no son X; un resumen de un resumen pierde los recuentos.

### H-05 — "En estos casos, el NGMEP coincide con sus coordenadas del municipio" como explicación de las 9 diferencias (propiedad que tienen las 47)
- **Estado:** confirmado por el cazador (8-oct-2026) — pendiente de revisión del puente. Es la **otra mitad** de la frase que originó H-04; el equipo puede decidir fusionarlos, pero se trata de una afirmación distinta, con evidencia distinta. **Corregido** el 8-oct-2026 en `data/caracterizacion_bloque1.md` §4 (cifras 8 078/8 132 y 47/47, sin atribuir causa).
- **Categoría:** Datos del mundo real (explicación espuria)
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.1) · **Fecha:** 7/8-oct-2026 · **Quién lo cazó:** cazador de alucinaciones (verificación adversarial de T2.1)
1. **Prompt (literal):** `alucinaciones/prompts/T2.1.md`, Prompt 2, punto 1: "Señala cualquier diferencia > 0,5 km y explícala". La frase se mantiene en la caracterización escrita tras el Prompt 3 (punto 4: limitaciones).
2. **Respuesta relevante de la IA (literal):**
   - Informe del subagente (2026-10-08T04:10:38Z, `evidencias/T2.1_transcripcion_extractos.txt`), bajo "**Explicación:**": "el NGMEP, en estos casos, coincide con sus propias coordenadas del municipio".
   - `data/caracterizacion_bloque1.md` §4, limitación 2: "**El punto NGMEP coincide con el del municipio.** En las 9 capitales distintas, la coordenada de la entidad "Capital de municipio" es exactamente la misma que la de la fila `TIPO = Municipio` del NGMEP."
3. **Cómo sospechamos:** tras H-04 (misma frase, misma estructura "en estos casos …"), se aplicó la lección de H-04: contar la propiedad también en los casos que no difieren.
4. **Evidencia:** `evidencias/T2.1_verificacion.py` → `.txt` §5: la coordenada de "Capital de municipio" es idéntica (texto exacto) a la de la fila `Municipio` en **47 de 47** capitales peninsulares (y en las 52 de `PROVINCIAS.csv`), incluidas las 38 que coinciden con IGR. `evidencias/T2.1_capital_vs_municipio.py` → `.txt`: lo mismo ocurre en **8 078 de los 8 132** municipios del NGMEP. Es una propiedad estructural del NGMEP (la Memoria dice que la tabla Municipios "se corresponde con un subconjunto" de Entidades y que las coordenadas de municipios y entidades son centroides "lo más centrado posible en el núcleo poblacional"), no una característica de las 9 capitales. Por tanto, no explica por qué esas 9 difieren de IGR. Lo que es verdad de la frase: en las 9, la igualdad se cumple.
5. **Corrección:** en `data/caracterizacion_bloque1.md` §4.2, sustituir por: "En las 47 capitales (y en 8 078 de los 8 132 municipios del NGMEP) la coordenada de la entidad capital es idéntica a la de la fila Municipio; esto no distingue a las 9 que difieren de IGR. La causa de las 9 diferencias sigue sin explicar." (pendiente: corresponde al `curador-datos`; el cazador no edita artefactos de datos).
6. **Lección:** misma que H-04: una explicación de "por qué difieren estos casos" debe ser una propiedad que los demás casos **no** tengan. Comprobarlo exige una línea de código y no se hizo; además, el error sobrevivió a la corrección de H-04 porque se corrigió solo la mitad de la frase.

### H-06 — Mérida en la lista de "homónimos de capitales" a verificar (no es capital de provincia)
- **Estado:** candidato (prompt literal disponible; falta confirmación del cazador)
- **Categoría:** Datos del mundo real
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente) · **Fecha:** 29-sep-2026 · **Quién lo cazó:** equipo Parte 2 durante T2.1 (8-oct-2026); origen rastreado por el puente (9-oct-2026)
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt A** (29-sep-2026); el error se repitió en las respuestas a los Prompts B (29-sep) y C (1-oct).
2. **Respuesta relevante de la IA (literal):**
   - Respuesta al Prompt A (guía personal del puente, §5.4, tabla de caza activa — archivo local no versionado): "coordenadas de capitales (confundir ciudad homónima, p. ej. Mérida de España/México, Córdoba de España/Argentina)".
   - Respuesta al Prompt B (`SOLUCIONES_PROPUESTAS.md` §3.2.1, local): "homónimos en otros países (Mérida, Córdoba, León, Valencia, Guadalajara…)".
   - Respuesta al Prompt C (Spec v1.0 §7.2, commit `2cd005b`): "homónimos fuera de España (Mérida, Córdoba, León, Valencia, Guadalajara)".
3. **Cómo sospechamos:** al construir `cities.csv`, Mérida no aparecía entre las 47 capitales del NGMEP (`construir_cities.py` emite el aviso "'Mérida' no corresponde a ninguna capital de provincia peninsular del IGN").
4. **Evidencia:** `data/raw/BD_Municipios-Entidades/PROVINCIAS.csv`: la capital de la provincia de Badajoz es Badajoz; Mérida es capital de la comunidad autónoma de Extremadura, no de provincia. `git show 2cd005b:docs/spec/SPEC.md` contiene la lista original.
5. **Corrección:** Spec v1.2 §7.2 retira Mérida de la lista.
6. **Lección:** una lista de "casos a verificar" debe derivarse de la lista oficial (las 47 capitales), no de asociaciones de memoria ("ciudades españolas con homónimos famosos"); confundir capital autonómica con capital de provincia es un error típico.

### H-07 — "PuLP trae CBC": falso desde PuLP 4.0 (además cambió la API de variables)
- **Estado:** candidato (prompt literal disponible; evidencia reproducible)
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente) · **Fecha:** 29-sep-2026 (afirmación) / 9-oct-2026 (detección) · **Quién lo cazó:** Claude como orquestador al ejecutar T0.1, al construir el entorno con versiones fijas
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt B** (29-sep-2026); repetido en la respuesta al Prompt C (Spec v1.0).
2. **Respuesta relevante de la IA (literal):**
   - `SOLUCIONES_PROPUESTAS.md` §1.1: "| Solver exacto TSP | **PuLP** (trae CBC) o **highspy** | OR-Tools | `pip install` y listo, también en Windows |".
   - Spec v1.0 §7.4: "Formulación DFJ con PuLP + CBC, eliminación iterativa de subtours".
3. **Cómo sospechamos:** al instalar `pip install pulp` en el entorno nuevo, `pulp.listSolvers(onlyAvailable=True)` devolvió `[]`.
4. **Evidencia:** `evidencias/H-07_pulp4.py` → `.txt` (PuLP 4.0.0, 9-oct-2026): sin extras no hay solvers; `PULP_CBC_CMD` ya no existe; `LpVariable("x", 0, 1, cat="Binary")` lanza `TypeError: LpVariable.__init__() got an unexpected keyword argument 'cat'`. Fuente primaria: página de PuLP en PyPI ("CBC is not shipped inside the PuLP package"; "Older releases bundled a CBC binary and exposed it as PULP_CBC_CMD; that API and the bundled solver are removed"), consultada el 9-oct-2026.
5. **Corrección:** `requirements.txt` instala `pulp[highs]` (highspy); Spec v1.3 §3 y §7.4: PuLP 4.0 + HiGHS y la API `problema.add_variable(...)`. La evidencia comprueba un TSP de 6 ciudades contra fuerza bruta (38 = 38).
6. **Lección:** las afirmaciones sobre librerías caducan con cada versión mayor; fijar versiones y comprobar la instalación real antes de diseñar sobre ellas. **Riesgo para el resto del proyecto:** cualquier subagente que escriba código PuLP "clásico" fallará → el Spec ya lo advierte.

### H-08 — "El contador nunca supera el presupuesto" (falso con k no entero; con k = ∞ el presupuesto se anula)
- **Estado:** candidato (prompt literal disponible; evidencia reproducible; severidad baja: no afecta al experimento, que usa enteros)
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `implementador`, T0.4) · **Fecha:** 9-oct-2026 · **Quién lo cazó:** subagente `verificador-matematico` (revisión de T0.4), reproducido de forma independiente por el orquestador
1. **Prompt (literal):** `prompts/T0.4.md`, prompt original de la tarea (pide "BudgetExhausted se lanza ANTES de exceder: el contador nunca supera el presupuesto, incluso con grad de costo k").
2. **Respuesta relevante de la IA:** `src/common/counter.py` (ronda 1) comprobaba `self.eval_equiv() + self.k > self.budget` y declaraba en su docstring y en `tests/test_budget.py` que el presupuesto nunca se excede; la prueba "con mezcla aleatoria" usaba k ∈ {1, 4, 6, 2.5}, todos representables exactamente en binario. La validación `not k > 0` aceptaba `k = inf`.
3. **Cómo sospechamos:** el prompt del verificador pedía explícitamente probar k no enteros y errores de punto flotante.
4. **Evidencia:** `evidencias/H-08_contador_redondeo.py` → `.txt`: con k = 1/3 y budget = 19.666666666666664, la comprobación previa da 19.666666666666664 (se acepta) pero el estado posterior es 19.666666666666668 > budget; con k = π y budget = 53.982297150257104 se rechaza una llamada que sí cabía; con k = ∞, eval_equiv = n_f + ∞·0 = NaN y el presupuesto deja de funcionar. El verificador reportó 28 excesos en 20 000 casos aleatorios con la versión de la ronda 1 y 0 con la corregida.
5. **Corrección:** ronda 2 de T0.4 — la comprobación previa usa la misma expresión que el estado posterior; k y budget deben ser finitos; pruebas con k no representables (1/3, 0.1, π, 2/7, 1.1).
6. **Lección:** una prueba "aleatoria" no cubre lo que no varía: si todos los valores de prueba son exactos en binario, el redondeo nunca aparece. Y "nunca X" en un docstring es una afirmación que hay que demostrar, no repetir.

### H-09 — "numpy escalar → float": `to_jsonable` deja `np.float64` sin convertir (y la prueba no lo detecta)
- **Estado:** candidato (prompt literal disponible; evidencia reproducible; severidad baja: el JSON se escribe bien porque `json` acepta subclases de `float`)
- **Categoría:** Código (también Conceptos: herencia de tipos de numpy)
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `implementador`, T0.3) · **Fecha:** 9-oct-2026 · **Quién lo cazó:** subagente `revisor-calidad`; reproducido por el orquestador
1. **Prompt (literal):** `prompts/T0.3.md`, prompt original ("to_jsonable(obj): convierte recursivamente tipos numpy (escalares, arreglos) … a tipos nativos de JSON").
2. **Respuesta relevante de la IA:** docstring de `src/common/results.py` (rondas 1–3): "numpy escalar → int/float/bool/str". La prueba `test_to_jsonable_convierte_tipos_numpy_tuplas_y_path` incluía `np.float64(0.1)` pero solo comparaba con `==`, y su verificación de tipos omitía justo esa clave.
3. **Cómo sospechamos:** revisión de calidad: `np.float64` es subclase de `float`, así que una rama `isinstance(obj, float)` colocada antes de la rama de numpy lo "atrapa" sin convertirlo.
4. **Evidencia:** `evidencias/H-09_to_jsonable_float64.txt`: `np.float64` → `numpy.float64` (suelto, en lista y en diccionario), mientras `np.int64` → `int` y `np.float32` → `float` (que no son subclases de tipos nativos). Es el tipo más frecuente en `history` y `f_best`.
5. **Corrección:** ronda 4 de T0.3 — comprobar `np.generic` antes que los tipos nativos; la prueba verifica `type(x) is float`.
6. **Lección:** `==` no prueba tipos; si un contrato habla de "tipos nativos", la prueba debe usar `type(x) is …`. Y en numpy, `float64 ⊂ float` (pero `float32` no): el orden de los `isinstance` importa.

### H-10 — Una prueba llamada "no comparte objetos" que no puede fallar
- **Estado:** candidato (prompt literal disponible; evidencia reproducible por prueba de mutación)
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `implementador`, T0.2 ronda 3) · **Fecha:** 9-oct-2026 · **Quién lo cazó:** subagente `revisor-calidad`; confirmado por el orquestador con una prueba de mutación
1. **Prompt (literal):** `prompts/T0.2.md`, ronda 3, punto 2 ("fusiona en profundidad … Pruebas: herencia simple y encadenada, la hija gana, listas reemplazadas, ciclo → error…").
2. **Respuesta relevante de la IA:** `src/common/config.py` (ronda 3) prometía en el docstring de la fusión "No muta las entradas", y `tests/test_config.py::test_herencia_no_comparte_objetos_con_la_base` decía verificarlo. La prueba llamaba dos veces a `load_config`, que **relee el disco en cada llamada**, así que los dos resultados eran independientes con cualquier implementación.
3. **Cómo sospechamos:** el revisor de calidad sustituyó la fusión por una versión que muta la base y vio que nada fallaba.
4. **Evidencia:** `evidencias/H-10_prueba_que_no_falla.py` → `.txt`: con `_fusionar` reemplazada por una versión defectuosa (muta la base y comparte objetos), **las 14 pruebas de herencia pasan** (14 passed).
5. **Corrección:** ronda 4 de T0.2 — la fusión se declara in-place sobre diccionarios recién leídos (documentado) y se elimina la prueba que no podía fallar.
6. **Lección:** una prueba sin la posibilidad de fallar es una afirmación disfrazada. Técnica útil para el resto del proyecto: **prueba de mutación** — romper a propósito el código y comprobar que alguna prueba se pone roja.

---

## Pistas por probar (aún no son hallazgos) — aportadas por el equipo Parte 2
- **Peajes liberados:** preguntar a una IA qué peajes hay entre Bilbao y Zaragoza, o entre Sevilla y Cádiz; comparar con el listado del Ministerio (AP-68, AP-7, AP-4, AP-2).
- **Consumo sin versión:** preguntar cuánto consume el Tucson híbrido y ver si aclara versión y país (215 CV en Bélgica vs 239 CV en España).
- **Fuente contradictoria:** una reseña del Corolla lo titula "híbrido enchufable" y en el texto lo describe como autorrecargable; ver si una IA repite el error.
- **Geocodificación:** pedir coordenadas de capitales con nombre bilingüe y verificar que el punto caiga en la ciudad correcta.
  Observado en T2.1 (7-oct-2026, Nominatim, no es IA): sin filtro de país "León" → Lyon y "Guadalajara" → Jalisco; con filtro, 10/47 primeros resultados son la provincia, Almería a 14 km del NGMEP. **Cifras reproducidas por el cazador** desde el crudo (`evidencias/T2.1_verificacion_fuentes.txt`: 7 `state_district` + 3 `province`; Almería 14,21 km). Falta pedírselo a una IA y comparar con `data/processed/cities.csv`; sin eso no es una alucinación de IA.
- **Spec §7.2 — Mérida:** ~~pista SIN PROMPT~~ → **promovida a candidato H-06** (9-oct-2026): el origen está en la asesoría de Claude al puente del 29-sep-2026 y el prompt literal ya está en `prompts/asesoria_puente_claude.md`.
- **Memoria NGMEP 2026 vs. CSV** (no es IA, es documentación oficial). **Verificado por el cazador** (`evidencias/T2.1_verificacion.txt` §1–2 y lectura de `Memoria_NGMEP_2026.pdf`): la Memoria declara 12 capitalidades + 1 entidad singular discrepantes (códigos terminados en 000001 y 000002), pero el CSV tiene 11 filas `DISCREPANTE_INE`, todas "Capital de municipio" con código terminado en 000001 y ninguna en 000002. Además: `SUPERFICIE_OFICIAL` (Memoria) frente a `SUPERFICIE` (CSV); en `COMJURIDIC`, la Memoria describe `PROVINCIA` como número, con una frase copiada de EATIMS ("…en la que se encuentra la EATIM"), pero el CSV trae un nombre (`Guipúzcoa`). Sin documentar en la Memoria: `COD_GEOGRAFICO` (COMJURIDIC) y también `COD_GEO` (MUNICIPIOS), y `ORIGENCOOR`/`ALTITUD`/`ORIGENALTITUD` en COMJURIDIC. Estas tres últimas omisiones no figuran en la caracterización (es incompleta, pero no es falsa). Útil como contraste en el blog.
- **`tests/test_cities.py` roto (Código, observado 8-oct-2026 ~13:04 UTC):** el subagente `curador-datos` (agent-a94a4cbb756be828d) reescribió el archivo vía Bash a las 13:03:35Z, y el literal `b"\x89PNG\r\n\x1a\n"` quedó con bytes de control reales (`\xc2\x89PNG\r\r\n\x1a\r\n`). Resultado: `SyntaxError` y `pytest tests/` no recoge nada (`tests/test_cities_ngmep.py` aislado: 7 passed). Evidencia: `evidencias/T2.1_test_png_literal.txt`. Es un error de escape del agente durante una edición en curso; falta el prompt literal de esa iteración (no está en `prompts/T2.1.md`) y comprobar si el propio agente lo detecta. **SIN PROMPT.**
- **Atribución "criterio de la Memoria"** (`caracterizacion_bloque1.md` §1 y `fuentes.md`): la cadena `PROVINCIAS.CAPITAL` → `MUNICIPIOS.COD_INE_CAPITAL` → `ENTIDADES` es una inferencia razonable a partir de las definiciones de los campos de la Memoria, pero la Memoria no describe ese procedimiento de unión. Es imprecisa pero inocua: la cadena funciona en las 47 capitales.
- **Documento de Camila (revisado 1-oct-2026):** afirmaciones verificables por contrastar — consumos 4,4–4,7 l/100 km del Corolla 140H por acabado; Octavia 4,9–5,3 y fase extra alta 5,0–5,5; Tucson HEV 215 CV (Bélgica) vs 239 CV (España); tarifas 2026 (+3,64 % a +4,68 %, SEITT +2 %, coinciden con prensa). Faltan sus prompts literales.

---

## Verificaciones que resultaron correctas (se documentan también)
| Fecha | Afirmación | Resultado | Evidencia |
|---|---|---|---|
| 29-sep-2026 | `scipy.optimize.differential_evolution` usa por defecto `strategy='best1bin'` y `polish=True` | Correcta | Documentación oficial de SciPy |
| 1-oct-2026 | El perfil de coche de OSRM declara `toll` como clase excluible | Correcta | `profiles/car.lua` en el repositorio de OSRM |
| 1-oct-2026 | Gradiente de Rosenbrock n-D del Spec (dos términos por coordenada interior) | Correcta | Diferencias centrales: error relativo 4.8e-11 (2D), 3.1e-10 (3D) |
| 1-oct-2026 | λ_max de la Hessiana de Rosenbrock 2D en x* ≈ 1001.6 | Correcta | Cálculo numérico (`H-03_rosenbrock_dominio.txt`) |
| 1-oct-2026 | Fin del peaje AP-68 el 11-nov-2026 (propuesta Parte 2) | Correcta en la fecha (falta el matiz foral, ver H-02) | Ministerio vía prensa; BOE pendiente |
| 8-oct-2026 | T2.1: `cities.csv` = NGMEP 202603 (`ENTIDADES.csv`, TIPO "Capital de municipio"): lat/lon a 6 decimales, `CODIGOINE` y `ORIGENCOOR` en `nota` | Correcta en 47/47 (muestra aleatoria de 8 con semilla 20261008 + 12 de la lista del Spec, y además todas las demás) | `evidencias/T2.1_verificacion.py` → `.txt` §4 |
| 8-oct-2026 | T2.1: las 47 son exactamente las capitales de `PROVINCIAS.csv` sin 07, 35, 38, 51 y 52 | Correcta (provincias 47/47). Nombres: `cities.capital` = `ENTIDADES.NOMBRE`; difiere de `PROVINCIAS.CAPITAL` en "Castelló de la Plana" (vs. "…/Castellón de la Plana") y "Oviedo/Uviéu" (vs. "Oviedo"), tal como declara la caracterización | `T2.1_verificacion.txt` §3 |
| 8-oct-2026 | T2.1: recuentos NGMEP (filas, columnas, nulos, TIPO, ORIGENCOOR, SUPRIMIDA 2, DISCREPANTE 11, CODIGOINE único, CRLF, cp1252 con 0x92 = `’` en "l’Estació") y SHA-256 de `fuentes.md` | Correctas todas | `T2.1_verificacion.txt` §0–2 |
| 8-oct-2026 | T2.1: 9 capitales difieren de IGR (códigos 01–06, 08, 09 y 47), máx. 2,350 km (Barcelona); Palma (07) también difiere; ninguna otra de 10–50; Ceuta y Melilla sin IGR; ORIGENCOOR 8 DA + 1 Coordinado_IGR | Correcta | `T2.1_verificacion.txt` §5 |
| 8-oct-2026 | T2.1: cifras de IGR `nuc` (32 consultas, 4 con datos, 50 registros, 34/14/1/1, NUCL 49/ENSI 1, 14 columnas sin nulos, fechas 2025-10-16..2025-12-05), Nominatim (52 consultas, 17/31/4), límites (53 unidades, 1 193 428 vértices, 13 188 834 bytes, timeStamp 03:36:02Z), INE (52 hojas, 8 132 municipios), rango lat/lon y par más cercano/lejano | Correctas | `evidencias/T2.1_verificacion_fuentes.py` → `.txt`; `T2.1_verificacion.txt` §6 |
| 8-oct-2026 | T2.1: Memoria NGMEP (31-mar-2026; fuentes REL/INE/boletines/Líneas Límite/IGR/BTN; ETRS89/REGCAN95; centroide "lo más centrado posible en el núcleo poblacional"; Anexo I "Entidad en la que está ubicado el Ayuntamiento") | Correctas (citas literales) | `Memoria_NGMEP_2026.pdf` págs. 3, 5, 7–10, 13, 14 |
| 8-oct-2026 | T2.1: URL de `fuentes.md` responden; CSW `dateStamp` 2026-01-19; identificador IGR-PO `20251216_…_v2024`; §3.8 "Se permiten combinaciones"; 26codmun.xlsx idéntico al crudo; IGR-PO usa el centroide de áreas residenciales cuando no hay coordenada de un organismo (respalda en parte "centro de la zona residencial") | Correctas (7/7 HTTP 200). "No hay versión NGMEP posterior a 202603": **no verificable** (la lista de ficheros del CNIG se carga dinámicamente; la página muestra "(2026)") | `evidencias/T2.1_urls_http.txt` |
