from dataclasses import replace

import pytest

from apc.config import CountingConfig
from apc.counting.tripwire import TripwireCounter
from apc.models import Track


def follow(positions, **overrides):
    config = replace(CountingConfig(), **overrides)
    counter = TripwireCounter(config)
    events = []
    for position in positions:
        centroid = (0.5, position) if config.orientation == "horizontal" else (position, 0.5)
        tracks = [] if position is None else [Track(1, centroid)]
        events.extend(counter.update(tracks))
    return [event.direction for event in events]


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
@pytest.mark.parametrize("positions,expected", [
    ([0.3, 0.4, 0.5, 0.7, 0.8, 0.8], ["entry"]),
    ([0.8, 0.7, 0.5, 0.3], ["exit"]),
    ([0.3, 0.4, 0.7, 0.7, 0.5, 0.3, 0.3, 0.7], ["entry", "exit", "entry"]),
    ([0.3, 0.49, 0.51, 0.48, 0.52, 0.5, 0.3], []),
    ([0.5, 0.49, 0.51, 0.7], []),
    ([0.3, 0.7], []),
    ([0.3, 0.7, 0.7], ["entry"]),
    ([0.3, 0.4, None, None, 0.7], ["entry"]),
    ([0.3, 0.4, None, None, None, 0.7, 0.8, 0.8], []),
])
def test_paths(orientation, positions, expected):
    assert follow(positions, orientation=orientation) == expected


def test_reverse_entry_direction():
    assert follow([0.3, 0.4, 0.7], enter_direction="negative") == ["exit"]


def test_one_missing_observation_and_no_duplicate_after_return():
    assert follow([0.3, 0.4, None, 0.7, None, 0.7, 0.8]) == ["entry"]


def test_two_people_cross_opposite_directions():
    counter = TripwireCounter(CountingConfig())
    events = []
    for left, right in [(0.3, 0.7), (0.4, 0.6), (0.7, 0.3)]:
        events.extend(counter.update([Track(1, (0.2, left)), Track(2, (0.8, right))]))
    assert [(e.track_id, e.direction) for e in events] == [(1, "entry"), (2, "exit")]


def test_changed_id_cannot_be_linked_safely():
    counter = TripwireCounter(CountingConfig())
    for _ in range(3):
        assert counter.update([Track(1, (0.5, 0.3))]) == []
    for _ in range(3):
        assert counter.update([Track(2, (0.5, 0.7))]) == []


def test_reset_and_invalid_observation():
    counter = TripwireCounter(CountingConfig())
    track = Track(1, (0.5, 0.3))
    with pytest.raises(ValueError):
        counter.update([track, track])
    with pytest.raises(ValueError):
        counter.update([Track(2, (float("nan"), 0.3))])
    counter.update([track])
    counter.update([track])
    counter.reset()
    assert counter.update([Track(1, (0.5, 0.7))]) == []


@pytest.mark.parametrize("orientation,direction,start,end", [
    ("vertical", "left", 0.8, 0.2),
    ("vertical", "right", 0.2, 0.8),
    ("horizontal", "up", 0.8, 0.2),
    ("horizontal", "down", 0.2, 0.8),
])
def test_explicit_entry_direction_and_return(orientation, direction, start, end):
    # La banda y la permanencia no duplican un cruce; la vuelta sí es otro cruce.
    assert follow(
        [start, start, 0.5, end, end, 0.5, end, end, 0.5, start, start],
        orientation=orientation, enter_direction=direction,
    ) == ["entry", "exit"]


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_band_boundaries_belong_to_band(orientation):
    # Valores binarios exactos para aislar la inclusión geométrica del redondeo.
    assert follow(
        [0.2, 0.375, 0.5, 0.625, 0.375, 0.2],
        orientation=orientation, band_half_width=0.125,
    ) == []
    assert follow(
        [0.2, 0.375, 0.625, 0.626, 0.625, 0.626],
        orientation=orientation, band_half_width=0.125,
    ) == ["entry"]


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_decimal_band_boundaries_do_not_create_rounding_crossing(orientation):
    assert follow(
        [0.2, 0.46, 0.5, 0.54, 0.46, 0.2],
        orientation=orientation, position=0.5, band_half_width=0.04,
    ) == []
    assert follow(
        [0.8, 0.54, 0.5, 0.46, 0.54, 0.8],
        orientation=orientation, position=0.5, band_half_width=0.04,
    ) == []


@pytest.mark.parametrize("orientation", ["vertical", "horizontal"])
def test_motion_parallel_to_line_is_not_a_crossing(orientation):
    counter = TripwireCounter(CountingConfig(orientation=orientation))
    for moving_axis in [0.2, 0.5, 0.8, 0.2]:
        point = (0.2, moving_axis) if orientation == "vertical" else (moving_axis, 0.2)
        assert counter.update([Track(4, point)]) == []


def test_track_age_counts_observations_not_missing_frames():
    # Dos ausencias toleradas conservan el lado, pero no maduran un track joven.
    assert follow([0.2, None, None, 0.8], min_track_frames=3) == []
    assert follow([0.2, None, None, 0.8, 0.8], min_track_frames=3) == ["entry"]


@pytest.mark.parametrize("missing,expected", [(2, ["entry"]), (3, [])])
def test_exact_missing_tolerance_with_minimum_age(missing, expected):
    assert follow(
        [0.2, 0.2] + [None] * missing + [0.8, 0.8, 0.8],
        min_track_frames=2, max_missing_frames=2,
    ) == expected


def test_new_id_does_not_inherit_another_tracks_age_or_side():
    counter = TripwireCounter(CountingConfig(orientation="vertical", enter_direction="left"))
    for _ in range(3):
        assert counter.update([Track(10, (0.8, 0.5))]) == []
    events = counter.update([Track(10, (0.2, 0.5)), Track(20, (0.8, 0.5))])
    assert [(event.track_id, event.direction) for event in events] == [(10, "entry")]
    assert counter.update([Track(10, (0.2, 0.5)), Track(20, (0.2, 0.5))]) == []
    events = counter.update([Track(10, (0.2, 0.5)), Track(20, (0.2, 0.5))])
    assert [(event.track_id, event.direction) for event in events] == [(20, "entry")]


@pytest.mark.parametrize("point", [(-0.01, 0.5), (0.5, 1.01), (float("inf"), 0.5)])
def test_counter_rejects_non_normalized_points(point):
    with pytest.raises(ValueError, match="normalizado"):
        TripwireCounter(CountingConfig()).update([Track(1, point)])


@pytest.mark.parametrize('orientation', ['horizontal', 'vertical'])
def test_short_gap_crossing_then_disappearance_does_not_duplicate(orientation):
    assert follow([.2, .3] + [None] * 5 + [.8] + [None] * 5 + [.8, .8],
                  orientation=orientation, max_missing_frames=5) == ['entry']
    assert follow([.2, .3] + [None] * 6 + [.8, .8, .8],
                  orientation=orientation, max_missing_frames=5) == []


def test_extended_gap_still_rejects_approach_and_return_and_band_jitter():
    assert follow([.2, .3, .59] + [None] * 5 + [.6, .56, .64, .62, .3],
                  position=.6, band_half_width=.04, max_missing_frames=5) == []
