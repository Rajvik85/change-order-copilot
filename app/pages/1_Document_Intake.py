"""Hardened multi-mode document intake and validation."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src", ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from co_copilot import __version__
from co_copilot.config import load_config
from co_copilot.document_loader import load_document_bytes
from co_copilot.mapping import (
    CANONICAL_SCHEMA,
    save_mapping_profile,
    suggest_mappings,
    validate_mapping,
)
from co_copilot.pipeline import load_project_metadata, run_pipeline
from co_copilot.security import validate_upload
from co_copilot.storage import atomic_write, persist_snapshot
from co_copilot.validation import validate_document
from styles import APP_CSS
from ui_components import (
    apply_styles,
    ensure_session,
    export_escape_hatch,
    footer,
    sidebar_status,
)

st.set_page_config(
    page_title="Document Intake · CO Copilot", page_icon="⇧", layout="wide"
)
apply_styles(APP_CSS)
_, artifact_folder = ensure_session()
sidebar_status()
config = load_config(ROOT / "config.yaml")
base_metadata = load_project_metadata(ROOT / "data/project_meta.yaml")

st.title("Document intake")
st.caption(
    "Validate first, analyze second. Malformed inputs become fix-oriented feedback—not tracebacks."
)


def _metadata_form(prefix: str) -> dict:
    metadata = dict(base_metadata)
    left, middle, right = st.columns(3)
    metadata["contract_sum"] = left.number_input(
        "Contract sum",
        min_value=1.0,
        value=float(base_metadata["contract_sum"]),
        step=1_000_000.0,
        key=f"{prefix}_sum",
    )
    currency = middle.text_input(
        "Canonical currency / symbol",
        value=str(base_metadata["currency"]),
        key=f"{prefix}_currency",
    )
    metadata["currency"] = currency.strip().upper() or "USD"
    metadata["notice_rules"] = dict(base_metadata["notice_rules"])
    metadata["notice_rules"]["event_notice_days"] = right.number_input(
        "Initial notice days",
        min_value=1,
        value=int(base_metadata["notice_rules"]["event_notice_days"]),
        key=f"{prefix}_notice",
    )
    metadata["notice_rules"]["particulars_days"] = right.number_input(
        "Particulars days",
        min_value=1,
        value=int(base_metadata["notice_rules"]["particulars_days"]),
        key=f"{prefix}_particulars",
    )
    return metadata


def _run_paths(paths: list[Path], metadata: dict, clause_dir: Path) -> None:
    progress_bar = st.progress(0, text="Preparing analysis…")
    status_box = st.empty()

    def report(current: int, total: int, filename: str, status: str) -> None:
        progress_bar.progress(current / max(total, 1), text=f"{filename} — {status}")
        status_box.caption(f"{current}/{total} · {filename} · {status}")

    with st.spinner("Extracting facts and applying deterministic checks…"):
        result = run_pipeline(paths, clause_dir, metadata, config, progress=report)
    progress_bar.empty()
    st.session_state["pipeline_result"] = result
    persist_snapshot(artifact_folder, result, __version__)
    st.success(
        f"● {len(result.documents)} documents analyzed and preserved for this session."
    )
    if result.messages:
        st.warning("▲ " + " · ".join(result.messages))


def _mapped_value(
    row: pd.Series, reverse: dict[str, str], name: str, default: str = "Not provided"
) -> str:
    """Return one canonical field from a mapped register row."""
    source = reverse.get(name)
    raw = row.get(source) if source else default
    return default if pd.isna(raw) else str(raw)


upload_tab, paste_tab, demo_tab = st.tabs(["UPLOAD", "PASTE", "DEMO"])

with upload_tab:
    st.subheader("Upload change-order documents")
    metadata = _metadata_form("upload")
    uploaded = st.file_uploader(
        "CO files",
        type=["md", "txt", "docx"],
        accept_multiple_files=True,
        help=f"Up to {config['uploads']['max_files_per_session']} files; "
        f"{config['uploads']['max_file_size_mb']} MB each.",
    )
    clause_uploads = st.file_uploader(
        "Optional synthetic/client-authorized clause excerpts",
        type=["md"],
        accept_multiple_files=True,
    )
    validation_rows: list[dict[str, str]] = []
    accepted: list[tuple[str, bytes]] = []
    if len(uploaded) > int(config["uploads"]["max_files_per_session"]):
        st.error(
            f"■ Select no more than {config['uploads']['max_files_per_session']} files "
            "per session. Split larger portfolios into batches."
        )
        uploaded = []
    for supplied in uploaded:
        try:
            safe_name = validate_upload(
                supplied.name, supplied.size, supplied.type, config
            )
            data = supplied.getvalue()
            document = load_document_bytes(data, safe_name)
            report = validate_document(document)
            accepted.append((safe_name, data)) if report.accepted else None
            issues = "; ".join(issue.message for issue in report.issues) or "Ready"
            hints = "; ".join(issue.fix_hint for issue in report.issues) or "None"
            validation_rows.append(
                {
                    "File": safe_name,
                    "Result": "● Loaded" if report.accepted else "■ Rejected",
                    "Sections": ", ".join(report.sections_found) or "Full text",
                    "Feedback": issues,
                    "Fix hint": hints,
                }
            )
        except Exception as exc:
            validation_rows.append(
                {
                    "File": supplied.name,
                    "Result": "■ Rejected",
                    "Sections": "—",
                    "Feedback": str(exc),
                    "Fix hint": "Use an individual .md, .txt, or valid .docx file.",
                }
            )
    if validation_rows:
        st.dataframe(
            pd.DataFrame(validation_rows), hide_index=True, use_container_width=True
        )
    if st.button("Analyze accepted documents", type="primary", disabled=not accepted):
        input_dir = artifact_folder / "inputs"
        paths = []
        for name, data in accepted:
            destination = input_dir / name
            atomic_write(destination, data)
            paths.append(destination)
        clause_dir = ROOT / "data/contract/clauses"
        if clause_uploads:
            clause_dir = artifact_folder / "clauses"
            for supplied in clause_uploads:
                safe_name = validate_upload(
                    supplied.name, supplied.size, supplied.type, config
                )
                atomic_write(clause_dir / safe_name, supplied.getvalue())
        _run_paths(paths, metadata, clause_dir)

    st.divider()
    st.subheader("Register CSV and column mapping")
    st.caption("For client registers whose headers do not match the canonical schema.")
    register_upload = st.file_uploader("Optional register CSV", type=["csv"])
    if register_upload:
        try:
            frame = pd.read_csv(io.BytesIO(register_upload.getvalue()), nrows=5000)
            suggestions = suggest_mappings(list(frame.columns))
            st.dataframe(frame.head(8), hide_index=True, use_container_width=True)
            mapping: dict[str, str] = {}
            options = ["— ignore —", *CANONICAL_SCHEMA]
            columns = st.columns(3)
            for index, header in enumerate(frame.columns):
                default = suggestions.get(header)
                selected = columns[index % 3].selectbox(
                    str(header),
                    options,
                    index=options.index(default) if default in options else 0,
                    key=f"map_{header}",
                )
                if selected != "— ignore —":
                    mapping[str(header)] = selected
            mapping_issues = validate_mapping(mapping)
            for issue in mapping_issues:
                (st.error if issue.severity == "error" else st.warning)(
                    f"{issue.message} {issue.fix_hint}"
                )
            profile_name = st.text_input("Mapping profile name", "client-register")
            if st.button("Save mapping profile", disabled=not mapping):
                profile = save_mapping_profile(artifact_folder, profile_name, mapping)
                st.success(f"● Saved {profile.name} for this isolated session.")
            if st.button(
                "Create and analyze mapped CO documents",
                type="primary",
                disabled=not mapping
                or any(i.severity == "error" for i in mapping_issues),
            ):
                reverse = {target: source for source, target in mapping.items()}
                mapped_dir = artifact_folder / "mapped_inputs"
                paths = []
                for row_number, row in frame.iterrows():
                    co_number = _mapped_value(
                        row, reverse, "co_number", f"CO-{row_number + 1:03d}"
                    )
                    text = f"""# Change Order {co_number}
## Header
Originator: {_mapped_value(row, reverse, 'originator')}
Contractor: {_mapped_value(row, reverse, 'contractor')}
Status: {_mapped_value(row, reverse, 'status', 'Draft')}
Event Date: {_mapped_value(row, reverse, 'event_date')}
Notice Date: {_mapped_value(row, reverse, 'notice_date')}
Particulars Date: {_mapped_value(row, reverse, 'particulars_date')}
## Event Description
Mapped register record. Change type: {_mapped_value(row, reverse, 'type')}.
## Contractual Basis
Clause {_mapped_value(row, reverse, 'cited_clause_refs', 'Not cited')}.
## Cost Impact
{metadata['currency']} {_mapped_value(row, reverse, 'cost_value', '0')}
## Schedule Impact
{_mapped_value(row, reverse, 'schedule_days', '0')} days.
"""
                    path = mapped_dir / f"mapped_{row_number + 1:04d}.md"
                    atomic_write(path, text.encode("utf-8"))
                    paths.append(path)
                _run_paths(paths, metadata, ROOT / "data/contract/clauses")
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
            st.error(f"■ The CSV could not be read safely: {exc}")

with paste_tab:
    st.subheader("Paste one change order for instant analysis")
    paste_metadata = _metadata_form("paste")
    pasted = st.text_area(
        "Change-order text",
        height=330,
        placeholder="# Change Order CO-101\n## Header\nEvent Date: ...",
    )
    if st.button(
        "Analyze pasted document", type="primary", disabled=len(pasted.strip()) < 80
    ):
        destination = artifact_folder / "inputs" / "pasted_change_order.md"
        atomic_write(destination, pasted.encode("utf-8"))
        _run_paths([destination], paste_metadata, ROOT / "data/contract/clauses")
    if pasted and len(pasted.strip()) < 80:
        st.warning(
            "▲ Add at least the header, event, cost/schedule impacts, and status."
        )

with demo_tab:
    st.subheader("Bundled synthetic EPC demonstration")
    st.write(
        "18 COs · 15 invented clauses · USD 250M fictional contract · fully offline"
    )
    if st.button("Load all demo documents", type="primary", key="intake_demo"):
        _run_paths(
            list((ROOT / "data/change_orders").glob("*")),
            base_metadata,
            ROOT / "data/contract/clauses",
        )

if result := st.session_state.get("pipeline_result"):
    export_escape_hatch(result, "intake")
footer()
