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

Ponga un video autorizado en `data/demo.avi` o seleccione un perfil propio con
`--config`, cambiando allí `source.path`. Las rutas se resuelven desde el padre de `configs/`.

```sh
python scripts/run_demo.py                         # Sin mostrar video
python scripts/run_demo.py --debug                # Vista local; Q termina
python scripts/run_demo.py --max-frames 100
python -m pytest -q
```

Configure `imgsz` (320, 352, 384 o 416), `conf`, `vid_stride`, áreas y línea en YAML.
`detection.torch_threads` permite limitar hilos CPU; `0` conserva la selección
automática de Ultralytics. Los hilos usados se registran en el benchmark.
Se informa FPS incluyendo arranque de inferencia; no es un benchmark estable.
Los pesos se descargan una vez, antes de la demo.

La línea horizontal cuenta entrada hacia abajo por defecto (`positive`).
Use `up/down` para horizontal y `left/right` para vertical; `positive/negative`
se conservan por compatibilidad. Ajuste `position` y
`band_half_width` en coordenadas 0–1. El resumen incluye entradas, salidas y ocupación.
`occupancy.initial` calibra la ocupación al iniciar; la API Python ofrece
`OccupancyCounter.calibrate(n)`, `reset()` y `TripwireCounter.reset()`.

## Fuentes

Cambie únicamente `source` en un perfil propio, por ejemplo `configs/live-demo.yaml`:

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

Para archivos, `--realtime` limita la entrega al FPS original informado por
OpenCV y `--loop` repite el mismo archivo sin copiarlo. Cada vuelta reinicia
ByteTrack, tripwire, ocupación al valor inicial y estelas; los totales corresponden
a esa vuelta. También se configuran con `source.realtime` y `source.loop`.
Si el procesamiento es lento, la reproducción tarda más; no se descartan frames
para recuperar retraso. Ambos flags requieren una fuente `file`.

## Nuevo montaje fijo: perfil de diagnóstico

`configs/door-demo.yaml` usa **data/demo2.mov**: 1080×1920, 29,793 FPS,
2038 frames reproducibles y 67,922 s de contenido editado. La lista de edición
MOV explica los 2053 frames declarados; FFprobe confirmó 2038, y 2053 al ignorarla.
No se modifica el video ni se amplía la tolerancia ±2. `--verified-frames 2038`
expresa esa referencia independiente para este archivo; no reutilizarla en otros.

**No está suficientemente fiable para la demo de conteo.** Baseline 0/0; perfil
actual **4 IN / 1 OUT frente a 12/13**, error agregado 80%. Cinco eventos
visualmente consistentes; no hay correspondencia temporal exhaustiva de los 25
cruces, así que no se afirma precision/recall. Se detuvo el trabajo antes de las
dos repeticiones de validación final y la verificación del dashboard nuevo.
Evidencia y ensayos: [door-demo-evaluation.json](docs/door-demo-evaluation.json).

Perfil: horizontal y=0.60 en el umbral físico, banda [0.56,0.64], IN↓/OUT↑,
centroide, mínimo 3 observaciones, hasta 5 ausencias. YOLOv8n CPU, 416, conf=0.10,
stride=1, hilos auto; ByteTrack mantiene high/new=0.25, low=0.10, buffer=30 y
match=0.8, con `fuse_score: false`. La tolerancia depende del FPS de inferencias;
recalibrarla al cambiar de cámara/cadencia. Webcam/HTTP/RTSP siguen elegibles
cambiando `source` en YAML. No se introducen ROI, dos orientaciones ni ReID.

Para abrir este **perfil diagnóstico**, use dos terminales desde la raíz.
Los comandos se documentan; el dashboard nuevo queda pendiente de verificar:

```sh
.venv/bin/python scripts/run_demo.py --config configs/door-demo.yaml
APC_CONFIG=configs/door-demo.yaml .venv/bin/python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Abra http://127.0.0.1:8501, con los puertos 8765/8501 libres. Video/estelas solo
locales y en RAM; el archivo se repite y reinicia conteos por vuelta.
Para otra evaluación numérica completa (destino nuevo; no sobrescribe):

```sh
.venv/bin/python scripts/evaluate_counts.py --config configs/door-demo.yaml --expected-in 12 --expected-out 13 --verified-frames 2038 --diagnostics --output docs/nueva-door-evaluation.json
```

El JSON relaciona eventos, lados, edad, centroide, pérdidas, bordes y expiraciones.
Usa tiempo del contenido de OpenCV; si falta, declara fallback frame/FPS.
La evaluación no publica video ni telemetría y desactiva loop/realtime del perfil.
FPS de esta pasada: 52,48, incluyendo la primera inferencia; no es un benchmark.

## Video real anotado en el dashboard

Desde la raíz del proyecto, cierre el simulador/publicador y el Streamlit anterior
si ocupan los puertos 8765/8501. Ejecute estos dos comandos en terminales separadas:

```sh
.venv/bin/python scripts/run_demo.py --config configs/video-demo.yaml
```

```sh
APC_CONFIG=configs/video-demo.yaml .venv/bin/python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Abra **http://127.0.0.1:8501** en este equipo. `video-demo.yaml` usa
`data/demo1.mov`, activa el stream con estelas y establece `source.realtime: true`
y `source.loop: true` (equivalentes a `--realtime --loop`). El archivo no se copia
ni se modifica. Cada vuelta reinicia tracker, contadores y estelas; los conteos
corresponden a esa pasada. La referencia manual es IN=6/OUT=6, no un valor forzado
en el contador. `Ctrl+C` termina cada proceso.

Resultado final con calibración visual: **IN=1/OUT=0 frente a 6/6**. Errores
absolutos IN=5, OUT=6, total=11 (**91,67%**). La línea vertical está en x=0.64,
banda ±0.04 e IN hacia la izquierda. Se conservaron imgsz=320, conf=0.35,
stride=1 y tolerancia de dos frames perdidos; no se ajustaron al objetivo 6/6.
El conteo aún no es fiable. Diagnóstico por intervalo y resultados reproducibles
en [calibration-evaluation.json](docs/calibration-evaluation.json) y
[LIMITATIONS](docs/LIMITATIONS.md#evaluación-real-con-calibración-visual--2026-10-03).

**VIDEO LOCAL: no se guarda ni se transmite fuera de este equipo**.
El YAML normal conserva `visualization.stream: false`.

## Calibración de Conteo en Streamlit

Con los dos procesos anteriores abiertos, entre a http://127.0.0.1:8501 y abra
la barra lateral con la flecha de la esquina superior izquierda si está cerrada.
La sección **Calibración de Conteo** muestra la fuente y el perfil que usa el
contador conectado; funciona con archivo, webcam/cámara USB, HTTP y RTSP.

1. Elija **Vertical** para movimiento izquierda/derecha u **Horizontal** para
   arriba/abajo.
2. Mueva **Posición de la línea** hasta el umbral físico del paso. Los valores
   0–1 representan x/anchura o y/altura, independientemente de la resolución.
   Puede usar las flechas del teclado sobre el deslizador para ajustes finos.
3. Ajuste **Semiancho de banda** en 0–1: los límites son posición ± semiancho.
   La histéresis requiere semiancho positivo y ambos límites dentro de la imagen.
   Una propuesta inválida muestra un error y conserva la última calibración válida.
4. Elija el **Sentido de ENTRADA**: izquierda/derecha para vertical, arriba/abajo
   para horizontal. OUT es el movimiento opuesto.
5. Cada cambio válido actualiza automáticamente el video en el siguiente frame,
   sujeto al límite de FPS del MJPEG. La línea central sólida y su leyenda
   **LÍNEA DE CONTEO**, la banda discontinua y las flechas IN/OUT permiten verificarlo.
   Mover controles **reinicia los conteos y la ocupación de la sesión** al valor
   inicial, conservando captura y ByteTrack; termine de calibrar antes de contar.
6. Pulse **Guardar calibración** cuando esté conforme. Solo entonces se escribe
   `counting` en el **YAML activo del contador**, conservando fuente, comentarios y
   demás secciones. No hay selector de otro destino. Con `default.yaml` activo,
   puede previsualizar pero el guardado está bloqueado con un mensaje claro.

Los cambios de vista previa viven en RAM: se pierden al reiniciar el contador si
no los guarda. Mantenga `visualization.stream`, `show_line` y `show_band` activos
para revisar la geometría. El simulador numérico no ofrece calibración de cámara.

Para el pitch con una futura cámara, copie **solo el YAML** de ejemplo y edite su
bloque `source`; no necesita modificar Python:

```sh
cp configs/visual-demo.yaml configs/live-demo.yaml
```

```yaml
source:
  type: webcam
  index: 1  # Ajustar al índice real de la cámara USB o webcam.
  width: 640
  height: 480
```

Para HTTP/RTSP, reemplace ese bloque por `type: stream` y `url` como en la sección
Fuentes. Después ejecute en dos terminales:

```sh
python scripts/run_demo.py --config configs/live-demo.yaml
APC_CONFIG=configs/live-demo.yaml streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Calibre observando ese montaje y guarde en `live-demo.yaml`. La calibración del
MOV no se reutiliza automáticamente en la cámara. Flujo compartido:
fuente → YOLO/ByteTrack → zona normalizada → IN/OUT → ocupación → dashboard.

También existe una CLI sin cámara ni imágenes: muestra la propuesta y solo la
persiste con `--save`, siempre en el perfil activo y con la misma protección:

```sh
python scripts/calibrate_counting.py --config configs/live-demo.yaml --orientation vertical --enter-direction left --position 0.5 --band-half-width 0.04
```

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
La línea sólida azul se identifica como LÍNEA DE CONTEO; la banda es discontinua,
IN es verde y OUT rojo, con flechas físicas según la orientación. El panel incluye ocupación y la leyenda:
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
y conteos de tracks artificiales. La suite prohíbe escribir imágenes o videos:
las capturas sintéticas de tests están en RAM, y el transporte HTTP decodifica
MJPEG real generado en memoria. Las nuevas pruebas verifican ritmo del archivo,
reinicio de conteos al repetir, evaluación, warmup y medición de etapas.

## Benchmark y evaluación — hito 5

**Hito 5 completado:** 134 tests aprobados, demo comprobada por HTTP/AppTest y
cinco evaluaciones de conteo documentadas. Se usaron las 144 mediciones existentes,
sin repetir el barrido. OpenCV
declara 1.308 frames del MOV y entrega 1.307: diferencias de hasta **±2 frames**
se registran como advertencia, por instrucción del usuario; no bloquean la
evaluación. Una diferencia mayor sigue produciendo error.

Se mantienen **imgsz=320 / vid_stride=1**. A cuatro hilos, el benchmark en este
equipo dio medias de **66,72 FPS sin stream / 61,54 con stream**. La evaluación
por defecto dio **0/0 frente a 6/6 (100% de error agregado)**; la mejor alternativa
evaluada, 416/1, dio **0/2 (83,33%)**. Se requiere calibrar y validar el conteo;
esas mediciones preceden a la calibración visual actual descrita arriba.
La documentación de uso y limitaciones está actualizada; la precisión sigue pendiente.

El video local autorizado es **`data/demo1.mov`**; no se renombra ni se incluye
en git. Referencia manual: **6 entradas y 6 salidas**. Es solo lectura y no se
generan imágenes ni videos de salida. El benchmark corre **en este equipo**;
un solo video no valida precisión general. Metodología, tablas, recomendaciones y límites
en [BENCHMARK](docs/BENCHMARK.md); estado de ejecución en [PROGRESS](docs/PROGRESS.md).

```sh
# Evaluación final del perfil calibrado: una pasada, sin realtime ni loop.
python scripts/evaluate_counts.py --config configs/video-demo.yaml --expected-in 6 --expected-out 6

# Alternativa puntual, sin modificar la calibración del YAML.
python scripts/evaluate_counts.py --video data/demo1.mov --expected-in 6 --expected-out 6 --imgsz 416 --vid-stride 1 --torch-threads 4

# Máxima velocidad: sin realtime, 12 combinaciones, stream apagado/encendido,
# video real y AVI sintético preexistente, warmup 30, tres repeticiones.
python scripts/benchmark_fps.py --torch-threads 4 --output docs/nueva-medicion.json
```

El benchmark conserva solo estadísticas JSON y rechaza sobrescribir resultados.
`--imgsz 320 352`, `--vid-stride 1 2`, `--warmup`, `--repeats` y `--max-frames`
permiten acotar otra medición. Usa por defecto `data/demo.avi` como comparación
sintética preexistente; `--synthetic-video` permite indicar otra entrada autorizada.
Mide FPS procesados y de origen por separado; stride no debe inflar la cifra de
imágenes analizadas. El modo stream mide overlay/JPEG en RAM, sin navegador ni
transporte HTTP. No se deben ejecutar otras inferencias o tests en paralelo al medir.

El evaluador informa IN/OUT, error absoluto y porcentaje por dirección, y suma
errores absolutos sin cancelarlos entre direcciones. Si la referencia es cero y
hay detecciones, su porcentaje es `null` (indefinido). Los conteos y umbrales
requieren calibración y validación independiente; no se ajustan línea, banda ni
confianza automáticamente a este video.

Estado: [PROGRESS](docs/PROGRESS.md). Supuestos: [DECISIONS](docs/DECISIONS.md).
Alcance: [LIMITATIONS](docs/LIMITATIONS.md).
