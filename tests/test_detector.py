from pathlib import Path
from types import SimpleNamespace

import numpy as np

from apc.config import CountingConfig, DetectionConfig
from apc.detection.detector import PersonDetector
from apc.models import Track
from apc.preview import annotate


class Tensor:
    def __init__(self, values):
        self.values = values

    def int(self): return self
    def cpu(self): return self
    def tolist(self): return self.values


def test_detector_filters_area_and_disables_saving():
    calls = []
    def track(frame, **kwargs):
        calls.append(kwargs)
        return [SimpleNamespace(boxes=SimpleNamespace(
            id=Tensor([1, 2, 3]),
            xyxy=Tensor([[10, 10, 30, 70], [0, 0, 1, 1], [0, 0, 100, 100]])))]
    detector = PersonDetector(DetectionConfig(), Path("unused"), model=SimpleNamespace(track=track))
    tracks = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
    assert tracks == [Track(1, (0.2, 0.4), (0.1, 0.1, 0.3, 0.7))]
    assert calls[0]["classes"] == [0]
    assert calls[0]["device"] == "cpu"
    assert calls[0]["persist"] is True
    assert calls[0]["tracker"] == "bytetrack.yaml"
    assert all(calls[0][key] is False for key in ("save", "save_txt", "save_crop", "show"))


def test_untracked_detections():
    model = SimpleNamespace(track=lambda *a, **k: [SimpleNamespace(boxes=SimpleNamespace(id=None))])
    detector = PersonDetector(DetectionConfig(), Path("unused"), model=model)
    assert detector.detect(np.zeros((100, 100, 3), dtype=np.uint8)) == []


def test_preview_is_in_memory_and_keeps_original():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    result = annotate(frame, [Track(7, (0.2, 0.3))], CountingConfig(), 21)
    assert np.count_nonzero(result) > 0
    assert np.count_nonzero(frame) == 0
