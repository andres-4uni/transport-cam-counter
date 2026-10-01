"""Un único JPEG en memoria; sin archivos, historial de frames ni grabación."""

from threading import Condition, Event
from time import monotonic

import cv2

from apc.config import VisualizationConfig


class LatestFrame:
    def __init__(self, config: VisualizationConfig, stale_after_seconds: float = 3):
        if not 0 < config.max_fps <= 60 or not 1 <= config.jpeg_quality <= 100:
            raise ValueError("FPS o calidad JPEG inválidos")
        if stale_after_seconds <= 0:
            raise ValueError("Caducidad de video inválida")
        self.config = config
        self.stale_after_seconds = stale_after_seconds
        self.closed = Event()
        self._condition = Condition()
        self._jpeg: bytes | None = None
        self._version = 0
        self._published_at = float("-inf")

    def can_publish(self) -> bool:
        with self._condition:
            return (self.config.stream and not self.closed.is_set()
                    and monotonic() - self._published_at >= 1 / self.config.max_fps)

    def publish(self, frame) -> bool:
        with self._condition:
            if not self.can_publish():
                return False
            ok, encoded = cv2.imencode(".jpg", frame,
                                       [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality])
            if not ok:
                raise RuntimeError("No se pudo codificar el JPEG en memoria")
            self._jpeg = encoded.tobytes()
            self._version += 1
            self._published_at = monotonic()
            self._condition.notify_all()
            return True

    def status(self) -> dict[str, int]:
        with self._condition:
            enabled = self.config.stream and not self.closed.is_set()
            ready = (enabled and self._jpeg is not None
                     and monotonic() - self._published_at < self.stale_after_seconds)
            return {"enabled": int(enabled), "ready": int(ready)}

    def next_frame(self, after: int, timeout: float = 0.5) -> tuple[int, bytes] | None:
        with self._condition:
            self._condition.wait_for(lambda: self.closed.is_set() or self._version > after, timeout)
            if self._version > after and self.status()["ready"]:
                return self._version, self._jpeg
            return None

    def close(self) -> None:
        with self._condition:
            self.closed.set()
            self._jpeg = None
            self._condition.notify_all()
