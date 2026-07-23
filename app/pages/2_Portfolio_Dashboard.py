"""Portfolio exposure dashboard for the runnable MVP."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
APP = ROOT / "app"
for path in (SRC, APP):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from co_copilot.config import load_config
from styles import APP_CSS
from ui_components import (
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    provisional_banner,
    sidebar_status,
)

st.set_page_config(
    page_title="Portfolio Dashboard · CO Copilot", page_icon="▦", layout="wide"
)
apply_styles(APP_CSS)
ensure_session()
sidebar_status()
st.title("Portfolio dashboard")
st.caption("Commercial exposure, procedural position, and concentrations at a glance.")

result = st.session_state.get("pipeline_result")
if not result:
    st.warning("○ No analysis loaded. Return to Home and select “Load demo project.”")
    footer()
    st.stop()

provisional_banner(result)
summary = result.analytics
register = summary["register"]
config = load_config(ROOT / "config.yaml")
palette = config["ui"]["categorical_palette"]

kpis = st.columns(5)
kpis[0].metric("Net CO exposure (USD)", f"${summary['total_exposure']/1_000_000:.2f}M")
kpis[1].metric("% of contract sum", f"{summary['exposure_percent']:.1f}%")
kpis[2].metric("Change orders", f"{len(register)}")
kpis[3].metric("Timely notice rate", f"{summary['compliance_rate']:.0%}")
kpis[4].metric(
    "Time-barred gross (USD)", f"${summary['time_barred_value']/1_000_000:.2f}M"
)

left, right = st.columns([1.45, 1])
with left:
    trend = go.Figure()
    trend.add_trace(
        go.Scatter(
            x=register["event_date"],
            y=register["cumulative_cost"] / 1_000_000,
            mode="lines+markers",
            name="Cumulative CO value",
            line={"color": "#0072B2", "width": 3},
            marker={"symbol": "circle", "size": 8},
        )
    )
    trend.add_hline(
        y=250,
        line_dash="dash",
        line_color="#D89414",
        annotation_text="Original contract sum · USD 250M",
    )
    trend.update_layout(
        title="Cumulative change value vs contract sum",
        yaxis_title="USD millions",
        xaxis_title=None,
        height=360,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        legend={"orientation": "h"},
    )
    st.plotly_chart(trend, use_container_width=True)
with right:
    by_status = register.groupby("status", as_index=False)["cost_value"].sum()
    status_chart = px.bar(
        by_status,
        x="status",
        y="cost_value",
        color="status",
        color_discrete_sequence=palette,
        title="Net value by status",
        labels={"cost_value": "USD", "status": "Status"},
    )
    status_chart.update_traces(marker_pattern_shape="/")
    status_chart.update_layout(
        height=360,
        showlegend=False,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    st.plotly_chart(status_chart, use_container_width=True)

by_type, by_contractor = st.columns(2)
with by_type:
    frame = register.groupby("type", as_index=False)["cost_value"].sum()
    chart = px.bar(
        frame,
        x="cost_value",
        y="type",
        orientation="h",
        color="type",
        color_discrete_sequence=palette,
        title="Exposure by change type",
    )
    chart.update_layout(height=390, showlegend=False, yaxis_title=None)
    st.plotly_chart(chart, use_container_width=True)
with by_contractor:
    frame = register.groupby("contractor", as_index=False)["cost_value"].sum()
    chart = px.bar(
        frame,
        x="cost_value",
        y="contractor",
        orientation="h",
        color="contractor",
        color_discrete_sequence=palette,
        title="Exposure by contractor",
    )
    chart.update_layout(height=390, showlegend=False, yaxis_title=None)
    st.plotly_chart(chart, use_container_width=True)

st.subheader("Ranked findings")
if not summary["findings"]:
    st.success("● No portfolio-level rule findings for the current selection.")
for finding in summary["findings"]:
    icon = {"critical": "■", "high": "▲", "medium": "◆"}.get(finding.severity, "●")
    st.markdown(
        f'<div class="finding-card finding-{finding.severity}"><strong>{icon} '
        f"{finding.title}</strong><br>{finding.message}</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Commercial rationale and affected COs"):
        st.write(finding.rationale)
        st.caption(", ".join(finding.affected_cos))

export_escape_hatch(result, "dashboard")
footer()
