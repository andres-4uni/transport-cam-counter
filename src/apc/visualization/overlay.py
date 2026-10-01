"""Overlay puro: devuelve una copia anotada, sin IO ni estado global."""

from collections import deque
from collections.abc import Mapping, Sequence

import cv2
import numpy as np

from apc.config import CountingConfig, VisualizationConfig
from apc.models import Track


def _bgr(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index + 2], 16) for index in (5, 3, 1))


def draw_overlay(frame: np.ndarray, tracks: Sequence[Track], counting: CountingConfig,
                 config: VisualizationConfig, *, entries: int, exits: int, occupancy: int,
                 fps: float = 0, simulated: bool = False,
                 trails: Mapping[int, Sequence[tuple[float, float]]] | None = None) -> np.ndarray:
    """No modifica el frame, tracks ni estelas; colores YAML en formato RGB."""
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("El overlay requiere un frame BGR uint8 de tres canales")
    image = frame.copy()
    height, width = image.shape[:2]

    def point(position):
        x, y = position
        return (max(0, min(width - 1, round(x * (width - 1)))),
                max(0, min(height - 1, round(y * (height - 1)))))

    def line(position, color, thickness):
        ends = ((0, position), (1, position)) if counting.orientation == "horizontal" else ((position, 0), (position, 1))
        cv2.line(image, point(ends[0]), point(ends[1]), _bgr(color), thickness)

    if config.show_band:
        for offset in (-counting.band_half_width, counting.band_half_width):
            line(counting.position + offset, config.band_color, 1)
    if config.show_line:
        line(counting.position, config.line_color, 2)
    for track in tracks:
        if config.show_trails and trails and track.track_id in trails:
            path = np.array([point(p) for p in trails[track.track_id]], dtype=np.int32)
            if len(path) > 1:
                cv2.polylines(image, [path], False, _bgr(config.trail_color), 2)
        x, y = point(track.centroid)
        if config.show_boxes and track.bbox:
            x1, y1, x2, y2 = track.bbox
            cv2.rectangle(image, point((x1, y1)), point((x2, y2)), _bgr(config.box_color), 2)
        if config.show_ids:
            cv2.putText(image, f"ID {track.track_id}", (max(0, x - 20), max(16, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, _bgr(config.box_color), 2)
    if config.show_counters:
        cv2.rectangle(image, (0, 0), (width - 1, 78), (15, 20, 28), -1)
        for index, (text, color) in enumerate([
            (f"IN {entries}", config.in_color), (f"OUT {exits}", config.out_color),
            (f"OCUPACION {occupancy}", config.occupancy_color),
        ]):
            cv2.putText(image, text, (12 + index * width // 3, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, _bgr(color), 2)
        cv2.putText(image, f"{fps:.1f} FPS", (12, 64),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 210, 220), 1)
    if simulated:
        cv2.putText(image, "SIMULACION - SIN CAMARA", (12, height - 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return image


class TrackTrails:
    """Estado externo al overlay: solo coordenadas de IDs presentes, nunca frames."""

    def __init__(self, length: int):
        self.length = length
        self._paths: dict[int, deque] = {}

    def update(self, tracks: Sequence[Track]) -> dict[int, tuple]:
        active = {track.track_id for track in tracks}
        self._paths = {key: path for key, path in self._paths.items() if key in active}
        for track in tracks:
            self._paths.setdefault(track.track_id, deque(maxlen=self.length)).append(track.centroid)
        return {key: tuple(path) for key, path in self._paths.items()}
