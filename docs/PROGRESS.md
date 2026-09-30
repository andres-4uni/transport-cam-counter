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

## Estado actual

| Hito | Estado | Commit / evidencia |
| --- | --- | --- |
| 1 | Completado | `7dce1fb`, 18 tests + demo CPU con debug |
| 2 | Completado | `130cd6e`, 48 tests + demo CPU con conteos |
| 3 | Completado | `99f4602`, 61 tests + transporte HTTP real |
| 4 | Completado | 68 tests + API/simulador/Streamlit en ejecución + AppTest contra API real |
