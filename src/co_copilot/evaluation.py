"""Gold-standard evaluation for honest extraction accuracy reporting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from co_copilot.models import ExtractionResult

EVALUATED_FIELDS = (
    "type",
    "cost_value",
    "schedule_days",
    "cited_clause_refs",
    "notice_date",
    "event_date",
    "status",
)


@dataclass(frozen=True)
class FieldScore:
    """Precision, recall, and F1 for one canonical field."""

    field: str
    precision: float
    recall: float
    f1: float
    support: int
    true_positive: int
    false_positive: int
    false_negative: int


@dataclass(frozen=True)
class EvaluationReport:
    """Per-field and micro-overall extraction results."""

    scores: tuple[FieldScore, ...]
    overall: FieldScore
    split: str


def _normalize_clause(value: object) -> str:
    return re.sub(r"[^0-9.]", "", str(value)).strip(".")


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _counts(expected: Any, actual: Any, field: str) -> tuple[int, int, int]:
    if field == "cited_clause_refs":
        expected_set = {_normalize_clause(item) for item in expected or []}
        actual_set = {_normalize_clause(item) for item in actual or []}
        return (
            len(expected_set & actual_set),
            len(actual_set - expected_set),
            len(expected_set - actual_set),
        )
    expected_value = _normalize_scalar(expected)
    actual_value = _normalize_scalar(actual)
    if expected_value is None:
        return (0, 1, 0) if actual_value is not None else (0, 0, 0)
    if expected_value == actual_value:
        return 1, 0, 0
    return 0, int(actual_value is not None), 1


def _score(field: str, counts: tuple[int, int, int], support: int) -> FieldScore:
    tp, fp, fn = counts
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return FieldScore(field, precision, recall, f1, support, tp, fp, fn)


def evaluate(
    results: tuple[ExtractionResult, ...],
    gold_path: Path,
    split: str = "all",
) -> EvaluationReport:
    """Compare extraction output with hand-labeled truth."""
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    allowed = set(gold["documents"])
    if split == "development":
        allowed = set(gold["metadata"]["development_split"])
    elif split == "held_out":
        allowed = set(gold["metadata"]["held_out_split"])

    per_field: list[FieldScore] = []
    overall = [0, 0, 0]
    selected = [result for result in results if result.document_id in allowed]
    for field in EVALUATED_FIELDS:
        counts = [0, 0, 0]
        support = 0
        for result in selected:
            expected = gold["documents"][result.document_id][field]
            actual = result.value(field)
            row = _counts(expected, actual, field)
            counts = [sum(values) for values in zip(counts, row, strict=True)]
            if expected is not None and expected != []:
                support += len(expected) if isinstance(expected, list) else 1
        field_score = _score(field, tuple(counts), support)
        per_field.append(field_score)
        overall = [sum(values) for values in zip(overall, counts, strict=True)]
    return EvaluationReport(
        scores=tuple(per_field),
        overall=_score(
            "overall", tuple(overall), sum(score.support for score in per_field)
        ),
        split=split,
    )


def to_markdown(report: EvaluationReport) -> str:
    """Render a methodology-ready score table."""
    lines = [
        f"### Extraction evaluation — {report.split} split",
        "",
        "| Field | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for score in (*report.scores, report.overall):
        lines.append(
            f"| {score.field} | {score.precision:.3f} | {score.recall:.3f} | "
            f"{score.f1:.3f} | {score.support} |"
        )
    return "\n".join(lines)
