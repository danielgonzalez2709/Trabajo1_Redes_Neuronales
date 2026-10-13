# Comentarios de legibilidad T1.1–T1.3 — prompts literales (12-oct-2026, orquestador: Claude Opus 5.5)

## Prompt del humano (Parte 1), literal

```text
Tarea de legibilidad del código de la Parte 1 (T1.1–T1.3). Estoy en la rama `parte1-optimizacion-numerica` (no crees ramas). Sigue el protocolo del CLAUDE.md: guarda ESTE prompt literal en `alucinaciones/prompts/comentarios-T1.1-T1.3.md` antes de hacer nada más. Despacha `implementador` para escribir los comentarios, luego `revisor-calidad` para comprobar que CADA comentario es exacto respecto a su línea, y luego `verificador-matematico` para las líneas con fórmulas (gradientes, proyección, condición de Armijo). Los archivos del árbol de trabajo están en CRLF (Windows): edítalos solo con la herramienta Edit, por bloques (una función o clase por edición), nunca reescribiendo el archivo completo.

OBJETIVO: que cada línea de código de `src/part1/functions.py` y `src/part1/gd.py` lleve un comentario breve en español que diga qué hace esa línea, y que las pruebas de `tests/test_gradients.py` y `tests/test_gd.py` tengan un comentario por prueba. SOLO comentarios: el comportamiento no cambia.

REGLAS DE LOS COMENTARIOS EN src/part1/functions.py y src/part1/gd.py
1. Todas las líneas con código ejecutable llevan comentario: imports, `class`, `def`, decoradores, asignaciones, `if/elif/else`, `for/while`, `try/except`, `return`, `raise`, `with`. Las líneas en blanco y las que solo cierran un paréntesis, corchete o llave NO llevan comentario; en una instrucción partida en varias líneas, comenta cada línea que aporte (cada argumento relevante).
2. Formato: comentario al final de la línea con dos espacios antes de `#`. Si la línea más el comentario superaría 100 caracteres, pon el comentario en la línea de arriba, con la misma sangría. No dejes ninguna línea NUEVA de más de 100 caracteres (las líneas que ya pasaban de 100 no se tocan ni se reformatean).
3. Contenido: qué hace la línea, en pocas palabras y con el símbolo matemático cuando aplique (η, ∇f, Π, x*, β, c). Añade el "para qué" solo cuando no sea obvio (por ejemplo, por qué se recorta, por qué se reutiliza f(x), por qué se registra con `observe`). Nada de comentarios que repitan la sintaxis sin explicar ("asigna x a y"). Ejemplos del tono buscado: `x_nuevo = np.clip(x - self.eta * g, self.lo, self.hi)  # paso de gradiente y proyección Π a la caja`.
4. Cada comentario debe ser verdad según el código y el Spec (secciones 5.1, 6.1, 6.2 y 6.3). Si una línea no la entiendes con certeza, NO inventes: léela en el Spec o en `src/common/counter.py`, y si sigue sin quedar claro escribe `# TODO(comentario): <duda>` y repórtalo.
5. Respeta los comentarios y docstrings que ya existen: no los borres ni los reescribas. Si una línea ya tiene comentario, déjalo como está.
6. PROHIBIDO tocar: cualquier token de código, nombres, orden, saltos de línea, sangría, imports, docstrings. No reformatees. Los comentarios no mencionan estudio, sustentación, autores ni este prompt.

REGLAS PARA LAS PRUEBAS (tests/test_gradients.py y tests/test_gd.py)
- Una línea de comentario encima de cada `def test_...` (o de cada grupo parametrizado) que diga qué propiedad verifica y por qué importa. En pruebas de más de 10 líneas, comentarios por bloque (preparación / ejecución / aserciones). NO comentes línea por línea. No toques `tests/test_ea.py` ni `tests/test_pso.py`.
- Misma regla de no cambiar nada que no sea comentario.

ARCHIVOS PERMITIDOS: src/part1/functions.py, src/part1/gd.py, tests/test_gradients.py, tests/test_gd.py, docs/MEMORIA.md y el prompt guardado. Nada más (ni ea.py, pso.py, configs, Spec, blog).

VERIFICACIÓN (ejecútala y pega las salidas)
1. Equivalencia exacta del código: para cada uno de los 4 archivos compara el árbol sintáctico antes (`git show HEAD:<ruta>`) y después (archivo en disco) con `ast.dump(ast.parse(texto))`. Deben ser IGUALES. Pega el resultado por archivo.
2. `python -m pytest -q` completo: debe dar exactamente lo mismo que antes de empezar (corre la suite ANTES de editar y anota passed/skipped/failed).
3. Que no se perdió el formato: el número de saltos `\n` sin `\r` en cada archivo debe ser el mismo antes y después. `git diff --stat` debe mostrar solo cambios en esos 4 archivos y en MEMORIA.
4. Ninguna línea nueva supera 100 caracteres: script que lo compruebe solo sobre las líneas añadidas por el diff.
5. Busca si algún script de `alucinaciones/evidencias/` o `scripts/` modifica o lee `gd.py` o `functions.py` por texto (por ejemplo para pruebas de mutación); si existe, repórtalo sin cambiarlo.
6. `revisor-calidad` y `verificador-matematico`: informe de comentarios inexactos o dudosos, con la línea. Corrige los que encuentren y repite el paso 1.
7. Si el cazador-alucinaciones o los revisores hallan comentarios que contradecían el código, anótalos como candidatos en `alucinaciones/registro.md` con el siguiente número libre.
8. Actualiza `docs/MEMORIA.md` con una fila nueva arriba en la bitácora: "Comentarios línea a línea en functions.py y gd.py y por prueba en test_gradients.py y test_gd.py; solo comentarios, AST idéntico, suite sin cambios". Sin commit: lo hago yo desde GitHub Desktop.

REPORTE FINAL: líneas de código comentadas por archivo, resultado del AST por archivo, conteo de pytest antes y después, comentarios dudosos o `TODO(comentario)`, y cualquier hallazgo del revisor o verificador.
```

## Estado inicial (orquestador)
Rama `parte1-optimizacion-numerica`, último commit `0e8874d`. Línea base: `pytest -q` → 1297 passed, 3 skipped, 0 failed
(Windows). Los 4 archivos están en **LF** (0 CRLF), no en CRLF como supone el prompt: el control "mismo número de `\n` sin `\r`"
se aplica como "0 CRLF antes y después, y la diferencia de LF = líneas añadidas por el diff". Punto 5: ningún script de
`alucinaciones/evidencias/` ni de `scripts/` lee `gd.py` o `functions.py` por texto; `tests/test_no_network.py` los lee con
`ast.parse` (los comentarios no le afectan).

## Ronda 1 — `implementador` (12-oct-2026)

```text
CONTEXTO DEL ORQUESTADOR
Repositorio: C:\Repositorios\Trabajo1_Redes_Neuronales, rama parte1-optimizacion-numerica. NO hagas commits, NO cambies de rama.
Python: .venv\Scripts\python.exe (3.12). Línea base: .venv\Scripts\python.exe -m pytest -q → 1297 passed, 3 skipped, 0 failed.
Los 4 archivos de esta tarea están en finales de línea LF (no CRLF). Edítalos SOLO con la herramienta Edit, por bloques (una
función o clase por edición), nunca reescribiendo el archivo completo ni con scripts; no conviertas finales de línea.
Archivos que puedes modificar: src/part1/functions.py, src/part1/gd.py, tests/test_gradients.py, tests/test_gd.py. NADA más
(docs/MEMORIA.md y el registro los actualiza el orquestador).
Si un comentario no lo puedes escribir con certeza, no inventes: escribe `# TODO(comentario): <duda>` y repórtalo.

ENCARGO
Añade SOLO comentarios (el comportamiento no cambia) para que cada línea de código de src/part1/functions.py y src/part1/gd.py
lleve un comentario breve en español que diga qué hace, y que las pruebas de tests/test_gradients.py y tests/test_gd.py tengan un
comentario por prueba. Lee antes docs/spec/SPEC.md §5.1, §6.1, §6.2 y §6.3 y src/common/counter.py.

REGLAS PARA src/part1/functions.py y src/part1/gd.py (literales del encargo humano)
1. Todas las líneas con código ejecutable llevan comentario: imports, `class`, `def`, decoradores, asignaciones, `if/elif/else`, `for/while`, `try/except`, `return`, `raise`, `with`. Las líneas en blanco y las que solo cierran un paréntesis, corchete o llave NO llevan comentario; en una instrucción partida en varias líneas, comenta cada línea que aporte (cada argumento relevante).
2. Formato: comentario al final de la línea con dos espacios antes de `#`. Si la línea más el comentario superaría 100 caracteres, pon el comentario en la línea de arriba, con la misma sangría. No dejes ninguna línea NUEVA de más de 100 caracteres (las líneas que ya pasaban de 100 no se tocan ni se reformatean).
3. Contenido: qué hace la línea, en pocas palabras y con el símbolo matemático cuando aplique (η, ∇f, Π, x*, β, c). Añade el "para qué" solo cuando no sea obvio (por ejemplo, por qué se recorta, por qué se reutiliza f(x), por qué se registra con `observe`). Nada de comentarios que repitan la sintaxis sin explicar ("asigna x a y"). Ejemplos del tono buscado: `x_nuevo = np.clip(x - self.eta * g, self.lo, self.hi)  # paso de gradiente y proyección Π a la caja`.
4. Cada comentario debe ser verdad según el código y el Spec (secciones 5.1, 6.1, 6.2 y 6.3). Si una línea no la entiendes con certeza, NO inventes: léela en el Spec o en `src/common/counter.py`, y si sigue sin quedar claro escribe `# TODO(comentario): <duda>` y repórtalo.
5. Respeta los comentarios y docstrings que ya existen: no los borres ni los reescribas. Si una línea ya tiene comentario, déjalo como está.
6. PROHIBIDO tocar: cualquier token de código, nombres, orden, saltos de línea, sangría, imports, docstrings. No reformatees. Los comentarios no mencionan estudio, sustentación, autores ni este prompt.
Aclaración del orquestador: las líneas DENTRO de un docstring no son código y no llevan comentario.

REGLAS PARA LAS PRUEBAS (tests/test_gradients.py y tests/test_gd.py)
- Una línea de comentario encima de cada `def test_...` (o de cada grupo parametrizado) que diga qué propiedad verifica y por qué importa. En pruebas de más de 10 líneas, comentarios por bloque (preparación / ejecución / aserciones). NO comentes línea por línea. No toques `tests/test_ea.py` ni `tests/test_pso.py`.
- Misma regla de no cambiar nada que no sea comentario.
Aclaración del orquestador: si la prueba lleva decoradores (@pytest.mark.parametrize), el comentario va encima del primer
decorador, no entre el decorador y el def.

VERIFICACIÓN (ejecútala tú y pega las salidas reales)
1. AST: para cada uno de los 4 archivos, ast.dump(ast.parse(texto)) de `git show HEAD:<ruta>` frente al archivo en disco: IGUALES.
2. .venv\Scripts\python.exe -m pytest -q completo: 1297 passed, 3 skipped, 0 failed.
3. Finales de línea: 0 CRLF en los 4 archivos, y la diferencia de LF de cada archivo = número de líneas añadidas por git diff.
   git diff --stat: solo esos 4 archivos (más alucinaciones/prompts/comentarios-T1.1-T1.3.md, que es del orquestador).
4. Script que compruebe que ninguna línea AÑADIDA por el diff supera 100 caracteres.
5. Cuenta, por archivo, las líneas de código (no blancas, no docstring, no solo cierre de paréntesis) y cuántas quedaron sin
   comentario (debe ser 0 en functions.py y gd.py); lista las excepciones si las hay.
ENTREGA: salida real de cada verificación, conteo de líneas comentadas por archivo, lista de `TODO(comentario)` y dudas.
```

Resultado: implementador ronda 1 entregado. Comprobado por el orquestador: AST idéntico en los 4 archivos; 0 CRLF; LF
132→140, 215→229, 220→250, 846→937 (= líneas añadidas netas); 0 líneas añadidas > 100; pytest 1297 passed, 3 skipped (según el
implementador). Sin TODO(comentario).

## Ronda 1 — `revisor-calidad` (12-oct-2026)

```text
Revisión de EXACTITUD de comentarios (tarea de legibilidad T1.1–T1.3). NO modifiques ningún archivo del repo.
Repositorio: C:\Repositorios\Trabajo1_Redes_Neuronales, rama parte1-optimizacion-numerica. Python: .venv\Scripts\python.exe.
Se añadieron SOLO comentarios (AST idéntico a HEAD, ya comprobado) en src/part1/functions.py, src/part1/gd.py,
tests/test_gradients.py y tests/test_gd.py. Ve el cambio con `git diff` de esos 4 archivos. Referencias: docs/spec/SPEC.md §5.1,
§6.1, §6.2 y §6.3; src/common/counter.py; src/common/config.py.
Reglas que debían cumplir (resumen del encargo humano): un comentario breve en español por CADA línea de código de functions.py y
gd.py (imports, class, def, asignaciones, if, for/while, try/except, return, raise); al final de la línea con dos espacios antes de
`#`, o en la línea de arriba si superaría 100 caracteres; dice qué hace la línea con el símbolo matemático cuando aplique (η, ∇f, Π,
x*, β, c) y el "para qué" solo cuando no es obvio; nada de repetir la sintaxis; sin mencionar estudio, sustentación, autores ni el
prompt; comentarios y docstrings previos intactos. En las pruebas: un comentario encima de cada test (o del primer decorador) que
diga qué propiedad verifica y por qué importa, y comentarios por bloque en pruebas de más de 10 líneas; nada línea por línea.

REVISA, comentario por comentario:
1. ¿Es EXACTO respecto a su línea? (¿describe lo que la línea hace de verdad?, ¿el símbolo/fórmula/número es correcto?, ¿el "para
   qué" es cierto según el código y el Spec?). Comprueba en el código las afirmaciones no triviales (conteos, por qué se usa observe,
   cuándo se lanza BudgetExhausted, qué pasa en el borde, qué valida cada función).
2. ¿Hay comentarios que solo repiten la sintaxis, ambiguos, demasiado largos o que mencionan cosas prohibidas?
3. En las pruebas: ¿el comentario describe la propiedad que la prueba REALMENTE comprueba (no más)? ¿Está encima del primer
   decorador?
4. Comprueba con un script: líneas de código de functions.py y gd.py sin comentario (debe ser 0); líneas añadidas > 100
   caracteres (debe ser 0); comentarios previos y docstrings idénticos a HEAD.
ENTREGA: dictamen APRUEBA / NO APRUEBA; lista de comentarios INEXACTOS (bloqueantes) y dudosos o mejorables (menores), cada uno
con archivo:línea, el texto actual, por qué es inexacto y el texto corregido propuesto; salida de los scripts.
```

## Ronda 1 — `verificador-matematico` (12-oct-2026)

```text
Verificación matemática de COMENTARIOS (tarea de legibilidad T1.1–T1.3). NO modifiques ningún archivo del repo; scripts solo
fuera del repo, con PYTHONPYCACHEPREFIX en una carpeta temporal fuera del repo.
Repositorio: C:\Repositorios\Trabajo1_Redes_Neuronales, rama parte1-optimizacion-numerica. Python: .venv\Scripts\python.exe.
Se añadieron solo comentarios (AST idéntico a HEAD) en src/part1/functions.py y src/part1/gd.py (y en tests/test_gradients.py y
tests/test_gd.py). Ve el cambio con `git diff`. Referencias: docs/spec/SPEC.md §6.1 (funciones), §6.2 (conteo), §6.3 (GD y Armijo,
incluidas las líneas [PENDIENTE] de T1.2 y T1.3); src/common/counter.py.

Verifica que cada comentario de una línea con FÓRMULA o afirmación matemática es correcto:
(a) functions.py: f y ∇f de Rosenbrock y Rastrigin (términos, índices, factores 100/400/200/2/10/20π/2π, dominio, x*, f*), y lo que
    los comentarios dicen de cada término del gradiente (qué índice, qué condición i < n / i > 1).
(b) gd.py: paso fijo x' = Π(x − η∇f) y proyección Π = recorte a la caja (¿es la proyección euclídea?), condición de Armijo
    f(x') ≤ f(x) − c·⟨∇f, x − x'⟩ y su equivalencia sin recorte con c·η‖∇f‖², signo y rango de "descenso", retroceso η ← β·η, parada
    ‖∇f‖ < tol, conteo (n_f, k por ∇f, eval_equiv = n_f + k·n_grad, f(x0) una sola vez, observe sin costo).
(c) En las pruebas, los comentarios que afirman algo matemático (contracción 0.5^t, ‖g‖ = 2‖x − x*‖, número exacto de
    gradientes, mínimos locales de Rastrigin, cotas de presupuesto): ¿son ciertos?
Si un comentario es falso o impreciso, da archivo:línea, el texto actual, la evidencia (cálculo o script con su salida real) y el
texto corregido propuesto. No inventes constantes; si citas una fuente externa, da URL.
ENTREGA: dictamen por apartado (CUMPLE / NO CUMPLE / OBSERVACIÓN), lista de comentarios a corregir, dictamen global APRUEBA /
NO APRUEBA.
```

Resultado: `revisor-calidad` NO APRUEBA (3 comentarios inexactos en pruebas: test_gd.py:185-186 "+1 si para por presupuesto",
test_gd.py:130-131 "el conteo coincide con las llamadas reales" (falso para f), test_gradients.py:46-47 "sin que ninguna otra
prueba lo notara"; más 11 menores). `verificador-matematico` APRUEBA con 2 observaciones (gd.py:90 "búsqueda lineal ... en la
dirección −∇f" no es una recta con proyección; test_gd.py:185 igual que el revisor). Fuera de alcance (comentarios previos, no
se tocan por la regla 5): gd.py:69, test_gd.py:465 y test_gd.py:604-605.

## Ronda 2 — `implementador` (12-oct-2026, mismo agente, vía SendMessage)

```text
Ronda 2 de la tarea de comentarios (correcciones de revisor-calidad y verificador-matematico). Mismas reglas que en la ronda 1:
solo comentarios, solo con Edit por bloques, sin tocar código, docstrings ni comentarios que ya existían en HEAD, ninguna línea
añadida > 100 caracteres, sin commits. Corrige SOLO estos comentarios (los números de línea son los del archivo actual):

INEXACTOS (obligatorio)
1. tests/test_gd.py:185-186 → "# Frames: forma de §5.1, uno por punto aceptado incluido x0 (n_grad frames si para por ‖∇f‖ < tol,
   n_grad + 1 si para por presupuesto); "best" = mejor punto visto hasta ese frame, aunque el GD oscile o diverja." (pártelo en
   las líneas de comentario que hagan falta).
2. tests/test_gd.py:130-131 → "# Paso fijo: observe evalúa f sin cobrarla (n_f = 0 aunque f sí se llama) y cada ∇f cuesta k;"
   / "# n_grad coincide con las llamadas reales a grad."
3. tests/test_gradients.py:46-47 → que no diga que ninguna otra prueba lo notaría; p. ej. "# es la prueba que cubre todo el
   dominio: un gradiente mal derivado arruinaría el GD."
MENORES (aplícalos)
4. tests/test_gd.py:266 → "# Semillas distintas (1 y 2) dan puntos iniciales distintos: el x0 depende de la semilla."
5. tests/test_gd.py:581 → "# Las llamadas reales a f son n_f cobradas + 1 observe de x0: no hay evaluaciones ocultas."
6. tests/test_gd.py:592-593 → "acepta con un ensayo" por "acepta casi siempre con un solo ensayo".
7. tests/test_gd.py:646 → "los conteos cuadran" por "n_f, n_grad y eval_equiv son coherentes con los ensayos".
8. src/part1/gd.py:90 → "# búsqueda con retroceso sobre el arco proyectado Π(x − η ∇f) (sin recorte, la recta en −∇f)"
   (si no cabe al final de la línea, en la línea de arriba).
9. src/part1/gd.py:85 → "... y constante c de Armijo".
10. src/part1/gd.py:29 → "# no es número real (o es bool)".
11. src/part1/gd.py:205 → "# variante recibida".
12. src/part1/functions.py:46 → "# solo lectura: evita modificar el dominio por accidente".
13. src/part1/functions.py:47 → que no use una "v" sin definir (nombra la variable real del código).
14. src/part1/functions.py:119 → fórmula completa "10n + Σ [x_i² − 10 cos(2π x_i)]" (en la línea de arriba si no cabe).
Antes de escribir 13 y 14, lee la línea real para que el comentario use los nombres que de verdad aparecen.
Después repite y pega: AST idéntico a HEAD en los 4 archivos; 0 CRLF; ninguna línea añadida > 100; 0 líneas de código sin
comentario en functions.py y gd.py; .venv\Scripts\python.exe -m pytest -q (1297 passed, 3 skipped).
```

Resultado: ronda 2 del implementador aplicada (14 correcciones; AST idéntico; 0 CRLF; 0 líneas añadidas > 100; 1297 passed,
3 skipped).

## Ronda 2 — `revisor-calidad` (12-oct-2026, mismo agente, vía SendMessage)

```text
Ronda 2 de la revisión de exactitud de comentarios (ya revisaste la ronda 1 y dictaminaste NO APRUEBA con 3 inexactos y 11
menores). NO modifiques archivos. El implementador aplicó tus 3 bloqueantes y tus menores, más la reformulación de gd.py:90 que
pidió el verificador-matematico ("búsqueda con retroceso sobre el arco proyectado Π(x − η ∇f) (sin recorte, la recta en −∇f)").
Cuatro comentarios pasaron a la línea de arriba por longitud (gd.py:29, gd.py:85, gd.py:205, functions.py:119). Los comentarios
previos de HEAD (gd.py:69, test_gd.py:465 y 604-605) quedan sin tocar a propósito (regla 5 del encargo).
Verifica con `git diff` que cada corrección es exacta respecto a su línea y que no introdujo comentarios nuevos inexactos; repite
tus scripts (AST idéntico, docstrings y comentarios previos idénticos, 0 líneas de código sin comentario en functions.py y gd.py,
0 líneas añadidas > 100, comentario encima del primer decorador en cada test).
ENTREGA: dictamen APRUEBA / NO APRUEBA, hallazgos nuevos con archivo:línea si los hay, y la salida de los scripts.
```

Resultado: `revisor-calidad` APRUEBA la ronda 2 (sin hallazgos nuevos). Candidato H-32 anotado en registro.md. Cierre hecho por el orquestador.
