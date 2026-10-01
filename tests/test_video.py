import builtins
import io
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

import cv2
import numpy as np
import pytest

from apc.config import CountingConfig, VisualizationConfig
from apc.publisher.client import fetch_video_status
from apc.publisher.server import TelemetryPublisher
from apc.publisher.telemetry import TelemetryStore
from apc.publisher.video import LatestFrame
from apc.visualization.overlay import draw_overlay


def open_local(url):
    return build_opener(ProxyHandler({})).open(url, timeout=3)


def read_jpeg(response):
    assert response.readline() == b"--frame\r\n"
    assert response.readline() == b"Content-Type: image/jpeg\r\n"
    length = int(response.readline().decode().split(":", 1)[1])
    assert response.readline() == b"\r\n"
    jpeg = response.read(length)
    assert response.read(2) == b"\r\n"
    return cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)


def test_http_mjpeg_headers_frame_and_shutdown():
    video = LatestFrame(VisualizationConfig(stream=True))
    frame = np.full((120, 160, 3), 160, dtype=np.uint8)
    assert video.publish(frame)
    with TelemetryPublisher(TelemetryStore(), port=0, video=video) as publisher:
        assert publisher._server.server_address[0] == "127.0.0.1"
        assert fetch_video_status(publisher.port) == {"enabled": 1, "ready": 1}
        response = open_local(f"http://127.0.0.1:{publisher.port}/video")
        assert response.status == 200
        assert response.headers["Content-Type"] == "multipart/x-mixed-replace; boundary=frame"
        assert "no-store" in response.headers["Cache-Control"]
        image = read_jpeg(response)
        assert image.shape == frame.shape
        assert abs(float(image.mean()) - 160) < 2
    assert video.closed.is_set()
    assert video.next_frame(0) is None
    assert response.read() == b"--frame--\r\n"
    response.close()


def test_video_disabled_or_waiting_has_explicit_http_response(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No se debe codificar cuando el stream está apagado")
    monkeypatch.setattr(cv2, "imencode", forbidden)
    disabled = LatestFrame(VisualizationConfig())
    assert not disabled.publish(np.zeros((20, 20, 3), dtype=np.uint8))
    for video, expected in [(None, 404), (disabled, 404),
                            (LatestFrame(VisualizationConfig(stream=True)), 503)]:
        with TelemetryPublisher(TelemetryStore(), port=0, video=video) as publisher:
            with pytest.raises(HTTPError) as error:
                open_local(f"http://127.0.0.1:{publisher.port}/video")
            assert error.value.code == expected


def test_latest_frame_replacement_fps_limit_and_staleness(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("apc.publisher.video.monotonic", lambda: clock[0])
    video = LatestFrame(VisualizationConfig(stream=True, max_fps=10), stale_after_seconds=3)
    dark = np.zeros((32, 32, 3), dtype=np.uint8)
    assert video.publish(dark)
    assert not video.publish(dark + 100)
    clock[0] = 0.11
    assert video.publish(dark + 200)
    version, jpeg = video.next_frame(0)
    assert version == 2
    image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert image.mean() > 195
    clock[0] = 4
    assert video.status() == {"enabled": 1, "ready": 0}
    assert video.next_frame(0) is None
    video.close()


def test_close_wakes_waiting_reader():
    video = LatestFrame(VisualizationConfig(stream=True))
    results = []
    reader = Thread(target=lambda: results.append(video.next_frame(0, timeout=10)))
    reader.start()
    video.close()
    reader.join(timeout=1)
    assert not reader.is_alive()
    assert results == [None]


def test_overlay_encode_and_http_never_write_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("La ruta de video intentó escribir o abrir un archivo")
    # Se prohíbe IO de archivos en toda la ruta de producción del frame.
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(cv2, "imwrite", forbidden)
        patch.setattr(cv2, "VideoWriter", forbidden)
        frame = draw_overlay(np.zeros((120, 160, 3), np.uint8), [], CountingConfig(),
                             VisualizationConfig(), entries=1, exits=0, occupancy=1)
        video = LatestFrame(VisualizationConfig(stream=True))
        assert video.publish(frame)
        with TelemetryPublisher(TelemetryStore(), port=0, video=video) as publisher:
            with open_local(f"http://127.0.0.1:{publisher.port}/video") as response:
                assert read_jpeg(response).shape == frame.shape
    assert list(Path.cwd().iterdir()) == []
