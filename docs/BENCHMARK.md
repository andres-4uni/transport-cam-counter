# Hito 5 — benchmark local

Medición de este equipo, no una certificación de precisión APC ni de rendimiento
en cualquier notebook. Referencia manual del único video real: **IN=6, OUT=6**.
**Trabajo detenido tras el barrido:** OpenCV informa 1.308 frames, pero todas las
pasadas decodificaron **1.307**. Falló la comprobación posterior que exigía igualdad
exacta. No se investigó ni corrigió esa diferencia; no prueba por sí sola corrupción
del video. Las tablas son mediciones **provisionales** sobre los frames entregados,
no validación de que se haya leído cada frame declarado. La evaluación de conteos
y la recomendación final quedan pendientes. Detalles en [PROGRESS](PROGRESS.md).

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

El MOV se lee hasta que OpenCV devuelve fin de lectura, sin `--realtime`. El AVI
sintético se repite hasta igualar los **1.307 frames efectivamente decodificados**
del MOV; cada vuelta reinicia ByteTrack y
conteos. No se descartan frames durante captura; stride omite inferencias. El
calentamiento consume más frames de origen con stride mayor, por lo que los
intervalos medidos no son idénticos. Apertura, carga de pesos y cierre quedan
fuera de los FPS medidos. El evaluador está diseñado para usar otra pasada hasta
fin de lectura y **no descartar calentamiento**; su validación sobre este MOV
quedó detenida por la diferencia entre frames declarados y decodificados.

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

## Resultados del barrido completo

Datos numéricos de las 144 ejecuciones: [benchmark-results.json](benchmark-results.json).
Resultados provisionales por la discrepancia 1.307/1.308 descrita arriba. Cada celda
de FPS muestra **media / p50 / p95** de tres pasadas; los mínimos se muestran
separadamente. Se usan cuatro hilos de torch en todas ellas.


### FPS — MOV real

| imgsz / stride | Stream apagado | Mínimo | Stream encendido | Mínimo | FPS origen medios apagado / encendido | >20 / ≥25 en ambos modos |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 320 / 1 | 66.72 / 66.46 / 70.80 | 62.42 | 61.54 / 61.68 / 61.83 | 61.11 | 66.72 / 61.54 | Sí / Sí |
| 320 / 2 | 38.25 / 37.95 / 39.39 | 37.25 | 36.49 / 36.10 / 37.27 | 35.96 | 76.50 / 72.97 | Sí / Sí |
| 320 / 3 | 34.19 / 34.17 / 34.47 | 33.88 | 32.86 / 33.16 / 33.18 | 32.25 | 102.64 / 98.66 | Sí / Sí |
| 352 / 1 | 60.69 / 60.37 / 61.63 | 59.92 | 64.31 / 64.74 / 64.87 | 63.31 | 60.69 / 64.31 | Sí / Sí |
| 352 / 2 | 40.51 / 40.73 / 40.79 | 40.01 | 38.26 / 38.12 / 38.52 | 38.09 | 81.02 / 76.51 | Sí / Sí |
| 352 / 3 | 31.96 / 32.07 / 32.65 | 31.09 | 29.75 / 29.65 / 29.94 | 29.63 | 95.95 / 89.33 | Sí / Sí |
| 384 / 1 | 52.19 / 52.14 / 52.60 | 51.79 | 49.64 / 49.70 / 49.87 | 49.34 | 52.19 / 49.64 | Sí / Sí |
| 384 / 2 | 37.73 / 37.32 / 38.78 | 36.91 | 31.73 / 31.13 / 33.52 | 30.28 | 75.45 / 63.46 | Sí / Sí |
| 384 / 3 | 31.20 / 30.85 / 32.18 | 30.42 | 28.42 / 28.53 / 28.92 | 27.76 | 93.67 / 85.33 | Sí / Sí |
| 416 / 1 | 43.77 / 44.31 / 44.98 | 41.95 | 44.46 / 44.11 / 46.95 | 42.00 | 43.77 / 44.46 | Sí / Sí |
| 416 / 2 | 43.45 / 43.34 / 43.67 | 43.31 | 42.44 / 42.34 / 42.68 | 42.27 | 86.90 / 84.88 | Sí / Sí |
| 416 / 3 | 24.15 / 24.07 / 24.72 | 23.60 | 21.88 / 21.85 / 21.96 | 21.82 | 72.52 / 65.70 | Sí / No |

### Latencia por etapa — MOV real, stream apagado

Milisegundos **media / p50 / p95**, agrupando las muestras de las tres pasadas. Captura usa muestras por frame de origen; las otras etapas, por inferencia.

| imgsz / stride | Captura | Inferencia | Tracking | Conteo | Overlay+JPEG |
| --- | ---: | ---: | ---: | ---: | ---: |
| 320 / 1 | 5.565 / 5.503 / 6.648 | 12.162 / 12.231 / 13.837 | 0.124 / 0.084 / 0.356 | 0.005 / 0.004 / 0.008 | 0.000 / 0.000 / 0.000 |
| 320 / 2 | 8.427 / 8.314 / 11.421 | 22.394 / 22.323 / 25.599 | 0.201 / 0.131 / 0.540 | 0.007 / 0.006 / 0.012 | 0.000 / 0.000 / 0.000 |
| 320 / 3 | 7.575 / 7.398 / 10.389 | 25.700 / 25.513 / 29.036 | 0.199 / 0.192 / 0.464 | 0.006 / 0.005 / 0.010 | 0.000 / 0.000 / 0.000 |
| 352 / 1 | 5.396 / 5.220 / 6.536 | 13.750 / 13.311 / 16.249 | 0.139 / 0.096 / 0.361 | 0.005 / 0.005 / 0.008 | 0.000 / 0.000 / 0.000 |
| 352 / 2 | 6.637 / 6.455 / 8.334 | 21.290 / 21.278 / 23.137 | 0.169 / 0.107 / 0.453 | 0.006 / 0.005 / 0.010 | 0.000 / 0.000 / 0.000 |
| 352 / 3 | 7.591 / 7.465 / 10.400 | 27.730 / 27.626 / 30.732 | 0.186 / 0.120 / 0.488 | 0.006 / 0.005 / 0.011 | 0.000 / 0.000 / 0.000 |
| 384 / 1 | 5.565 / 5.489 / 6.393 | 16.267 / 16.204 / 17.712 | 0.154 / 0.097 / 0.409 | 0.005 / 0.005 / 0.009 | 0.000 / 0.000 / 0.000 |
| 384 / 2 | 6.929 / 6.782 / 8.696 | 23.055 / 22.983 / 25.948 | 0.182 / 0.113 / 0.485 | 0.006 / 0.006 / 0.011 | 0.000 / 0.000 / 0.000 |
| 384 / 3 | 7.485 / 7.345 / 10.377 | 28.463 / 28.306 / 31.803 | 0.192 / 0.121 / 0.502 | 0.006 / 0.005 / 0.011 | 0.000 / 0.000 / 0.000 |
| 416 / 1 | 5.891 / 5.685 / 6.994 | 19.868 / 19.832 / 21.778 | 0.181 / 0.108 / 0.474 | 0.006 / 0.005 / 0.010 | 0.000 / 0.000 / 0.000 |
| 416 / 2 | 5.258 / 5.075 / 6.570 | 20.415 / 19.819 / 24.662 | 0.165 / 0.106 / 0.383 | 0.005 / 0.005 / 0.009 | 0.000 / 0.000 / 0.000 |
| 416 / 3 | 8.850 / 8.784 / 11.221 | 37.274 / 37.248 / 41.742 | 0.261 / 0.238 / 0.620 | 0.008 / 0.007 / 0.013 | 0.000 / 0.000 / 0.000 |

### Latencia por etapa — MOV real, stream encendido

Milisegundos **media / p50 / p95**, agrupando las muestras de las tres pasadas. Captura usa muestras por frame de origen; las otras etapas, por inferencia.

| imgsz / stride | Captura | Inferencia | Tracking | Conteo | Overlay+JPEG |
| --- | ---: | ---: | ---: | ---: | ---: |
| 320 / 1 | 5.599 / 5.488 / 6.525 | 12.476 / 12.440 / 13.393 | 0.127 / 0.086 / 0.368 | 0.005 / 0.004 / 0.009 | 0.793 / 0.000 / 5.672 |
| 320 / 2 | 8.299 / 8.194 / 11.233 | 21.796 / 21.746 / 24.840 | 0.202 / 0.133 / 0.546 | 0.007 / 0.006 / 0.012 | 1.929 / 0.000 / 8.810 |
| 320 / 3 | 7.547 / 7.359 / 10.470 | 25.119 / 25.058 / 29.150 | 0.199 / 0.195 / 0.467 | 0.006 / 0.005 / 0.010 | 1.726 / 0.000 / 7.404 |
| 352 / 1 | 4.885 / 4.763 / 5.542 | 12.685 / 12.545 / 14.189 | 0.122 / 0.083 / 0.330 | 0.005 / 0.004 / 0.008 | 0.595 / 0.000 / 4.318 |
| 352 / 2 | 6.595 / 6.296 / 8.234 | 21.367 / 21.280 / 23.325 | 0.171 / 0.109 / 0.457 | 0.006 / 0.005 / 0.010 | 1.403 / 0.000 / 6.589 |
| 352 / 3 | 7.684 / 7.563 / 10.610 | 28.034 / 27.925 / 30.978 | 0.191 / 0.122 / 0.507 | 0.006 / 0.006 / 0.011 | 1.886 / 0.000 / 7.536 |
| 384 / 1 | 5.499 / 5.510 / 6.098 | 16.231 / 16.204 / 17.121 | 0.156 / 0.097 / 0.413 | 0.005 / 0.005 / 0.009 | 0.978 / 0.000 / 5.841 |
| 384 / 2 | 8.041 / 7.910 / 10.479 | 25.846 / 25.658 / 30.077 | 0.212 / 0.130 / 0.583 | 0.007 / 0.006 / 0.013 | 2.080 / 0.000 / 8.890 |
| 384 / 3 | 7.817 / 7.634 / 10.481 | 29.387 / 29.180 / 32.924 | 0.202 / 0.127 / 0.521 | 0.006 / 0.006 / 0.011 | 2.077 / 0.000 / 7.620 |
| 416 / 1 | 5.458 / 5.326 / 6.334 | 18.637 / 18.532 / 20.433 | 0.171 / 0.103 / 0.442 | 0.005 / 0.005 / 0.009 | 1.145 / 0.000 / 6.129 |
| 416 / 2 | 5.174 / 5.059 / 6.245 | 20.212 / 19.811 / 23.888 | 0.163 / 0.104 / 0.381 | 0.005 / 0.005 / 0.009 | 0.850 / 0.000 / 4.304 |
| 416 / 3 | 9.129 / 9.167 / 11.470 | 38.118 / 38.133 / 42.938 | 0.284 / 0.248 / 0.688 | 0.008 / 0.007 / 0.015 | 3.295 / 0.000 / 10.763 |

### FPS — AVI sintético preexistente

| imgsz / stride | Stream apagado | Mínimo | Stream encendido | Mínimo | FPS origen medios apagado / encendido | >20 / ≥25 en ambos modos |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 320 / 1 | 102.06 / 101.35 / 103.30 | 101.31 | 102.54 / 102.73 / 102.76 | 102.13 | 102.06 / 102.54 | Sí / Sí |
| 320 / 2 | 92.01 / 92.41 / 92.95 | 90.61 | 92.96 / 93.22 / 93.55 | 92.07 | 184.02 / 185.92 | Sí / Sí |
| 320 / 3 | 95.78 / 95.80 / 97.54 | 93.81 | 94.66 / 95.18 / 95.87 | 92.86 | 284.32 / 280.99 | Sí / Sí |
| 352 / 1 | 89.53 / 89.85 / 91.46 | 87.12 | 85.48 / 88.59 / 91.17 | 76.39 | 89.53 / 85.48 | Sí / Sí |
| 352 / 2 | 81.94 / 81.67 / 82.40 | 81.67 | 84.07 / 84.02 / 84.86 | 83.25 | 163.88 / 168.15 | Sí / Sí |
| 352 / 3 | 80.86 / 80.92 / 81.59 | 80.00 | 81.66 / 81.69 / 82.46 | 80.75 | 240.03 / 242.41 | Sí / Sí |
| 384 / 1 | 81.11 / 81.30 / 82.27 | 79.66 | 83.36 / 83.57 / 83.68 | 82.82 | 81.11 / 83.36 | Sí / Sí |
| 384 / 2 | 68.22 / 68.77 / 69.94 | 65.83 | 71.74 / 72.35 / 72.85 | 69.96 | 136.45 / 143.48 | Sí / Sí |
| 384 / 3 | 74.54 / 73.79 / 76.70 | 72.79 | 77.50 / 77.41 / 77.78 | 77.25 | 221.25 / 230.04 | Sí / Sí |
| 416 / 1 | 70.09 / 70.18 / 70.30 | 69.78 | 69.12 / 69.13 / 70.19 | 67.93 | 70.09 / 69.12 | Sí / Sí |
| 416 / 2 | 64.72 / 64.88 / 64.91 | 64.36 | 64.22 / 64.23 / 64.90 | 63.46 | 129.43 / 128.44 | Sí / Sí |
| 416 / 3 | 58.28 / 57.78 / 59.71 | 57.14 | 61.79 / 62.19 / 62.71 | 60.42 | 173.00 / 183.42 | Sí / Sí |

### Latencia por etapa — AVI sintético preexistente, stream apagado

Milisegundos **media / p50 / p95**, agrupando las muestras de las tres pasadas. Captura usa muestras por frame de origen; las otras etapas, por inferencia.

| imgsz / stride | Captura | Inferencia | Tracking | Conteo | Overlay+JPEG |
| --- | ---: | ---: | ---: | ---: | ---: |
| 320 / 1 | 0.407 / 0.402 / 0.480 | 9.215 / 9.193 / 9.705 | 0.063 / 0.061 / 0.085 | 0.003 / 0.003 / 0.004 | 0.000 / 0.000 / 0.000 |
| 320 / 2 | 0.436 / 0.425 / 0.513 | 10.240 / 10.244 / 10.518 | 0.060 / 0.059 / 0.071 | 0.003 / 0.003 / 0.004 | 0.000 / 0.000 / 0.000 |
| 320 / 3 | 0.394 / 0.386 / 0.469 | 9.855 / 9.852 / 10.248 | 0.058 / 0.056 / 0.071 | 0.003 / 0.003 / 0.004 | 0.000 / 0.000 / 0.000 |
| 352 / 1 | 0.397 / 0.392 / 0.476 | 10.497 / 10.323 / 11.148 | 0.065 / 0.064 / 0.078 | 0.004 / 0.003 / 0.004 | 0.000 / 0.000 / 0.000 |
| 352 / 2 | 0.423 / 0.418 / 0.513 | 11.458 / 11.356 / 12.048 | 0.073 / 0.072 / 0.085 | 0.004 / 0.003 / 0.004 | 0.000 / 0.000 / 0.000 |
| 352 / 3 | 0.413 / 0.412 / 0.472 | 11.665 / 11.550 / 12.189 | 0.073 / 0.072 / 0.085 | 0.004 / 0.004 / 0.004 | 0.000 / 0.000 / 0.000 |
| 384 / 1 | 0.441 / 0.435 / 0.503 | 11.582 / 11.627 / 12.029 | 0.073 / 0.073 / 0.082 | 0.004 / 0.004 / 0.004 | 0.000 / 0.000 / 0.000 |
| 384 / 2 | 0.481 / 0.467 / 0.584 | 13.848 / 13.642 / 14.977 | 0.078 / 0.076 / 0.092 | 0.004 / 0.004 / 0.005 | 0.000 / 0.000 / 0.000 |
| 384 / 3 | 0.435 / 0.431 / 0.504 | 12.671 / 12.638 / 13.700 | 0.076 / 0.074 / 0.092 | 0.004 / 0.004 / 0.005 | 0.000 / 0.000 / 0.000 |
| 416 / 1 | 0.447 / 0.443 / 0.488 | 13.478 / 13.375 / 13.891 | 0.077 / 0.076 / 0.086 | 0.004 / 0.004 / 0.004 | 0.000 / 0.000 / 0.000 |
| 416 / 2 | 0.386 / 0.373 / 0.479 | 14.651 / 14.146 / 17.594 | 0.085 / 0.083 / 0.105 | 0.004 / 0.004 / 0.005 | 0.000 / 0.000 / 0.000 |
| 416 / 3 | 0.484 / 0.478 / 0.565 | 16.280 / 16.206 / 17.473 | 0.083 / 0.082 / 0.096 | 0.004 / 0.004 / 0.005 | 0.000 / 0.000 / 0.000 |

### Latencia por etapa — AVI sintético preexistente, stream encendido

Milisegundos **media / p50 / p95**, agrupando las muestras de las tres pasadas. Captura usa muestras por frame de origen; las otras etapas, por inferencia.

| imgsz / stride | Captura | Inferencia | Tracking | Conteo | Overlay+JPEG |
| --- | ---: | ---: | ---: | ---: | ---: |
| 320 / 1 | 0.403 / 0.398 / 0.476 | 9.121 / 9.153 / 9.440 | 0.060 / 0.059 / 0.071 | 0.003 / 0.003 / 0.004 | 0.062 / 0.000 / 0.677 |
| 320 / 2 | 0.428 / 0.419 / 0.501 | 10.064 / 10.069 / 10.564 | 0.059 / 0.058 / 0.072 | 0.003 / 0.003 / 0.004 | 0.075 / 0.000 / 0.753 |
| 320 / 3 | 0.401 / 0.388 / 0.481 | 9.901 / 9.877 / 10.506 | 0.057 / 0.056 / 0.070 | 0.003 / 0.003 / 0.004 | 0.073 / 0.000 / 0.718 |
| 352 / 1 | 0.390 / 0.380 / 0.488 | 11.016 / 10.281 / 13.618 | 0.071 / 0.066 / 0.096 | 0.004 / 0.004 / 0.005 | 0.064 / 0.000 / 0.575 |
| 352 / 2 | 0.411 / 0.405 / 0.495 | 11.090 / 11.063 / 11.448 | 0.071 / 0.070 / 0.081 | 0.003 / 0.003 / 0.004 | 0.078 / 0.000 / 0.715 |
| 352 / 3 | 0.406 / 0.405 / 0.463 | 11.467 / 11.471 / 11.699 | 0.073 / 0.071 / 0.085 | 0.004 / 0.004 / 0.004 | 0.081 / 0.000 / 0.730 |
| 384 / 1 | 0.429 / 0.422 / 0.498 | 11.187 / 11.148 / 11.596 | 0.072 / 0.071 / 0.080 | 0.004 / 0.004 / 0.004 | 0.077 / 0.000 / 0.690 |
| 384 / 2 | 0.451 / 0.440 / 0.553 | 13.050 / 12.769 / 14.949 | 0.076 / 0.075 / 0.088 | 0.004 / 0.004 / 0.005 | 0.103 / 0.000 / 0.800 |
| 384 / 3 | 0.412 / 0.408 / 0.476 | 12.078 / 11.994 / 12.588 | 0.074 / 0.073 / 0.082 | 0.004 / 0.004 / 0.004 | 0.093 / 0.000 / 0.730 |
| 416 / 1 | 0.448 / 0.442 / 0.497 | 13.585 / 13.453 / 14.128 | 0.077 / 0.076 / 0.089 | 0.004 / 0.004 / 0.004 | 0.096 / 0.000 / 0.712 |
| 416 / 2 | 0.391 / 0.377 / 0.481 | 14.680 / 14.093 / 17.878 | 0.085 / 0.083 / 0.104 | 0.004 / 0.004 / 0.005 | 0.086 / 0.000 / 0.585 |
| 416 / 3 | 0.457 / 0.457 / 0.523 | 15.236 / 15.005 / 15.965 | 0.080 / 0.078 / 0.091 | 0.004 / 0.004 / 0.005 | 0.113 / 0.000 / 0.777 |

### Codificación efectiva y carga observada

Coste de un JPEG **cuando sí se codifica**, separado del promedio por inferencia que incluye frames omitidos por el límite de 10 JPEG/s:

| Fuente / configuración | Overlay+JPEG activo, ms media / p50 / p95 | JPEG/s medios |
| --- | ---: | ---: |
| real / 320 / 1 | 5.554 / 5.499 / 5.898 | 8.79 |
| synthetic / 320 / 1 | 0.679 / 0.679 / 0.717 | 9.34 |
| real / 416 / 1 | 5.855 / 5.817 / 6.511 | 8.68 |
| synthetic / 416 / 1 | 0.705 / 0.696 / 0.738 | 9.39 |

Carga ajena estimada (media de las 144 ejecuciones): **11.1%** del total de ocho CPU; rango **1.3–38.4%**. CPU total ocupada media: **54.7%**. Load average de un minuto al iniciar cada ejecución: **3.58–10.98**. Son observaciones de la sesión, no un entorno aislado.

Los modos se ejecutaron secuencialmente. Diferencias de FPS donde stream encendido parece más rápido no prueban que el overlay acelere inferencia: hay variación de carga y condiciones térmicas no controladas. El coste directo de overlay/JPEG está medido en las tablas por etapa.
