"""Video sintético en RAM: ningún test escribe frames, imágenes ni videos."""

from pathlib import Path

import cv2
import numpy as np
import pytest


class MemoryCapture:
    def __init__(self):
        self.index = 0
        self.released = False

    def isOpened(self):
        return not self.released

    def get(self, prop):
        return {cv2.CAP_PROP_FPS: 10, cv2.CAP_PROP_FRAME_WIDTH: 96,
                cv2.CAP_PROP_FRAME_HEIGHT: 64, cv2.CAP_PROP_FRAME_COUNT: 5}.get(prop, 0)

    def set(self, prop, value):
        if prop == cv2.CAP_PROP_POS_FRAMES and value == 0:
            self.index = 0
            return True
        return False

    def read(self):
        if self.index == 5:
            return False, None
        value = (20, 60, 100, 140, 180)[self.index]
        self.index += 1
        return True, np.full((64, 96, 3), value, dtype=np.uint8)

    def release(self):
        self.released = True


@pytest.fixture
def video_path(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.avi"
    is_file = Path.is_file
    capture = cv2.VideoCapture
    monkeypatch.setattr(Path, "is_file", lambda p: True if p == path else is_file(p))
    monkeypatch.setattr(cv2, "VideoCapture", lambda p, *a, **k:
                        MemoryCapture() if str(p) == str(path) else capture(p, *a, **k))
    return path


@pytest.fixture(autouse=True)
def prohibit_image_files(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No se permite escribir frames/imágenes/videos durante las pruebas")
    monkeypatch.setattr(cv2, "imwrite", forbidden)
    monkeypatch.setattr(cv2, "VideoWriter", forbidden)
