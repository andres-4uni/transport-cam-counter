import pytest

from apc.sources.file import FileSource


def test_reads_in_order_and_finishes(video_path):
    with FileSource(video_path, queue_size=1) as source:
        packets = list(source)
        assert source.read() is None
    assert [packet.index for packet in packets] == list(range(5))
    assert [round(float(packet.frame.mean()) / 10) * 10 for packet in packets] == [20, 60, 100, 140, 180]
    assert not source._thread.is_alive()


def test_early_close_with_full_queue(video_path):
    with FileSource(video_path, queue_size=1) as source:
        assert source.read() is not None
    assert not source._thread.is_alive()


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        with FileSource(tmp_path / "missing.avi"):
            pass


def test_read_before_open(video_path):
    with pytest.raises(RuntimeError):
        FileSource(video_path).read()
