"""Selección de contador y reloj compartidos por todas las fuentes y ejecutores."""

from apc.counting.dual_zone import DualZoneCounter
from apc.counting.tripwire import TripwireCounter


def create_counter(config, *, diagnostic=None):
    cls = DualZoneCounter if config.mode == "dual_zone" else TripwireCounter
    return cls(config, diagnostic=diagnostic)


def update_counter(counter, tracks, packet, source):
    if not counter.config.max_missing_seconds:
        return counter.update(tracks)
    seconds = getattr(packet, "media_seconds", None)
    if seconds is None and hasattr(source, "metadata") and not getattr(source, "_live", False):
        fps = source.metadata.get("fps", 0)
        if fps <= 0:
            raise ValueError("Archivo sin tiempo de contenido ni FPS válido")
        seconds = packet.index / fps
    if seconds is None:
        seconds = packet.timestamp
    return counter.update(tracks, timestamp=seconds)


def configure_detector_clock(detector, source):
    if hasattr(detector, "set_source_fps"):
        detector.set_source_fps(getattr(source, "metadata", {}).get("fps", 0))
