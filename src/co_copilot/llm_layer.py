"""Provider-agnostic, grounded, optional LLM memo enhancement."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, Protocol

from co_copilot.models import ComplianceResult, ExtractionResult, LLMResult
from co_copilot.prompts import PROMPTS


class ProviderAdapter(Protocol):
    """Minimal adapter contract shared by optional provider SDKs."""

    provider: str
    model: str

    def complete(self, system: str, user: str) -> str:
        """Return one grounded completion."""


class OpenAIAdapter:
    """OpenAI Responses API adapter loaded only when explicitly configured."""

    provider = "openai"

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key, timeout=timeout)

    def complete(self, system: str, user: str) -> str:
        """Request a bounded completion from the configured OpenAI model."""
        response = self._client.responses.create(
            model=self.model,
            instructions=system,
            input=user,
        )
        return response.output_text


class AnthropicAdapter:
    """Anthropic Messages API adapter loaded only when explicitly configured."""

    provider = "anthropic"

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        from anthropic import Anthropic

        self.model = model
        self._client = Anthropic(api_key=api_key, timeout=timeout)

    def complete(self, system: str, user: str) -> str:
        """Request a bounded completion from the configured Anthropic model."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1600,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )


def configured_provider() -> str | None:
    """Return the first configured provider without exposing secret values."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def _adapter(provider: str, config: dict[str, Any]) -> ProviderAdapter:
    timeout = float(config["llm"]["timeout_seconds"])
    if provider == "openai":
        return OpenAIAdapter(
            os.environ["OPENAI_API_KEY"],
            str(config["llm"]["openai_model"]),
            timeout,
        )
    if provider == "anthropic":
        return AnthropicAdapter(
            os.environ["ANTHROPIC_API_KEY"],
            str(config["llm"]["anthropic_model"]),
            timeout,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


def grounding_payload(
    extraction: ExtractionResult,
    compliance: ComplianceResult,
    clause_texts: dict[str, str],
) -> dict[str, Any]:
    """Create the exact structured context disclosed in the UI grounding panel."""
    facts = {
        name: field.value
        for name, field in extraction.fields.items()
        if name != "event_phrases"
    }
    cited = extraction.value("cited_clause_refs", [])
    relevant_clauses = {
        reference: clause_texts[reference]
        for reference in cited
        if reference in clause_texts
    }
    for reference in ("20.1", "20.3"):
        if reference in clause_texts:
            relevant_clauses[reference] = clause_texts[reference]
    return {
        "structured_facts": facts,
        "deterministic_checks": [asdict(check) for check in compliance.checks],
        "fixed_time_bar_verdict": compliance.time_bar_verdict,
        "relevant_clauses": relevant_clauses,
    }


def generate_review(
    capability: str,
    extraction: ExtractionResult,
    compliance: ComplianceResult,
    clause_texts: dict[str, str],
    config: dict[str, Any],
    provider: str | None = None,
    adapter: ProviderAdapter | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> LLMResult:
    """Generate one grounded draft or return a typed, non-crashing status."""
    selected = provider or configured_provider()
    payload = grounding_payload(extraction, compliance, clause_texts)
    if not selected and adapter is None:
        return LLMResult(
            status="not_configured",
            content=(
                "Optional AI is not configured. The extraction, compliance, analytics, "
                "and exports remain fully available offline."
            ),
            grounded_facts=payload,
        )
    prompt = PROMPTS.get(capability)
    if prompt is None:
        return LLMResult(
            status="error",
            content=f"Unknown review capability: {capability}",
            provider=selected,
            grounded_facts=payload,
        )
    try:
        client = adapter or _adapter(str(selected), config)
    except (ImportError, KeyError, ValueError) as exc:
        return LLMResult(
            status="error",
            content=f"Optional provider setup is incomplete: {exc}",
            provider=selected,
            grounded_facts=payload,
        )
    user = (
        f"TASK\n{prompt.task}\n\nOUTPUT SCHEMA\n{prompt.output_schema}\n\n"
        f"GROUNDING PAYLOAD\n{json.dumps(payload, default=str, indent=2)}"
    )
    retries = int(config["llm"]["max_retries"])
    backoff = float(config["llm"]["retry_backoff_seconds"])
    last_error = ""
    for attempt in range(retries + 1):
        try:
            content = client.complete(prompt.system, user).strip()
            if not content:
                raise ValueError("Provider returned an empty response.")
            return LLMResult(
                status="ok",
                content=content,
                provider=client.provider,
                model=client.model,
                grounded_facts=payload,
                clauses=tuple(payload["relevant_clauses"]),
            )
        except (TimeoutError, ConnectionError, RuntimeError, ValueError) as exc:
            last_error = str(exc)
            if attempt < retries:
                sleep(backoff * (2**attempt))
    return LLMResult(
        status="error",
        content=f"The optional provider failed after bounded retries: {last_error}",
        provider=getattr(client, "provider", selected),
        model=getattr(client, "model", None),
        grounded_facts=payload,
    )
