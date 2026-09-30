import pytest

from apc.config import OccupancyConfig
from apc.counting.occupancy import OccupancyCounter
from apc.counting.tripwire import CrossingEvent


@pytest.mark.parametrize("value,color", [(0, "green"), (39, "green"), (40, "yellow"),
                                        (75, "yellow"), (76, "red"), (120, "red")])
def test_thresholds(value, color):
    counter = OccupancyCounter(OccupancyConfig(initial=value))
    assert counter.occupancy == value
    assert counter.color == color


def test_clamp_calibration_and_reset():
    counter = OccupancyCounter(OccupancyConfig())
    counter.apply([CrossingEvent(1, "exit", 0)])
    assert counter.occupancy == 0
    counter.calibrate(20)
    assert (counter.entries, counter.exits, counter.occupancy) == (0, 0, 20)
    counter.apply([CrossingEvent(2, "entry", 1), CrossingEvent(3, "entry", 1),
                   CrossingEvent(4, "exit", 2)])
    assert counter.occupancy == 21
    counter.reset()
    assert (counter.entries, counter.exits, counter.occupancy) == (0, 0, 0)
    with pytest.raises(ValueError):
        counter.calibrate(-1)
