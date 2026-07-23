"""Mocked optional-LLM tests; no live provider calls are permitted."""

from __future__ import annotations

from pathlib import Path

from co_copilot.clause_library import load_clause_library
from co_copilot.config import load_config
from co_copilot.llm_layer import generate_review, grounding_payload


class FakeAdapter:
    """Deterministic provider double for success and retry tests."""

    provider = "mock"
    model = "mock-grounded-1"

    def __init__(self, failures: int = 0) -> None:
        self.failures = failures
        self.calls = 0
        self.last_user = ""

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        self.last_user = user
        assert "never invent" in system.lower()
        if self.calls <= self.failures:
            raise TimeoutError("synthetic timeout")
        return "Facts\nGrounded mock draft.\n\nRecommended action\nHuman review."


def _context(demo_result, project_root: Path):
    extraction = demo_result.extractions[0]
    compliance = demo_result.compliance[0]
    clauses = load_clause_library(project_root / "data/contract/clauses")
    return extraction, compliance, clauses


def test_no_key_returns_typed_not_configured(
    demo_result, project_root: Path, monkeypatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    extraction, compliance, clauses = _context(demo_result, project_root)
    result = generate_review(
        "review_memo",
        extraction,
        compliance,
        clauses,
        load_config(project_root / "config.yaml"),
    )
    assert result.status == "not_configured"
    assert "fully available offline" in result.content
    assert result.grounded_facts["fixed_time_bar_verdict"] == "COMPLIANT"


def test_mocked_success_is_grounded_and_labeled(
    demo_result, project_root: Path
) -> None:
    extraction, compliance, clauses = _context(demo_result, project_root)
    adapter = FakeAdapter()
    result = generate_review(
        "review_memo",
        extraction,
        compliance,
        clauses,
        load_config(project_root / "config.yaml"),
        adapter=adapter,
    )
    assert result.status == "ok"
    assert result.provider == "mock"
    assert "human review required" in result.label.lower()
    assert '"fixed_time_bar_verdict": "COMPLIANT"' in adapter.last_user
    assert "13.2" in result.clauses
    assert extraction.text not in adapter.last_user


def test_retry_backoff_is_bounded(demo_result, project_root: Path) -> None:
    extraction, compliance, clauses = _context(demo_result, project_root)
    adapter = FakeAdapter(failures=2)
    sleeps: list[float] = []
    result = generate_review(
        "executive_summary",
        extraction,
        compliance,
        clauses,
        load_config(project_root / "config.yaml"),
        adapter=adapter,
        sleep=sleeps.append,
    )
    assert result.status == "ok"
    assert adapter.calls == 3
    assert sleeps == [1.0, 2.0]


def test_error_paths_remain_typed(demo_result, project_root: Path) -> None:
    extraction, compliance, clauses = _context(demo_result, project_root)
    unknown = generate_review(
        "invented_capability",
        extraction,
        compliance,
        clauses,
        load_config(project_root / "config.yaml"),
        adapter=FakeAdapter(),
    )
    assert unknown.status == "error"
    failing = generate_review(
        "weakness_review",
        extraction,
        compliance,
        clauses,
        load_config(project_root / "config.yaml"),
        adapter=FakeAdapter(failures=99),
        sleep=lambda _: None,
    )
    assert failing.status == "error"
    assert "bounded retries" in failing.content


def test_grounding_contains_only_relevant_clauses(
    demo_result, project_root: Path
) -> None:
    extraction, compliance, clauses = _context(demo_result, project_root)
    payload = grounding_payload(extraction, compliance, clauses)
    assert set(payload["relevant_clauses"]) == {"13.2", "20.1", "20.3"}
    assert payload["structured_facts"]["cost_value"] == 1_250_000
