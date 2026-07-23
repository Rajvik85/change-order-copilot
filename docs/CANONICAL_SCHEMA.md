# Canonical Change-Order Schema

This document is the single source of truth for mapped registers, extraction
output, UI facts, and exports.

| Field | Type | Required | Normalization | Meaning |
|---|---|---:|---|---|
| `co_number` | string | yes | uppercase `CO-NNN` where present | Change reference |
| `event_date` | ISO date / null | yes for compliance | `YYYY-MM-DD` | Awareness/event date used by rules |
| `notice_date` | ISO date / null | no | `YYYY-MM-DD` | Proven initial notice service date |
| `particulars_date` | ISO date / null | no | `YYYY-MM-DD` | Detailed submission date |
| `contractor` | string / null | yes | trimmed text | Commercial counterparty |
| `originator` | string / null | no | trimmed text | Person/role raising the record |
| `type` | controlled string | yes | one of eight classes | Commercial change category |
| `cost_value` | float / null | yes | base currency units, signed | Positive exposure; credits negative |
| `schedule_days` | integer / null | yes | signed calendar days | Claimed delay positive; recovery/benefit negative |
| `status` | controlled string | yes | draft/submitted/approved/disputed | Workflow position |
| `cited_clause_refs` | list[string] | no | numeric dotted refs | Clauses cited in the CO basis |
| `event_phrases` | list[string] | no | lowercase spaCy matches | Auxiliary NLP signals |

Every `ExtractionResult` field also carries:

- `confidence`: `0.0–1.0`, describing extraction confidence, not entitlement;
- `source.start` and `source.end`: normalized-text character offsets; and
- `source.text`: the sentence shown by traceability views.

## Controlled change types

- `scope addition`
- `design change`
- `differing site conditions`
- `acceleration`
- `prolongation/EOT`
- `force majeure`
- `deletion/descope`
- `disputed backcharge`

## Accepted source formats

Documents: UTF-8/Windows-1252 `.md` or `.txt`, and valid `.docx`.

Mapped registers: `.csv` with fuzzy header suggestions and explicit user
confirmation. Dates accept ISO, `DD-MM-YYYY`, slash formats, English long dates,
and Excel serials. Ambiguous slash dates produce a warning. Currency accepts
commas, signs, and `K/M/B` suffixes.

## Null semantics

`null` means “not evidenced in supplied input.” It never means zero,
not-applicable, waived, or compliant. A missing notice date produces `AT RISK`,
not `COMPLIANT`.
