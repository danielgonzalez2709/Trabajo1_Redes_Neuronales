# Caracterización de los datos — Bloque 1 (coordenadas de las 47 capitales)

Tarea T2.1 del PLAN. Explica qué forma tienen los datos de cada fuente, cómo se unen y por qué el producto
`data/processed/cities.csv` cumple el Spec §7.2 (Bloque 1) y el contrato §5.3.

- Todas las cifras de este documento salen de `scripts/caracterizar_bloque1.py --fecha 2026-10-07`, que lee solo
  `data/raw/` y `data/processed/` y escribe `data/processed/caracterizacion_bloque1.json`.
- Las URL y las fechas de consulta están en `data/fuentes.md`.
- **Decisión del equipo (2026-10-08):** el **NGMEP 202603** es la fuente principal de las coordenadas de
  `cities.csv` (Spec §7.2). **IGR Poblaciones** pasa a ser el contraste. Antes de esa fecha, IGR fue la fuente
  provisional, porque la descarga del NGMEP exige reCAPTCHA.

---

## 1. Linaje (raw → processed)

```
 DESCARGA MANUAL (reCAPTCHA)                       INTERNET (solo scripts/descargar_datos.py --bloque 1)
 ───────────────────────────                       ─────────────────────────────────────────────────────
 CNIG Centro de Descargas                          api-features.ign.es/nuc ──► data/raw/ign_nuc_capitales_provincia_2026-10-07.json
        │                                          api-features.ign.es/administrativeunit ──► data/raw/ign_provincias_2026-10-07.geojson.gz
        ▼                                          ine.es 26codmun.xlsx ──► data/raw/ine_26codmun_2026-10-07.xlsx
 data/raw/BD_Municipios-Entidades/                 nominatim.openstreetmap.org ──► data/raw/nominatim_capitales_2026-10-07.json
 (NGMEP 202603: 5 CSV + MDB + Memoria)                (consultas construidas con los nombres del crudo IGR)
        │  FUENTE PRINCIPAL (lat, lon, CODIGOINE,            │  CONTRASTE Y CONTROL (código IGR, polígonos provinciales,
        │  nombre, provincia, ORIGENCOOR)                    │  nombre oficial INE, punto OSM)
        └──────────────────────┬─────────────────────────────┘
                               ▼
        scripts/construir_cities.py --fecha 2026-10-07 [--fecha-ngmep 2026-10-07]   (sin red;
        utilidades comunes en scripts/comun_bloque1.py, donde también se documenta el orden del pipeline)
                               │
          ┌────────────────────┼───────────────────────────────┐
          ▼                    ▼                               ▼
 data/processed/cities.csv   data/processed/cities_verificacion.csv   data/processed/cities_mapa_control.png
 (contrato §5.3)             (evidencia por capital, incluye lat_igr/lon_igr/dist_igr_km)
                               │
                               ▼
        scripts/validar_cities_ngmep.py (sin red) ──► data/processed/cities_contraste_ngmep.csv
        (valida cities.csv contra el NGMEP crudo; mide IGR → NGMEP leyendo IGR del crudo)
                               │
                               ▼
        scripts/caracterizar_bloque1.py        ──► data/processed/caracterizacion_bloque1.json

 Pruebas (sin red):
   tests/test_cities.py        contrato §5.3 y aceptación del Spec §7.2
   tests/test_cities_ngmep.py  procedencia NGMEP y contraste IGR → NGMEP (X = 2,5 km)
   tests/test_geo.py           punto en polígono, variantes de nombre y haversine
   tests/test_comun_bloque1.py la falta de OSM es un error, lectura del NGMEP y ruta_unica
```

**Claves de unión entre fuentes:**

| Unión | Clave | Comentario |
|---|---|---|
| NGMEP `ENTIDADES` ↔ IGR `nuc` | `CODIGOINE` = `codine` (11 dígitos INE, `PPMMMECESNN`) | Coinciden en las 47 capitales; el script se detiene si no coinciden. |
| IGN `nuc` ↔ INE 26codmun | `codine[:5]` = `CPRO`+`CMUN` | Municipio al que pertenece el núcleo. |
| IGN `nuc` ↔ límites IGN | `cpro` = `nationalcode[4:6]` | `nationalcode` = `34` + CCAA(2) + CPRO(2) + `00000`. |
| NGMEP `PROVINCIAS` → `MUNICIPIOS` → `ENTIDADES` | `COD_PROV` + `CAPITAL` = `NOMBRE_ACTUAL` → `COD_INE_CAPITAL` = `CODIGOINE` | Es el criterio de la Memoria para encontrar la entidad capital; de ahí salen las coordenadas de `cities.csv`. |
| NGMEP `ENTIDADES` ↔ límites IGN | `COD_PROV` = `nationalcode[4:6]` | Para la comprobación punto-en-provincia. |
| Nominatim ↔ IGN | nombre (texto) | Unión débil por nombre, por eso Nominatim solo sirve de control. Se usa la primera parte de un nombre bilingüe "A/B". |

---

## 2. Fuentes

### 2.1 NGMEP — Nomenclátor Geográfico de Municipios y Entidades de Población (IGN), versión 202603

- **Qué es.** El inventario oficial de municipios y entidades de población con coordenadas. Lo publica el
  Registro Central de Cartografía del IGN; la Memoria tiene fecha de actualización 31-mar-2026.
- **Fuentes del propio NGMEP (según su Memoria).** Registro de Entidades Locales (REL), Nomenclátor del INE,
  boletines oficiales, Líneas Límite del IGN, IGR Poblaciones y la Base Topográfica Nacional (BTN).
- **Formato.** Cinco CSV:
  - separador `;`;
  - codificación **cp1252**: `ENTIDADES.csv` contiene el byte 0x92, que en cp1252 es `’` y en latin-1 sería un
    carácter de control;
  - fin de línea CRLF;
  - **coma decimal**;
  - booleanos escritos como `VERDADERO`/`FALSO`.
- **Coordenadas.** Geográficas, en grados decimales. ETRS89 en la península y Baleares; REGCAN95 en Canarias.
  Según la Memoria, el punto es un centroide "lo más centrado posible en el núcleo poblacional".
- **Papel en el pipeline.** **Fuente principal** de `cities.csv` (decisión del equipo, 2026-10-08). De aquí salen
  `lat`, `lon` (redondeadas a 6 decimales), `capital`, `provincia` y el `CODIGOINE` y el `ORIGENCOOR` que se
  copian en `nota`.

| CSV | Una fila = | Filas | Cols. | Columnas relevantes (tipo; ejemplo real) | Nulos |
|---|---|---|---|---|---|
| `PROVINCIAS.csv` | provincia o ciudad autónoma | 52 | 5 | `COD_PROV` (texto de 2 dígitos; `01`), `PROVINCIA` (texto; `Araba/Álava`), `CAPITAL` (texto; `Vitoria-Gasteiz`) | ninguno |
| `MUNICIPIOS.csv` | municipio | 8 132 | 18 | `COD_INE` (texto de 11; `01001000000`), `NOMBRE_ACTUAL` (`Alegría-Dulantzi`), `COD_INE_CAPITAL` (texto de 11; `01001000101`), `LONGITUD_ETRS89_REGCAN95` (decimal con coma; `-2,512507724`), `LATITUD_ETRS89_REGCAN95` (`42,84045247`), `ORIGENCOOR` (`Detección automática`) | ninguno |
| `ENTIDADES.csv` | unidad poblacional (municipio, capital de municipio, entidad colectiva, entidad singular, núcleo u otra entidad, diseminado) | 153 950 | 15 | `CODIGOINE` (único en las 153 950 filas), `NOMBRE`, `TIPO`, `INEMUNI` (5 dígitos), coordenadas, `ORIGENCOOR`, `SUPRIMIDA_INE`, `DISCREPANTE_INE` | ninguno |
| `EATIMS.csv` | entidad local menor (EATIM) | 3 676 | 13 | `CODINSCRIP` (`4010001`), `DENOMINACION` (`Adana`), `CODINE` (`01053000100`), coordenadas | ninguno |
| `COMJURIDIC.csv` | comunidad jurisdiccional | 82 | 13 | `NOMBRE_ACTUAL`, `MUNICIPIOS` (lista separada por `;` y entre comillas), `idINES` | `ORIGENCOOR`, `ALTITUD` y `ORIGENALTITUD` vacíos en las 82 filas |

**Detalle de `ENTIDADES.csv`.**

- Valores de `TIPO`:

  | `TIPO` | Filas |
  |---|---|
  | Municipio | 8 132 |
  | Capital de municipio | 8 132 |
  | Entidad colectiva | 4 904 |
  | Entidad singular | 62 084 |
  | Otras entidades | 29 459 |
  | Diseminado | 41 239 |

- Valores de `ORIGENCOOR`:

  | `ORIGENCOOR` | Filas |
  |---|---|
  | Mapa | 55 066 |
  | Coordinado_IGR Poblaciones | 43 739 |
  | Detección automática | 42 064 |
  | Investigación | 10 528 |
  | No disponible | 1 272 |
  | GPS. PNRGM | 1 116 |
  | En estudio | 162 |
  | GPS | 2 |
  | MDT | 1 |

- `SUPRIMIDA_INE = VERDADERO`: 2 filas. `DISCREPANTE_INE = VERDADERO`: 11 filas.
- La entidad de cada capital es la fila de `TIPO = "Capital de municipio"`. La Memoria (Anexo I) la define como la
  "Entidad en la que está ubicado el Ayuntamiento del municipio".
- Las 47 capitales tienen `SUPRIMIDA_INE = FALSO` y `DISCREPANTE_INE = FALSO`.
- `ORIGENCOOR` de las 47 capitales:

  | `ORIGENCOOR` | Capitales |
  |---|---|
  | Detección automática | 38 |
  | Investigación | 6 |
  | Coordinado_IGR Poblaciones | 2 |
  | GPS. PNRGM | 1 |

  - Las 9 capitales cuya coordenada difiere de IGR tienen `ORIGENCOOR` = "Detección automática" en 8 casos y
    "Coordinado_IGR Poblaciones" en 1 (Valladolid).
  - Así que "Detección automática" **no** distingue a esas 9: también la tienen 30 de las 38 capitales idénticas.

**Diferencias Memoria ↔ CSV** (no afectan al Bloque 1):

- La Memoria nombra `SUPERFICIE_OFICIAL`; el CSV usa `SUPERFICIE`.
- En `COMJURIDIC`, la Memoria describe `PROVINCIA` como un número, pero el CSV trae un nombre (`Guipúzcoa`).
- La Memoria no documenta la columna `COD_GEOGRAFICO`.
- La Memoria habla de 12 capitalidades + 1 entidad discrepantes; el CSV trae 11 filas con `DISCREPANTE_INE = VERDADERO`.

### 2.2 IGR Poblaciones — colección `nuc` (IGN, API OGC Features)

- **Qué es.** Los núcleos de población de la Información Geográfica de Referencia del IGN.
  - Metadato `spaign_IGR_Poblaciones`, con `dateStamp` 2026-01-19.
  - Especificación: `20251216_IGN_especificaciones_IGR-PO_v2024`.
- **Una fila = un núcleo** (en un caso, una entidad singular), con geometría y punto representativo. Solo se
  descargan los atributos (`skipGeometry=true`).
- **Volumen del crudo.**
  - Se hicieron 32 consultas, una por cada código de capitalidad posible con el 3.er dígito = 1 ("capital de
    provincia").
  - Solo 4 consultas devolvieron registros, 50 en total (50 provincias):

    | `capital` | Significado | Registros |
    |---|---|---|
    | `001100` | provincia + municipio | 34 |
    | `011100` | CC. AA. + provincia + municipio | 14 |
    | `011110` | además EATIM | 1 (Vitoria-Gasteiz) |
    | `111100` | además nación | 1 (Madrid) |

  - Hay 14 columnas y ningún nulo.
- **Columnas relevantes** (ejemplo real: Cádiz):

  | Columna | Tipo | Ejemplo |
  |---|---|---|
  | `codine` | texto de 11 dígitos | `11012000101` |
  | `nombre` | texto | `Cádiz` |
  | `cpro` | entero | 11 |
  | `tipo` | texto | `NUCL` (49) o `ENSI` (1, Murcia) |
  | `capital` | texto de 6 dígitos | `001100` |
  | `latitud`, `longitud` | float | 36.52959441, -6.292954632 |
  | `fecha` | fecha-hora | de 2025-10-16 a 2025-12-05 |

- **Coordenadas.** ETRS89, compatible con WGS84. Según la especificación IGR-PO, el punto es la "localización
  puntual que representa el centro de la población" (no el centroide del municipio).
- **Codificación.** JSON en UTF-8.
- **Papel en el pipeline.** **Contraste** (desde 2026-10-08):
  - el código `codine` debe coincidir con el `CODIGOINE` del NGMEP;
  - la distancia IGR → NGMEP debe ser ≤ 2,5 km;
  - el nombre de las consultas a Nominatim sale de aquí.

  Antes del 2026-10-08 fue la fuente provisional de las coordenadas.

### 2.3 Límites provinciales — colección `administrativeunit` (IGN, INSPIRE AU)

- **Qué es.** Las unidades administrativas oficiales del IGN (Líneas Límite), filtradas con
  `nationallevelname=Provincia`.
- **Una fila = una provincia** con su geometría. Hay 53 filas:
  - 50 provincias;
  - Ceuta y Melilla;
  - "Territorios no asociados a ninguna provincia".
- **Columnas.** 8 de atributos, más una geometría `MultiPolygon` en las 53 filas, con 1 193 428 vértices en total.

  | Columna | Ejemplo |
  |---|---|
  | `nationalcode` | `34160100000` |
  | `nameunit` | `Araba/Álava` |
  | `nationallevelname` | `Provincia` |

- **Nulos.** `codnut3` vacío en las 53 filas; `codnut1` y `codnut2` vacíos en 1 fila.
- **CRS.** Lon/lat en grados (GeoJSON).
- **Crudo.** UTF-8, comprimido con gzip: 13 188 834 bytes. El servidor marca la respuesta con `timeStamp`
  2026-10-08T03:36:02Z en UTC, que es el 2026-10-07 en hora local.
- **Papel en el pipeline.**
  - Comprobación punto-en-provincia, con la regla par-impar sobre todos los vértices.
  - Control de que el nombre de provincia del NGMEP coincide con `nameunit` (coincide en las 47).
  - Mapa de control.

### 2.4 INE — Relación de municipios y códigos a 1 de enero de 2026 (`26codmun.xlsx`)

- **Una fila = un municipio.** 8 132 filas repartidas en 52 hojas (una por provincia).
- **Columnas.** 4, sin nulos.

  | Columna | Ejemplo |
  |---|---|
  | `CPRO` | `01` |
  | `CMUN` | `051` |
  | `DC` | `3` |
  | `NOMBRE` | `Agurain/Salvatierra` |

- **Particularidades.**
  - El INE pospone el artículo: escribe `Coruña, A`.
  - Algunos nombres de provincia invierten el orden bilingüe respecto al IGN: el INE escribe `Alicante/Alacant` y
    el IGN `Alacant/Alicante`.
- **Papel en el pipeline.** Nombre oficial del municipio y comprobación del código INE, que se usan en la
  verificación de nombres bilingües y homónimos.

### 2.5 OpenStreetMap / Nominatim

- **Una fila = una consulta** con hasta 3 resultados. Hay 52 consultas:
  - 47 con `countrycodes=es`, una por capital;
  - 5 sin filtro de país, para los homónimos.
- **Resultados por consulta.** 3 resultados: 17 consultas; 2 resultados: 31; 1 resultado: 4.
- **Columnas de cada resultado.** `address`, `addresstype`, `boundingbox`, `category`, `display_name`,
  `importance`, `lat`, `licence`, `lon`, `name`, `osm_id`, `osm_type`, `place_id`, `place_rank`, `type`.
  - `lat` y `lon` llegan como **texto**.
- **Codificación.** JSON en UTF-8; datos con licencia ODbL.
- **Forma de los datos** (lo relevante para el Spec):
  - En 10 de las 47 consultas con filtro de país, el primer resultado **no es la ciudad sino la provincia**:

    | `addresstype` del primer resultado | Consultas |
    |---|---|
    | `city` | 33 |
    | `municipality` | 4 |
    | `state_district` | 7 |
    | `province` | 3 |

    Por eso el pipeline elige el primer resultado de tipo `city`/`town`/`municipality`/`village`.
  - Sin filtro de país, "León" se resuelve en Francia (Lyon) y "Guadalajara" en México. Mérida, Córdoba y Valencia
    se resuelven en España.
- **Papel en el pipeline.** Solo control: el punto OSM debe caer en la misma provincia IGN. Nunca es la fuente de
  las coordenadas.

### 2.6 Producto final: `data/processed/cities.csv`

- **Una fila = una capital de provincia peninsular.** 47 filas, 9 columnas en el orden exacto del contrato §5.3,
  sin nulos.
- **Columnas** (ejemplo real: Vitoria-Gasteiz):

  | Columna | Tipo | Ejemplo / contenido |
  |---|---|---|
  | `id` | entero | 0 a 46, ordenado por código INE de provincia; sin cambios respecto a la versión IGR |
  | `capital` | texto | NGMEP `ENTIDADES.NOMBRE`, idéntico al nombre IGR, p. ej. `Vitoria-Gasteiz` |
  | `provincia` | texto | NGMEP `PROVINCIAS.PROVINCIA`, idéntico a `nameunit` del IGN, p. ej. `Araba/Álava` |
  | `lat`, `lon` | decimal con 6 decimales (≈ 0,1 m) | NGMEP: 42.846824, -2.672340 |
  | `fuente` | texto | `IGN - NGMEP 202603 (ENTIDADES.csv, TIPO 'Capital de municipio')` en las 47 filas |
  | `fecha_consulta` | fecha | `2026-10-07` (descarga del NGMEP) en las 47 filas |
  | `verificado_manual` | `true`/`false` | |
  | `nota` | texto | `CODIGOINE`, `ORIGENCOOR` del NGMEP, distancia a IGR, municipio INE, comprobaciones |

- **Rango de coordenadas.**
  - Latitud: de 36.529594 (Cádiz) a 43.462343 (Santander).
  - Longitud: de -8.646859 (Pontevedra) a 2.824786 (Girona).
- **Distancias entre capitales.**
  - El par más cercano está a 43,051 km (Palencia–Valladolid); con las coordenadas IGR eran 42,906 km.
  - El más lejano, a 991,008 km (Cádiz–Girona).
- **Puntos OSM.** La distancia del punto OSM al punto de `cities.csv` tiene mediana 0,58 km y máximo 14,21 km
  (Almería; OSM devuelve el centroide del municipio).
- **`verificado_manual`.** `true` en las 12 capitales de la lista del Spec; `false` en las otras 35, que pasan las
  mismas comprobaciones automáticas pero no requieren verificación manual.
- **CRS y codificación.** ETRS89 (compatible con WGS84); UTF-8; separador `,`; punto decimal.
- **Cambio respecto a la versión IGR.** Cambian 9 coordenadas, a una distancia de entre 0,444 y 2,350 km. Las
  otras 38 son idénticas.

---

## 3. Matriz requisito del Spec → evidencia

| Requisito (Spec §7.2 Bloque 1 / §5.3) | Evidencia | Estado |
|---|---|---|
| 47 filas | `tests/test_cities.py::test_47_filas` | cumple |
| Columnas exactas `id, capital, provincia, lat, lon, fuente, fecha_consulta, verificado_manual, nota` | `test_columnas_exactas_del_contrato` | cumple |
| Ids únicos | `test_ids_unicos_y_consecutivos`, `test_capitales_y_provincias_unicas` | cumple |
| Excluidas Palma, Las Palmas de G. C., Santa Cruz de Tenerife, Ceuta y Melilla | `test_sin_capitales_excluidas` (por nombre y provincia) y `test_coordenadas_en_peninsula` (caja envolvente) | cumple |
| Fuente primaria IGN, Nomenclátor de Municipios y Entidades (NGMEP) | `test_coordenadas_iguales_a_ngmep` (lat/lon = NGMEP a 6 decimales), `test_fuente_y_fecha_ngmep` (`fuente` contiene "NGMEP 202603"; `fecha_consulta` 2026-10-07), `test_codigo_ine_es_el_de_la_capital_ngmep`, `test_nombre_y_provincia_coinciden` | cumple |
| Coordenada de la **entidad de población**, no el centroide del municipio | NGMEP `TIPO = "Capital de municipio"` (entidad del Ayuntamiento), comprobado en `test_codigo_ine_es_el_de_la_capital_ngmep` | cumple, con el matiz de §4.2 |
| Contraste con una segunda fuente oficial | `test_contraste_igr_a_ngmep` (IGR → NGMEP ≤ 2,5 km, mismo código INE); `test_umbral_menor_que_10_por_ciento_de_la_separacion_minima`; `cities_contraste_ngmep.csv` | cumple (máx. 2,350 km) |
| Mapa de control con los 47 puntos, cada uno dentro de su provincia | `data/processed/cities_mapa_control.png` (`test_existe_el_mapa_de_control`); `test_cada_punto_dentro_de_su_provincia`, que recalcula con los polígonos crudos del IGN; algoritmo probado en `tests/test_geo.py` | cumple |
| `verificado_manual` completa | `test_verificado_manual_sin_nulos_y_booleano`; `test_verificado_manual_exactamente_en_las_12_de_la_lista` | cumple (12 `true`) |
| Verificación de la lista de nombres bilingües y homónimos | `test_lista_de_verificacion_manual_presente_y_marcada`; método escrito en `nota` | cumple 12/13 (Mérida no es capital de provincia) |
| Descarga única a `data/raw/` con fecha en el nombre | `scripts/descargar_datos.py`; nombres `*_2026-10-07.*` | cumple, salvo la carpeta NGMEP: descarga manual y sin fecha en el nombre, por decisión del equipo; la fecha y los SHA-256 están en `fuentes.md` |
| Registro en `data/fuentes.md` con URL y fecha | `data/fuentes.md` | cumple |
| Procesamiento sin internet | `construir_cities.py`, `validar_cities_ngmep.py` y `caracterizar_bloque1.py` solo leen ficheros | cumple (por inspección; aún no existe `test_no_network.py`) |
| Control OSM obligatorio | `construir_cities.exigir_resultado_osm` y `comun_bloque1.coordenadas_osm` (`tests/test_comun_bloque1.py`): la falta de OSM es un error explícito en los tres scripts | cumple |

---

## 4. Limitaciones y verificaciones solo del agente

1. **Coordenadas NGMEP con origen automático.** 38 de las 47 coordenadas del NGMEP tienen `ORIGENCOOR` =
   "Detección automática"; solo 6 son "Investigación" y 1 es "GPS. PNRGM".
   - En las 9 capitales que difieren de IGR (códigos de provincia 01–09 y Valladolid), el origen es "Detección
     automática" en 8 y "Coordinado_IGR Poblaciones" en Valladolid.
   - El mismo patrón aparece en Palma, que está excluida, y en ninguna otra capital de código 10–50; IGR no publica capital para Ceuta ni Melilla, que son los códigos 51 y 52.
   - Las cifras no permiten saber la causa; queda escalado.
2. **Coordenada de la capital = coordenada del municipio en el NGMEP.** Es un rasgo general del NGMEP, no algo
   propio de las 9 capitales que difieren de IGR:
   - la entidad "Capital de municipio" tiene la misma coordenada (comparada como texto) que su fila
     `TIPO = Municipio` en 8 078 de los 8 132 municipios;
   - ocurre en las 47 capitales de `cities.csv`, tanto en las 38 idénticas a IGR como en las 9 distintas.

   Por eso no sirve para explicar las 9 diferencias, y aquí no se les atribuye causa.

   Tampoco hay un patrón de cercanía al punto OSM. El punto NGMEP queda más cerca en 4 de las 9 (Albacete,
   Alicante, Badajoz y Barcelona) y el de IGR en las otras 5 (Vitoria-Gasteiz, Almería, Ávila, Burgos y
   Valladolid).

   Las cifras salen de `caracterizacion_bloque1.json`:
   - `ngmep.ENTIDADES.csv.capital_de_municipio_igual_a_municipio`;
   - `cities.capitales_con_coordenada_igual_a_su_municipio_ngmep`;
   - `cities.ngmep.distintas_*_mas_cerca_de_osm`.

   Hay una evidencia independiente en `alucinaciones/evidencias/T2.1_capital_vs_municipio.txt`.
3. **Verificación de la lista del Spec: automática y humana.** El agente revisó, caso por caso:
   - `CODIGOINE` del NGMEP = código IGR;
   - nombre oficial y provincia del INE;
   - punto NGMEP y punto OSM dentro del polígono provincial IGN;
   - distancia a IGR ≤ 2,5 km.

   **Confirmación humana:** Jose Miguel Pulgarin, 2026-10-08. Revisó el mapa de control (47 puntos, cada uno en su
   provincia) y las coordenadas de las 12 capitales de la lista sobre un visor de mapas: todas correctas.
   Duda resuelta durante la revisión: Santiago de Compostela no aparece porque es capital de la comunidad autónoma de
   Galicia, no de provincia; la capital de la provincia 15 es A Coruña (`PROVINCIAS.csv` del NGMEP). Es el mismo caso
   que Mérida (Extremadura) en la lista del Spec.
4. **Murcia.** IGR Poblaciones la publica como `ENSI` (entidad singular). El NGMEP la registra como "Capital de
   municipio" (`30030000100`, origen "Investigación") con las mismas coordenadas.
5. **Nominatim** devuelve centroides de municipio o de provincia; por ejemplo, el punto OSM de Almería está a
   14,21 km del punto NGMEP. No es una fuente válida de coordenadas de entidad.
6. **Tamaño del crudo de límites.** Ocupa 13 MB comprimido; falta decidir si se versiona.
7. **Entorno de ejecución.** Las pruebas se ejecutaron con Python 3.11, porque en la máquina no hay 3.12 (el Spec
   pide 3.12). `requirements.txt` aún no existe (es de T0.1).
