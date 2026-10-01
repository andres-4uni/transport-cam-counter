"""Flujos cíclicos reproducibles, acotados y sin cámara."""

from dataclasses import replace

from apc.config import Config
from apc.counting.occupancy import OccupancyCounter
from apc.publisher.telemetry import make_sample


def simulation_samples(config: Config, step: int, timestamp: float):
    """Genera cualquier paso sin recorrer ni almacenar toda la historia.

    Los tres primeros perfiles oscilan alrededor de ocupaciones baja, media y
    alta. El cuarto recorre todo el rango. Cada cambio de ocupación representa
    entradas o salidas enteras; los acumuladores siguen creciendo entre ciclos.
    """
    if type(step) is not int or step < 0:
        raise ValueError("El paso de simulación debe ser un entero no negativo")
    simulation = config.simulation
    capacity = config.occupancy.capacity
    limit = int(capacity * simulation.maximum_ratio)
    profiles = []
    for target in (simulation.low_target_ratio, simulation.medium_target_ratio,
                   simulation.high_target_ratio):
        minimum = max(0, round(capacity * (target - simulation.variation_ratio)))
        maximum = min(limit, round(capacity * (target + simulation.variation_ratio)))
        initial = min(maximum, max(minimum, round(capacity * target)))
        profiles.append((minimum, maximum, initial))
    profiles.append((0, limit, min(limit, round(capacity * simulation.variable_initial_ratio))))
    samples = []
    for index in range(config.telemetry.simulated_wagons):
        minimum, maximum, initial = profiles[index % len(profiles)]
        counter = OccupancyCounter(replace(config.occupancy, initial=initial))
        span = maximum - minimum
        if span > 0:
            # Onda triangular: subir y bajar requiere 2 * span movimientos.
            # El intervalo de publicación convierte pasos en tiempo simulado.
            movement = int(step * config.telemetry.interval_seconds * 2 * span
                           / simulation.period_seconds)
            offset = initial - minimum
            cycles, phase = divmod(offset + movement, 2 * span)
            counter.entries = cycles * span + min(phase, span) - offset
            counter.exits = cycles * span + max(phase - span, 0)
        # Si el redondeo deja un rango de cero personas, ambos conteos quedan en cero.
        samples.append(make_sample(index + 1, counter, 0.0, timestamp=timestamp, simulated=True))
    return samples
