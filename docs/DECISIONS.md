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
