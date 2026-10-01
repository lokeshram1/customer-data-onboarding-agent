# Architecture

```text
Browser (Next.js)
  ├─ Upload + preview
  ├─ Profile and mapping review
  └─ Validation and exports
       │ JSON / multipart HTTP
       ▼
FastAPI process
  ├─ CSV validation and profiling
  ├─ Mapping provider (Mock or OpenAI)
  ├─ Deterministic validators
  ├─ Human decision gate
  ├─ Approved-field transformation
  └─ Final validation and exports
       │
       └─ In-memory run state (cleared on restart)
```

## Decision boundary

The mapping provider proposes a target and reason from a compact profile payload. It does not receive the full dataset. A typed mapping object constrains the shape of the proposal. Independent deterministic checks then inspect actual source values for requiredness, duplicates, parseability, and type compatibility. Confidence combines provider confidence with profiling evidence and validation penalties; the score never replaces user review. A mapping with status `approved` is required before its source values can enter the transformed output.

## Data flow and privacy

Uploads are restricted to UTF-8 CSV, 10 MB, and 100,000 rows. Data remains in process memory; logs contain no row values. OpenAI credentials remain in the backend environment. Hosted requests contain schema, headers, aggregate profile facts, and a small masked sample. CSV and JSON exports are generated from the reviewed run state.

## Failure handling

Malformed uploads and missing run state return HTTP errors. Mapping target names are checked against the schema during review. Final validation reports row-level required-field/email/date issues and aggregate duplicate IDs. Ignored, rejected, and unreviewed mappings do not transform.
