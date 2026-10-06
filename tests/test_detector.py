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


def test_detector_uses_configured_tracker_without_changing_centroid():
    from dataclasses import replace
    calls = []
    def track(frame, **kwargs):
        calls.append(kwargs)
        return [SimpleNamespace(boxes=SimpleNamespace(
            id=Tensor([1]), xyxy=Tensor([[0, 20, 80, 100]])))]
    detector = PersonDetector(replace(DetectionConfig(), tracker='/tmp/custom-bytetrack.yaml'),
                              Path('unused'), model=SimpleNamespace(track=track))
    tracks = detector.detect(np.zeros((100, 100, 3), dtype=np.uint8))
    assert calls[0]['tracker'] == '/tmp/custom-bytetrack.yaml'
    assert tracks[0].centroid == (0.4, 0.6)
    assert tracks[0].bbox == (0, 0.2, 0.8, 1)


def test_raw_diagnostics_use_tracker_threshold_before_association():
    detector = PersonDetector(DetectionConfig(), Path('unused'), model=SimpleNamespace(track=None))
    predictor = SimpleNamespace(results=[SimpleNamespace(boxes=SimpleNamespace(conf=Tensor([.3, .5])))],
                                trackers=[SimpleNamespace(args=SimpleNamespace(track_high_thresh=.4))])
    detector._observe_detections(predictor)
    assert detector.last_diagnostics == {'person_detections': 2, 'low_confidence_detections': 1}


def test_roi_maps_boxes_and_area_to_full_frame_without_modifying_pixels():
    calls = []
    def track(frame, **kwargs):
        calls.append(frame.shape)
        return [SimpleNamespace(boxes=SimpleNamespace(
            id=Tensor([7, 8]), xyxy=Tensor([[0, 0, 20, 40], [0, 0, 1, 1]])))]
    config = DetectionConfig(imgsz=640, roi_left=.2, roi_top=.1,
                             roi_right=.8, roi_bottom=.9)
    detector = PersonDetector(config, Path('unused'), model=SimpleNamespace(track=track))
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    assert detector.detect(frame) == [Track(7, (.3, .2), (.2, .1, .4, .3))]
    assert calls == [(160, 60, 3)]
    assert detector.last_diagnostics['area_rejections'] == 1
    assert not frame.any()


def test_tracker_seconds_use_source_fps_and_inference_stride():
    detector = PersonDetector(DetectionConfig(track_buffer_seconds=.9, vid_stride=2),
                              Path('unused'), model=SimpleNamespace(track=None))
    detector.set_source_fps(29.793)
    tracker = SimpleNamespace(args=SimpleNamespace(track_high_thresh=.25))
    detector._observe_detections(SimpleNamespace(
        results=[SimpleNamespace(boxes=None)], trackers=[tracker]))
    assert tracker.max_time_lost == 14
