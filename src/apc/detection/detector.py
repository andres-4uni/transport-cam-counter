"""YOLOv8n + ByteTrack en CPU, sin guardar imágenes."""

import os
from pathlib import Path

from apc.config import DetectionConfig
from apc.models import Track


class PersonDetector:
    def __init__(self, config: DetectionConfig, model_path: Path, *, model=None):
        self.config = config
        if model is None:
            if not model_path.is_file():
                raise FileNotFoundError(f"Descargue primero los pesos YOLOv8n en {model_path}")
            os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(".cache/ultralytics").resolve()))
            os.environ.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
            os.environ["YOLO_AUTOINSTALL"] = "false"
            Path(os.environ["YOLO_CONFIG_DIR"]).mkdir(parents=True, exist_ok=True)
            Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
            from ultralytics import YOLO, settings
            settings.update({"sync": False})
            model = YOLO(str(model_path))
        self.model = model

    def detect(self, frame) -> list[Track]:
        result = self.model.track(
            frame, persist=True, tracker="bytetrack.yaml", classes=[0],
            device="cpu", imgsz=self.config.imgsz, conf=self.config.conf,
            verbose=False, save=False, save_txt=False, save_crop=False,
            show=False, stream=False,
        )[0]
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return []
        height, width = frame.shape[:2]
        tracks = []
        for track_id, coords in zip(boxes.id.int().cpu().tolist(), boxes.xyxy.cpu().tolist()):
            x1, y1, x2, y2 = coords
            area = (x2 - x1) * (y2 - y1) / (width * height)
            if self.config.min_area_ratio <= area <= self.config.max_area_ratio:
                tracks.append(Track(int(track_id), ((x1 + x2) / (2 * width),
                                                    (y1 + y2) / (2 * height)),
                                    (x1 / width, y1 / height, x2 / width, y2 / height)))
        return tracks
