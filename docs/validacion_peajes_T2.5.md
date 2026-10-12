# Validación de peajes por ruta (T2.5, Spec §7.2 Bloque 3)

Fecha de cálculo: 2026-10-12. Fecha de corte de las tarifas: 2026-10-01. Todo sale de archivos versionados
(`scripts/asignar_peajes.py`, sin red). Pruebas: `tests/test_asignar_peajes.py` y `tests/test_peajes_anclas.py`.

## 1. Método en cinco líneas

1. Un paso de `rutas_pasos_peaje.csv` sin `ref` es un enlace (rampa): no se cobra. La tarifa va por tramo, no por enlace
   (479 pasos, 274 km).
2. Un paso con `ref` se asigna a una **cadena** de `peajes_cadenas.csv` (tramos contiguos de una autopista, en orden):
   por `ref` y por cercanía a sus anclas, no por el prefijo del nombre.
3. Cada extremo del paso se sitúa en el **km de la cadena** con `peajes_anclas.csv` (ajuste a un ancla a ≤ 1,5 km; si no,
   proyección sobre la poligonal de anclas). No se usa `n_intersecciones_toll / n_intersecciones` para medir km: da
   hasta un 25 % de error en pasos parciales y no dice en qué tramo está.
4. Por ruta y cadena se cobra el recorrido `[mín, máx]` de sus pasos (OSM deja sin clase `toll` algunos trozos de
   autopista, p. ej. 8 km de la AP-7 de Málaga).
5. Peaje = Σ tarifa del tramo × (km recorridos / km del tramo); desde el 95 % del tramo se cobra la tarifa completa.
   **Suma de tramos** también en peaje cerrado (decisión del 12-oct, Spec v1.9). Las filas `sin_peaje` que pasan por la
   clase `toll` (26) se cobran igual.

`km_peaje` = km recorridos en tramos con tarifa > 0. `vias_peaje` = vías con importe > 0, separadas por `;`, en el
orden en que aparecen en la ruta. `rutas_peajes_detalle.csv` guarda una fila por ruta y tramo (auditable).

## 2. Los cinco pares obligatorios

Todos los importes son ligeros, efectivo/tarjeta, tarifa vigente el 2026-10-01.

| Par | Ruta `rapida` de OSRM | Peaje calculado | Referencia oficial | Diferencia | Comentario |
|---|---|---|---|---|---|
| Bilbao–Zaragoza (44, 46) | 305,5 km; AP-68 293,2 km, 94 intersecciones `toll` | **41,50 €** (AP68-01..07: 6,85 + 6,00 + 0,90 + 1,90 + 4,85 + 9,40 + 11,60), `km_peaje` 291,697 | 39,90 € (Ministerio de Transportes, tarifas AP-68 vigentes desde 01/01/2026, p. 1, fila BILBAO–ZARAGOZA; `data/raw/peajes_2026-10-12/mitma_tarifas_2026_ap-68.pdf`) | **+1,60 € (+4,0 %)** | Peaje cerrado: la tabla oficial no es aditiva (p. 1: Bilbao–Altube 6,85 + Altube–Zaragoza 33,45 = 40,30 ≠ 39,90). Cada tramo suelto sí coincide con la tabla oficial (Bilbao–Altube 6,85; Altube–Autop. Burgos 6,00; Autop. Burgos–Zambrana 0,90; Zambrana–Haro 1,90; Haro–Logroño 4,85; Logroño–Autop. Navarra 9,40; Autop. Navarra–Zaragoza 11,60). La `sin_peaje` (294,3 km por N-232/N-240) cuesta 0,00 €. |
| Sevilla–Cádiz (9, 37) | 123,6 km; AP-4 92,8 km, **0** intersecciones `toll` | **0,00 €** (las dos alternativas) | 0,00 €: AP-4 sin peaje desde el 1-ene-2020, fin de la concesión de Aumar (Ministerio de Transportes, "Peajes dependientes de la AGE"; fila AP4-01) | 0,00 | Confirma la regla del Spec: un nombre "AP-" no implica peaje. OSRM no marca `toll` en la AP-4. |
| Madrid–Toledo (26, 41) | 74,7 km; A-42 66,7 km, 0 intersecciones `toll` | **0,00 €** (las dos alternativas) | 0,00 €: la A-42 es "Autovía" en el Catálogo RCE 2025. La AP-41 (SEITT, 5,95 € en efectivo, fila AP41-01) es la alternativa de pago que OSRM no elige | 0,00 | Si el viajero tomara la AP-41 pagaría 5,95 €; el modelo `rapida` no la usa porque la A-42 es más rápida. |
| Alicante–Murcia (2, 28) | 81,9 km; A-7 39,3 km, A-70 28,5 km, A-31 3,0 km, 0 intersecciones `toll` | **0,00 €** (las dos alternativas) | 0,00 €: A-31, A-70 y A-7 son "Autovía" en el Catálogo RCE 2025; la AP-7 Alicante–Cartagena (AP7-AC-01/02) no está en el corredor | 0,00 | La AP-7 Circunvalación de Alicante es gratuita (BOE-A-2025-25961). |
| A Coruña–Pontevedra (13, 33) | 133,5 km; AP-9 126,5 km, 33 intersecciones `toll` | **16,35 €** (AP9-01 0,00 + AP9-02 8,80 + AP9-03 0,00 + AP9-04 7,55), `km_peaje` 114,0 | 16,35 € (calculadora oficial de Audasa, origen "A Coruña" y destino "Pontevedra", ligeros; `alucinaciones/evidencias/T2.4_audasa_calculadora_2026-10-12.json`) | **0,00** | AP9-03 (Santiago norte–sur) = 0 € confirmado. La `sin_peaje` (130,3 km por N-550) cuesta 0,00 €. |

Evidencia de las vías que usa cada ruta: `alucinaciones/evidencias/T2.5_vias_5_pares.json` (la genera
`T2.5_vias_5_pares.py` desde los crudos de OSRM, que no se versionan).

## 3. Contraste adicional con tarifas oficiales publicadas

Rutas completas o casi completas de una autopista, comparadas con la tarifa que publica el operador. No son
validaciones obligatorias; muestran el error típico de "suma de tramos".

| Par | Calculado | Referencia | Diferencia | Observación |
|---|---|---|---|---|
| Vitoria–Bilbao (0, 44) | 6,85 € | Bilbao–Altube 6,85 € (Ministerio, AP-68 p. 1) | 0,00 | Entra por Altube. |
| Burgos–Bilbao (7, 44) | 12,85 € | Bilbao–Autop. Burgos 12,40 € (ídem) | +0,45 (+3,6 %) | Peaje cerrado. |
| Vitoria–Zaragoza (0, 46) | 27,75 € | Zambrana–Zaragoza 26,80 € (ídem) | +0,95 (+3,5 %) | Entra por Zambrana. |
| Logroño–Zaragoza (24, 46) | 19,60 € | Agoncillo–Zaragoza 18,85 €; Logroño–Zaragoza 20,70 € (ídem) | +0,75 (+4,0 %) frente a Agoncillo | OSRM entra a 10 km al este de Logroño (-2,34, 42,45), cerca de Agoncillo. |
| Pamplona–Zaragoza (29, 46) | 23,00 € | Autop. Navarra–Zaragoza 11,60 € + AP-15 Sur 11,40 € | 0,00 | Las dos piezas coinciden. |
| Pontevedra–Santander (33, 35) | 15,39 € | Guísamo–Pontevedra 15,40 € (Audasa) | −0,01 | Sale de la AP-9 en el enlace con la A-6. |
| **A Coruña–Madrid (13, 26)** | 14,55 € (AP-9 **1,05** + AP-6 13,50) | A Coruña–Guísamo 2,05 € (Audasa) + AP-6 completa 15,70 € = 17,75 € | **−3,20 (−18 %)** | La AP-9 de A Coruña al enlace con la A-6 se cobra a 1,05 € frente a 2,05 € oficiales (44 filas). |
| Madrid–Valladolid (26, 43) | 13,25 € | AP-6 Villalba–Adanero completa 15,70 € (nota de AP6-01) | **−2,45 (−15,6 %)** | Mayor sesgo sistemático: la AP-6 aparece en 182 filas. Suma de tramos 5,65 + 3,20 + 4,65 = 13,50 € frente a 15,70 € del recorrido completo (−2,20 €, la regla de suma de tramos). Además la ruta sale de la AP-6 unos 1,8 km antes de Adanero y paga el 94,6 % del último tramo (4,40 € en vez de 4,65 €): eso explica solo −0,25 €. |
| Madrid–Segovia (26, 36) | 8,70 € | Villalba–Segovia explotación conjunta normal 8,60 € (nota de AP61-01) | +0,10 (+1,2 %) | |
| Madrid–Ávila (4, 26) | 10,60 € | Villalba–Ávila explotación conjunta normal 11,85 € (nota de AP51-01) | −1,25 (−10,5 %) | |
| Oviedo–León (22, 31) | 16,50 € | Campomanes–León 16,20 € (nota de AP66-01) | +0,30 (+1,9 %) | |
| Bilbao–Donostia (18, 44) | 13,25 € | Bilbao–Donostia (Bidegi) 13,81 € (nota de AP8-01) | −0,56 (−4,1 %) | |
| Vitoria–Donostia (0, 18) | 17,61 € | Eibar–Vitoria 10,04 € + Eibar–Donostia 7,43 € = 17,47 € | +0,14 (+0,8 %) | |
| Barcelona–Tarragona (6, 39) | 13,45 € | Barcelona–El Vendrell O. 13,45 € (folleto Aucat) | 0,00 | |
| Málaga–Cádiz (9, 27) | 11,95 € | Málaga–Estepona 9,55 € + Estepona–Guadiaro 2,45 € = 12,00 € | −0,05 | |

Sesgo total: la suma de tramos queda entre −18,0 % y +4,0 % frente al recorrido publicado. Tres casos quedan fuera de
±5 % y los tres usan la AP-6: A Coruña–Madrid −18,0 %, Madrid–Valladolid −15,6 % y Madrid–Ávila −10,5 %. Sus causas
conocidas son la AP-6 (−14 % en recorrido completo: 13,50 frente a 15,70 €) y el enlace de A Coruña (−49 % en los 12 km hasta
el enlace: 1,05 frente a 2,05 €); en Madrid–Ávila no se separó la causa. Los demás casos están entre −4,1 % y +4,0 %.

## 4. Lo que no se cobra y por qué

| Caso | Pasos | Qué se hizo |
|---|---|---|
| Enlaces sin `ref` (rampas) con clase `toll` | 479 (274 km), todos < 1,5 km | No se cobran: la tarifa va por tramo. |
| `ref` = `N-622` (Álava, entre Vitoria y el enlace de Altube) | 9 (168,6 km de paso; solo unos 2 km con `toll`) | Sin fila en `peajes_tramos.csv` (carretera nacional): es la clase `toll` de OSM en un enlace. Aviso `ref_sin_cadena`. |
| `ref` = `PA-34` (Pamplona) | 11 (10,8 km) | Ídem. |
| `ref` = `GI-20` (Donostia) | 18 (46,6 km) | Ídem; queda justo después de la salida 27 de la AP-8, donde acaba AP8-03. Sin fila de tarifa: por verificar si ese trozo es de pago. |
| Tramos sin ninguna ruta | AP4-01, AP41-01, AP51-02 (gratuito), AP7-AC-01/02, R3-01 | `R3-01` (Madrid M-40–M-50, 0,95 €) no se cobra en ninguna ruta: OSRM entra a la R-3 en la M-50 y la A-3 hasta ahí es libre. |

Todos los avisos están en `data/processed/peajes_avisos.csv` (38 filas, todas `ref_sin_cadena` de la alternativa `rapida`).

## 5. Sensibilidad a los parámetros del método

Total de `peaje_eur` de las 560 rutas con pasos de peaje: 8 693,22 €. Cambiando un parámetro cada vez:

| Parámetro | Valor | Total | Rutas que cambian | Mayor cambio en una ruta |
|---|---|---|---|---|
| ajuste a un ancla (`SNAP_M`) | 1,0 km / 2,0 km / sin ajuste | 8 687,15 / 8 696,97 / 8 688,31 | 33 / 15 / 110 | 0,21 / 0,25 / 0,21 € |
| tarifa completa desde (`FRACCION_COMPLETA`) | 90 % / 100 % | 8 696,97 / 8 693,22 | 15 / 0 | 0,25 / 0,00 € |

`SNAP_M` y `FRACCION_COMPLETA` son parámetros elegidos por el curador (sin fuente que los respalde; ver el docstring de
`scripts/asignar_peajes.py`). Los otros (`SOLAPE_MIN_KM`, `DIST_MAX_*`) no cambian ninguna ruta al anularlos. Los parámetros apenas importan: lo que pesa es la regla de suma de tramos (sección 3).

## 6. Qué es dato medido y qué es decisión del curador

- **Medido o citado**: tarifas y km (T2.4), nodos de OSM (14 anclas, ids en `fuente_coord`), puntos de paso de OSRM (6) y
  centroides de extremos de paso (57, recalculados por `tests/test_peajes_anclas.py`).
- **Decisión del curador (T2.5), por verificar**: qué cluster de extremos de paso corresponde a cada enlace de la tabla
  (se identificó comparando km de pasos con km de tramos: p. ej. AP-6, pasos de 12,3 / 19,8 / 28,6 km frente a tramos de
  9,6 / 19,7 / 28,3 km); los anclas con `origen_km` distinto de "inicio/fin del tramo" (14: AP-68 ×4, R-4 ×3, AP-7 ×6, AP-9 ×1) y
  los 4 anclas equivalentes a un extremo (Basauri, Zaragoza, Castelldefels, Urgoiti).
- **Sin coordenada**: AP-7 Alicante, AP-41 y AP-4 (ninguna ruta pasa por ellas); R3-01 y el resto de interiores de cadena
  se interpolan por km entre anclas vecinos.

## 7. Reproducir

```
.venv/Scripts/python.exe scripts/asignar_peajes.py          # reescribe rutas.csv y regenera los otros 3 archivos
.venv/Scripts/python.exe -m pytest tests/test_asignar_peajes.py tests/test_peajes_anclas.py
```

Archivos: `data/processed/{rutas.csv, rutas_peajes_detalle.csv, peajes_avisos.csv, peajes_resumen.json,
peajes_cadenas.csv, peajes_anclas.csv}`.
