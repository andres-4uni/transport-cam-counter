"""Acumuladores y semáforo; la calibración inicia un nuevo período de conteo."""

from apc.config import OccupancyConfig
from apc.counting.tripwire import CrossingEvent


class OccupancyCounter:
    def __init__(self, config: OccupancyConfig):
        if config.capacity <= 0 or not 0 <= config.green_below < config.red_above <= 1:
            raise ValueError("Capacidad o umbrales inválidos")
        self.config = config
        self.calibrate(config.initial)

    def calibrate(self, occupancy: int) -> None:
        if type(occupancy) is not int or occupancy < 0:
            raise ValueError("La ocupación inicial debe ser un entero no negativo")
        self.initial = occupancy
        self.entries = 0
        self.exits = 0

    def reset(self) -> None:
        self.calibrate(0)

    def apply(self, events: list[CrossingEvent]) -> None:
        if any(event.direction not in {"entry", "exit"} for event in events):
            raise ValueError("Dirección de evento inválida")
        self.entries += sum(event.direction == "entry" for event in events)
        self.exits += sum(event.direction == "exit" for event in events)

    @property
    def occupancy(self) -> int:
        return max(0, self.initial + self.entries - self.exits)

    @property
    def ratio(self) -> float:
        return self.occupancy / self.config.capacity

    @property
    def color(self) -> str:
        if self.ratio < self.config.green_below:
            return "green"
        if self.ratio > self.config.red_above:
            return "red"
        return "yellow"
