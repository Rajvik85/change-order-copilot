"""Reusable UI components with accessible icon-plus-color semantics."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import streamlit as st

from co_copilot import __version__
from co_copilot.models import PipelineResult
from co_copilot.storage import (
    artifact_zip,
    load_snapshot,
    restore_pipeline_result,
    session_artifact_dir,
)

STATUS_ICONS = {
    "PASS": "● Pass",
    "WARN": "▲ Review",
    "FAIL": "■ Fail",
    "INFO": "◆ Info",
    "COMPLIANT": "● Compliant",
    "AT RISK": "▲ At risk",
    "TIME-BARRED": "■ Time-barred",
}


def ensure_session() -> tuple[str, Path]:
    """Create or recover an isolated session identifier through query params."""
    query_id = str(st.query_params.get("sid", ""))
    if len(query_id) == 32 and all(char in "0123456789abcdef" for char in query_id):
        session_id = query_id
    else:
        session_id = uuid.uuid4().hex
        st.query_params["sid"] = session_id
    st.session_state.setdefault("session_id", session_id)
    return session_id, session_artifact_dir(session_id)


def apply_styles(css: str) -> None:
    """Apply the shared visual system."""
    st.markdown(css, unsafe_allow_html=True)


def sidebar_status() -> None:
    """Render global document and optional-LLM status."""
    with st.sidebar:
        st.markdown("### Workspace status")
        result = st.session_state.get("pipeline_result")
        count = len(result.documents) if isinstance(result, PipelineResult) else 0
        st.caption(f"{'●' if count else '○'} Documents loaded: {count}")
        import os

        configured = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        st.caption(
            f"{'●' if configured else '○'} Optional AI: {'ready' if configured else 'offline'}"
        )
        st.caption(f"Version {__version__}")


def provisional_banner(result: PipelineResult) -> None:
    """Show when a bounded pipeline returned a useful partial result."""
    if result.provisional:
        st.markdown(
            '<div class="provisional">▲ Provisional results — a time or document '
            "limit was reached. Completed records remain available.</div>",
            unsafe_allow_html=True,
        )


def export_escape_hatch(result: PipelineResult, key: str) -> None:
    """Provide a page-level export of everything computed so far."""
    st.download_button(
        "⇩ Export everything computed so far",
        data=artifact_zip(result, __version__),
        file_name=f"co_copilot_all_artifacts_{result.input_hash}.zip",
        mime="application/zip",
        key=f"escape_{key}",
        help="JSON, CSV, compliance evidence, and traceability manifest in one ZIP.",
    )


def recovery_panel(folder: Path, metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Offer the owning session's last safe snapshot after a rerun or crash."""
    snapshot = load_snapshot(folder)
    if snapshot and "pipeline_result" not in st.session_state:
        count = snapshot.get("manifest", {}).get("document_count", 0)
        with st.expander(f"↻ Restore last session summary ({count} documents)"):
            st.caption("The safe JSON snapshot can restore all interactive views.")
            if st.button("Restore interactive results", key="restore_snapshot"):
                restored = restore_pipeline_result(folder, metadata)
                if restored is not None:
                    st.session_state["pipeline_result"] = restored
                    st.rerun()
            st.download_button(
                "Download recovery snapshot",
                data=str.encode(__import__("json").dumps(snapshot, indent=2)),
                file_name="co_copilot_recovery_snapshot.json",
                mime="application/json",
            )
        return snapshot
    return None


def footer() -> None:
    """Render product version and portfolio disclaimer."""
    st.markdown(
        f'<div class="app-footer">Change Order Copilot v{__version__} · '
        "Synthetic data · Assistive analysis, not legal advice</div>",
        unsafe_allow_html=True,
    )
