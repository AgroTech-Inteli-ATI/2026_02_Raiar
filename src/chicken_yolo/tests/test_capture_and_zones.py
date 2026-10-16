import cv2
import numpy as np
import pytest
import yaml

from chicken_yolo.capture import iter_frames, write_image
from chicken_yolo.domain import parse_timestamp
from chicken_yolo.zones import Zone, ZoneConfig, load_zones


def test_unicode_image_path_and_missing_time(tmp_path):
    source = tmp_path / "galinhas-recriação.png"
    write_image(source, np.full((100, 100, 3), 120, dtype=np.uint8))
    frame = next(iter_frames(source))
    assert frame.image.shape == (100, 100, 3)
    assert frame.metadata["capturado_em"] is None


def test_video_sampling_preserves_offsets_and_original_start(tmp_path):
    source = tmp_path / "video.avi"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"MJPG"), 10, (100, 100))
    assert writer.isOpened()
    for index in range(30):
        writer.write(np.full((100, 100, 3), index * 5, dtype=np.uint8))
    writer.release()
    frames = list(iter_frames(source, 1.0, "camera-01", "lote-01", "2026-10-14T12:00:00-03:00"))
    assert [f.metadata["offset_ms"] for f in frames] == [0, 1000, 2000]
    assert frames[-1].metadata["capturado_em"] == "2026-10-14T15:00:02+00:00"
    assert len({f.metadata["quadro_id"] for f in frames}) == 3


def test_capture_rejects_naive_times_and_empty_video(tmp_path):
    with pytest.raises(ValueError, match="fuso"):
        parse_timestamp("2026-10-14T12:00:00")
    source = tmp_path / "invalid.avi"
    source.write_bytes(b"invalid")
    with pytest.raises(ValueError):
        list(iter_frames(source))


def test_corrupt_image_is_an_invalid_frame_not_a_zero_count(tmp_path):
    source = tmp_path / "corrupt.jpg"
    source.write_bytes(b"broken")
    frame = next(iter_frames(source))
    assert frame.image is None
    assert frame.error


def test_uncalibrated_example_is_blocked(tmp_path):
    path = tmp_path / "zones.yaml"
    path.write_text(yaml.safe_dump({"calibrated": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="calibradas"):
        load_zones(path)


def test_overlap_and_outside_remain_indeterminate():
    zone = Zone("a", ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)))
    zones = ZoneConfig("cam", "v1", "r1", (100, 100), (zone, Zone("b", zone.polygon)), "sha")
    assert zones.assign((20, 20, 40, 40), 100, 100) == (None, "zonas_sobrepostas")
    assert zones.assign((0, 0, 4, 4), 100, 100) == (None, "fora_das_zonas")


@pytest.mark.parametrize(
    "polygon",
    [
        ((0, 0), (1, 1), (1, 0), (0, 1)),
        ((0, 0), (0.5, 0.5), (1, 1)),
        ((0, 0), (2, 0), (1, 1)),
        ((0, 0), (0, 0), (1, 1)),
    ],
)
def test_invalid_zone_polygons_are_rejected(polygon):
    with pytest.raises(ValueError):
        Zone("zone", polygon)
