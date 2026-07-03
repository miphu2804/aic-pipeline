# Technical 06 - Main workflows

## W1 - Import corpus manifest

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `api_ui_adapter` | Parse request | none | none | correlation id | `QUERY_PARAM_INVALID` | FR-01 |
| 2 | `dataset_catalog` | Validate manifest schema and paths | none | `CorpusAsset DRAFT` | invalid row report | `MANIFEST_INVALID` | BR-02 |
| 3 | `dataset_catalog` | Persist corpus/videos/metadata | single transaction | `DRAFT -> READY` | corpus version | rollback on write failure | AC-01 |
| 4 | `evaluation_ops` | Audit import | append log | none | import counts | log warning only | NFR-05 |

## W2 - Build index artifacts

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `index_registry` | Create index run | write run row | `QUEUED` | run id | `PIPELINE_CONFIG_INVALID` | FR-02..FR-06 |
| 2 | `keyframe_pipeline` | Build/import keyframes | branch transaction | `RUNNING` | coverage stats | `KEYFRAME_MAP_REQUIRED` | FR-02 |
| 3 | `asr_pipeline` | Build ASR docs/index | temp artifact | `BUILDING` | segment stats | `ASR_INPUT_UNREADABLE` | FR-03 |
| 4 | `ocr_pipeline` | Build OCR docs/index | temp artifact | `BUILDING` | OCR stats | `OCR_OUTPUT_UNMAPPED` | FR-04 |
| 5 | `feature_pipeline` | Build vectors/attributes | temp artifact | `BUILDING` | vector stats | `VECTOR_DIMENSION_MISMATCH` | FR-05, FR-06 |
| 6 | `index_registry` | Validate manifests and publish | active pointer transaction | `ACTIVE`, run `SUCCEEDED` | lineage report | `INDEX_VERSION_MISMATCH` | FR-14 |

## W3 - Textual KIS query

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `query_planner` | Validate task/query | query transaction | `DRAFT -> RUNNING` | selected branches | `TASK_CONTRACT_INVALID` | FR-07 |
| 2 | `retrieval_fusion` | Search semantic vector | none/read-only | `RUNNING` | branch latency | branch warning | FR-08 |
| 3 | `retrieval_fusion` | Search OCR/ASR text | none/read-only | `RUNNING` | branch latency | branch warning | FR-08 |
| 4 | `retrieval_fusion` | Combine/dedup/rerank | fusion transaction | `COMBINING -> READY` | score breakdown | `EVIDENCE_MISSING` | FR-09 |
| 5 | `task_solvers` | Create KIS submission draft | output transaction | `DRAFT -> READY` | selected rank | `CANONICAL_LOCATOR_MISSING` | FR-10 |

## W4 - TRAKE

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `query_planner` | Validate `TRAKE` query | query transaction | `DRAFT -> RUNNING` | task type | `TASK_CONTRACT_INVALID` | FR-07 |
| 2 | `task_solvers` | Decompose query into `TemporalEvent` | output temp | `RUNNING` | sub-event count | `TRAKE_DECOMPOSITION_FAILED` | FR-11 |
| 3 | `retrieval_fusion` | Retrieve each event | read-only plus hits | `RUNNING -> COMBINING` | hit count/event | branch warning | FR-08 |
| 4 | `task_solvers` | Assemble ordered sequence | output transaction | `READY` | selected sequence score | `TRAKE_ORDER_NOT_FOUND` | BR-08 |
| 5 | `api_ui_adapter` | Return sequence | none | none | response correlation id | none | AC-11 |

## W5 - VQA

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `query_planner` | Validate `VQA` question | query transaction | `DRAFT -> RUNNING` | question type | `TASK_CONTRACT_INVALID` | FR-07 |
| 2 | `retrieval_fusion` | Retrieve candidate evidence | read-only plus hits | `COMBINING` | evidence coverage | branch warning | FR-08, FR-09 |
| 3 | `task_solvers` | Extract supporting evidence | output temp | `DRAFT` | evidence refs | `INSUFFICIENT_EVIDENCE` | BR-09 |
| 4 | `task_solvers` | Generate concise answer | output transaction | `ANSWERED` | confidence | `VQA_UNSUPPORTED_QUESTION` | FR-12 |
| 5 | `api_ui_adapter` | Return answer with evidence | none | none | response correlation id | none | AC-12 |

## W6 - Feedback and evaluation

| Step | Module | Command/Query | Transaction | State | Logs/Side effects | Failure branch | Trace |
|---|---|---|---|---|---|---|---|
| 1 | `evaluation_ops` | Record feedback | feedback transaction | `NEW` | label target | `FEEDBACK_TARGET_INVALID` | FR-13 |
| 2 | `evaluation_ops` | Run query set | evaluation transaction | none | config/artifact versions | `EVALUATION_QUERYSET_INVALID` | FR-13 |
| 3 | `retrieval_fusion` | Reuse retrieval/fusion for each query | per-query transaction | query states | metrics | per-query failure logged | AC-13 |
| 4 | `evaluation_ops` | Produce report | report write | `APPLIED_TO_RUN` | top-k/failure categories | report warning | NFR-10 |

## Workflow traceability

Workflows W1 to W6 cover all MVP acceptance criteria AC-01 through AC-14. Visual KIS future workflow uses W3 with visual media validation and vector-first retrieval, traced by FR-15 and AC-15.

