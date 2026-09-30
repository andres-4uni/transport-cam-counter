"""Publica varios vagones de prueba; Ctrl+C finaliza limpiamente."""

import argparse
from time import sleep, time

from apc.config import load_config
from apc.publisher.server import TelemetryPublisher
from apc.publisher.simulation import simulation_samples
from apc.publisher.telemetry import TelemetryStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--steps", type=int, default=0, help="0: continuo")
    args = parser.parse_args()
    if args.steps < 0:
        parser.error("--steps debe ser no negativo")
    config = load_config(args.config)
    store = TelemetryStore()
    try:
        with TelemetryPublisher(store, config.telemetry.port) as publisher:
            print(f"SIMULACIÓN: http://127.0.0.1:{publisher.port}/telemetry", flush=True)
            step = 0
            while args.steps == 0 or step < args.steps:
                for sample in simulation_samples(config, step, time()):
                    store.publish(sample)
                step += 1
                sleep(config.telemetry.interval_seconds)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
