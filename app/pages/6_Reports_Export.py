"""Configurable Excel, HTML, JSON, and CSV report exports."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from co_copilot import __version__
from co_copilot.report_export import (
    excel_register_bytes,
    extracted_json_bytes,
    html_review_pack,
)
from styles import APP_CSS
from ui_components import (
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    sidebar_status,
)

st.set_page_config(
    page_title="Reports & Export · CO Copilot", page_icon="⇩", layout="wide"
)
apply_styles(APP_CSS)
ensure_session()
sidebar_status()
st.title("Reports and export")
st.caption(
    "Every artifact is stamped with version, timestamp, configuration hash, and input hash."
)

result = st.session_state.get("pipeline_result")
if not result:
    st.warning("○ No computed results are available to export.")
    footer()
    st.stop()

left, right = st.columns([1, 1])
with left:
    st.subheader("Review-pack sections")
    include_summary = st.checkbox("Executive summary", value=True)
    include_findings = st.checkbox("Ranked findings", value=True)
    include_pages = st.checkbox("Per-CO one-pagers", value=True)
    include_method = st.checkbox("Method and limitations", value=True)
    as_of = st.date_input("As-of date", value=date.today())
with right:
    narrative = st.text_area(
        "Reviewer narrative",
        height=170,
        placeholder="Add the commercial lead's context, reservations, or meeting position.",
    )
    st.caption(
        f"Version {__version__} · config {result.config_hash} · input {result.input_hash}"
    )

sections = {
    name
    for name, enabled in (
        ("summary", include_summary),
        ("findings", include_findings),
        ("co_pages", include_pages),
        ("method", include_method),
    )
    if enabled
}
html_pack = html_review_pack(
    result,
    __version__,
    as_of,
    narrative,
    memos=st.session_state.get("report_memos", {}),
    sections=sections,
)
excel_pack = excel_register_bytes(result, __version__)
facts_json = extracted_json_bytes(result, __version__)
register_csv = result.analytics["register"].to_csv(index=False).encode("utf-8")

st.subheader("Downloads")
buttons = st.columns(4)
buttons[0].download_button(
    "⇩ Excel register",
    excel_pack,
    "change_order_register.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
buttons[1].download_button(
    "⇩ HTML review pack",
    html_pack.encode("utf-8"),
    "co_review_pack.html",
    "text/html",
    use_container_width=True,
)
buttons[2].download_button(
    "⇩ Extracted facts JSON",
    facts_json,
    "extracted_facts.json",
    "application/json",
    use_container_width=True,
)
buttons[3].download_button(
    "⇩ CO register CSV",
    register_csv,
    "co_register.csv",
    "text/csv",
    use_container_width=True,
)

st.subheader("HTML preview")
components.html(html_pack, height=720, scrolling=True)
export_escape_hatch(result, "reports")
footer()
