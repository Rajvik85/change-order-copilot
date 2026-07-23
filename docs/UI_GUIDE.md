# UI Guide

## The review journey

1. **Home:** load the complete synthetic project and see immediate exposure.
2. **Document Intake:** upload, paste, map a register, or reload the demo.
3. **Portfolio Dashboard:** prioritize value, procedural risk, and concentration.
4. **CO Analysis:** compare original text, extracted facts, and compliance.
5. **Compliance Checker:** scan the full matrix, urgency radar, and clause text.
6. **AI Review Memo:** inspect the no-key design or generate a grounded draft.
7. **Reports & Export:** configure, preview, and download the review pack.

## Home

The landing message uses domain language rather than NLP terminology. Loading
the demo runs 18 records offline and preserves the result for all pages.
Sidebar indicators show document count and optional-AI readiness.

## Document Intake

Upload validates size, filename, extension, content hint, parse result, and
sections. A failure row contains a remedy. Uploaded material is stored only in
the isolated session folder.

Paste gives a fast single-document loop. Demo reloads the fixed corpus. The CSV
flow fuzzily suggests canonical fields, but dropdown confirmation remains
mandatory. Mapping profiles are JSON scoped to the session.

## Portfolio Dashboard

Five KPIs answer exposure and procedural questions first. Charts use the
Okabe–Ito colorblind-safe palette, and bar status also uses pattern/shape.
Findings use icon plus color:

- ■ critical/fail
- ▲ review/high
- ◆ medium/info
- ● pass

This avoids color-only meaning.

## CO Analysis and source-span traceability

The register is filterable and sortable. Selecting a CO drives three panels.
The “Trace a fact” selector highlights the exact supporting sentence in the
normalized document. Confidence describes extraction, not entitlement.

Commercial reviewers require this because an attractive register can otherwise
hide an incorrect source value. Traceability turns the UI into a review surface
rather than a black box.

## Compliance Checker

The matrix supports portfolio scanning. The radar sorts negative remaining days
first; missing evidence remains separate from lateness. Clause expanders show
the invented text and the checks it powers.

## AI Review Memo

Without a key, the page is intentionally complete: it explains the boundary and
shows a static development memo. With a key, the user selects a draft type,
reviews the exact grounding payload, and generates a labeled draft. The code
block provides Streamlit's copy control; “Add to report” is session-only.

## Reports

Users choose sections, as-of date, and narrative, then preview the exact
self-contained HTML. Excel, HTML, JSON, CSV, and the global artifact ZIP carry
traceability stamps.

## State and recovery

`st.session_state` holds the typed pipeline result and selected memos. The demo
cache key includes input and configuration hashes. A safe JSON snapshot is
written atomically to the session folder; a returning session with its `sid`
can download the last snapshot and reconstruct by reloading source inputs.

Every page shows a friendly empty state and an “Export everything computed so
far” escape hatch when results exist. Exceptions are translated into cards at
the intake boundary; raw tracebacks are not part of the designed experience.

## Laptop layout

Content is capped near 1180px, charts use responsive container width, and
columns collapse on narrow screens. The primary acceptance viewport is
1440×900, representative of a 13-inch laptop; no horizontal page scrolling is
required.
