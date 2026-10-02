from dataclasses import replace
from time import perf_counter

import pytest

from apc.config import load_config
from apc.evaluation import count_error, evaluate
from apc.models import Track
from apc.sources import create_source
from apc.sources.file import FileSource


def test_loop_rewinds_frames_and_marks_cycles(video_path):
    with FileSource(video_path, loop=True, queue_size=1) as source:
        packets = [source.read() for _ in range(12)]
    assert [p.index for p in packets] == list(range(5)) * 2 + [0, 1]
    assert [p.cycle for p in packets] == [0] * 5 + [1] * 5 + [2] * 2
    assert packets[0].frame.mean() == packets[5].frame.mean()
    assert all(p.capture_ms >= 0 for p in packets)
    assert not source._thread.is_alive()
    assert not video_path.exists()


def test_realtime_limits_delivery_to_original_fps(video_path):
    with FileSource(video_path, realtime=True) as source:
        assert source.metadata == {"fps": 10, "width": 96, "height": 64, "frames": 5}
        start = perf_counter()
        packets = list(source)
        elapsed = perf_counter() - start
    assert len(packets) == 5
    assert elapsed >= 0.39  # 4 intervalos de 100 ms; sin límite superior frágil.


def test_factory_passes_file_playback_options(video_path):
    config = load_config()
    config = replace(config, source=replace(config.source, path=str(video_path), realtime=True, loop=True))
    source = create_source(config)
    assert source.realtime and source.loop


class CrossingDetector:
    def reset(self):
        self.calls = 0

    def detect(self, frame):
        self.calls += 1
        y = (0.2, 0.25, 0.7, 0.75, 0.8)[self.calls - 1]
        return [Track(1, (0.3, y)), Track(2, (0.7, 1 - y))]


def test_evaluate_synthetic_video_counts_both_directions(video_path):
    result = evaluate(load_config(), FileSource(video_path), CrossingDetector(), expected_in=1, expected_out=1)
    assert result["decoded_frames"] == result["processed_frames"] == 5
    assert result["in"] == result["out"] == count_error(1, 1)
    assert result["absolute_error_sum"] == result["error_percent_combined"] == 0
    assert result["occupancy"] == 0


@pytest.mark.parametrize("observed,expected,error,percent", [(4, 6, 2, 100 / 3), (7, 6, 1, 100 / 6),
                                                         (0, 0, 0, 0), (1, 0, 1, None)])
def test_absolute_and_percent_error(observed, expected, error, percent):
    result = count_error(observed, expected)
    assert result["absolute_error"] == error
    if percent is None:
        assert result["error_percent"] is None
    else:
        assert result["error_percent"] == pytest.approx(percent)


def test_evaluation_rejects_loop(video_path):
    with pytest.raises(ValueError, match="pasada"):
        evaluate(load_config(), FileSource(video_path, loop=True), CrossingDetector(), expected_in=1, expected_out=1)
