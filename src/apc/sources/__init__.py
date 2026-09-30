"""Fuentes intercambiables de video."""

from apc.config import Config
from apc.sources.file import FileSource


def create_source(config: Config):
    if config.source.type != "file":
        raise ValueError("Este hito implementa solamente source.type=file")
    return FileSource(config.resolve(config.source.path), config.source.queue_size)
