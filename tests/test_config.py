from pathlib import Path

import pytest
import yaml

from apc.config import CountingConfig, counting_from_dict, load_config, validate_counting


def test_defaults():
    config = load_config()
    assert not config.debug.show_video
    assert not config.debug.counting
    assert not config.visualization.stream
    assert config.detection.imgsz == 320
    assert config.resolve("data/demo.avi") == Path.cwd() / "data/demo.avi"


@pytest.mark.parametrize("value", [
    {"detection": {"imgsz": 319}}, {"detection": {"conf": 0}},
    {"detection": {"vid_stride": 0}}, {"debug": {"show_video": "false"}},
    {"source": {"typo": 1}}, {"occupancy": {"capacity": 0}},
    {"counting": {"position": 1}}, {"occupancy": {"red_above": 0.2}},
    {"telemetry": {"interval_seconds": float("nan")}}, {"wrong": {}},
    {"simulation": {"period_seconds": 0}},
    {"simulation": {"maximum_ratio": 1.2}},
    {"simulation": {"low_target_ratio": 0.7}},
    {"simulation": {"variation_ratio": 0.4}},
    {"simulation": {"variable_initial_ratio": -0.1}},
    {"visualization": {"stream": "false"}},
    {"visualization": {"jpeg_quality": 101}},
    {"visualization": {"max_fps": 0}},
    {"visualization": {"line_color": "blue"}},
    {"visualization": {"trail_length": 0}},
    {"simulation": {"fake_cycle_seconds": 0}},
])
def test_invalid_config(tmp_path, value):
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):
        load_config(path)


@pytest.mark.parametrize("orientation,direction,positive", [
    ("vertical", "left", False), ("vertical", "right", True),
    ("horizontal", "up", False), ("horizontal", "down", True),
])
def test_semantic_directions_round_trip_through_yaml(tmp_path, orientation, direction, positive):
    path = tmp_path / "calibration.yaml"
    values = dict(orientation=orientation, enter_direction=direction,
                  position=0.4, band_half_width=0.03,
                  min_track_frames=4, max_missing_frames=1)
    path.write_text(yaml.safe_dump({"counting": values}), encoding="utf-8")
    counting = load_config(path).counting
    assert counting == counting_from_dict(values)
    assert counting.entry_direction == direction
    assert counting.entry_positive is positive
    assert counting.position == 0.4
    assert counting.band_half_width == 0.03
    assert counting.min_track_frames == 4
    assert counting.max_missing_frames == 1


@pytest.mark.parametrize("orientation,legacy,semantic", [
    ("vertical", "negative", "left"), ("vertical", "positive", "right"),
    ("horizontal", "negative", "up"), ("horizontal", "positive", "down"),
])
def test_legacy_direction_remains_compatible(orientation, legacy, semantic):
    counting = counting_from_dict(dict(orientation=orientation, enter_direction=legacy))
    assert counting.enter_direction == legacy
    assert counting.entry_direction == semantic
    assert counting.entry_positive is (semantic in {"right", "down"})


@pytest.mark.parametrize("values", [
    {"orientation": "diagonal"},
    {"orientation": "vertical", "enter_direction": "up"},
    {"orientation": "vertical", "enter_direction": "down"},
    {"orientation": "horizontal", "enter_direction": "left"},
    {"orientation": "horizontal", "enter_direction": "right"},
    {"enter_direction": "unknown"}, {"enter_direction": True},
    {"band_half_width": 0}, {"band_half_width": -0.01},
    {"position": 0.03, "band_half_width": 0.04},
    {"position": 0.98, "band_half_width": 0.03},
    {"position": float("nan")}, {"band_half_width": float("inf")},
    {"min_track_frames": 1}, {"min_track_frames": 2.5},
    {"max_missing_frames": -1}, {"max_missing_frames": True},
    {"unused": 1},
])
def test_counting_validation_is_shared_by_yaml_and_live_calibration(tmp_path, values):
    with pytest.raises(ValueError):
        counting_from_dict(values)
    path = tmp_path / "invalid-counting.yaml"
    path.write_text(yaml.safe_dump({"counting": values}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_direct_counting_dataclass_validation():
    with pytest.raises(ValueError, match="Dirección"):
        validate_counting(CountingConfig(orientation="vertical", enter_direction="up"))


@pytest.mark.parametrize("source", [
    {"type": "file", "path": "data/another-video.mp4"},
    {"type": "webcam", "index": 1},
    {"type": "stream", "url": "http://127.0.0.1:8080/video"},
    {"type": "stream", "url": "rtsp://127.0.0.1/live"},
])
def test_normalized_calibration_does_not_depend_on_source(tmp_path, source):
    counting = dict(orientation="vertical", enter_direction="left",
                    position=0.4, band_half_width=0.02)
    path = tmp_path / "live-demo.yaml"
    path.write_text(yaml.safe_dump({"source": source, "counting": counting}), encoding="utf-8")
    assert load_config(path).counting == counting_from_dict(counting)


def test_counting_debug_requires_explicit_boolean(tmp_path):
    path = tmp_path / "debug.yaml"
    path.write_text("debug:\n  counting: true\n", encoding="utf-8")
    assert load_config(path).debug.counting is True
    path.write_text('debug:\n  counting: "false"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
