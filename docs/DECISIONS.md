# Decisiones

## Hito 1 — 2026-09-30
- Usar la raíz existente como `apc-metro/`, sin duplicar carpetas.
- Configuración con dataclasses y YAML seguro; rutas relativas al padre de la
  carpeta del YAML. Se rechazan opciones desconocidas y valores inválidos.
- Tracks y línea normalizados: cambiar resolución no cambia la calibración.
- Captura en hilo con cola acotada; los archivos conservan todos sus frames.
  `vid_stride` selecciona los frames antes de inferencia.
- CPU obligatoria; YOLOv8n y ByteTrack, clase person. `lap` es requerido por ByteTrack.
- Pesos locales explícitos: no descargar modelos durante una demo.
- Debug local optativo, sin grabación. Pruebas con video sintético.
- API verificada en [documentación oficial](https://docs.ultralytics.com/modes/track/).

## Hito 2
- La banda se expresa como semiancho normalizado. Solo pasar de un lado externo
  al otro confirma el cruce; permanecer dentro no genera eventos. Volver a cruzar
  permite otro evento con el mismo ID.
- Vida mínima = observaciones efectivas; tolerancia de pérdidas = llamadas al
  contador sin ese ID. Los frames omitidos por `vid_stride` no son observaciones.
- Si el ID cambia, no se intenta reconocer a la persona. Mantener el mismo ID
  permite tolerar hasta dos pérdidas; una ausencia mayor caduca su historial.
- Calibrar ocupación establece un saldo inicial y reinicia entradas/salidas.
  `reset()` fija cero; al reiniciar toda una sesión también se resetea el tripwire.
- Ocupación = max(0, saldo inicial + entradas − salidas), sin limitar a capacidad;
  40% y 75% son amarillos. Salidas sin entradas pueden exigir recalibración.

## Hito 3
- `create_source` selecciona archivo, webcam o stream sin cambiar la inferencia.
- En vivo se descarta el frame más antiguo cuando se llena la cola. En archivo
  se conserva el orden completo. Los errores y el final no se descartan.
- Stream usa FFmpeg y timeouts de apertura/lectura, según
  [OpenCV](https://docs.opencv.org/4.x/d4/d15/group__videoio__flags__base.html).
- Una desconexión termina con error explícito. No reconectar automáticamente:
  hacerlo sin reiniciar el tracker podría unir IDs entre sesiones distintas.
- Webcam validada con backend simulado; HTTP con servidor real local de video sintético.

## Hito 4
- API HTTP de solo lectura con la biblioteca estándar; Streamlit consulta
  `/telemetry` a intervalos configurables. Evita incorporar FastAPI/WebSocket
  cuando la demo requiere únicamente unos pocos números cada medio segundo.
- Servidor ligado exclusivamente a 127.0.0.1, sin registro ni persistencia.
  Esquema validado de valores numéricos: incluye ID de vagón, nunca ID de persona.
- `level`: 0 verde, 1 amarillo, 2 rojo; `simulated`: 0 real, 1 prueba;
  timestamp Unix de captura. Muestras antiguas no reemplazan las más nuevas.
- Simulador separado para varios vagones. No mezclar datos de prueba con la cámara
  dentro de una misma demo. El programa de cámara publica un vagón configurado.
- Dashboard con refresco automático mediante
  [st.fragment](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).
  Datos caducados se muestran grises y se excluyen del total con señal.
- API y dashboard se cierran por separado; cuando acaba el archivo, termina su API.
  No se muestran datos viejos como si continuara la captura.

## Corrección del simulador — 2026-09-30
- Reemplazar el crecimiento lineal de entradas/salidas por ondas triangulares
  deterministas: movimientos graduales alrededor de objetivos bajo, medio y alto,
  y un cuarto vagón que recorre todo el rango de 0 a 110%.
- Período y perfiles configurables en `simulation`; los pasos se convierten a
  segundos usando `telemetry.interval_seconds`. Por defecto el ciclo dura 120 s,
  con rangos 10–30%, 50–70%, 80–100% y 0–110% para capacidad 100.
- Calcular entradas y salidas acumuladas a partir de los tramos recorridos y ciclos
  completos, sin reiniciar conteos ni recortar el saldo después de contarlos.
  La identidad `initial_occupancy + entries - exits = occupancy` se conserva.
- Cálculo directo de cualquier paso, sin reproducir ni guardar la historia. No se
  añaden dependencias ni aleatoriedad; pruebas reproducibles incluso para pasos grandes.
- Personas enteras: el límite global se redondea hacia abajo; si un perfil queda
  sin amplitud por una capacidad muy pequeña, permanece constante.
- Son patrones de demostración para visualizar estados y transiciones, no un modelo
  de demanda de pasajeros validado en trenes. El hito 5 no se inicia.

## Hito 4.5 — vista local anotada (2026-10-01)

- El usuario autoriza explícitamente video como **modo demo opcional y local**.
  `visualization.stream` permanece apagado por defecto; la telemetría numérica
  sigue siendo lo único publicado en modo normal. `/telemetry` conserva su esquema.
- Overlay puro en `visualization/overlay.py`: copia del frame, sin IO ni estado
  global. La estela es un estado separado y acotado de coordenadas, no de imágenes.
  Los colores YAML son RGB y se convierten a BGR al dibujar con OpenCV.
- JPEG mediante `cv2.imencode`, exclusivamente en memoria. Un único JPEG vigente
  compartido, sin cola de video ni historial; cada cliente puede tener un buffer
  transitorio de envío. El cierre elimina la referencia al JPEG.
- MJPEG en `/video` del HTTP existente, siempre en 127.0.0.1. Se limita tanto la
  codificación como el envío a `visualization.max_fps`; lectores lentos reciben
  el frame más reciente y tienen timeout de escritura. No se introduce otro servidor.
- `/video/status` separa habilitado y listo; stream apagado responde 404 y sin
  frame reciente responde 503. La caducidad usa el umbral de telemetría existente.
- Streamlit consulta el estado real del backend y muestra un `<img>` a la URL
  loopback junto a los semáforos, con la leyenda de video local. El navegador
  recibe MJPEG directamente; Streamlit no guarda ni reenvía imágenes.
  Se usa [HTML en Streamlit](https://docs.streamlit.io/develop/api-reference/text/st.markdown)
  para el consumidor MJPEG, manteniendo el frontend existente.
- `run_demo.py --fake-tracks` genera frames artificiales en RAM y entrega tracks
  al mismo contador y overlay del modo cámara. No instancia detector ni captura.
  Dos IDs nuevos por ciclo permiten comprobar exactamente una entrada y una salida.
- El simulador multivagón anterior continúa siendo numérico: no se vinculan sus
  ocupaciones inventadas con conteos de otra escena. La demo visual usa un vagón.
- Las pruebas integradas y su estado pendiente se registran en PROGRESS. No se
  inicia el benchmark ni la optimización del hito 5.

## Hito 5 — archivos y evaluación (2026-10-02)

- El usuario autoriza retomar el hito 5 con `data/demo1.mov`, referencia IN=6 y
  OUT=6. Se conserva el archivo local sin copiarlo, modificarlo ni subirlo.
- `source.realtime` / `--realtime` limita la entrega al FPS informado por OpenCV;
  si el cómputo es más lento, no descarta frames para ponerse al día. `--loop`
  rebobina el mismo archivo y reinicia ByteTrack, tripwire, ocupación y estelas
  por vuelta: el salto final→inicio no representa un cruce real.
- La evaluación siempre recorre una sola pasada completa, sin descartar
  calentamiento; informa cada dirección y la suma de errores absolutos, para
  evitar que una entrada extra oculte una salida perdida. Con referencia cero,
  el porcentaje es 0 si no hay error y `null` si no se puede definir.
- Los tests de archivo usan frames sintéticos en RAM y un backend de captura
  simulado. El test HTTP sigue usando OpenCV/FFmpeg real, con MJPEG generado en
  RAM. Se prohíben `imwrite` y `VideoWriter` durante toda la suite. La apertura
  real de MOV y el AVI sintético preexistente se verifican fuera de esos mocks.
- `detection.torch_threads=0` conserva la selección automática; un entero positivo
  se aplica después de la inicialización CPU de Ultralytics. Se mide el callback
  integrado de ByteTrack sin cambiar el tracker. Inferencia/pre/postproceso usan
  sus temporizadores internos; la primera llamada sin callback instrumentado se
  descarta dentro del calentamiento.
- Benchmark sin realtime y sin servidor HTTP: el modo stream utiliza el mismo
  overlay y `LatestFrame` (calidad 80, máximo 10 JPEG/s) en RAM; mide codificación,
  no transporte ni renderizado en navegador. Captura y espera en cola se reportan
  por separado: la captura se solapa con inferencia, sus latencias no son sumables.
- FPS procesados = inferencias medidas / tiempo de pared; FPS de origen = frames
  decodificados / tiempo de pared. Los umbrales 20/25 se aplican al mínimo de las
  tres repeticiones de FPS procesados. Se reportan también FPS instantáneos.
- La comparación sintética lee `data/demo.avi`, creado en hitos anteriores;
  lo repite en memoria hasta igualar los frames decodificados del MOV, reiniciando
  tracks por vuelta. No se crea un video nuevo ni se usa el MOV como material
  sintético. Las diferentes resoluciones/contenidos limitan la comparación.
