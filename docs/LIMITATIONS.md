# Limitaciones

- El dashboard se verificó con AppTest, incluida conexión a la API real, y el
  servidor por HTTP. No hubo inspección visual en navegador porque la herramienta
  de interfaz no estuvo disponible durante la validación.

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
- La API es local y de una sola sesión, sin autenticación ni persistencia;
  no está diseñada para publicarse en una red. Al terminar el proceso se pierde el estado.
- La demo de cámara publica un solo vagón; los múltiples vagones son simulación.
  Agregar varias cámaras/puertas reales y agregar sus conteos queda fuera de estos hitos.
- Las pruebas sintéticas no miden precisión APC sobre personas. Se requiere una
  validación con compañeros, conteo manual y consentimiento antes de presentar métricas.
