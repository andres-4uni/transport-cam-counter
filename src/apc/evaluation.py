"""Evaluación de conteos agregados; no conserva tracks ni imágenes."""

from time import perf_counter

from apc.counting.occupancy import OccupancyCounter
from apc.counting.tripwire import TripwireCounter


def count_error(observed: int, expected: int) -> dict:
    if min(observed, expected) < 0:
        raise ValueError("Los conteos no pueden ser negativos")
    absolute = abs(observed - expected)
    return {"expected": expected, "observed": observed, "absolute_error": absolute,
            "error_percent": 100 * absolute / expected if expected else (0.0 if not absolute else None)}


def evaluate(config, source, detector, *, expected_in: int, expected_out: int) -> dict:
    """Una pasada completa, sin calentamiento descartado ni reproducción en bucle."""
    if min(expected_in, expected_out) < 0:
        raise ValueError("La referencia manual no puede ser negativa")
    if getattr(source, "loop", False):
        raise ValueError("La evaluación debe usar una sola pasada")
    counter = TripwireCounter(config.counting)
    occupancy = OccupancyCounter(config.occupancy)
    processed = decoded = 0
    start = perf_counter()
    detector.reset()
    with source:
        for packet in source:
            decoded += 1
            if packet.index % config.detection.vid_stride:
                continue
            occupancy.apply(counter.update(detector.detect(packet.frame)))
            processed += 1
    if not processed:
        raise RuntimeError("El video no entregó frames para evaluar")
    entries = count_error(occupancy.entries, expected_in)
    exits = count_error(occupancy.exits, expected_out)
    denominator = expected_in + expected_out
    absolute = entries["absolute_error"] + exits["absolute_error"]
    return {"decoded_frames": decoded, "processed_frames": processed,
            "elapsed_seconds": perf_counter() - start,
            "in": entries, "out": exits, "absolute_error_sum": absolute,
            "error_percent_combined": 100 * absolute / denominator if denominator else
            (0.0 if not absolute else None), "occupancy": occupancy.occupancy}
