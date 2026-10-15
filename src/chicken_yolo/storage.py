"""Histórico local idempotente e exportação incremental por análise."""

import csv
import json
import sqlite3
import uuid
from pathlib import Path

from .domain import utc_now

CSV_FIELDS = [
    "analise_id",
    "quadro_id",
    "camera_id",
    "lote_id",
    "capturado_em",
    "nivel_id",
    "status",
    "motivo_status",
    "quantidade_aves_visiveis",
    "total_atribuido_quadro",
    "quantidade_sem_nivel",
    "percentual_nivel",
    "modelo_versao",
    "zonas_versao",
    "regra_atribuicao_versao",
    "limiar_confianca",
    "processado_em",
    "inference_ms",
    "processing_ms",
]


def level_rows(result: dict):
    levels = result["contagens_por_nivel"]
    for level in levels or [None]:
        yield {
            **{key: result.get(key) for key in CSV_FIELDS},
            "nivel_id": level,
            "quantidade_aves_visiveis": levels[level]
            if level
            else result["quantidade_aves_visiveis"],
            "percentual_nivel": result["percentuais_por_nivel"].get(level),
        }


class ResultStore:
    def __init__(self, database: Path, output: Path):
        database.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        self.output = output
        self.connection = sqlite3.connect(database)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, occurred_at TEXT NOT NULL, type TEXT NOT NULL,
            payload TEXT NOT NULL)""")
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS analyses (
            analise_id TEXT PRIMARY KEY, quadro_id TEXT NOT NULL, processado_em TEXT NOT NULL,
            status TEXT NOT NULL, payload TEXT NOT NULL)""")
        self.connection.execute("CREATE INDEX IF NOT EXISTS analyses_frame ON analyses(quadro_id)")
        self.jsonl = (output / "results.jsonl").open("a", encoding="utf-8")
        csv_path = output / "counts.csv"
        has_header = csv_path.exists() and csv_path.stat().st_size > 0
        self.csv_file = csv_path.open("a", encoding="utf-8", newline="")
        self.writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS)
        if not has_header:
            self.writer.writeheader()

    def save(self, result: dict) -> bool:
        payload = json.dumps(result, ensure_ascii=False, allow_nan=False)
        with self.connection:
            cursor = self.connection.execute(
                "INSERT OR IGNORE INTO analyses VALUES (?, ?, ?, ?, ?)",
                (
                    result["analise_id"],
                    result["quadro_id"],
                    result["processado_em"],
                    result["status"],
                    payload,
                ),
            )
        if not cursor.rowcount:
            return False
        self.jsonl.write(payload + "\n")
        self.jsonl.flush()
        self.writer.writerows(level_rows(result))
        self.csv_file.flush()
        return True

    def close(self):
        self.jsonl.close()
        self.csv_file.close()
        self.connection.close()

    def record_event(self, event_type: str, metadata: dict) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    utc_now(),
                    event_type,
                    json.dumps(metadata, ensure_ascii=False, allow_nan=False),
                ),
            )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
