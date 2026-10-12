"""Cazador T2.5, afirmacion 6: ancla (lon, lat, km_cadena) frente al Catalogo RCE 2025.

Independiente del curador: lee el shapefile del zip (struct, sin librerias), invierte UTM 30N (formulas de Snyder),
ubica en la geometria RCE el p.k. oficial que corresponde al km de la cadena y mide la distancia al ancla.
Uso: python -I T2.5_anclas_vs_rce.py <zip> <peajes_anclas.csv>
"""
import csv, math, struct, sys, zipfile

A, F = 6378137.0, 1 / 298.257222101
E2 = F * (2 - F); EP2 = E2 / (1 - E2); K0 = 0.9996; LON0 = math.radians(-3.0)


def utm_inv(x, y):
    x -= 500000.0
    M = y / K0
    mu = M / (A * (1 - E2 / 4 - 3 * E2**2 / 64 - 5 * E2**3 / 256))
    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    p1 = mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu) + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu) \
        + (151 * e1**3 / 96) * math.sin(6 * mu) + (1097 * e1**4 / 512) * math.sin(8 * mu)
    s, c, t = math.sin(p1), math.cos(p1), math.tan(p1)
    N1 = A / math.sqrt(1 - E2 * s * s); T1 = t * t; C1 = EP2 * c * c
    R1 = A * (1 - E2) / (1 - E2 * s * s) ** 1.5; D = x / (N1 * K0)
    lat = p1 - (N1 * t / R1) * (D**2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * EP2) * D**4 / 24
                                + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * EP2 - 3 * C1**2) * D**6 / 720)
    lon = LON0 + (D - (1 + 2 * T1 + C1) * D**3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * EP2 + 24 * T1**2) * D**5 / 120) / c
    return math.degrees(lon), math.degrees(lat)


def dist_km(a, b):
    return math.hypot((a[0] - b[0]) * math.cos(math.radians(a[1])), a[1] - b[1]) * 111.195


def leer(zpath):
    with zipfile.ZipFile(zpath) as z:
        nom = {n.lower().rsplit('.', 1)[1]: n for n in z.namelist()}
        dbf, shp = z.read(nom['dbf']), z.read(nom['shp'])
    n, hc, hr = struct.unpack('<IHH', dbf[4:12]); campos, pos = [], 32
    while dbf[pos] != 0x0D:
        campos.append((dbf[pos:pos + 11].split(b'\0')[0].decode(), dbf[pos + 16])); pos += 32
    filas = []
    for k in range(n):
        r = dbf[hc + k * hr: hc + (k + 1) * hr]; d, o = {}, 1
        for nm, ln in campos:
            d[nm] = r[o:o + ln].decode('utf-8', 'replace').strip(); o += ln
        filas.append(d)
    geos, p = [], 100
    while p < len(shp):
        _, cl = struct.unpack('>ii', shp[p:p + 8]); body = shp[p + 8:p + 8 + 2 * cl]; p += 8 + 2 * cl
        t = struct.unpack('<i', body[:4])[0]
        if t == 0: geos.append(None); continue
        npart, npts = struct.unpack('<ii', body[36:44])
        parts = list(struct.unpack(f'<{npart}i', body[44:44 + 4 * npart])) + [npts]
        o = 44 + 4 * npart; pts = [struct.unpack('<dd', body[o + 16 * i:o + 16 * i + 16]) for i in range(npts)]
        geos.append([pts[parts[i]:parts[i + 1]] for i in range(npart)])
    assert len(geos) == len(filas), (len(geos), len(filas))
    return filas, geos


def punto_en_pk(filas, geos, via, pk, prov=None):
    """Devuelve los 2 candidatos (por si la geometria va al reves) del p.k. en el tramo que lo contiene."""
    out = []
    for f, g in zip(filas, geos):
        if f['carretera'] != via or g is None or (prov and f['provincia'] not in prov): continue
        a, b = float(f['pk_inicio']), float(f['pk_fin'])
        if a - 1e-6 <= pk <= b + 1e-6 and b > a:
            linea = [pt for parte in g for pt in parte]
            cum = [0.0]
            for u, v in zip(linea, linea[1:]): cum.append(cum[-1] + math.hypot(v[0] - u[0], v[1] - u[1]))
            for fr in ((pk - a) / (b - a), 1 - (pk - a) / (b - a)):
                tgt = fr * cum[-1]; i = next(i for i in range(1, len(cum)) if cum[i] >= tgt - 1e-9)
                w = (tgt - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-9)
                x = linea[i - 1][0] + w * (linea[i][0] - linea[i - 1][0]); y = linea[i - 1][1] + w * (linea[i][1] - linea[i - 1][1])
                out.append((utm_inv(x, y), f['pk_inicio'], f['pk_fin'], f['clase'] if 'clase' in f else ''))
    return out


if __name__ == '__main__':
    filas, geos = leer(sys.argv[1])
    anclas = list(csv.DictReader(open(sys.argv[2], encoding='utf-8')))
    # (indice de ancla, via RCE, p.k. oficial esperado)
    casos = [(int(a), v, float(pk)) for a, v, pk in (x.split(':') for x in sys.argv[3:])]
    for k, via, pk in casos:
        an = anclas[k]; ref = (float(an['lon']), float(an['lat']))
        c = punto_en_pk(filas, geos, via, pk)
        print(f"ancla {k} {an['cadena']} km_cadena={an['km_cadena']} ({an['etiqueta']}, {an['tipo_coord']}); RCE {via} pk {pk}")
        if not c: print('   sin tramo RCE para ese p.k.'); continue
        ds = sorted((dist_km(p[0], ref), p) for p in c)
        for d, p in ds[:4]:
            print(f"   candidato lon={p[0][0]:.4f} lat={p[0][1]:.4f} tramo {p[1]}-{p[2]} distancia al ancla {d:.2f} km")
        print(f"   MEJOR distancia: {ds[0][0]:.2f} km")
