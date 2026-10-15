"""Execução limitada e visualização de previsões no notebook."""

import csv
import json
import uuid
from contextlib import closing
from dataclasses import dataclass, replace
from html import escape
from itertools import islice
from pathlib import Path

import yaml

from .capture import iter_frames, read_image, write_image
from .cli import configure_runtime
from .config import InferenceConfig, resolve_path
from .detector import YOLODetector, prepare_model
from .domain import Frame
from .pipeline import Pipeline, annotate
from .storage import ResultStore
from .zones import load_zones

MODE_LABELS = {"standard": "Direto", "sliced": "SAHI"}


@dataclass
class PreviewRun:
    output: Path
    source: Path
    frames: list[Frame]
    configs: dict[str, InferenceConfig]
    results: dict[str, list[dict]]
    annotated: dict[str, list[Path]]


def run_preview(
    root: Path,
    source: str | Path,
    config: InferenceConfig,
    *,
    max_frames: int = 6,
    modes: tuple[str, ...] = ("standard", "sliced"),
    camera_id: str | None = None,
    lote_id: str | None = None,
    captured_at: str | None = None,
) -> PreviewRun:
    """Rodar o pipeline real e salvar uma execução nova; a visualização é separada."""
    if type(max_frames) is not int or not 1 <= max_frames <= 60:
        raise ValueError("Selecione de 1 a 60 quadros para a prévia.")
    if not modes or len(set(modes)) != len(modes) or any(m not in MODE_LABELS for m in modes):
        raise ValueError("Modos aceitos: standard e sliced, sem repetições.")
    root = root.resolve()
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Informe a raiz do projeto, contendo pyproject.toml.")
    source = resolve_path(root, source)
    if not source.exists():
        raise FileNotFoundError(f"Entrada não encontrada: {source}. Confira o campo Entrada.")
    configure_runtime(root)
    with closing(
        iter_frames(source, config.sample_seconds, camera_id, lote_id, captured_at)
    ) as generator:
        frames = list(islice(generator, max_frames))
    if not frames or any(frame.image is None for frame in frames):
        raise ValueError("A entrada contém quadros que não puderam ser decodificados.")
    if not config.weights:
        prepare_model(root, config.model)
    detector = YOLODetector(config, root)
    zones = load_zones(resolve_path(root, config.zones)) if config.zones else None
    output = root / "outputs" / f"notebook-{uuid.uuid4().hex[:12]}"
    output.mkdir(parents=True, exist_ok=False)
    run = PreviewRun(output, source, frames, {}, {}, {})
    with (output / "frames.jsonl").open("w", encoding="utf-8") as handle:
        for index, frame in enumerate(frames):
            path = output / "frames" / f"frame-{index:02d}.png"
            write_image(path, frame.image)
            handle.write(
                json.dumps(
                    {**frame.metadata, "frame_salvo": path.relative_to(output).as_posix()},
                    ensure_ascii=False,
                )
                + "\n"
            )
    for mode in modes:
        settings = replace(config, slicing=replace(config.slicing, enabled=mode == "sliced"))
        run.configs[mode] = settings
        detector.config = settings
        pipeline = Pipeline(settings, detector, zones)
        folder = output / mode
        folder.mkdir()
        (folder / "config.yaml").write_text(
            yaml.safe_dump(settings.snapshot(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        run.results[mode], run.annotated[mode] = [], []
        with ResultStore(resolve_path(root, config.database), folder) as store:
            for index, frame in enumerate(frames):
                result = pipeline.process(frame)
                store.save(result)
                path = folder / "annotated" / f"frame-{index:02d}.jpg"
                write_image(path, annotate(frame.image, result, zones))
                run.results[mode].append(result)
                run.annotated[mode].append(path)
                print(
                    f"{MODE_LABELS[mode]} · quadro {index + 1}/{len(frames)} · "
                    f"{result['status']} · caixas: {result['quantidade_aves_visiveis']}",
                    flush=True,
                )
    summary = preview_rows(run)
    with (output / "comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    (output / "run.json").write_text(
        json.dumps(
            {
                "source": str(source),
                "frames": len(frames),
                "max_frames": max_frames,
                "configs": {mode: cfg.snapshot() for mode, cfg in run.configs.items()},
                "models": {mode: values[0]["modelo"] for mode, values in run.results.items()},
                "summary": summary,
                "counts_are_unique_animals": False,
                "ground_truth_available": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return run


def preview_rows(run: PreviewRun) -> list[dict]:
    rows = []
    for index, frame in enumerate(run.frames):
        offset = frame.metadata.get("offset_ms")
        for mode, results in run.results.items():
            value = results[index]
            rows.append(
                {
                    "quadro": index + 1,
                    "instante_s": round(offset / 1000, 3) if offset is not None else None,
                    "modo": MODE_LABELS[mode],
                    "caixas_previstas": value["quantidade_aves_visiveis"],
                    "status": value["status"],
                    "confianca_maxima": max(
                        (d["confidence"] for d in value["detections"]), default=None
                    ),
                    "inferencia_ms": value["inference_ms"],
                }
            )
    return rows


def preview_figure(run: PreviewRun, index: int = 0):
    """Ler os resultados da execução e desenhar; nenhuma inferência é feita aqui."""
    import cv2
    import matplotlib.pyplot as plt

    if not 0 <= index < len(run.frames):
        raise IndexError("Quadro fora da prévia disponível.")
    with plt.ioff():
        figure, axes = plt.subplots(
            1, 1 + len(run.results), figsize=(8 * (1 + len(run.results)), 5)
        )
        axes[0].imshow(cv2.cvtColor(run.frames[index].image, cv2.COLOR_BGR2RGB))
        axes[0].set_title("Original")
        for axis, mode in zip(axes[1:], run.results, strict=True):
            result = run.results[mode][index]
            image = read_image(run.annotated[mode][index])
            axis.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            axis.set_title(
                f"{MODE_LABELS[mode]} · caixas: {result['quantidade_aves_visiveis']}\n"
                f"Confiança mínima: {run.configs[mode].confidence:.2f} · {result['status']}"
            )
        for axis in axes:
            axis.axis("off")
        offset = run.frames[index].metadata.get("offset_ms")
        instant = f"{offset / 1000:.2f} s" if offset is not None else "imagem"
        figure.suptitle(
            f"Quadro {index + 1}/{len(run.frames)} · {instant} · {run.source.name}",
            y=0.99,
            fontsize=13,
        )
        figure.tight_layout(rect=(0, 0, 1, 0.88))
    return figure


def preview_viewer(run: PreviewRun):
    """Controle de navegação entre quadros já processados."""
    import ipywidgets as widgets
    import matplotlib.pyplot as plt
    from IPython.display import clear_output, display

    slider = widgets.IntSlider(
        value=1, min=1, max=len(run.frames), description="Quadro:", continuous_update=False
    )
    output = widgets.Output()

    def redraw(change):
        with output:
            clear_output(wait=True)
            figure = preview_figure(run, change["new"] - 1)
            display(figure)
            plt.close(figure)

    slider.observe(redraw, names="value")
    redraw({"new": 1})
    return widgets.VBox(
        [
            widgets.HTML("<b>Mova o controle para visualizar outro quadro já processado.</b>"),
            slider,
            output,
        ]
    )


def preview_table(run: PreviewRun):
    from IPython.display import HTML

    rows = preview_rows(run)
    headers = "".join(f"<th>{escape(key)}</th>" for key in rows[0])
    body = ""
    for row in rows:
        values = []
        for value in row.values():
            text = "—" if value is None else f"{value:.3f}" if isinstance(value, float) else value
            values.append(f"<td>{escape(str(text))}</td>")
        body += "<tr>" + "".join(values) + "</tr>"
    return HTML(
        "<p>Caixas previstas não são uma contagem validada de animais. "
        "Não some quadros como aves únicas.</p>"
        f"<table><thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table>"
    )
