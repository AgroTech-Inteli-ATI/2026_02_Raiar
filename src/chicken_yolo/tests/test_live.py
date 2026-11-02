import threading
import time

import numpy as np
import pytest
from conftest import FakeDetector

from chicken_yolo import cli
from chicken_yolo.config import InferenceConfig
from chicken_yolo.live import (
    CameraSpec,
    LatestFrameReader,
    cameras_from_env,
    make_frame,
    parse_cameras,
    redact_source,
    run_cameras,
)
from chicken_yolo.pipeline import Pipeline
from chicken_yolo.storage import ResultStore


class FakeCapture:
    """Entrega `frames` imagens e depois falha na leitura, como um stream que cai."""

    def __init__(self, frames, opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        if self.frames:
            return True, self.frames.pop(0)
        return False, None

    def release(self):
        self.released = True


def image(value=10):
    return np.full((8, 8, 3), value, dtype=np.uint8)


def wait_for(predicate, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_rtsp_credentials_never_reach_the_history():
    assert (
        redact_source("rtsp://admin:segredo@192.168.0.10:554/ch1") == "rtsp://192.168.0.10:554/ch1"
    )
    assert redact_source("/dev/video0") == "/dev/video0"
    camera = CameraSpec("1", "rtsp://admin:segredo@dvr/ch1")
    frame = make_frame(camera, image())
    assert "segredo" not in str(frame.metadata)
    assert frame.metadata["camera_id"] == "1"
    assert frame.metadata["capturado_em"].endswith("+00:00")


def test_cameras_file_is_validated():
    cameras = parse_cameras(
        {
            "cameras": [
                {"id": 3, "source": "rtsp://dvr/ch1"},
                {"id": "4", "source": "0", "enabled": False},
            ]
        }
    )
    assert [c.id for c in cameras] == ["3", "4"]
    assert cameras[0].interval_seconds == 5.0 and not cameras[1].enabled
    with pytest.raises(ValueError, match="intervalo mínimo"):
        parse_cameras({"cameras": [{"id": 1, "source": "x", "interval_seconds": 1}]})
    with pytest.raises(ValueError, match="repetida"):
        parse_cameras({"cameras": [{"id": 1, "source": "x"}, {"id": 1, "source": "y"}]})
    with pytest.raises(ValueError, match="ao menos uma"):
        parse_cameras({"cameras": []})
    with pytest.raises(ValueError, match="'id' e 'source'"):
        parse_cameras({"cameras": [{"id": 1}]})


def test_single_camera_comes_from_environment():
    camera = cameras_from_env({"RAIAR_CAMERA_SOURCE": "rtsp://dvr/ch1", "RAIAR_CAMERA_ID": "7"})[0]
    assert (camera.id, camera.source, camera.lote_id) == ("7", "rtsp://dvr/ch1", None)
    with pytest.raises(ValueError, match="RAIAR_CAMERA_SOURCE"):
        cameras_from_env({})


def test_reader_reconnects_with_backoff_after_stream_drops():
    captures = [
        FakeCapture([], opened=False),
        FakeCapture([image(1), image(2)]),
        FakeCapture([image(3)]),
    ]
    opened = []

    def opener(source):
        opened.append(source)
        return captures[min(len(opened) - 1, len(captures) - 1)]

    reader = LatestFrameReader("rtsp://dvr/ch1", opener, backoff_start=0.01).start()
    try:
        assert wait_for(lambda: reader.latest()[0] >= 3 and reader.reconnects >= 2)
        seq, latest = reader.latest()
        assert seq >= 3 and latest is not None
        assert all(c.released for c in captures[:2])
    finally:
        reader.stop()
    assert reader.last_error


def test_run_cameras_samples_each_new_frame_once_and_stops_at_limit():
    captures = FakeCapture([image(v) for v in range(1, 50)])
    seen = []
    done = run_cameras(
        [CameraSpec("1", "rtsp://dvr/ch1", lote_id="L9")],
        seen.append,
        threading.Event(),
        max_frames=1,
        opener=lambda source: captures,
        backoff_start=0.01,
    )
    assert done == len(seen) == 1
    assert seen[0].metadata["lote_id"] == "L9"


def test_run_cameras_skips_disabled_and_reports_processing_errors():
    errors = []

    def process(frame):
        raise RuntimeError("disco cheio")

    stop = threading.Event()

    def stopper(camera, exc):
        errors.append((camera.id, str(exc)))
        stop.set()

    run_cameras(
        [CameraSpec("1", "a"), CameraSpec("2", "b", enabled=False)],
        process,
        stop,
        opener=lambda source: FakeCapture([image(v) for v in range(1, 50)]),
        backoff_start=0.01,
        on_error=stopper,
    )
    assert errors == [("1", "disco cheio")]
    with pytest.raises(ValueError, match="Nenhuma câmera"):
        run_cameras([CameraSpec("2", "b", enabled=False)], print, threading.Event())


def test_live_results_land_in_the_sync_queue(tmp_path):
    pipeline = Pipeline(InferenceConfig(), FakeDetector())
    stop = threading.Event()
    with ResultStore(tmp_path / "results.sqlite3", tmp_path / "live") as store:
        run_cameras(
            [CameraSpec("5", "rtsp://u:p@dvr/ch1")],
            lambda frame: store.save(pipeline.process(frame)),
            stop,
            max_frames=1,
            opener=lambda source: FakeCapture([image(v) for v in range(1, 50)]),
            backoff_start=0.01,
        )
        rows = store.connection.execute("SELECT payload FROM analyses").fetchall()
    assert len(rows) == 1
    assert '"camera_id": "5"' in rows[0][0] and ":p@" not in rows[0][0]


def test_cli_exposes_run_command():
    args = cli.build_parser().parse_args(["run", "--cameras", "c.yaml", "--max-frames", "2"])
    assert args.command == "run" and args.max_frames == 2 and args.model is None


def test_stream_drop_and_recovery_are_reported_without_leaking_credentials():
    captures = [FakeCapture([image(1)]), FakeCapture([image(v) for v in range(2, 50)])]
    opened = []

    def opener(source):
        opened.append(source)
        return captures[min(len(opened) - 1, 1)]

    events = []
    stop = threading.Event()

    def on_status(camera, event, detail):
        events.append((camera.id, event, detail))
        if event == "recuperada":
            stop.set()

    run_cameras(
        [CameraSpec("1", "rtsp://admin:segredo@dvr/ch1", interval_seconds=5)],
        lambda frame: None,
        stop,
        opener=opener,
        backoff_start=0.01,
        on_status=on_status,
    )
    assert [e[1] for e in events] == ["queda", "recuperada"]
    assert "rtsp://dvr/ch1" in events[0][2] and "segredo" not in events[0][2]


def test_each_camera_can_carry_its_own_zones_file():
    cameras = parse_cameras(
        {
            "cameras": [
                {"id": 1, "source": "a", "zones": "config/zonas-1.yaml"},
                {"id": 2, "source": "b"},
            ]
        }
    )
    assert [c.zones for c in cameras] == ["config/zonas-1.yaml", None]
    env = cameras_from_env(
        {"RAIAR_CAMERA_SOURCE": "x", "RAIAR_LOTE_ID": "", "RAIAR_ZONES": "config/z.yaml"}
    )[0]
    assert env.lote_id is None and env.zones == "config/z.yaml"
