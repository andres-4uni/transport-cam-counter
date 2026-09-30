"""Ejecuta captura e inferencia; --debug habilita la ventana local."""

import argparse
import json
from time import perf_counter

import cv2

from apc.config import load_config
from apc.counting.occupancy import OccupancyCounter
from apc.counting.tripwire import TripwireCounter
from apc.detection.detector import PersonDetector
from apc.preview import annotate
from apc.publisher.server import TelemetryPublisher
from apc.publisher.telemetry import TelemetryStore, make_sample
from apc.sources import create_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0, help="0: hasta finalizar")
    args = parser.parse_args()
    if args.max_frames < 0:
        parser.error("--max-frames no puede ser negativo")
    config = load_config(args.config)
    detector = PersonDetector(config.detection, config.resolve(config.detection.model))
    counter = TripwireCounter(config.counting)
    occupancy = OccupancyCounter(config.occupancy)
    store = TelemetryStore()
    show = args.debug or config.debug.show_video
    processed = 0
    start = perf_counter()
    last_publish = 0.0
    try:
        with TelemetryPublisher(store, config.telemetry.port), create_source(config) as source:
            for packet in source:
                if packet.index % config.detection.vid_stride:
                    continue
                tracks = detector.detect(packet.frame)
                occupancy.apply(counter.update(tracks))
                processed += 1
                fps = processed / max(perf_counter() - start, 1e-9)
                if perf_counter() - last_publish >= config.telemetry.interval_seconds:
                    store.publish(make_sample(config.telemetry.wagon_id, occupancy, fps,
                                              timestamp=packet.timestamp))
                    last_publish = perf_counter()
                if show:
                    cv2.imshow("APC - vista local (Q para salir)",
                               annotate(packet.frame, tracks, config.counting, fps))
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                if args.max_frames and processed >= args.max_frames:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if show:
            cv2.destroyAllWindows()
    print(json.dumps({"frames": processed,
                      "fps": round(processed / max(perf_counter() - start, 1e-9), 2),
                      "entries": occupancy.entries, "exits": occupancy.exits,
                      "occupancy": occupancy.occupancy}))


if __name__ == "__main__":
    main()
