# Progreso

## Hito 1 — completado
- Implementados esqueleto, configuración validada, captura de archivo en hilo,
  YOLOv8n/ByteTrack en CPU, filtrado de área y vista anotada local optativa.
- Validación: `.venv/bin/python -m pytest -q`: **18 passed**.
- Ejecutado `.venv/bin/python scripts/run_demo.py --debug --max-frames 80`:
  **80 frames, 33.23 FPS**, YOLOv8n real en CPU y vista OpenCV activada,
  con video sintético sin personas. Esto valida ejecución, no precisión de detección.
- `compileall` y `git diff --check` sin errores.
- Entorno: inicialmente Python 3.14; instalado Python 3.11.15. La descarga
  requirió acceso de red fuera del sandbox. La primera demo dentro del sandbox
  terminó (40 frames, 3.72 FPS), pero macOS avisó de un servicio gráfico no accesible;
  repetida fuera del sandbox sin ese aviso. Caché Ultralytics creada explícitamente.
- Dependencias exactas registradas en `requirements-lock.txt` (macOS ARM64).
- Ningún test falló. Siguiente: hito 2, conteo puro y ocupación.

## Hito 2 — completado
- Implementado tripwire puro con banda, vida mínima, caducidad y retorno del mismo ID.
- Implementada ocupación con calibración/reseteo, límites del semáforo e integración en demo.
- Validación acumulada: `.venv/bin/python -m pytest -q`: **48 passed**.
- Ejecutada demo CPU sobre 40 frames sintéticos; salida numérica con cero entradas,
  salidas y ocupación. Cruces reales del contador verificados con tracks simulados.
- `git diff --check` sin errores. Ningún test falló. Siguiente: fuentes webcam/stream.

## Hito 3 — completado
- Fuentes webcam/HTTP(S)/RTSP seleccionables por YAML, cola reciente para vivo,
  timeouts de stream, errores explícitos y liberación de recursos.
- `.venv/bin/python -m pytest -q`: **61 passed**, incluida lectura HTTP real con
  OpenCV/FFmpeg y servidor 127.0.0.1 (requiere sockets fuera del sandbox).
- Verificados selección YAML, parámetros de webcam/timeouts, reemplazo de frames,
  desconexión, apertura fallida y liberación de capturas. Webcam y RTSP simulados.
- `compileall` y `git diff --check` sin errores. Ningún test falló.
- Siguiente: hito 4, API numérica local y dashboard multivagón.

## Hito 4 — completado (2026-09-30)
- API HTTP local en memoria, esquema numérico validado y publisher integrado en la demo.
- Simulador multivagón y dashboard Streamlit con semáforos, conteos, identificación
  visible de simulación y estado sin señal para datos viejos.
- Corregidas las tres pruebas del dashboard con una ruta absoluta compartida:
  `Path(__file__).resolve().parents[1] / "dashboard" / "app.py"`.
- Suite completa: `.venv/bin/python -m pytest -q` → **68 passed in 1.74s**.
  Ejecutada fuera del sandbox para habilitar los sockets locales de las pruebas.
- Servicios ejecutados después de aprobar la suite:
  - `.venv/bin/python scripts/simulate_telemetry.py`
  - `.venv/bin/python -m streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8501`
- Verificación HTTP: `/health` de la API en el puerto 8765 devolvió **200** con
  `{"ok": 1}`; `/_stcore/health` de Streamlit en 8501 devolvió **200** con `ok`;
  la página `/` devolvió **200**, contenido HTML.
- Dos lecturas de `/telemetry` confirmaron **cuatro vagones**, `simulated=1`,
  timestamps crecientes y entradas cambiantes.
- Dashboard ejecutado mediante AppTest **contra la API real, sin mocks**:
  cero excepciones y errores, etiqueta SIMULACIÓN, tarjetas VAGÓN 01–04 y
  **4 / 4** vagones con señal. Una segunda ejecución actualizó entradas de **650 a 655**.
  La suite también verifica los tres colores, datos caducados y desconexión.
- Límite de esta comprobación: no hubo inspección visual en navegador. La herramienta
  de navegador no estuvo disponible (IAB no disponible; interfaz nativa sin poder
  iniciar y runtime Node ausente al reintentar). Se verificaron HTTP, ejecución de
  Streamlit y actualización de métricas mediante AppTest; no se afirma revisión visual.
- Antecedente resuelto: en el commit WIP `3a0fe43` hubo **65 aprobadas y 3 fallidas**
  porque Streamlit 1.64.0 resolvía la ruta relativa desde `tests/`. Se había detenido
  el trabajo; esta corrección y validación fueron autorizadas al retomarlo.
- Dependencias exactas en `requirements-lock.txt`. No se modificó el producto ni
  se añadieron dependencias para corregir los tests.
- Hito 5 **no iniciado**, por instrucción del usuario. Hito 6 no iniciado.

## Corrección de simulación — completada (2026-09-30)

- Problema: las fórmulas anteriores acumulaban más entradas que salidas para todos
  los vagones, de modo que la ocupación crecía indefinidamente y todos acababan rojos.
- Implementados ciclos acotados en el generador usado por `simulate_telemetry.py`,
  con objetivos y período configurables en `configs/default.yaml`.
- Rangos por defecto con capacidad 100: **10–30, 50–70, 80–100 y 0–110**.
  Entradas/salidas acumulativas, coherentes con el saldo inicial y sin reinicio al
  cambiar de ciclo. Los primeros tres vagones mantienen verde, amarillo y rojo;
  el cuarto cambia entre los tres colores.
- `.venv/bin/python -m pytest -q`: **83 passed in 2.44s**. Regresión de 10.000 pasos
  para capacidades 1, 37, 100 y 317; valida límites, saldo, acumuladores y gradualidad.
  Otras pruebas cubren oscilación, colores, paso 1.000.000.000, cadencia y configuración.
- Reiniciado el simulador local; comprobado por HTTP y con AppTest conectado a la
  API real: cuatro vagones con señal, ocupación acotada, saldo consistente y los tres
  estados presentes en el dashboard, sin errores.
- Sin fallos de pruebas. Hito 5 no iniciado; cambios preexistentes en `AGENTS.md`
  conservados fuera de esta corrección.

## Hito 4.5 — implementación hecha; validación integrada detenida (2026-10-01)

- Commit `91ec1e7`: configuración visual y overlay puro. **94 passed in 2.49s**,
  incluidos colores, toggles, estelas acotadas, copia del frame y stream apagado.
- Commit `e07d2df`: MJPEG local en memoria. **99 passed in 5.06s**. HTTP real,
  cabeceras y JPEG decodificado, apagado, espera sin frames, caducidad, FPS, cierre
  de lectores y prohibición de IO de archivos durante overlay/codificación/HTTP.
- Commit `80b3a39`: dashboard con estado real del video, leyenda local y modo
  `--fake-tracks`. Suite completa: **108 passed in 7.66s**. Tres ciclos producen
  IN=3, OUT=3 y ocupación final=0 en ambas orientaciones/sentidos; alcanza 1 durante
  el ciclo. La CLI fake se prueba sin detector, captura ni escritura de imágenes.
- Ejecución real: `.venv/bin/python scripts/run_demo.py --fake-tracks --config
  .cache/hito45/configs/demo.yaml --max-frames 600`. Configuración temporal de prueba:
  puerto 18765, fake_fps=30, fake_cycle_seconds=1, stream=true y estelas activas.
  Salida exitosa: `{"frames": 600, "fps": 29.93, "entries": 20, "exits": 20,
  "occupancy": 0}`. Es una comprobación funcional, no un benchmark del hito 5.
- **Falló la comprobación integrada posterior** al solicitar `/video/status` en
  127.0.0.1:18765: `URLError: <urlopen error [Errno 61] Connection refused>`.
  La demo finita ya había terminado sus 600 frames y cerrado el servidor. El script
  de comprobación se interrumpió antes de leer dos frames y ejecutar AppTest contra
  ese proceso. No es un fallo de los 108 tests, pero sí de la verificación adicional.
- Según la regla del usuario, se detuvo la validación al primer fallo. No se reinició
  la demo ni se repitió el chequeo; no se completó inspección visual del frame sintético.
- README, DECISIONS y LIMITATIONS actualizados con modo optativo, uso, privacidad
  y alcance pendiente. `visualization.stream` sigue false en `default.yaml`; el
  ejemplo `visual-demo.yaml` requiere selección explícita.
- Al retomar: iniciar un publicador persistente (sin `--max-frames`) o sincronizar
  prueba y proceso con un readiness check; leer MJPEG, verificar AppTest contra la
  API de esa misma demo y revisar un frame sintético solo en memoria. Detener luego
  el proceso de prueba. No afirmar finalización integral hasta cerrar esos pasos.
- Hito 5 no iniciado. Los cambios previos del usuario en `AGENTS.md` quedan intactos.

## Hito 5 — detenido en el paso 0 (2026-10-01)

- Se leyó este documento antes de trabajar. No se repitieron las verificaciones
  anteriores ni se retomó la validación pendiente del hito 4.5.
- Se intentó abrir `data/demo.mov` con `cv2.VideoCapture` desde la raíz del proyecto,
  usando `.venv/bin/python`. Resultado: `capture.isOpened()` devolvió false.
- Mensaje de OpenCV: `Couldn't read video stream from file "data/demo.mov"`.
  La comprobación terminó con código 1 antes de decodificar cualquier frame.
- Comprobación posterior de existencia, sin abrir el contenido: la ruta
  `/Users/andresespinoza/transport-cam-counter/data/demo.mov` **no existe** en este
  workspace (`Path.exists() == False`, `Path.is_file() == False`). No hay evidencia
  de un problema de códec: falta el archivo en la ubicación solicitada.
- FPS, resolución y número de frames: **no disponibles**, porque no se pudo abrir.
  No se copió, modificó, convirtió ni subió ningún video. No se escribieron frames
  ni imágenes a disco.
- Se detuvo el trabajo siguiendo la condición explícita del usuario. No se
  implementaron `--realtime`, `--loop`, evaluación ni benchmark; tampoco se ejecutó
  el barrido ni se modificó la configuración por defecto. No hay resultados nuevos
  de rendimiento o precisión que reportar. La suite no se repitió: solo cambió esta
  documentación después del fallo de la comprobación inicial.
- Para retomar: disponer del video en la ruta indicada o confirmar su ubicación
  local correcta; repetir primero la apertura. Los valores manuales N/M de
  entradas/salidas también quedan pendientes para la evaluación posterior.
- Hito 6 no iniciado. Se preservan los cambios previos del usuario en `AGENTS.md`.

### Reintento del paso 0 — discrepancia de nombre identificada (2026-10-01)

- Se volvió a leer PROGRESS antes de retomar. El usuario confirmó referencia manual:
  **6 entradas y 6 salidas**; esos valores ya no están pendientes.
- La nueva comprobación de `data/demo.mov` falló en `Path.stat()` con
  `FileNotFoundError`, antes de ejecutar `cv2.VideoCapture`. Se detuvo el trabajo
  inmediatamente; no hubo una segunda apertura ni se pasó al benchmark.
- Inspección solo de nombres/metadatos de `data/`: el archivo real presente se
  llama **`data/demo1.mov`**, de **36.190.296 bytes**. También está `data/demo.avi`,
  el video sintético anterior. `data/demo.mov` sigue sin existir en este workspace.
- El fallo anterior no puede marcarse como resuelto todavía: se identificó la
  diferencia `demo1.mov` frente a `demo.mov`, pero no se verificó la apertura del
  archivo encontrado. No se renombró, copió, modificó ni abrió ese video; tampoco
  se guardaron frames o imágenes.
- Para retomar sin cambiar el archivo, usar explícitamente `data/demo1.mov` y
  comprobar primero su apertura. Mantener referencia manual IN=6 / OUT=6.
- Solo se actualiza esta documentación y se conserva la regla de detenerse ante
  fallos. Sin resultados de rendimiento, cambios de código ni inicio del hito 6.

### Paso 0 resuelto — apertura verificada (2026-10-02)

- Por instrucción del usuario se utiliza **`data/demo1.mov`**, sin renombrarlo.
  El fallo de ruta anterior queda **resuelto**: OpenCV/FFmpeg lo abrió y decodificó
  el primer frame en memoria. Referencia manual confirmada: **IN=6, OUT=6**.
- Metadatos: **1080 × 1920**, **59,9724896836 FPS**, **1.308 frames**, **21,81 s**,
  **36.190.296 bytes**. `mtime_ns` inicial: `1790883891314778494`.
- El video sigue siendo solo lectura: sin copia, conversión, subida ni escritura
  de frames/imágenes. No se mostraron imágenes con personas mediante herramientas.
- Revisión del código: todavía faltan realtime/loop, evaluación y benchmark.
  Se continúa desde esas partes, sin repetir la validación del hito 4.5.
- Lectura de hardware: el sandbox restringió `sysctl`; la misma consulta de solo
  lectura se ejecutó con autorización del entorno. Equipo: Mac14,2, Apple M2,
  8 CPU lógicas, 16 GiB, macOS 26.6.2. No fue un fallo de tests ni del video.
- Hito 5 en curso. Hito 6 no iniciado.

### Paso 1 — archivos y evaluación verificados (2026-10-02)

- Implementados `--realtime` y `--loop`, también configurables en YAML. Cada
  vuelta reinicia las identidades y los conteos; no acumula cruces entre vueltas.
- `scripts/evaluate_counts.py` informa conteos por dirección, error absoluto y
  porcentual, incluyendo el caso de referencia cero sin división por cero.
- Suite completa: `.venv/bin/python -m pytest -q -x` → **117 passed in 8.27s**,
  con sockets locales autorizados. Pruebas nuevas de ritmo, bucle y evaluación
  sobre video sintético en memoria. Se eliminó la escritura de AVI temporal de
  las pruebas y se prohíben `imwrite`/`VideoWriter` en toda la suite.
- CLI ejecutada con YOLO/ByteTrack reales sobre el AVI sintético preexistente:
  `evaluate_counts.py --video data/demo.avi --expected-in 0 --expected-out 0`:
  80 frames, IN=0, OUT=0, error 0. Sin creación de imágenes/videos.
- Sin fallos de validación. Siguiente: instrumentación, benchmark y barrido.

### Paso 2 — instrumentación verificada; mediciones en curso (2026-10-02)

- Implementado `benchmark_fps.py`: warmup descartado, tres repeticiones,
  percentiles, barrido de tamaño/stride, captura/inferencia/ByteTrack/conteo/
  overlay+JPEG, comparación sintética y registro de carga de fondo.
- Hilos de torch configurables en YAML/CLI, sin dependencias nuevas. Se mantiene
  la elección automática por defecto. Ningún ajuste de línea, banda o confianza.
- Suite completa: **123 passed in 7.65s**. Incluye warmup, stream en RAM, stride,
  estadísticas, rechazo de realtime y callback de tracking sin duplicación.
- Piloto real ejecutado (300 frames, warmup 30, tres repeticiones por modo):
  320/stride 1, automático = 7 hilos reales; media **69,57 FPS** sin stream,
  **67,32 FPS** con stream. Archivo `docs/benchmark-pilot-auto.json`, solo números.
  Es una muestra inicial, no reemplaza el barrido completo ni evalúa precisión.
- Siguiente: comparar hilos explícitos, barrido completo y evaluación IN=6/OUT=6.

## Estado actual

| Hito | Estado | Commit / evidencia |
| --- | --- | --- |
| 1 | Completado | `7dce1fb`, 18 tests + demo CPU con debug |
| 2 | Completado | `130cd6e`, 48 tests + demo CPU con conteos |
| 3 | Completado | `99f4602`, 61 tests + transporte HTTP real |
| 4 | Completado | 83 tests + simulación acotada + API real y AppTest verificados |
| 4.5 | Validación integrada pendiente | 108 tests aprobados; CLI fake correcta; chequeo HTTP posterior fallido |
| 5 | En curso; ruta resuelta | `data/demo1.mov` abierto: 1080×1920, 59,97 FPS, 1.308 frames; referencia 6 IN / 6 OUT |
