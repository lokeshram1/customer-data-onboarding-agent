# Customer Data Onboarding Agent

A functional AI-powered onboarding system for turning an uploaded customer CSV into a clean, reviewed, validated dataset. It profiles the source data, proposes field mappings, checks them independently, routes uncertain choices through human review, transforms only approved fields, and exports the result with a mapping report.

## Architecture

- **Next.js + TypeScript** provides the data workflow, profiling tables, mapping review controls, validation summary, and exports.
- **FastAPI + Pydantic** owns file parsing, profiling, mapping, deterministic validation, transformation, and reporting. Run state stays in memory; data is processed locally.
- **Mock mapping provider** is the default and works without a key. It makes proposals from column labels and observed profile evidence; it does not encode sample-specific row mappings.
- **OpenAI provider** can be configured with `OPENAI_API_KEY`. The backend owns the secret and sends only column labels, profile summaries, and up to five limited/masked examples per field.

The stages deliberately separate LLM reasoning, deterministic validation, human decisions, and transformation. The LLM suggests; deterministic checks measure observable data quality; the user decides; only approved decisions affect output.

## Run locally

1. Install backend dependencies and the API-test client: `python -m pip install -r backend/requirements-dev.txt`
2. Start the API: `uvicorn backend.main:app --reload --port 8000`
3. Install frontend packages: `pnpm install`
4. Start the UI: `pnpm dev`
5. Open `http://localhost:3000` and upload `data/sample_customer_data.csv`.

The API is available at `http://localhost:8000`; health check is `/api/health`.

## Environment

- `OPENAI_API_KEY` (optional): enables the hosted OpenAI mapping provider.
- `OPENAI_MODEL` (optional; default `gpt-4o-mini`): provider model.
- `NEXT_PUBLIC_API_URL` (optional; default `http://localhost:8000`): API base URL.

The API key is read only by the backend. Never define it with a `NEXT_PUBLIC_` prefix.

## Example workflow

Upload CSV → inspect preview and profiling → generate proposals → edit targets and approve/reject/ignore each mapping → apply approved mappings → inspect final validation → download clean CSV and mapping report.

## Tests

Run `python -m unittest discover -s backend -p 'test_*.py'`. Frontend checks: `pnpm typecheck` and `pnpm build`.

## Confidence calculation

The displayed score starts with the provider's bounded proposal confidence. A small evidence adjustment (+0.04) applies when observed values agree with an email/phone/date/identifier mapping. Each deterministic issue subtracts 0.14; the score is clamped to 0–0.99. A score of 90% or more is high confidence, but data warnings still require review. Everything else requires review. A human approval is always explicitly recorded and gates transformation.

## Privacy and data handling

CSV input is capped at 10 MB and 100,000 records, decoded as UTF-8, and held in process memory for the run. It is not written to disk or logged. For hosted LLM use, only the schema, source column names, aggregate profiling, and a few masked representative samples are sent. No authentication or persistence layer is included; restart clears run data.

## Design decisions and limitations

The MVP favors a single local API and in-memory run state over external infrastructure. Profiling and quality checks use deterministic Python logic; the sample includes malformed email/date values, a repeated ID, missing phone, and formatting variation. Date parsing and phone cleanup are intentionally conservative. The standard-library CSV parser is used to keep the local setup small. OpenAI mode requires connectivity and valid credentials. Suggested future work includes durable run storage, richer locale-aware parsing, configurable schemas in the UI, and more comprehensive production security controls.
