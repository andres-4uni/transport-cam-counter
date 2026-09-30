"""Captura de webcam local en hilo; conserva frames recientes."""

import cv2

from apc.config import SourceConfig
from apc.sources.base import ThreadedSource


class WebcamSource(ThreadedSource):
    def __init__(self, config: SourceConfig):
        super().__init__(config.queue_size, live=True)
        self.config = config

    def _open_capture(self):
        capture = cv2.VideoCapture(self.config.index)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("No se pudo abrir la webcam; revise índice y permisos del sistema")
        # Son solicitudes: algunos dispositivos no aceptan esta resolución.
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        return capture
