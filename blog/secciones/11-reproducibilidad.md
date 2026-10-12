<!--
SECCIÓN: Reproducibilidad · RESPONSABLE: puente (Daniel) · ESTADO: borrador (actualizar con los comandos finales de T1.8 y T3.7).
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
