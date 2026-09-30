"""Cliente local y validación de datos para el dashboard."""

import json
from urllib.request import ProxyHandler, build_opener

from apc.publisher.telemetry import TelemetrySample


def fetch_samples(port: int, timeout: float = 1) -> list[TelemetrySample]:
    # Evitar que variables de proxy envíen solicitudes locales fuera del equipo.
    opener = build_opener(ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}/telemetry", timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("wagons"), list):
        raise ValueError("Respuesta de telemetría inválida")
    samples = [TelemetrySample(**row) for row in payload["wagons"]]
    if len({sample.wagon_id for sample in samples}) != len(samples):
        raise ValueError("Vagones duplicados")
    return sorted(samples, key=lambda sample: sample.wagon_id)
