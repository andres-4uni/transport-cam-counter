"""Comprobaciones de metadatos; nunca vuelven a abrir ni modifican el video."""

import warnings


def validate_frame_count(declared: int, decoded: int, *, tolerance: int = 2) -> dict:
    """Comparar una pasada completa: los contenedores pueden aproximar el total."""
    if decoded < 0 or tolerance < 0:
        raise ValueError("Frames decodificados y tolerancia deben ser no negativos")
    difference = decoded - declared if declared > 0 else None
    message = None
    if difference is None:
        message = "El archivo no declara un total de frames; se informa el total decodificado"
    elif abs(difference) > tolerance:
        raise RuntimeError(f"Frames declarados={declared}, decodificados={decoded}: "
                           f"diferencia {difference:+d} fuera de la tolerancia ±{tolerance}")
    elif difference:
        message = (f"Frames declarados={declared}, decodificados={decoded}: "
                   f"diferencia {difference:+d} aceptada dentro de ±{tolerance}")
    if message:
        warnings.warn(message, RuntimeWarning, stacklevel=2)
    return {"declared": declared, "decoded": decoded, "difference": difference,
            "tolerance": tolerance, "status": "warning" if message else "ok",
            "warning": message}
