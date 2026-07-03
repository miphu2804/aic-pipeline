# Technical 10 - Local development setup

## Objective

Keep local development simple while preserving contracts needed for future implementation. Current verified repo is a minimal Python backend, so setup below separates verified commands from inferred target commands.

## Verified prerequisites

| Item | Source | Status |
|---|---|---|
| Python | `backend/pyproject.toml`, `backend/.python-version` | Python 3.11.3 target verified. |
| Package manager | `backend/README.md` | `uv` verified. |
| Formatting | `.pre-commit-config.yaml` | black and isort configured for `backend/`. |
| Tests | `backend/README.md` | `uv run pytest` documented, but no tracked test `.py` file was found during baseline. |

## Verified commands

```sh
cd backend
uv sync
uv run aic-pipeline
uv run black --check src tests
uv run isort --check-only src tests
uv run pytest
```

Pre-commit install:

```sh
cd backend
uv run pre-commit install --config ../.pre-commit-config.yaml
```

## Target environment variables

These are inferred targets for implementation:

| Variable | Purpose | Default for local |
|---|---|---|
| `AIC_PIPELINE_ENV` | Runtime profile. | `local` |
| `AIC_PIPELINE_DB_URL` | Metadata store. | `sqlite:///./data/aic_pipeline.db` |
| `AIC_PIPELINE_ARTIFACT_DIR` | Artifact root. | `./artifacts` |
| `AIC_PIPELINE_MEDIA_ROOT` | Base path for raw media. | unset, required for real corpus |
| `AIC_PIPELINE_TEXT_INDEX_URL` | Text index service URL if using Meilisearch. | `http://localhost:7700` |
| `AIC_PIPELINE_LOG_LEVEL` | Structured logging level. | `INFO` |

## Target local runbook

Inferred CLI shape:

```sh
cd backend
uv run aic-pipeline corpus import --manifest ../data/sample/manifest.json
uv run aic-pipeline index run --corpus sample --branches keyframes,semantic,ocr,asr
uv run aic-pipeline query textual-kis "người đàn ông mặc áo vàng viền đen đang trả lời phỏng vấn" --top-k 20
uv run aic-pipeline eval run --query-set ../data/sample/query_set.json
```

## Seed data strategy

- Use a tiny local corpus with 2 to 5 short videos or synthetic frame fixtures.
- Include fixture manifest, keyframe images, OCR text, ASR transcript and precomputed vector fixture where possible.
- Seed data must avoid hard-coded private absolute paths in committed files.

## Local validation guardrails

- No command should publish active artifact without manifest validation.
- No query should run without at least one active branch artifact.
- Local debug mode may expose raw paths only when explicitly enabled.
- Every fixture query should have expected top-k or expected error code.

## Observability basics

- Log JSON lines or structured fields for module, operation, correlation id, artifact id and error code.
- Persist index run stats and query branch latencies.
- Health command should report active artifact versions and branch availability.

## Developer workflow

1. Create or update BRDS/technical trace first for behavior changes.
2. Add focused tests for new module contract.
3. Implement module with owned data and interfaces.
4. Run formatting and tests from `backend/README.md`.
5. Run a sample workflow or fixture query, not only import/build checks.

## Known risks and mitigations

| Risk | Mitigation | Trace |
|---|---|---|
| No runtime dependencies yet | Add dependencies only when implementing the module needing them. | NFR-06 |
| No tracked tests currently | Start with domain/unit tests for validation/state/error contracts. | NFR-10 |
| Local media paths can leak | Keep path export behind debug flag and safe response DTOs. | BR-13 |
| Text/vector services may be absent | Keep adapters swappable and support fixture/local fallback for tests. | NFR-09 |

## Non-goals

- This file does not mandate Docker or cloud deployment for MVP.
- This file does not choose final official contest submission integration.
- This file does not require installing FAISS/Meilisearch before the corresponding module is implemented.

## BRDS traceability

Local setup supports FR-14, NFR-01, NFR-05, NFR-06, NFR-09 and NFR-10.

