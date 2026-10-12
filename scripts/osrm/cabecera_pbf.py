"""Lee la cabecera (HeaderBlock) de un .osm.pbf y la imprime en JSON, sin dependencias externas.

Sirve para registrar la fecha de los datos de un extracto de Geofabrik: el campo
osmosis_replication_timestamp (campo 32 del HeaderBlock, formato OSM PBF) es el instante de los datos.
Uso: python3 -I scripts/osrm/cabecera_pbf.py osrm-data/spain-261001.osm.pbf
"""
import struct, sys, zlib, datetime, json
def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, i
def fields(b):
    i = 0
    while i < len(b):
        k, i = varint(b, i); f, w = k >> 3, k & 7
        if w == 0: v, i = varint(b, i)
        elif w == 2:
            n, i = varint(b, i); v = b[i:i+n]; i += n
        elif w == 1: v = b[i:i+8]; i += 8
        elif w == 5: v = b[i:i+4]; i += 4
        yield f, v
with open(sys.argv[1], 'rb') as fh:
    n = struct.unpack('>I', fh.read(4))[0]
    bh = dict(fields(fh.read(n)))
    blob = dict(fields(fh.read(bh[3])))
    data = zlib.decompress(blob[3]) if 3 in blob else blob[1]
out = {"required_features": [], "optional_features": []}
for f, v in fields(data):
    if f == 4: out["required_features"].append(v.decode())
    elif f == 5: out["optional_features"].append(v.decode())
    elif f == 16: out["writingprogram"] = v.decode()
    elif f == 17: out["source"] = v.decode()
    elif f == 32: out["osmosis_replication_timestamp"] = datetime.datetime.fromtimestamp(v, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    elif f == 33: out["osmosis_replication_sequence_number"] = v
    elif f == 34: out["osmosis_replication_base_url"] = v.decode()
print(json.dumps(out, indent=2))
