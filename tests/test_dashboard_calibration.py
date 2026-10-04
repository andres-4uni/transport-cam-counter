from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from apc.calibration import CalibrationSession
from apc.config import load_config
from apc.publisher import client


APP_PATH = Path(__file__).resolve().parents[1] / "dashboard/app.py"


@pytest.fixture
def calibration_app(tmp_path, monkeypatch):
    profile = tmp_path / "configs" / "usb-camera.yaml"
    profile.parent.mkdir()
    profile.write_text("source:\n  type: webcam\n  index: 2\n")
    session = CalibrationSession(load_config(profile), profile)
    monkeypatch.setattr(client, "fetch_samples", lambda port: [])
    monkeypatch.setattr(client, "fetch_video_status", lambda port: {"enabled": 0, "ready": 0})
    monkeypatch.setattr(client, "fetch_calibration", lambda port: session.snapshot())
    applied, saved = [], []
    def apply(port, values):
        applied.append(values)
        return session.apply(values)
    def save(port, values):
        saved.append(values)
        return session.save(values)
    monkeypatch.setattr(client, "apply_calibration", apply)
    monkeypatch.setattr(client, "save_calibration", save)
    return AppTest.from_file(APP_PATH), session, profile, applied, saved


def test_dashboard_uses_active_source_and_separates_apply_from_save(calibration_app):
    app, session, profile, applied, saved = calibration_app
    original = profile.read_text()
    app.run(timeout=20)
    assert not app.exception
    assert "webcam / cámara USB" in " ".join(item.value for item in app.caption)
    assert str(profile) in " ".join(item.value for item in app.caption)
    app.selectbox(key="cal_orientation").set_value("vertical").run()
    app.selectbox(key="cal_direction").set_value("left").run()
    app.slider(key="cal_position").set_value(0.6).run()
    assert not app.exception and applied and not saved
    assert profile.read_text() == original
    assert applied[-1]["enter_direction"] == "left"
    assert session.current()[1].position == 0.6
    assert profile.read_text() == original and not saved
    app.button(key="cal_save").click().run()
    assert not app.exception and len(saved) == 1
    assert load_config(profile).counting.entry_direction == "left"
    app.run()
    assert len(saved) == 1 and len(app.success) == 1
    app.slider(key="cal_position").set_value(0.61).run()
    assert not app.success and load_config(profile).counting.position == 0.6


def test_dashboard_updates_directions_and_rejects_invalid_band(calibration_app):
    app, session, _, applied, saved = calibration_app
    app.run(timeout=20)
    assert app.selectbox(key="cal_direction").options == ["Arriba (↑)", "Abajo (↓)"]
    app.selectbox(key="cal_orientation").set_value("vertical").run()
    assert app.selectbox(key="cal_direction").options == ["Izquierda (←)", "Derecha (→)"]
    app.slider(key="cal_position").set_value(0.01).run()
    assert not app.exception
    assert app.button(key="cal_save").disabled
    assert not saved
    assert session.current()[1].position == 0.5


def test_dashboard_reports_save_error_without_crashing(calibration_app, monkeypatch):
    app, _, _, _, _ = calibration_app
    def reject(*args):
        raise ValueError("default.yaml está protegido")
    monkeypatch.setattr(client, "save_calibration", reject)
    app.run(timeout=20)
    app.button(key="cal_save").click().run()
    assert not app.exception
    assert any("default.yaml está protegido" in item.value for item in app.error)


def test_dashboard_preserves_valid_calibration_near_image_edge(calibration_app):
    app, session, _, applied, _ = calibration_app
    session.apply({"position": 0.0005, "band_half_width": 0.0001})
    app.run(timeout=20)
    assert not app.exception
    assert app.slider(key="cal_position").value == 0.0005
    assert app.slider(key="cal_band").value == 0.0001
    assert not app.button(key="cal_save").disabled
    captions = " ".join(item.value for item in app.caption)
    assert "y=0.0005" in captions and "[0.0004, 0.0006]" in captions
    assert not applied  # El backend ya tenía estos valores; no reiniciar sin cambios.
    assert session.current()[0] == 1


def test_default_profile_can_preview_but_cannot_save(calibration_app):
    app, session, profile, applied, saved = calibration_app
    session.config_path = profile.with_name("default.yaml")
    session.config_path.write_text(profile.read_text())
    original = session.config_path.read_text()
    app.run(timeout=20)
    app.slider(key="cal_position").set_value(0.6).run()
    assert not app.exception and applied
    assert app.button(key="cal_save").disabled
    assert any("default.yaml está protegido" in item.value for item in app.warning)
    assert not saved and session.config_path.read_text() == original


def test_preview_failure_disables_save_and_keeps_yaml(calibration_app, monkeypatch):
    app, _, profile, _, saved = calibration_app
    def unavailable(*args):
        raise OSError("sin conexión")
    monkeypatch.setattr(client, "apply_calibration", unavailable)
    original = profile.read_text()
    app.run(timeout=20)
    app.slider(key="cal_position").set_value(0.6).run()
    assert not app.exception
    assert app.button(key="cal_save").disabled
    assert any("vista previa" in item.value for item in app.error)
    assert not saved and profile.read_text() == original
