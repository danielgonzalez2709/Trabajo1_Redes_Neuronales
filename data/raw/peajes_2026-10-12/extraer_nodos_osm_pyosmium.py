# Fragmento usado el 2026-10-12 (T2.4, ronda 5) para leer los nodos highway=motorway_junction del extracto
# Geofabrik spain-261001 (osrm-data/spain-261001.osm.pbf, md5 27c3c06719ce8045421b34b530687063) con pyosmium 4.3.1,
# instalado aparte (no está en requirements.txt). Uso:
#   python -I extraer_nodos_osm_pyosmium.py <dir_con_osmium> <spain-261001.osm.pbf> osm_motorway_junction_spain-261001.csv
# Salida: osm_motorway_junction_spain-261001.csv (1054 nodos, coordenadas redondeadas a 7 decimales).
# Código sin cambios respecto al ejecutado (solo se añadió esta cabecera).
import sys, csv
sys.path.insert(0, sys.argv[1])
import osmium
BOX = [(-3.2, 41.5, -0.8, 43.4), (1.4, 41.1, 2.1, 41.35)]  # País Vasco/Navarra/La Rioja/Aragón; C-32
class H(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.rows = []
    def node(s, n):
        if n.tags.get('highway') == 'motorway_junction':
            lon, lat = n.location.lon, n.location.lat
            if any(a <= lon <= c and b <= lat <= d for a, b, c, d in BOX):
                s.rows.append((n.id, round(lon, 7), round(lat, 7), n.tags.get('ref', ''), n.tags.get('name', '')))
h = H(); h.apply_file(sys.argv[2])
with open(sys.argv[3], 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['osm_id', 'lon', 'lat', 'ref', 'name']); w.writerows(h.rows)
print(len(h.rows))
