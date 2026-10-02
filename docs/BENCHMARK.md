# Hito 5 — benchmark local

Medición de este equipo, no una certificación de precisión APC ni de rendimiento
en cualquier notebook. Referencia manual del único video real: **IN=6, OUT=6**.
Resultados completos y evaluación en curso; el estado verificable está en PROGRESS.

## Equipo y entradas

- Mac14,2, Apple M2, 8 CPU lógicas, 16 GiB; macOS 26.6.2 (25G83), ARM64.
- Python 3.11.15, torch 2.14.1, OpenCV 4.14.0, Ultralytics 8.3.253; CPU obligatoria,
  YOLOv8n local, ByteTrack integrado, clase `person`, sin nuevas dependencias.
- MOV real: `data/demo1.mov`, 1080×1920, 59,9724896836 FPS, 1.308 frames,
  21,81 s, 36.190.296 bytes. Solo lectura; no renombrado, copiado ni convertido.
- Comparación: `data/demo.avi`, sintético preexistente sin personas. No se creó
  otro archivo de video. Sus dimensiones y códec distintos limitan la comparación.
- No se guardan frames, imágenes, rostros, boxes ni IDs en los resultados. Solo
  estadísticas numéricas y metadatos técnicos; el JPEG optativo vive en RAM.

## Método reproducible

```sh
.venv/bin/python scripts/benchmark_fps.py --torch-threads 4 --output docs/nueva-medicion.json
```

El resultado no puede sobreescribir un archivo existente. Por defecto mide las
12 combinaciones de `imgsz` 320/352/384/416 y `vid_stride` 1/2/3; tres repeticiones
por video y estado del stream: **144 ejecuciones**. Orden de combinaciones mezclado
con semilla 17, fuentes/modos en secuencia; no se ejecutan benchmarks en paralelo.
En cada ejecución se descartan las primeras 30 inferencias (no 30 frames de origen).
La captura usa un hilo separado y una cola acotada de dos frames.

El MOV se recorre completo sin `--realtime`. El AVI sintético se repite hasta
igualar los 1.308 frames decodificados del MOV; cada vuelta reinicia ByteTrack y
conteos. No se descartan frames durante captura; stride omite inferencias. El
calentamiento consume más frames de origen con stride mayor, por lo que los
intervalos medidos no son idénticos. Apertura, carga de pesos y cierre quedan
fuera de los FPS medidos. La evaluación de conteos usa otra pasada completa y
**no descarta calentamiento**.

Se separan:

- **FPS procesados**: inferencias medidas / segundos de pared. La media, p50 y
  p95 principales se calculan sobre las tres repeticiones. “>20” y “≥25” exigen
  que las tres superen el umbral correspondiente, usando el mínimo sin redondear.
- **FPS de origen**: frames decodificados / segundos de pared; sube con stride,
  pero no equivale al número de imágenes analizadas. Los JSON incluyen también
  media/p50/p95 de FPS instantáneos entre inferencias.
- **Captura**: tiempo de `VideoCapture.read()` en el hilo, por frame decodificado.
  La espera del consumidor en cola se reporta aparte. Captura e inferencia se
  solapan: no sumar sus latencias para deducir FPS.
- **Inferencia**: ejecución de la red según el temporizador de Ultralytics.
  Preproceso, postproceso y resto de adaptación Python se registran por separado.
- **Tracking**: callback real de ByteTrack, incluida conversión de sus resultados.
- **Conteo**: tripwire, ocupación y actualización de estelas si están habilitadas.
- **Overlay+JPEG**: mismo overlay y `LatestFrame` que la demo, calidad 80,
  máximo 10 FPS. La media por inferencia incluye ceros cuando se limita el stream;
  `encoded_only` informa el coste de los frames efectivamente codificados.
  Apagado cuesta cero porque se omiten overlay y JPEG. No mide transferencia
  HTTP, consumo de Streamlit ni renderizado del navegador.

Los percentiles de latencia agrupan todas las muestras medidas de las tres
repeticiones. p95 de FPS representa el extremo rápido; p95 de latencia representa
el extremo lento. Se conserva el detalle por repetición en el JSON.

La carga de fondo se estima con tiempos CPU de sistema menos los del proceso de
benchmark, divididos por tiempo de pared × ocho CPU. Se registra también load
average. Es una estimación: incluye procesos ajenos, núcleo y actividad del IDE;
no se cerraron aplicaciones del usuario ni se controló temperatura/energía.

## Piloto de hilos

300 frames por pasada, warmup 30, 320/stride 1, tres repeticiones. Cada celda es
media de FPS procesados. Estos pilotos breves orientan la elección de hilos;
no sustituyen el barrido completo.

| Hilos solicitados / efectivos | Real apagado | Real encendido | Sintético apagado | Sintético encendido |
| --- | ---: | ---: | ---: | ---: |
| Auto / 7 | 69,57 | 67,32 | 85,72 | 84,82 |
| 4 / 4 | 71,80 | 69,42 | 99,75 | 98,23 |
| 1 / 1 | 71,32 | 69,26 | 72,01 | 70,15 |

Se usan cuatro hilos explícitos en el barrido. La diferencia real entre uno y
cuatro es pequeña; el sintético favorece cuatro. No se afirma una ventaja
universal ni se modifica el modo automático por estos pilotos.

Datos: [auto](benchmark-pilot-auto.json), [cuatro hilos](benchmark-pilot-4threads.json),
[un hilo](benchmark-pilot-1thread.json).
