"""YOLOv8n + ByteTrack en CPU, sin guardar imágenes."""

import os
from pathlib import Path
from time import perf_counter
from math import ceil, isfinite

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
        self.last_timings: dict[str, float] = {}
        self._tracking_ms = 0.0
        self._instrumented = False
        self.last_diagnostics: dict = {}
        self._source_fps = 30.0
        if hasattr(model, "add_callback"):
            # select_device de Ultralytics establece sus propios hilos durante
            # setup_model; aplicar nuestra opción después, antes de inferencia.
            model.add_callback("on_predict_start", self._configure_threads)
            # Se registra antes de ByteTrack: distinguir cajas YOLO de tracks.
            model.add_callback("on_predict_postprocess_end", self._observe_detections)

    def _observe_detections(self, predictor) -> None:
        boxes = predictor.results[0].boxes
        scores = [] if boxes is None else boxes.conf.cpu().tolist()
        trackers = getattr(predictor, "trackers", ())
        if self.config.track_buffer_seconds:
            # ByteTrack avanza una vez por inferencia, no por frame capturado.
            for tracker in trackers:
                tracker.max_time_lost = ceil(self.config.track_buffer_seconds *
                                             self._source_fps / self.config.vid_stride)
        threshold = getattr(getattr(trackers[0], "args", None), "track_high_thresh", 0.25) if trackers else 0.25
        self.last_diagnostics = {"person_detections": len(scores),
                                 "low_confidence_detections": sum(score < threshold for score in scores)}

    def set_source_fps(self, fps: float) -> None:
        if isfinite(fps) and fps > 0:
            self._source_fps = fps

    def _configure_threads(self, predictor) -> None:
        if self.config.torch_threads:
            import torch
            if torch.get_num_threads() != self.config.torch_threads:
                torch.set_num_threads(self.config.torch_threads)

    def _instrument_tracking(self) -> None:
        """Medir el callback integrado de ByteTrack sin reemplazar su algoritmo."""
        if self._instrumented or not hasattr(self.model, "callbacks"):
            return
        callbacks = self.model.callbacks["on_predict_postprocess_end"]
        for index, callback in enumerate(callbacks):
            function = getattr(callback, "func", callback)
            if (getattr(function, "__module__", "") == "ultralytics.trackers.track"
                    and getattr(function, "__name__", "") == "on_predict_postprocess_end"):
                def timed(predictor, original=callback):
                    start = perf_counter()
                    original(predictor)
                    self._tracking_ms += (perf_counter() - start) * 1000
                callbacks[index] = timed
                self._instrumented = True
                return
        raise RuntimeError("No se encontró el callback de tracking para medirlo")

    def reset(self) -> None:
        """Una vuelta nueva no conserva identidades de la vuelta anterior."""
        predictor = getattr(self.model, "predictor", None)
        for tracker in getattr(predictor, "trackers", ()):
            tracker.reset()

    def detect(self, frame) -> list[Track]:
        start = perf_counter()
        self.last_diagnostics = {}
        self._tracking_ms = 0.0
        height, width = frame.shape[:2]
        left, top = int(width * self.config.roi_left), int(height * self.config.roi_top)
        right, bottom = int(width * self.config.roi_right), int(height * self.config.roi_bottom)
        if right <= left or bottom <= top:
            raise ValueError("ROI vacío a esta resolución")
        cropped = frame[top:bottom, left:right]
        result = self.model.track(
            cropped, persist=True, tracker=self.config.tracker, classes=[0],
            device="cpu", imgsz=self.config.imgsz, conf=self.config.conf,
            verbose=False, save=False, save_txt=False, save_crop=False,
            show=False, stream=False,
        )[0]
        # La primera llamada registra el tracker. Esa llamada pertenece al
        # calentamiento del benchmark; desde la siguiente se mide ByteTrack.
        self._instrument_tracking()
        tracks = self._extract_tracks(result, frame, offset=(left, top))
        speed = getattr(result, "speed", {})
        self.last_timings = {key: float(speed.get(key, 0))
                             for key in ("preprocess", "inference", "postprocess")}
        self.last_timings["tracking"] = self._tracking_ms
        self.last_timings["detector_other"] = max(0.0, (perf_counter() - start) * 1000
                                                 - sum(self.last_timings.values()))
        return tracks

    def _extract_tracks(self, result, frame, *, offset=(0, 0)) -> list[Track]:
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return []
        height, width = frame.shape[:2]
        tracks = []
        rejected = 0
        for track_id, coords in zip(boxes.id.int().cpu().tolist(), boxes.xyxy.cpu().tolist()):
            x1, y1, x2, y2 = coords
            x1, x2 = x1 + offset[0], x2 + offset[0]
            y1, y2 = y1 + offset[1], y2 + offset[1]
            area = (x2 - x1) * (y2 - y1) / (width * height)
            if self.config.min_area_ratio <= area <= self.config.max_area_ratio:
                tracks.append(Track(int(track_id), ((x1 + x2) / (2 * width),
                                                    (y1 + y2) / (2 * height)),
                                    (x1 / width, y1 / height, x2 / width, y2 / height)))
            else:
                rejected += 1
        self.last_diagnostics.update(tracked_before_area=len(tracks) + rejected,
                                     area_rejections=rejected)
        return tracks
