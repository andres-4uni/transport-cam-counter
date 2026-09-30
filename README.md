# APC Metro

Prototipo universitario de conteo de pasajeros. Procesamiento local en notebook
sin GPU; no almacena frames, rostros ni videos de salida.

## Instalación (Python 3.11)

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
mkdir -p models
curl -L --fail https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt -o models/yolov8n.pt
```

`requirements-lock.txt` registra las versiones verificadas en macOS ARM64;
para reproducirlas: `python -m pip install -r requirements-lock.txt`.

Ponga un video autorizado en `data/demo.avi` o cambie `source.path` en
`configs/default.yaml`. Las rutas se resuelven desde el padre de `configs/`.

```sh
python scripts/run_demo.py                         # Sin mostrar video
python scripts/run_demo.py --debug                # Vista local; Q termina
python scripts/run_demo.py --max-frames 100
python -m pytest -q
```

Configure `imgsz` (320, 352, 384 o 416), `conf`, `vid_stride`, áreas y línea en YAML.
Se informa FPS incluyendo arranque de inferencia; no es un benchmark estable.
Los pesos se descargan una vez, antes de la demo.

La línea horizontal cuenta entrada al moverse hacia abajo por defecto (`positive`).
En orientación vertical, positivo es hacia la derecha. Ajuste `position` y
`band_half_width` en coordenadas 0–1. El resumen incluye entradas, salidas y ocupación.
`occupancy.initial` calibra la ocupación al iniciar; la API Python ofrece
`OccupancyCounter.calibrate(n)`, `reset()` y `TripwireCounter.reset()`.

Estado: [PROGRESS](docs/PROGRESS.md). Supuestos: [DECISIONS](docs/DECISIONS.md).
Alcance: [LIMITATIONS](docs/LIMITATIONS.md).
