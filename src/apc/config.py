"""Configuración validada sin inicializar cámaras ni modelos."""

from dataclasses import dataclass, fields
from math import isfinite
from pathlib import Path
from typing import get_type_hints

import yaml


@dataclass(frozen=True)
class SourceConfig:
    type: str = "file"
    path: str = "data/demo.avi"
    index: int = 0
    url: str = ""
    width: int = 640
    height: int = 480
    queue_size: int = 2
    open_timeout_ms: int = 5000
    read_timeout_ms: int = 2000


@dataclass(frozen=True)
class DetectionConfig:
    model: str = "models/yolov8n.pt"
    imgsz: int = 320
    conf: float = 0.35
    vid_stride: int = 1
    min_area_ratio: float = 0.005
    max_area_ratio: float = 0.85


@dataclass(frozen=True)
class CountingConfig:
    orientation: str = "horizontal"
    position: float = 0.5
    band_half_width: float = 0.04
    enter_direction: str = "positive"
    min_track_frames: int = 3
    max_missing_frames: int = 2


@dataclass(frozen=True)
class OccupancyConfig:
    capacity: int = 100
    initial: int = 0
    green_below: float = 0.4
    red_above: float = 0.75


@dataclass(frozen=True)
class TelemetryConfig:
    port: int = 8765
    wagon_id: int = 1
    interval_seconds: float = 0.5
    stale_after_seconds: float = 3.0
    simulated_wagons: int = 4


@dataclass(frozen=True)
class DebugConfig:
    show_video: bool = False


@dataclass(frozen=True)
class Config:
    source: SourceConfig
    detection: DetectionConfig
    counting: CountingConfig
    occupancy: OccupancyConfig
    telemetry: TelemetryConfig
    debug: DebugConfig
    root: Path

    def resolve(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.root / path


def _section(cls, values):
    if not isinstance(values, dict):
        raise ValueError(f"{cls.__name__}: se esperaba un mapa YAML")
    hints = get_type_hints(cls)
    if set(values) - hints.keys():
        raise ValueError(f"{cls.__name__}: opciones desconocidas")
    result = cls(**values)
    for field in fields(cls):
        value, expected = getattr(result, field.name), hints[field.name]
        valid = type(value) is expected
        if expected is float:
            valid = type(value) in (int, float) and isfinite(value)
        if not valid:
            raise ValueError(f"{cls.__name__}.{field.name}: tipo o valor inválido")
    return result


def load_config(path: str | Path = "configs/default.yaml") -> Config:
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("La configuración debe ser un mapa YAML")
    classes = dict(source=SourceConfig, detection=DetectionConfig,
                   counting=CountingConfig, occupancy=OccupancyConfig,
                   telemetry=TelemetryConfig, debug=DebugConfig)
    if set(raw) - classes.keys():
        raise ValueError("Secciones desconocidas en la configuración")
    config = Config(**{key: _section(cls, raw.get(key, {}))
                       for key, cls in classes.items()}, root=path.parent.parent)
    s, d, c, o, t = (config.source, config.detection, config.counting,
                      config.occupancy, config.telemetry)
    checks = [
        (s.type in {"file", "webcam", "stream"}, "source.type inválido"),
        (s.index >= 0 and min(s.width, s.height, s.queue_size,
                            s.open_timeout_ms, s.read_timeout_ms) > 0, "Captura inválida"),
        (320 <= d.imgsz <= 416 and d.imgsz % 32 == 0, "imgsz: múltiplo de 32 entre 320 y 416"),
        (0 < d.conf <= 1 and d.vid_stride >= 1, "conf o vid_stride inválido"),
        (0 <= d.min_area_ratio < d.max_area_ratio <= 1, "Áreas inválidas"),
        (c.orientation in {"horizontal", "vertical"}, "Orientación inválida"),
        (c.enter_direction in {"positive", "negative"}, "Dirección inválida"),
        (0 < c.band_half_width < min(c.position, 1 - c.position), "Banda fuera de la imagen"),
        (c.min_track_frames >= 2 and c.max_missing_frames >= 0, "Vida de tracks inválida"),
        (o.capacity > 0 and o.initial >= 0, "Capacidad u ocupación inválida"),
        (0 <= o.green_below < o.red_above <= 1, "Umbrales inválidos"),
        (1 <= t.port <= 65535 and t.wagon_id > 0 and t.simulated_wagons > 0, "Telemetría inválida"),
        (0 < t.interval_seconds < t.stale_after_seconds, "Intervalos inválidos"),
    ]
    for valid, message in checks:
        if not valid:
            raise ValueError(message)
    return config
