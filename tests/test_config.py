from pathlib import Path

import pytest
import yaml

from apc.config import load_config


def test_defaults():
    config = load_config()
    assert not config.debug.show_video
    assert config.detection.imgsz == 320
    assert config.resolve("data/demo.avi") == Path.cwd() / "data/demo.avi"


@pytest.mark.parametrize("value", [
    {"detection": {"imgsz": 319}}, {"detection": {"conf": 0}},
    {"detection": {"vid_stride": 0}}, {"debug": {"show_video": "false"}},
    {"source": {"typo": 1}}, {"occupancy": {"capacity": 0}},
    {"counting": {"position": 1}}, {"occupancy": {"red_above": 0.2}},
    {"telemetry": {"interval_seconds": float("nan")}}, {"wrong": {}},
])
def test_invalid_config(tmp_path, value):
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):
        load_config(path)
