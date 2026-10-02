"""Evalúa un video local una sola vez contra el conteo manual, sin guardar imágenes."""

import argparse
from dataclasses import replace
import json

from apc.config import load_config
from apc.detection.detector import PersonDetector
from apc.evaluation import evaluate
from apc.sources.file import FileSource


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--video", help="Archivo local; por defecto source.path del YAML")
    parser.add_argument("--expected-in", type=int, required=True)
    parser.add_argument("--expected-out", type=int, required=True)
    parser.add_argument("--imgsz", type=int, choices=(320, 352, 384, 416))
    parser.add_argument("--vid-stride", type=int)
    args = parser.parse_args(argv)
    if min(args.expected_in, args.expected_out) < 0 or (args.vid_stride is not None and args.vid_stride < 1):
        parser.error("Conteos no negativos y vid-stride positivo requeridos")
    config = load_config(args.config)
    config = replace(config, detection=replace(config.detection,
                     imgsz=args.imgsz or config.detection.imgsz,
                     vid_stride=args.vid_stride or config.detection.vid_stride))
    path = config.resolve(args.video or config.source.path)
    detector = PersonDetector(config.detection, config.resolve(config.detection.model))
    result = evaluate(config, FileSource(path, config.source.queue_size), detector,
                      expected_in=args.expected_in, expected_out=args.expected_out)
    result.update(video=str(path.relative_to(config.root)) if path.is_relative_to(config.root) else path.name,
                  imgsz=config.detection.imgsz, vid_stride=config.detection.vid_stride,
                  conf=config.detection.conf)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
