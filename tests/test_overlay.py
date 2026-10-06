from dataclasses import replace

import cv2
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


@pytest.mark.parametrize('orientation', ['horizontal', 'vertical'])
def test_dual_zones_tint_exteriors_keep_neutral_and_use_actual_anchor(orientation):
    config = VisualizationConfig(show_line=False, show_counters=False,
                                 show_boxes=True, show_ids=False)
    counting = CountingConfig(mode='dual_zone', max_missing_seconds=.9, orientation=orientation)
    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    image = draw_overlay(frame, [Track(7, (.8, .8))], counting, config,
                         entries=0, exits=0, occupancy=0)
    a, neutral, b = ((120, 10), (300, 10), (500, 10)) if orientation == 'horizontal' else (
        (590, 100), (590, 400), (590, 700))
    assert tuple(image[a]) == (0, 0, 36)
    assert tuple(image[neutral]) == (0, 0, 0)
    assert tuple(image[b]) == (0, 36, 0)
    assert tuple(image[round(.8*599), round(.8*799)]) == (255, 255, 255)
    assert not frame.any()


@pytest.mark.parametrize("orientation,direction", [
    ("vertical", "left"), ("vertical", "right"),
    ("horizontal", "up"), ("horizontal", "down"),
])
@pytest.mark.parametrize("shape", [(480, 640), (1920, 1080)])
def test_legend_arrows_follow_explicit_entry_direction(monkeypatch, orientation, direction, shape):
    arrows = []
    labels = []
    original_arrow, original_text = cv2.arrowedLine, cv2.putText

    def arrow(image, start, end, color, *args, **kwargs):
        if color in {(0, 255, 0), (0, 0, 255)}:
            arrows.append((start, end, color))
        return original_arrow(image, start, end, color, *args, **kwargs)

    def text(image, value, origin, *args, **kwargs):
        labels.append((value, origin))
        return original_text(image, value, origin, *args, **kwargs)

    monkeypatch.setattr(cv2, "arrowedLine", arrow)
    monkeypatch.setattr(cv2, "putText", text)
    image = np.zeros((*shape, 3), dtype=np.uint8)
    draw_overlay(image, [], CountingConfig(orientation=orientation, enter_direction=direction),
                 VisualizationConfig(), entries=0, exits=0, occupancy=0)
    assert len(arrows) == 2
    axis = 0 if orientation == "vertical" else 1
    entry_sign = 1 if direction in {"right", "down"} else -1
    for start, end, color in arrows:
        movement = end[axis] - start[axis]
        assert movement * (entry_sign if color == (0, 255, 0) else -entry_sign) > 0
        assert start[1 - axis] == end[1 - axis]
        assert min(start[1], end[1]) > 78  # No tapa el panel de contadores.
    assert any(value == "LINEA DE CONTEO" for value, _ in labels)
    assert any(value.startswith("BANDA +/-") for value, _ in labels)
    assert any(value == "PUNTO = CENTROIDE" for value, _ in labels)


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("shape", [(240, 320), (480, 640), (1920, 1080)])
def test_band_is_dashed_and_uses_normalized_coordinates(orientation, shape):
    counting = CountingConfig(orientation=orientation, position=0.6, band_half_width=0.1)
    config = VisualizationConfig(show_line=False, show_boxes=False, show_ids=False,
                                 show_counters=False)
    image = draw_overlay(np.zeros((*shape, 3), dtype=np.uint8), [], counting, config,
                         entries=0, exits=0, occupancy=0)
    height, width = shape
    for position in (0.5, 0.7):
        axis_length = width if orientation == "vertical" else height
        coordinate = round(position * (axis_length - 1))
        pixels = image[:, coordinate] if orientation == "vertical" else image[coordinate, :]
        assert np.any(np.all(pixels == (139, 116, 100), axis=1))
        assert np.any(np.all(pixels == (0, 0, 0), axis=1))


def test_counting_point_is_actual_centroid_and_not_bottom_of_box():
    config = VisualizationConfig(show_line=False, show_band=False, show_counters=False)
    frame, image = render(config)
    centroid = (round(0.3 * (frame.shape[0] - 1)), round(0.25 * (frame.shape[1] - 1)))
    assert tuple(image[centroid]) == (255, 255, 255)
    bottom = (round(0.4 * (frame.shape[0] - 1)), centroid[1])
    assert tuple(image[bottom]) != (255, 255, 255)
