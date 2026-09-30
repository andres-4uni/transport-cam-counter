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

## Hito 4 — detenido por pruebas fallidas (2026-09-30)
- API HTTP local en memoria, esquema numérico validado y publisher integrado en la demo.
- Simulador multivagón y dashboard Streamlit con semáforos, conteos, identificación
  visible de simulación y estado sin señal para datos viejos.
- Comando: `.venv/bin/python -m pytest -q`, ejecutado fuera del sandbox para
  habilitar los sockets locales usados por las pruebas.
- Resultado: **3 failed, 65 passed in 2.37s**. Las pruebas de API, esquema,
  concurrencia, simulación y recorrido tripwire → HTTP pasaron.
- Fallaron las tres pruebas de `tests/test_dashboard.py`:
  - `test_dashboard_renders_train_and_simulation_label`
  - `test_dashboard_marks_stale_data_without_live_total`
  - `test_dashboard_api_unavailable`
- Causa observada: con Streamlit **1.64.0**, `AppTest.from_file("dashboard/app.py")`
  resuelve la ruta relativa al archivo Python llamador, por lo que intenta abrir
  `tests/dashboard/app.py`. El archivo implementado está en `dashboard/app.py`.
  Excepción: `FileNotFoundError: AppTest script not found at .../tests/dashboard/app.py`.
  El dashboard no llegó a ejecutarse en estas pruebas.
- Se detuvo el trabajo al detectar el fallo, según la instrucción explícita del usuario.
  No se corrigieron ni se volvieron a ejecutar estas pruebas; no se abrió el dashboard
  ni se ejecutó la demo integrada del hito 4 después del fallo.
- Próximo paso cuando se retome: pasar una ruta absoluta derivada de `__file__`
  a AppTest, ejecutar la suite completa y, solo si pasa, verificar simulador,
  dashboard en navegador y demo de cámara/video con API. No afirmar que el hito 4 funciona aún.
- El código del hito 4 se conserva en un commit **WIP**, no como hito completado.
- `compileall` y `git diff --check` habían pasado. Dependencias exactas actualizadas
  en `requirements-lock.txt`. Hitos 5 y 6 no iniciados.

## Resumen al detenerse

| Hito | Estado | Commit / evidencia |
| --- | --- | --- |
| 1 | Completado | `7dce1fb`, 18 tests + demo CPU con debug |
| 2 | Completado | `130cd6e`, 48 tests + demo CPU con conteos |
| 3 | Completado | `99f4602`, 61 tests + transporte HTTP real |
| 4 | Pendiente de corrección y validación | 65 aprobadas, 3 fallidas; ver causa arriba |
