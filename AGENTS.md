Actúa como ingeniero senior de visión por computadora y software embebido. Vas a trabajar de forma autónoma mientras yo no estoy, así que sigue este documento al pie de la letra.

## CONTEXTO
Proyecto de Taller de Diseño en Ingeniería (universidad): sistema APC (Automated Passenger Counting) "vendible a Metro" que cuenta entradas/salidas por puerta y estima la ocupación de cada vagón (verde <40%, amarillo 40–75%, rojo >75%).
Restricciones: bajo presupuesto, no se puede intervenir trenes reales, validación en el marco de una puerta de sala con compañeros, demo en vivo proyectada en clase.
Aún NO tenemos cámara final. Hoy probamos con celular/webcam y videos grabados; después habrá una cámara comprada, posiblemente inalámbrica (ESP32-CAM / cámara IP / RTSP). El procesamiento siempre corre en un notebook sin GPU.

## STACK
Python 3.11, OpenCV, Ultralytics YOLOv8n (clase `person`), ByteTrack (integrado), dashboard en Streamlit (o FastAPI + WebSocket si lo justificas), pytest.

## PRINCIPIOS DE DISEÑO
1. **Fuente de video intercambiable:** interfaz `VideoSource` con implementaciones `WebcamSource`, `StreamSource` (URL HTTP/RTSP, celular) y `FileSource` (video grabado). Se elige por config, sin tocar el resto.
2. **Lógica de conteo pura y testeable:** el contador recibe tracks (id, centroide) y devuelve eventos; no depende de YOLO ni de la cámara.
3. **Todo configurable en `configs/default.yaml`:** fuente, imgsz, conf, posición/orientación de la línea, umbrales del semáforo, capacidad del vagón.
4. **Privacidad por diseño:** no guardar frames ni rostros; solo emitir telemetría numérica (entradas, salidas, ocupación, timestamp). Modo debug con video anotado solo local y desactivado por defecto.
5. **Rendimiento:** meta >20 FPS en laptop sin GPU. Captura en hilo separado, `imgsz` configurable (320–416), `vid_stride` configurable. Mide y reporta FPS.

## ESTRUCTURA DEL REPO
```
apc-metro/
├── configs/default.yaml
├── src/apc/
│   ├── sources/      # base.py, webcam.py, stream.py, file.py
│   ├── detection/    # detector.py (YOLO + ByteTrack)
│   ├── counting/     # tripwire.py, occupancy.py
│   ├── publisher/    # telemetría vía WebSocket/API local
│   └── config.py
├── dashboard/app.py  # esquema del tren con semáforo por vagón
├── scripts/          # run_demo.py, benchmark_fps.py
├── tests/            # tests del contador con tracks simulados
├── docs/             # PROGRESS.md, DECISIONS.md, LIMITATIONS.md
└── README.md
```

## CASOS BORDE A MANEJAR EN EL CONTEO
- Contar cada `track_id` una sola vez por cruce (evitar doble conteo).
- Histéresis: el centroide debe alejarse una distancia mínima de la línea para validar el cruce (personas paradas sobre la línea).
- Zona de conteo (banda) en vez de cruce exacto, tolerante a pérdida de 1–2 frames.
- Descartar tracks de vida muy corta (falsos positivos) y detecciones de área anómala (mochilas, bultos).
- Ocupación = max(0, entradas − salidas), con función de reseteo/calibración.

## HITOS (en orden; no pases al siguiente sin cumplir el anterior)
1. Esqueleto del repo, config, `FileSource` y detector mostrando video anotado.
2. Tripwire + contador con tests unitarios (cruces, ida y vuelta, persona parada, ID perdido).
3. `WebcamSource` y `StreamSource`; selección por config.
4. Publisher de telemetría + dashboard con semáforo por vagón (simular varios vagones con datos de prueba).
5. Benchmark de FPS y optimización; documenta resultados.
6. Documentación: README con instrucciones de uso, `LIMITATIONS.md` honesto (qué falla y por qué), `DECISIONS.md`.

## REGLAS DE TRABAJO
- Haz commits pequeños en git con mensajes claros, uno por hito o subtarea.
- Verifica tu trabajo: corre los tests y el código tú mismo antes de declarar algo terminado. No digas que funciona si no lo ejecutaste.
- Si algo es ambiguo, toma la decisión más simple, anótala en `docs/DECISIONS.md` y sigue. No te detengas a preguntar.
- No agregues dependencias pesadas ni features fuera de este documento.
- Mantén `docs/PROGRESS.md` actualizado: qué hiciste, qué falló, qué sigue.
- Código legible y comentado en español; nombres de variables en inglés.

Empieza por el hito 1.
