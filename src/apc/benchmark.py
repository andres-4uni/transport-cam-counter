"""Mediciones del pipeline CPU; resultados numéricos y JPEG efímero en RAM."""

from collections import defaultdict
from time import perf_counter

import numpy as np

from apc.counting.occupancy import OccupancyCounter
from apc.counting.tripwire import TripwireCounter
from apc.publisher.video import LatestFrame
from apc.visualization.overlay import TrackTrails, draw_overlay


def describe(values) -> dict[str, float]:
    if not len(values):
        raise ValueError("No hay muestras para calcular estadísticas")
    return {"mean": float(np.mean(values)), "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)), "min": float(np.min(values)),
            "max": float(np.max(values))}


def benchmark_once(config, source, detector, *, warmup: int = 30, max_frames: int = 0):
    """Descarta N inferencias iniciales; captura y cómputo se solapan en hilos."""
    if warmup < 2 or max_frames < 0 or getattr(source, "realtime", False):
        raise ValueError("Benchmark: warmup >= 2, max_frames >= 0 y sin realtime")
    if getattr(source, "loop", False) and not max_frames:
        raise ValueError("Un archivo en bucle necesita un límite de frames")
    detector.reset()
    counter, occupancy = TripwireCounter(config.counting), OccupancyCounter(config.occupancy)
    video = LatestFrame(config.visualization)
    history = TrackTrails(config.visualization.trail_length) if config.visualization.show_trails else None
    samples = defaultdict(list)
    processed = decoded = measured = measured_decoded = encoded = 0
    window_start = previous_end = None
    cycle = 0
    try:
        with source:
            while True:
                start = perf_counter()
                packet = source.read()
                wait_ms = (perf_counter() - start) * 1000
                if packet is None:
                    break
                decoded += 1
                if window_start is not None:
                    measured_decoded += 1
                    samples["capture"].append(packet.capture_ms)
                    samples["capture_wait"].append(wait_ms)
                if packet.cycle != cycle:
                    cycle = packet.cycle
                    detector.reset()
                    counter, occupancy = TripwireCounter(config.counting), OccupancyCounter(config.occupancy)
                    history = TrackTrails(config.visualization.trail_length) if history else None
                if packet.index % config.detection.vid_stride == 0:
                    tracks = detector.detect(packet.frame)
                    start = perf_counter()
                    occupancy.apply(counter.update(tracks))
                    trails = history.update(tracks) if history else None
                    counting_ms = (perf_counter() - start) * 1000
                    overlay_ms = 0.0
                    published = False
                    if video.can_publish():
                        start = perf_counter()
                        annotated = draw_overlay(packet.frame, tracks, config.counting,
                                                 config.visualization, entries=occupancy.entries,
                                                 exits=occupancy.exits, occupancy=occupancy.occupancy,
                                                 trails=trails)
                        published = video.publish(annotated)
                        overlay_ms = (perf_counter() - start) * 1000
                        del annotated
                    end = perf_counter()
                    processed += 1
                    if processed > warmup:
                        measured += 1
                        for key, value in detector.last_timings.items():
                            samples[key].append(value)
                        samples["counting"].append(counting_ms)
                        samples["overlay_jpeg"].append(overlay_ms)
                        samples["step"].append((end - previous_end) * 1000)
                        samples["instantaneous_fps"].append(1 / (end - previous_end))
                        if published:
                            encoded += 1
                            samples["encoded_only"].append(overlay_ms)
                    if processed == warmup:
                        window_start = end
                    previous_end = end
                if max_frames and decoded >= max_frames:
                    break
            window_end = perf_counter()
    finally:
        video.close()
    if not measured:
        raise RuntimeError("El video no alcanza el calentamiento más una muestra")
    elapsed = window_end - window_start
    result = {"decoded_frames": decoded, "processed_frames": processed,
              "measured_frames": measured, "measured_decoded_frames": measured_decoded,
              "warmup_frames": warmup, "elapsed_seconds": elapsed,
              "processed_fps": measured / elapsed,
              "source_fps": measured_decoded / elapsed, "encoded_frames": encoded,
              "encoded_fps": encoded / elapsed,
              "stages_ms": {key: describe(values) for key, values in samples.items()
                            if key != "instantaneous_fps"},
              "instantaneous_fps": describe(samples["instantaneous_fps"]),
              "metadata": getattr(source, "metadata", {})}
    return result, samples
