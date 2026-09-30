"""Máquina de estados por ID, con banda de histéresis y caducidad."""

from dataclasses import dataclass
from math import isfinite

from apc.config import CountingConfig
from apc.models import Track


@dataclass(frozen=True)
class CrossingEvent:
    track_id: int
    direction: str
    frame_index: int


@dataclass
class _TrackState:
    last_seen: int
    observations: int = 0
    stable_side: int = 0


class TripwireCounter:
    def __init__(self, config: CountingConfig):
        if config.orientation not in {"horizontal", "vertical"}:
            raise ValueError("Orientación inválida")
        if config.enter_direction not in {"positive", "negative"}:
            raise ValueError("Dirección inválida")
        if not 0 < config.band_half_width < min(config.position, 1 - config.position):
            raise ValueError("Banda inválida")
        if config.min_track_frames < 2 or config.max_missing_frames < 0:
            raise ValueError("Vida de tracks inválida")
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._states: dict[int, _TrackState] = {}
        self._frame_index = -1

    def update(self, tracks: list[Track]) -> list[CrossingEvent]:
        """Una llamada por frame procesado, incluso si no hay detecciones.

        Un cruce se confirma al alcanzar el lado opuesto fuera de la banda.
        No exige una detección dentro de ella: tolera saltos y frames perdidos.
        """
        seen = set()
        for track in tracks:
            if track.track_id in seen:
                raise ValueError("ID duplicado en una misma observación")
            if not all(isfinite(value) and 0 <= value <= 1 for value in track.centroid):
                raise ValueError("Centroide debe estar normalizado y ser finito")
            seen.add(track.track_id)
        self._frame_index += 1
        frame_index = self._frame_index
        # Al reaparecer, la distancia temporal incluye el frame actual.
        self._states = {key: state for key, state in self._states.items()
                        if frame_index - state.last_seen <= self.config.max_missing_frames + 1}
        events = []
        axis = 1 if self.config.orientation == "horizontal" else 0
        for track in tracks:
            state = self._states.setdefault(track.track_id, _TrackState(frame_index))
            state.last_seen = frame_index
            state.observations += 1
            distance = track.centroid[axis] - self.config.position
            side = (1 if distance > self.config.band_half_width else
                    -1 if distance < -self.config.band_half_width else 0)
            if side == 0:
                continue
            if state.stable_side == 0:
                state.stable_side = side
            elif side != state.stable_side and state.observations >= self.config.min_track_frames:
                positive = side > state.stable_side
                entering = positive == (self.config.enter_direction == "positive")
                events.append(CrossingEvent(track.track_id, "entry" if entering else "exit", frame_index))
                # Solo otro cruce completo puede rearmar un evento para este ID.
                state.stable_side = side
        return events
