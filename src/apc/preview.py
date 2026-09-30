"""Anotación en memoria para visualización exclusivamente local."""

import cv2

from apc.config import CountingConfig
from apc.models import Track


def annotate(frame, tracks: list[Track], counting: CountingConfig, fps: float):
    image = frame.copy()
    height, width = image.shape[:2]
    for offset, color in [(0, (0, 255, 255)),
                          (-counting.band_half_width, (128, 128, 128)),
                          (counting.band_half_width, (128, 128, 128))]:
        position = counting.position + offset
        if counting.orientation == "horizontal":
            start, end = (0, int(position * height)), (width - 1, int(position * height))
        else:
            start, end = (int(position * width), 0), (int(position * width), height - 1)
        cv2.line(image, start, end, color, 2)
    for track in tracks:
        x, y = int(track.centroid[0] * width), int(track.centroid[1] * height)
        cv2.circle(image, (x, y), 4, (0, 255, 0), -1)
        cv2.putText(image, f"ID {track.track_id}", (x + 5, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        if track.bbox:
            x1, y1, x2, y2 = track.bbox
            cv2.rectangle(image, (int(x1 * width), int(y1 * height)),
                          (int(x2 * width), int(y2 * height)), (0, 255, 0), 2)
    cv2.putText(image, f"CPU | {fps:.1f} FPS", (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return image
