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
