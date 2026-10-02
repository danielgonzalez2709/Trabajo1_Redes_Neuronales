# 🎯 Registro de la Cacería de la alucinación

> Meta: ≥5 hallazgos **genuinos** en ≥3 categorías. **Nunca inventar.** Un candidato sin prompt literal o sin evidencia no cuenta.
> Evidencias en `alucinaciones/evidencias/`. Prompts literales en `alucinaciones/prompts/`.

## Cobertura actual
| Categoría | Candidatos | Confirmados |
|---|---|---|
| Matemáticas | 1 | 0 |
| Código | 0 | 0 |
| Datos del mundo real | 2 | 0 |
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
- **Estado:** candidato — **falta el prompt literal**
- **Categoría:** Datos del mundo real / Código
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente, 29-sep-2026). Nota: el documento de Camila (1-oct-2026) lo plantea **correctamente** (OSRM local con extracto de Geofabrik); el mensaje previo del equipo Parte 2 era ambiguo sobre el servidor público. El hallazgo se atribuye solo a la respuesta de Claude.
1. **Prompt (literal):** PENDIENTE — primer mensaje del puente a Claude (29-sep-2026).
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
- **Estado:** candidato — falta el prompt literal
- **Categoría:** Matemáticas / Conceptos
- **Herramienta y modelo:** Claude Opus 5.5 (asesoría al puente, 29-sep-2026)
1. **Prompt (literal):** PENDIENTE — mensaje del puente pidiendo "soluciones viables para cada parte con todos sus detalles" (29-sep-2026).
2. **Respuesta relevante:** "Rosenbrock 2D en el mínimo: Hessiana … λ_max ≈ 1001.6 → η < ≈0.002" y luego, en el Spec v1.0, "usar η = 1e-3" como valor "justificado".
3. **Cómo sospechamos:** al evaluar qué dominio usar, se calculó la curvatura en todo el dominio, no solo en x*.
4. **Evidencia:** `evidencias/H-03_rosenbrock_dominio.py` y `.txt`: en [−2.048, 2.048]² la constante de Lipschitz del gradiente es L ≈ 5 971 → la
   garantía global exige η ≤ 1/L ≈ 1.7e-4; η = 1e-3 la viola (aunque empíricamente converge). En [−5, 10]² (L ≈ 122 133) el mismo η diverge.
   Lo correcto de la afirmación original: λ_max(x*) = 1001.6 (verificado).
5. **Corrección:** Spec v1.1 §6.3: η = 1e-3 declarado como elección empírica sin garantía global; η = 1/L como sensibilidad; Armijo como variante adaptativa.
6. **Lección:** una cota de estabilidad local (en el óptimo) no justifica un paso fijo desde inicios aleatorios lejanos; calcular L en todo el dominio.

---

## Pistas por probar (aún no son hallazgos) — aportadas por el equipo Parte 2
- **Peajes liberados:** preguntar a una IA qué peajes hay entre Bilbao y Zaragoza, o entre Sevilla y Cádiz; comparar con el listado del Ministerio (AP-68, AP-7, AP-4, AP-2).
- **Consumo sin versión:** preguntar cuánto consume el Tucson híbrido y ver si aclara versión y país (215 CV en Bélgica vs 239 CV en España).
- **Fuente contradictoria:** una reseña del Corolla lo titula "híbrido enchufable" y en el texto lo describe como autorrecargable; ver si una IA repite el error.
- **Geocodificación:** pedir coordenadas de capitales con nombre bilingüe y verificar que el punto caiga en la ciudad correcta.
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
