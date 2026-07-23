"""Flexible client-column mapping to the canonical register schema."""

from __future__ import annotations

import difflib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from co_copilot.models import MappingProfile, ValidationIssue
from co_copilot.storage import atomic_write

CANONICAL_SCHEMA = {
    "co_number": ("co", "change order", "variation number", "reference"),
    "event_date": ("event date", "occurrence date", "cause date"),
    "notice_date": ("notice date", "notification", "notice served"),
    "particulars_date": ("particulars", "claim date", "detailed submission"),
    "contractor": ("contractor", "vendor", "supplier", "counterparty"),
    "originator": ("originator", "raised by", "requestor"),
    "type": ("type", "change type", "category"),
    "cost_value": ("cost", "amount", "claim amount", "value", "forecast exposure"),
    "schedule_days": ("days", "delay", "schedule impact", "eot"),
    "status": ("status", "stage", "approval status"),
    "cited_clause_refs": ("clause", "contract basis", "clause reference"),
}


def suggest_mappings(headers: list[str], cutoff: float = 0.52) -> dict[str, str]:
    """Suggest internal fields for unfamiliar headers using deterministic fuzzy match."""
    suggestions: dict[str, str] = {}
    for header in headers:
        candidate_scores: list[tuple[float, str]] = []
        normalized = header.strip().lower().replace("_", " ")
        for canonical, aliases in CANONICAL_SCHEMA.items():
            score = max(
                difflib.SequenceMatcher(None, normalized, alias).ratio()
                for alias in (canonical.replace("_", " "), *aliases)
            )
            candidate_scores.append((score, canonical))
        score, canonical = max(candidate_scores)
        if score >= cutoff:
            suggestions[header] = canonical
    return suggestions


def validate_mapping(mapping: dict[str, str]) -> tuple[ValidationIssue, ...]:
    """Validate uniqueness and minimum fields after user confirmation."""
    issues: list[ValidationIssue] = []
    destinations = [value for value in mapping.values() if value]
    duplicates = sorted(
        {value for value in destinations if destinations.count(value) > 1}
    )
    if duplicates:
        issues.append(
            ValidationIssue(
                "error",
                "mapping",
                f"Multiple columns map to: {', '.join(duplicates)}.",
                "Choose exactly one source column for each canonical field.",
            )
        )
    for required in ("co_number", "cost_value", "status"):
        if required not in destinations:
            issues.append(
                ValidationIssue(
                    "warning",
                    required,
                    f"No source column is mapped to {required}.",
                    "Confirm the closest client header or leave it blank intentionally.",
                )
            )
    return tuple(issues)


def save_mapping_profile(folder: Path, name: str, mappings: dict[str, str]) -> Path:
    """Save a reusable mapping only inside the caller's session folder."""
    safe_name = "".join(
        character for character in name if character.isalnum() or character in "-_"
    )
    safe_name = safe_name[:80] or "mapping"
    profile = MappingProfile(safe_name, mappings, datetime.now(UTC).isoformat())
    path = folder / "mapping_profiles" / f"{safe_name}.json"
    atomic_write(path, json.dumps(asdict(profile), indent=2).encode("utf-8"))
    return path


def load_mapping_profile(path: Path) -> MappingProfile:
    """Load a JSON mapping profile without executable deserialization."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MappingProfile(**payload)
