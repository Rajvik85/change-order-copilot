"""Pipeline timeout, recovery, and atomic-artifact tests."""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from co_copilot import __version__
from co_copilot.config import load_config
from co_copilot.pipeline import (
    hash_inputs,
    load_project_metadata,
    result_manifest,
    run_pipeline,
    snapshot_payload,
)
from co_copilot.storage import (
    artifact_zip,
    atomic_write,
    load_snapshot,
    persist_snapshot,
    session_artifact_dir,
)


def test_traceability_manifest_and_zip(demo_result) -> None:
    manifest = result_manifest(demo_result, __version__)
    assert manifest["version"] == __version__
    assert len(manifest["input_data_hash"]) == 16
    payload = snapshot_payload(demo_result, __version__)
    assert len(payload["register"]) == 18
    with zipfile.ZipFile(BytesIO(artifact_zip(demo_result, __version__))) as archive:
        assert {"manifest.json", "co_register.csv", "compliance.json"} <= set(
            archive.namelist()
        )


def test_atomic_snapshot_roundtrip(tmp_path: Path, demo_result) -> None:
    output = tmp_path / "nested" / "value.json"
    atomic_write(output, b'{"safe": true}')
    assert json.loads(output.read_text())["safe"]
    path = persist_snapshot(tmp_path, demo_result, __version__)
    assert path.exists()
    restored = load_snapshot(tmp_path)
    assert restored["manifest"]["document_count"] == 18


def test_session_directory_is_isolated() -> None:
    session_id = "a" * 32
    assert session_artifact_dir(session_id).name == session_id
    try:
        session_artifact_dir("../unsafe")
    except ValueError as exc:
        assert "Invalid session" in str(exc)
    else:
        raise AssertionError("Unsafe session identifier was accepted")


def test_cancellation_returns_provisional_subset(project_root: Path) -> None:
    paths = sorted((project_root / "data/change_orders").glob("*"))[:2]
    statuses: list[str] = []
    result = run_pipeline(
        paths,
        project_root / "data/contract/clauses",
        load_project_metadata(project_root / "data/project_meta.yaml"),
        load_config(project_root / "config.yaml"),
        progress=lambda _i, _t, _name, status: statuses.append(status),
        cancel_requested=lambda: True,
    )
    assert result.provisional
    assert not result.documents
    assert "canceled" in result.messages[0]
    assert not statuses
    assert hash_inputs(paths) == hash_inputs(list(reversed(paths)))
