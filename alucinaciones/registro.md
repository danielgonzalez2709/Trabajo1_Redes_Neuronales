# 🎯 Registro de la Cacería de la alucinación

> Meta: ≥5 hallazgos **genuinos** en ≥3 categorías. **Nunca inventar.** Un candidato sin prompt literal o sin evidencia no cuenta.
> Evidencias en `alucinaciones/evidencias/`. Prompts literales en `alucinaciones/prompts/`.

## Cobertura actual
| Categoría | Candidatos | Confirmados |
|---|---|---|
| Matemáticas | 1 (H-03) | 1 (H-03, puente) |
| Código | 8 (H-07, H-08, H-09, H-10, H-11, H-20 débil, H-21, H-23) | 3 (H-07, H-08, H-10, puente) |
| Datos del mundo real | 9 (H-01, H-02, H-04, H-05, H-06, H-14, H-15, H-17, H-18) — H-13 descartado | 4 por el puente (H-04, H-05, H-14, H-17) + 1 confirmado por el cazador, pendiente del puente (H-18) |
| Bibliografía | 2 (H-19: error de cita confirmado, origen IA pendiente; H-22) | 1 (H-22, puente) |
| Conceptos | 1 (H-16) — H-12 descartado | 0 |

**Total confirmados por el puente: 9 en 4 categorías** (meta del enunciado: ≥5 en ≥3). Los 7 de la sección del blog: H-03, H-07, H-08, H-10, H-04, H-17, H-22.

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
   **Completado por el cazador (12-oct-2026, T2.4; `evidencias/T2.4_verificacion.txt` §6, crudos en `data/raw/peajes_2026-10-12/`):**
   - Respuesta del Gobierno al Congreso (23-feb-2026, `congreso_e_0102096_n_000.pdf`): la concesión dura "hasta el 10 de noviembre de 2026"; los tramos estatales "los que discurren por La Rioja y Aragón, pasarán a ser libres de peaje desde el día siguiente al final de la concesión, el resto de los tramos serán las administraciones titulares las que decidan". Por tanto, "11-nov" (Camila) es correcto para los tramos estatales, y "deja de cobrar el 10 de noviembre" (Claude) es impreciso: el 10 es el último día de cobro.
   - Bizkaia sí seguirá cobrando: nota oficial de la Diputación (22-jul-2026), ligeros 6,85 → 4,20 € desde el 11-nov. Álava: ninguna fuente oficial fija tarifa; el BOTHA núm. 83 (22-jul-2026) solo subvenciona el peaje de Avasa hasta el 10-nov. Navarra decide y no se encontró decisión oficial.
   - El BOE núm. 225 (RD 730/2026) regula bonificaciones a "Pesados 2" en Zambrana–Tudela; no dice nada del régimen de los ligeros tras el 10-nov (ver H-19).
   - Sigue faltando el prompt de Camila; sin él, la parte de su documento no cuenta.
5. **Corrección:** escenario base con fecha de corte 1-oct-2026 (AP-68 con peaje); escenario `post_ap68` con tramos de Álava y Bizkaia aún de pago.
6. **Lección:** para datos con vigencia, siempre preguntar "¿desde cuándo, hasta cuándo y en qué tramos?".

### H-03 — Paso de GD "justificado" con la curvatura en el mínimo (garantía solo local)
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: candidato — prompt literal disponible (9-oct-2026)
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
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: confirmado por el cazador (8-oct-2026, evidencia independiente desde el crudo) — pendiente de revisión del puente
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
- **Estado:** **confirmado por el puente** (Daniel, aprobado en el PR #1, 9-oct-2026). Antes: confirmado por el cazador (8-oct-2026) — pendiente de revisión del puente. Es la **otra mitad** de la frase que originó H-04; el equipo puede decidir fusionarlos, pero se trata de una afirmación distinta, con evidencia distinta. **Corregido** el 8-oct-2026 en `data/caracterizacion_bloque1.md` §4 (cifras 8 078/8 132 y 47/47, sin atribuir causa).
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
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: candidato (prompt literal disponible; evidencia reproducible)
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
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: candidato (prompt literal disponible; evidencia reproducible; severidad baja: no afecta al experimento, que usa enteros)
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
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: candidato (prompt literal disponible; evidencia reproducible por prueba de mutación)
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `implementador`, T0.2 ronda 3) · **Fecha:** 9-oct-2026 · **Quién lo cazó:** subagente `revisor-calidad`; confirmado por el orquestador con una prueba de mutación
1. **Prompt (literal):** `prompts/T0.2.md`, ronda 3, punto 2 ("fusiona en profundidad … Pruebas: herencia simple y encadenada, la hija gana, listas reemplazadas, ciclo → error…").
2. **Respuesta relevante de la IA:** `src/common/config.py` (ronda 3) prometía en el docstring de la fusión "No muta las entradas", y `tests/test_config.py::test_herencia_no_comparte_objetos_con_la_base` decía verificarlo. La prueba llamaba dos veces a `load_config`, que **relee el disco en cada llamada**, así que los dos resultados eran independientes con cualquier implementación.
3. **Cómo sospechamos:** el revisor de calidad sustituyó la fusión por una versión que muta la base y vio que nada fallaba.
4. **Evidencia:** `evidencias/H-10_prueba_que_no_falla.py` → `.txt`: con `_fusionar` reemplazada por una versión defectuosa (muta la base y comparte objetos), **las 14 pruebas de herencia pasan** (14 passed).
5. **Corrección:** ronda 4 de T0.2 — la fusión se declara in-place sobre diccionarios recién leídos (documentado) y se elimina la prueba que no podía fallar.
6. **Lección:** una prueba sin la posibilidad de fallar es una afirmación disfrazada. Técnica útil para el resto del proyecto: **prueba de mutación** — romper a propósito el código y comprobar que alguna prueba se pone roja.

### H-11 — Números de campo del `HeaderBlock` de OSM PBF equivocados (18/19/20 en vez de 32/33/34)
- **Estado:** candidato — falta cita textual del código erróneo y verificación del cazador
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.2) · **Fecha:** 10/11-oct-2026 · **Quién lo cazó:** el propio subagente (autodetectado: la fecha no salía) y lo reportó al orquestador
1. **Prompt (literal):** `alucinaciones/prompts/T2.2.md`, "Qué hacer", paso 2: "Registrar la fecha de los datos del extracto tal como la publica Geofabrik".
2. **Respuesta relevante de la IA:** informe final del subagente: "en mi lector de la cabecera del PBF puse números de campo equivocados (18/19/20 en lugar de 32/33/34) y la fecha no salía". La versión corregida está en `scripts/osrm/cabecera_pbf.py`. PENDIENTE: extraer de la transcripción la versión errónea literal.
3. **Cómo sospechamos:** el lector no devolvía `osmosis_replication_timestamp`.
4. **Evidencia:** PENDIENTE (cazador): contrastar con `osmformat.proto` de OSM-binary (https://github.com/openstreetmap/OSM-binary/blob/master/osmpbf/osmformat.proto) y con la fecha 2026-10-01T20:22:06Z que dan `state.txt` de Geofabrik y `osrm-extract` (`data/raw/osrm_2026-10-10/`).
5. **Corrección:** campos 32/33/34 en `scripts/osrm/cabecera_pbf.py`; la fecha coincide con las otras dos fuentes.
6. **Lección:** números de campo de un `.proto` se copian de la definición, no de memoria; validar el lector contra una segunda fuente de la misma fecha.

### H-12 — "El máximo WLTP de 4,8 es la configuración más equipada" (explicación plausible sin fuente que acabó en el Spec)
- **Estado:** **descartado por el puente** (Daniel, 12-oct-2026, según la propuesta del equipo Parte 2): se documenta en Verificaciones como afirmación imprecisa. Antes: candidato — verificado por el cazador (11-oct); **propuesta: descartar** (pasar a "Verificaciones" como imprecisa). Decide el puente.
- **Categoría:** Conceptos (aplicación sin verificar de un concepto de homologación a un caso concreto)
- **Herramienta y modelo:** Claude Opus 5.5 (orquestador, sesión principal) · **Fecha:** 11-oct-2026 · **Quién lo cazó:** subagente `curador-datos` (T2.7, ronda 2), al contrastarlo con los crudos
1. **Prompt (literal):** `alucinaciones/prompts/asesoria_T2.7_claude.md` (pregunta de Jose Miguel sobre la fase extra alta y la rúbrica).
2. **Respuesta relevante de la IA:** "Es el WLTP del **mismo** ciclo con la versión más equipada (llantas más grandes, extras)". El orquestador la copió en el Spec v1.7 §7.2 Bloque 5: "es el combinado de la configuración más equipada".
3. **Cómo sospechamos:** el curador revisó la configuración completa del configurador y no encontró nada que pudiera "equipar más" el coche.
4. **Evidencia:** `data/raw/vehiculo_2026-10-11/texus_corolla_sedan_GetFullConfiguration.json`. El Style Plus MY27 tiene 0 opciones internas, 0 externas, 0 packs y una única llanta de 17". Toyota publica `FUELCOMBINEDWLTPMAX` = 4,8 sin explicar su origen (`…GetTechnicalSpecifications.json`).
   **Completado por el cazador (11-oct-2026, `evidencias/T2.7_verificacion.py` → `.txt` §1–2 y `evidencias/H-12_reglamento_2017_1151_extractos.txt`):**
   - Fuente primaria: Reglamento (UE) 2017/1151, anexo XXI (texto original del DO L 175 de 7-7-2017, vía legislation.gov.uk; EUR-Lex no respondió). Subanexo 4, 4.2.1.2: "Test vehicle H shall be the vehicle producing the higher, and preferably highest, cycle energy demand of that selection, test vehicle L the one producing the lower, and preferably lowest". Según 4.2.1.1, esa demanda depende de la "mass, aerodynamic drag and tyre rolling resistance", y para las llantas la guía es "a) the largest width, b) the largest diameter, and c) the most open structure design". Subanexo 7, 3.2.3.2: cada vehículo individual recibe un valor interpolado entre L y H.
   - Lo que confirma: la idea general de la IA ("versión más equipada: llantas más grandes, extras") coincide con la definición del vehículo H. Además, "mismo ciclo" es correcto: Toyota lo llama "Consumo combinado WLTP - Max" (no es una fase).
   - Lo que no confirma: Toyota no dice que su "Max" sea el vehículo H, y en Toyota España no hay ninguna configuración del Style Plus MY27 más equipada (un solo acabado y una sola motorización; 0 opciones y 0 packs). Matiz sobre el texto anterior: el configurador sí ofrece 1 llanta como accesorio (`AvailableAccessoryWheels` = 1) y 42 accesorios. Son accesorios del concesionario, no opciones homologadas (anexo XXI, 3.2.9).
   - Indicios, sin demostrar: Toyota publica un peso en orden de marcha de 1355–1415 kg (`KERBWGHT`) y llama "medio" al CO₂ de 105 ("CO2 combinado WLTP – medio"). El catálogo de 2023 da para la gama 4,4–4,8 l/100 km y 99–109 g/km, el mismo máximo actual (4,8 / 109). Encaja con un rango L–H de la familia, pero la fuente no lo dice.
   - **Propuesta del cazador: descartar como alucinación.** El concepto está respaldado por la normativa, y aplicarlo a este caso no se puede refutar. Se propone pasarlo a "Verificaciones" como *imprecisa / no verificable en el caso concreto* (decide el puente). La corrección del Spec ("su origen no está documentado […] no se usa") sigue siendo correcta.
5. **Corrección:** Spec §7.2 Bloque 5, redactado de nuevo tras la verificación: es el ciclo combinado, no la fase de autopista, y no se usa. En el crudo lleva `Type: "vehicleHigh"`, que es el "vehículo H" del Reglamento (UE) 2017/1151, y Toyota no documenta qué configuración concreta es. El 4,8 no entra en ningún cálculo.
6. **Lección:** una explicación genérica ("el máximo corresponde a la versión más equipada") se comprueba contra los datos del caso antes de escribirla en el Spec. Aquí bastaba con mirar las opciones del configurador, que ya estaban descargadas.

### H-13 — "No existe ficha oficial de Toyota España del Corolla Sedán 140H" (resumen del buscador web)
- **Estado:** **descartado por el puente** (Daniel, 12-oct-2026, según la propuesta del equipo Parte 2): error del buscador web, no de la IA (ver H-15). Antes: candidato — verificado por el cazador (11-oct), con la cita literal recuperada; **propuesta: descartar** como error del buscador (ver H-15). Decide el puente.
- **Categoría:** Datos
- **Herramienta y modelo:** herramienta de búsqueda web usada por el subagente `curador-datos` (Claude Opus 5.5) · **Fecha:** 11-oct-2026 · **Quién lo cazó:** el propio subagente
1. **Prompt (literal):** consulta de búsqueda "Toyota España Corolla Sedán 140H ficha técnica consumo WLTP" (encargo en `alucinaciones/prompts/T2.7.md`, ronda 1).
2. **Respuesta relevante de la IA:** según el informe del subagente, el resumen automático afirmó tres cosas: que no existía ficha oficial de Toyota España, que el ECO daba "4,6, igual que el Style Plus", y un valor de 4,70 que mezclaba el Touring Sports. **Cita textual recuperada por el cazador** (`evidencias/H-13_H-14_transcripcion_extractos.txt`; transcripción `agent-ad02ff449667aa29b.jsonl`, líneas 29 y 31, 2026-10-12T01:47:59Z/01:48:05Z; consulta literal confirmada):
   - "No encontré la ficha oficial de Toyota España para el Sedán 140H. Las cifras disponibles proceden de sitios de terceros y no coinciden del todo."
   - "**KM77, Sedán 140H Eco (2022):** aparecen los mismos datos de consumo combinado (4,6 l/100 km) y de CO₂ (104 g/km) que en la versión Style Plus."
   - "**Motor.es, 140H Style Touring Sport:** da 4,70 l/100 km y 106 g/km de CO₂. Esta versión aparece en un listado que no especifica carrocería, así que no es seguro que sea el Sedán."
   - Cierre: "conviene confirmarlo en la web de Toyota España o en la ficha de homologación antes de darlo por definitivo."
3. **Cómo sospechamos:** el configurador de toyota.es sí publica la ficha.
4. **Evidencia:** `data/raw/vehiculo_2026-10-11/texus_corolla_sedan_GetTechnicalSpecifications.json` y `toyota_es_corolla_sedan_build.html` (Style Plus, `FUELCOMBINEDWLTP` = 4,6). Para el ECO, Toyota da 4,4–4,6 / 4,4 / 4,5 (`toyota_es_promo_corolla_sedan_eco_kinto.html`, `toyota_es_empresas_corolla_sedan_eco.html`).
   **Contraste del cazador con la cita literal (11-oct-2026):**
   - (a) La herramienta dijo "No encontré", no "no existe". Es cierto para esa búsqueda: entre los 9 resultados no hay ninguna URL de toyota.es. Además, recomendó confirmarlo en la web de Toyota España.
   - (b) El 4,6 / 104 del ECO lo atribuye a km77, y km77 lo dice así: `km77_corolla_sedan_140h_eco.html`, "Consumo WLTP Combinado 4,6 l/100 km Emisiones de CO₂ WLTP 104 gr/km" (`evidencias/T2.7_verificacion.txt` §2b). No dice que sea el dato de Toyota.
   - (c) El 4,70 del Touring Sports no se mezcla con el Sedán: la herramienta avisa de que "no es seguro que sea el Sedán". La frase "un listado que no especifica carrocería" es imprecisa, porque el nombre ya dice "Touring Sport".
   - Conclusión: las tres afirmaciones que el registro atribuye al buscador no están en su respuesta. Salen del **informe del subagente `curador-datos`** (línea 308, 2026-10-12T02:01:17Z): "afirmó que no existía ficha oficial de Toyota España. También dio el ECO como "4,6, igual que el Style Plus" y mezcló un Touring Sports de 4,70". Esa frase convierte "no encontré" en "no existía", quita la atribución a km77 y omite el aviso sobre el Touring Sports.
   - **Propuesta del cazador: descartar H-13 como alucinación del buscador.** Se propone abrir un candidato nuevo: "paráfrasis infiel de la salida de una herramienta" por el `curador-datos` (Claude Opus 5.5). El prompt literal es `prompts/T2.7.md`, ronda 1, y la evidencia es el mismo archivo de extractos. La categoría la decide el puente: Datos, o Bibliografía si se trata como cita falsa de una fuente.
5. **Corrección:** la ficha se tomó directamente del configurador oficial.
6. **Lección:** el resumen de un buscador no es una fuente. Hay que ir a la página primaria y guardar su copia.

### H-14 — "Ni Toyota España ni km77 publican la fase WLTP extra alta" (generalización a partir de las fuentes consultadas)
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026, según la propuesta del equipo Parte 2; gravedad baja). Antes: candidato — verificado por el cazador (11-oct); **propuesta: confirmar** (gravedad baja). Decide el puente.
- **Categoría:** Datos
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.7 ronda 1; el orquestador lo copió en el Spec v1.7) · **Fecha:** 11-oct-2026 · **Quién lo cazó:** el mismo subagente, en la ronda 3, al leer el catálogo
1. **Prompt (literal):** `alucinaciones/prompts/T2.7.md`, ronda 1 ("usar también el consumo de la fase WLTP "extra alta" (autopista), si la ficha la publica").
2. **Respuesta relevante de la IA:** informe de la ronda 1: "**Fase extra alta:** no la publican ni Toyota España ni km77". El orquestador escribió en el Spec v1.7: "Ni Toyota España ni km77 la publican".
3. **Cómo sospechamos:** el catálogo oficial de Toyota España que descargó Jose Miguel la trae.
4. **Evidencia:** `data/raw/vehiculo_2026-10-11/14764_CORS_48_ES_WEB_S.pdf`, pág. PDF 17: "Ritmo extra alto (l/100km) 5,6-6,2" (SHA-256 a59be953…2463ad).
   **Completado por el cazador (11-oct-2026):**
   - Cita literal del informe de la ronda 1 (transcripción `agent-ad02ff449667aa29b.jsonl`, línea 308, 2026-10-12T02:01:17Z; `evidencias/H-13_H-14_transcripcion_extractos.txt`): "- **Fase extra alta:** no la publican ni Toyota España ni km77, así que no he añadido `consumo_wltp_extra_alta_l100`."
   - Lo que es cierto: ninguna de las 14 fuentes HTML/JSON de Toyota y km77 guardadas menciona la fase extra alta (0 coincidencias de "extra alt"/"extra high"; `evidencias/T2.7_verificacion.txt` §3). Tampoco la menciona la captura de Wayback del 2-oct-2026.
   - Lo que es falso: el catálogo "Corolla Sedan" de Toyota España ("© 2023 Toyota España S.L.U.", "09/23/CORSEDAN/ES/0000", pág. PDF 25) trae "Ritmo extra alto (l/100km) 5,6-6,2" y "Ritmo extra alto (g/km) 126-139" (pág. PDF 17; §4).
   - Límites: el catálogo es de 2023 y da rangos de la gama de entonces. Además, no está documentada la URL desde la que Toyota España lo sirve hoy: es un `TODO` de `fuentes.md`, y la página de manuales guardada no lo enlaza. Por eso lo refutado es "Toyota España no la publica"; "la ficha actual no la publica" es correcto.
   - **Propuesta del cazador: confirmar** (gravedad baja). Es una generalización de "no está en las fuentes que revisé" a "Toyota España no la publica", refutada por un documento oficial de Toyota España. Antes de cerrarlo, conviene documentar la URL del catálogo.
5. **Corrección:** Spec §7.2 Bloque 5: "La ficha actual de Toyota España (MY27) y km77 no la publican. El catálogo […] 09/2023 […] sí la da".
   - **URL del catálogo ya documentada** (11-oct, después de la verificación): https://www.toyota.es/content/dam/toyota/nmsc/spain/cross-model/new-cars/catalogos-precios/pdf/14764_CORS_48_ES_WEB_S.pdf. Comprobada por el orquestador: HTTP 200, mismo SHA-256 y `Last-Modified` 05-oct-2023. Ver `data/fuentes.md`, Bloque 5.
6. **Lección:** "no lo publican" solo vale para las fuentes revisadas. Se escribe "no aparece en X e Y", nunca "no existe".

### H-15 — Paráfrasis infiel de la salida de una herramienta ("no encontré" → "no existía")
- **Estado:** candidato — propuesto por el cazador al verificar H-13; falta que el puente fije la categoría · **Categoría fijada por el puente: Datos** (12-oct-2026, según la propuesta del cazador).
- **Categoría:** Datos (fijada por el puente el 12-oct-2026)
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.7 ronda 1) · **Fecha:** 11-oct-2026 · **Quién lo cazó:** `cazador-alucinaciones`, al recuperar la cita literal de H-13
1. **Prompt (literal):** `alucinaciones/prompts/T2.7.md`, ronda 1.
2. **Respuesta relevante de la IA:** informe final del curador (transcripción `agent-ad02ff449667aa29b.jsonl`, línea 308, 2026-10-12T02:01:17Z): el resumen automático "afirmó que no existía ficha oficial de Toyota España. También dio el ECO como "4,6, igual que el Style Plus" y mezcló un Touring Sports de 4,70".
3. **Cómo sospechamos:** al recuperar la salida literal del buscador para H-13, no coincidía con lo que el curador decía que había dicho.
4. **Evidencia:** `alucinaciones/evidencias/H-13_H-14_transcripcion_extractos.txt`. El buscador dijo:
   - "No encontré la ficha oficial…", no "no existe";
   - atribuyó el 4,6 / 104 del ECO a km77, que lo dice así;
   - avisó de que el Touring Sports "no es seguro que sea el Sedán".
5. **Corrección:** H-13 se reescribe con la cita literal; la ficha oficial se tomó del configurador.
6. **Lección:** cuando un agente resume lo que dijo otra herramienta, se cita literal y se enlaza la transcripción; la paráfrasis puede convertir una ausencia de resultados en una afirmación de inexistencia.

### H-16 — "`exclude=toll` no evita las vías de peaje" (causa mal atribuida por un diagnóstico; el orquestador la copió en el Spec v1.8)
- **Estado:** candidato — falta la verificación del cazador
- **Categoría:** Conceptos (conclusión causal sobre el comportamiento de una herramienta; el puente puede preferir Código)
- **Herramienta y modelo:** Claude Opus 5.5. Subagente `curador-datos` (diagnóstico) y orquestador, que lo escribió en el Spec v1.8 como hecho verificado · **Fecha:** 11/12-oct-2026 · **Quién lo cazó:** otro `curador-datos`, en la ronda 2 de T2.3
1. **Prompt (literal):** `alucinaciones/prompts/T2.3-diagnostico-toll.md` (pregunta 2: "¿Por qué `exclude=toll` no las evita?").
2. **Respuesta relevante de la IA:**
   - Diagnóstico: "The cause is **(B), a problem in OSRM itself**: `exclude=toll` does not reliably avoid those roads". Añadía: "With one thread the result is stable but wrong […] 26 `sin_peaje` routes have the `toll` class".
   - Spec v1.8, primera redacción: "OSRM v26.10.0 **no garantiza** que evite todas las vías con la clase `toll`. Verificado el 11-oct-2026".
3. **Cómo sospechamos:** al repetir la corrida con `--threads 1`, la respuesta cambiaba según la primera consulta después de arrancar el servidor.
4. **Evidencia:** `alucinaciones/evidencias/T2.3_historial_osrm/` (README).
   - En el mismo proceso, el orden inverso de consultas cambia 50 de 2202 rutas.
   - Con un proceso por alternativa hay 0 rutas `sin_peaje` con `toll` en los dos órdenes.
   - El "stable but wrong" del diagnóstico era el efecto de un historial concreto, no una limitación de `exclude`.
   - El mecanismo interno no está confirmado.
5. **Corrección:** Spec §7.2 Bloque 2 (v1.8, corregido el 12-oct): "la respuesta depende del **historial de consultas** del proceso; con **un proceso por alternativa**, 0 rutas `sin_peaje` tienen `toll`".
6. **Lección:** antes de atribuir un fallo a una función de la herramienta, se varían las condiciones del experimento (orden, proceso, estado inicial). Un resultado estable no es lo mismo que un resultado correcto, ni que una causa demostrada.

### H-17 — Tarifas de la AP-9 transcritas una fila más abajo (Caldas–Curro 2,85 en vez de 1,65)
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: confirmado por el cazador (12-oct-2026, evidencia literal y fuente oficial) — pendiente de revisión del puente. Ya corregido: la tabla final no contiene esos importes.
- **Categoría:** Datos
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.4) · **Fecha:** 12-oct-2026 · **Quién lo cazó:** el `curador-datos` que rehízo la tabla; confirmado por el cazador
1. **Prompt (literal):** `alucinaciones/prompts/T2.4.md`, "Ronda 2 — Prompt literal" (regla 1: "Si una tarifa no aparece en un crudo oficial, pon `TODO(dato-faltante)` … NUNCA la deduzcas"). Nota: el orquestador lo llamó "primera ronda"; fue el agente que recibió el prompt de la ronda 2.
2. **Respuesta relevante de la IA (literal):** `scripts/construir_peajes.py` escrito a las 2026-10-12T10:38:46Z (`evidencias/T2.4_extractos.txt`, A1): `("Caldas de Reis", "Curro", 2.85), ("Caldas de Reis", "Pontevedra", 1.80), ("Curro", "Pontevedra", 1.45), ("Pontevedra", "Vilaboa", 3.65), ("Pontevedra", "Morrazo", 5.05), ("Pontevedra", "Vigo / Puxeiros", None)`.
3. **Cómo sospechamos:** el curador siguiente releyó el PDF y vio que los importes no cuadraban (`T2.4_extractos.txt`, A2).
4. **Evidencia:** `evidencias/T2.4_verificacion.py` → `.txt` §3–4.
   - PDF del Ministerio (`mitma_tarifas_2026_ap-9.pdf`, `pdftotext -raw`): Caldas–Curro 1,65; Caldas–Pontevedra 2,85; Curro–Pontevedra 1,80; Pontevedra–Vilaboa 1,45; Pontevedra–Morrazo 3,65. La tabla de recurrencia del mismo PDF (50 %) da 0,82 / 1,42 / 0,90 / 0,72 / 1,82, que confirma la alineación.
   - Calculadora oficial de Audasa (consultada el 12-oct-2026, `evidencias/T2.4_audasa_calculadora_2026-10-12.json`): Caldas→Curro 1,65; Curro→Pontevedra 1,80; Caldas→Pontevedra 2,85.
   - Cada importe se desplazó una fila hacia arriba a partir de Caldas de Reis, y el último quedó en `None`. En la extracción `-layout`, los nombres y los importes de esa página aparecen en líneas distintas; el agente los emparejó sin comprobarlos.
5. **Corrección:** el curador siguiente rehízo la tabla; las filas AP-9 finales usan A Coruña/A Barcala–Santiago 8,80 y Santiago–Pontevedra 7,55, verificadas por el cazador.
6. **Lección:** en tablas extraídas de PDF, comprobar la alineación con una segunda columna o tabla relacionada (aquí, la de descuento del 50 %) o con `pdftotext -raw`. Un desplazamiento de una fila produce importes plausibles y es invisible a simple vista.

### H-18 — "El Catálogo excluye los tramos transferidos (AP-68 vasco y navarro)": el tramo navarro sí está
- **Estado:** confirmado por el cazador (12-oct-2026) — pendiente de revisión del puente. Ya corregido en `data/fuentes.md`. Gravedad baja: los km de AP68-06/07 ya incluían el tramo navarro.
- **Categoría:** Datos (afirmación falsa sobre el contenido de una fuente; el puente puede preferir Bibliografía)
- **Herramienta y modelo:** Claude Opus 5.5 (subagente `curador-datos`, T2.4) · **Fecha:** 12-oct-2026 · **Quién lo cazó:** `revisor-spec`; confirmado por el cazador con un lector propio del Catálogo
1. **Prompt (literal):** `alucinaciones/prompts/T2.4.md`, prompt original (primer bloque). Pide "Cada tarifa, km y vigencia sale de una página/PDF oficial que hayas leído".
2. **Respuesta relevante de la IA (literal):** escrito en `data/fuentes.md` a las 2026-10-12T10:50:45Z (`evidencias/T2.4_extractos.txt`, B1): "El Catálogo excluye los tramos transferidos (AP-68 vasco y navarro) y las vías forales/autonómicas."
3. **Cómo sospechamos:** `revisor-spec` vio que las filas AP68-06/07 sumaban km de Navarra sacados del mismo Catálogo (B2). El curador lo reconoció (B3).
4. **Evidencia:** `evidencias/T2.4_verificacion.txt` §5, con un lector `.dbf` independiente del script del curador: el Catálogo RCE 2025 (`260306-catalogorce2025.zip`) tiene 6 tramos de la AP-68 en Navarra (39,66 km, p.k. 162,53–166,48 y 201,85–237,0), todos "Autopista de peaje", y ninguno en Bizkaia ni Álava (empieza en el p.k. 77,597, L.P. Álava-Burgos). La mitad vasca de la frase es cierta. La navarra es una inferencia ("transferido por el RD 1230/2025 → fuera del Catálogo") que no se comprobó contra el zip, aunque el zip ya estaba descargado.
5. **Corrección:** `fuentes.md`: "excluye el tramo vasco de la AP-68 […] pero **sí incluye el tramo navarro**".
6. **Lección:** una deducción legal ("si se transfirió, no está en el Catálogo estatal") no sustituye a mirar el dato. El Catálogo 2025 (marzo de 2026) aún no refleja un traspaso de diciembre de 2025.

### H-19 — BOE núm. 225 (RD 730/2026) citado como fuente para la rebaja Logroño–Bilbao 19,60 → 6,65 € (no la contiene)
- **Estado:** candidato — **el error de cita está confirmado; el origen IA, no**. No cuenta hasta resolver el origen. Atenuante: el propio Spec lo marcó "[VERIFICAR]".
- **Categoría:** Bibliografía
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente; Spec v1.0, commit `2cd005b`) · **Fecha:** 1-oct-2026 · **Quién lo cazó:** subagente `curador-datos` (T2.4, al leer el BOE); confirmado por el cazador
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt C** (1-oct-2026). Falta su entrada, `message.txt` (propuesta del equipo Parte 2), para descartar que la cita viniera de ahí. **Pedírsela a Daniel o a Camila.**
2. **Respuesta relevante de la IA (literal, Spec v1.0 §7.1, igual en la versión vigente):** "Fuente de prensa reportó que Logroño–Bilbao pasaría de 19,60 € a 6,65 € [VERIFICAR con fuente oficial y la resolución del BOE núm. 225 de 11-sep-2026]". En §15: "BOE núm. 225, 11-sep-2026, disposición 19039 (Ministerio de Transportes) [VERIFICAR contenido]".
3. **Cómo sospechamos:** el curador de T2.4 descargó el BOE para fijar las vigencias y no encontró nada sobre ligeros.
4. **Evidencia:** `evidencias/T2.4_verificacion.txt` §6 (crudo `data/raw/peajes_2026-10-12/boe_A-2026-19039.pdf`, SHA-256 en su `MANIFEST.txt`):
   - Título: "Real Decreto 730/2026 … para la aplicación de medidas de bonificación de peajes a determinados vehículos pesados en el tramo Zambrana-Tudela".
   - Ni "19,60", ni "6,65", ni "ligeros", ni "turismos" aparecen en el texto. Solo menciona el fin de la concesión ("el 10 de noviembre de 2026").
   - Lo que es verdad: 19,60 € es la tarifa oficial vigente Bilbao–Logroño (PDF del Ministerio, "BILBAO LOGROÑO 19,60"). El 6,65 no aparece en ninguna fuente oficial descargada. Las dos notas de prensa citadas en el Spec §15 (Motorpasión, 5-ene-2026; Xataka, 7-ago-2026, consultadas el 12-oct) tampoco mencionan el BOE ni las cifras 19,60 / 6,65.
   - El mismo párrafo atribuye al Ministerio que "La Rioja, Navarra y Aragón quedan libres". La respuesta oficial del Gobierno al Congreso (23-feb-2026) solo libera La Rioja y Aragón; Navarra "decide". Xataka sí dice que en Navarra "los turismos viajarán gratis", pero es prensa, no el Ministerio. No se cuenta como hallazgo aparte (no está refutado).
5. **Corrección (propuesta; el cazador no edita el Spec):** en §7.1, citar la respuesta al Congreso para el régimen posterior, retirar el BOE núm. 225 como fuente de la rebaja y marcar el 6,65 como dato de prensa sin fuente oficial.
6. **Lección:** una referencia "[VERIFICAR contenido]" que se cita para respaldar una cifra concreta ya es una afirmación sobre la fuente. Si no se leyó, se escribe "pendiente de localizar la fuente oficial", sin número de BOE.

### H-20 — "56 pruebas en verde" de T2.5 no detectan anclas interiores con km erróneo (mutante superviviente)
- **Estado:** candidato **débil** (deficiencia de pruebas, no una afirmación falsa sobre el mundo; mismo tipo que H-10). Cuenta solo si el equipo lo acepta como Código.
- **Categoría:** Código
- **Herramienta y modelo:** Claude Code → subagente `curador-datos` (claude-sonnet-5-5), T2.5 · **Fecha:** 12-oct-2026 · **Quién lo cazó:** cazador-alucinaciones (prueba de mutación)
1. **Prompt (literal):** `prompts/T2.5.md` ("Pruebas primero, incluyendo los 5 pares y casos límite"; el informe del curador declara 56 pruebas verdes entre `test_asignar_peajes.py` y `test_peajes_anclas.py`).
2. **Respuesta relevante de la IA:** `tests/test_peajes_anclas.py` valida que las anclas de extremo de tramo suman los km de la tabla y que los centroides se recalculan; para las anclas intermedias (14 con `origen_km` ≠ extremo de tramo) no hay prueba del km. `docs/validacion_peajes_T2.5.md` §6 las llama "decisión del curador, por verificar".
3. **Cómo sospechamos:** el propio documento admite que esas anclas no están verificadas; se probó si las pruebas lo notarían.
4. **Evidencia:** `evidencias/T2.5_cazador/T2.5_mutacion.py` → `T2.5_mutacion.txt` (copia fuera del repo). Mutantes de código (M1 recorrido solo del primer paso, M2 `km_peaje` con tramos gratuitos, M3 sin prorrata): **muertos** (4, 2 y 7 pruebas fallan). M4 (intercambiar el km de San Rafael y Villacastín en la AP-6): muerto por una sola prueba. **M5 sobrevive**: dos anclas intermedias de la AP-68 con km +36 y +40 (139,14 → 175,0 y 219,74 → 260,0), salidas regeneradas: **56 pasan**, 16 rutas cambian hasta 5,55 € y el script emite 16 avisos `km_incoherente` que ninguna prueba exige que sean 0 (los datos reales solo tienen 38 avisos `ref_sin_cadena`).
5. **Corrección (propuesta; el cazador no edita código):** una prueba sobre los datos reales que exija `avisos_por_motivo == {"ref_sin_cadena": 38}` (sin `km_incoherente`) mataría a M5.
6. **Lección:** la prueba de regresión que compara `rutas.csv` con lo que recalcula el script solo protege contra cambios no regenerados; el error de un dato de entrada (ancla) pasa si el autor regenera. Hace falta una prueba contra una verdad externa o contra el diagnóstico del propio script.

### H-21 — La prueba del par (0, 44) se llamaba "Logroño", pero la ciudad 0 es Vitoria-Gasteiz
- **Estado:** candidato (el propio subagente admitió que inventó el nombre; falta la revisión del puente)
- **Categoría:** Código (propuesta de `revisor-spec`; el puente decide si va en Datos, porque es un nombre de ciudad real)
- **Herramienta y modelo:** Claude Code → subagente `implementador`, T3.1 (sesión principal en claude-opus-5-5; el modelo del subagente lo fija su definición en `.claude/agents/`) · **Fecha:** 12-oct-2026 · **Quién lo cazó:** `revisor-spec` (hallazgo H4 de su ronda 1)
1. **Prompt (literal):** `prompts/T3.1.md` (ronda 1: "Par calculado a mano: toma un par real de `rutas.csv`…"). El prompt no nombra ninguna ciudad.
2. **Respuesta relevante de la IA:** en `tests/test_cost.py` la prueba del par (0, 44) se llamaba `test_par_a_mano_logrono_44_…`. Al preguntarle por el origen del nombre (ronda 2), el subagente respondió: "Lo inventé. En la ronda 1 no leí `cities.csv`: vi `AP-68` en `vias_peaje` del par (0, 44) y supuse que la ciudad 0 era Logroño."
3. **Cómo sospechamos:** `revisor-spec` contrastó el nombre de la prueba con `data/processed/cities.csv`.
4. **Evidencia:** `data/processed/cities.csv`: id 0 = Vitoria-Gasteiz, id 44 = Bilbao, id 24 = Logroño. Las cifras de la prueba eran correctas (reproducidas por `verificador-matematico` con aritmética exacta); solo el nombre era falso.
5. **Corrección:** ronda 2 del implementador: la prueba pasó a `test_par_a_mano_vitoria_bilbao_cambia_de_alternativa_entre_w_bajo_y_w_alto`, con los nombres comprobados contra `cities.csv`.
6. **Lección:** un nombre de prueba también es una afirmación sobre los datos. La IA dedujo la ciudad a partir de la autopista (la AP-68 pasa por Logroño) en vez de leer el archivo; una prueba que pasa no valida su propio nombre ni sus comentarios.

### H-22 — Dantzig, Fulkerson y Johnson (1954) citado en "Operations Research" (en 1954 la revista tenía otro nombre)
- **Estado:** **confirmado por el puente** (Daniel, 12-oct-2026; incluido en la sección Cacería del blog). Antes: candidato (prompt literal disponible; evidencia reproducible contra Crossref; severidad baja, pero muy sutil)
- **Categoría:** Bibliografía
- **Herramienta y modelo:** Claude Opus 5.5 (orquestador, T0.7) · **Fecha:** 12-oct-2026 · **Quién lo cazó:** el orquestador, al verificar contra Crossref la lista que había escrito de memoria
1. **Prompt (literal):** "Avancemos con el esqueleto del blog" (Daniel, 12-oct-2026, sesión de asesoría del puente; se añade a `prompts/asesoria_puente_claude.md`).
2. **Respuesta relevante de la IA:** en `evidencias/H-bib_verificacion_doi.py`, la lista `REFERENCIAS_DE_MEMORIA` (escrita ANTES de consultar nada) atribuye `10.1287/opre.2.4.393` a la revista "Operations Research".
3. **Cómo sospechamos:** regla del proyecto: ninguna referencia se escribe de memoria; todas se contrastan con el registro oficial.
4. **Evidencia:** `evidencias/H-bib_verificacion_doi.txt`: Crossref registra `container-title` = "Journal of the Operations Research Society of America" (vol. 2, n.º 4, pp. 393–410, nov-1954). El prefijo del DOI (`opre`) usa el nombre actual de la revista, lo que hace fácil la confusión.
5. **Corrección:** `blog/references.bib` usa el nombre registrado en 1954.
6. **Lección:** APA cita la revista con el nombre que tenía al publicarse el artículo; el DOI no sirve para deducirlo. Las otras 10 referencias recordadas coincidieron en autor y año (también se documenta: ver la tabla de verificaciones).

### H-23 — Encabezados YAML de dos agentes inválidos desde su creación (`:` sin comillas): `revisor-spec` y `revisor-calidad` no cargaban
- **Estado:** candidato (prompt literal disponible; evidencia reproducible)
- **Categoría:** Código
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente) · **Fecha:** 1-oct-2026 (creación) / 12-oct-2026 (corrección integrada en el PR #3 por el equipo Parte 2; registro por el puente)
1. **Prompt (literal):** `prompts/asesoria_puente_claude.md`, **Prompt C** (1-oct-2026: "…que tipo de agentes crees que sean necesarios…").
2. **Respuesta relevante de la IA:** `.claude/agents/revisor-spec.md` y `revisor-calidad.md` (commit `2cd005b`) con `description: Revisa que la implementación … (ni más ni menos): contratos, …` — un `: ` dentro de un valor YAML sin comillas.
3. **Cómo sospechamos:** en la sesión del equipo Parte 2 esos dos tipos de agente no cargaban (anotado en MEMORIA el 9-oct); el equipo puso las descripciones entre comillas en el PR #3.
4. **Evidencia:** `evidencias/H-23_frontmatter_agentes.txt`: `yaml.safe_load` del encabezado original → `ScannerError: mapping values are not allowed here` en ambos; los otros agentes (sin `: ` en la descripción) cargan bien. Los 10 agentes actuales validan.
5. **Corrección:** comillas en las dos descripciones (PR #3).
6. **Lección:** un archivo de configuración generado también se prueba (aquí bastaba cargar cada encabezado con `yaml.safe_load`); que "funcionara" en una sesión no garantiza que funcione en otra.

---

## Pistas por probar (aún no son hallazgos) — aportadas por el equipo Parte 2
- **Aceptación de T2.2 "Madrid→Barcelona con `exclude=toll`"** (PLAN): esa ruta ya no tiene peaje (A-2 + AP-2 + AP-7 liberadas), así que `rapida` = `sin_peaje` y la prueba no puede validar la clase `toll`. El curador añadió Bilbao–Zaragoza (AP-68) y A Coruña–Pontevedra (AP-9). Falta averiguar quién/qué redactó la aceptación (¿IA?) y su prompt. **SIN PROMPT.**
- **Spec §7.2 Bloque 3, paso 1** ("pasos que tienen clase `toll`"): la clase está por intersección, no por paso; un paso de 293 km de la AP-68 tiene 94/96 intersecciones `toll` y uno de 11,4 km de la AP-9, 3/12. Sumar pasos completos sobreestima km de peaje (relevante en T2.5). Evidencia: `data/raw/osrm_2026-10-10/`. Origen del texto sin prompt. **SIN PROMPT.**
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

## Discrepancias en fuentes humanas (T2.4, 12-oct-2026) — no son alucinaciones de IA
Se documentan para el blog y para T2.5. Evidencia: `evidencias/T2.4_verificacion.txt` (§ indicado).
- **OpenStreetMap, `ref` erróneas en vías de peaje reales:** "A-66" en la AP-66 Campomanes–León (26 de 27 intersecciones `toll`; tarifa oficial en el PDF del Ministerio de la AP-66); "A-8" en la AP-8 de Bizkaia (Interbiak, Decreto Foral 147/2025); "DO" en la AP-8 de Gipuzkoa (Bidegi). El peaje es real y lo cubren AP66-*, AP8-01 y AP8-03.
- **OSM, cruces `toll` en N-622, GI-20 y PA-34:** las intersecciones `toll` están en el extremo del paso donde enlaza una autopista de peaje: N-622, 2 de 21, en (−2,859; 42,963) y (−2,863; 42,963), junto al enlace de Altube de la AP-68; GI-20, 2 de 2 al inicio del paso, que continúa por la AP-8 (Bidegi dice que la GI-20 es "antiguo tramo de la AP-8"); PA-34, 1 de 4, en (−1,683; 42,840). Es coherente con que sean las plazas o ramales de la autopista adyacente, pero **no verificable** con los crudos: no hay fuente oficial descargada que localice esas plazas a ese nivel de detalle.
- **Catálogo RCE 2025:** clasifica la AP-7 p.k. 676,3–706,75 (Circunvalación de Alicante) como "Autopista de peaje". El BOE-A-2025-25961 fija para ella una tarifa de "0 euros" para todas las categorías (§8). No es un error en sentido estricto: el BOE mantiene la vía en el régimen de peaje con tarifa 0, a la espera de la liberación formal. Es una **imprecisión** para quien lea la clase como "se paga".
- **SEITT, encabezados de los PDF de la R-4** (§8): `tarifas_r4_2026_1.pdf` (el enlazado) dice "Peaje 2026 R4" y "En vigor desde el 1 de enero de 2025"; `tarifas_r4_2025.pdf` dice "Peaje 2025" y "2023"; `tarifas_r4_2025_0.pdf` dice "Peaje 2024" y "2025". Los PDF de R-2, R-3 y AP-41 dicen "2026" de forma coherente. Error de la fuente.
- **Diputación Foral de Bizkaia, nota de 22-jul-2026** (§6): anuncia "una reducción media del 20% tanto para vehículos ligeros como para pesados", pero su tabla da −38,7 % (ligeros 6,85 → 4,20), −31,3 % (P1) y −31,6 % (P2). Incoherencia interna de la fuente oficial.
- **Ministerio, AP-9:** el PDF publica "SANTIAGO - SANTIAGO 4,55" sin explicar el recorrido; la web de Audasa tampoco (su lista de estaciones no tiene ninguna llamada "Santiago"). La calculadora oficial de Audasa muestra que el tráfico que cruza Santiago no lo paga (§4).

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
| 12-oct-2026 | T2.4: 15 tarifas de `peajes_tramos.csv` (dos muestras aleatorias, semillas 20261012 y 20261013, más la cadena AP-68 y la AP-9) frente al PDF oficial, con `pdftotext -raw`; R2-05, AP41-01 y R4-01 a mano en la matriz | Correctas todas. Haro–Logroño 4,85: el modo `-layout` lo desalinea y `-raw` lo confirma | `evidencias/T2.4_verificacion.txt` §1–2 |
| 12-oct-2026 | T2.4: km de las filas de los 5 pares de validación (AP-68, AP-9, AP-4, AP-41, AP-7, M-12) = suma de `longitud` del Catálogo RCE 2025 | Correctas (lector `.dbf` independiente) | `T2.4_verificacion.txt` §5 |
| 12-oct-2026 | T2.4: A Coruña–Pontevedra = AP9-01..04 = 16,35 € (AP9-03 a 0 €) | Correcta: la calculadora oficial de Audasa da 16,35 €. Con "Santiago-Santiago" serían 20,90 € | `T2.4_verificacion.txt` §4; `T2.4_audasa_calculadora_2026-10-12.json` |
| 12-oct-2026 | T2.4: AP-4 Sevilla–Cádiz "Autopista libre" (0 €); vigencias de la AP-68 hasta el 10-nov-2026 y La Rioja/Aragón libres desde el día siguiente; el BOE núm. 225 solo trata de pesados; Bizkaia 6,85 → 4,20 | Correctas | `T2.4_verificacion.txt` §5–6 |
| 12-oct-2026 | T2.4: los 54 SHA-256 de `data/raw/peajes_2026-10-12/MANIFEST.txt` | Correctos | `T2.4_verificacion.txt` §0 |
| 8-oct-2026 | T2.1: URL de `fuentes.md` responden; CSW `dateStamp` 2026-01-19; identificador IGR-PO `20251216_…_v2024`; §3.8 "Se permiten combinaciones"; 26codmun.xlsx idéntico al crudo; IGR-PO usa el centroide de áreas residenciales cuando no hay coordenada de un organismo (respalda en parte "centro de la zona residencial") | Correctas (7/7 HTTP 200). "No hay versión NGMEP posterior a 202603": **no verificable** (la lista de ficheros del CNIG se carga dinámicamente; la página muestra "(2026)") | `evidencias/T2.1_urls_http.txt` |
| 12-oct-2026 | T2.5: referencias oficiales de la validación: Bilbao–Zaragoza 39,90 (PDF AP-68), Bilbao–Altube 6,85, Bilbao–Autop. Burgos 12,40, Zambrana–Zaragoza 26,80, Agoncillo–Zaragoza 18,85, Logroño–Zaragoza 20,70, Autop. Navarra–Zaragoza 11,60; AP-41 5,95 (SEITT); A Coruña–Pontevedra 16,35, A Coruña–Guísamo 2,05, Guísamo–Pontevedra 15,40 (calculadora Audasa); Villalba–Segovia normal 8,60, Villalba–Ávila normal 11,85, Campomanes–León 16,20 (PDF Ministerio); Eibar–Vitoria 10,04 y Eibar–Donostia 7,43 (Bidegi); Málaga–Estepona 9,55 y Estepona–Guadiaro 2,45 | Correctas todas. Fechas de consulta coherentes con las cabeceras `Date` (12-oct-2026) | `evidencias/T2.5_cazador/` y PDFs de `data/raw/peajes_2026-10-12/` (`pdftotext -raw`) |
| 12-oct-2026 | T2.5: vías de los 5 pares (AP-68 293,2 km con 94 intersecciones `toll`; AP-4 92,8 km sin `toll`; A-42 66,7; A-7 39,3 + A-70 28,5 + A-31 3,0; AP-9 126,5 km con 33) | Correctas (lectura independiente de los crudos OSRM) | `evidencias/T2.5_cazador/T2.5_vias_independiente.py` → `.txt` |
| 12-oct-2026 | T2.5: A-42, A-31, A-70, A-7 (Alicante/Murcia) = "Autovía"; AP-4 = "Autopista libre"; AP-41 y AP-66 = "Autopista de peaje" en el Catálogo RCE 2025 | Correctas | `evidencias/T2.5_cazador/T2.5_clases_rce.py` → `.txt` |
| 12-oct-2026 | T2.5: contraste de 3 rutas al azar (semilla 20261012) de las 15 adicionales: Vitoria–Bilbao 6,85 (= oficial), Vitoria–Donostia 17,61 (17,47 oficial, +0,8 %), A Coruña–Madrid 14,55 frente a 17,75 (−18,0 %) | Correctas, incluido el −18 %; causa: AP-9 Barcala–Guísamo 2,05 oficial frente a 1,05 prorrateado, y AP-6 no aditiva (Villalba–Adanero 15,70 frente a 13,50) | `T2.5_cazador/`; PDF AP-6, calculadora Audasa |
| 12-oct-2026 | T2.5: hipótesis "error aguas arriba en T2.4: la nota de AP51-01 cita 11,85 y la ruta Madrid–Ávila da 10,60" | **Refutada**: 11,85 es el valor del PDF (Villalba–Ávila, normal). La diferencia (−1,25 €) es exactamente la no aditividad de la AP-6: Villalba–Villacastín oficial 10,10 frente a 5,65 + 3,20 = 8,85. Es el efecto de la decisión "suma de tramos", no un dato mal transcrito | PDFs `mitma_tarifas_2026_ap-6.pdf` y `ap-51.pdf` |
| 12-oct-2026 | T2.5: `A-66` y `AP-66` son el mismo corredor Campomanes–León (nombre "Autopista Ruta de la Plata"; dos sentidos con `ref` distinta); `DO` ("Kantauriko autobidea") es la AP-8 guipuzcoana (de la salida 27 hacia Eibar); `A-8` ("Bizkaiko Golkoko Autobidea") es la AP-8 vizcaína hasta Ermua | Correctas por geometría y nombre en los crudos; la causa de la etiqueta en OSM no es verificable | `T2.5_cazador/T2.5_vias_independiente.py`; `rutas_pasos_peaje.csv` |
| 12-oct-2026 | T2.5: "OSM deja sin toll unos 8 km de la AP-7 de Málaga" | Correcta en la cifra: 2 pasos "A-7/AP-7" con 0 intersecciones `toll` suman 7,79 km (Málaga–Cádiz). Que el coche siga en la autopista de peaje no es verificable con las fuentes locales; Málaga–Cádiz da 11,95 frente a 12,00 oficial | crudo `09_27_rapida.json.gz` |
| 12-oct-2026 | T2.5: 1-oct-2026 es temporada baja (nivel normal) en la AP-7 Málaga–Guadiaro | Correcta: la temporada alta es junio–septiembre y 17 días de Semana Santa | PDFs AP-7 Málaga–Estepona y Estepona–Guadiaro |
| 12-oct-2026 | T2.5: 6 anclas no-OSM al azar (semilla 20261012: 1, 8, 9, 32, 56, 72). Contraste con la geometría del Catálogo RCE en el p.k. correspondiente: AP-68 km 139,14 (0,17 km), AP-68 Enlace AP-15 (0,05 km), AP-9 Santiago sur (1,07 km), R-4 Ocaña (0,13 km); AP-1 Etxabarri-Ibiña (0,04 km de la salida 107 de OSM; km 38,094 frente a 145,8 − 107 = 38,8 de Bidegi, −1,8 %) | Coherentes (4 + 1). **No verificable:** ancla 1 (Basauri, "equivalente al inicio" de la AP-68): el Catálogo excluye el tramo vasco | `T2.5_cazador/T2.5_anclas_vs_rce.py` → `.txt` |
| 12-oct-2026 | T2.5: `GI-20`, `N-622`, `PA-34` no son de pago | `N-622`: libre según prensa (Gasteizhoy) y no figura en el Catálogo como autopista; `GI-20`: antigua AP-8, hoy autovía foral, Bidegi no publica tarifa para ella (Wikipedia + `bidegi_gure-autobideak_es.html`); `PA-34`: **no verificable** con fuente primaria. El efecto en `peaje_eur` es nulo por construcción (no se cobran) | `data/raw/peajes_2026-10-12/bidegi_gure-autobideak_es.html`; búsqueda web 12-oct |
| 12-oct-2026 | T2.5: "AP-15 sin barreras prorrateado hasta −17 %" (afirmación del curador, no está en el informe) | Verificada en la aritmética: 9,494 € frente a 11,40 € (tramo AP15-01 con fracción 0,8328; 31 filas, entre 0,83 y 1). Si la ruta paga o no una barrera (Tiebas/Marcilla) no es verificable sin los p.k. de las estaciones | `rutas_peajes_detalle.csv` |
| 12-oct-2026 | Bibliografía del blog (T0.7): 11 referencias escritas de memoria (DOI, primer autor, año, revista) contrastadas con Crossref | 10 de 11 coinciden en autor y año (Kennedy 1995 y Shi 1998: Crossref no registra el año de las actas; Berahas: en línea 2021, número 2022 → APA usa 2022). Discrepancia real: revista de Dantzig 1954 (H-22). Además, Crossref trae dañado el título de Stützle y Hoos ("– Ant System" en vez de "MAX–MIN Ant System"): copiar del registro a ciegas también introduce errores | `evidencias/H-bib_verificacion_doi.py` → `.txt` |
| 12-oct-2026 | H-12 (descartado por el puente): "El máximo WLTP de 4,8 es la configuración más equipada" | Imprecisa: explicación plausible sin fuente; se retiró del Spec. Se documenta aquí en lugar de como hallazgo | Entrada H-12 de este registro |
