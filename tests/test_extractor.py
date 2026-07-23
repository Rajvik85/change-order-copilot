"""Extraction correctness and CI accuracy-floor tests."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from co_copilot.evaluation import evaluate, to_markdown
from co_copilot.parsing import parse_currency_amount, parse_date


def test_headline_extraction_values(demo_result) -> None:
    by_id = {item.document_id: item for item in demo_result.extractions}
    assert by_id["CO-001"].value("cost_value") == 1_250_000
    assert by_id["CO-004"].value("schedule_days") == -18
    assert by_id["CO-005"].value("cited_clause_refs") == ["8.4", "13.6"]
    assert by_id["CO-014"].value("event_date") == date(2026, 8, 5)
    assert by_id["CO-017"].value("notice_date") is None


def test_every_numeric_fact_has_source_evidence(demo_result) -> None:
    for result in demo_result.extractions:
        for field in ("cost_value", "schedule_days"):
            extracted = result.fields[field]
            assert extracted.value is not None
            assert extracted.source is not None
            assert extracted.source.text
            assert 0 <= extracted.source.start < extracted.source.end


def test_accuracy_floor_all_and_held_out(demo_result, project_root: Path) -> None:
    gold = project_root / "data/gold_standard.json"
    report = evaluate(demo_result.extractions, gold, split="all")
    held_out = evaluate(demo_result.extractions, gold, split="held_out")
    assert report.overall.f1 >= 0.90
    assert held_out.overall.f1 >= 0.90
    assert "| overall |" in to_markdown(report)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("USD 1.2M", 1_200_000),
        ("-2,400,000", -2_400_000),
        ("$875K", 875_000),
        ("1.5B", 1_500_000_000),
        ("not money", None),
    ],
)
def test_currency_units_and_separators(raw: str, expected: float | None) -> None:
    assert parse_currency_amount(raw) == expected


def test_multiformat_dates_excel_serial_and_ambiguity() -> None:
    assert parse_date("2026-07-23").value == date(2026, 7, 23)
    assert parse_date("23-07-2026").value == date(2026, 7, 23)
    assert parse_date("July 23, 2026").value == date(2026, 7, 23)
    assert parse_date(2).value == date(1900, 1, 1)
    ambiguous = parse_date("08/05/2026", day_first=False)
    assert ambiguous.value == date(2026, 8, 5)
    assert "Ambiguous" in str(ambiguous.warning)
    assert parse_date("not a date").value is None
