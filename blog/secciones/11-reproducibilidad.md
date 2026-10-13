<!--
SECCIÓN: Reproducibilidad · RESPONSABLE: puente · ESTADO: borrador (actualizar con los comandos finales de T1.8 y T3.7).
-->

## Reproducibilidad

Todo el código, los datos del problema del viajero y los registros de este trabajo están en el
[repositorio del proyecto](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales). Para reproducir los
resultados con Python 3.12:

```bash
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
python run.py part1 --config configs/part1/demo.yaml
python run.py part2 --config configs/part2/demo.yaml --set costo.valor_hora=25
mkdocs build --strict -f blog/mkdocs.yml
```

Las semillas son fijas (`base_seed + run_id`), los parámetros se cambian con `--set clave=valor` sin editar el código, y
ningún experimento usa internet: los datos del problema del viajero están guardados en `data/processed/`.

### Optimización de hiperparámetros de la Parte 1

La optimización de hiperparámetros (HPO, Hyperparameter Optimization) de la Parte 1 se ejecuta con el subcomando
`hpo` de `run.py`:

```bash
# Demo (unos 7 s): pocos ensayos y semillas; escribe solo en carpetas *_hpo_demo, ignoradas por git
python run.py hpo --config configs/part1/hpo_demo.yaml

# HPO completa (unos 6-7 min con 6 procesos; depende del equipo): ensayos, selección, config afinada,
# experimento afinado y tabla comparacion.csv
python run.py hpo --config configs/part1/base.yaml --set workers=6

# Reanudación (unos 2 min): reutiliza los ensayos guardados sin repetir las corridas de ajuste
python run.py hpo --config configs/part1/base.yaml --set workers=6 --set hpo.reanudar=true

# Solo el experimento afinado, con la config que escribió la HPO
python run.py part1 --config configs/part1/tuned.yaml
```

La HPO completa escribe en `results/data/part1_hpo/` (un `ensayos_<unidad>.json` por unidad y `seleccion.json`), en
`configs/part1/tuned.yaml` y en el experimento afinado (`results/data/part1_tuned/` y `results/tables/part1_tuned/`,
con `comparacion.csv`); no reescribe los resultados por defecto de `results/data/part1/`. El archivo `tuned.yaml`
trae `hereda` (hereda de `base.yaml`), `salida`, `tablas` y los hiperparámetros que cambiaron; no se edita a mano.
La HPO completa exige que exista `results/data/part1/summary.json` (los resultados por defecto, que están versionados)
con las mismas semillas, presupuesto, funciones, dimensiones y métodos; si falta, el comando lo dice antes de correr y
hay que ejecutar primero `python run.py part1 --config configs/part1/base.yaml`.

Se versionan `results/data/part1_hpo/` (incluida la carpeta `regla_v1/`, con la evidencia de la primera versión de la
regla de selección), `configs/part1/tuned.yaml`, los `summary.json` y las tablas CSV de `results/tables/`. No se
versionan los JSON por corrida (`runs/` y `k1/runs/` de cada experimento), que se regeneran con los comandos de arriba,
ni las carpetas `*_demo`. No versionar los JSON por corrida es, por ahora, una decisión provisional del equipo.
