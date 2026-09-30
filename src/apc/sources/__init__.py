"""Fuentes intercambiables de video."""

from apc.config import Config
from apc.sources.file import FileSource
from apc.sources.webcam import WebcamSource
from apc.sources.stream import StreamSource
from apc.sources.base import VideoSource


def create_source(config: Config) -> VideoSource:
    if config.source.type == "file":
        return FileSource(config.resolve(config.source.path), config.source.queue_size)
    if config.source.type == "webcam":
        return WebcamSource(config.source)
    if config.source.type == "stream":
        return StreamSource(config.source)
    raise ValueError("Tipo de fuente desconocido")
