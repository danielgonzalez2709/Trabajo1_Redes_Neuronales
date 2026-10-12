# T2.3: diagnóstico de `sin_peaje` con clase `toll`

Diagnóstico acotado, hecho el 11-oct-2026 a las 23:54–00:00 hora local (UTC−5), que corresponde al
**2026-10-12T04:54Z–05:01Z**. Los nombres de archivo llevan la fecha local (2026-10-11). No modifica `data/processed/`,
`scripts/`, `tests/` ni `docs/`. Las rutas de este directorio son **solo diagnóstico**: no son datos del proyecto.

Servidor: `osrm-espana` (imagen `ghcr.io/project-osrm/osrm-backend:v26.10.0-debian`, digest `sha256:55dbfd47…a786f`,
`osrm-routed --algorithm mld`, 16 hilos por defecto, `data_version` 2026-10-01T20:22:06Z), en http://127.0.0.1:5001.
Perfil `/opt/car.lua` SHA-256 `57778a75…59fa66`; `/opt/lib/way_handlers.lua` SHA-256 `4d503da9a7d1fb2228f869e218404524cf9cca7027c382e06ae65830f007a6c0`.
Servidor de contraste temporal `osrm-diag-t1` en 127.0.0.1:5002: misma imagen y mismos datos (montados en solo lectura),
`--threads 1`. Se detuvo y se eliminó al terminar.

## Archivos

| Archivo | Origen (URL) | Consulta (UTC) | SHA-256 |
|---|---|---|---|
| `osrm_16_18_rapida_nodes_2026-10-11.json` | `http://127.0.0.1:5001/route/v1/driving/-3.598691,37.174289;-1.985721,43.321523?alternatives=false&steps=true&geometries=geojson&overview=full&annotations=nodes` | 2026-10-12T04:54Z | `a806990d308bfe2319beea4e0ed367a5a40b005eeb6b264b16358fae4f488052` |
| `osrm_16_18_sin_peaje_nodes_2026-10-11.json` | la misma URL `&exclude=toll` | 2026-10-12T04:54Z | `3d484b8c979d7b4d6e28ed7e332f1da934d50f383b64cb371fbcef14eb9af81f` |
| `osrm_16_18_sin_peaje_nodes_variante_toll0_2026-10-11.json` | la misma URL `&exclude=toll` (variante sin `toll`) | 2026-10-12T04:55Z | `3d484b8c979d7b4d6e28ed7e332f1da934d50f383b64cb371fbcef14eb9af81f` |
| `osrm_16_18_sin_peaje_nodes_variante_toll6_2026-10-11.json` | la misma URL `&exclude=toll` (variante con 6 intersecciones `toll`) | 2026-10-12T04:55Z | `d39e82771e3dc5a897ff6df96b725527ea0188c17172f28ee61e74ef266e1ed2` |
| `osrm_16_18_sin_peaje_url_original_2026-10-11.json` | URL original de T2.3 (`geometries=polyline&overview=simplified&exclude=toll`) | 2026-10-12T04:54Z | `7c797b0055c58dc6b002abbac5042884fe6a59edaeb0e5c4948abd5e8201109b` |
| `osrm_26_29_rapida_nodes_2026-10-11.json` | `http://127.0.0.1:5001/route/v1/driving/-3.691978,40.419026;-1.644406,42.818565?alternatives=false&steps=true&geometries=geojson&overview=full&annotations=nodes` | 2026-10-12T04:54Z | `9289d632716f9b8d8c4f08f5fc9d1f7678694472ef7d9e1534e586724047d027` |
| `osrm_26_29_sin_peaje_nodes_2026-10-11.json` | la misma URL `&exclude=toll` | 2026-10-12T04:54Z | `eb06c9e0ce953d0e9fdc197cc791907ca4a52922881eae9b65aaa8a05fee5565` |
| `osrm_26_29_sin_peaje_nodes_variante_toll0_2026-10-11.json` | la misma URL `&exclude=toll` (variante sin `toll`) | 2026-10-12T04:55Z | `eb06c9e0ce953d0e9fdc197cc791907ca4a52922881eae9b65aaa8a05fee5565` |
| `osrm_26_29_sin_peaje_nodes_variante_toll8_2026-10-11.json` | la misma URL `&exclude=toll` (variante con 8 intersecciones `toll`) | 2026-10-12T04:55Z | `ff7c183b04a6590e8e6c77c2c8e03fd3ce1e3c0db339a63c7bf272f4b1fb0daa` |
| `osrm_26_29_sin_peaje_url_original_2026-10-11.json` | URL original de T2.3 | 2026-10-12T04:54Z | `501d045cf463ced9c947081c0e2623b5c0c7060b223c2fec2b69cf16ea752f04` |
| `repeticiones_2026-10-11.json` | URL original repetida 30 veces + 15 alternando con `rapida` (puerto 5001) | 2026-10-12T04:55Z | `cb9d469a50b8b008202d4afef8c2deaca120533ee4626ce3f0266492f260bec0` |
| `pesos_variantes_2026-10-11.json` | 24 repeticiones por par y alternativa, con `weight` (puerto 5001) | 2026-10-12T04:55Z | `964a7b0b954a951d3838100a58fe85d364ef1b9580a9e01b8ba7906ee07c93b6` |
| `repeticiones_threads1_2026-10-11.json` | 20 repeticiones por par y alternativa (puerto 5002, `--threads 1`) | 2026-10-12T04:59Z | `c9ba64a457e1ad015201c2485b9b621a7fde57b319fcb64e1ecc5b6d543495dd` |
| `replay_1081_threads1_2026-10-11.csv` | las 2 162 URL de `data/raw/osrm_2026-10-11/rutas/` repetidas en el puerto 5002 frente a la respuesta guardada | 2026-10-12T05:00:05Z–05:00:34Z | `df57e5f21bae7d20d196cad6fc167ea446a66310c714878f3e80ffe1580c09ea` |
| `osm_api_ways_actual_2026-10-11.json` | `https://api.openstreetmap.org/api/0.6/node/<id>/ways.json` (un nodo por arista `toll`); datos **actuales**, no del 1-oct | 2026-10-12T04:56Z | `c52de41ecc288f58682549a7c4658161c955a4488786557953575694686928e5` |
| `mitma_np_251230_tarifas_2026.pdf` | https://cdn.transportes.gob.es/portal-web-transportes/recursos-web/transportes/media/press_release/251230-np-nacional-revision-tarifas-autopistas-estatales-y-seitt.pdf | 2026-10-12T04:57Z | `f192265355c2c62d1871afe92079042a89e6e8d94b8dc1cef0893af4ed857bab` |
| `BOE-A-2025-25961.html` | https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-25961 | 2026-10-12T04:57Z | `2b364367f6fba22dbf4ac1b9514b01591aa45088da8b408248677ce516406c65` |
| `BOE-A-2026-19039.pdf` | https://www.boe.es/boe/dias/2026/09/11/pdfs/BOE-A-2026-19039.pdf | 2026-10-12T04:57Z | `2d3e401a44ae6a8609bd15bc75ff385d83afbcb2192f69b561227fd1382d2dd8` |
| `audenasa_tarifas.html` | https://www.audenasa.es/tarifas (redirige a `/la-autopista/tarifas-y-descuentos/`) | 2026-10-12T04:57Z | `55f65087cf8fc863f738415bc72c197e2b9798a97349d65c89005fb8d98701b6` |
| `BON_2025_258_9.html` | https://bon.navarra.es/es/anuncio/-/texto/2025/258/9 | 2026-10-12T04:58Z | `8887a992a97248cce823daa819f8a49b6dfda00b719125a1f3f60fd42cbc79aa` |

Los dos pares de archivos con el mismo SHA-256 (`*_sin_peaje_nodes_*` y `*_variante_toll0_*`) son respuestas idénticas
obtenidas en consultas distintas.

`scripts_diagnostico/`: scripts ad hoc que generaron los archivos (`diag1.py` a `diag10.py`; falta `diag7.py`, la consulta
a Overpass que falló con HTTP 504 y 500). SHA-256:

| Script | SHA-256 |
|---|---|
| `diag1.py` | `8b3ad60ce4cf36862bc600c28a1087bd95c8b5caf555ed91eec65aff2aad157d` |
| `diag2.py` | `67095de1385e241c757b52325719eae8d9375ad5583f1eb8a42b5031035fd4ec` |
| `diag3.py` | `34c5ffdfb092aaf7a2273931a475bcd0882f4478dbb2d88f9fbb4c3ee6deaa27` |
| `diag4.py` | `04cb3097da39fca51952091c01d9d84d4aa868472ace1653be3e980d6d56ab58` |
| `diag5.py` | `29b40fba7ca9994f48bea46e1d668c02e288be7090fb3efdcc030445944337f7` |
| `diag6.py` | `8a358f877a2e54f80b51977199b15fa69374eed24240894edf6cdb5bfa349f24` |
| `diag8.py` | `6b4e5c03fce3298c3378b8f47a7e96c085d60b032af866557823b6a352d48f04` |
| `diag9.py` | `e4fa112a403a10493deb8c7ac7bf37b1f8035ee9a4b210f6a133af6010f95a51` |
| `diag10.py` | `bfc3933e6d2c8349a1334e8714c57f97ef802ce74bcefede821ee18230b9d414` |

## Citas oficiales

- M-12. BOE-A-2025-25961 (Acuerdo del Consejo de Ministros de 9-dic-2025): «En las autopistas: 1. Autopista R-3/R-5. 2. Autopista R-2. 3. Autopista R-4. 4. Autopista M-12. […] se aplicarán las siguientes tarifas máximas». Nota de prensa del Ministerio (30-dic-2025): «las tarifas de las autopistas de peaje que gestiona la Sociedad Estatal de Infraestructuras de Transporte Terrestre (SEITT) —R-3/R-5; R-2; R-4, M-12, AP-7 (Cartagena-Vera), AP-36 (Ocaña-La Roda) y la AP-41 (Madrid-Toledo)—, tendrán en 2026 un incremento del 2%».
- AP-15. BON 258 de 30-dic-2025: «ACUERDO del Gobierno de Navarra, de 23 de diciembre de 2025, por el que se aprueban las tarifas base, los peajes base y los peajes con descuentos específicos de la Autopista de Navarra, para el período de 1 de enero a 31 de diciembre de 2026». Tabla: «Sur (Tudela-Pamplona) 0,110243 […] Norte (Pamplona-Irurtzun) 0,121368» €/km para ligeros.
- BOE-A-2026-19039 (RD 730/2026): «siendo gratuito completamente el tramo de la autopista AP-15 entre el enlace de la A-68 y la AP-68». Se refiere solo a la categoría «Pesados 2». No afecta a un turismo.
