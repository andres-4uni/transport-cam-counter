import warnings

import cv2
import pytest

from apc.benchmark import benchmark_once
from apc.config import load_config
from apc.evaluation import evaluate
from apc.sources.file import FileSource
from apc.sources.validation import validate_frame_count


@pytest.mark.parametrize("difference", [-2, -1, 1, 2])
def test_small_frame_difference_is_a_warning(difference):
    with pytest.warns(RuntimeWarning, match="aceptada"):
        result = validate_frame_count(1308, 1308 + difference)
    assert result["status"] == "warning"
    assert result["difference"] == difference
    assert result["tolerance"] == 2


def test_exact_frame_count_does_not_warn():
    with warnings.catch_warnings(record=True) as seen:
        result = validate_frame_count(1308, 1308)
    assert seen == []
    assert result["status"] == "ok"
    assert result["warning"] is None


@pytest.mark.parametrize("difference", [-3, 3])
def test_larger_frame_difference_still_fails(difference):
    with pytest.raises(RuntimeError, match="fuera de la tolerancia"):
        validate_frame_count(1308, 1308 + difference)


class EmptyDetector:
    last_timings = {"inference": 0.0, "tracking": 0.0}

    def reset(self):
        pass

    def detect(self, frame):
        return []


@pytest.mark.parametrize("runner", ["evaluation", "benchmark"])
def test_full_pass_preserves_frame_warning(video_path, monkeypatch, runner):
    capture_factory = cv2.VideoCapture
    def open_capture(*args, **kwargs):
        capture = capture_factory(*args, **kwargs)
        get = capture.get
        capture.get = lambda prop: 6 if prop == cv2.CAP_PROP_FRAME_COUNT else get(prop)
        return capture
    monkeypatch.setattr(cv2, "VideoCapture", open_capture)
    with pytest.warns(RuntimeWarning, match="declarados=6, decodificados=5"):
        if runner == "evaluation":
            result = evaluate(load_config(), FileSource(video_path), EmptyDetector(), expected_in=0, expected_out=0)
        else:
            result, _ = benchmark_once(load_config(), FileSource(video_path), EmptyDetector(), warmup=2)
    assert result["decoded_frames"] == 5
    assert result["frame_validation"]["difference"] == -1


def test_limited_benchmark_does_not_compare_with_full_file(video_path):
    result, _ = benchmark_once(load_config(), FileSource(video_path), EmptyDetector(), warmup=2, max_frames=3)
    assert result["decoded_frames"] == 3
    assert "frame_validation" not in result
