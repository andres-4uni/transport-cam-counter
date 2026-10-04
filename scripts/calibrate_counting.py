"""Mostrar o guardar una calibración sin abrir cámaras, modelos ni videos."""

import argparse
import json

from apc.calibration import counting_values, save_calibration
from apc.config import counting_from_dict, load_config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--orientation", choices=["vertical", "horizontal"])
    parser.add_argument("--position", type=float)
    parser.add_argument("--band-half-width", type=float)
    parser.add_argument("--enter-direction", choices=["left", "right", "up", "down"])
    parser.add_argument("--min-track-frames", type=int)
    parser.add_argument("--max-missing-frames", type=int)
    parser.add_argument("--save", action="store_true", help="Escribir explícitamente la propuesta")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        values = counting_values(config.counting)
        for key in values:
            value = getattr(args, key, None)
            if value is not None:
                values[key] = value
        counting = counting_from_dict(values)
        result = {"counting": counting_values(counting), "saved": False}
        if args.save:
            result.update(saved=True, saved_path=str(save_calibration(args.config, counting)))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
