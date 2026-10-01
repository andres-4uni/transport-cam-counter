from pathlib import Path
from time import time

import pytest
from streamlit.testing.v1 import AppTest

from apc.config import load_config
from apc.publisher import client
from apc.publisher.simulation import simulation_samples


# AppTest debe ubicar la app independientemente del directorio llamador.
APP_PATH = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


@pytest.fixture(autouse=True)
def disabled_video(monkeypatch):
    monkeypatch.setattr(client, "fetch_video_status", lambda port: {"enabled": 0, "ready": 0})


def test_dashboard_renders_train_and_simulation_label(monkeypatch):
    config = load_config()
    monkeypatch.setattr(client, "fetch_samples", lambda port: simulation_samples(config, 0, time()))
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception
    assert "SIMULACIÓN" in app.warning[0].value
    assert app.metric[0].value == "205"
    assert app.metric[3].value == "4 / 4"
    markup = " ".join(element.value for element in app.markdown)
    assert all(value in markup for value in ("VAGÓN 01", "VAGÓN 04", "Disponible", "Ocupación media", "Ocupación alta"))


def test_dashboard_marks_stale_data_without_live_total(monkeypatch):
    config = load_config()
    monkeypatch.setattr(client, "fetch_samples", lambda port: simulation_samples(config, 0, time() - 20))
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception
    assert app.metric[0].value == "—"
    assert app.metric[3].value == "0 / 4"
    assert "desactualizados" in app.error[0].value
    assert "Sin señal" in " ".join(element.value for element in app.markdown)


def test_dashboard_api_unavailable(monkeypatch):
    def unavailable(port):
        raise OSError("sin servidor")
    monkeypatch.setattr(client, "fetch_samples", unavailable)
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception
    assert "Sin conexión" in app.error[0].value
    assert not app.metric


@pytest.mark.parametrize("enabled,ready,message", [
    (0, 0, "Video desactivado"), (1, 0, "sin frames recientes"),
    (1, 1, "http://127.0.0.1:8765/video"),
])
def test_video_panel_respects_backend_state_and_local_notice(monkeypatch, enabled, ready, message):
    monkeypatch.setattr(client, "fetch_video_status", lambda port: {"enabled": enabled, "ready": ready})
    monkeypatch.setattr(client, "fetch_samples", lambda port: [])
    app = AppTest.from_file(APP_PATH).run(timeout=20)
    assert not app.exception
    assert any("VIDEO LOCAL: no se guarda ni se transmite fuera de este equipo" in item.value for item in app.caption)
    content = " ".join(item.value for item in (*app.info, *app.markdown))
    assert message in content
    assert ('<img src="http://127.0.0.1:8765/video"' in content) == bool(enabled and ready)
