"""Diagnóstico con tracks y video sintético en RAM; nunca abre videos reales."""
from dataclasses import replace

import pytest

from apc.config import load_config
from apc.evaluation import evaluate
from apc.models import Track
from apc.sources.file import FileSource


class Detector:
    last_diagnostics = {"person_detections": 2, "area_rejections": 1, "low_confidence_detections": 1}

    def reset(self):
        self.index = 0

    def detect(self, frame):
        y = [0.2, 0.3, 0.7, 0.8, 0.8][self.index]
        self.index += 1
        return [Track(11, (0.3, y), (0.0, y - 0.1, 0.6, min(1, y + 0.1)))]


def test_numeric_events_include_source_frame_anchor_age_and_sides(video_path):
    result = evaluate(load_config(), FileSource(video_path), Detector(), expected_in=1,
                      expected_out=0, diagnostics=True)
    detail = result["diagnostics"]
    event, = detail["events"]
    assert event["frame"] == event["processed_frame"] == 2
    assert event["video_seconds"] == 0.2
    assert event["anchor"] == (0.3, 0.7)
    assert event["age_observations"] == 3
    assert (event["from_side"], event["to_side"], event["direction"]) == (-1, 1, "in")
    assert detail["person_detections"] == 10
    assert detail["area_rejections"] == detail["low_confidence_detections"] == 5
    assert detail["ids"][0]["border_observations"] == 5
    assert result["fps"] > 0


def test_verified_reference_preserves_declared_and_does_not_widen_tolerance(video_path, monkeypatch):
    source = FileSource(video_path)
    open_capture = source._open_capture
    def altered_metadata():
        capture = open_capture()
        source.metadata["frames"] = 20
        return capture
    monkeypatch.setattr(source, "_open_capture", altered_metadata)
    result = evaluate(load_config(), source, Detector(), expected_in=1, expected_out=0,
                      verified_frames=5)
    assert result["frame_validation"]["container_declared"] == 20
    assert result["frame_validation"]["container_difference"] == -15
    assert result["frame_validation"]["tolerance"] == 2
    with pytest.raises(RuntimeError, match="fuera de la tolerancia"):
        evaluate(load_config(), FileSource(video_path), Detector(), expected_in=1,
                 expected_out=0, verified_frames=8)


def test_stride_reports_source_and_processed_indices_separately(video_path):
    config = load_config()
    config = replace(config, detection=replace(config.detection, vid_stride=2))
    result = evaluate(config, FileSource(video_path), Detector(), expected_in=1,
                      expected_out=0, diagnostics=True)
    event, = result["diagnostics"]["events"]
    assert event["frame"] == 4 and event["processed_frame"] == 2
    assert event["video_seconds"] == 0.4
    assert result["processed_frames"] == 3


def test_cli_saves_numeric_report_and_refuses_overwrite(video_path, tmp_path, monkeypatch, capsys):
    import importlib.util
    import json
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / 'scripts/evaluate_counts.py'
    spec = importlib.util.spec_from_file_location('evaluation_cli_test', script)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(cli, 'PersonDetector', lambda *a: Detector())
    output = tmp_path / 'evaluation.json'
    args = ['--video', str(video_path), '--expected-in', '1', '--expected-out', '0',
            '--diagnostics', '--verified-frames', '5', '--output', str(output)]
    cli.main(args)
    data = json.loads(output.read_text())
    assert data['in']['observed'] == 1
    assert len(data['diagnostics']['events']) == 1
    assert data['detection']['imgsz'] == 320
    assert 'frame' not in data  # Ninguna imagen ni array de píxeles en el informe.
    original = output.read_bytes()
    with pytest.raises(SystemExit):
        cli.main(args)
    assert output.read_bytes() == original


def test_event_uses_media_time_instead_of_average_fps(video_path):
    from apc.sources.base import FramePacket
    class MediaSource:
        loop = False
        metadata = {'fps': 10, 'frames': 5}
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def __iter__(self):
            for i, seconds in enumerate([0, .04, .12, .18, .25]):
                yield FramePacket(i, 100 + i, None, media_seconds=seconds)
    result = evaluate(load_config(), MediaSource(), Detector(), expected_in=1,
                      expected_out=0, diagnostics=True)
    assert result['diagnostics']['events'][0]['video_seconds'] == .12
    assert result['diagnostics']['timestamp_fallback_frames'] == 0


def test_dual_zone_diagnostics_consolidate_tracklets_and_keep_raw_ids(video_path):
    class FragmentedDetector(Detector):
        def detect(self, frame):
            y = [.2, .3, .5, .7, .8][self.index]
            key = 7 if self.index < 3 else 12
            self.index += 1
            return [Track(key, (.5, y))]
    config = load_config()
    config = replace(config, counting=replace(config.counting, mode='dual_zone',
                     max_missing_seconds=.9, stitching=True))
    result = evaluate(config, FileSource(video_path), FragmentedDetector(),
                      expected_in=1, expected_out=0, diagnostics=True)
    report = result['diagnostics']
    assert result['in']['observed'] == 1
    assert report['unique_ids'] == 2 and report['logical_passengers'] == 1
    assert len(report['stitches']) == 1
    event, = report['events']
    assert (event['logical_id'], event['track_id'], event['direction']) == (1, 12, 'in')
    assert report['ids'][0]['track_ids'] == [7, 12]
    assert report['ids'][0]['observations'] == 5
