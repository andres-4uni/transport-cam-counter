# Limitaciones

- Hito 4.5: 108 pruebas aprobadas y CLI fake ejecutada; una verificación integrada
  adicional falló por conexión rechazada después de finalizar la demo limitada a
  600 frames. Se detuvo el trabajo. Falta repetirla manteniendo vivo el publicador
  y revisar visualmente un frame sintético; no se declara validación integral.
- MJPEG y overlay agregan trabajo de CPU y tráfico loopback. El hito 5 registra
  mediciones provisionales de overlay/JPEG en RAM; no mide tráfico ni navegador.
  Bajar calidad JPEG/FPS puede reducir esa carga.
- El video demo puede mostrar rostros si se activa sobre una cámara real. No se
  anonimiza. Úselo localmente con autorización de quienes aparecen. La app no graba,
  pero no puede impedir que otro programa o el navegador capture lo mostrado.
- La leyenda de uso local corresponde al servidor ligado a 127.0.0.1 y dashboard
  local: no exponerlos mediante proxies, túneles o un despliegue remoto. Cualquier
  proceso local con acceso al puerto puede leer el stream optativo.
- El navegador debe soportar MJPEG; AppTest valida la estructura del panel pero
  no decodifica el video como un navegador. Las pruebas HTTP sí decodifican JPEG.

- El dashboard se verificó con AppTest, incluida conexión a la API real, y el
  servidor por HTTP. No hubo inspección visual en navegador porque la herramienta
  de interfaz no estuvo disponible durante la validación.

- Prototipo de aula; no se ha validado en trenes ni con cámara definitiva.
- La meta de más de 20 FPS no está certificada de forma general. Hay mediciones
  locales provisionales del hito 5, detenido por la discrepancia de frames.
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

## Alcance del hito 5

- OpenCV declara 1.308 frames de `data/demo1.mov`, pero las 72 pasadas del MOV
  entregaron 1.307; las 72 sintéticas se limitaron al mismo número observado.
  Falló una comprobación posterior de igualdad exacta. No se sabe todavía si es
  un metadato aproximado, un frame no decodificado u otra diferencia del backend.
  Se detuvo el trabajo sin convertir el archivo ni repetir lecturas para investigarlo.
  No hay evaluación aceptada de conteos sobre el MOV ni recomendación final.
- Un video de 21,81 s y una referencia agregada de 6 entradas / 6 salidas no validan
  precisión general. Coincidir en los totales tampoco demuestra que se detectaron
  los mismos eventos: falsos positivos y negativos pueden compensarse. Faltan
  anotaciones temporales, variedad de escenas y validación independiente.
- El benchmark corre en este equipo, con aplicaciones de fondo; no controla
  temperatura, estado energético ni throttling. Tres pasadas cortas no representan
  una jornada de operación ni certifican FPS en otra CPU.
- El AVI sintético preexistente tiene otra resolución y no contiene personas:
  sus FPS no predicen el coste de tracking con aglomeraciones ni aíslan el efecto
  del contenido respecto de la resolución y el códec.
- La medición del stream cubre overlay y JPEG en RAM, con el límite de 10 FPS;
  excluye transporte HTTP y navegador. Las estelas están apagadas en el barrido
  y activas en las configuraciones de demostración.
- `vid_stride` omite inferencias, pero el lector sigue decodificando los frames
  del archivo. Su tasa de origen no es la tasa de imágenes realmente analizadas;
  aumentar stride puede perder identidades, vida mínima o cruces rápidos.
- `--realtime` usa el FPS informado por OpenCV y no los PTS individuales de un
  archivo de tasa variable. No acelera un pipeline lento ni elimina frames para
  recuperar retraso. `--loop` reinicia identidades y conteos al rebobinar.
- Los temporizadores de inferencia y el callback de tracking corresponden a
  Ultralytics 8.3.253. Un cambio de API requiere revisar esa instrumentación;
  el programa informa si no encuentra el callback, en lugar de inventar latencias.
