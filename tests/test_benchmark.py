from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from apc.benchmark import benchmark_once, describe
from apc.config import DetectionConfig, load_config
from apc.detection.detector import PersonDetector
from apc.publisher.video import LatestFrame
from apc.sources.file import FileSource


class EmptyDetector:
    last_timings = {"inference": 2.0, "tracking": 0.5}

    def reset(self):
        pass

    def detect(self, frame):
        return []


@pytest.mark.parametrize("stream", [False, True])
def test_benchmark_discards_warmup_and_measures_encoding_in_ram(video_path, monkeypatch, stream):
    config = load_config()
    config = replace(config, visualization=replace(config.visualization, stream=stream))
    # Cadencia determinista para comprobar codificación en cada muestra.
    monkeypatch.setattr(LatestFrame, "can_publish", lambda self: self.config.stream)
    result, samples = benchmark_once(config, FileSource(video_path), EmptyDetector(), warmup=2)
    assert result["decoded_frames"] == result["processed_frames"] == 5
    assert result["measured_frames"] == result["measured_decoded_frames"] == 3
    assert result["encoded_frames"] == (3 if stream else 0)
    assert result["processed_fps"] == pytest.approx(3 / result["elapsed_seconds"])
    assert samples["inference"] == [2.0] * 3
    assert all(value > 0 if stream else value == 0 for value in samples["overlay_jpeg"])
    assert len(samples["capture"]) == 3
    assert not video_path.exists()


def test_benchmark_stride_distinguishes_source_from_processed_fps(video_path):
    config = load_config()
    config = replace(config, detection=replace(config.detection, vid_stride=2))
    result, _ = benchmark_once(config, FileSource(video_path), EmptyDetector(), warmup=2)
    assert result["processed_frames"] == 3
    assert result["measured_frames"] == 1
    assert result["measured_decoded_frames"] == 2
    assert result["source_fps"] == pytest.approx(2 * result["processed_fps"])


def test_benchmark_rejects_realtime_and_short_videos(video_path):
    with pytest.raises(ValueError, match="sin realtime"):
        benchmark_once(load_config(), FileSource(video_path, realtime=True), EmptyDetector())
    with pytest.raises(RuntimeError, match="calentamiento"):
        benchmark_once(load_config(), FileSource(video_path), EmptyDetector(), warmup=5)


def test_statistics_mean_percentiles():
    assert describe([10, 20, 30]) == {"mean": 20, "p50": 20, "p95": 29, "min": 10, "max": 30}


def test_tracking_instrumentation_wraps_once_and_reset_preserves_model():
    class Model:
        def __init__(self):
            self.calls = self.updates = self.resets = 0
            self.callbacks = {"on_predict_start": [], "on_predict_postprocess_end": []}
            self.predictor = SimpleNamespace(trackers=[SimpleNamespace(reset=self.reset)],
                                             results=[SimpleNamespace(boxes=None)])

        def reset(self):
            self.resets += 1

        def add_callback(self, name, callback):
            self.callbacks[name].append(callback)

        def track(self, *args, **kwargs):
            if not self.calls:
                def on_predict_postprocess_end(predictor):
                    self.updates += 1
                on_predict_postprocess_end.__module__ = "ultralytics.trackers.track"
                self.add_callback("on_predict_postprocess_end", on_predict_postprocess_end)
            self.calls += 1
            for callback in self.callbacks["on_predict_postprocess_end"]:
                callback(self.predictor)
            return [SimpleNamespace(boxes=None, speed={"inference": 0, "preprocess": 0, "postprocess": 0})]
    model = Model()
    detector = PersonDetector(DetectionConfig(), Path("unused"), model=model)
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    for _ in range(3):
        detector.detect(frame)
    assert detector.last_timings["tracking"] > 0
    # Un observador numérico y exactamente un callback de ByteTrack envuelto.
    assert len(model.callbacks["on_predict_postprocess_end"]) == 2
    assert model.updates == 3
    detector.reset()
    assert model.resets == 1
    assert detector.model is model
