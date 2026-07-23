"""Portfolio aggregation and finding-rule tests."""

from __future__ import annotations

import pytest

from co_copilot.analytics import build_register


def test_portfolio_totals_and_scorecard(demo_result) -> None:
    summary = demo_result.analytics
    assert summary["total_exposure"] == pytest.approx(26_660_000)
    assert summary["gross_positive_exposure"] == pytest.approx(31_560_000)
    assert summary["exposure_percent"] == pytest.approx(10.664)
    assert summary["time_barred_value"] == pytest.approx(10_000_000)
    assert summary["compliance_rate"] == pytest.approx(13 / 18)
    assert summary["schedule_days_claimed"] == 256
    assert summary["schedule_days_recovery"] == -58


def test_register_and_findings_are_auditable(demo_result) -> None:
    register = build_register(demo_result.extractions, demo_result.compliance)
    assert len(register) == 18
    assert register.iloc[-1]["cumulative_cost"] == pytest.approx(26_660_000)
    ids = {finding.finding_id for finding in demo_result.analytics["findings"]}
    assert {"F-TIMEBAR", "F-BASIS"} <= ids
    cumulative = [item for item in ids if item.startswith("F-CUM")]
    assert cumulative
