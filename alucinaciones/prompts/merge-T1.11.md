# Merge de `origin/parte1-optimizacion-numerica` sobre T1.11 — prompt literal

```text
Hay un merge en curso en la rama `parte1-optimizacion-numerica`: se está trayendo `origin/parte1-optimizacion-numerica` (commits de Andrés y de Daniel: T4.6 parcial de la Parte 1 con las subsecciones de EA, PSO y DE del blog, el merge de `main` con la Parte 2, `.gitattributes` y la HPO ya integrada) sobre mi commit local de T1.11. NO hagas commit, NO hagas push, NO abortes el merge, NO cambies de rama ni crees ramas. Guarda ESTE prompt literal en `alucinaciones/prompts/merge-T1.11.md` antes de hacer nada más.

REGLAS DE ESTA SESIÓN
1. Sin marcas de revisión ni de autoría, ni nombres de personas, en ningún archivo que escribas (el nombre "Andrés" solo puede aparecer donde ya aparecía).
2. Edita SOLO con la herramienta Edit y respeta los finales de línea de cada archivo (`git ls-files --eol`: los .md de este equipo están en CRLF en el árbol de trabajo; `.py` y `.yaml` se fijan en LF con `.gitattributes`). `alucinaciones/evidencias/**` está marcado `-text`: se guarda byte a byte; edítalo solo donde se indica.
3. No resuelvas un conflicto con `git checkout --ours/--theirs` de un archivo entero: hay que conservar lo de los dos lados.
4. Todo error que detectes en un texto o prompt anterior va a `alucinaciones/registro.md` (no debería haber ninguno nuevo; si lo hay, el siguiente número libre es H-44).

SITUACIÓN (simulada de antemano; verifícala con `git status` antes de actuar)
- Conflictos reales en TRES archivos: `alucinaciones/registro.md` (2 bloques), `blog/secciones/03-parte1-metodologia.md` (1 bloque) y `docs/MEMORIA.md` (3 bloques). `docs/spec/PLAN.md` y `src/common/cli.py` se fusionan solos: solo verifícalos. El código, las configs y los resultados no se tocan.
- Colisión de numeración: Andrés ya renumeró su hallazgo del PSO a **H-41** (blog, "cada partícula se desplaza c₂·R₂⊙(g − x)") y está subido. Mis dos hallazgos de T1.11 usan también H-41 y H-42, así que pasan a **H-42** y **H-43**:
  - mi H-41 ("η = 1,5e-4 cumple η ≤ 1/L en 2D y 3D"; falso en 3D) -> **H-42**;
  - mi H-42 ("frac_c = fracción de N que se cruza") -> **H-43**;
  - H-38, H-39 y H-40 (míos de T1.10/T1.10b) no cambian; H-41 (PSO) no se toca.

RESOLUCIÓN

A) `blog/secciones/03-parte1-metodologia.md` (un bloque, en la subsección del DE)
 1. Conserva la versión de `origin` de las subsecciones EA, PSO y DE completas (hasta el final de «Qué no garantiza» del DE).
 2. Elimina de mi lado el marcador «*Pendiente (T1.4, T1.5 y T1.6).*» del DE, y de su lado la subsección «### Ajuste de hiperparámetros» con su línea «*Pendiente: …*» (la sustituye mi subsección).
 3. Después del DE deja mi subsección «### Optimización de hiperparámetros» COMPLETA, tal como está en mi lado (protocolo, tabla `espacios-hpo`, regla de selección, ejemplo del PSO y «Corrección de la regla»).
 4. Comentario de cabecera del archivo (líneas 2-3, «ESTADO: borrador (13-oct-2026): protocolo, GD, EA, PSO y DE redactados; falta la subsección "Ajuste de hiperparámetros"»): quita la cláusula «falta la subsección …» y deja el estado como borrador con todas las subsecciones redactadas.
 5. Comprueba que los identificadores `::: tabla` y `::: figura` del archivo son únicos (`parametros-gd`, `sensibilidad-eta`, las de EA/PSO/DE y `espacios-hpo`) y que cada uno se cita con `[[tab:id]]`.

B) `alucinaciones/registro.md` (dos bloques)
 1. Bloque de la tabla de cobertura y de los totales: parte de la versión de `origin` y súmale mis dos hallazgos ya renumerados. Resultado esperado (recalcúlalo con `grep -c '^### H-'` y ajusta el texto si no coincide): Conceptos 9 (H-16; Parte 1: H-26, H-31, H-32, H-34, H-39, H-41, H-42, H-43; H-31, H-32, H-41, H-42 y H-43 de severidad baja); Código 18 (sin cambios); **Total registrados: 43** (H-01–H-43), conservando en la frase los textos de H-38, H-39, H-40 y H-41 y añadiendo H-42 y H-43 con su descripción corta.
 2. Bloque de las entradas: deja las secciones en orden numérico: … H-38, H-39, H-40 (mías, ya estaban), **H-41 de Andrés (completa, tal como la trae `origin`)**, **H-42 (mi antigua H-41, η = 1/L)** y **H-43 (mi antigua H-42, frac_c)**. Cambia los encabezados y cualquier referencia interna a esos números dentro de las dos entradas.
 3. Comprueba: `grep -oE '^### H-[0-9]+' alucinaciones/registro.md | sort | uniq -d` vacío, y los encabezados van de H-01 a H-43 sin repetir ni saltar.

C) Referencias a mis números antiguos (SOLO en lo que es mío de T1.11; nunca toques lo de Andrés)
 - `alucinaciones/evidencias/H-T1.11_auditoria.md`, `alucinaciones/evidencias/H-T1.11_cifras.txt` y `alucinaciones/prompts/T1.11.md`: cambia «H-41» por «H-42» (η) y «H-42» por «H-43» (frac_c) donde se refieran a MIS hallazgos (hazlo de mayor a menor: primero H-42 -> H-43, luego H-41 -> H-42). Verifica antes con `git grep` que estos tres archivos son nuevos (no están en `origin`) y que ningún README de evidencias lista su SHA-256.
 - La fila de T1.11 en `docs/spec/PLAN.md` y las entradas de `docs/MEMORIA.md`: misma regla.
 - `git grep -n -E 'H-4[1-3]'` al final: cada mención debe corresponder a un hallazgo correcto (H-41 = PSO de Andrés; H-42 = η; H-43 = frac_c).

D) `docs/MEMORIA.md` (tres bloques; el resultado debe quedar en ≤ 150 líneas, `wc -l`)
 1. Filas «Fase» y «Próxima tarea»: parte de la versión de `origin` (T1.1–T1.7 y T1.10 ✅ en el PR #10) y añade: T1.10b ✅, T1.11 ✅ (blog: sección 03 al día con T1.7 y subsección de la HPO, 04 y 08 con el efecto de afinar, 11 con los comandos) y las subsecciones de EA, PSO y DE ✅ (Andrés, T4.6 parcial). Próxima tarea de la Parte 1, en este orden: T4.2 figuras (Andrés), T4.3 GIFs de GD y PSO (reutilizar el patrón de `src/viz/gifs.py` de la Parte 2), resultados principales en la 04 (tabla por configuración, sensibilidad k = 1, figuras) y discusión GD frente a heurísticos en la 08, T4.7 bibliografía (TODO(cita) abiertos), T1.8 (auditor de la demo) y T1.9 opcional; nombres completos de la Parte 1 en `blog/docs/index.md`.
 2. Párrafo «Candidatos»: parte de la versión de `origin` (41, con el H-41 del PSO) y recalcula: **43 candidatos** (añade H-42 y H-43), activos 41, confirmados por el puente 9 (sin cambio), categoría Conceptos 9.
 3. Bitácora: conserva las filas de `origin` (ya vienen condensadas) y añade arriba, con fecha 2026-10-13, mis filas de T1.11, T1.10b y la de este merge. Si sobrepasa 150 líneas, condensa las filas más antiguas de la Parte 1 (regla 3 de la propia MEMORIA); no borres hallazgos ni decisiones.

E) Verificaciones sin conflicto
 1. `docs/spec/PLAN.md`: debe tener la fila T1.11 y las filas T1.7 y T1.10 (con el texto de T1.10b) intactas; no cambies estados de otras filas.
 2. `src/common/cli.py`: `python run.py --help` debe listar `part1`, `hpo`, `part2` y `figures`.
 3. `blog/secciones/09-uso-ia.md` y `10-caceria.md` dicen «38 candidatos»: es una cifra vieja. Si la frase es solo ese total, cámbiala por el total real del registro (43); si está atada a otros números que no puedas comprobar (confirmados, categorías), no la toques y repórtala.
 4. NO toques `blog/docs/index.md` (los nombres de los autores de la Parte 1 los escribe una persona a mano).

VERIFICACIÓN (ejecútala y pega las salidas)
1. `git grep -n -E '^(<<<<<<< |=======$|>>>>>>> )'` sin resultados y `git status` sin rutas «unmerged» (sin hacer `git add`: déjalas modificadas; yo hago el commit del merge).
2. `python -m mkdocs build --strict -f blog/mkdocs.yml` sin errores.
3. `python -m pytest -q` completo. Línea base de mi rama antes del merge: 5 failed (higiene LF por `core.autocrlf`), 2369 passed, 3 skipped. Con `.gitattributes` (`*.py` y `*.yaml` con `eol=lf`) esos 5 deberían desaparecer SOLO si los archivos se vuelven a escribir con LF; si siguen fallando, NO cambies finales de línea ni código: repórtalo con la lista de archivos y con la salida de `git ls-files --eol` de esos cinco.
4. `wc -l docs/MEMORIA.md` ≤ 150 y el resultado de las comprobaciones de los apartados B.3 y C.
5. Búsqueda en los archivos que escribiste: «Juan», «Daniel», «revis», «sustent», «estudio» y «§» en texto nuevo del blog: 0 coincidencias nuevas (las que ya existían en lo de Andrés o en «Spec §» no cuentan).

REPORTE FINAL: tabla de archivos con conflicto y regla aplicada, lista de menciones de H-41/H-42/H-43 que dejaste, líneas de MEMORIA, salida de mkdocs, totales de pytest, y cualquier cosa dudosa o decisión que deba ir a Daniel.
```
