"""Hand-verified deterministic compliance arithmetic."""

from __future__ import annotations

from pathlib import Path

import pytest

from co_copilot.clause_library import load_clause_library, quote_clause
from co_copilot.compliance import assess_compliance
from co_copilot.exceptions import ComplianceRuleError


def test_late_notice_and_particulars_math(demo_result) -> None:
    by_id = {item.document_id: item for item in demo_result.compliance}
    co3 = by_id["CO-003"]
    # Hand verification: 20 Mar - 1 Mar = 19 calendar days; 19 - 14 = 5 late.
    assert co3.notice_elapsed_days == 19
    assert co3.time_bar_verdict == "TIME-BARRED"
    assert "5 days over" in co3.checks[0].calculation
    # Hand verification: 5 Apr - 1 Mar = 35 calendar days; 35 - 28 = 7 late.
    assert co3.particulars_elapsed_days == 35
    assert "7 days over" in co3.checks[1].calculation


def test_boundary_day_is_compliant_but_late_particulars_fail(demo_result) -> None:
    by_id = {item.document_id: item for item in demo_result.compliance}
    co15 = by_id["CO-015"]
    # Hand verification: 24 Aug - 10 Aug = exactly 14 calendar days.
    assert co15.notice_elapsed_days == 14
    assert co15.time_bar_verdict == "COMPLIANT"
    # Hand verification: 14 Sep - 10 Aug = 35 calendar days, seven late.
    assert co15.particulars_elapsed_days == 35
    assert co15.checks[1].status == "FAIL"


def test_missing_notice_is_at_risk_and_not_assumed_compliant(demo_result) -> None:
    by_id = {item.document_id: item for item in demo_result.compliance}
    assert by_id["CO-006"].time_bar_verdict == "AT RISK"
    assert by_id["CO-017"].time_bar_verdict == "AT RISK"


def test_clause_quotes_and_basis_mapping(demo_result, project_root: Path) -> None:
    library = load_clause_library(project_root / "data/contract/clauses")
    assert len(library) == 15
    assert "14 calendar days" in str(quote_clause(library, "20.1"))
    co1 = next(item for item in demo_result.compliance if item.document_id == "CO-001")
    assert co1.checks[2].status == "PASS"
    co9 = next(item for item in demo_result.compliance if item.document_id == "CO-009")
    assert co9.checks[2].status == "FAIL"


def test_missing_notice_rules_raise_actionable_error(
    demo_result, project_root: Path
) -> None:
    library = load_clause_library(project_root / "data/contract/clauses")
    with pytest.raises(ComplianceRuleError, match="event_notice_days"):
        assess_compliance(demo_result.extractions[0], {}, library)
