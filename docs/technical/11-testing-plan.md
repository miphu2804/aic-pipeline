# Technical 11 - Testing plan

## Test strategy

Testing follows the BRDS trace, not file names. Each module needs tests for validation, state transitions, error codes and at least one happy path. Runtime proof should use sample corpus/query workflows once implementation exists.

## Test layers

| Layer | Purpose | Examples |
|---|---|---|
| Unit | Domain validation, score/fusion deterministic logic, state guards. | locator validation, TRAKE order, VQA evidence guard |
| Adapter contract | Filesystem/text/vector/media adapters with fixtures. | FAISS dimension check, text search response mapping |
| Integration | Module workflow across repositories/adapters. | import corpus -> keyframe catalog -> index publish |
| E2E/CLI/API | User-visible workflows. | Textual KIS query returns ranked candidate and submission draft |
| Evaluation regression | Retrieval quality on fixed query set. | top-k metrics, failure categories |

## Core scenario matrix

| Scenario | Expected Result | Layer | Modules | Traceability |
|---|---|---|---|---|
| Import valid manifest | Corpus becomes `READY`; video count matches. | Integration | `dataset_catalog` | AC-01, FR-01 |
| Import manifest with duplicate video ID | Reject with `MANIFEST_INVALID`. | Unit/integration | `dataset_catalog` | AC-01, BR-02 |
| Build/import keyframe catalog | Keyframes have canonical locator and timestamp. | Integration | `keyframe_pipeline` | AC-02, BR-01 |
| Keyframe timestamp outside duration | Reject with `KEYFRAME_OUT_OF_RANGE`. | Unit | `keyframe_pipeline` | AC-02 |
| Build ASR text docs | Searchable transcript refs video/time range. | Adapter/integration | `asr_pipeline`, text adapter | AC-03 |
| Build OCR text docs | OCR block includes bbox/confidence/keyframe ref. | Adapter/integration | `ocr_pipeline`, text adapter | AC-04 |
| Build semantic vector index | Vector count and dimension match manifest. | Adapter/integration | `feature_pipeline` | AC-05 |
| Vector dimension mismatch | Artifact not active; `VECTOR_DIMENSION_MISMATCH`. | Unit/adapter | `feature_pipeline` | AC-05, BR-11 |
| Extract visual attributes | Color/object evidence can influence rerank. | Unit/integration | `feature_pipeline`, `retrieval_fusion` | AC-06 |
| Submit valid Textual KIS query | Query session stores task type and selected branches. | Integration/API | `query_planner` | AC-07 |
| Submit invalid task contract | Reject with `TASK_CONTRACT_INVALID`. | Unit/API | `query_planner` | AC-07, BR-07 |
| Fan-out with all branches active | Raw hits include branch latency and evidence. | Integration | `retrieval_fusion` | AC-08 |
| Fan-out with one branch unavailable | Result is degraded warning or fail according to policy. | Integration | `retrieval_fusion`, `index_registry` | AC-08, NFR-09 |
| Fusion deterministic | Same inputs/config produce same ranking. | Unit | `retrieval_fusion` | AC-09, BR-05 |
| Candidate missing evidence | Candidate dropped or error `EVIDENCE_MISSING`. | Unit | `retrieval_fusion` | AC-09, BR-04 |
| Create KIS submission | Output contains `VideoId`, `FrameId`. | API/e2e | `task_solvers` | AC-10 |
| TRAKE valid ordered events | Returns sequence in increasing temporal order. | Unit/integration | `task_solvers`, `retrieval_fusion` | AC-11, BR-08 |
| TRAKE no valid order | Returns `TRAKE_ORDER_NOT_FOUND`. | Unit | `task_solvers` | AC-11 |
| VQA with sufficient evidence | Returns answer text with evidence refs. | Integration | `task_solvers` | AC-12 |
| VQA without evidence | Returns `INSUFFICIENT_EVIDENCE`. | Unit | `task_solvers` | AC-12, BR-09 |
| Record feedback | Feedback stored separately from index artifact. | Integration | `evaluation_ops` | AC-13, BR-10 |
| Run evaluation report | Report includes top-k metrics and config/artifact versions. | Integration | `evaluation_ops`, `retrieval_fusion` | AC-13 |
| Health/lineage report | Active artifacts and versions are listed. | API/integration | `index_registry`, `evaluation_ops` | AC-14 |
| Artifact manifest invalid | Artifact not activated. | Unit/integration | `index_registry` | AC-14, BR-11 |
| Candidate review supports fast evidence inspection | Ranked results expose preview/evidence fields needed for quick selection. | E2E/API | `api_ui_adapter`, `retrieval_fusion` | NFR-08, AC-10 |
| Visual KIS media unsupported | Reject with task/media error. | API/unit | `query_planner`, `task_solvers` | AC-15 |

## Unit coverage targets

| Module | Minimum unit targets |
|---|---|
| `dataset_catalog` | manifest schema, duplicate ID, locator validation |
| `keyframe_pipeline` | timestamp bounds, keyframe map validation |
| `asr_pipeline` | segment validation, text doc mapping |
| `ocr_pipeline` | OCR block mapping, bbox validation |
| `feature_pipeline` | vector dimension, artifact model version |
| `index_registry` | publish/deprecate transitions, manifest compatibility |
| `query_planner` | task contract matrix, branch plan selection |
| `retrieval_fusion` | score normalization, dedup, deterministic ranking |
| `task_solvers` | KIS output, TRAKE ordering, VQA evidence guard |
| `evaluation_ops` | feedback target validation, metric calculation |

## Integration coverage targets

- Corpus import to keyframe catalog.
- Keyframe catalog to OCR/vector branch artifact.
- Active artifact registry to query planning.
- Query fan-out to fusion result with evidence.
- Task solver output to feedback/evaluation record.

## E2E/CLI/API coverage targets

- `Textual KIS`: query -> candidates -> KIS submission draft.
- `TRAKE`: multi-event query -> ordered sequence or clear reason.
- `VQA`: question -> evidence -> answer or `UNANSWERED`.
- `Health`: active artifact lineage after index run.

## Deterministic test controls

- Use fixed fixture corpus and model/vector fixtures for unit/integration tests.
- Pin fusion weights and artifact version in test data.
- Avoid live model calls in deterministic unit tests.
- Store expected first failure code for invalid cases.

## Local validation gates

Current verified commands from backend README:

```sh
cd backend
uv run black --check src tests
uv run isort --check-only src tests
uv run pytest
```

Once pipeline modules exist, add a sample workflow gate:

```sh
uv run aic-pipeline corpus import --manifest ../data/sample/manifest.json
uv run aic-pipeline index run --corpus sample --branches keyframes,semantic,ocr
uv run aic-pipeline query textual-kis "sample query" --top-k 5
```

## Defect severity model

| Severity | Definition | Examples |
|---|---|---|
| S1 | Blocks correct submission or corrupts artifact/data. | Wrong locator, active artifact overwritten incorrectly. |
| S2 | Major retrieval/task behavior wrong but recoverable. | TRAKE order ignored, VQA answer without evidence. |
| S3 | Degraded quality or missing evidence in edge case. | One branch warning not surfaced. |
| S4 | Cosmetic or developer-experience issue. | Non-critical wording/log formatting. |

## Reporting template

Each test/evaluation report should include:

- corpus version
- artifact versions
- query set version
- fusion config version
- top-k metrics
- latency summary
- failure category counts
- representative false positive/false negative examples

## BRDS traceability

Every AC-01 through AC-15 appears in the core scenario matrix. Rules BR-01 through BR-14 are covered through validation, state, error and workflow tests.
