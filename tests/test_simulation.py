"""Regresiones de simulación prolongada, saldo y diversidad de ocupaciones."""

from dataclasses import replace
from math import ceil

import pytest

from apc.config import load_config
from apc.publisher.simulation import simulation_samples


@pytest.mark.parametrize("capacity", [1, 37, 100, 317])
def test_simulation_remains_bounded_and_conserves_passengers_for_many_steps(capacity):
    config = load_config()
    config = replace(config, occupancy=replace(config.occupancy, capacity=capacity))
    previous = simulation_samples(config, 0, 0)
    max_change = ceil(2 * int(capacity * config.simulation.maximum_ratio)
                      * config.telemetry.interval_seconds / config.simulation.period_seconds)
    for step in range(1, 10_001):
        current = simulation_samples(config, step, step * config.telemetry.interval_seconds)
        for before, after in zip(previous, current):
            assert 0 <= after.occupancy <= capacity * 1.10
            assert after.initial_occupancy == before.initial_occupancy
            assert after.occupancy == after.initial_occupancy + after.entries - after.exits
            assert after.entries >= before.entries
            assert after.exits >= before.exits
            assert after.occupancy - before.occupancy == (
                after.entries - before.entries - (after.exits - before.exits)
            )
            assert abs(after.occupancy - before.occupancy) <= max_change
        previous = current


def test_profiles_oscillate_and_keep_all_three_colors_available():
    config = load_config()
    occupancies = [set() for _ in range(4)]
    variable_levels = set()
    previous = simulation_samples(config, 0, 0)
    increasing, decreasing = set(), set()
    for step in range(481):
        samples = simulation_samples(config, step, step * config.telemetry.interval_seconds)
        assert [sample.level for sample in samples[:3]] == [0, 1, 2]
        for index, (before, sample) in enumerate(zip(previous, samples)):
            occupancies[index].add(sample.occupancy)
            if sample.occupancy > before.occupancy:
                increasing.add(index)
            if sample.occupancy < before.occupancy:
                decreasing.add(index)
        variable_levels.add(samples[3].level)
        previous = samples
    assert [(min(values), max(values)) for values in occupancies] == [
        (10, 30), (50, 70), (80, 100), (0, 110),
    ]
    assert increasing == decreasing == set(range(4))
    assert variable_levels == {0, 1, 2}


def test_large_step_is_reproducible_without_resetting_totals():
    config = load_config()
    samples = simulation_samples(config, 10**9, 100)
    assert samples == simulation_samples(config, 10**9, 100)
    for sample in samples:
        assert 0 <= sample.occupancy <= 110
        assert sample.entries > 1000 and sample.exits > 1000
        assert sample.occupancy == sample.initial_occupancy + sample.entries - sample.exits


def test_cadence_changes_do_not_change_the_occupancy_for_same_elapsed_time():
    config = load_config()
    slower = replace(config, telemetry=replace(config.telemetry, interval_seconds=1.0))
    assert simulation_samples(config, 120, 100) == simulation_samples(slower, 60, 100)


@pytest.mark.parametrize("step", [-1, 0.5, True])
def test_invalid_step(step):
    with pytest.raises(ValueError):
        simulation_samples(load_config(), step, 100)
