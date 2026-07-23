# NLP and LLM Methodology

## Evaluation protocol

All 18 documents are synthetic. They were written and hand-labeled before
extractor implementation. The split is fixed in both `project_meta.yaml` and
`gold_standard.json`:

- development: CO-001 through CO-012;
- held-out: CO-013 through CO-018.

Dates and numbers require exact equality after canonical parsing. Status and
type require normalized exact match. Clause references compare normalized sets.
The test suite enforces micro-F1 ≥ 0.90.

### Extraction evaluation — all documents

| Field | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| type | 1.000 | 1.000 | 1.000 | 18 |
| cost_value | 1.000 | 1.000 | 1.000 | 18 |
| schedule_days | 1.000 | 1.000 | 1.000 | 18 |
| cited_clause_refs | 1.000 | 1.000 | 1.000 | 19 |
| notice_date | 1.000 | 1.000 | 1.000 | 16 |
| event_date | 1.000 | 1.000 | 1.000 | 18 |
| status | 1.000 | 1.000 | 1.000 | 18 |
| **overall** | **1.000** | **1.000** | **1.000** | **125** |

### Extraction evaluation — held-out documents

| Field | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| type | 1.000 | 1.000 | 1.000 | 6 |
| cost_value | 1.000 | 1.000 | 1.000 | 6 |
| schedule_days | 1.000 | 1.000 | 1.000 | 6 |
| cited_clause_refs | 1.000 | 1.000 | 1.000 | 7 |
| notice_date | 1.000 | 1.000 | 1.000 | 5 |
| event_date | 1.000 | 1.000 | 1.000 | 6 |
| status | 1.000 | 1.000 | 1.000 | 6 |
| **overall** | **1.000** | **1.000** | **1.000** | **42** |

Perfect performance is plausible only because the benchmark is small,
synthetic, and structurally constrained. It is a regression guarantee for this
portfolio fixture—not a claim of production generalization.

## Extraction design

Regex handles fields whose surface form is governed by commercial notation:
CO numbers, labeled dates, signed currency, day counts, and clauses. Sections
reduce false positives—for example, the 14-day notice rule should not become a
schedule impact.

spaCy contributes tokenization, optional NER, sentence boundaries, and
PhraseMatcher event signals. If `en_core_web_sm` is unavailable, the matcher
continues with a blank English pipeline. Critical numeric fields do not depend
on statistical model downloads.

Classification uses transparent keyword-group scores plus a clause hint. The
confidence is a heuristic extraction confidence, not calibrated probability or
commercial merit.

## Traceability

Every numeric output stores normalized-text start/end offsets and its supporting
sentence. The UI selects a fact and highlights that exact range. This prevents a
reviewer from treating a dashboard value as unsupported truth and exposes
wrong-section extraction immediately.

## Error analysis

The current fixture is solved, but these realistic variations remain failure
risks:

- scanned/image-only PDFs: there is no text until OCR;
- multiple events in one letter: a single event/notice pair is insufficient;
- currencies without symbols or with locale decimals: the money parser may
  reject or mis-scale them;
- table-only Word content: paragraph extraction does not yet traverse every
  nested table;
- ambiguous dates without a document-level clue: `05/08/2026` needs human
  confirmation;
- a narrative citing many irrelevant clauses: set match may over-extract;
- indirect classification language with no mapped clause: keyword confidence
  falls;
- amendments that alter the 14/28-day rules: project metadata must reflect the
  governing version;
- source sentence offsets after OCR normalization: page-aware provenance is
  needed.

Production evaluation should sample real authorized documents, define an
annotation guide, measure inter-annotator agreement, and report performance by
format, contractor, and document quality.

## Prompt design

Every prompt applies four controls:

1. **grounding:** canonical facts, fixed checks, and only relevant clauses;
2. **role boundary:** assistive internal writer, not entitlement decision-maker;
3. **output schema:** stable sections or table columns;
4. **refusal on missing facts:** “Not evidenced in the supplied facts.”

### Before

> Review this change order and tell me whether the contractor is entitled.

This invites invented law, missing context, and an opaque conclusion.

### After

> Using only STRUCTURED FACTS, DETERMINISTIC CHECKS, and RELEVANT CLAUSES,
> explain the fixed compliance result. Do not invent or alter a clause, date,
> value, attachment, or verdict. Use headings: Facts; Deterministic compliance
> position; Commercial exposure; Evidentiary gaps; Recommended action.

The application additionally discloses the exact payload in a grounding
expander.

## Hallucination controls

- Raw documents and the entire clause library are not sent.
- Clause IDs originate from extraction and a loaded library.
- The deterministic verdict is explicitly fixed.
- Missing data has prescribed wording.
- Outputs are typed and labeled as AI-assisted drafts.
- Bounded retries do not change prompt content or silently switch providers.
- Live calls require environment keys; CI uses injected mock adapters.
- Human review remains required in UI and HTML exports.

No prompt can guarantee truth. These controls reduce and expose failure; they
do not eliminate it.

## LLM spot-check protocol

For each supported capability, a reviewer should sample at least:

- one compliant, one at-risk, and one time-barred CO;
- one positive variation, one credit, and one disputed backcharge;
- one missing basis and one multi-clause EOT/prolongation case.

Score: factual consistency, clause-citation validity, verdict preservation,
missing-fact behavior, action usefulness, tone, and harmful overstatement.
Record provider/model/version and retain the grounding payload. A failed
verdict-preservation or invented citation is a release blocker.

## When rules beat models—and when they stop

Rules win when syntax is stable, the decision is arithmetic, errors must be
explained, and data is too small for honest learning. That describes this
prototype.

At hundreds of heterogeneous documents, rules may need layout-aware parsing,
OCR confidence, richer NER, and learned document classification. At thousands
of authorized labeled examples, a supervised model may improve recall for
implicit events and varied headings. Even then, dates and money should retain
deterministic validation, source spans, and a rule-based compliance layer.

Method selection is not “AI versus no AI.” It is choosing the least complex
method that meets accuracy, auditability, data, latency, and governance needs.
