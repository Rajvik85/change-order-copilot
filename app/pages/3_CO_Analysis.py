"""Single-CO traceability and compliance review."""

from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from styles import APP_CSS
from ui_components import (
    STATUS_ICONS,
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    sidebar_status,
)

st.set_page_config(page_title="CO Analysis · CO Copilot", page_icon="⌁", layout="wide")
apply_styles(APP_CSS)
ensure_session()
sidebar_status()
st.title("Change-order analysis")
st.caption("Every extracted fact stays tied to the sentence that supports it.")

result = st.session_state.get("pipeline_result")
if not result:
    st.warning("○ No analysis loaded. Load documents from Home or Document Intake.")
    footer()
    st.stop()

register = result.analytics["register"]
filter_col, status_col = st.columns([2, 1])
query = filter_col.text_input(
    "Filter register", placeholder="CO number, contractor, or type"
)
statuses = ["All", *sorted(register["status"].dropna().unique())]
status_filter = status_col.selectbox("Status", statuses)
filtered = register.copy()
if query:
    mask = (
        filtered.astype(str)
        .apply(lambda column: column.str.contains(query, case=False, na=False))
        .any(axis=1)
    )
    filtered = filtered[mask]
if status_filter != "All":
    filtered = filtered[filtered["status"] == status_filter]
st.dataframe(
    filtered[
        [
            "co_number",
            "type",
            "contractor",
            "cost_value",
            "schedule_days",
            "status",
            "time_bar_verdict",
        ]
    ],
    hide_index=True,
    use_container_width=True,
)
available = filtered["co_number"].tolist()
if not available:
    st.info("No COs match the current filter.")
    footer()
    st.stop()
selected_number = st.selectbox("Review change order", available)
row = filtered.loc[filtered["co_number"] == selected_number].iloc[0]
extraction = next(
    item for item in result.extractions if item.document_id == row.document_id
)
assessment = next(
    item for item in result.compliance if item.document_id == row.document_id
)

traced_fields = [
    name for name, field in extraction.fields.items() if field.source is not None
]
trace_field = st.selectbox(
    "Trace a fact to its source sentence",
    traced_fields,
    format_func=lambda value: value.replace("_", " ").title(),
)
source = extraction.fields[trace_field].source
original, facts, checks = st.columns([1.35, 1, 1.1])
with original:
    st.subheader("1 · Original document")
    if source:
        marked = (
            html.escape(extraction.text[: source.start])
            + "<mark>"
            + html.escape(extraction.text[source.start : source.end])
            + "</mark>"
            + html.escape(extraction.text[source.end :])
        )
    else:
        marked = html.escape(extraction.text)
    st.markdown(
        f"<pre style='white-space:pre-wrap;background:white;border:1px solid #dbe4ed;"
        f"border-radius:12px;padding:14px;max-height:700px;overflow:auto'>{marked}</pre>",
        unsafe_allow_html=True,
    )
with facts:
    st.subheader("2 · Extracted facts")
    for name, field in extraction.fields.items():
        if name == "event_phrases":
            continue
        value = field.value
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        st.markdown(
            f"**{name.replace('_', ' ').title()}**  \n"
            f"{value if value not in (None, [], '') else 'Not evidenced'}  \n"
            f"`confidence {field.confidence:.0%}`"
        )
    with st.expander("spaCy event signals"):
        st.write(extraction.value("event_phrases", []) or "No matcher signal")
with checks:
    st.subheader("3 · Compliance checklist")
    st.markdown(f"### {STATUS_ICONS[assessment.time_bar_verdict]}")
    for check in assessment.checks:
        st.markdown(f"**{STATUS_ICONS[check.status]} · {check.label}**")
        st.write(check.verdict)
        st.code(check.calculation, language=None)
        with st.expander("Rule and clause evidence"):
            st.write(check.rule)
            if check.clause_reference:
                st.caption(f"Clause {check.clause_reference}")
            st.write(check.clause_text or "No clause quote required for this check.")

export_escape_hatch(result, "analysis")
footer()
