"""Lectura de archivos locales; nunca escribe frames."""

from pathlib import Path

import cv2

from apc.sources.base import ThreadedSource


class FileSource(ThreadedSource):
    def __init__(self, path: str | Path, queue_size: int = 2):
        super().__init__(queue_size)
        self.path = Path(path)

    def _open_capture(self):
        if not self.path.is_file():
            raise FileNotFoundError(f"No existe el video local: {self.path}")
        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("OpenCV no pudo abrir el archivo de video")
        return capture
