# Temporal Semantics

How a question about an earlier contract state is turned into a date, and where
that date is applied. Implementation: `backend/app/retrieval/temporal.py`;
the result is carried on `QueryPlan.as_of` and consumed by graph traversal and
structured retrieval.

## 1. Policy

| Rule | Decision |
| --- | --- |
| Timezone | Calendar dates, no timezone conversion. Procurement documents record dates, not instants. |
| Reference date | `app.core.clock.today()`, which honours `EVAL_AS_OF_DATE` so evaluation is reproducible. |
| Point in time | “as of 31 March 2025” → that exact date. |
| Period | “during 2024”, “in June 2025” → the **end** of the period. What was in force during a window is the state at its close. |
| Month precision | Resolved to the last day of that month, with a note. |
| Year precision | Resolved to 31 December of that year, intent `RANGE`. |
| Relative | `last year` → 31 Dec of the previous year; `last quarter` → the previous quarter's end; `last month` → the last day of the previous month; `current`/`latest` → the reference date. |
| Ambiguous input | `03/04/2025` is left unresolved (`ambiguous: true`). No as-of filter is applied and the ambiguity is reported. |
| No anchor | A temporal question with no resolvable date applies no filter and records that fact. Nothing is invented. |
| “Original” | A version question, not a date: intent `ORIGINAL`, no as-of date, earliest recorded version preferred. |
| “After the second amendment” | Intent `CHANGE`; the amendment dates come from the stored contract rows. |

## 2. Which date is which

| Stored field | Used for | Never used as |
| --- | --- | --- |
| `effective_date` | start of a validity window | publication date |
| `expiry_date` | end of a validity window | ingestion date |
| `contract.effective_date` on an amendment row | when the amendment took effect | when the file was uploaded |
| `Price.effective_date` / `expiry_date` | which price was in force | document creation date |
| `Document.created_at` / `updated_at` | ordering in the document list only | contract effective date |
| `IngestionJob.created_at` | queue diagnostics | any procurement fact |

The as-of filter is applied to validity windows only. Document creation and
ingestion timestamps are never substituted for a contractual date.

## 3. Where the date is applied

- **Graph** — `graph_lookup` passes `as_of` to `GraphProvider.traverse`; the local
  and Neo4j providers drop edges whose `effective_date` is later or whose
  `expiry_date` is earlier (`providers/graph/temporal.py`). Filtering happens
  before the frontier expands, so a superseded version cannot seed further hops.
- **Structured SQL** — price facts are filtered with the same
  `fact_valid_in_period` rule used for explicit ranges, so a point-in-time
  question and a period question cannot disagree. Contract and compliance
  `is_expired` are computed against the plan's as-of date rather than today.
- **Vector** — chunk ordering already penalises expired chunks and prefers
  newer effective dates for temporal questions; it reads the same plan.

## 4. Worked examples

| Question | Derived | Behaviour |
| --- | --- | --- |
| What was the contract status as of 31 March 2025? | 2025-03-31 | Rows and edges effective on that day; later amendments excluded. |
| Which amendment was effective in June 2025? | 2025-06-30 | Month resolved to its end; amendments effective after June excluded. |
| What were the original payment terms? | none (`ORIGINAL`) | Earliest version preferred; no date filter. |
| What terms changed after the second amendment? | none (`CHANGE`) | Amendment dates read from the contract rows. |
| Which supplier agreement was active during 2024? | 2024-12-31 | Agreements in force on 31 Dec 2024; 2025 renewals excluded. |
| What changed last year? | 31 Dec of the previous year | Relative to the reference date. |
| Is the contract current? | reference date | “Current” is an explicit as-of, not a missing value. |
| as of 03/04/2025 | none, `ambiguous` | Ambiguity reported; no filter applied. |

## 5. Known limitations

1. **No natural-language time expressions beyond the listed patterns.** “Since the
   framework was renewed” is not resolved; it degrades to no filter with a note.
2. **Amendment ordering is by recorded date**, not by an explicit sequence
   number, so two amendments with the same effective date are ordered by version.
3. **Clause-level temporal validity** inherits the document's effective/expiry
   dates; clauses are not individually dated unless the source states a date.
4. **Vector retrieval is not hard-filtered by as-of.** Chunks carry document-level
   dates and are reordered, not excluded; only graph and structured retrieval
   apply a strict validity filter.
5. **Timezone is UTC by policy.** A deployment that records local-midnight
   effective dates should state that in its source documents.
6. **Ambiguity is reported, not resolved.** A UI that wants to ask the user for
   clarification would read `TemporalResolution.ambiguous` and
   `TemporalResolution.notes`; the current answer path proceeds without a filter.

## 6. Tests

- `tests/unit/test_temporal_as_of.py` — parsing, relative dates, ambiguity,
  version questions, defaults.
- `tests/unit/test_temporal_plan_wiring.py` — the interpretation reaches
  `QueryPlan.as_of` for the brief's example questions.
- `tests/unit/test_graph_temporal.py` — edge validity boundaries.
