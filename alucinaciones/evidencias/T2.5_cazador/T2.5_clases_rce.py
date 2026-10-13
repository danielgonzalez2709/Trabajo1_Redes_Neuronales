"""Cazador T2.5, afirmacion 1: clase de A-42, A-31, A-70, A-7 (Alicante-Murcia), AP-4, AP-41, A-66 en el Catalogo RCE 2025.
Uso: python -I T2.5_clases_rce.py <zip>   (lee solo el .dbf del zip)"""
import sys, zipfile, struct, collections
z = zipfile.ZipFile(sys.argv[1]); dbf = z.read(next(n for n in z.namelist() if n.lower().endswith('.dbf')))
n, hc, hr = struct.unpack('<IHH', dbf[4:12]); campos, pos = [], 32
while dbf[pos] != 0x0D: campos.append((dbf[pos:pos + 11].split(b'\0')[0].decode(), dbf[pos + 16])); pos += 32
print('campos:', [c for c, _ in campos])
cnt = collections.defaultdict(float)
for k in range(n):
    r = dbf[hc + k * hr: hc + (k + 1) * hr]; d, o = {}, 1
    for nm, ln in campos: d[nm] = r[o:o + ln].decode('utf-8', 'replace').strip(); o += ln
    if d['carretera'] in ('A-42', 'A-31', 'A-70', 'A-7', 'AP-4', 'AP-41', 'A-66', 'AP-66', 'GI-20', 'N-622', 'PA-34') and \
       (d['carretera'] != 'A-7' or d['provincia'] in ('Alicante/Alacant', 'Murcia')):
        cnt[(d['carretera'], d['provincia'], d['clase'])] += float(d['longitud'])
for k, v in sorted(cnt.items()): print(k, round(v, 1), 'km')
