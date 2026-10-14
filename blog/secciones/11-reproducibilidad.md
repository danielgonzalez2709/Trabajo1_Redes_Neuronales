<!--
SECCIÓN: Reproducibilidad · RESPONSABLE: puente · ESTADO: completa (13-oct).
-->

## Reproducibilidad

Todo el código, los datos del problema del viajero y los registros de este trabajo están en el
[repositorio del proyecto](https://github.com/danielgonzalez2709/Trabajo1_Redes_Neuronales). Para reproducir los
resultados con Python 3.12:

```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
# macOS o Linux
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Demos y blog (python y mkdocs son los del entorno .venv)
python run.py part1 --config configs/part1/demo.yaml
python run.py part2 --config configs/part2/demo.yaml
mkdocs build --strict -f blog/mkdocs.yml
```

Las semillas son fijas (`base_seed + run_id`), los parámetros se cambian con `--set clave=valor` sin editar el código, y
ningún experimento usa internet: los datos del problema del viajero están guardados en `data/processed/`.

La demostración de la Parte 1 (Rastrigin 2D, PSO frente al descenso por gradiente de paso fijo, 5 corridas) imprime
las tablas, el tiempo de ejecución y la ruta de la figura de trayectoria que escribe,
`results/data/part1_demo/trayectoria_rastrigin_2d.png`. En el equipo de desarrollo (AMD Ryzen 5 3500U, Fedora 43)
tardó entre 3,7 y 3,8 s en tres repeticiones, y dos ejecuciones seguidas dejaron los mismos archivos byte a byte.
Falta medirla en un equipo distinto al de desarrollo.

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

### Experimento completo y figuras de la Parte 1

```bash
# Experimento por defecto: 20 configuraciones x 30 semillas y sensibilidad k = 1 de los dos GD
# (9 min 39 s en serie en el equipo donde se midió; workers reparte las corridas entre procesos)
python run.py part1 --config configs/part1/base.yaml
python run.py part1 --config configs/part1/base.yaml --set workers=6

# Sensibilidad del paso fijo en Rosenbrock con eta = 1.5e-4
python run.py part1 --config configs/part1/base.yaml --set "methods=[gdfijo]" --set "func=[rosenbrock]" \
    --set gd.eta.rosenbrock=1.5e-4 --set salida=results/data/part1_eta_1l --set tablas=results/tables/part1_eta_1l

# Datos del deslizador de eta y de las animaciones (no necesitan las corridas del experimento)
python scripts/part1_eta_deslizador.py
python scripts/part1_gif_trayectorias.py

# Figuras interactivas y GIF de las dos partes
python run.py figures
```

El experimento por defecto escribe en `results/data/part1/` un JSON por corrida (`runs/` y, para la sensibilidad
$k = 1$, `k1/runs/`) y el resumen `summary.json`, y en `results/tables/part1/` las tablas CSV. La clave `workers`
solo cambia el tiempo de ejecución, no el resultado. Los dos scripts escriben `results/data/part1/eta_deslizador.json`
y `results/data/part1/gif_trayectorias.json`.

De la Parte 1 se versionan los `summary.json` (por defecto, afinado y sensibilidad de $\eta$), `eta_deslizador.json`
y `gif_trayectorias.json`. Como los JSON por corrida no se versionan, en un clon limpio `python run.py figures` solo
regenera las curvas de nivel, el deslizador de $\eta$ y los GIF; para las figuras de convergencia, de cajas y del
enjambre avisa del comando que falta, y se regeneran después de ejecutar el experimento por defecto y el afinado
(`python run.py part1 --config configs/part1/tuned.yaml`).

### Parte 2

```bash
# Barrido del valor de la hora: 11 valores de w, MMAS, AS y GA, 10 corridas cada uno (unos 18 minutos)
python run.py part2 --config configs/part2/sweep_w.yaml

# Sensibilidad al consumo (5,6 l/100 km; el segundo valor con --set)
python run.py part2 --config configs/part2/sensibilidad_consumo.yaml
python run.py part2 --config configs/part2/sensibilidad_consumo.yaml --set costo.consumo_l100=6.2

# Óptimo exacto y umbrales exactos del valor de la hora para los tres consumos (unos 13 minutos)
python scripts/umbrales_exactos.py
```

El barrido escribe `results/data/part2/sweep_w.json`, `umbrales_w.json` y los historiales de convergencia; el script
exacto, `results/data/part2/umbrales_exactos.json`, que usan el mapa y la sección de resultados. La demo escribe en
`results/data/part2/demo/`, que no se versiona.

### Pruebas y diferencias entre equipos

`python -m pytest -q` corre las pruebas del proyecto (unas 2 700). Una sola necesita internet, porque consulta el
certificado del sitio del Ministerio del que sale el precio del combustible.

Con las mismas semillas, los resultados son idénticos en el mismo equipo. Entre sistemas operativos hay una diferencia
conocida: en Rastrigin, el descenso con búsqueda de Armijo cuenta un número algo distinto de evaluaciones, porque la
función coseno de cada plataforma puede diferir en el último bit y eso cambia cuántos retrocesos hace la búsqueda. En
2D la diferencia es menor de 0,02 % y en 3D de unos 5 % (19 882 frente a 20 796 evaluaciones medias de la función);
los valores finales y las tasas de éxito no cambian.

El reporte se publica en <https://danielgonzalez2709.github.io/Trabajo1_Redes_Neuronales/> con
`mkdocs gh-deploy -f blog/mkdocs.yml` desde `main`.
