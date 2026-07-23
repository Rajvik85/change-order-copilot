"""Per-session atomic persistence and portable escape-hatch bundles."""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

from co_copilot.analytics import portfolio_analytics
from co_copilot.models import (
    ComplianceCheck,
    ComplianceResult,
    Document,
    ExtractedField,
    ExtractionResult,
    PipelineResult,
    TextSpan,
)
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


def restore_pipeline_result(
    folder: Path, metadata: dict[str, Any]
) -> PipelineResult | None:
    """Reconstruct safe typed results from the owning session's JSON snapshot."""
    payload = load_snapshot(folder)
    if payload is None:
        return None
    documents = tuple(
        Document(
            document_id=item["document_id"],
            filename=item["filename"],
            path=(
                Path(item["path"])
                if item.get("path") and Path(item["path"]).exists()
                else None
            ),
            text=item["text"],
            sections=item["sections"],
            warnings=tuple(item.get("warnings", [])),
            content_hash=item.get("content_hash", ""),
        )
        for item in payload["documents"]
    )
    extraction_items = []
    for item in payload["extractions"]:
        fields: dict[str, ExtractedField] = {}
        for name, field in item["fields"].items():
            value = field["value"]
            if name in {"event_date", "notice_date", "particulars_date"} and value:
                value = date.fromisoformat(value)
            source = TextSpan(**field["source"]) if field.get("source") else None
            fields[name] = ExtractedField(value, field["confidence"], source)
        extraction_items.append(
            ExtractionResult(
                document_id=item["document_id"],
                filename=item["filename"],
                fields=fields,
                text=item["text"],
                warnings=tuple(item.get("warnings", [])),
            )
        )
    compliance_items = []
    for item in payload["compliance"]:
        compliance_items.append(
            ComplianceResult(
                document_id=item["document_id"],
                co_number=item["co_number"],
                time_bar_verdict=item["time_bar_verdict"],
                checks=tuple(ComplianceCheck(**check) for check in item["checks"]),
                notice_elapsed_days=item.get("notice_elapsed_days"),
                particulars_elapsed_days=item.get("particulars_elapsed_days"),
                score=item.get("score", 0.0),
            )
        )
    extractions = tuple(extraction_items)
    compliance = tuple(compliance_items)
    manifest = payload["manifest"]
    return PipelineResult(
        documents=documents,
        extractions=extractions,
        compliance=compliance,
        analytics=portfolio_analytics(extractions, compliance, metadata),
        provisional=bool(manifest.get("provisional")),
        messages=tuple(manifest.get("messages", [])),
        generated_at=manifest.get("generated_at", ""),
        config_hash=manifest.get("config_hash", ""),
        input_hash=manifest.get("input_data_hash", ""),
    )


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
