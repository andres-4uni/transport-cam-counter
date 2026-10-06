"""Configuración validada sin inicializar cámaras ni modelos."""

from dataclasses import dataclass, fields, replace
from math import isfinite
from pathlib import Path
from re import fullmatch
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
    realtime: bool = False
    loop: bool = False


@dataclass(frozen=True)
class DetectionConfig:
    model: str = "models/yolov8n.pt"
    tracker: str = "bytetrack.yaml"
    imgsz: int = 320
    conf: float = 0.35
    vid_stride: int = 1
    torch_threads: int = 0  # 0 conserva la selección automática de Ultralytics.
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

    @property
    def entry_direction(self) -> str:
        """Sentido físico; positive/negative se aceptan por compatibilidad."""
        if self.enter_direction in {"positive", "negative"}:
            negative, positive = (("up", "down") if self.orientation == "horizontal"
                                  else ("left", "right"))
            return positive if self.enter_direction == "positive" else negative
        return self.enter_direction

    @property
    def entry_positive(self) -> bool:
        return self.entry_direction in {"right", "down"}


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
class SimulationConfig:
    period_seconds: float = 120.0
    maximum_ratio: float = 1.10
    low_target_ratio: float = 0.20
    medium_target_ratio: float = 0.60
    high_target_ratio: float = 0.90
    variation_ratio: float = 0.10
    variable_initial_ratio: float = 0.35
    fake_fps: float = 15.0
    fake_cycle_seconds: float = 8.0


@dataclass(frozen=True)
class VisualizationConfig:
    stream: bool = False
    show_line: bool = True
    show_band: bool = True
    show_boxes: bool = True
    show_ids: bool = True
    show_trails: bool = False
    show_counters: bool = True
    trail_length: int = 20
    line_color: str = "#0000FF"
    band_color: str = "#64748B"
    box_color: str = "#00DFFF"
    trail_color: str = "#FFD166"
    in_color: str = "#00FF00"
    out_color: str = "#FF0000"
    occupancy_color: str = "#FFFFFF"
    jpeg_quality: int = 80
    max_fps: float = 10.0


@dataclass(frozen=True)
class DebugConfig:
    show_video: bool = False
    counting: bool = False


@dataclass(frozen=True)
class Config:
    source: SourceConfig
    detection: DetectionConfig
    counting: CountingConfig
    occupancy: OccupancyConfig
    telemetry: TelemetryConfig
    simulation: SimulationConfig
    visualization: VisualizationConfig
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


def validate_counting(config: CountingConfig) -> None:
    """Validación compartida por YAML, contador, CLI y calibración en vivo."""
    from dataclasses import asdict
    _section(CountingConfig, asdict(config))
    if config.orientation not in {"horizontal", "vertical"}:
        raise ValueError("Orientación inválida")
    directions = {"left", "right"} if config.orientation == "vertical" else {"up", "down"}
    if config.entry_direction not in directions:
        raise ValueError("Dirección de entrada incompatible con la orientación")
    if not 0 < config.band_half_width < min(config.position, 1 - config.position):
        raise ValueError("Banda fuera de la imagen")
    if config.min_track_frames < 2 or config.max_missing_frames < 0:
        raise ValueError("Vida de tracks inválida")


def counting_from_dict(values: dict) -> CountingConfig:
    config = _section(CountingConfig, values)
    validate_counting(config)
    return config


def load_config(path: str | Path = "configs/default.yaml") -> Config:
    path = Path(path).resolve()
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("La configuración debe ser un mapa YAML")
    classes = dict(source=SourceConfig, detection=DetectionConfig,
                   counting=CountingConfig, occupancy=OccupancyConfig,
                   telemetry=TelemetryConfig, simulation=SimulationConfig,
                   visualization=VisualizationConfig, debug=DebugConfig)
    if set(raw) - classes.keys():
        raise ValueError("Secciones desconocidas en la configuración")
    config = Config(**{key: _section(cls, raw.get(key, {}))
                       for key, cls in classes.items()}, root=path.parent.parent)
    s, d, c, o, t = (config.source, config.detection, config.counting,
                      config.occupancy, config.telemetry)
    simulation = config.simulation
    visualization = config.visualization
    validate_counting(c)
    checks = [
        (s.type in {"file", "webcam", "stream"}, "source.type inválido"),
        (s.index >= 0 and min(s.width, s.height, s.queue_size,
                            s.open_timeout_ms, s.read_timeout_ms) > 0, "Captura inválida"),
        (320 <= d.imgsz <= 416 and d.imgsz % 32 == 0, "imgsz: múltiplo de 32 entre 320 y 416"),
        (0 < d.conf <= 1 and d.vid_stride >= 1, "conf o vid_stride inválido"),
        (d.torch_threads >= 0, "torch_threads debe ser 0 (auto) o positivo"),
        (0 <= d.min_area_ratio < d.max_area_ratio <= 1, "Áreas inválidas"),
        (o.capacity > 0 and o.initial >= 0, "Capacidad u ocupación inválida"),
        (0 <= o.green_below < o.red_above <= 1, "Umbrales inválidos"),
        (1 <= t.port <= 65535 and t.wagon_id > 0 and t.simulated_wagons > 0, "Telemetría inválida"),
        (0 < t.interval_seconds < t.stale_after_seconds, "Intervalos inválidos"),
        (simulation.period_seconds >= 4 * t.interval_seconds, "Período de simulación demasiado corto"),
        (0 < simulation.maximum_ratio <= 1.10, "Máximo simulado debe estar entre 0 y 110%"),
        (0 <= simulation.low_target_ratio < simulation.medium_target_ratio
         < simulation.high_target_ratio <= simulation.maximum_ratio, "Objetivos de simulación inválidos"),
        (0 < simulation.variation_ratio <= min(simulation.low_target_ratio,
                                               simulation.maximum_ratio - simulation.high_target_ratio),
         "Variación simulada fuera de los límites"),
        (0 <= simulation.variable_initial_ratio <= simulation.maximum_ratio,
         "Ocupación inicial del vagón variable inválida"),
        (0 < simulation.fake_fps <= 60 and
         simulation.fake_cycle_seconds * simulation.fake_fps >= 4 * c.min_track_frames,
         "Cadencia o ciclo de tracks simulados inválido"),
        (1 <= visualization.jpeg_quality <= 100 and 0 < visualization.max_fps <= 60,
         "Calidad JPEG o FPS del stream inválidos"),
        (1 <= visualization.trail_length <= 300, "Longitud de estela inválida"),
        (all(fullmatch(r"#[0-9a-fA-F]{6}", getattr(visualization, field.name))
             for field in fields(VisualizationConfig) if field.name.endswith("_color")),
         "Colores de visualization deben usar #RRGGBB"),
    ]
    for valid, message in checks:
        if not valid:
            raise ValueError(message)
    if d.tracker != "bytetrack.yaml":
        tracker_path = config.resolve(d.tracker)
        if not tracker_path.is_file():
            raise ValueError("No existe el perfil de ByteTrack configurado")
        with tracker_path.open(encoding="utf-8") as handle:
            tracker = yaml.safe_load(handle)
        if not isinstance(tracker, dict) or tracker.get("tracker_type") != "bytetrack":
            raise ValueError("El perfil de tracking debe usar ByteTrack")
        config = replace(config, detection=replace(d, tracker=str(tracker_path)))
    return config
