"""Anotación en memoria para visualización exclusivamente local."""

from apc.config import CountingConfig, VisualizationConfig
from apc.models import Track
from apc.visualization.overlay import draw_overlay


def annotate(frame, tracks: list[Track], counting: CountingConfig, fps: float):
    return draw_overlay(frame, tracks, counting, VisualizationConfig(show_counters=False),
                        entries=0, exits=0, occupancy=0, fps=fps)
