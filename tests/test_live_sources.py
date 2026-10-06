from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import cv2
import numpy as np
import pytest

from apc.config import SourceConfig, load_config
from apc.sources import create_source
from apc.sources.base import FramePacket
from apc.sources.file import FileSource
from apc.sources.stream import StreamSource
from apc.sources.webcam import WebcamSource


class FakeCapture:
    def __init__(self, opened=True, count=2):
        self.opened = opened
        self.count = count
        self.released = False
        self.properties = {}

    def isOpened(self):
        return self.opened

    def set(self, prop, value):
        self.properties[prop] = value

    def get(self, prop):
        return 30.0 if prop == cv2.CAP_PROP_FPS else 0.0

    def read(self):
        if self.count == 0:
            return False, None
        self.count -= 1
        return True, np.zeros((48, 64, 3), dtype=np.uint8)

    def release(self):
        self.released = True


@pytest.mark.parametrize("kind,cls", [("file", FileSource), ("webcam", WebcamSource), ("stream", StreamSource)])
def test_factory(kind, cls):
    config = load_config()
    config = replace(config, source=replace(config.source, type=kind, url="http://127.0.0.1/video"))
    assert isinstance(create_source(config), cls)


def test_webcam_properties_disconnect_and_release(monkeypatch):
    capture = FakeCapture()
    indices = []
    def open_capture(index):
        indices.append(index)
        return capture
    monkeypatch.setattr(cv2, "VideoCapture", open_capture)
    with WebcamSource(SourceConfig(index=2)) as source:
        assert source.metadata['fps'] == 30.0
        assert source.read().frame.shape == (48, 64, 3)
        assert source.read() is not None
        with pytest.raises(RuntimeError, match="desconectó"):
            source.read()
    assert indices == [2]
    assert capture.properties[cv2.CAP_PROP_FRAME_WIDTH] == 640
    assert capture.released
    assert not source._thread.is_alive()


def test_stream_timeouts(monkeypatch):
    capture = FakeCapture()
    calls = []
    def open_capture(*args):
        calls.append(args)
        return capture
    monkeypatch.setattr(cv2, "VideoCapture", open_capture)
    with StreamSource(SourceConfig(url="rtsp://127.0.0.1/video")) as source:
        assert source.read() is not None
    assert calls[0][1] == cv2.CAP_FFMPEG
    assert calls[0][2] == [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000]
    assert capture.released


@pytest.mark.parametrize("url", ["", "file:///private/video", "ftp://camera/video", "rtsp://"])
def test_invalid_stream_url(url):
    with pytest.raises(ValueError):
        StreamSource(SourceConfig(url=url))


@pytest.mark.parametrize("cls", [WebcamSource, StreamSource])
def test_open_failure_releases_capture(monkeypatch, cls):
    capture = FakeCapture(opened=False)
    monkeypatch.setattr(cv2, "VideoCapture", lambda *args: capture)
    with pytest.raises(RuntimeError):
        cls(SourceConfig(url="http://127.0.0.1/video")).open()
    assert capture.released


def test_live_queue_replaces_old_frames():
    source = WebcamSource(SourceConfig(queue_size=1))
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    source._put(FramePacket(0, 0, frame))
    source._put(FramePacket(1, 1, frame))
    assert source._queue.get_nowait().index == 1
    source.close()


def test_real_http_video_transport():
    # FFmpeg decodifica un video MJPEG servido desde RAM por HTTP real.
    ok, jpeg = cv2.imencode(".jpg", np.full((64, 96, 3), 80, dtype=np.uint8))
    assert ok
    payload = jpeg.tobytes()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                for _ in range(100):
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                     + str(len(payload)).encode() + b"\r\n\r\n" + payload + b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass  # El lector solo necesita el primer frame.
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/synthetic.mjpg"
        with StreamSource(SourceConfig(url=url)) as source:
            packet = source.read()
            assert packet is not None
            assert packet.frame.shape == (64, 96, 3)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
