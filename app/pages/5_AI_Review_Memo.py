"""Designed no-key state and grounded optional memo drafting."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from co_copilot.clause_library import load_clause_library
from co_copilot.config import load_config
from co_copilot.llm_layer import configured_provider, generate_review, grounding_payload
from styles import APP_CSS
from ui_components import (
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    sidebar_status,
)

st.set_page_config(
    page_title="AI Review Memo · CO Copilot", page_icon="✦", layout="wide"
)
apply_styles(APP_CSS)
ensure_session()
sidebar_status()
st.title("AI review memo")
st.caption(
    "Optional narrative assistance. Deterministic verdicts remain fixed and visible."
)

result = st.session_state.get("pipeline_result")
provider = configured_provider()
if not provider:
    st.markdown(
        """
        <div class="status-card"><strong>○ Optional AI is not configured</strong><br>
        The complete extraction, compliance, analytics, and report workflow remains
        available offline. To enable live drafts, install <code>.[llm]</code> and set
        one environment key shown—blank—in <code>.env.example</code>. Keys are never
        stored in project files.</div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Static development example")
    st.warning("▲ AI-assisted draft — human review required")
    st.markdown(
        """
**Facts**  
CO-003 records unexpected cemented gravel, USD 3.75M, and 30 claimed days.

**Deterministic compliance position**  
The notice was served 19 calendar days after the event against a 14-day rule:
five days late. The engine therefore reports **TIME-BARRED**. This draft does
not alter that result.

**Commercial exposure**  
Quantum and critical-path causation require QS and planner validation. The
submission identifies a fragnet and measured cost categories, but waiver or
other time-bar evidence is not evidenced in the supplied facts.

**Recommended action**  
Preserve correspondence on knowledge or waiver, audit contemporaneous records,
and separate entitlement review from quantum assessment.
        """
    )
    with st.expander("What a live model would receive"):
        st.write(
            "Only canonical extracted facts, deterministic checks, Clause 4.7, and "
            "the invented notice/time-bar excerpts—not the entire document library."
        )

if not result:
    st.info("Load a project to inspect grounding or generate a live memo.")
    footer()
    st.stop()

register = result.analytics["register"]
selected = st.selectbox("Change order", register["co_number"].tolist())
row = register.loc[register["co_number"] == selected].iloc[0]
extraction = next(
    item for item in result.extractions if item.document_id == row.document_id
)
assessment = next(
    item for item in result.compliance if item.document_id == row.document_id
)
clauses = load_clause_library(ROOT / "data/contract/clauses")
grounding = grounding_payload(extraction, assessment, clauses)
with st.expander("Grounding supplied to the model"):
    st.json(grounding)

if provider:
    capability_labels = {
        "executive_summary": "Executive summary",
        "weakness_review": "Weakness review",
        "review_memo": "Full review memo",
        "clause_consistency": "Clause consistency",
    }
    capability = st.radio(
        "Draft type",
        list(capability_labels),
        format_func=capability_labels.get,
        horizontal=True,
    )
    if st.button("Generate grounded draft", type="primary"):
        with st.spinner(f"Generating through {provider.title()} with bounded retries…"):
            memo = generate_review(
                capability,
                extraction,
                assessment,
                clauses,
                load_config(ROOT / "config.yaml"),
                provider=provider,
            )
        if memo.status == "ok":
            st.session_state.setdefault("review_memos", {})[row.document_id] = memo
        else:
            st.error(f"■ {memo.content}")

memo = st.session_state.get("review_memos", {}).get(row.document_id)
if memo:
    st.warning("▲ AI-assisted draft — human review required")

    def stream_words():
        for word in memo.content.split():
            yield word + " "

    st.write_stream(stream_words)
    st.code(memo.content, language=None)
    if st.button(
        "Add to report",
        disabled=row.document_id in st.session_state.get("report_memos", {}),
    ):
        st.session_state.setdefault("report_memos", {})[row.document_id] = memo
        st.success("● Memo added to this session's review pack.")

export_escape_hatch(result, "memo")
footer()
