"""Portfolio compliance matrix, urgency radar, and clause reference."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from co_copilot.clause_library import load_clause_library
from co_copilot.config import load_config
from styles import APP_CSS
from ui_components import (
    STATUS_ICONS,
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    sidebar_status,
)

st.set_page_config(
    page_title="Compliance Checker · CO Copilot", page_icon="✓", layout="wide"
)
apply_styles(APP_CSS)
ensure_session()
sidebar_status()
st.title("Compliance checker")
st.caption(
    "Procedural discipline shown as rules, evidence, and exact calendar-day arithmetic."
)

result = st.session_state.get("pipeline_result")
if not result:
    st.warning("○ No analysis loaded. Load documents from Home or Document Intake.")
    footer()
    st.stop()

matrix_rows = []
for assessment in result.compliance:
    row = {
        "CO": assessment.co_number,
        "Time-bar position": STATUS_ICONS[assessment.time_bar_verdict],
    }
    row.update({check.label: STATUS_ICONS[check.status] for check in assessment.checks})
    matrix_rows.append(row)
st.subheader("Portfolio compliance matrix")
st.dataframe(pd.DataFrame(matrix_rows), hide_index=True, use_container_width=True)

config = load_config(ROOT / "config.yaml")
notice_limit = int(config["compliance"]["notice_period_days"])
radar_rows = []
for assessment in result.compliance:
    elapsed = assessment.notice_elapsed_days
    remaining = None if elapsed is None else notice_limit - elapsed
    radar_rows.append(
        {
            "CO": assessment.co_number,
            "Position": STATUS_ICONS[assessment.time_bar_verdict],
            "Notice elapsed": elapsed,
            "Days remaining (+) / overdue (-)": remaining,
            "Urgency": 999 if remaining is None else remaining,
        }
    )
radar = pd.DataFrame(radar_rows).sort_values("Urgency")
st.subheader("Time-bar radar")
st.dataframe(
    radar.drop(columns="Urgency"),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Days remaining (+) / overdue (-)": st.column_config.NumberColumn(
            help="Negative values are days beyond the configured 14-day limit."
        )
    },
)

st.subheader("What the clauses say")
library = load_clause_library(ROOT / "data/contract/clauses")
search = st.text_input(
    "Search loaded clauses", placeholder="notice, acceleration, backcharge…"
)
check_links: dict[str, list[str]] = {}
for assessment in result.compliance:
    for check in assessment.checks:
        if check.clause_reference:
            for reference in check.clause_reference.replace(" / ", ",").split(","):
                check_links.setdefault(reference.strip(), []).append(
                    f"{assessment.co_number} · {check.label}"
                )
for reference, text in library.items():
    if search and search.lower() not in text.lower():
        continue
    with st.expander(f"Clause {reference}"):
        st.markdown(text)
        powered = sorted(set(check_links.get(reference, [])))
        st.caption(
            "Checks powered: " + (", ".join(powered) if powered else "Reference only")
        )

export_escape_hatch(result, "compliance")
footer()
