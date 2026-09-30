"""Captura HTTP(S)/RTSP mediante FFmpeg con tiempos de espera acotados."""

from urllib.parse import urlsplit

import cv2

from apc.config import SourceConfig
from apc.sources.base import ThreadedSource


class StreamSource(ThreadedSource):
    def __init__(self, config: SourceConfig):
        try:
            url = urlsplit(config.url)
            valid = url.scheme in {"http", "https", "rtsp"} and bool(url.hostname)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("La fuente requiere una URL HTTP(S) o RTSP válida")
        super().__init__(config.queue_size, live=True,
                         close_timeout=config.read_timeout_ms / 1000 + 1)
        self.config = config

    def _open_capture(self):
        # Estos timeouts se establecen al abrir, no con capture.set().
        capture = cv2.VideoCapture(self.config.url, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.config.open_timeout_ms,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.config.read_timeout_ms,
        ])
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("No se pudo abrir el stream; revise conectividad, URL y soporte FFmpeg")
        return capture
