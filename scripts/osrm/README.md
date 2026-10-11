# OSRM local para la Parte 2 (T2.2)

Servidor OSRM local con Docker y el extracto de España de Geofabrik. Se monta en local porque el servidor público de
demostración **no admite `exclude=toll`** (Spec §7.2, Bloque 2). Este servidor lo usa T2.3 para descargar las rutas
`rapida` y `sin_peaje` de los 1 081 pares.

Montado y probado el **2026-10-10** (hora local UTC−3; 2026-10-11 02:26–02:42 UTC).

## Qué se usa

| Pieza | Valor |
|---|---|
| Imagen Docker | `ghcr.io/project-osrm/osrm-backend:v26.10.0-debian` |
| Digest (índice multi-arquitectura) | `sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f` |
| Manifiesto linux/arm64 que se usa en el M4 | `sha256:b0045097b8b4ad5e72dce6b900326cd6ee0e98c729709214e674d0472b463f49` (nativo, sin emulación) |
| Versión de OSRM | `osrm-routed --version` → `v26.10.0`. Release de GitHub publicada el 2026-10-01 08:13:32Z; el tag apunta al commit `26a73bd16dd0fba18dc4adc92b5c022bcc40cabe` |
| Perfil | `/opt/car.lua` de la propia imagen (SHA-256 `57778a75…59fa66`). Declara `excludable = {toll}, {motorway}, {ferry}` y `classes = toll, motorway, ferry, restricted, tunnel` |
| Algoritmo | MLD (`osrm-extract` → `osrm-partition` → `osrm-customize`; `osrm-routed --algorithm mld`) |
| Extracto | Geofabrik `europe/spain-261001.osm.pbf`: 1 487 592 334 bytes; md5 `27c3c06719ce8045421b34b530687063`, verificado |
| **Fecha de los datos** | **2026-10-01T20:22:06Z** (`osmosis_replication_timestamp` de la cabecera del PBF; secuencia de replicación 4926 de `spain-updates`; coincide con el `state.txt` de Geofabrik) |
| Fecha del fichero en Geofabrik | `Last-Modified: Fri, 02 Oct 2026 17:35:18 GMT` (cuándo se publicó, no cuándo son los datos) |
| Fecha de descarga | 2026-10-11 02:26–02:31 UTC (2026-10-10 23:26–23:31 hora local) |
| Contenedor / puerto | `osrm-espana`, en `http://127.0.0.1:5001` (solo localhost) |

### Por qué estas elecciones

- **Imagen de GHCR y no de Docker Hub.** En Docker Hub, `osrm/osrm-backend` solo publica amd64 y su última etiqueta es de
  2021 (v5.25.0). El proyecto publica ahora en `ghcr.io/project-osrm/osrm-backend`. Allí, la etiqueta `v26.10.0-debian`
  es un índice con linux/amd64 y linux/arm64. Ambos datos se consultaron en los registros el 2026-10-10; el índice está
  en `data/raw/osrm_2026-10-10/ghcr_osrm-backend_v26.10.0-debian_index.json`. La imagen se fija por etiqueta **y** por
  digest: si alguien vuelve a publicar la etiqueta, el digest no cambia.
- **Extracto fechado `spain-261001` y no `spain-latest`.** El 2026-10-10, `spain-latest` tenía datos hasta
  2026-10-08T20:21:06Z, después de la fecha de corte del Spec (1-oct-2026). Geofabrik conserva extractos diarios
  fechados, y `spain-261001` corresponde al día del corte.
- **Puerto 5001 y no 5000.** En macOS, el puerto 5000 lo ocupa `ControlCenter` (receptor AirPlay) en `*:5000`. Se puede
  cambiar con `OSRM_PUERTO=<puerto>`.

## Requisitos

- Docker. En esta máquina: Colima 0.10.3 (VM `vz`, aarch64) con Docker CLI 29.9.0.
- **RAM:** el contenedor necesita **al menos 12 GiB** disponibles. Medido en Colima: la VM necesita 12 GiB. `osrm-extract` llegó a 10,9 GiB según su propio registro
  (11,06 GiB de `memory.peak` en el cgroup), muy cerca del techo de 11,65 GiB que ve el contenedor. No ejecute otros
  contenedores pesados durante `preparar`. Con menos memoria, `osrm-extract` probablemente muera por falta de memoria
  (OOM). No se ha probado.
  - **Docker Desktop (macOS/Windows):** Settings → Resources → Memory **≥ 12 GiB** (la VM de Docker Desktop es el techo
    del contenedor, igual que en Colima). No se ha probado en esta máquina; la cifra sale del pico medido de
    `osrm-extract` (10,9 GiB).
  - **Linux nativo:** no hay VM; el contenedor ve la RAM del host. Hacen falta **≥ 12 GiB libres** en el host durante
    `preparar` (mismo pico medido, 10,9 GiB). No se ha probado en Linux.
- **Disco:** 4,8 GB en `osrm-data/` (1,49 GB del PBF y el resto de archivos `.osrm*`). Además, la imagen ocupa unos 129 MB.
- Python 3 (solo biblioteca estándar) para la prueba de aceptación y para leer la cabecera del PBF.
- Si Colima está parado: `colima start` (conserva la configuración: 8 CPU, 12 GiB y 60 GiB). Para crearlo desde cero:
  `colima start --vm-type vz --cpu 8 --memory 12 --disk 60`.

## Comandos

Todo pasa por `scripts/osrm/osrm.sh`. Se ejecuta desde cualquier directorio; los datos van a `osrm-data/`, que git
ignora.

```bash
scripts/osrm/osrm.sh descargar   # baja spain-261001.osm.pbf y su .md5 y verifica el md5; si ambos ya están en
                                 # osrm-data/ y cuadran con el md5 fijado, no toca la red. Imprime la cabecera del PBF
docker pull ghcr.io/project-osrm/osrm-backend:v26.10.0-debian@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f
scripts/osrm/osrm.sh preparar    # extract -> partition -> customize; registro en osrm-data/preparar_<fecha>.log
scripts/osrm/osrm.sh arrancar    # crea o reinicia el contenedor osrm-espana y espera a que responda (ver abajo)
scripts/osrm/osrm.sh prueba      # prueba de aceptación; por defecto NO escribe nada (solo imprime)
scripts/osrm/osrm.sh prueba --salida /tmp/osrm_prueba            # guarda los JSON en un directorio cualquiera
scripts/osrm/osrm.sh prueba --salida data/raw/osrm_<AAAA-MM-DD>  # solo para generar evidencia NUEVA y versionarla
scripts/osrm/osrm.sh estado      # estado del contenedor
scripts/osrm/osrm.sh parar       # detiene y elimina el contenedor (los datos de osrm-data/ se conservan)
scripts/osrm/osrm.sh todo        # descargar + pull + preparar + arrancar + prueba
```

Equivalentes sin el script, para referencia (IMG es la imagen con su digest):

```bash
docker run --rm -v "$PWD/osrm-data:/data" $IMG osrm-extract -p /opt/car.lua --data_version osmosis /data/spain-261001.osm.pbf
docker run --rm -v "$PWD/osrm-data:/data" $IMG osrm-partition /data/spain-261001.osrm
docker run --rm -v "$PWD/osrm-data:/data" $IMG osrm-customize /data/spain-261001.osrm
docker run -d --name osrm-espana -p 127.0.0.1:5001:5000 -v "$PWD/osrm-data:/data" $IMG \
  osrm-routed --algorithm mld /data/spain-261001.osrm
```

Con `--data_version osmosis`, cada respuesta del servidor incluye `"data_version": "2026-10-01T20:22:06Z"`. Así, cada
JSON que descargue T2.3 queda ligado a la fecha del extracto.

Una vez preparado, `arrancar` tarda unos 3 s y `osrm-routed` ocupa unos 2,2 GiB de RAM.

Comportamiento de `arrancar`:
- Antes de lanzar nada comprueba que existen en `osrm-data/` los 20 archivos `spain-261001.osrm.*` que necesita
  `osrm-routed --algorithm mld`: los "required" de `--list-inputs` más `cells`, `cell_metrics`, `mldgr` y `partition`.
  Si falta alguno, falla al instante con la lista de los que faltan y pide ejecutar `descargar` y `preparar`.
- Si el contenedor `osrm-espana` ya existe, solo lo reutiliza (`docker start`) cuando su puerto publicado es
  `127.0.0.1:${OSRM_PUERTO:-5001}` y su imagen es la fijada en el script. Si no coincide, **no lo recrea**: sale con
  error y propone `scripts/osrm/osrm.sh parar && OSRM_PUERTO=<puerto> scripts/osrm/osrm.sh arrancar`.

### Si Geofabrik retira `spain-261001`

Si `descargar` recibe un 404 por `spain-261001.osm.pbf`, **no lo sustituya por `spain-latest`**: tendría datos
posteriores a la fecha de corte (Spec §7.1) y todas las rutas cambiarían sin aviso. Hay que **escalarlo al puente**
(Daniel). No se ha comprobado cuánto tiempo conserva Geofabrik los extractos fechados. El 2026-10-10 el listado
(`data/raw/osrm_2026-10-10/geofabrik_spain_2026-10-10.html`) mostraba `spain-261001` y los extractos de los días
siguientes.

Fecha de los datos de cualquier PBF: `python3 -I scripts/osrm/cabecera_pbf.py osrm-data/spain-261001.osm.pbf`.

## Medidas del preprocesado (2026-10-11 UTC; M4, Colima con 8 CPU y 12 GiB)

| Paso | Tiempo de pared | Pico de RAM (registro de OSRM, "RAM: peak bytes used") | `memory.peak` del cgroup (incluye la caché de páginas) |
|---|---|---|---|
| `osrm-extract` | 482 s (8 min 2 s) | 11 713 925 120 B (10,9 GiB) | 11 871 006 720 B (11,06 GiB) |
| `osrm-partition` | 55 s | 3 004 858 368 B (2,8 GiB) | 3 507 814 400 B (3,27 GiB) |
| `osrm-customize` | 14 s | 2 161 868 800 B (2,0 GiB) | 3 217 629 184 B (3,0 GiB) |

El registro completo está en `data/raw/osrm_2026-10-10/osrm_preparar_2026-10-10.log`. Tiene 50 avisos `[warn]` y
ningún error. Los avisos son habituales en OSRM: giros en U en dos nodos de Sevilla y "unreachable boundary nodes per
cell" en la partición.

## Prueba de aceptación

`scripts/osrm/osrm.sh prueba [--salida DIR]` ejecuta `python3 -I scripts/osrm/prueba_aceptacion.py --raiz <repo> --url
http://127.0.0.1:5001 [--salida DIR]`. Toma las coordenadas de `data/processed/cities.csv` y pide cada par con `steps=true`, sin
restricciones y con `exclude=toll`. Sale con código distinto de 0 si algo falla. **Sin `--salida` no escribe ningún archivo**, así que repetir la prueba no
toca la evidencia versionada. Con `--salida DIR` (relativo a la raíz del repo o absoluto), guarda en DIR los 6 JSON y
`resumen_aceptacion.json`.

- **A (PLAN T2.2), Madrid → Barcelona:** las dos alternativas deben responder `code: "Ok"`, y la ruta `exclude=toll` no
  puede tener ninguna intersección con la clase `toll`.
- **B (Spec §7.2 Bloque 3, paso 1, "[VERIFICAR que el OSRM local la marca]"):** se usan dos pares de validación del Spec
  con peaje vigente a la fecha de corte, Bilbao → Zaragoza (AP-68) y A Coruña → Pontevedra (AP-9). En ellos, la ruta
  rápida debe tener intersecciones con la clase `toll` y la ruta `exclude=toll` ninguna.

Resultado del 2026-10-11 02:42 UTC: **OK**.

| Par | Alternativa | code | km | h | Pasos con la clase `toll` (refs) |
|---|---|---|---|---|---|
| Madrid → Barcelona | rapida | Ok | 617,0 | 6,82 | 0 |
| Madrid → Barcelona | sin_peaje | Ok | 617,0 | 6,82 | 0 |
| Bilbao → Zaragoza | rapida | Ok | 305,5 | 3,35 | 1 (AP-68) |
| Bilbao → Zaragoza | sin_peaje | Ok | 294,3 | 4,36 | 0 |
| A Coruña → Pontevedra | rapida | Ok | 133,5 | 1,54 | 2 (AP-9) |
| A Coruña → Pontevedra | sin_peaje | Ok | 130,3 | 2,29 | 0 |

La evidencia está en `data/raw/osrm_2026-10-10/`: las respuestas crudas `<origen>_<destino>_{rapida,sin_peaje}.json`
y `resumen_aceptacion.json`. El resumen recoge las URL, los km por `ref` y los pasos con la clase `toll`.

Nota sobre `resumen_aceptacion.json`: antes de existir `--salida`, la prueba se ejecutó una segunda vez en el repo y
reescribió el archivo. Su `fecha_consulta_utc` (2026-10-11T02:45:50Z) es la de esa última corrida, no la de las 02:42
UTC de la tabla. Las 6 respuestas de ruta salieron idénticas en las dos corridas. Se deja el archivo como está.

**Observaciones para T2.3 y T2.5:**
- La ruta rápida de Madrid → Barcelona **no tiene peaje**. Va por A-2 (317 km), AP-2 (216 km), AP-7 (49 km) y B-23
  (19 km); la AP-2 y la AP-7 conservan el nombre "AP-" aunque ya son gratuitas (Spec §7.2 Bloque 3, paso 2). Por eso
  `sin_peaje` es idéntica a `rapida`: es el caso "se marca y se reutiliza" del Bloque 2. Ese par no sirve para
  verificar la clase `toll`; para eso están los pares de control.
- La clase `toll` se asigna **por intersección**, no por paso: está en `steps[].intersections[].classes`. Un paso puede
  ser muy largo y estar marcado solo en parte. Por ejemplo, la AP-68 de Bilbao → Zaragoza es un único paso de 293 km con
  94 de sus 96 intersecciones marcadas con `toll`, y en la AP-9, en un paso de 11,4 km, solo 3 de 12 lo están. Sumar la
  distancia de los pasos "con toll" sobreestima los km de peaje. T2.5 debería medir los km por intersección o por
  segmento.

## Problemas encontrados

1. **Docker Hub `osrm/osrm-backend` está abandonado** (solo amd64; última etiqueta de 2021). Se usa la imagen oficial
   de GHCR.
2. **`spain-latest` es posterior a la fecha de corte.** Se usa el extracto fechado `spain-261001`.
3. **El puerto 5000 está ocupado por macOS** (AirPlay). Docker llegó a enlazar `127.0.0.1:5000` sin error, a pesar de que
   había otro proceso escuchando en `*:5000`, así que no estaba garantizado qué proceso contestaba. Se pasó a 5001.
4. **Memoria justa en `osrm-extract`:** 10,9 GiB de un techo de 11,65 GiB. Ver los requisitos.
5. El archivo `/opt/OSRM_GITSHA` de la imagen está vacío. El commit se tomó del tag de GitHub (`git ls-remote`).
6. `docker buildx` no está instalado en esta máquina. Los manifiestos se consultaron con la API del registro de GHCR.
