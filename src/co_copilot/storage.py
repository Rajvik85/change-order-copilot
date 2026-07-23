"""Per-session atomic persistence and portable escape-hatch bundles."""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from co_copilot.models import PipelineResult
from co_copilot.pipeline import snapshot_payload

_SESSION_ID = re.compile(r"^[a-f0-9]{32}$")


def session_artifact_dir(session_id: str) -> Path:
    """Return a process-independent, isolated session folder in system temp."""
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("Invalid session identifier.")
    path = Path(tempfile.gettempdir()) / "co_copilot_sessions" / session_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write(path: Path, data: bytes) -> None:
    """Write, flush, fsync, and replace so partial exports are never visible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def persist_snapshot(folder: Path, result: PipelineResult, version: str) -> Path:
    """Persist computed results for crash/rerun recovery in one session."""
    path = folder / "latest_snapshot.json"
    payload = snapshot_payload(result, version)
    atomic_write(
        path,
        json.dumps(payload, indent=2, default=str).encode("utf-8"),
    )
    return path


def load_snapshot(folder: Path) -> dict[str, Any] | None:
    """Load a safe JSON recovery snapshot if the session owns one."""
    path = folder / "latest_snapshot.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_zip(result: PipelineResult, version: str) -> bytes:
    """Return every computed artifact as a self-contained in-memory ZIP."""
    payload = snapshot_payload(result, version)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json", json.dumps(payload["manifest"], indent=2, default=str)
        )
        archive.writestr(
            "extracted_facts.json",
            json.dumps(payload["extractions"], indent=2, default=str),
        )
        archive.writestr(
            "compliance.json",
            json.dumps(payload["compliance"], indent=2, default=str),
        )
        archive.writestr(
            "portfolio_summary.json",
            json.dumps(payload["analytics"], indent=2, default=str),
        )
        archive.writestr(
            "co_register.csv",
            result.analytics["register"].to_csv(index=False),
        )
    return buffer.getvalue()
