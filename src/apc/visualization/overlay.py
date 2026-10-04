"""Overlay puro: devuelve una copia anotada, sin IO ni estado global."""

from collections import deque
from collections.abc import Mapping, Sequence

import cv2
import numpy as np

from apc.config import CountingConfig, VisualizationConfig
from apc.models import Track


def _bgr(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index + 2], 16) for index in (5, 3, 1))


def _dashed_line(image: np.ndarray, start: tuple[int, int], end: tuple[int, int],
                 color: tuple[int, int, int], dash: int = 10, gap: int = 7) -> None:
    """Los límites discontinuos se distinguen de la línea central sólida."""
    length = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
    if not length:
        return
    for offset in range(0, length + 1, dash + gap):
        finish = min(offset + dash, length)
        points = [tuple(round(a + (b - a) * distance / length)
                        for a, b in zip(start, end)) for distance in (offset, finish)]
        cv2.line(image, points[0], points[1], color, 1)


def _draw_counting_legend(image: np.ndarray, counting: CountingConfig,
                          config: VisualizationConfig) -> None:
    """Leyenda local: las flechas representan el movimiento, no el lado de origen."""
    width = image.shape[1]
    scale = min(1.1, max(0.38, width / 900))
    row = max(19, round(40 * scale))
    top = 96 if config.show_counters else row
    font = cv2.FONT_HERSHEY_SIMPLEX

    def label(text, x, y, color):
        # El contorno mantiene legibilidad sin cubrir la imagen con otro panel.
        cv2.putText(image, text, (x, y), font, scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(image, text, (x, y), font, scale, color, 1, cv2.LINE_AA)

    line_color = _bgr(config.line_color)
    cv2.line(image, (12, top - 5), (37, top - 5), line_color, 2)
    label("LINEA DE CONTEO", 46, top, line_color)
    # Hershey no incluye Í: dibujamos su acento en vez de imprimir caracteres '?'.
    prefix_width = cv2.getTextSize("L", font, scale, 1)[0][0]
    letter_width, letter_height = cv2.getTextSize("I", font, scale, 1)[0]
    accent_x = 46 + prefix_width + letter_width // 2 - 1
    accent_y = top - letter_height - 2
    cv2.line(image, (accent_x, accent_y), (accent_x + 3, accent_y - 3), (0, 0, 0), 3)
    cv2.line(image, (accent_x, accent_y), (accent_x + 3, accent_y - 3), line_color, 1)
    y = top + row
    if config.show_band:
        band_color = _bgr(config.band_color)
        _dashed_line(image, (12, y - 5), (37, y - 5), band_color, dash=7, gap=5)
        label(f"BANDA +/- {counting.band_half_width:.3f}", 46, y, band_color)
        y += row

    # Dos flechas en la leyenda evitan ocultar cruces junto a la línea de conteo.
    # En imagen, x crece a la derecha e y crece hacia abajo.
    for index, positive in enumerate((False, True)):
        entering = positive == counting.entry_positive
        color = _bgr(config.in_color if entering else config.out_color)
        x = 12 + index * max(104, round(220 * scale))
        label("IN" if entering else "OUT", x, y, color)
        axis_x, axis_y = x + round(145 * scale), y - round(10 * scale)
        radius = max(7, round(17 * scale))
        if counting.orientation == "vertical":
            start, end = (axis_x - radius, axis_y), (axis_x + radius, axis_y)
        else:
            start, end = (axis_x, axis_y - radius), (axis_x, axis_y + radius)
        if not positive:
            start, end = end, start
        cv2.arrowedLine(image, start, end, (0, 0, 0), 4, tipLength=0.4)
        cv2.arrowedLine(image, start, end, color, 2, tipLength=0.4)

    if config.show_boxes or config.show_ids:
        y += row
        cv2.circle(image, (24, y - 5), 5, (0, 0, 0), -1)
        cv2.circle(image, (24, y - 5), 3, (255, 255, 255), -1)
        label("PUNTO = CENTROIDE", 46, y, (255, 255, 255))


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

    def line(position, color, thickness, dashed=False):
        ends = ((0, position), (1, position)) if counting.orientation == "horizontal" else ((position, 0), (position, 1))
        if dashed:
            _dashed_line(image, point(ends[0]), point(ends[1]), _bgr(color))
        else:
            cv2.line(image, point(ends[0]), point(ends[1]), _bgr(color), thickness)

    if config.show_band:
        for offset in (-counting.band_half_width, counting.band_half_width):
            line(counting.position + offset, config.band_color, 1, dashed=True)
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
        if config.show_boxes or config.show_ids:
            cv2.circle(image, (x, y), 6, (0, 0, 0), -1)
            cv2.circle(image, (x, y), 4, (255, 255, 255), -1)
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
    if config.show_line:
        _draw_counting_legend(image, counting, config)
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
