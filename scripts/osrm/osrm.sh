#!/usr/bin/env bash
# OSRM local para la Parte 2 (T2.2). Ver scripts/osrm/README.md.
#
# Uso: scripts/osrm/osrm.sh {descargar|preparar|arrancar|parar|estado|prueba|todo}
#
# Todo lo pesado va a osrm-data/ (ignorado por git). La única descarga de internet es la de "descargar"
# (extracto de Geofabrik); la imagen Docker se descarga con "docker pull" la primera vez.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Git Bash (Windows): ruta de la raíz en forma C:/... (la entienden docker, python y curl nativos) y sin conversión
# automática de rutas POSIX, que convertiría "-v ...:/data" en una lista de rutas de Windows y "/data/..." en
# "C:/Program Files/Git/data/...". En macOS y Linux no cambia nada.
case "$(uname -s)" in
  MINGW*|MSYS*) RAIZ="$(cd "${RAIZ}" && pwd -W)"; export MSYS_NO_PATHCONV=1 ;;
esac
DATOS="${RAIZ}/osrm-data"

# Imagen oficial del proyecto OSRM en GHCR, fijada por etiqueta Y digest (índice multi-arquitectura,
# incluye linux/arm64 nativo). Docker Hub osrm/osrm-backend solo publica amd64 y está congelado en 2021.
IMAGEN="ghcr.io/project-osrm/osrm-backend:v26.10.0-debian@sha256:55dbfd47d984c2cacd64e32901b4321c86b5ec761438e69aa053dc78698a786f"

# Extracto fechado de Geofabrik que coincide con la fecha de corte del Spec (1-oct-2026).
# NO usar spain-latest: contiene datos posteriores al corte.
EXTRACTO="spain-261001"
URL_BASE="https://download.geofabrik.de/europe"
MD5_ESPERADO="27c3c06719ce8045421b34b530687063"

CONTENEDOR="osrm-espana"
PUERTO="${OSRM_PUERTO:-5001}"  # 5000 lo ocupa macOS (ControlCenter/AirPlay)
# --threads 1 (Spec v1.8 §7.2 Bloque 2): con los hilos por defecto (16) la misma URL devolvía rutas distintas, a veces
# no óptimas. Ver alucinaciones/evidencias/T2.3_toll_diagnostico/README.md.
ROUTED_CMD=(osrm-routed --algorithm mld --threads 1 "/data/${EXTRACTO}.osrm")

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }

md5_de() {
  if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi
}

descargar() {
  mkdir -p "${DATOS}"
  cd "${DATOS}"
  if [[ -f "${EXTRACTO}.osm.pbf" && -f "${EXTRACTO}.osm.pbf.md5" ]] \
     && [[ "$(cut -d' ' -f1 "${EXTRACTO}.osm.pbf.md5")" == "${MD5_ESPERADO}" ]] \
     && [[ "$(md5_de "${EXTRACTO}.osm.pbf")" == "${MD5_ESPERADO}" ]]; then
    log "PBF y .md5 locales presentes y verificados (${MD5_ESPERADO}); no se accede a la red."
  else
    log "Descargando ${EXTRACTO}.osm.pbf.md5 de ${URL_BASE}"
    curl -sS -fL -O "${URL_BASE}/${EXTRACTO}.osm.pbf.md5"
    if [[ -f "${EXTRACTO}.osm.pbf" ]] && [[ "$(md5_de "${EXTRACTO}.osm.pbf")" == "${MD5_ESPERADO}" ]]; then
      log "El extracto ya existe y su md5 es correcto; no se vuelve a descargar."
    else
      log "Descargando ${EXTRACTO}.osm.pbf de ${URL_BASE}"
      curl -sS -fL -D "${EXTRACTO}.headers.txt" -O "${URL_BASE}/${EXTRACTO}.osm.pbf"
    fi
  fi
  local publicado calculado
  publicado="$(cut -d' ' -f1 "${EXTRACTO}.osm.pbf.md5")"
  calculado="$(md5_de "${EXTRACTO}.osm.pbf")"
  log "md5 publicado: ${publicado} | calculado: ${calculado} | fijado en el script: ${MD5_ESPERADO}"
  [[ "${publicado}" == "${calculado}" && "${calculado}" == "${MD5_ESPERADO}" ]] || { log "ERROR: md5 no coincide"; exit 1; }
  log "md5 verificado."
  log "Cabecera del PBF (osmosis_replication_timestamp = fecha de los datos):"
  python3 -I "${RAIZ}/scripts/osrm/cabecera_pbf.py" "${DATOS}/${EXTRACTO}.osm.pbf"
}

# Ejecuta un paso de OSRM en un contenedor efímero; mide tiempo de pared y el pico de memoria del cgroup
# (memory.peak, cgroup v2; incluye caché de páginas, así que es una cota superior aproximada).
paso() {
  local nombre="$1"; shift
  local inicio fin
  log "== ${nombre}: $*"
  inicio=$(date +%s)
  docker run --rm -v "${DATOS}:/data" "${IMAGEN}" \
    sh -c "$* && echo \"cgroup memory.peak (bytes): \$(cat /sys/fs/cgroup/memory.peak)\""
  fin=$(date +%s)
  log "== ${nombre}: tiempo de pared $((fin - inicio)) s"
}

preparar() {
  [[ -f "${DATOS}/${EXTRACTO}.osm.pbf" ]] || { log "Falta el extracto; ejecute primero: $0 descargar"; exit 1; }
  local registro
  registro="${DATOS}/preparar_$(date +%F).log"
  log "Registro del preprocesado: ${registro}"
  {
    log "Imagen: ${IMAGEN}"
    paso extract   "osrm-extract -p /opt/car.lua --data_version osmosis /data/${EXTRACTO}.osm.pbf"
    paso partition "osrm-partition /data/${EXTRACTO}.osrm"
    paso customize "osrm-customize /data/${EXTRACTO}.osrm"
  } 2>&1 | tee "${registro}"
}

# Archivos que osrm-routed --algorithm mld necesita (salida de "osrm-routed --algorithm mld --list-inputs":
# los "required" más los cuatro de MLD que genera partition/customize).
SUFIJOS_MLD=(datasource_names ebg_nodes edges fileIndex geometry icd maneuver_overrides names nbg_nodes properties
  ramIndex timestamp tld tls turn_duration_penalties turn_weight_penalties cells cell_metrics mldgr partition)

comprobar_datos() {
  local faltan=() suf
  for suf in "${SUFIJOS_MLD[@]}"; do
    [[ -f "${DATOS}/${EXTRACTO}.osrm.${suf}" ]] || faltan+=("${EXTRACTO}.osrm.${suf}")
  done
  if (( ${#faltan[@]} > 0 )); then
    log "ERROR: faltan ${#faltan[@]} archivos en ${DATOS}: ${faltan[*]}"
    log "Ejecute primero: $0 descargar && $0 preparar"
    exit 1
  fi
}

arrancar() {
  comprobar_datos
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTENEDOR}"; then
    # docker start reutiliza el puerto, la imagen y el comando con que se creó el contenedor: si no coinciden con lo
    # pedido, se aborta (no se recrea en silencio).
    local publicado imagen_actual cmd_actual
    publicado="$(docker inspect "${CONTENEDOR}" --format '{{range (index .HostConfig.PortBindings "5000/tcp")}}{{.HostIp}}:{{.HostPort}}{{end}}')"
    imagen_actual="$(docker inspect "${CONTENEDOR}" --format '{{.Config.Image}}')"
    cmd_actual="$(docker inspect "${CONTENEDOR}" --format '{{join .Config.Cmd " "}}')"
    if [[ "${publicado}" != "127.0.0.1:${PUERTO}" || "${imagen_actual}" != "${IMAGEN}" \
          || "${cmd_actual}" != "${ROUTED_CMD[*]}" ]]; then
      log "ERROR: el contenedor ${CONTENEDOR} ya existe con puerto '${publicado}', imagen '${imagen_actual}'"
      log "       y comando '${cmd_actual}',"
      log "       pero se pidió 127.0.0.1:${PUERTO}, imagen ${IMAGEN} y comando '${ROUTED_CMD[*]}'."
      log "       Recréelo con: $0 parar && OSRM_PUERTO=${PUERTO} $0 arrancar"
      exit 1
    fi
    log "El contenedor ${CONTENEDOR} ya existe (127.0.0.1:${PUERTO}); se reinicia si estaba parado."
    docker start "${CONTENEDOR}" >/dev/null
  else
    docker run -d --name "${CONTENEDOR}" -p "127.0.0.1:${PUERTO}:5000" -v "${DATOS}:/data" "${IMAGEN}" \
      "${ROUTED_CMD[@]}" >/dev/null
  fi
  log "Esperando a que responda http://127.0.0.1:${PUERTO} ..."
  for _ in $(seq 1 120); do
    # Comprobación de salud: coordenadas de Madrid tomadas de data/processed/cities.csv.
    if curl -sf "http://127.0.0.1:${PUERTO}/nearest/v1/driving/-3.691978,40.419026" >/dev/null; then
      log "OSRM listo en http://127.0.0.1:${PUERTO} (contenedor ${CONTENEDOR})"; return 0
    fi
    sleep 1
  done
  log "ERROR: OSRM no respondió en 120 s"; docker logs --tail 50 "${CONTENEDOR}"; exit 1
}

parar() {
  if docker rm -f "${CONTENEDOR}" >/dev/null 2>&1; then
    log "Contenedor ${CONTENEDOR} detenido y eliminado."
  else
    log "No había contenedor ${CONTENEDOR}."
  fi
}

estado() {
  docker ps -a --filter "name=^${CONTENEDOR}$" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'
}

# Por defecto no escribe nada en el repositorio. Para guardar evidencia nueva:
#   scripts/osrm/osrm.sh prueba --salida data/raw/osrm_<AAAA-MM-DD>
prueba() {
  python3 -I "${RAIZ}/scripts/osrm/prueba_aceptacion.py" --raiz "${RAIZ}" --url "http://127.0.0.1:${PUERTO}" "$@"
}

case "${1:-}" in
  descargar) descargar ;;
  preparar)  preparar ;;
  arrancar)  arrancar ;;
  parar)     parar ;;
  estado)    estado ;;
  prueba)    shift; prueba "$@" ;;
  todo)      descargar; docker pull "${IMAGEN}"; preparar; arrancar; prueba ;;
  *) echo "Uso: $0 {descargar|preparar|arrancar|parar|estado|prueba|todo}"; exit 2 ;;
esac
