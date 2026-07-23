"""Change Order Copilot landing page and demo vertical slice."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from co_copilot.config import config_hash, load_config
from co_copilot.pipeline import hash_inputs, load_project_metadata, run_pipeline
from co_copilot.storage import persist_snapshot
from styles import APP_CSS
from ui_components import (
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    provisional_banner,
    recovery_panel,
    sidebar_status,
)

st.set_page_config(
    page_title="Change Order Copilot",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles(APP_CSS)
_, artifact_folder = ensure_session()
sidebar_status()


@st.cache_data(show_spinner=False)
def _cached_demo(input_data_hash: str, configuration_hash: str, root_path: str):
    """Cache immutable demo analysis by content and configuration hashes."""
    del input_data_hash, configuration_hash
    project_root = Path(root_path)
    config = load_config(project_root / "config.yaml")
    metadata = load_project_metadata(project_root / "data" / "project_meta.yaml")
    paths = list((project_root / "data" / "change_orders").glob("*"))
    return run_pipeline(
        paths,
        project_root / "data" / "contract" / "clauses",
        metadata,
        config,
    )


st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">Commercial intelligence · Offline first</div>
      <h1>Turn a pile of change orders into a defensible commercial position.</h1>
      <p>Extract traceable facts, test notice and time-bar compliance, and see
      portfolio exposure—without sending a contract document to an external model.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

columns = st.columns(3)
cards = (
    (
        "⌁",
        "Extract",
        "Turn inconsistent CO narratives into a canonical register with source evidence.",
    ),
    (
        "✓",
        "Check compliance",
        "Show exact calendar-day math, supporting clauses, and approval routes.",
    ),
    (
        "✦",
        "Draft memos",
        "Optionally explain deterministic findings in an AI-assisted, human-reviewed draft.",
    ),
)
for column, (icon, title, body) in zip(columns, cards, strict=True):
    with column:
        st.markdown(
            f'<div class="feature-card"><div class="eyebrow">{icon}</div>'
            f"<h3>{title}</h3><p>{body}</p></div>",
            unsafe_allow_html=True,
        )

st.write("")
action, context = st.columns([1, 2])
with action:
    load_clicked = st.button(
        "Load demo project →", type="primary", use_container_width=True
    )
with context:
    st.caption(
        "18 synthetic COs · USD 250M fictional EPC project · no API key · "
        "typically completes in a few seconds"
    )

recovery_panel(artifact_folder)

if load_clicked:
    paths = list((ROOT / "data" / "change_orders").glob("*"))
    config = load_config(ROOT / "config.yaml")
    with st.spinner("Reading, extracting, and checking 18 change orders…"):
        result = _cached_demo(
            hash_inputs(paths),
            config_hash(config),
            str(ROOT),
        )
    st.session_state["pipeline_result"] = result
    persist_snapshot(artifact_folder, result, "0.1.0")
    st.success(
        f"● {len(result.documents)} documents analyzed. "
        "Open Portfolio Dashboard from the sidebar."
    )

result = st.session_state.get("pipeline_result")
if result:
    provisional_banner(result)
    summary = result.analytics
    metrics = st.columns(4)
    metrics[0].metric("Net exposure", f"USD {summary['total_exposure']/1_000_000:.2f}M")
    metrics[1].metric("Contract value", f"{summary['exposure_percent']:.1f}%")
    metrics[2].metric("Timely notices", f"{summary['compliance_rate']:.0%}")
    metrics[3].metric(
        "Time-barred gross", f"USD {summary['time_barred_value']/1_000_000:.2f}M"
    )
    export_escape_hatch(result, "home")

st.info(
    "All documents and clauses in this project are synthetic. The deterministic "
    "checks support—never replace—professional contract review."
)
footer()
