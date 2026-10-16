import json

import pytest

from chicken_yolo.dataset import (
    prepare_dataset,
    publish_dataset,
    read_labels,
    split_groups,
    validate_dataset,
)


def test_groups_are_never_split_and_assignment_is_reproducible(raw_dataset):
    root, manifest, _ = raw_dataset
    first = prepare_dataset(root, manifest, root / "v1")
    second = prepare_dataset(root, manifest, root / "v2")
    assert first["group_assignment"] == second["group_assignment"]
    assert first["dataset_sha256"] == second["dataset_sha256"]
    _, records, _ = validate_dataset(root / "v1/dataset.yaml")
    for group in {row["grupo_origem"] for row in records}:
        assert len({row["split"] for row in records if row["grupo_origem"] == group}) == 1
    assert {row["split"] for row in records} == {"train", "val", "test"}


def test_too_few_independent_groups_are_rejected():
    with pytest.raises(ValueError, match="três grupos"):
        split_groups({"video-a", "video-b"})


@pytest.mark.parametrize(
    "label",
    [
        "1 .5 .5 .2 .2",
        "0 .5 .5 0 .2",
        "0 nan .5 .2 .2",
        "0 .95 .5 .2 .2",
        "0 .5 .5 .2",
        "0 .5 .5 inf .2",
    ],
)
def test_invalid_labels_are_rejected(tmp_path, label):
    path = tmp_path / "label.txt"
    path.write_text(label, encoding="utf-8")
    with pytest.raises(ValueError):
        read_labels(path)


def test_negative_images_require_explicit_empty_label(tmp_path):
    path = tmp_path / "negative.txt"
    path.write_text("", encoding="utf-8")
    assert read_labels(path) == []
    with pytest.raises(FileNotFoundError):
        read_labels(tmp_path / "missing.txt")


@pytest.mark.parametrize(
    "field,value", [("status_revisao", "rascunho"), ("qualidade", "pendente"), ("grupo_origem", "")]
)
def test_unreviewed_or_ungrouped_images_are_rejected(raw_dataset, field, value):
    root, manifest, rows = raw_dataset
    rows[0][field] = value
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_dataset(root, manifest, root / "invalid")
    assert not (root / "invalid").exists()


def test_duplicate_pixels_across_groups_are_rejected(raw_dataset):
    root, manifest, rows = raw_dataset
    (root / rows[2]["imagem"]).write_bytes((root / rows[0]["imagem"]).read_bytes())
    with pytest.raises(ValueError, match="duplicado"):
        prepare_dataset(root, manifest, root / "invalid")


def test_dataset_changes_and_overwrites_are_rejected(prepared_dataset):
    root, output, _ = prepared_dataset
    with pytest.raises(FileExistsError):
        prepare_dataset(root, root / "manifest.jsonl", output)
    _, records, _ = validate_dataset(output / "dataset.yaml")
    (output / records[0]["rotulo"]).write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="alterado"):
        validate_dataset(output / "dataset.yaml")


def test_extra_images_are_detected_before_training(prepared_dataset):
    _, output, _ = prepared_dataset
    (output / "images/train/unregistered.png").write_bytes(b"extra")
    with pytest.raises(ValueError, match="extras"):
        validate_dataset(output / "dataset.yaml")


def test_dataset_publication_retries_transient_windows_lock_without_overwriting(
    tmp_path, monkeypatch
):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "data.txt").write_text("dataset", encoding="utf-8")
    output = tmp_path / "v1"
    original = type(staging).rename
    attempts = []

    def rename(path, target):
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError("temporary lock")
        return original(path, target)

    monkeypatch.setattr(type(staging), "rename", rename)
    publish_dataset(staging, output)
    assert (output / "data.txt").read_text() == "dataset"
    assert len(attempts) == 3
    with pytest.raises(FileExistsError):
        publish_dataset(tmp_path / "other", output)
