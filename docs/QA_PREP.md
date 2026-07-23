# Interview QA Preparation

## Domain and commercial judgment

### 1. Why do change orders exist?

They control a departure from the contractual baseline by recording cause,
allocation, procedure, valuation, and time effect. Without that chain, an
estimate is not a defensible commercial position.

### 2. Why are time bars strictly enforced?

They protect contemporaneous investigation and mitigation. Where drafted as a
condition precedent, missing the period can defeat entitlement regardless of
quantum. The tool shows procedure separately from merit.

### 3. Why is a missing notice date “at risk,” not “time-barred”?

Absence of evidence is not proof of lateness. Assuming compliance would be
equally unsafe. “At risk” accurately communicates the evidence gap.

### 4. Why calculate calendar days instead of business days?

The synthetic clause says calendar days. Day basis is a contract fact, so the
real system would configure holidays and business-day calendars where required.

### 5. Why not add all schedule-impact days?

CO delays can overlap, be non-critical, or become concurrent. The dashboard
shows claimed exposure; a logic-linked schedule analysis determines entitlement.

### 6. What makes an acceleration claim credible?

A written instruction, a target milestone, incremental resources and premium,
productivity assumptions, and a recovery fragnet showing the effect.

### 7. What is the difference between EOT and prolongation?

EOT is time relief. Prolongation is demonstrable time-related cost. Concurrency
can allow time while limiting cost.

### 8. Why include negative values?

Omissions and backcharges are commercial credits. Ignoring them overstates net
exposure and hides package negotiation offsets.

### 9. What is cumulative impact?

Many small changes may interact through congestion, resequencing, supervision,
or disruption. The flag prompts package-level review; it does not calculate
entitlement.

### 10. How would you use the portfolio findings in a meeting?

Start with procedural jeopardy, then gross/net value, concentration, missing
basis, and schedule evidence. Agree actions, owners, and dates before debating
detailed rates.

## NLP and evaluation

### 11. Why not fine-tune a model on 18 documents?

Eighteen examples cannot support a credible generalization claim. The dominant
fields are structured patterns, so deterministic extraction plus a frozen gold
benchmark is more honest and auditable.

### 12. Why use spaCy at all?

It provides tokenization, optional NER, sentence handling, and PhraseMatcher
signals for event language. Critical numbers remain regex-grounded.

### 13. How is the held-out split protected?

Its IDs are declared in data before rule implementation and evaluation reports
it separately. In a team, labels would be access-controlled and reviewed by
someone other than the extractor author.

### 14. Why micro-F1?

It summarizes field-level errors while preserving the TP/FP/FN accounting.
Per-field tables remain essential because a strong status score must not hide a
weak cost or date extractor.

### 15. Why is perfect F1 not a production claim?

The corpus is small, synthetic, and intentionally constrained. The README and
methodology explicitly limit the claim to regression performance on this fixture.

### 16. How are clause references normalized?

Formatting words and punctuation are removed while dotted numeric identity is
preserved. Comparison is set-based, so order does not matter.

### 17. How do you stop the notice rule's “14 days” becoming schedule impact?

Numeric regexes search the labeled impact sections first. Section scope is a
simple, powerful false-positive control.

### 18. What input will break extraction?

Image-only PDFs, multi-event letters, table-only Word content, unfamiliar
currencies, ambiguous dates, and highly implicit basis language. These are
documented, not hidden.

### 19. What would you measure next?

Performance by format and contractor, span accuracy, ambiguity rate,
inter-annotator agreement, and calibration of confidence against observed error.

### 20. When would a learned model become justified?

When there is a sufficiently large, authorized, representative labeled corpus
and rules plateau on implicit language. Deterministic validation and compliance
would still remain.

## LLM engineering

### 21. How do you prevent hallucinated clause citations?

The model sees only cited/relevant loaded clauses, cannot create references by
instruction, and the UI discloses the payload. Human review is mandatory.

### 22. Why not send raw documents?

Structured facts reduce context, improve provenance, limit irrelevant clause
surface, and make grounding testable. Raw page context may later be added only
for cited spans.

### 23. Can the LLM change a time-bar verdict?

No. The verdict is computed before the LLM call, supplied as a fixed fact, and
used unchanged in UI and exports.

### 24. What happens without an API key?

The provider function returns a typed `not_configured` result. Every core page
works, and the memo page shows an intentionally designed example state.

### 25. How are provider failures handled?

Requests have SDK timeouts, bounded exponential retries, and typed errors.
There is no silent provider switch and CI injects a mock adapter.

### 26. How would you evaluate memo quality?

Spot-check across compliance and change types for factual consistency,
citation validity, verdict preservation, missing-fact behavior, usefulness,
tone, and overstatement.

### 27. Why store prompts in code?

Versioned, documented constants make review and regression possible. Scattered
UI strings are hard to govern or compare.

## Product and software engineering

### 28. Why a multi-page app instead of a script?

Commercial review is a journey: intake, portfolio triage, record-level evidence,
procedure, narrative, and report. Session state preserves that mental model.

### 29. What is the “wow” feature technically?

Every fact stores normalized character offsets and sentence evidence. Selecting
the fact highlights the same source range beside the deterministic checklist.

### 30. How do exports remain auditable?

They include application version, UTC timestamp, configuration hash, input hash,
fixed checks, and AI labels. Atomic writes avoid partial artifacts.

## Resilience, flexibility, and governance

### 31. What happens with a 200 MB upload?

It is rejected before parsing with a friendly 10 MB-per-file limit. The user is
asked to split documents or use an approved batch ingestion path. The public UI
never attempts to hold 200 MB in a shared process.

### 32. What survives a crash mid-analysis?

Each completed pipeline result is atomically serialized as safe JSON in the
isolated session folder. Exports are built atomically or in memory. The UI
offers the prior snapshot when the session ID returns.

### 33. How do you support different CSV headers?

Deterministic fuzzy suggestions map client headers to the canonical schema. The
user confirms dropdowns, gets per-field validation, and can save a named JSON
profile for the session.

### 34. How is the public app safe for multiple users?

No session writes repository files. Each session has an unguessable folder;
uploads are sanitized and bounded; caches key immutable demo content; keys come
only from the environment.

### 35. How do you make status accessible?

Color never stands alone. Pass, review, fail, and information states use ●, ▲,
■, and ◆ labels. Charts use a colorblind-safe palette and status bars add
pattern/shape where possible.
