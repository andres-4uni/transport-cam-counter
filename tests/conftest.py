"""Videos artificiales: las pruebas no capturan ni almacenan personas."""

import cv2
import numpy as np
import pytest


@pytest.fixture
def video_path(tmp_path):
    path = tmp_path / "synthetic.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (96, 64))
    assert writer.isOpened()
    for value in (20, 60, 100, 140, 180):
        writer.write(np.full((64, 96, 3), value, dtype=np.uint8))
    writer.release()
    return path
