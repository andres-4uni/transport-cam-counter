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
