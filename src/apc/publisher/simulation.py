"""Datos de prueba reproducibles para varios vagones, sin cámara."""

from dataclasses import replace

from apc.config import Config
from apc.counting.occupancy import OccupancyCounter
from apc.publisher.telemetry import make_sample


def simulation_samples(config: Config, step: int, timestamp: float):
    levels = (0.20, 0.60, 0.90, 0.35)
    samples = []
    for index in range(config.telemetry.simulated_wagons):
        initial = round(config.occupancy.capacity * levels[index % len(levels)])
        counter = OccupancyCounter(replace(config.occupancy, initial=initial))
        counter.entries = step * (index + 1) // 3
        counter.exits = step * index // 4
        samples.append(make_sample(index + 1, counter, 0.0, timestamp=timestamp, simulated=True))
    return samples
