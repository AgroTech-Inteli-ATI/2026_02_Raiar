"""Ensaio local com entrada representativa, atrasos e amostras de recursos."""

import json
import math
import platform
import statistics
import threading
import time
from pathlib import Path

import psutil

from .capture import iter_frames
from .domain import utc_now
from .evaluation import _p95
from .pipeline import Pipeline


def benchmark(
    pipeline: Pipeline,
    source: Path,
    output: Path,
    duration_seconds: float,
    interval_seconds: float,
    camera_id=None,
    lote_id=None,
) -> dict:
    if any(not math.isfinite(v) or v <= 0 for v in (duration_seconds, interval_seconds)):
        raise ValueError("Duração e intervalo devem ser positivos e finitos.")
    output.mkdir(parents=True, exist_ok=False)
    stop = threading.Event()
    resources = []

    def sample_resources():
        psutil.cpu_percent()
        while not stop.wait(1):
            memory = psutil.virtual_memory()
            resources.append(
                {
                    "at": utc_now(),
                    "cpu_percent": psutil.cpu_percent(),
                    "available_memory_percent": 100 * memory.available / memory.total,
                }
            )

    monitor = threading.Thread(target=sample_resources, daemon=True)
    monitor.start()
    frames = iter(iter_frames(source, interval_seconds, camera_id, lote_id))
    times = []
    processing = []
    statuses = {"valido": 0, "imagem_inadequada": 0, "falha_processamento": 0}
    missed_intervals = 0
    start = next_capture = time.perf_counter()
    try:
        with (output / "frames.jsonl").open("w", encoding="utf-8") as handle:
            while time.perf_counter() - start < duration_seconds:
                delay = next_capture - time.perf_counter()
                if delay > 0:
                    time.sleep(min(delay, max(0, duration_seconds - (time.perf_counter() - start))))
                if time.perf_counter() - start >= duration_seconds:
                    break
                try:
                    frame = next(frames)
                except StopIteration:
                    frames = iter(iter_frames(source, interval_seconds, camera_id, lote_id))
                    frame = next(frames)
                result = pipeline.process(frame)
                handle.write(json.dumps(result, ensure_ascii=False, allow_nan=False) + "\n")
                statuses[result["status"]] += 1
                if result["inference_ms"] is not None:
                    times.append(result["inference_ms"])
                processing.append(result["processing_ms"])
                next_capture += interval_seconds
                now = time.perf_counter()
                if now > next_capture:
                    missed = int((now - next_capture) // interval_seconds) + 1
                    missed_intervals += missed
                    next_capture += missed * interval_seconds
    finally:
        stop.set()
        monitor.join(timeout=2)
        frames.close()
    cpu_windows = [
        statistics.mean(r["cpu_percent"] for r in resources[i : i + 300])
        for i in range(0, len(resources), 300)
    ]
    report = {
        "at": utc_now(),
        "platform": platform.platform(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_bytes": psutil.virtual_memory().total,
        "duration_seconds": time.perf_counter() - start,
        "interval_seconds": interval_seconds,
        "model": pipeline.detector.metadata,
        "config": pipeline.config.snapshot(),
        "statuses": statuses,
        "missed_intervals": missed_intervals,
        "inference_p95_ms": _p95(times),
        "processing_p95_ms": _p95(processing),
        "inference_within_80_percent_interval": sum(v <= interval_seconds * 800 for v in times)
        / len(times)
        if times
        else None,
        "cpu_mean_per_window_percent": cpu_windows,
        "min_available_memory_percent": min(
            (r["available_memory_percent"] for r in resources), default=None
        ),
        "resource_samples": resources,
        "limitations": [
            "Reprodução de arquivos locais; não mede captura ao vivo nem rede.",
            "Janelas de CPU são de até cinco minutos; a última pode ser parcial.",
            "Temperatura e redução de frequência exigem inspeção no dispositivo.",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
