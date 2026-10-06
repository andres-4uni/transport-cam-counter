"""Diagnóstico con tracks y video sintético en RAM; nunca abre videos reales."""
from dataclasses import replace

import pytest

from apc.config import load_config
from apc.evaluation import evaluate
from apc.models import Track
from apc.sources.file import FileSource


class Detector:
    last_diagnostics = {"person_detections": 2, "area_rejections": 1, "low_confidence_detections": 1}

    def reset(self):
        self.index = 0

    def detect(self, frame):
        y = [0.2, 0.3, 0.7, 0.8, 0.8][self.index]
        self.index += 1
        return [Track(11, (0.3, y), (0.0, y - 0.1, 0.6, min(1, y + 0.1)))]


def test_numeric_events_include_source_frame_anchor_age_and_sides(video_path):
    result = evaluate(load_config(), FileSource(video_path), Detector(), expected_in=1,
                      expected_out=0, diagnostics=True)
    detail = result["diagnostics"]
    event, = detail["events"]
    assert event["frame"] == event["processed_frame"] == 2
    assert event["video_seconds"] == 0.2
    assert event["anchor"] == (0.3, 0.7)
    assert event["age_observations"] == 3
    assert (event["from_side"], event["to_side"], event["direction"]) == (-1, 1, "in")
    assert detail["person_detections"] == 10
    assert detail["area_rejections"] == detail["low_confidence_detections"] == 5
    assert detail["ids"][0]["border_observations"] == 5
    assert result["fps"] > 0


def test_verified_reference_preserves_declared_and_does_not_widen_tolerance(video_path, monkeypatch):
    source = FileSource(video_path)
    open_capture = source._open_capture
    def altered_metadata():
        capture = open_capture()
        source.metadata["frames"] = 20
        return capture
    monkeypatch.setattr(source, "_open_capture", altered_metadata)
    result = evaluate(load_config(), source, Detector(), expected_in=1, expected_out=0,
                      verified_frames=5)
    assert result["frame_validation"]["container_declared"] == 20
    assert result["frame_validation"]["container_difference"] == -15
    assert result["frame_validation"]["tolerance"] == 2
    with pytest.raises(RuntimeError, match="fuera de la tolerancia"):
        evaluate(load_config(), FileSource(video_path), Detector(), expected_in=1,
                 expected_out=0, verified_frames=8)


def test_stride_reports_source_and_processed_indices_separately(video_path):
    config = load_config()
    config = replace(config, detection=replace(config.detection, vid_stride=2))
    result = evaluate(config, FileSource(video_path), Detector(), expected_in=1,
                      expected_out=0, diagnostics=True)
    event, = result["diagnostics"]["events"]
    assert event["frame"] == 4 and event["processed_frame"] == 2
    assert event["video_seconds"] == 0.4
    assert result["processed_frames"] == 3
