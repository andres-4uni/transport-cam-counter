from dataclasses import replace

import numpy as np
import pytest

from apc.config import CountingConfig, VisualizationConfig, load_config
from apc.models import Track
from apc.visualization.overlay import TrackTrails, draw_overlay


def render(config=VisualizationConfig(), counting=CountingConfig(), **kwargs):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    tracks = [Track(12, (0.25, 0.3), (0.2, 0.2, 0.3, 0.4))]
    return frame, draw_overlay(frame, tracks, counting, config, entries=7, exits=3, occupancy=4, **kwargs)


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_overlay_line_colors_counters_and_no_input_mutation(orientation):
    frame, image = render(counting=CountingConfig(orientation=orientation))
    assert np.count_nonzero(frame) == 0
    assert not np.shares_memory(frame, image)
    pixel = image[240, 10] if orientation == "horizontal" else image[450, 320]
    assert tuple(pixel) == (255, 0, 0)  # Línea azul en BGR.
    assert np.any(np.all(image[:78, :213] == (0, 255, 0), axis=2))
    assert np.any(np.all(image[:78, 213:426] == (0, 0, 255), axis=2))
    assert np.any(np.all(image[:78, 426:] == (255, 255, 255), axis=2))


def test_overlay_toggles_disable_every_annotation():
    config = VisualizationConfig(show_line=False, show_band=False, show_boxes=False,
                                 show_ids=False, show_trails=False, show_counters=False)
    frame, image = render(config)
    assert np.array_equal(frame, image)
    for toggle in ("show_line", "show_band", "show_boxes", "show_ids", "show_counters"):
        _, changed = render(replace(config, **{toggle: True}))
        assert np.any(changed != frame)


def test_trails_are_bounded_and_drawing_does_not_modify_history():
    history = TrackTrails(3)
    for index in range(10):
        paths = history.update([Track(12, (0.25, 0.2 + index * 0.01))])
    assert len(paths[12]) == 3
    before = dict(paths)
    _, enabled = render(VisualizationConfig(show_trails=True), trails=paths)
    _, disabled = render(trails=paths)
    assert np.any(enabled != disabled)
    assert paths == before
    assert history.update([]) == {}


def test_visualization_stream_is_off_by_default():
    assert not VisualizationConfig().stream
    assert not load_config().visualization.stream
