from time import time

from streamlit.testing.v1 import AppTest

from apc.config import load_config
from apc.publisher import client
from apc.publisher.simulation import simulation_samples


def test_dashboard_renders_train_and_simulation_label(monkeypatch):
    config = load_config()
    monkeypatch.setattr(client, "fetch_samples", lambda port: simulation_samples(config, 0, time()))
    app = AppTest.from_file("dashboard/app.py").run(timeout=20)
    assert not app.exception
    assert "SIMULACIÓN" in app.warning[0].value
    assert app.metric[0].value == "205"
    assert app.metric[3].value == "4 / 4"
    markup = " ".join(element.value for element in app.markdown)
    assert all(value in markup for value in ("VAGÓN 01", "VAGÓN 04", "Disponible", "Ocupación media", "Ocupación alta"))


def test_dashboard_marks_stale_data_without_live_total(monkeypatch):
    config = load_config()
    monkeypatch.setattr(client, "fetch_samples", lambda port: simulation_samples(config, 0, time() - 20))
    app = AppTest.from_file("dashboard/app.py").run(timeout=20)
    assert not app.exception
    assert app.metric[0].value == "—"
    assert app.metric[3].value == "0 / 4"
    assert "desactualizados" in app.error[0].value
    assert "Sin señal" in " ".join(element.value for element in app.markdown)


def test_dashboard_api_unavailable(monkeypatch):
    def unavailable(port):
        raise OSError("sin servidor")
    monkeypatch.setattr(client, "fetch_samples", unavailable)
    app = AppTest.from_file("dashboard/app.py").run(timeout=20)
    assert not app.exception
    assert "Sin conexión" in app.error[0].value
    assert not app.metric
