"""Diagnóstico optativo y exclusivamente textual; nunca recibe imágenes."""

import sys


class CountingDebug:
    """Transiciones y un recordatorio cada 30 observaciones; estado acotado por ID."""

    def __init__(self, output=None):
        self.output = output or sys.stderr
        self._last: dict[int, tuple] = {}

    def __call__(self, row: dict) -> None:
        key = row["track_id"]
        signature = (row["position"], row["current"], row["reason"], row["event"])
        if (signature != self._last.get(key) or row["age"] % 30 == 0
                or row["event"] != "none"):
            x, y = row["point"]
            event = {"entry": "IN", "exit": "OUT", "none": "-"}[row["event"]]
            negative, positive = (("arriba", "abajo") if row.get("orientation") == "horizontal"
                                  else ("izquierda", "derecha"))
            zone = {-1: negative, 0: "banda", 1: positive}.get(row["position"], row["position"])
            print(f"COUNT frame={row['frame']} id={key} edad={row['age']} "
                  f"p=({x:.4f},{y:.4f}) zona={zone} "
                  f"estado={row['previous']}->{row['current']} mov={row['movement']} "
                  f"evento={event} motivo={row['reason']} ausencias={row['missing']}",
                  file=self.output)
        self._last[key] = signature
        if row["position"] == "expired":
            del self._last[key]
