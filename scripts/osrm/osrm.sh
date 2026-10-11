#!/usr/bin/env bash
# OSRM local para la Parte 2 (T2.2). Ver scripts/osrm/README.md.
#
# Uso: scripts/osrm/osrm.sh {descargar|preparar|arrancar|parar|estado|prueba|todo}
#
# Todo lo pesado va a osrm-data/ (ignorado por git). La única descarga de internet es la de "descargar"
# (extracto de Geofabrik); la imagen Docker se descarga con "docker pull" la primera vez.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }

md5_de() {
  if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi
}

descargar() {
  mkdir -p "${DATOS}"
  cd "${DATOS}"
  log "Descargando ${EXTRACTO}.osm.pbf.md5 y ${EXTRACTO}.osm.pbf de ${URL_BASE}"
  curl -sS -fL -O "${URL_BASE}/${EXTRACTO}.osm.pbf.md5"
  if [[ -f "${EXTRACTO}.osm.pbf" ]] && [[ "$(md5_de "${EXTRACTO}.osm.pbf")" == "${MD5_ESPERADO}" ]]; then
    log "El extracto ya existe y su md5 es correcto; no se vuelve a descargar."
  else
    curl -sS -fL -D "${EXTRACTO}.headers.txt" -O "${URL_BASE}/${EXTRACTO}.osm.pbf"
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
  local registro="${DATOS}/preparar_$(date +%F).log"
  log "Registro del preprocesado: ${registro}"
  {
    log "Imagen: ${IMAGEN}"
    paso extract   "osrm-extract -p /opt/car.lua --data_version osmosis /data/${EXTRACTO}.osm.pbf"
    paso partition "osrm-partition /data/${EXTRACTO}.osrm"
    paso customize "osrm-customize /data/${EXTRACTO}.osrm"
  } 2>&1 | tee "${registro}"
}

arrancar() {
  if docker ps -a --format '{{.Names}}' | grep -qx "${CONTENEDOR}"; then
    log "El contenedor ${CONTENEDOR} ya existe; se reinicia."
    docker start "${CONTENEDOR}" >/dev/null
  else
    docker run -d --name "${CONTENEDOR}" -p "127.0.0.1:${PUERTO}:5000" -v "${DATOS}:/data" "${IMAGEN}" \
      osrm-routed --algorithm mld "/data/${EXTRACTO}.osrm" >/dev/null
  fi
  log "Esperando a que responda http://127.0.0.1:${PUERTO} ..."
  for _ in $(seq 1 120); do
    if curl -sf "http://127.0.0.1:${PUERTO}/nearest/v1/driving/-3.691978,40.419026" >/dev/null; then
      log "OSRM listo en http://127.0.0.1:${PUERTO} (contenedor ${CONTENEDOR})"; return 0
    fi
    sleep 1
  done
  log "ERROR: OSRM no respondió en 120 s"; docker logs --tail 50 "${CONTENEDOR}"; exit 1
}

parar() {
  docker rm -f "${CONTENEDOR}" >/dev/null 2>&1 && log "Contenedor ${CONTENEDOR} detenido y eliminado." \
    || log "No había contenedor ${CONTENEDOR}."
}

estado() {
  docker ps -a --filter "name=^${CONTENEDOR}$" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'
}

prueba() {
  python3 -I "${RAIZ}/scripts/osrm/prueba_aceptacion.py" --raiz "${RAIZ}" --url "http://127.0.0.1:${PUERTO}"
}

case "${1:-}" in
  descargar) descargar ;;
  preparar)  preparar ;;
  arrancar)  arrancar ;;
  parar)     parar ;;
  estado)    estado ;;
  prueba)    prueba ;;
  todo)      descargar; docker pull "${IMAGEN}"; preparar; arrancar; prueba ;;
  *) echo "Uso: $0 {descargar|preparar|arrancar|parar|estado|prueba|todo}"; exit 2 ;;
esac
