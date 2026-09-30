"""Contrato de captura y lectura ordenada en un hilo separado."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Event, Thread
from time import time
from typing import Iterator

import numpy as np


@dataclass(frozen=True)
class FramePacket:
    index: int
    timestamp: float
    frame: np.ndarray


class VideoSource(ABC):
    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> FramePacket | None: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()

    def __iter__(self) -> Iterator[FramePacket]:
        while (packet := self.read()) is not None:
            yield packet


class ThreadedSource(VideoSource):
    """Cola acotada: no acumula un video completo en memoria."""

    def __init__(self, queue_size: int = 2):
        if queue_size < 1:
            raise ValueError("queue_size debe ser positivo")
        self._queue: Queue = Queue(maxsize=queue_size)
        self._stop = Event()
        self._thread: Thread | None = None
        self._ended = False

    @abstractmethod
    def _open_capture(self): ...

    def open(self) -> None:
        if self._thread is not None:
            raise RuntimeError("La fuente ya fue abierta; cree otra instancia")
        capture = self._open_capture()
        self._thread = Thread(target=self._capture, args=(capture,), daemon=True)
        self._thread.start()

    def _put(self, value) -> None:
        while not self._stop.is_set():
            try:
                self._queue.put(value, timeout=0.1)
                return
            except Full:
                continue

    def _capture(self, capture) -> None:
        try:
            index = 0
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    break
                self._put(FramePacket(index, time(), frame))
                index += 1
        except Exception:
            # Evitar mensajes del backend que podrían contener credenciales de una URL.
            self._put(RuntimeError("Falló la lectura de la fuente de video"))
        finally:
            capture.release()
            self._put(None)

    def read(self) -> FramePacket | None:
        if self._thread is None:
            raise RuntimeError("Abra la fuente antes de leer")
        if self._ended or self._stop.is_set():
            return None
        while not self._stop.is_set():
            try:
                value = self._queue.get(timeout=0.1)
                if isinstance(value, Exception):
                    raise value
                if value is None:
                    self._ended = True
                return value
            except Empty:
                continue
        return None

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError("El backend de captura no respondió al cierre")
