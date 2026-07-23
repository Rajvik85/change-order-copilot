"""Deterministic contractual compliance and time-bar checks."""

from __future__ import annotations

from datetime import date
from typing import Any

from co_copilot.clause_library import quote_clause
from co_copilot.exceptions import ComplianceRuleError
from co_copilot.models import ComplianceCheck, ComplianceResult, ExtractionResult

CLAUSE_SUPPORT = {
    "scope addition": {"13.2"},
    "design change": {"13.3"},
    "differing site conditions": {"4.7"},
    "acceleration": {"8.6"},
    "prolongation/EOT": {"8.4", "13.6"},
    "force majeure": {"18.2"},
    "deletion/descope": {"13.4"},
    "disputed backcharge": {"15.4"},
}


def _days_between(start: date | None, end: date | None) -> int | None:
    return (end - start).days if start and end else None


def assess_compliance(
    result: ExtractionResult,
    metadata: dict[str, Any],
    clauses: dict[str, str],
) -> ComplianceResult:
    """Apply transparent notice, particulars, basis, and authority rules.

    Domain note:
        Time bars are often strictly construed because they are conditions
        precedent to entitlement. The engine therefore shows exact calendar-day
        arithmetic and never asks an LLM to decide the verdict.
    """
    rules = metadata.get("notice_rules", {})
    try:
        notice_limit = int(rules["event_notice_days"])
        particulars_limit = int(rules["particulars_days"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ComplianceRuleError(
            "Project metadata must define numeric event_notice_days and particulars_days."
        ) from exc

    event_date = result.value("event_date")
    notice_date = result.value("notice_date")
    particulars_date = result.value("particulars_date")
    notice_elapsed = _days_between(event_date, notice_date)
    particulars_elapsed = _days_between(event_date, particulars_date)
    checks: list[ComplianceCheck] = []

    notice_clause = quote_clause(clauses, "20.1")
    time_bar_clause = quote_clause(clauses, "20.3")
    if not event_date or not notice_date:
        time_bar_verdict = "AT RISK"
        notice_status = "WARN"
        notice_calc = (
            "Event date or notice date is missing; elapsed days cannot be evidenced."
        )
        notice_verdict = "Evidence gap"
    elif notice_elapsed is not None and notice_elapsed > notice_limit:
        time_bar_verdict = "TIME-BARRED"
        notice_status = "FAIL"
        overdue = notice_elapsed - notice_limit
        notice_calc = (
            f"{notice_date.isoformat()} − {event_date.isoformat()} = "
            f"{notice_elapsed} calendar days; {overdue} days over the "
            f"{notice_limit}-day limit."
        )
        notice_verdict = f"Late by {overdue} days"
    else:
        time_bar_verdict = "COMPLIANT"
        notice_status = "PASS"
        remaining = notice_limit - int(notice_elapsed or 0)
        notice_calc = (
            f"{notice_date.isoformat()} − {event_date.isoformat()} = "
            f"{notice_elapsed} calendar days; {remaining} days inside the "
            f"{notice_limit}-day limit."
        )
        notice_verdict = "Initial notice timely"
    checks.append(
        ComplianceCheck(
            "initial_notice",
            "Initial notice",
            notice_status,
            notice_verdict,
            f"Serve written notice within {notice_limit} calendar days of awareness.",
            notice_calc,
            "20.1 / 20.3",
            "\n\n".join(filter(None, (notice_clause, time_bar_clause))),
        )
    )

    if not event_date or not particulars_date:
        particulars_status = "WARN"
        particulars_verdict = "Detailed particulars not evidenced"
        particulars_calc = "Event date or particulars date is missing."
    elif particulars_elapsed is not None and particulars_elapsed > particulars_limit:
        late = particulars_elapsed - particulars_limit
        particulars_status = "FAIL"
        particulars_verdict = f"Particulars late by {late} days"
        particulars_calc = (
            f"{particulars_date.isoformat()} − {event_date.isoformat()} = "
            f"{particulars_elapsed} calendar days; {late} days over the "
            f"{particulars_limit}-day limit."
        )
    else:
        particulars_status = "PASS"
        particulars_verdict = "Detailed particulars timely"
        particulars_calc = (
            f"{particulars_date.isoformat()} − {event_date.isoformat()} = "
            f"{particulars_elapsed} calendar days; within {particulars_limit} days."
        )
    checks.append(
        ComplianceCheck(
            "particulars",
            "Detailed particulars",
            particulars_status,
            particulars_verdict,
            f"Submit detailed particulars within {particulars_limit} calendar days.",
            particulars_calc,
            "20.3",
            time_bar_clause,
        )
    )

    co_type = result.value("type")
    cited = set(result.value("cited_clause_refs", []))
    supported = CLAUSE_SUPPORT.get(co_type, set())
    matching = sorted(cited & supported)
    if not cited:
        basis_status, basis_verdict = "FAIL", "No contractual basis cited"
    elif not matching:
        basis_status, basis_verdict = "FAIL", "Cited clause does not support CO type"
    else:
        basis_status, basis_verdict = (
            "PASS",
            f"Supported by Clause {', '.join(matching)}",
        )
    basis_ref = matching[0] if matching else (sorted(cited)[0] if cited else None)
    checks.append(
        ComplianceCheck(
            "contractual_basis",
            "Contractual basis",
            basis_status,
            basis_verdict,
            f"{co_type} should cite one of: {', '.join(sorted(supported)) or 'mapped clause'}.",
            f"Cited {', '.join(sorted(cited)) or 'none'}; expected support "
            f"{', '.join(sorted(supported)) or 'not mapped'}.",
            basis_ref,
            quote_clause(clauses, basis_ref) if basis_ref else None,
        )
    )

    value = abs(float(result.value("cost_value", 0) or 0))
    thresholds = metadata.get("approval_thresholds", {})
    executive = float(thresholds.get("executive_committee", 5_000_000))
    director = float(thresholds.get("project_director", 1_000_000))
    if value >= executive:
        authority = "Executive Committee"
        authority_status = "WARN"
    elif value >= director:
        authority = "Project Director"
        authority_status = "INFO"
    else:
        authority = "Delegated commercial authority"
        authority_status = "PASS"
    checks.append(
        ComplianceCheck(
            "approval_authority",
            "Approval authority",
            authority_status,
            authority,
            "Route gross change value to the configured delegated authority.",
            f"Absolute value USD {value:,.0f}; director threshold USD {director:,.0f}; "
            f"executive threshold USD {executive:,.0f}.",
        )
    )

    score_weights = {"PASS": 1.0, "INFO": 1.0, "WARN": 0.5, "FAIL": 0.0}
    score = sum(score_weights[check.status] for check in checks) / len(checks)
    return ComplianceResult(
        document_id=result.document_id,
        co_number=result.value("co_number", result.document_id),
        time_bar_verdict=time_bar_verdict,
        checks=tuple(checks),
        notice_elapsed_days=notice_elapsed,
        particulars_elapsed_days=particulars_elapsed,
        score=score,
    )


def assess_many(
    results: tuple[ExtractionResult, ...],
    metadata: dict[str, Any],
    clauses: dict[str, str],
) -> tuple[ComplianceResult, ...]:
    """Assess a sequence of extractions in stable order."""
    return tuple(assess_compliance(result, metadata, clauses) for result in results)
