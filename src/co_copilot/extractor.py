"""Deterministic regex and lightweight spaCy-assisted fact extraction."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from co_copilot.models import Document, ExtractedField, ExtractionResult, TextSpan
from co_copilot.parsing import parse_currency_amount, parse_date

LOGGER = logging.getLogger(__name__)

_LABEL_PATTERNS = {
    "contractor": r"(?im)^Contractor\s*:\s*(?P<value>[^\n]+)",
    "originator": r"(?im)^Originator\s*:\s*(?P<value>[^\n]+)",
    "status": r"(?im)^Status\s*:\s*(?P<value>Draft|Submitted|Approved|Disputed)\b",
    "event_date": r"(?im)^Event Date\s*:\s*(?P<value>[^\n]+)",
    "notice_date": r"(?im)^Notice Date\s*:\s*(?P<value>[^\n]+)",
    "particulars_date": r"(?im)^Particulars Date\s*:\s*(?P<value>[^\n]+)",
}

_TYPE_PATTERNS = {
    "scope addition": (
        r"\b(add|addition|additional|install)\b",
        r"\b(outside the priced scope|requested|instructed)\b",
    ),
    "design change": (
        r"\b(design|redesign|rework|revised drawing)\b",
        r"\b(post-freeze|design freeze|approved design|client revised)\b",
    ),
    "differing site conditions": (
        r"\b(unexpected|uncharted|concealed|differing)\b",
        r"\b(gravel|buried|subsurface|physical condition|excavation)\b",
    ),
    "acceleration": (
        r"\b(acceleration|accelerate|recover)\b",
        r"\b(second shift|round-the-clock|additional crews|premium)\b",
    ),
    "prolongation/EOT": (
        r"\b(prolongation|extension of time|EOT)\b",
        r"\b(extended|late .*access|late .*availability|critical delay)\b",
    ),
    "force majeure": (
        r"\b(force majeure|exceptional external event)\b",
        r"\b(outside .* control|port closure|export-control|unforeseeable)\b",
    ),
    "deletion/descope": (
        r"\b(delete|deletion|descope|omit|omission)\b",
        r"\b(credit|avoided|redundant|unused)\b",
    ),
    "disputed backcharge": (
        r"\b(backcharge|deduction)\b",
        r"\b(nonconforming|defective|replacement|corrective)\b",
    ),
}

_TYPE_CLAUSE_HINTS = {
    "4.7": "differing site conditions",
    "8.4": "prolongation/EOT",
    "8.6": "acceleration",
    "13.2": "scope addition",
    "13.3": "design change",
    "13.4": "deletion/descope",
    "13.6": "prolongation/EOT",
    "15.4": "disputed backcharge",
    "18.2": "force majeure",
}

_EVENT_PHRASES = (
    "scope addition",
    "design change",
    "differing physical conditions",
    "instructed acceleration",
    "extension of time",
    "prolongation",
    "force majeure",
    "exceptional external event",
    "omission and descope",
    "backcharge",
    "critical path",
    "concurrent delay",
)


def _sentence_span(text: str, start: int, end: int) -> TextSpan:
    left_candidates = [text.rfind(token, 0, start) for token in ("\n", ". ")]
    left = max(left_candidates) + 1
    right_candidates = [
        position
        for position in (text.find("\n", end), text.find(". ", end))
        if position >= 0
    ]
    right = min(right_candidates) + 1 if right_candidates else len(text)
    return TextSpan(left, right, text[left:right].strip())


def _field_from_match(
    text: str, match: re.Match[str], value: Any, confidence: float
) -> ExtractedField:
    start, end = match.span("value") if "value" in match.groupdict() else match.span()
    return ExtractedField(value, confidence, _sentence_span(text, start, end))


def _search_label(text: str, field_name: str) -> re.Match[str] | None:
    return re.search(_LABEL_PATTERNS[field_name], text)


@lru_cache(maxsize=2)
def _load_spacy(model_name: str):
    """Load the configured model or a deterministic matcher-only fallback."""
    import spacy

    try:
        nlp = spacy.load(model_name, disable=["parser", "lemmatizer", "textcat"])
        LOGGER.info("Loaded spaCy model %s", model_name)
    except OSError:
        nlp = spacy.blank("en")
        LOGGER.warning(
            "spaCy model %s unavailable; using matcher-only fallback.", model_name
        )
    if "sentencizer" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def _spacy_signals(
    document: Document, model_name: str
) -> tuple[list[str], TextSpan | None, list[str]]:
    """Use spaCy NER and PhraseMatcher for entities and event language."""
    from spacy.matcher import PhraseMatcher

    nlp = _load_spacy(model_name)
    doc = nlp(document.text)
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("COMMERCIAL_EVENT", [nlp.make_doc(phrase) for phrase in _EVENT_PHRASES])
    matches = matcher(doc)
    phrases = list(
        dict.fromkeys(doc[start:end].text.lower() for _, start, end in matches)
    )
    source = None
    if matches:
        _, start, end = matches[0]
        source = _sentence_span(
            document.text, doc[start].idx, doc[end - 1].idx + len(doc[end - 1])
        )
    entities = [
        entity.text for entity in doc.ents if entity.label_ in {"ORG", "PERSON"}
    ]
    return phrases, source, entities


def _extract_clause_refs(document: Document) -> ExtractedField:
    basis = document.sections.get("basis", "")
    search_text = basis or document.text
    base_offset = document.text.find(search_text) if basis else 0
    pattern = re.compile(r"\b(?:Sub-)?Clause\s+(\d{1,2}(?:\.\d{1,2}){1,2})\b", re.I)
    matches = list(pattern.finditer(search_text))
    values = list(dict.fromkeys(match.group(1) for match in matches))
    if not matches:
        return ExtractedField([], 0.95 if basis else 0.65, None)
    start = base_offset + matches[0].start()
    end = base_offset + matches[-1].end()
    return ExtractedField(
        values,
        0.98 if basis else 0.78,
        _sentence_span(document.text, start, end),
    )


def _extract_cost(document: Document) -> ExtractedField:
    section = document.sections.get("cost_impact", "")
    search_text = section or document.text
    base_offset = document.text.find(search_text) if section else 0
    pattern = re.compile(
        r"(?:USD|US\$|\$)\s*(?P<value>[+-]?\d[\d,]*(?:\.\d+)?\s*[KMB]?)\b",
        re.I,
    )
    match = pattern.search(search_text)
    if not match:
        return ExtractedField(None, 0.0, None)
    value = parse_currency_amount(match.group("value"))
    start, end = base_offset + match.start("value"), base_offset + match.end("value")
    return ExtractedField(
        value,
        0.99 if section else 0.75,
        _sentence_span(document.text, start, end),
    )


def _extract_schedule(document: Document) -> ExtractedField:
    section = document.sections.get("schedule_impact", "")
    search_text = section or document.text
    base_offset = document.text.find(search_text) if section else 0
    match = re.search(
        r"(?P<value>[+-]?\d{1,4})\s+(?:calendar\s+)?days?\b", search_text, re.I
    )
    if not match:
        return ExtractedField(None, 0.0, None)
    start, end = base_offset + match.start("value"), base_offset + match.end("value")
    return ExtractedField(
        int(match.group("value")),
        0.98 if section else 0.72,
        _sentence_span(document.text, start, end),
    )


def _classify(document: Document, clauses: Iterable[str]) -> ExtractedField:
    narrative = " ".join(
        document.sections.get(name, "") for name in ("description", "basis")
    )
    search_text = narrative or document.text
    scores: dict[str, int] = {}
    for label, patterns in _TYPE_PATTERNS.items():
        scores[label] = sum(
            bool(re.search(pattern, search_text, re.I)) for pattern in patterns
        )
    for clause in clauses:
        hinted = _TYPE_CLAUSE_HINTS.get(clause)
        if hinted:
            scores[hinted] += 2
    best = max(scores, key=lambda key: (scores[key], key))
    total = scores[best]
    confidence = min(0.99, 0.60 + 0.10 * total)
    evidence_pattern = _TYPE_PATTERNS[best][0]
    match = re.search(evidence_pattern, document.text, re.I)
    source = _sentence_span(document.text, *match.span()) if match else None
    return ExtractedField(best, confidence, source)


def extract(
    document: Document,
    low_confidence: float = 0.72,
    spacy_model: str = "en_core_web_sm",
) -> ExtractionResult:
    """Extract auditable canonical facts from a change-order document.

    spaCy is intentionally optional at runtime: labeled commercial fields and
    critical numbers remain deterministic. This keeps cold starts predictable
    and allows offline operation even when the small language model is absent.
    """
    fields: dict[str, ExtractedField] = {}
    event_phrases, event_source, named_entities = _spacy_signals(document, spacy_model)
    number_match = re.search(r"\b(?P<value>CO-\d{3})\b", document.text, re.I)
    fields["co_number"] = (
        _field_from_match(
            document.text, number_match, number_match.group("value").upper(), 1.0
        )
        if number_match
        else ExtractedField(document.document_id, 0.55, None)
    )
    for name in ("contractor", "originator", "status"):
        match = _search_label(document.text, name)
        value = match.group("value").strip() if match else None
        if not value and named_entities and name in {"contractor", "originator"}:
            value = named_entities[0]
        if name == "status" and value:
            value = value.lower()
        if match:
            fields[name] = _field_from_match(document.text, match, value, 0.99)
        elif value:
            fields[name] = ExtractedField(value, 0.62, None)
        else:
            fields[name] = ExtractedField(None, 0.0, None)
    slash_dates = re.findall(r"(?m)Date\s*:\s*(\d{1,2})/(\d{1,2})/\d{4}", document.text)
    day_first: bool | None = None
    if any(int(first) > 12 for first, _ in slash_dates):
        day_first = True
    elif any(int(second) > 12 for _, second in slash_dates):
        day_first = False
    for name in ("event_date", "notice_date", "particulars_date"):
        match = _search_label(document.text, name)
        raw = match.group("value").strip() if match else None
        parsed = parse_date(raw, day_first=day_first)
        confidence = 0.98 if parsed.value else (0.90 if raw else 0.0)
        fields[name] = (
            _field_from_match(document.text, match, parsed.value, confidence)
            if match
            else ExtractedField(None, 0.0, None)
        )
    fields["cost_value"] = _extract_cost(document)
    fields["schedule_days"] = _extract_schedule(document)
    fields["cited_clause_refs"] = _extract_clause_refs(document)
    fields["type"] = _classify(document, fields["cited_clause_refs"].value)
    fields["event_phrases"] = ExtractedField(
        event_phrases,
        0.86 if event_phrases else 0.55,
        event_source,
    )

    warnings = list(document.warnings)
    for name, field in fields.items():
        if field.value is not None and field.confidence < low_confidence:
            message = f"{name} confidence {field.confidence:.0%} is below threshold."
            warnings.append(message)
            LOGGER.warning("%s %s", document.filename, message)
    LOGGER.info("Extracted %s", document.filename)
    return ExtractionResult(
        document_id=document.document_id,
        filename=document.filename,
        fields=fields,
        text=document.text,
        warnings=tuple(warnings),
    )


def extract_many(
    documents: Iterable[Document],
    low_confidence: float = 0.72,
    spacy_model: str = "en_core_web_sm",
) -> tuple[ExtractionResult, ...]:
    """Extract a deterministic sequence of documents."""
    return tuple(
        extract(document, low_confidence, spacy_model) for document in documents
    )
