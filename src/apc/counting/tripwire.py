"""Máquina de estados por ID, con banda de histéresis y caducidad."""

from dataclasses import dataclass
from math import isfinite
from collections.abc import Callable

from apc.config import CountingConfig, validate_counting
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
    point: tuple[float, float] | None = None


class TripwireCounter:
    def __init__(self, config: CountingConfig, *, diagnostic: Callable[[dict], None] | None = None):
        validate_counting(config)
        self.config = config
        self.diagnostic = diagnostic
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
        for key, state in list(self._states.items()):
            missing = frame_index - state.last_seen - int(key in seen)
            if missing > self.config.max_missing_frames:
                self._report(key, state, state.stable_side, "expired", "perdió el track", missing=missing)
                del self._states[key]
            elif key not in seen:
                self._report(key, state, state.stable_side, "missing", "ausencia tolerada", missing=missing)
        events = []
        axis = 1 if self.config.orientation == "horizontal" else 0
        for track in tracks:
            state = self._states.setdefault(track.track_id, _TrackState(frame_index))
            state.last_seen = frame_index
            state.observations += 1
            previous_point = state.point
            state.point = track.centroid
            previous = state.stable_side
            # Comparar los límites directamente evita que 0.54 - 0.5 > 0.04
            # por redondeo clasifique el propio borde como exterior.
            position = track.centroid[axis]
            side = (1 if position > self.config.position + self.config.band_half_width else
                    -1 if position < self.config.position - self.config.band_half_width else 0)
            if side == 0:
                reason = "sigue dentro de banda"
            elif state.stable_side == 0:
                state.stable_side = side
                reason = "primer lado estable; falta cruce"
            elif side != state.stable_side and state.observations >= self.config.min_track_frames:
                positive = side > state.stable_side
                entering = positive == self.config.entry_positive
                events.append(CrossingEvent(track.track_id, "entry" if entering else "exit", frame_index))
                # Solo otro cruce completo puede rearmar un evento para este ID.
                state.stable_side = side
                reason = "cruce completo"
            elif side != state.stable_side:
                reason = "track demasiado joven"
            else:
                reason = "no cambió de lado"
            event = events[-1].direction if events and events[-1].track_id == track.track_id else "none"
            delta = 0 if previous_point is None else track.centroid[axis] - previous_point[axis]
            direction = ("down" if axis else "right") if delta > 0 else (
                ("up" if axis else "left") if delta < 0 else "still")
            self._report(track.track_id, state, previous, side, reason, event=event, movement=direction)
        return events

    def _report(self, track_id, state, previous, side, reason, *, event="none", movement="unknown", missing=0):
        if self.diagnostic is not None:
            self.diagnostic(dict(frame=self._frame_index, track_id=track_id,
                                 age=state.observations, point=state.point, position=side,
                                 previous=previous, current=state.stable_side,
                                 movement=movement, event=event, reason=reason, missing=missing,
                                 orientation=self.config.orientation))
