# Blog del reporte — guía para redactar

El reporte es **una sola entrada de blog** (`docs/index.md`) que une las secciones de `secciones/`. Cada equipo escribe
**solo sus archivos** de `secciones/` (el comentario del inicio de cada archivo dice quién es responsable y qué exige el enunciado).

## Ver el blog mientras se escribe

```bash
.venv\Scripts\mkdocs serve -f blog/mkdocs.yml
```
Abre <http://127.0.0.1:8000> y se recarga al guardar. Antes de hacer commit:

```bash
.venv\Scripts\mkdocs build --strict -f blog/mkdocs.yml
```
Si falla, el mensaje dice qué regla se rompió. **No se fusiona un PR con el build en rojo.**

## Sintaxis

| Qué | Cómo se escribe |
|---|---|
| Ecuación en línea | `$f(\mathbf{x})$` |
| Ecuación en bloque | `$$ ... $$` en líneas aparte |
| Figura (APA) | ver abajo |
| Tabla (APA) | igual que la figura, con `::: tabla <id>` y una tabla Markdown dentro |
| Citar una figura o tabla | `[[fig:<id>]]` o `[[tab:<id>]]` → se convierte en "Figura N" / "Tabla N" con enlace |
| Cita entre paréntesis | `[@kennedy1995]` → (Kennedy & Eberhart, 1995) |
| Cita narrativa | `@storn1997 propusieron…` → Storn & Price (1997) propusieron… |
| Varias citas / página | `[@clerc2002; @shi1998]`, `[@dantzig1954, p. 395]` |
| Nota para el equipo (no se publica) | `<!-- … -->` (las citas dentro de comentarios no cuentan) |

Figura (la numeración es automática; **título y fuente son obligatorios**):

```text
::: figura convergencia-rastrigin-2d
Título: Convergencia en Rastrigin 2D (mediana e intervalo intercuartílico de 30 corridas)
Fuente: Elaboración propia a partir de results/data/part1/summary.json.
![Curvas de convergencia](figures/convergencia_rastrigin_2d.png)
:::
```
- Las imágenes van en `docs/figures/` y las genera el código (`python run.py figures`): **no se editan a mano**.
- Para una figura interactiva de Plotly: dentro del bloque, `incluir: figures/<archivo>.html`.
- El `id` usa minúsculas, números y guiones.

## Reglas que el build hace cumplir (requisitos del enunciado)
1. Toda figura y tabla tiene **número, título y fuente** (formato APA 7).
2. Toda figura y tabla **se cita en el texto** — una figura huérfana hace fallar el build.
3. Una referencia `[[fig:…]]` a algo que no existe hace fallar el build.
4. Toda cita está en `references.bib`; la lista de referencias se arma sola **con las obras citadas** (APA 7 vía pandoc + `apa.csl`).

## Bibliografía (`references.bib`)
- **Nunca** escribir una referencia de memoria (ni pedírsela a una IA y copiarla): obtener el BibTeX del DOI
  (`https://doi.org/<doi>` con `Accept: application/x-bibtex`) y verificarlo con
  `alucinaciones/evidencias/H-bib_verificacion_doi.py` (agregar la referencia a su lista). Ver H-22.
- Clave = apellido del primer autor + año, en minúsculas (`kennedy1995`). Toda entrada lleva `doi`.
- Una cita inventada o mal atribuida se penaliza: cualquier sospecha va al registro de la cacería.

## Notas técnicas
- `mkdocs` está fijado en **1.6.x**: MkDocs 2.0 elimina los plugins y hooks y rompería `hooks/reporte.py`.
- El hook (`hooks/reporte.py`) tiene pruebas en `tests/test_blog.py`.
- Paleta: `src/viz/paleta.py` es la fuente única de colores (validada para daltonismo); `docs/stylesheets/ds.css` la sigue. Design System: skill `apple-design`.
