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
