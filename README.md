# APC Metro

Prototipo universitario de conteo de pasajeros. Procesamiento local en notebook
sin GPU; no almacena frames, rostros ni videos de salida. El modo normal publica
solo telemetría numérica; el video local anotado es una opción de demostración.

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

## Fuentes

Cambie únicamente `source` en `configs/default.yaml`:

```yaml
# Webcam del notebook; puede requerir permiso del sistema operativo.
source:
  type: webcam
  index: 0
  width: 640
  height: 480
```

```yaml
# URL del flujo de video, no la página de administración de la cámara.
source:
  type: stream
  url: "http://192.168.1.20:8080/video"  # También rtsp://...
  open_timeout_ms: 5000
  read_timeout_ms: 2000
```

Conserve las otras secciones del YAML. Webcam y stream priorizan frames recientes;
archivo conserva todos. Ante desconexión, el programa termina con error y libera
la fuente. Reinicie después de recuperar la conexión.

## Dashboard y demo sin cámara

**Hito 4 completado:** suite de 83 pruebas aprobada, simulador y servidor Streamlit
verificados por HTTP, y dashboard ejecutado con AppTest contra la API real de cuatro
vagones. Consulte [la evidencia y el alcance de la verificación](docs/PROGRESS.md).

Abra dos terminales desde la raíz, con `.venv` activado:

```sh
# Terminal 1: cuatro vagones simulados; Ctrl+C termina.
python scripts/simulate_telemetry.py
```

```sh
# Terminal 2: dashboard local.
streamlit run dashboard/app.py --server.address 127.0.0.1
```

Abra http://127.0.0.1:8501. El panel indica **SIMULACIÓN**, muestra los tres colores
y se actualiza solo. El gris significa dato de más de `stale_after_seconds` segundos.
La ocupación simulada oscila en ciclos de dos minutos, sin crecimiento ilimitado:

| Vagón | Perfil | Ocupación con capacidad 100 |
| --- | --- | --- |
| 1 | Bajo | 10–30 personas (verde) |
| 2 | Medio | 50–70 personas (amarillo) |
| 3 | Alto | 80–100 personas (rojo) |
| 4 | Variable | 0–110 personas (cambia de color) |

Los perfiles se repiten si configura más vagones. La sección `simulation` del
YAML permite ajustar período, objetivos, variación, máximo y ocupación inicial
del vagón variable. Los cambios son de personas enteras y las entradas/salidas
son acumulativas: `occupancy = initial_occupancy + entries - exits` incluso al
comenzar otro ciclo. El máximo se redondea hacia abajo para no superar el 110%.

Para usar cámara/video, cierre el simulador y ejecute `python scripts/run_demo.py`
en la primera terminal. Un archivo termina al llegar al final; en ese momento
también se cierra la API y el panel indica desconexión.

La API sirve `GET http://127.0.0.1:8765/telemetry` y `/health`, solo en este equipo.
`telemetry.port`, `wagon_id`, `interval_seconds` y `simulated_wagons` se configuran
en YAML. Para un YAML alternativo use `--config ruta/configs/default.yaml` en los
scripts y `APC_CONFIG=ruta/configs/default.yaml streamlit run dashboard/app.py`.

Campos por vagón: `wagon_id`, `entries`, `exits`, `initial_occupancy`, `occupancy`,
`capacity`, `level` (0 verde, 1 amarillo, 2 rojo), `timestamp` (Unix), `fps` y
`simulated` (0/1). `/telemetry` no transmite imágenes, coordenadas ni IDs de personas.
No ejecute dos publicadores en el mismo puerto. `Ctrl+C` libera servidor y fuente.

## Vista en vivo anotada — hito 4.5

**Implementada; verificación integrada final pendiente.** La suite pasó 108 pruebas
y la CLI sintética terminó correctamente. Una comprobación HTTP adicional se inició
después de que terminara esa demo finita y recibió conexión rechazada; el trabajo
se detuvo según la regla acordada. Evidencia en [PROGRESS](docs/PROGRESS.md).

Para la demo visual sin cámara, pesos YOLO ni archivos de video, cierre cualquier
simulador/publicador anterior y use estas dos terminales desde la raíz:

```sh
# Terminal 1: mantener activo mientras se usa el dashboard.
python scripts/run_demo.py --fake-tracks --config configs/visual-demo.yaml
```

```sh
# Terminal 2: abrir http://127.0.0.1:8501 en este mismo equipo.
APC_CONFIG=configs/visual-demo.yaml streamlit run dashboard/app.py --server.address 127.0.0.1
```

`configs/visual-demo.yaml` activa explícitamente el video y las estelas; sus campos
omitidos usan los valores de las dataclasses, no heredan cambios de `default.yaml`.
En `configs/default.yaml`, **`visualization.stream: false` sigue siendo el valor
normal**. Para usar cámara o archivo, configure su fuente y quite `--fake-tracks`.

La sección `visualization` controla línea/banda, cajas, IDs, estelas, contadores,
colores `#RRGGBB`, `trail_length`, `jpeg_quality` (1–100) y `max_fps` (por defecto 10).
La línea es azul; IN es verde y OUT rojo. El panel incluye ocupación y la leyenda:
**VIDEO LOCAL: no se guarda ni se transmite fuera de este equipo**.

El servidor existente ofrece `/video` como MJPEG exclusivamente en 127.0.0.1.
Solo conserva el último JPEG en RAM y reemplaza el anterior, sin historial ni
grabación. `/video/status` indica si está habilitado y tiene un frame reciente.
Video desactivado devuelve HTTP 404; habilitado sin frames recientes, HTTP 503.
El dashboard muestra un aviso en ambos casos. El JPEG caduca con
`telemetry.stale_after_seconds`; las conexiones terminan al cerrar el publicador.

`--fake-tracks` genera dos cajas con IDs nuevos por ciclo: una entra y otra sale,
alimentando el TripwireCounter y overlay reales. Por defecto, cada ciclo de 8 s
produce IN +1 y OUT +1, con ocupación intermedia 1 y final 0 si se inicia vacío.
`simulation.fake_fps`, `fake_cycle_seconds` y `source.width/height` controlan la
escena artificial. `--max-frames 120` finaliza un ciclo y **cierra también la API**;
omita ese límite para revisar el panel sin que termine antes de abrirlo.

El simulador multivagón `simulate_telemetry.py` sigue publicando solo números.
La demo de tracks usa un único vagón para mantener iguales los conteos visibles
en el video y en la telemetría; no mezcla esos cruces con ocupaciones de prueba ajenas.

## Validación

```sh
python -m pytest -q
```

La suite usa tracks, video sintético, HTTP local real y Streamlit AppTest. No abre
la cámara física ni descarga pesos. La prueba HTTP requiere permitir sockets locales.
La regresión de simulación recorre 10.000 pasos por capacidad y comprueba límites,
saldo, acumuladores no decrecientes y cambios graduales. También verifica que los
perfiles oscilen y que los tres colores sigan presentes durante varios ciclos.
Las pruebas del hito 4.5 incluyen overlay sin mutación del frame, MJPEG por HTTP
local, límites de FPS, apagado por defecto, cierre, prohibición de IO de imágenes
y conteos de tracks artificiales. No se certifica precisión en personas ni la meta
de 20 FPS sostenidos; el hito 5 no se ha iniciado.

Estado: [PROGRESS](docs/PROGRESS.md). Supuestos: [DECISIONS](docs/DECISIONS.md).
Alcance: [LIMITATIONS](docs/LIMITATIONS.md).
