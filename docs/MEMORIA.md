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
| Última actualización | 2026-10-12 |
| Fase | **F0 — Fundaciones** T0.1–T0.4 ✅ en `main`; **T0.5 ✅, T0.7 blog ✅, T4.1 paleta ✅** (rama `integracion/t05-t41`, PR pendiente) · **F1 — Parte 1** en curso (T1.1 ✅, T1.2 ✅, T1.3 ✅, T1.4 ✅, T1.5 ✅, T1.6 ✅; falta T1.7; `main` ya integrado en `parte1-optimizacion-numerica`) · **F2 — Datos Parte 2** ✅ cerrada (T2.0–T2.8) · **F3** T3.1 ✅ |
| Próxima tarea | Parte 1: **T1.7** (`experiment.py`; ya existen los 5 optimizadores) y, en otra sesión, una **ronda de refactor** (funciones compartidas `validar_limites`, `validar_poblacion`, `leer_record_frames`, `construir_frame`, `_exigir_forma` y helpers de prueba, hoy duplicados en `ea.py`/`pso.py`/`de.py`); revisión de Daniel a T1.5/T1.6 y PR. Parte 2: **T3.2** exacto, **T3.3** ACO, **T3.4** GA, T3.5 2-opt (todas paralelizables tras T3.1; T3.3 y T3.4 editan `base.yaml`: integrar de a una). Integración: secciones del puente en el blog (uso de IA, cacería). **Todos: redactar su sección en `blog/secciones/` (guía: `blog/README.md`).** **Las tareas de Camila (T2.3 ejecución, T2.6, T2.7) las asumió Jose Miguel el 11-oct.** |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 1) |
| Sustentación | jue 15-oct-2026, 6 p. m. (por confirmar) |

## 👥 Equipo
| Rol | Quién |
|---|---|
| Parte 1 — Optimización numérica | 2 integrantes (nombres: Edinson y Juan Jose) |
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
- Bloque 3 (Spec v1.9, T2.4): `peajes_tramos.csv` con 56 tramos encadenados; km del **Catálogo RCE 2025** (zip de 24 MB sin versionar)
  y 11 km forales/autonómicos **medidos en OSM** (aproximación, `scripts/medir_km_osm.py`); una tarifa por tramo (AP-51/61 normal,
  AP-71 diurna, SEITT efectivo, AP-7 temporada baja); **M-12 paga de la M-40 a la M-13**; AP9-03 = 0 € (calculadora de Audasa).
- Bloque 1 (Spec v1.2): coordenadas del **NGMEP 202603** (fila "Capital de municipio", descarga manual por reCAPTCHA);
  IGR Poblaciones = contraste (≤ 2,5 km); Nominatim solo control. Crudos versionados salvo el `.mdb`.
- **EA de la Parte 1 (Spec 1.14, 12-oct; `docs/spec/propuestas/CAMBIO-EA.md` la llama "v1.4": es la misma, renumerada al integrar `main`):** esquema de clase (IRNA202602), N=50, frac_e=0.15 / frac_m=0.10 / frac_c=0.75; mutación de un gen
  con σ poblacional; cruce de un punto ∈ {1,…,d−1}; élite **no se reevalúa** (50 + 42 por generación); parada por presupuesto §6.2;
  `ea.esquema` solo `clase` (torneo/BLX-α queda reservado, no implementado).
- **PSO de la Parte 1 (T1.5, 12-oct):** gbest con inercia; N=30, w=0.7298, c1=c2=1.49618 (cifras redondeadas de la constricción con φ = 4.1;
  **cita de Clerc & Kennedy sin verificar → no citar**), `vmax_frac`=0.2 (v_max = 0.2·(ub−lb)), **v inicial = 0**, frontera = recortar y v=0 solo en la
  componente que salió; n_f = N·(T+1); en 2D con 20 000: 666 frames; `pso.iteraciones: null` (parar por presupuesto), `vmax_frac: null` = sin límite; aviso si w ≥ 1.
- **DE de la Parte 1 (T1.6, 12-oct):** DE/rand/1/bin síncrono; NP=30, F=0.7, CR=0.9, `generaciones: null`; padres r1≠r2≠r3≠i (una llamada al rng: `argsort` de uniformes, NP ≥ 4);
  reinicio U(lb, ub) por componente **sobre el mutante antes del cruce** (cierre inclusivo); cruce binomial `U ≤ CR` o `j_rand`; selección `f(u) ≤ f(x)` (el hijo gana en empate);
  la generación truncada por presupuesto se **descarta** (sin frame); n_f = NP·(T+1); en 2D con 20 000: 666 frames. Éxitos 30/30, 30/30, 30/30 y 28/30 (Rastrigin 3D).
- Algoritmos Parte 2: AS → MMAS, GA (OX + inversión), 2-opt opcional, óptimo exacto con PuLP como referencia.
- Front: **Material for MkDocs** + Plotly (interactivas) + matplotlib con estilo DS (GIF). Todo Python.
- **Blog (T0.7):** una entrada (`blog/docs/index.md`) que une `blog/secciones/*.md`; hook `blog/hooks/reporte.py` numera figuras/tablas APA
  (`::: figura id` … `:::`), resuelve `[[fig:id]]` y citas `[@clave]` con pandoc + APA 7, y **falla** si falta título/fuente, una figura no
  se cita o una cita no está en `references.bib`. Bibliografía SOLO desde el BibTeX oficial del DOI (nunca de memoria). `mkdocs` fijado en 1.6.x
  (MkDocs 2.0 elimina los hooks). Comando: `mkdocs build --strict -f blog/mkdocs.yml`.
- Desarrollo con **Subagent Driven Development**: 10 agentes en `.claude/agents/`, protocolo en `CLAUDE.md`.
- **F0 disponible para los equipos** (Spec §4.1, §5.1, §5.4): `run.py part1|part2|figures --config … --set clave=valor`;
  configs con herencia (`hereda: base.yaml`; **cada método añade su bloque completo a `base.yaml`**); YAML 1.2 (`1e-3` es número,
  `010` es 10, `no` es texto); un bloque no se reemplaza por un valor; `CountedProblem(func, k, budget)` lanza `BudgetExhausted`
  antes de exceder y lee dominio/dimensión de `problem.func`; `make_rng(base_seed, run_id)`; `save_json` (sin NaN/inf) y
  `run_filename(func, dim, method, seed)` con identificadores `^[a-z0-9]+$` (`gdfijo`, `gdarmijo`, `ea`, `pso`, `de`).

## ⏳ Pendientes / bloqueos
- [ ] **`base.yaml` sin clave de consumo ni de precio** (solo `costo.valor_hora`): sin ella la sensibilidad de §7.5 con `--set` no funciona. Asignado a **T3.6**. Punto de partida (no decidido): claves opcionales `consumo_l100` y `precio_l`; vacías = valores de `vehiculo.yaml` y `combustible.json`.
- [ ] T3.6: hay cruces de alternativa a 0,011 €/h de w = 30 (pares (34,40) y (34,42)), por debajo de la resolución de 0,5 €/h de la bisección.
- [ ] T2.2: ¿`osrm.sh descargar` como paso manual documentado o vía `descargar_datos.py`? (CLAUDE.md: solo ese script usa internet).
- [x] Spec §7.2 Bloque 3: la clase `toll` va por intersección, no por paso → resuelto en T2.5 (Spec v1.10: km por anclas, no por proporción de intersecciones).
- [ ] **T2.5, verificar a mano:** los 63 anclas no-OSM (5 de 6 verificados por muestreo); parámetros 1,5 km y 95 % sin fuente; `GI-20`/`N-622`/`PA-34` sin cobrar (sin tarifa publicada). Ampliación de §5.3 (5 archivos auxiliares): **confirmada por Jose Miguel el 12-oct.**
- [x] Zona horaria (T2.8, 12-oct): la 1.ª iteración de OSRM salió del equipo de Camila (UTC−3, Brasil); el resto, del PC de Jose Miguel (UTC−5). Documentado en el encabezado de `fuentes.md`; la atribución a UTC−3 se apoya en `scripts/osrm/README.md`, no en los crudos.
- [ ] **`AP68-POST-VI`** (Álava, tras el 10-nov): `tarifa_ligeros_eur` en `TODO(dato-faltante)`, sin tarifa oficial. Pendiente de decisión humana; el test lo admite solo fuera de la vigencia del corte y documentado por id.
- [x] **Acabado** del Corolla: Style Plus 140H e-CVT MY27 (Spec v1.7). Extra alta 5,6–6,2 (catálogo 2023) = sensibilidad.
- [x] Puente (Daniel, 12-oct): H-12 y H-13 descartados, H-14 confirmado, H-15 en Datos (propuestas del equipo Parte 2). Confirmados además H-03, H-04, H-07, H-08, H-10, H-17, H-22 → **9 confirmados en 4 categorías**.
- [x] **T2.3 (12-oct):** OSRM depende del historial de consultas del proceso → `--threads 1`, arranque limpio y una
  corrida (Spec v1.8). 26 `sin_peaje` con `toll` (M-12, AP-15, AP-68): **T2.5 los cobra**. Opcional si sobra tiempo: un
  proceso por alternativa (probado, 0 con `toll`). **T2.4 debe incluir M-12 y AP-15.**
- [x] **Design System:** skill `apple-design` (Emil Kowalski). Falta la **paleta de colores** (T4.1); la skill no la define.
- [x] **T2.5:** peaje cerrado = **suma de tramos** [DECIDIDO 12-oct]; se reporta la diferencia (41,50 vs. 39,90 €; AP-6 −14 %; sesgo −18 %…+4 %).
- [ ] Blog (T4.6): reportar los km aproximados de OSM; el contraste de la AP-8 debe citarse como Urgoiti–Durango (17,506 vs. 17,5 km),
  no Urgoiti–Ermua (parcialmente circular). AP-15 Norte: −12,9 % frente a un contraste derivado, sin explicar.
- [ ] H-19 (Bibliografía): falta `message.txt` del Prompt C (Daniel o Camila) para confirmar que la cita del BOE vino de la IA.
- [ ] ¿Escenario opcional `post_ap68`? Tras el 10-nov: La Rioja y Aragón libres, Bizkaia 4,20 €; Álava y Navarra sin tarifa oficial.
- [ ] Confirmar fecha/hora de la sustentación.
- [ ] Prompts literales para la cacería: ~~H-01, H-03 (Daniel)~~ ✅ en `alucinaciones/prompts/asesoria_puente_claude.md`; H-02 (Camila) pendiente.
- [ ] **T1.4 — cambios al Spec que decide Daniel (el Spec lo edita el equipo):** (a) "round de Python (mitades al par)" en §6.4; (b) añadir a la validación
  `n_cruzantes > N` → error (N=3 con defaults); (c) corregir "σ → 0 al converger" por "colapso prematuro" (H-26); (d) aclarar que `frac_c` bajo no reduce el cruce
  si el relleno lo anula; (e) comentario de cabecera de `base.yaml` desactualizado. Y la **revisión de Daniel al Spec 1.14 (antes "v1.4" de la Parte 1)** sigue pendiente.
- [ ] **T1.4 — 7 mejoras opcionales de revisor-calidad** (`alucinaciones/prompts/T1.4.md`, sección D) sin aplicar; no bloquean.
- [ ] **T1.5 — cambios al Spec que decide Daniel:** (a) en §6.4 PSO: v inicial = 0, claves `iteraciones` y `vmax_frac` (con `null` = sin límite) y aviso si w ≥ 1;
  (b) `SPEC.md:291`: 1.49618 es cifra derivada (χ·φ/2), no un valor del artículo (H-29). Y la **revisión de Daniel a T1.5** y el PR.
- [ ] **T1.5 — pendientes menores:** (a) verificar la cita primaria de Clerc & Kennedy (2002; DOI candidato verificado en Crossref, texto no accesible); (b) si todas las
  evaluaciones dan NaN o +inf, `problem.best_x` es None y `optimize` lanza `AttributeError` (`pso.py` y `ea.py`; no ocurre con Rosenbrock/Rastrigin) — decidir si se añade una guarda;
  (c) la prueba `test_la_particula_que_es_g…solo_se_mueve_por_inercia` conserva un nombre impreciso (opcional); (d) en el blog documentar: el líder no se mueve con v(0)=0 hasta que g cambie
  y "PSO garantiza el óptimo global" es falso (Rastrigin 3D: 26/30 éxitos).
- [ ] **T1.6 — cambios al Spec que decide Daniel** (ya escritos como línea `[PENDIENTE]` en Spec §6.4, tras la tabla; falta su aprobación): en §6.4 DE: (a) regla `≤` en la selección; (b) reinicio sobre el mutante antes del cruce; (c) esquema síncrono y sorteo de padres;
  (d) claves `NP`, `F`, `CR`, `generaciones` (null = parar por presupuesto) y `NP ≥ 4`; (e) convención `U ≤ CR`; (f) generación truncada descartada: `f_best` puede venir de un hijo de esa
  generación (mejor punto visto, §5.1); (g) `best` del frame = mejor de la población actual. Y la **revisión de Daniel a T1.6** y el PR.
- [ ] **T1.6 — pendientes menores:** (a) **M1** `_exigir_forma` duplicada con `pso.py` y **M8** helpers de prueba repetidos / pruebas de sanidad lentas (~17 s) → ronda de refactor;
  (b) mutante M11 (`U<=CR`→`U<CR`) equivalente, sin prueba; (c) falta el contraste numérico con SciPy `rand1bin` (no está instalado; lo cubre T1.9); (d) en el blog: "DE garantiza el
  óptimo global" es falso (Rastrigin 3D: 28/30) y la diferencia solo se encoge si la población se concentra (H-32); (e) misma guarda pendiente de NaN que en PSO/EA.
- [x] `revisor-spec` y `revisor-calidad` no cargaban como agentes: su `description` llevaba `": "` sin comillas (YAML inválido, verificado con PyYAML el 11-oct). Corregido con comillas; reiniciar Claude Code para que carguen.

## 🎯 Cacería de alucinaciones
Candidatos: **34** (H-32 docstrings del DE "se encoge al converger" / "el mejor individuo nunca se pierde" (T1.6, severidad baja) · H-21 "Logroño" inventado en T3.1 · H-22 Dantzig 1954: revista con el nombre actual · H-23 YAML de dos agentes inválido · H-20 débil: mutante de T2.5 que las pruebas no cazaban, ya cerrado · H-01 OSRM público · H-02 AP-68 · H-03 paso de GD · H-04 ORIGENCOOR · H-05 capital = municipio · H-06 Mérida ·
H-07 PuLP 4 sin CBC · H-08 contador y redondeo · H-09 np.float64 · H-10 prueba que no falla · H-11 campos PBF · H-12 WLTP máx. 4,8 ·
H-13 buscador "sin ficha" · H-14 "no publican extra alta" · H-15 paráfrasis infiel · H-16 causa OSRM mal atribuida · H-17 AP-9 desplazada una fila · H-18 Catálogo "excluye" la AP-68 navarra · H-19 BOE núm. 225 mal citado ·
Parte 1, renumerados al integrar `main` (antes H-12–H-19 de su rama): H-24 .pyc obsoleto · H-25 TestFunction · H-26 "σ→0 al converger" · H-27 prompt 714 frames en 3D · H-28 anclas "de esta implementación" · H-29 1.49618 atribuido a Clerc & Kennedy · H-30 línea base "513 passed, 1 skipped" · H-31 papel de b_i con v = 0 · H-33 comentarios de prueba inexactos · H-34 umbral de redondeo de Armijo en el blog) —
confirmados por el puente: **9** (H-03, H-04, H-05, H-07, H-08, H-10, H-14, H-17, H-22; 4 categorías); por el cazador, pendiente del puente: H-18; descartados: H-12, H-13 — activos 32; categorías (tabla del registro): Datos (9, más H-13 descartado), Matemáticas (1), Código (14),
Conceptos (5: H-16, H-26, H-31, H-32, H-34; más H-12 descartado), Bibliografía (3: H-19 origen pendiente, H-22, H-29). Técnica útil: **prueba de mutación**.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-12 | Parte 1 + Claude (SDD) | T4.6 parcial Parte 1: secciones 02 y 03 (GD). 02: párrafo del GD con la condición de Armijo proyectada; 03: protocolo común, GD de paso fijo (L de Rastrigin), Armijo y tabla `parametros-gd`. redactor-tecnico 2 rondas; cazador ✅ (refutó la premisa "Armijo en Rastrigin termina por presupuesto" y halló **H-34**). Pendiente: sección 03 de EA/PSO/DE y toda la 04 tras T1.7; TODO(cita) de η ≤ 1/L. ⚠️ `origin/main` ya usa H-24 (GA): renumerar al integrar. |
| 2026-10-12 | Parte 1 + Claude (SDD) | Merge de `origin/parte1-optimizacion-numerica` (T1.6 DE de Andrés) con los comentarios de T1.1–T1.3: conflictos solo en `registro.md` y `MEMORIA.md`; el H-32 de los comentarios pasa a H-33 porque H-32 ya era el de los docstrings del DE; pytest (Windows) 1417 passed, 3 skipped, 0 failed (`test_de.py` 119 passed; el +1 es `test_no_network`, que ahora revisa también `de.py`); `mkdocs build --strict -f blog/mkdocs.yml` sin errores; AST de `functions.py`, `gd.py`, `test_gradients.py` y `test_gd.py` idéntico al de 2ffcd4a. |
| 2026-10-12 | Parte 1 + Claude (SDD) | Comentarios línea a línea en functions.py y gd.py y por prueba en test_gradients.py y test_gd.py; solo comentarios, AST idéntico, suite sin cambios (1297 passed, 3 skipped). implementador 2 rondas; revisor-calidad ✅ (ronda 2; en la 1 halló 3 comentarios de prueba inexactos), verificador-matematico ✅. Candidato **H-33** (Código). Prompts en `alucinaciones/prompts/comentarios-T1.1-T1.3.md`. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **Merge de `parte1-optimizacion-numerica` (Spec 1.14, `main` integrado) en `feat/parte1/T1.6-de`**: conflictos solo en `PLAN.md`, `MEMORIA.md` y `registro.md` (código y `base.yaml` fusionaron solos); se conservó la renumeración H-24..H-31 y el EA en esquema de clase del Spec §6.4; el candidato de T1.6 pasó de H-20 a **H-32** (H-20 ya existe en `main`); estado y próxima tarea actualizados sin tocar lo de la Parte 2. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **T1.6 ✅** (`de.py` + `tests/test_de.py`, 119 pruebas; suite 981 passed): `optimize` orquestador + 6 componentes puros (padres, mutación, reinicio, cruce, selección) con rng inyectado y orden fijo; defaults solo en `base.yaml`. Rondas: implementador ×2 (ronda 2 = M2–M7 de calidad) y E1–E3 de redacción aplicadas por el orquestador, revisor-spec ✅ (0 bloqueantes), revisor-calidad ✅ (8 mejoras; M1 y M8 diferidas a refactor), verificador-matematico ✅ (reimplementación bit a bit 30 semillas × 4 configs; 25/26 mutantes muertos, M11 equivalente; SciPy no instalado). 2D/20 000: 0.35 s; 3D/30 000: 0.48 s. Candidato **H-32** (Conceptos, baja). Pendiente: cambios al Spec, revisión de Daniel y PR. Planeación y prompts en `alucinaciones/prompts/T1.6.md`. |
| 2026-10-12 | Parte 1 + Claude | Merge de origin/main en parte1-optimizacion-numerica: conflictos en registro.md, MEMORIA.md y SPEC.md resueltos; H-12..H-16 renumerados a H-24..H-28 (y H-17..H-19 de T1.5 a H-29..H-31); Spec 1.14; pytest (Windows) 1297 passed, 3 skipped, 0 failed (incluye test_no_network, test_blog y test_viz de `main`); `mkdocs build --strict -f blog/mkdocs.yml` sin errores; `src/part1`, `configs/part1` y sus pruebas sin cambios. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **T1.3 ✅** (variante `armijo` de `gd.py` con bucle común `_descenso` + reglas `_PasoFijo`/`_PasoArmijo`; condición sobre el punto proyectado; suite 697 passed, 1 skipped; 35 mutantes muertos): revisor-spec ✅ (1 ronda), revisor-calidad ✅ (2 rondas, forma y una aserción tautológica del oráculo), verificador-matematico ✅ (reimplementación idéntica bit a bit; ~10 f/iteración en Rosenbrock = 9 retrocesos ≈ log2(λ_max/2); Rastrigin 3D no llega a ‖g‖ < 1e-8 por la resolución de f). Spec §6.3: línea [PENDIENTE] de Armijo proyectado. Sin candidatos nuevos. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **T1.2 ✅** (`gd.py` paso fijo con proyección + bloque `gd:` en `base.yaml`; 69 pruebas; suite 416 passed, 1 skipped; 15/15 mutantes muertos): revisor-spec ✅ (1 ronda), revisor-calidad ✅ (2 rondas, correcciones de forma), verificador-matematico ✅ (reimplementación independiente idéntica en 30 semillas × 4 configs). Spec §6.3: línea [PENDIENTE] de la config del GD. Escalar: el ejemplo `--set gd.armijo=true` de §4.1 ya no aplica. Candidato **H-28** (Código). |
| 2026-10-12 | Andrés (Parte 1) + Claude (SDD) | **T1.5 ✅** (`pso.py` + `tests/test_pso.py`, 163 pruebas; suite 677 passed): `optimize` orquestador + 9 componentes puros (SRP/DIP) con R1/R2 inyectadas, celdas `# %%` con LaTeX; en `ea.py` solo se quitó el `_` de 4 funciones compartidas (renombrado mecánico autorizado). Rondas: implementador ×5, revisor-spec ✅ (M1–M2 de pruebas corregidos), revisor-calidad ✅ (7 mejoras aplicadas), verificador-matematico ✅ (36 mutantes, 34 muertos, 2 equivalentes; w y c = constricción φ = 4.1 redondeada), cazador ✅ (fuente Clerc & Kennedy parcial). Candidatos **H-29**, **H-30**, **H-31**. Pendiente: guarda NaN (decidir), cita primaria, cambios al Spec, PR y revisión de Daniel. Planeación y prompts en `alucinaciones/prompts/T1.5.md`. |
| 2026-10-12 | Andrés (Parte 1) + Claude (SDD) | **T1.4 ✅** (`ea.py` + `tests/test_ea.py`, 165 pruebas; suite 513 passed): `optimize` orquestador + componentes puros (SRP/DIP), celdas `# %%` con LaTeX; revisor-spec ✅ ronda 1, revisor-calidad ✅ ronda 2 (B1 celdas), verificador-matematico ✅ (EA independiente bit a bit, 20 mutantes muertos). Candidatos **H-26** (Conceptos) y **H-27** (prompt). Pendiente: PR y revisión de Daniel. |
| 2026-10-12 | Andrés (Parte 1) + Claude | **T1.4 planeada** (aún sin código): `optimize` como orquestador + componentes puros (`ParametrosEA`, población inicial, evaluar, élite, mutación, cruce, ensamblar) con `rng` y evaluador inyectados (SRP/DIP), `ea.py` en celdas `# %%` con LaTeX y docstrings numpy; `frames` según §5.1 sin campos extra; `ea.generaciones` se conserva (null = presupuesto). Planeación y mensajes literales en `alucinaciones/prompts/T1.4.md`. Pendiente: revisión de Daniel del Spec v1.4 antes de despachar al implementador. |
| 2026-10-12 | Andrés (Parte 1) + Claude | **Spec v1.4**: EA pasa al esquema de clase (§6.2 y §6.4, notas, §10, §11, §13); PLAN T1.4 y T1.7 ajustados. Propuesta en `docs/spec/propuestas/CAMBIO-EA.md`; prompt en `alucinaciones/prompts/CAMBIO-EA.md`. Excepción única autorizada a "Claude no edita Spec/PLAN". Falta que Daniel (puente) revise el cambio. |
| 2026-10-12 | Parte 1 + Claude (SDD) | **T1.1 ✅** (`functions.py`, 73 pruebas; suite 347 passed, 1 skipped): revisor-spec, revisor-calidad y verificador-matematico aprueban en ronda 1; fórmulas, x*, f* y dominio de Rastrigin verificados contra SFU (12-oct). Candidatos **H-24** y **H-25** (Código). |
| 2026-10-12 | Daniel + Claude | Sección **Uso de IA** del blog (`blog/secciones/09-uso-ia.md`): metodología SDD, tabla de prompts principales con enlace al archivo literal (Tabla 3) e impacto (qué aceleró, qué errores introdujo, cómo se controlaron, qué no se delegó). **Pendiente equipo Parte 1:** agregar sus filas T1.x a la tabla al fusionar. |
| 2026-10-12 | Daniel + Claude | Sección **Cacería** del blog redactada (`blog/secciones/10-caceria.md`): 7 hallazgos en 4 categorías con prompt literal (citas verificadas contra los archivos) y evidencia enlazada (H-03, H-07, H-08, H-10, H-04, H-17, H-22) + tabla resumen. **Pendiente: que el puente confirme los 7** para marcarlos como confirmados en el registro. |
| 2026-10-12 | Daniel + Claude | **T0.5 ✅** prueba sin red (run.py con sockets bloqueados + análisis estático de src/; mutante detectado). **T4.1 ✅** `src/viz/paleta.py` (fuente única de colores: método → color fijo; rampa azul), `theme.py` (Plotly) y `style.py` (matplotlib); figuras siempre sobre superficie clara (tarjeta en modo oscuro). 663 pruebas. |
| 2026-10-12 | Daniel + Claude | **T0.7 ✅** blog: MkDocs Material + hook `reporte.py` (APA con pandoc citeproc; `mkdocs-bibtex` descartado porque cita con notas al pie) + 12 secciones con responsables + 15 pruebas (640 en total). Bibliografía: 12 referencias del BibTeX oficial, 11 contrastadas con Crossref (H-21). H-23 confirmado con PyYAML. `mkdocs` fijado en 1.6.1 por el aviso de MkDocs 2.0. |
| 2026-10-12 | Jose Miguel + Claude | **T3.1 ✅**: `costos.py` + `test_cost.py` (42 pruebas; 669 en total). implementador 3 rondas; revisor-spec ✅, verificador-matematico ✅ (cifras con aritmética exacta), revisor-calidad ✅. **Spec v1.11**: criterios de §7.3 reformulados (w = 0 por peaje + combustible; simetría contra `rutas.csv`). Validación: punto medio (`rutas.csv` sí; en `matriz_costos` solo parámetros finitos y ≥ 0). 554 de 1 081 pares con alternativas idénticas; 393 cruces en 0 < w ≤ 100. Cacería: **H-21** ("Logroño" inventado para la ciudad 0). |
| 2026-10-12 | Jose Miguel + Claude | **T2.8 ✅** (cierra F2): `fuentes.md` completo y `test_data_integrity.py` (51 pruebas; 627 en total). curador-datos 3 rondas; revisor-spec devolvió una aserción de simetría que no podía fallar (la matriz se arma espejando: `rutas.csv` guarda i<j, simetría por construcción, Spec §7.2); revisor-calidad devolvió pruebas tautológicas y duplicadas. La cabecera `Date` de caché (SEITT, Mitma) engañaba: la hora real es la "fecha local de la captura". Zona horaria resuelta. |
| 2026-10-12 | Jose Miguel + Claude | **T2.5 ✅**: peajes asignados a las 2 162 filas de `rutas.csv` (curador-datos, 2 rondas; revisor-spec ✅, revisor-calidad ✅, cazador ✅ CONFORME; 568 pruebas). Suma de tramos [DECIDIDO]; `peajes_tramos.csv` no tiene coordenadas → archivos laterales de cadenas y anclas. 5 pares validados (Bilbao–Zaragoza 41,50 €, A Coruña–Pontevedra 16,35 € = Audasa). El cazador refutó la sospecha de tarifa errónea de AP51-01. **Spec v1.10.** |
| 2026-10-12 | Jose Miguel + Claude | **T2.4 ✅**: tabla de peajes (56 tramos; curador-datos, 6 rondas; revisor-spec ✅, revisor-calidad ✅, cazador ✅; 512 pruebas). Una ronda previa transcribió matrices origen–destino sin km: se rehízo por tramos con km del Catálogo RCE y de OSM. **Spec v1.9** (AP-68 tras el 10-nov, tarifas, M-12). Cacería: H-17 a H-19. |
| 2026-10-12 | Jose Miguel + Claude | **T2.3 ✅**. Un diagnóstico mostró que OSRM no excluía peajes y una 2.ª ronda refutó la causa: la respuesta depende del historial de consultas del proceso (H-16). Corrida vigente `osrm_2026-10-12` con `--threads 1`; 26 `sin_peaje` con peaje, que cobra T2.5. **Spec v1.8**. |
| 2026-10-11 | Jose Miguel + Claude | **T2.7 ✅**: Corolla Style Plus 140H MY27, 4,6 l/100 km; combustible del catálogo de Toyota 09/2023 (descarga manual, verificado). **Spec v1.7**: acabado, `anio_modelo`, sensibilidad de consumo 5,6/6,2 en §7.5. Cacería: H-12 a H-15. |
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
