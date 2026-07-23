"""Schema and document validation with fix-oriented feedback."""

from __future__ import annotations

from datetime import date
from typing import Any

from co_copilot.models import Document, ValidationIssue, ValidationReport


def validate_document(document: Document) -> ValidationReport:
    """Validate a parsed document without treating messiness as a crash."""
    issues: list[ValidationIssue] = []
    if len(document.text.strip()) < 80:
        issues.append(
            ValidationIssue(
                "error",
                "text",
                "The document contains too little readable text for analysis.",
                "Add the CO header, event narrative, impacts, and status.",
            )
        )
    required = {"header", "description", "impacts"}
    missing = sorted(required - set(document.sections))
    if missing:
        issues.append(
            ValidationIssue(
                "warning",
                "sections",
                f"Could not confidently identify: {', '.join(missing)}.",
                "Use simple headings such as Header, Event Description, and Impacts.",
            )
        )
    return ValidationReport(
        name=document.filename,
        accepted=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
        sections_found=tuple(document.sections),
    )


def validate_project_metadata(metadata: dict[str, Any]) -> tuple[ValidationIssue, ...]:
    """Check the minimum commercial metadata required by deterministic rules."""
    issues: list[ValidationIssue] = []
    if float(metadata.get("contract_sum", 0)) <= 0:
        issues.append(
            ValidationIssue(
                "error",
                "contract_sum",
                "Contract sum must be greater than zero.",
                "Enter the original awarded contract value.",
            )
        )
    for key in ("commencement_date",):
        value = metadata.get(key)
        try:
            date.fromisoformat(str(value))
        except (TypeError, ValueError):
            issues.append(
                ValidationIssue(
                    "error",
                    key,
                    f"{key.replace('_', ' ').title()} must use YYYY-MM-DD.",
                    "Example: 2026-01-01.",
                )
            )
    return tuple(issues)
