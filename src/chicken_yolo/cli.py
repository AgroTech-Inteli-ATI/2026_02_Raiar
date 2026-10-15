"""Interface de linha de comando para preparar, detectar, treinar e avaliar."""

import argparse
import json
import os
import sys
import uuid
from dataclasses import replace
from pathlib import Path

from .benchmark import benchmark
from .capture import iter_frames, write_image
from .config import load_inference, resolve_path
from .dataset import export_crops, extract_frames, prepare_dataset
from .detector import YOLODetector, prepare_model
from .evaluation import evaluate_dataset
from .pipeline import Pipeline, annotate
from .storage import ResultStore
from .sync import sync_pending
from .training import export_model, train_model
from .zones import load_zones


def configure_runtime(root: Path):
    for key, folder in (
        ("YOLO_CONFIG_DIR", "ultralytics"),
        ("MPLCONFIGDIR", "matplotlib"),
        ("TORCH_HOME", "torch"),
    ):
        path = root / ".cache" / folder
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(key, str(path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chicken-yolo",
        description="Detecção e contagem de aves visíveis — Raiar",
        epilog=(
            "Exemplos:\n"
            "  chicken-yolo prepare-model\n"
            "  chicken-yolo predict --source data/raw/video.mp4\n"
            "  chicken-yolo predict --help"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Raiz do repositório.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-model", help="Baixar e registrar pesos pré-treinados.")
    prepare.add_argument(
        "model",
        choices=["poultryvision", "coco"],
        nargs="?",
        default="poultryvision",
        help="Modelo pré-treinado (padrão: poultryvision).",
    )
    predict = commands.add_parser("predict", help="Processar imagem, vídeo ou pasta local.")
    predict.add_argument("--source", type=Path, required=True)
    predict.add_argument("--camera-id")
    predict.add_argument("--lote-id")
    predict.add_argument(
        "--captured-at", help="Horário da imagem ou início do vídeo, incluindo fuso."
    )
    for sub in (
        predict,
        commands.add_parser("evaluate", help="Avaliar usando referências revisadas."),
        commands.add_parser("benchmark", help="Medir tempo e recursos com entrada local."),
    ):
        sub.add_argument("--config", type=Path, default=Path("configs/inference.yaml"))
        sub.add_argument("--weights", help="Checkpoint próprio ou artefato exportado.")
        sub.add_argument("--model", choices=["poultryvision", "coco"])
        sub.add_argument("--zones", help="YAML de zonas calibradas.")
        sub.add_argument("--output", type=Path)
    evaluate = commands.choices["evaluate"]
    evaluate.add_argument("--dataset", type=Path, required=True)
    evaluate.add_argument("--split", choices=["val", "test"], default="val")
    bench = commands.choices["benchmark"]
    bench.add_argument("--source", type=Path, required=True)
    bench.add_argument("--duration-seconds", type=float, default=60)
    bench.add_argument("--interval-seconds", type=float)
    bench.add_argument("--camera-id")
    bench.add_argument("--lote-id")
    sync = commands.add_parser("sync", help="Enviar resultados pendentes ao backend configurado.")
    sync.add_argument("--database", type=Path, default=Path("outputs/results.sqlite3"))
    sync.add_argument("--url", required=True)
    sync.add_argument("--token-env", default="RAIAR_SYNC_TOKEN")
    sync.add_argument("--batch-size", type=int, default=100)
    extract = commands.add_parser(
        "extract", help="Extrair quadros e preservar metadados de origem."
    )
    extract.add_argument("--source", type=Path, required=True)
    extract.add_argument("--session-id", required=True)
    extract.add_argument("--camera-id", required=True)
    extract.add_argument("--lote-id", help="ID real do lote; desconhecido permanece nulo.")
    extract.add_argument("--sample-seconds", type=float, default=1)
    extract.add_argument("--captured-at")
    extract.add_argument("--image-format", choices=["png", "jpg"], default="png")
    crop = commands.add_parser("crop", help="Exportar recortes PNG e preservar a origem.")
    crop.add_argument("--manifest", type=Path, required=True)
    crop.add_argument("--output", type=Path, required=True)
    crop.add_argument("--roi", type=float, nargs=4, required=True)
    crop.add_argument("--predictions-dir", type=Path)
    dataset = commands.add_parser(
        "prepare-dataset", help="Validar rótulos e separar grupos de origem."
    )
    dataset.add_argument("--manifest", type=Path, required=True)
    dataset.add_argument("--output", type=Path, default=Path("data/processed/galinhas-v1"))
    dataset.add_argument("--seed", type=int, default=42)
    dataset.add_argument("--ratios", type=float, nargs=3, default=(0.7, 0.15, 0.15))
    train = commands.add_parser("train", help="Ajustar pesos pré-treinados com dataset próprio.")
    train.add_argument("--config", type=Path, default=Path("configs/training.yaml"))
    export = commands.add_parser("export", help="Exportar checkpoint para ONNX ou NCNN.")
    export.add_argument("--weights", type=Path, required=True)
    export.add_argument("--format", choices=["onnx", "ncnn"], required=True)
    export.add_argument("--imgsz", type=int, default=640)
    return parser


def run(args) -> tuple[dict, int]:
    root = args.root.resolve()
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Execute na raiz do repositório ou informe --root.")
    configure_runtime(root)
    if args.command == "prepare-model":
        return prepare_model(root, args.model), 0
    if args.command == "crop":
        path = export_crops(
            root,
            resolve_path(root, args.manifest),
            resolve_path(root, args.output),
            tuple(args.roi),
            resolve_path(root, args.predictions_dir) if args.predictions_dir else None,
        )
        return {"manifest": str(path)}, 0
    if args.command == "sync":
        return sync_pending(
            resolve_path(root, args.database),
            args.url,
            os.environ.get(args.token_env),
            args.batch_size,
        ), 0
    if args.command == "extract":
        manifest = extract_frames(
            root,
            resolve_path(root, args.source),
            args.session_id,
            args.camera_id,
            args.lote_id,
            args.sample_seconds,
            args.captured_at,
            args.image_format,
        )
        return {"manifest": str(manifest)}, 0
    if args.command == "prepare-dataset":
        return prepare_dataset(
            root,
            resolve_path(root, args.manifest),
            resolve_path(root, args.output),
            args.seed,
            args.ratios,
        ), 0
    if args.command == "train":
        return train_model(resolve_path(root, args.config)), 0
    if args.command == "export":
        return {
            "artifact": export_model(resolve_path(root, args.weights), args.format, args.imgsz)
        }, 0
    config_path = resolve_path(root, args.config)
    config, config_root = load_inference(config_path)
    if config_root != root:
        raise ValueError("Configuração pertence a outro projeto.")
    overrides = {
        key: getattr(args, key)
        for key in ("weights", "model", "zones")
        if getattr(args, key) is not None
    }
    config = replace(config, **overrides)
    zones = load_zones(resolve_path(root, config.zones)) if config.zones else None
    detector = YOLODetector(config, root)
    if args.command == "benchmark":
        output = (
            resolve_path(root, args.output)
            if args.output
            else root / "reports/generated" / f"benchmark-{uuid.uuid4().hex[:12]}"
        )
        report = benchmark(
            Pipeline(config, detector, zones),
            resolve_path(root, args.source),
            output,
            args.duration_seconds,
            args.interval_seconds if args.interval_seconds is not None else config.sample_seconds,
            args.camera_id,
            args.lote_id,
        )
        return {"report": str(output / "report.json"), **report}, int(
            report["statuses"]["falha_processamento"] > 0
        )
    if args.command == "evaluate":
        output = (
            resolve_path(root, args.output)
            if args.output
            else root / "reports/generated" / f"evaluation-{uuid.uuid4().hex[:12]}"
        )
        report = evaluate_dataset(
            config, detector, resolve_path(root, args.dataset), output, zones, args.split
        )
        return {"report": str(output / "report.json"), **report}, int(
            report["coverage"]["falha_processamento"] > 0
        )
    output = (
        resolve_path(root, args.output)
        if args.output
        else resolve_path(root, config.output_dir) / f"predict-{uuid.uuid4().hex[:12]}"
    )
    if output.exists():
        raise FileExistsError("Pasta de saída já existe. Escolha outra para preservar a execução.")
    pipeline = Pipeline(config, detector, zones)
    counts = {"valido": 0, "imagem_inadequada": 0, "falha_processamento": 0}
    with ResultStore(resolve_path(root, config.database), output) as store:
        frames = iter_frames(
            resolve_path(root, args.source),
            config.sample_seconds,
            args.camera_id,
            args.lote_id,
            args.captured_at,
        )
        while True:
            try:
                frame = next(frames)
            except StopIteration:
                break
            except Exception as exc:
                store.record_event(
                    "falha_captura",
                    {
                        "arquivo_ref": str(args.source),
                        "camera_id": args.camera_id,
                        "lote_id": args.lote_id,
                        "error": str(exc),
                    },
                )
                raise
            result = pipeline.process(frame)
            store.save(result)
            counts[result["status"]] += 1
            if config.save_annotated and frame.image is not None:
                write_image(
                    output / "annotated" / f"{result['quadro_id'][:20]}.jpg",
                    annotate(frame.image, result, zones),
                )
    return {"output": str(output), "frames": sum(counts.values()), **counts}, int(
        counts["falha_processamento"] > 0
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result, code = run(args)
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return code
