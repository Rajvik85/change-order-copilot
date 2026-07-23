"""Typed domain models shared across the deterministic pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Verdict = Literal["COMPLIANT", "AT RISK", "TIME-BARRED", "NOT ASSESSED"]
CheckStatus = Literal["PASS", "WARN", "FAIL", "INFO"]


@dataclass(frozen=True)
class TextSpan:
    """Character offsets and sentence evidence for a traced fact."""

    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ExtractedField:
    """One extracted value with confidence and auditable source evidence."""

    value: Any
    confidence: float
    source: TextSpan | None


@dataclass(frozen=True)
class Document:
    """Normalized source document and best-effort labeled sections."""

    document_id: str
    filename: str
    path: Path | None
    text: str
    sections: dict[str, str]
    warnings: tuple[str, ...] = ()
    content_hash: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    """Canonical structured facts produced by the offline extractor."""

    document_id: str
    filename: str
    fields: dict[str, ExtractedField]
    text: str
    warnings: tuple[str, ...] = ()

    def value(self, field_name: str, default: Any = None) -> Any:
        """Return a field value while keeping call sites concise."""
        item = self.fields.get(field_name)
        return item.value if item is not None else default

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result without losing evidence spans."""
        return asdict(self)


@dataclass(frozen=True)
class ComplianceCheck:
    """One deterministic checklist line with transparent inputs and rule."""

    check_id: str
    label: str
    status: CheckStatus
    verdict: str
    rule: str
    calculation: str
    clause_reference: str | None = None
    clause_text: str | None = None


@dataclass(frozen=True)
class ComplianceResult:
    """Deterministic contractual position for a single change order."""

    document_id: str
    co_number: str
    time_bar_verdict: Verdict
    checks: tuple[ComplianceCheck, ...]
    notice_elapsed_days: int | None = None
    particulars_elapsed_days: int | None = None
    score: float = 0.0


@dataclass(frozen=True)
class Finding:
    """Ranked portfolio finding and its commercial rationale."""

    finding_id: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str
    message: str
    rationale: str
    affected_cos: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationIssue:
    """Friendly, actionable validation feedback."""

    severity: Literal["error", "warning", "info"]
    field: str
    message: str
    fix_hint: str


@dataclass(frozen=True)
class ValidationReport:
    """Validation outcome for one supplied file or metadata object."""

    name: str
    accepted: bool
    issues: tuple[ValidationIssue, ...] = ()
    sections_found: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineResult:
    """Complete or provisional deterministic pipeline output."""

    documents: tuple[Document, ...]
    extractions: tuple[ExtractionResult, ...]
    compliance: tuple[ComplianceResult, ...]
    analytics: dict[str, Any]
    provisional: bool = False
    messages: tuple[str, ...] = ()
    generated_at: str = ""
    config_hash: str = ""
    input_hash: str = ""


@dataclass(frozen=True)
class LLMResult:
    """Typed response for both configured and unavailable LLM paths."""

    status: Literal["ok", "not_configured", "error"]
    content: str
    provider: str | None = None
    model: str | None = None
    grounded_facts: dict[str, Any] = field(default_factory=dict)
    clauses: tuple[str, ...] = ()
    label: str = "AI-assisted draft — human review required"


@dataclass(frozen=True)
class MappingProfile:
    """Reusable mapping from variable client headers to canonical fields."""

    name: str
    mappings: dict[str, str]
    created_at: str
