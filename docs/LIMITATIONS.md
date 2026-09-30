# Limitaciones

- Prototipo de aula; no se ha validado en trenes ni con cámara definitiva.
- La meta de más de 20 FPS no está certificada: requiere el benchmark del hito 5.
- YOLO/ByteTrack puede fallar con oclusiones, contraluz, aglomeraciones y cambios de ID.
- Filtros de área y confianza requieren calibración con la posición real de cámara.
- No se guarda video. Los archivos de entrada deben proporcionarse con consentimiento.
- La distribución comercial requiere revisar las licencias de Ultralytics y sus pesos.
- Un cambio de ID durante el cruce puede perder el evento; no se hace reidentificación.
  La banda y la vida mínima pueden omitir cruces extremadamente rápidos.
- Falta validar webcam física y RTSP/celular/cámara definitiva. El soporte depende
  de codecs y backend de OpenCV. La resolución de webcam es una solicitud al dispositivo.
- Algunos drivers de webcam pueden bloquear `read()`; el cierre informa si el hilo
  no responde en cinco segundos. Los streams FFmpeg sí tienen timeout configurable.
- Red lenta y descarte de frames pueden omitir cruces. Una desconexión exige reiniciar
  la sesión y revisar la calibración. No versionar URLs con credenciales.
