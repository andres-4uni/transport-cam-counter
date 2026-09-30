"""Datos de seguimiento independientes de OpenCV y YOLO."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    track_id: int
    # Coordenadas normalizadas a [0, 1].
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float] | None = None
