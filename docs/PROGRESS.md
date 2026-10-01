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

## Estado actual

Hito 4.5 en curso: configuración visual y overlay puro implementados.
Primera subtarea validada: **94 passed in 2.49s**, incluidos colores, toggles,
estelas acotadas, copia del frame y stream apagado por defecto.
Segunda subtarea validada: **99 passed in 5.06s**. `/video` sirve MJPEG solo en
127.0.0.1, conserva el último JPEG en RAM y respeta calidad/FPS configurados.
Se probaron HTTP real, apagado por defecto, espera sin frames, caducidad, cierre
de lectores y prohibición de IO de archivos durante overlay/codificación/HTTP.
Tercera subtarea validada: **108 passed in 7.66s**. Dashboard con video según el
estado real del backend y leyenda local; `--fake-tracks` alimenta contador y overlay
sin detector ni captura. Tres ciclos producen IN=3, OUT=3 y ocupación final=0 en
ambas orientaciones/sentidos; la ocupación intermedia alcanza 1.
Pendiente: ejecución integrada, revisión sintética en memoria y documentación final.
No se inicia el hito 5. `AGENTS.md` conserva los cambios previos del usuario.

| Hito | Estado | Commit / evidencia |
| --- | --- | --- |
| 1 | Completado | `7dce1fb`, 18 tests + demo CPU con debug |
| 2 | Completado | `130cd6e`, 48 tests + demo CPU con conteos |
| 3 | Completado | `99f4602`, 61 tests + transporte HTTP real |
| 4 | Completado | 83 tests + simulación acotada + API real y AppTest verificados |
