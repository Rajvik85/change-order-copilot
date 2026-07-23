# Code Walkthrough

## Start here

`run.py` is the non-UI orchestrator. It loads the bundled project, runs the
deterministic pipeline, evaluates against the gold standard, and optionally
launches Streamlit. `app/Home.py` is the product entry point.

## `document_loader.py`

`load_document_bytes` keeps uploads in memory until they pass extension and
content checks. Text decoding tries UTF-8 with BOM, UTF-8, then Windows-1252.
Word documents are read from `BytesIO`. `segment_sections` recognizes Markdown
and plain uppercase headings. Unknown layouts become a `full_text` section and
carry a warning so downstream regexes can still attempt extraction.

To add PDF/OCR, implement a new byte reader here and preserve normalized
character/page coordinates in `TextSpan`.

## `parsing.py`

`parse_date` centralizes ISO, day-first, month-first, long English dates, and
Excel serials. A document-level clue—such as `08/18/2026`—sets the slash-date
order for related header dates. `parse_currency_amount` removes symbols and
separators, then applies decimal K/M/B multipliers.

To support another locale, add explicit formats and an ambiguity policy; do not
let pandas silently guess contractual dates.

## `extractor.py`

The money regex finds `USD 1.2M`, signed credits, and comma-separated amounts
inside the Cost Impact section first. The schedule regex is similarly scoped to
avoid picking up notice-day rules. Clause extraction is confined to the
Contractual Basis section where available.

Classification scores two keyword groups plus a stronger clause hint. This is
transparent and deterministic. spaCy loads the configured small model where
available; otherwise `spacy.blank("en")` plus `PhraseMatcher` preserves the
offline event-signal path. Labeled commercial fields remain regex-grounded.

To add a change class, update `_TYPE_PATTERNS`, `_TYPE_CLAUSE_HINTS`,
`CLAUSE_SUPPORT`, the canonical schema, and gold labels.

## `evaluation.py`

Scalar fields use exact normalized match. Clause references become normalized
sets, allowing `Clause 13.2` and `Sub-Clause 13.2` to compare identically.
Micro-F1 is calculated from true positive, false positive, and false negative
counts; missing gold values do not create artificial support. `to_markdown`
produces the methodology table.

## `compliance.py`

`assess_compliance` is intentionally procedural. It subtracts `date` objects,
compares integer calendar days, and records every input in `calculation`.
Clause-to-type support is a visible mapping. Approval uses absolute value so a
large credit still reaches the correct authority.

To change notice rules, edit project metadata—not code.

## `analytics.py`

`build_register` creates one pandas row per CO. Signed value preserves descope
credits. Gross positive exposure is kept separately. Findings are plain
`Finding` dataclasses with severity, message, rationale, and affected COs.

To add a finding, implement one documented predicate in `generate_findings` and
test both trigger and non-trigger behavior.

## `mapping.py` and `security.py`

Fuzzy header suggestions use `difflib`, then the user confirms every mapping.
Profiles are JSON in the owning session directory. Filenames are reduced to a
safe basename; size, extension, count, and MIME hints are checked before parse.

## `pipeline.py` and `storage.py`

The pipeline checks cancellation and elapsed time between documents. Completed
records survive a limit as a provisional `PipelineResult`. Hashes are based on
actual input bytes and canonical configuration JSON.

Storage never uses pickle. `atomic_write` writes, flushes, calls `fsync`, then
replaces the destination. The escape-hatch ZIP is created in memory.

## `prompts.py` and `llm_layer.py`

Each `PromptTemplate` states role, task, output schema, and design reasoning.
`grounding_payload` excludes raw document text. Provider imports occur only
when the matching environment key exists. `generate_review` returns typed
`ok`, `not_configured`, or `error` results and retries only bounded transient
exceptions.

To add a provider, implement the small `ProviderAdapter` protocol; no UI change
should be required.

## `report_export.py`

The workbook contains register, portfolio summary, and compliance scorecard
sheets. The HTML pack has inline CSS and no remote dependencies. Both include
version, timestamp, configuration hash, and input hash.

## Streamlit app

`ui_components.py` owns session IDs, global status, accessibility labels,
footer, provisional banner, and the page-level ZIP. Each page reads the same
`st.session_state["pipeline_result"]`; no page writes repository data.

To change visual identity, edit `styles.py` and `.streamlit/config.toml`.
