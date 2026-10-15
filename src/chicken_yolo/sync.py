"""Fila de sincronização durável; confirmar somente IDs aceitos pelo servidor."""

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import requests

from .domain import utc_now


def sync_pending(
    database: Path, url: str, token: str | None = None, batch_size: int = 100, post=None
) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Endpoint deve usar HTTPS; HTTP é permitido apenas em localhost.")
    if parsed.username or parsed.password or not parsed.hostname or batch_size < 1:
        raise ValueError("Endpoint ou tamanho de lote inválido.")
    if not database.is_file():
        raise FileNotFoundError("Histórico local não encontrado.")
    with sqlite3.connect(database) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS sync_receipts (
            analise_id TEXT PRIMARY KEY, synced_at TEXT NOT NULL)""")
        rows = connection.execute(
            """SELECT a.analise_id, a.payload FROM analyses a
            LEFT JOIN sync_receipts s ON a.analise_id = s.analise_id
            WHERE s.analise_id IS NULL ORDER BY a.processado_em, a.analise_id LIMIT ?""",
            (batch_size,),
        ).fetchall()
        accepted = []
        if rows:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            response = (post or requests.post)(
                url,
                json={"schema_version": 1, "analyses": [json.loads(row[1]) for row in rows]},
                headers=headers,
                timeout=30,
                allow_redirects=False,
            )
            response.raise_for_status()
            if not 200 <= response.status_code < 300:
                raise ValueError("Sincronização requer resposta HTTP 2xx sem redirecionamento.")
            accepted = response.json().get("accepted_analysis_ids")
            sent = {row[0] for row in rows}
            if not isinstance(accepted, list) or any(
                not isinstance(v, str) or v not in sent for v in accepted
            ):
                raise ValueError("Servidor deve confirmar apenas IDs presentes no lote enviado.")
            accepted = sorted(set(accepted))
            connection.executemany(
                "INSERT OR IGNORE INTO sync_receipts VALUES (?, ?)",
                [(value, utc_now()) for value in accepted],
            )
        pending = connection.execute("""SELECT count(*) FROM analyses a
            LEFT JOIN sync_receipts s ON a.analise_id = s.analise_id
            WHERE s.analise_id IS NULL""").fetchone()[0]
    return {"sent": len(rows), "accepted": len(accepted), "pending": pending}
