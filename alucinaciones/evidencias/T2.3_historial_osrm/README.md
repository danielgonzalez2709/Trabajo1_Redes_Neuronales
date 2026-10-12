# Evidencia: la respuesta de OSRM depende del historial de consultas del proceso (T2.3, ronda 2)

- Fecha: 2026-10-12 (UTC 04:30–05:20 aprox.).
- Quién: subagente `curador-datos` (Claude Opus 5.5). Prompt literal: `alucinaciones/prompts/T2.3-ejecucion.md`, ronda 2.
- Servidor: OSRM v26.10.0 (imagen fijada en `scripts/osrm/osrm.sh`), extracto `spain-261001`, MLD, `--threads 1`.
  Máquina Windows 11 + Docker Desktop.
- Los experimentos se ejecutaron en el scratchpad de la sesión y aquí se copian sin cambios (orquestador, 12-oct).

| Archivo | Qué muestra |
|---|---|
| `scripts/determinismo.py`, `det_check.json` | La misma URL repetida 10 veces da la misma respuesta con `--threads 1` |
| `scripts/primera.py`, `primera_threads1.txt` | La ruta de `26_29_rapida` cambia según la primera consulta después de arrancar |
| `scripts/historia.py`, `historia_threads1.txt`; `scripts/acotar.py`, `acotar_threads1.txt` | Cómo depende la respuesta de las consultas previas |
| `scripts/replay.py`, `replay.txt`, `replay_mismo.json`, `replay_inverso.json` | Mismo orden que `descargar_datos.py`: 0 de 2202 rutas distintas. Orden inverso: 50 de 2202 distintas |
| `scripts/separado.py`, `sep_{rapida,sin_peaje}_{mismo,inverso}.json` | Un proceso por alternativa: 0 `sin_peaje` con `toll`, igual en los dos órdenes; las `rapida` coinciden en weight con la corrida del 12-oct |
| `scripts/comparar.py`, `comparacion_11_vs_12.txt` | Corrida del 11-oct (16 hilos) frente a la del 12-oct (`--threads 1`) |

Los scripts esperan el servidor local en `http://127.0.0.1:5001` (o en los puertos temporales que indican) y los crudos de
`data/raw/osrm_2026-10-1{1,2}/`, que no se versionan.
