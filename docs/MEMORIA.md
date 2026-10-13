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
| Fase | **F0 — Fundaciones** T0.1–T0.4 ✅ en `main`; **T0.5 ✅, T0.7 blog ✅, T4.1 paleta ✅** (en `main`, PR #5) · **F2 — Datos Parte 2** ✅ cerrada (T2.0–T2.8) · **F3** T3.1, T3.3, T3.4 ✅ |
| Próxima tarea | Parte 2: **T3.6** experimentos (presupuesto común ACO vs GA), T3.5 2-opt (recomendado: el MMAS deja cruces visibles); **T3.2 exacto = opcional** (Spec v1.14). Integración: secciones del puente en el blog (uso de IA, cacería). **Todos: redactar su sección en `blog/secciones/` (guía: `blog/README.md`).** **Las tareas de Camila (T2.3 ejecución, T2.6, T2.7) las asumió Jose Miguel el 11-oct.** |
| Entrega | **mar 13-oct-2026, 23:59** (días restantes: 1) |
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
- Parte 2: fecha de corte **1-oct-2026**; OSRM **local con Docker** (T2.0, 10-oct; el servidor público no admite `exclude=toll`; ORS solo contingencia); dos alternativas por par
  (rápida / sin peaje); par sin peaje = la rápida no pasa por ninguna intersección `toll` (Spec v1.5); crudos de rutas NO se versionan,
  T2.5 usa `rutas_pasos_peaje.csv`; peajes oficiales + forales; Gasolina 95 E5 **media peninsular** (v1.6; la nacional queda como sensibilidad); **Toyota Corolla Sedán Hybrid 2026 1.8 L (140H)**.
- Bloque 3 (Spec v1.9, T2.4): `peajes_tramos.csv` con 56 tramos encadenados; km del **Catálogo RCE 2025** (zip de 24 MB sin versionar)
  y 11 km forales/autonómicos **medidos en OSM** (aproximación, `scripts/medir_km_osm.py`); una tarifa por tramo (AP-51/61 normal,
  AP-71 diurna, SEITT efectivo, AP-7 temporada baja); **M-12 paga de la M-40 a la M-13**; AP9-03 = 0 € (calculadora de Audasa).
- Bloque 1 (Spec v1.2): coordenadas del **NGMEP 202603** (fila "Capital de municipio", descarga manual por reCAPTCHA);
  IGR Poblaciones = contraste (≤ 2,5 km); Nominatim solo control. Crudos versionados salvo el `.mdb`.
- Algoritmos Parte 2: AS → MMAS, GA (OX + inversión), 2-opt opcional; exacto con PuLP **opcional** (v1.14).
- **GA (Spec v1.15 §7.4.2):** esquema clásico (torneo k=4, OX con dos hijos, mutación con **un** operador 50/50 inversión/intercambio,
  2 élites); notebooks del profesor (`data/raw/GA/`, sin salidas) solo como referencia. Conteo `150 + 148·gen` (cada candidato = 1).
  Población inicial con el vecino más cercano (mismo arranque que MMAS). Piezas comunes en `src/part2/recorridos.py`.
- **ACO (Spec v1.14 §7.4.1):** las **notas del profesor** (`data/raw/ACO/notas_aco.html`) priman sobre el Spec y todo cambio
  se trae al Spec. MMAS principal (ρ 0.02, p_best 0.05, alterna ib/bs), AS comparación (ρ 0.5). Berroa solo como referencia
  de estructura (repo sin licencia: no se copia código). Presupuesto común de recorridos ACO vs GA: lo fija T3.6.
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
- [ ] **T3.6, presupuesto común** ACO vs GA (hoy 14 101 vs 148 150 recorridos). El GA pierde diversidad (~30 recorridos
  distintos de 150 desde la gen. ~100, con o sin vecino más cercano); con 3 semillas, final 2 565–2 702 €. `scripts/ver_ga_temporal.py`. Con ρ = 0.02 y 300 iteraciones MMAS
  sigue mejorando al final y τ_min casi no actúa (~289 iteraciones para llegar). ACO tarda ~29 µs/recorrido (n = 47).
- [ ] Hallazgo para el blog: aun con w = 500 solo ~12 de 47 tramos pagan peaje; es el techo (tramos cuya rápida tiene
  peaje: ~23 % de los pares vecinos), no un error. `scripts/ver_aco_temporal.py --barrido` lo grafica.
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
- [x] `revisor-spec` y `revisor-calidad` no cargaban como agentes: su `description` llevaba `": "` sin comillas (YAML inválido, verificado con PyYAML el 11-oct). Corregido con comillas; reiniciar Claude Code para que carguen.

## 🎯 Cacería de alucinaciones
Candidatos: **24** (H-24 GA: prueba que no distinguía el orden de los padres, débil · H-21 "Logroño" inventado en T3.1 · H-22 Dantzig 1954: revista con el nombre actual · H-23 YAML de dos agentes inválido · H-20 débil: mutante de T2.5 que las pruebas no cazaban, ya cerrado · H-01 OSRM público · H-02 AP-68 · H-03 paso de GD · H-04 ORIGENCOOR · H-05 capital = municipio · H-06 Mérida ·
H-07 PuLP 4 sin CBC · H-08 contador y redondeo · H-09 np.float64 · H-10 prueba que no falla · H-11 campos PBF · H-12 WLTP máx. 4,8 ·
H-13 buscador "sin ficha" · H-14 "no publican extra alta" · H-15 paráfrasis infiel · H-16 causa OSRM mal atribuida · H-17 AP-9 desplazada una fila · H-18 Catálogo "excluye" la AP-68 navarra · H-19 BOE núm. 225 mal citado) —
confirmados por el puente: **9** (H-03, H-04, H-05, H-07, H-08, H-10, H-14, H-17, H-22; 4 categorías); por el cazador, pendiente del puente: H-18; descartados: H-12, H-13 — categorías: Datos (10), Matemáticas (1), Código (8: incl. H-23 y H-24),
Conceptos (2: H-12 con propuesta de descarte, y H-16), Bibliografía (2: H-19 origen pendiente, H-22). Técnica útil: **prueba de mutación**.
Meta: ≥5 genuinos en ≥3 categorías. Registro: `alucinaciones/registro.md`.

## 🗒️ Bitácora (más reciente primero)
| Fecha | Quién | Qué pasó |
|---|---|---|
| 2026-10-12 | Jose Miguel + Claude | **T3.4 ✅**: `ga.py` + `recorridos.py` (piezas comunes con ACO) + 103 pruebas (874 en total). implementador 3 rondas (Opus); revisor-spec devolvió una prueba que no distinguía OX(P1,P2)/OX(P2,P1) (**H-24**, débil) y luego ✅; revisor-calidad ✅ (Sonnet). **Spec v1.15** (§7.4.2). w = 25, semilla 0: GA 2 701,56 € con 148 150 recorridos (semillas 1–2: 2 565,53 €). Gráficos temporales en `scripts/ver_ga_temporal.py`. |
| 2026-10-12 | Jose Miguel + Claude | **T3.3 ✅**: `aco.py` (AS + MMAS, `solve` + `iterar`) y `test_aco.py` (60 pruebas; 769 en total). implementador 3 rondas (Opus); revisor-spec ✅, verificador-matematico ✅ (demostró que con el orden aprobado el recorte superior nunca se activa), revisor-calidad ✅ (Sonnet). w = 25: MMAS 2 589,55 €, AS 2 659,76 €, vecino más cercano 3 173,83 €. Sin candidatos nuevos a la cacería. |
| 2026-10-12 | Jose Miguel + Claude | **Spec v1.14**: T3.2 opcional; ACO según las notas del profesor (§7.4.1). Hallado: los valores por defecto daban 14 100 recorridos a ACO y ~150 000 a GA (comparación injusta) → presupuesto común en T3.6. Despachada T3.3. |
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
