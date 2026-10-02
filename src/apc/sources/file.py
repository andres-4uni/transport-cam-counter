"""Lectura de archivos locales; nunca escribe frames."""

from pathlib import Path
from math import isfinite
from time import perf_counter, time

import cv2

from apc.sources.base import FramePacket, ThreadedSource


class FileSource(ThreadedSource):
    def __init__(self, path: str | Path, queue_size: int = 2, *,
                 realtime: bool = False, loop: bool = False):
        super().__init__(queue_size)
        self.path = Path(path)
        self.realtime = realtime
        self.loop = loop
        self.metadata: dict[str, float | int] = {}
        self._delivered = 0
        self._started: float | None = None

    def _open_capture(self):
        if not self.path.is_file():
            raise FileNotFoundError(f"No existe el video local: {self.path}")
        capture = cv2.VideoCapture(str(self.path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError("OpenCV no pudo abrir el archivo de video")
        self.metadata = {
            "fps": capture.get(cv2.CAP_PROP_FPS),
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "frames": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        }
        if self.realtime and (not isfinite(self.metadata["fps"]) or self.metadata["fps"] <= 0):
            capture.release()
            raise RuntimeError("El archivo no informa FPS válidos para --realtime")
        return capture

    def _capture(self, capture) -> None:
        index = cycle = 0
        try:
            while not self._stop.is_set():
                start = perf_counter()
                ok, frame = capture.read()
                elapsed = (perf_counter() - start) * 1000
                if not ok:
                    if not self.loop:
                        break
                    if index == 0 or not capture.set(cv2.CAP_PROP_POS_FRAMES, 0):
                        raise RuntimeError("No se pudo reiniciar el archivo de video")
                    cycle += 1
                    index = 0
                    continue
                self._put(FramePacket(index, time(), frame, cycle, elapsed))
                index += 1
        except Exception as error:
            self._put(RuntimeError(f"Falló la lectura del archivo: {error}"))
        finally:
            capture.release()
            self._put(None)

    def read(self) -> FramePacket | None:
        packet = super().read()
        if packet is not None and self.realtime:
            if self._started is None:
                self._started = perf_counter()
            # Ritmo de entrega original, sin descartar frames; incluye los saltados
            # por vid_stride y continúa sin saltos temporales al repetir el archivo.
            deadline = self._started + self._delivered / self.metadata["fps"]
            self._stop.wait(max(0, deadline - perf_counter()))
            self._delivered += 1
        return packet
