"""Evalúa un video local una sola vez contra el conteo manual, sin guardar imágenes."""

import argparse
from dataclasses import asdict, replace
import json

from apc.config import load_config
from apc.calibration import counting_values
from apc.detection.detector import PersonDetector
from apc.evaluation import evaluate
from apc.sources.file import FileSource


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", help="Archivo local; por defecto source.path del YAML")
    parser.add_argument("--counting-debug", action="store_true", help="Diagnóstico textual de cruces, sin imágenes")
    parser.add_argument("--diagnostics", action="store_true", help="Resumen numérico de eventos, IDs y expiraciones")
    parser.add_argument("--verified-frames", type=int, help="Total reproducible verificado independientemente; no amplía ±2")
    parser.add_argument("--output", help="Guardar solo JSON numérico; rechaza sobrescribir")
    parser.add_argument("--expected-in", type=int, required=True)
    parser.add_argument("--expected-out", type=int, required=True)
    parser.add_argument("--imgsz", type=int, choices=tuple(range(320, 641, 32)))
    parser.add_argument("--vid-stride", type=int)
    parser.add_argument("--torch-threads", type=int)
    args = parser.parse_args(argv)
    from pathlib import Path
    if args.output and Path(args.output).exists():
        parser.error("El archivo de evaluación ya existe")
    if min(args.expected_in, args.expected_out) < 0 or (args.vid_stride is not None and args.vid_stride < 1):
        parser.error("Conteos no negativos y vid-stride positivo requeridos")
    if args.torch_threads is not None and args.torch_threads < 0:
        parser.error("--torch-threads debe ser no negativo")
    config = load_config(args.config)
    config = replace(config, debug=replace(config.debug, counting=args.counting_debug or config.debug.counting))
    config = replace(config, detection=replace(config.detection,
                     imgsz=args.imgsz or config.detection.imgsz,
                     vid_stride=args.vid_stride or config.detection.vid_stride,
                     torch_threads=config.detection.torch_threads if args.torch_threads is None else args.torch_threads))
    path = config.resolve(args.video or config.source.path)
    detector = PersonDetector(config.detection, config.resolve(config.detection.model))
    result = evaluate(config, FileSource(path, config.source.queue_size), detector,
                      expected_in=args.expected_in, expected_out=args.expected_out,
                      diagnostics=args.diagnostics, verified_frames=args.verified_frames)
    result.update(video=str(path.relative_to(config.root)) if path.is_relative_to(config.root) else path.name,
                  config=args.config, counting=counting_values(config.counting),
                  imgsz=config.detection.imgsz, vid_stride=config.detection.vid_stride,
                  conf=config.detection.conf, torch_threads_requested=config.detection.torch_threads)
    result.update(detection=asdict(config.detection))
    tracker_path = Path(config.detection.tracker)
    if tracker_path.is_absolute() and tracker_path.is_relative_to(config.root):
        result["detection"]["tracker"] = str(tracker_path.relative_to(config.root))
    serialized = json.dumps(result, indent=2, allow_nan=False)
    if args.output:
        with Path(args.output).open("x", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
        print(json.dumps({"output": args.output, "in": result["in"], "out": result["out"],
                          "processed_frames": result["processed_frames"], "fps": result["fps"]}))
    else:
        print(serialized)


if __name__ == "__main__":
    main()
