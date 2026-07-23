"""Portfolio exposure, concentration, trends, and commercial findings."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from co_copilot.models import ComplianceResult, ExtractionResult, Finding


def build_register(
    extractions: tuple[ExtractionResult, ...],
    compliance: tuple[ComplianceResult, ...],
) -> pd.DataFrame:
    """Build the canonical CO register used by dashboards and exports."""
    compliance_by_id = {item.document_id: item for item in compliance}
    records: list[dict[str, Any]] = []
    for result in extractions:
        assessment = compliance_by_id.get(result.document_id)
        records.append(
            {
                "co_number": result.value("co_number"),
                "document_id": result.document_id,
                "document_date": result.value("event_date"),
                "type": result.value("type"),
                "contractor": result.value("contractor"),
                "cost_value": float(result.value("cost_value", 0) or 0),
                "schedule_days": int(result.value("schedule_days", 0) or 0),
                "status": result.value("status"),
                "notice_date": result.value("notice_date"),
                "event_date": result.value("event_date"),
                "particulars_date": result.value("particulars_date"),
                "clauses": ", ".join(result.value("cited_clause_refs", [])),
                "time_bar_verdict": (
                    assessment.time_bar_verdict if assessment else "NOT ASSESSED"
                ),
                "compliance_score": assessment.score if assessment else 0.0,
            }
        )
    columns = [
        "co_number",
        "document_id",
        "document_date",
        "type",
        "contractor",
        "cost_value",
        "schedule_days",
        "status",
        "notice_date",
        "event_date",
        "particulars_date",
        "clauses",
        "time_bar_verdict",
        "compliance_score",
    ]
    frame = pd.DataFrame.from_records(records, columns=columns)
    if not frame.empty:
        frame = frame.sort_values(["event_date", "co_number"], na_position="last")
        frame["cumulative_cost"] = frame["cost_value"].cumsum()
    else:
        frame["cumulative_cost"] = pd.Series(dtype=float)
    return frame.reset_index(drop=True)


def generate_findings(
    register: pd.DataFrame,
    extractions: tuple[ExtractionResult, ...],
    metadata: dict[str, Any],
) -> tuple[Finding, ...]:
    """Generate ranked, documented rules that express commercial rationale."""
    findings: list[Finding] = []
    time_barred = register.loc[
        register["time_bar_verdict"] == "TIME-BARRED", "co_number"
    ].tolist()
    if time_barred:
        value = (
            register.loc[register["time_bar_verdict"] == "TIME-BARRED", "cost_value"]
            .abs()
            .sum()
        )
        findings.append(
            Finding(
                "F-TIMEBAR",
                "critical",
                "Time-barred exposure requires immediate strategy",
                f"{len(time_barred)} COs with USD {value:,.0f} gross value were noticed late.",
                "A valid claim can fail on procedure alone; preserve waiver, knowledge, "
                "and prevention arguments before debating quantum.",
                tuple(time_barred),
            )
        )

    positive = register[register["cost_value"] > 0]
    total_positive = positive["cost_value"].sum()
    threshold = float(metadata.get("concentration_threshold_percent", 40))
    if total_positive:
        by_contractor = positive.groupby("contractor")["cost_value"].sum()
        for contractor, value in by_contractor.items():
            share = value / total_positive * 100
            if share > threshold:
                affected = tuple(
                    positive.loc[positive["contractor"] == contractor, "co_number"]
                )
                findings.append(
                    Finding(
                        f"F-CONC-{contractor}",
                        "high",
                        "Exposure is concentrated with one contractor",
                        f"{contractor} represents {share:.1f}% of positive CO value.",
                        "Concentration increases negotiation leverage and package-level "
                        "settlement risk; review common causation and duplicated indirects.",
                        affected,
                    )
                )

    missing_basis = tuple(
        result.value("co_number")
        for result in extractions
        if not result.value("cited_clause_refs", [])
    )
    if missing_basis:
        findings.append(
            Finding(
                "F-BASIS",
                "high",
                "Drafts lack a stated contractual route",
                f"{len(missing_basis)} COs do not cite a supporting clause.",
                "Retrospective basis-hunting weakens notice quality and obscures the "
                "valuation route.",
                missing_basis,
            )
        )

    no_fragnet = tuple(
        result.value("co_number")
        for result in extractions
        if int(result.value("schedule_days", 0) or 0) != 0
        and "fragnet" not in result.text.lower()
    )
    if no_fragnet:
        findings.append(
            Finding(
                "F-FRAGNET",
                "medium",
                "Schedule assertions need logic-linked support",
                f"{len(no_fragnet)} COs claim time without naming a fragnet.",
                "Days are not automatically additive or critical; a logic-linked fragnet "
                "shows causation, path, mitigation, and concurrency.",
                no_fragnet,
            )
        )

    small = register[(register["cost_value"] > 0) & (register["cost_value"] < 250_000)]
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for row in small.itertuples():
        grouped[row.contractor].append(row.co_number)
    for contractor, numbers in grouped.items():
        if len(numbers) >= 3:
            findings.append(
                Finding(
                    f"F-CUM-{contractor}",
                    "medium",
                    "Repeated small changes may conceal cumulative impact",
                    f"{contractor} has {len(numbers)} sub-USD 250k COs.",
                    "Individually minor instructions can interact; reconcile shared "
                    "supervision, disruption, and schedule effects before settlement.",
                    tuple(numbers),
                )
            )

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    return tuple(sorted(findings, key=lambda item: (rank[item.severity], item.title)))


def portfolio_analytics(
    extractions: tuple[ExtractionResult, ...],
    compliance: tuple[ComplianceResult, ...],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate commercial exposure without pretending delay days are additive."""
    register = build_register(extractions, compliance)
    contract_sum = float(metadata["contract_sum"])
    by_status = (
        register.groupby("status", dropna=False)["cost_value"].sum().to_dict()
        if not register.empty
        else {}
    )
    by_type = (
        register.groupby("type", dropna=False)["cost_value"].sum().to_dict()
        if not register.empty
        else {}
    )
    by_contractor = (
        register.groupby("contractor", dropna=False)["cost_value"].sum().to_dict()
        if not register.empty
        else {}
    )
    assessed = [item for item in compliance if item.time_bar_verdict != "NOT ASSESSED"]
    compliant = [item for item in assessed if item.time_bar_verdict == "COMPLIANT"]
    time_barred_ids = {
        item.document_id
        for item in compliance
        if item.time_bar_verdict == "TIME-BARRED"
    }
    time_barred_value = (
        register.loc[register["document_id"].isin(time_barred_ids), "cost_value"]
        .abs()
        .sum()
    )
    findings = generate_findings(register, extractions, metadata)
    return {
        "register": register,
        "total_exposure": float(register["cost_value"].sum()),
        "gross_positive_exposure": float(
            register.loc[register["cost_value"] > 0, "cost_value"].sum()
        ),
        "exposure_percent": (
            float(register["cost_value"].sum()) / contract_sum * 100
            if contract_sum
            else 0.0
        ),
        "by_status": by_status,
        "by_type": by_type,
        "by_contractor": by_contractor,
        "schedule_days_claimed": int(
            register.loc[register["schedule_days"] > 0, "schedule_days"].sum()
        ),
        "schedule_days_recovery": int(
            register.loc[register["schedule_days"] < 0, "schedule_days"].sum()
        ),
        "compliance_rate": len(compliant) / len(assessed) if assessed else 0.0,
        "time_barred_value": float(time_barred_value),
        "findings": findings,
    }
