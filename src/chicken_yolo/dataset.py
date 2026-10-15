"""Dataset revisado, partições por grupo e cópias verificáveis das anotações."""

import hashlib
import json
import math
import random
import re
import shutil
import tempfile
import time
from pathlib import Path

import yaml

from .capture import iter_frames, read_image, write_image
from .config import InferenceConfig, file_hash, fingerprint, load_yaml, resolve_path
from .detector import roi_pixels

SPLITS = ("train", "val", "test")


def publish_dataset(staging: Path, output: Path) -> None:
    # Windows/antivírus pode manter uma pasta recém-criada bloqueada brevemente.
    # Preservar a publicação atômica e nunca substituir uma versão existente.
    for attempt in range(5):
        if output.exists():
            raise FileExistsError("Dataset já existe; escolha outra versão.")
        try:
            staging.rename(output)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05 * 2**attempt)


def read_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if line.strip():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"JSON inválido em {path}, linha {index}.") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Registro deve ser um objeto, linha {index}.")
                records.append(row)
    return records


def read_labels(path: Path) -> list[tuple[float, float, float, float]]:
    boxes = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            values = [float(v) for v in line.split()]
        except ValueError as exc:
            raise ValueError(f"Rótulo não numérico: {path}:{index}") from exc
        if len(values) != 5 or any(not math.isfinite(v) for v in values):
            raise ValueError(f"Rótulo deve ter cinco números finitos: {path}:{index}")
        cls, x, y, width, height = values
        if cls != 0 or not 0 < width <= 1 or not 0 < height <= 1:
            raise ValueError(f"Classe deve ser 0 e caixa deve ter área positiva: {path}:{index}")
        if not (
            0 <= x - width / 2 + 1e-6
            and x + width / 2 <= 1 + 1e-6
            and 0 <= y - height / 2 + 1e-6
            and y + height / 2 <= 1 + 1e-6
        ):
            raise ValueError(f"Caixa fora da imagem: {path}:{index}")
        boxes.append((x, y, width, height))
    return boxes


def extract_frames(
    root: Path,
    source: Path,
    session_id: str,
    camera_id: str,
    lote_id: str | None,
    sample_seconds: float,
    captured_at: str | None = None,
    image_format: str = "png",
) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", session_id):
        raise ValueError("session-id deve conter apenas letras, números, hífen ou sublinhado.")
    if source.is_dir():
        raise ValueError("Extraia um vídeo ou uma imagem por sessão para preservar sua origem.")
    if image_format not in {"png", "jpg"}:
        raise ValueError("Formato de extração deve ser png ou jpg.")
    destination = root / "data/interim" / session_id
    if destination.exists():
        raise FileExistsError("Sessão já existe; escolha outro ID para preservar os originais.")
    destination.mkdir(parents=True)
    manifest = destination / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as handle:
        for frame in iter_frames(source, sample_seconds, camera_id, lote_id, captured_at):
            if frame.error:
                raise ValueError(frame.error)
            offset = frame.metadata.get("offset_ms") or 0
            image_path = (
                destination
                / f"frame-{offset:09d}ms-{frame.metadata['quadro_id'][:16]}.{image_format}"
            )
            write_image(image_path, frame.image)
            row = {
                **frame.metadata,
                "imagem": image_path.relative_to(root).as_posix(),
                "rotulo": image_path.with_suffix(".txt").relative_to(root).as_posix(),
                "grupo_origem": session_id,
                "qualidade": "pendente",
                "status_revisao": "rascunho",
                "tipo_amostra": "rotina",
                "imagem_sha256": file_hash(image_path),
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return manifest


def split_groups(groups: set[str], ratios=(0.7, 0.15, 0.15), seed: int = 42) -> dict[str, str]:
    if len(groups) < 3:
        raise ValueError(
            "São necessários pelo menos três grupos independentes para train/val/test."
        )
    if (
        len(ratios) != 3
        or any(not math.isfinite(r) or r <= 0 for r in ratios)
        or not math.isclose(sum(ratios), 1)
    ):
        raise ValueError("Proporções devem ser positivas e somar 1.")
    ordered = sorted(groups)
    random.Random(seed).shuffle(ordered)
    n = len(ordered)
    n_train = max(1, min(n - 2, round(n * ratios[0])))
    n_val = max(1, min(n - n_train - 1, round(n * ratios[1])))
    return {
        group: "train" if i < n_train else "val" if i < n_train + n_val else "test"
        for i, group in enumerate(ordered)
    }


def prepare_dataset(
    root: Path, manifest: Path, output: Path, seed: int = 42, ratios=(0.7, 0.15, 0.15)
) -> dict:
    if output.exists():
        raise FileExistsError(
            "Dataset já existe. Escolha outra versão para preservar as partições."
        )
    records = read_jsonl(manifest)
    if not records:
        raise ValueError("Manifesto vazio.")
    validated = []
    hashes = set()
    frame_ids = set()
    for row in records:
        if row.get("status_revisao") != "revisada" or row.get("qualidade") != "avaliavel":
            raise ValueError("Todo quadro do dataset deve estar revisado e avaliável.")
        group = row.get("grupo_origem")
        if not isinstance(group, str) or not group.strip():
            raise ValueError("Informe grupo_origem para cada imagem.")
        image_path = resolve_path(root, row["imagem"])
        label_path = resolve_path(root, row["rotulo"])
        boxes = read_labels(label_path)  # Negativos precisam de arquivo explicitamente vazio.
        image = read_image(image_path)
        if image is None:
            raise ValueError(f"Imagem não decodificada: {image_path}")
        image_hash = file_hash(image_path)
        pixel_hash = fingerprint([image.shape, hashlib.sha256(image.tobytes()).hexdigest()])
        frame_id = row.get("quadro_id") or image_hash
        if pixel_hash in hashes or frame_id in frame_ids:
            raise ValueError("Imagem ou quadro duplicado no manifesto; revise as amostras.")
        hashes.add(pixel_hash)
        frame_ids.add(frame_id)
        manual_counts = row.get("contagens_por_nivel")
        if manual_counts is not None and (
            not isinstance(manual_counts, dict)
            or any(type(v) is not int or v < 0 for v in manual_counts.values())
            or sum(manual_counts.values()) > len(boxes)
        ):
            raise ValueError(
                "Contagens manuais por nível devem ser inteiras e coerentes com as caixas."
            )
        validated.append((row, image_path, label_path, image_hash, frame_id))
    assignment = split_groups({row["grupo_origem"] for row in records}, ratios, seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Somente arquivos criados nesta pasta temporária são limpos automaticamente.
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temp:
        staging = Path(temp) / "dataset"
        for split in SPLITS:
            (staging / "images" / split).mkdir(parents=True)
            (staging / "labels" / split).mkdir(parents=True)
        prepared = []
        for i, (row, image_path, label_path, image_hash, frame_id) in enumerate(validated):
            split = assignment[row["grupo_origem"]]
            stem = f"{i:06d}-{image_hash[:12]}"
            image_rel = Path("images") / split / f"{stem}{image_path.suffix.lower()}"
            label_rel = Path("labels") / split / f"{stem}.txt"
            shutil.copy2(image_path, staging / image_rel)
            shutil.copy2(label_path, staging / label_rel)
            prepared.append(
                {
                    **row,
                    "quadro_id": frame_id,
                    "split": split,
                    "imagem": image_rel.as_posix(),
                    "rotulo": label_rel.as_posix(),
                    "imagem_sha256": image_hash,
                    "rotulo_sha256": file_hash(label_path),
                }
            )
        metadata = {
            "version": output.name,
            "seed": seed,
            "ratios": list(ratios),
            "dataset_sha256": fingerprint(prepared),
            "group_assignment": assignment,
            "counts": {split: sum(r["split"] == split for r in prepared) for split in SPLITS},
        }
        (staging / "manifest.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in prepared),
            encoding="utf-8",
        )
        (staging / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "dataset.yaml").write_text(
            yaml.safe_dump(
                {
                    "path": str(output.resolve()),
                    "train": "images/train",
                    "val": "images/val",
                    "test": "images/test",
                    "names": {0: "galinha"},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        publish_dataset(staging, output)
    return metadata


def validate_dataset(yaml_path: Path) -> tuple[Path, list[dict], dict]:
    raw = load_yaml(yaml_path)
    dataset_root = resolve_path(yaml_path.parent, raw["path"])
    if raw.get("names") != {0: "galinha"} or any(raw.get(s) != f"images/{s}" for s in SPLITS):
        raise ValueError("Use o dataset de uma classe produzido por prepare-dataset.")
    records = read_jsonl(dataset_root / "manifest.jsonl")
    metadata = json.loads((dataset_root / "metadata.json").read_text(encoding="utf-8"))
    if fingerprint(records) != metadata["dataset_sha256"]:
        raise ValueError("Manifesto do dataset foi alterado. Prepare uma nova versão.")
    seen_groups = {}
    expected = set()
    for row in records:
        split = row["split"]
        if split not in SPLITS:
            raise ValueError("Partição inválida no dataset.")
        group = row["grupo_origem"]
        if group in seen_groups and seen_groups[group] != split:
            raise ValueError("Grupo de origem aparece em mais de uma partição.")
        seen_groups[group] = split
        for key, hash_key, folder in (
            ("imagem", "imagem_sha256", "images"),
            ("rotulo", "rotulo_sha256", "labels"),
        ):
            path = resolve_path(dataset_root, row[key])
            if path.parent != (dataset_root / folder / split).resolve():
                raise ValueError("Caminho do arquivo não corresponde à partição do manifesto.")
            if file_hash(path) != row[hash_key]:
                raise ValueError(f"Dataset foi alterado: {row[key]}. Prepare outra versão.")
            expected.add(path)
        read_labels(dataset_root / row["rotulo"])
    actual = {
        p.resolve()
        for folder in ("images", "labels")
        for p in (dataset_root / folder).rglob("*")
        if p.is_file()
    }
    if actual != expected or any(not any(r["split"] == s for r in records) for s in SPLITS):
        raise ValueError("Dataset possui arquivos extras, ausentes ou partição vazia.")
    return dataset_root, records, metadata


def export_crops(
    root: Path, manifest: Path, output: Path, roi: tuple, predictions_dir: Path | None = None
) -> Path:
    """Recortes sem perda, preservando o grupo e deixando anotações pendentes."""
    InferenceConfig(roi=roi)
    if output.exists():
        raise FileExistsError("Pasta de recortes já existe. Escolha outra versão.")
    records = read_jsonl(manifest)
    if not records:
        raise ValueError("Manifesto de origem vazio.")
    output.parent.mkdir(parents=True, exist_ok=True)
    cropped_records = []
    with tempfile.TemporaryDirectory(prefix=f".{output.name}-", dir=output.parent) as temp:
        staging = Path(temp) / "crops"
        staging.mkdir()
        for index, row in enumerate(records):
            image_path = resolve_path(root, row["imagem"])
            if row.get("imagem_sha256") and file_hash(image_path) != row["imagem_sha256"]:
                raise ValueError("Quadro de origem foi alterado; prepare outra versão.")
            image = read_image(image_path)
            if image is None:
                raise ValueError(f"Quadro não decodificado: {image_path}")
            box = roi_pixels(image, roi)
            target = staging / f"crop-{index:04d}-{fingerprint(row['quadro_id'])[:12]}.png"
            write_image(target, image[box[1] : box[3], box[0] : box[2]])
            proposals = []
            if predictions_dir:
                prediction_path = predictions_dir / f"{image_path.stem}.json"
                if prediction_path.is_file():
                    prediction = json.loads(prediction_path.read_text(encoding="utf-8"))
                    if prediction["quadro_id"] != row["quadro_id"]:
                        raise ValueError("Previsão não corresponde ao quadro de origem.")
                    for detection in prediction["detections"]:
                        b = detection["bbox_px"]
                        clipped = [
                            max(b[0], box[0]),
                            max(b[1], box[1]),
                            min(b[2], box[2]),
                            min(b[3], box[3]),
                        ]
                        if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
                            continue
                        proposals.append(
                            {
                                "bbox_px": [
                                    clipped[0] - box[0],
                                    clipped[1] - box[1],
                                    clipped[2] - box[0],
                                    clipped[3] - box[1],
                                ],
                                "confidence": detection["confidence"],
                                "partial": list(b) != clipped,
                                "source_class": detection["class_name"],
                                "source_model": prediction.get("modelo_versao"),
                            }
                        )
            final = output / target.name
            cropped_records.append(
                {
                    **row,
                    "quadro_id": fingerprint({"parent": row["quadro_id"], "roi_px": box}),
                    "parent_quadro_id": row["quadro_id"],
                    "parent_imagem": row["imagem"],
                    "imagem": final.relative_to(root).as_posix(),
                    "rotulo": final.with_suffix(".txt").relative_to(root).as_posix(),
                    "imagem_sha256": file_hash(target),
                    "roi_px": list(box),
                    "roi_version": fingerprint(roi),
                    "proposals": proposals,
                    "qualidade": "pendente",
                    "status_revisao": "rascunho",
                }
            )
        (staging / "manifest.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in cropped_records),
            encoding="utf-8",
        )
        publish_dataset(staging, output)
    return output / "manifest.jsonl"
