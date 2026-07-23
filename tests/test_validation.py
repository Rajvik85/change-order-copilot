"""Validation, upload hardening, mapping, and security hygiene tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from co_copilot.config import config_hash, load_config
from co_copilot.document_loader import load_document_bytes
from co_copilot.exceptions import ValidationError
from co_copilot.mapping import (
    load_mapping_profile,
    save_mapping_profile,
    suggest_mappings,
    validate_mapping,
)
from co_copilot.security import sanitize_filename, validate_upload
from co_copilot.validation import validate_document, validate_project_metadata


def test_friendly_document_and_metadata_feedback() -> None:
    tiny = load_document_bytes(b"tiny but nonempty", "tiny.txt")
    report = validate_document(tiny)
    assert not report.accepted
    assert report.issues[0].fix_hint
    issues = validate_project_metadata({"contract_sum": 0, "commencement_date": "bad"})
    assert {issue.field for issue in issues} == {"contract_sum", "commencement_date"}
    assert not validate_project_metadata(
        {"contract_sum": 1, "commencement_date": date(2026, 1, 1).isoformat()}
    )


def test_filename_sanitization_and_upload_limits(project_root: Path) -> None:
    config = load_config(project_root / "config.yaml")
    assert sanitize_filename("../../CO 001?.md") == "CO_001_.md"
    assert validate_upload("CO-001.md", 1024, "text/markdown", config) == "CO-001.md"
    with pytest.raises(ValidationError, match="rejected"):
        validate_upload("payload.zip", 10, "application/zip", config)
    with pytest.raises(ValidationError, match="limit"):
        validate_upload("large.txt", 11 * 1024 * 1024, "text/plain", config)
    with pytest.raises(ValidationError, match="not supported"):
        validate_upload("claim.pdf", 1024, "application/pdf", config)
    with pytest.raises(ValidationError, match="no usable"):
        sanitize_filename("../...")


def test_fuzzy_mapping_profile_roundtrip(tmp_path: Path) -> None:
    suggestions = suggest_mappings(["Variation No", "Claim Amount", "Approval Status"])
    assert suggestions["Variation No"] == "co_number"
    assert suggestions["Claim Amount"] == "cost_value"
    assert not validate_mapping(suggestions)
    duplicate = validate_mapping({"A": "status", "B": "status"})
    assert any(issue.severity == "error" for issue in duplicate)
    path = save_mapping_profile(tmp_path, "Client A/unsafe", suggestions)
    loaded = load_mapping_profile(path)
    assert loaded.mappings == suggestions
    assert "/" not in path.name


def test_config_hash_is_deterministic(project_root: Path) -> None:
    config = load_config(project_root / "config.yaml")
    assert config_hash(config) == config_hash(dict(reversed(list(config.items()))))
    assert len(config_hash(config)) == 16


def test_repository_contains_no_secret_like_values(project_root: Path) -> None:
    forbidden_prefixes = ("sk-" + "proj-", "sk-" + "ant-")
    for path in project_root.rglob("*"):
        if not path.is_file() or ".venv" in path.parts or ".git" in path.parts:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        assert not any(prefix in text for prefix in forbidden_prefixes), path
