"""End-to-end deterministic pipeline with bounded, provisional completion."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from co_copilot.analytics import portfolio_analytics
from co_copilot.clause_library import load_clause_library
from co_copilot.compliance import assess_compliance
from co_copilot.config import config_hash
from co_copilot.document_loader import load_document
from co_copilot.extractor import extract
from co_copilot.models import PipelineResult

ProgressCallback = Callable[[int, int, str, str], None]
CancelCallback = Callable[[], bool]


def hash_inputs(paths: list[Path]) -> str:
    """Hash names and bytes for deterministic cache keys and export stamps."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def run_pipeline(
    document_paths: list[Path],
    clause_directory: Path,
    metadata: dict[str, Any],
    config: dict[str, Any],
    progress: ProgressCallback | None = None,
    cancel_requested: CancelCallback | None = None,
) -> PipelineResult:
    """Run load, extract, compliance, and analytics within a hard time budget.

    On timeout or cancellation, the completed subset is returned with a
    provisional banner rather than discarding commercially useful work.
    """
    started = time.monotonic()
    timeout = float(config["performance"]["pipeline_timeout_seconds"])
    maximum = int(config["performance"]["max_documents"])
    selected = sorted(document_paths, key=lambda path: path.name)[:maximum]
    messages: list[str] = []
    if len(document_paths) > maximum:
        messages.append(
            f"Input contained {len(document_paths)} documents; the first {maximum} "
            "were analyzed to protect interactive performance."
        )
    documents = []
    extractions = []
    compliance = []
    clauses = load_clause_library(clause_directory)
    total = len(selected)
    provisional = False
    for index, path in enumerate(selected, start=1):
        if cancel_requested and cancel_requested():
            provisional = True
            messages.append("Analysis was canceled; completed documents are retained.")
            break
        if time.monotonic() - started >= timeout:
            provisional = True
            messages.append(
                f"The {timeout:.0f}-second analysis limit was reached; completed "
                "documents are shown as provisional results."
            )
            break
        try:
            document = load_document(path)
            extraction = extract(
                document,
                low_confidence=float(config["extraction"]["low_confidence_threshold"]),
            )
            assessment = assess_compliance(extraction, metadata, clauses)
        except Exception as exc:
            if progress:
                progress(index, total, path.name, f"rejected: {exc}")
            messages.append(f"{path.name}: {exc}")
            continue
        documents.append(document)
        extractions.append(extraction)
        compliance.append(assessment)
        if progress:
            progress(index, total, path.name, "complete")
    analytics = portfolio_analytics(tuple(extractions), tuple(compliance), metadata)
    return PipelineResult(
        documents=tuple(documents),
        extractions=tuple(extractions),
        compliance=tuple(compliance),
        analytics=analytics,
        provisional=provisional,
        messages=tuple(messages),
        generated_at=datetime.now(UTC).isoformat(),
        config_hash=config_hash(config),
        input_hash=hash_inputs(selected),
    )


def load_project_metadata(path: Path) -> dict[str, Any]:
    """Load project-level deterministic compliance metadata."""
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def result_manifest(result: PipelineResult, version: str) -> dict[str, Any]:
    """Create a compact traceability stamp for every export."""
    return {
        "application": "change-order-copilot",
        "version": version,
        "generated_at": result.generated_at,
        "config_hash": result.config_hash,
        "input_data_hash": result.input_hash,
        "document_count": len(result.documents),
        "provisional": result.provisional,
        "messages": list(result.messages),
    }


def snapshot_payload(result: PipelineResult, version: str) -> dict[str, Any]:
    """Serialize all computed evidence without unsafe pickle files."""
    analytics = {
        key: value
        for key, value in result.analytics.items()
        if key not in {"register", "findings"}
    }
    analytics["findings"] = [
        asdict(item) for item in result.analytics.get("findings", ())
    ]
    return {
        "manifest": result_manifest(result, version),
        "documents": [
            {
                **asdict(document),
                "path": str(document.path) if document.path else None,
            }
            for document in result.documents
        ],
        "extractions": [item.to_dict() for item in result.extractions],
        "compliance": [asdict(item) for item in result.compliance],
        "analytics": json.loads(json.dumps(analytics, default=str)),
        "register": json.loads(
            result.analytics["register"].to_json(orient="records", date_format="iso")
        ),
    }
