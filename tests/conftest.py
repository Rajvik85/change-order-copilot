"""Shared offline fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from co_copilot.config import load_config
from co_copilot.pipeline import load_project_metadata, run_pipeline


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Repository root."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def demo_result(project_root: Path):
    """Complete deterministic demo output, computed once per test session."""
    return run_pipeline(
        list((project_root / "data" / "change_orders").glob("*")),
        project_root / "data" / "contract" / "clauses",
        load_project_metadata(project_root / "data" / "project_meta.yaml"),
        load_config(project_root / "config.yaml"),
    )
