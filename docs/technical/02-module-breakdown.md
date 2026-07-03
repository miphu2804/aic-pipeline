# Technical 02 - Module breakdown

## Design principles

- Keep v1 local-first and module-first: one backend package can host all modules, but ownership boundaries must be explicit.
- Commands mutate state and return versioned result snapshots.
- Queries are side-effect free except audit/logging for user-facing search when configured.
- Modules write only owned data unless a documented transaction boundary allows orchestration.
- Text, vector and feedback evidence are never collapsed into a single opaque score.

## Module contract matrix

| Module | Owns | Interfaces | Depends On | Guardrails | Errors | Tests | Traces |
|---|---|---|---|---|---|---|---|
| `dataset_catalog` | `CorpusManifest`, `VideoAsset`, `SourceMetadata`, `FrameLocator` | CLI/API import, catalog queries | Filesystem | Canonical IDs, path validation, immutable corpus version | `MANIFEST_INVALID`, `CANONICAL_LOCATOR_MISSING` | Unit schema, integration import | FR-01, BR-02, AC-01 |
| `keyframe_pipeline` | `Keyframe`, keyframe map | Index job command | `dataset_catalog`, video reader adapter | No online full-frame scan; timestamp bounds | `KEYFRAME_MAP_REQUIRED`, `KEYFRAME_OUT_OF_RANGE` | Unit mapper, integration sample video | FR-02, BR-01, AC-02 |
| `asr_pipeline` | `TranscriptSegment`, ASR docs | Index branch command | `dataset_catalog`, ASR adapter, text index adapter | Segment maps to video/time, versioned model | `ASR_INPUT_UNREADABLE`, `INDEX_VERSION_MISMATCH` | Adapter contract, text search integration | FR-03, AC-03 |
| `ocr_pipeline` | `OCRBlock`, OCR docs | Index branch command | `keyframe_pipeline`, OCR adapter, text index adapter | OCR maps to keyframe locator, confidence retained | `OCR_OUTPUT_UNMAPPED`, `ARTIFACT_MANIFEST_INVALID` | OCR fixture, bbox schema | FR-04, AC-04 |
| `feature_pipeline` | `FeatureVector`, `VisualAttribute`, vector docs | Index branch command | `keyframe_pipeline`, embedding/color/object adapters | Vector dimension stable, model config versioned | `VECTOR_DIMENSION_MISMATCH`, `ATTRIBUTE_CONFIG_INVALID` | Vector dimension, attribute extraction | FR-05, FR-06, AC-05, AC-06 |
| `index_registry` | `IndexArtifact`, artifact manifests, active pointers | Publish, health, lineage queries | All index branches, storage adapters | Atomic publish, active artifact immutable | `ARTIFACT_NOT_ACTIVE`, `INDEX_VERSION_MISMATCH` | Publish/deprecate, rollback | FR-14, BR-11, BR-12, AC-14 |
| `query_planner` | `QuerySession`, `NormalizedQuery`, retrieval plan | Query submit endpoint/command | `index_registry` | Task contract first, branch eligibility | `TASK_CONTRACT_INVALID`, `QUERY_INVALID` | Task validation matrix | FR-07, AC-07 |
| `retrieval_fusion` | `CandidateHit`, `RankedCandidate`, `FusionRun` | Retrieval command, candidate query | text/vector adapters, `query_planner` | Preserve branch evidence, deterministic fusion | `INDEX_BRANCH_UNAVAILABLE`, `EVIDENCE_MISSING`, `FUSION_CONFIG_INVALID` | Branch fan-out, fusion determinism | FR-08, FR-09, AC-08, AC-09 |
| `task_solvers` | `TaskSubmission`, `TemporalEvent`, `TemporalSequence`, `VQAAnswer`, `VisualQuery` | KIS, TRAKE, VQA, Visual KIS commands | `retrieval_fusion`, evidence readers | Output matches task type, answer grounded | `TRAKE_ORDER_NOT_FOUND`, `INSUFFICIENT_EVIDENCE`, `SUBMISSION_FORMAT_INVALID` | Solver scenario tests | FR-10..FR-12, FR-15 |
| `evaluation_ops` | `FeedbackRecord`, `EvaluationRun`, metrics, health snapshots | Feedback/eval/health commands | `retrieval_fusion`, `index_registry` | Feedback does not mutate raw artifact | `FEEDBACK_TARGET_INVALID`, `EVALUATION_QUERYSET_INVALID` | Evaluation report, feedback immutability | FR-13, FR-14, AC-13 |
| `api_ui_adapter` | Request/response DTOs, session boundary | REST/CLI/UI contracts | All application services | No private raw path leak, stable error envelope | `AUTH_FORBIDDEN`, `DATA_PATH_NOT_EXPORTABLE` | API contract/e2e | FR-07..FR-15, BR-13 |

## Module details

### `dataset_catalog`

- Responsibilities: parse manifest, validate video metadata, assign corpus version, provide lookup for video and locator.
- Non-responsibilities: extracting keyframes, reading OCR/ASR results, ranking candidates.
- Public interfaces: `import_manifest`, `get_corpus`, `get_video`, `resolve_locator`.
- Transaction boundary: import manifest writes corpus and videos atomically.
- Observability: import counts, invalid rows, checksum warnings.

### `keyframe_pipeline`

- Responsibilities: generate/import keyframes, maintain keyframe-to-video/frame/time map.
- Non-responsibilities: OCR, embedding, text/vector indexing.
- Public interfaces: `create_keyframe_run`, `import_keyframes`, `list_keyframes`.
- Transaction boundary: keyframe catalog publish happens after all required records validate.
- Observability: keyframes per video, skipped frames, duration coverage.

### `asr_pipeline`

- Responsibilities: extract/import transcripts, normalize text, create text index documents.
- Non-responsibilities: final text search scoring policy and fusion.
- Public interfaces: `run_asr_index`, `import_transcript`, `build_asr_text_docs`.
- Consistency boundary: transcript segment and text document reference the same `video_id/start_ms/end_ms`.
- Observability: segment count, empty transcript rate, ASR adapter errors.

### `ocr_pipeline`

- Responsibilities: detect/recognize scene text, persist OCR blocks, create OCR text documents.
- Non-responsibilities: visual semantic embedding or VQA answer generation.
- Public interfaces: `run_ocr_index`, `build_ocr_text_docs`.
- Consistency boundary: OCR block must reference an existing `keyframe_id`.
- Observability: blocks per keyframe, low-confidence distribution.

### `feature_pipeline`

- Responsibilities: create semantic vectors, color vectors/tags, object/attribute signals.
- Non-responsibilities: deciding final candidate rank.
- Public interfaces: `run_semantic_index`, `run_color_index`, `run_attribute_extraction`.
- Consistency boundary: vector id maps to one keyframe and one model version.
- Observability: vector count, dimension, model version, index build time.

### `index_registry`

- Responsibilities: store artifact manifests, active pointers, lineage and health checks.
- Non-responsibilities: building index content.
- Public interfaces: `publish_artifact`, `deprecate_artifact`, `get_active_artifacts`, `health_check`.
- Transaction boundary: active pointer switch is atomic.
- Observability: active artifact versions, publish/deprecate events.

### `query_planner`

- Responsibilities: validate task contract, normalize query, select retrieval branches.
- Non-responsibilities: executing search or ranking.
- Public interfaces: `submit_query`, `plan_retrieval`, `get_query_session`.
- Consistency boundary: query session stores active artifact versions used.
- Observability: task type, selected branches, validation failures.

### `retrieval_fusion`

- Responsibilities: execute branch search through adapters, normalize scores, merge/dedup, rerank.
- Non-responsibilities: importing dataset or producing final VQA answer.
- Public interfaces: `retrieve`, `combine_hits`, `rank_candidates`.
- Transaction boundary: raw hit lists and fusion run are persisted together for reproducibility.
- Observability: branch latency, hit counts, score breakdown, dedup groups.

### `task_solvers`

- Responsibilities: task-specific output for Textual KIS, TRAKE, VQA and future Visual KIS.
- Non-responsibilities: low-level index search implementation.
- Public interfaces: `create_kis_submission`, `solve_trake`, `answer_vqa`, `solve_visual_kis`.
- Consistency boundary: task output must reference ranked candidate/evidence generated by the same query session.
- Observability: selected rank, TRAKE order failures, VQA evidence used.

### `evaluation_ops`

- Responsibilities: feedback records, benchmark runs, metric reports, operational health.
- Non-responsibilities: mutating active index artifact content.
- Public interfaces: `record_feedback`, `run_evaluation`, `get_metrics`, `get_lineage`.
- Transaction boundary: evaluation run records query set, config and artifact versions.
- Observability: top-k metrics, failure categories, branch health.

### `api_ui_adapter`

- Responsibilities: stable CLI/REST/UI DTOs, error envelope, safe response shaping.
- Non-responsibilities: domain decisions.
- Public interfaces: REST endpoints in `05-api-design.md`, CLI commands in `10-local-development-setup.md`.
- Guardrails: strip private raw paths unless explicitly local debug mode.
- Observability: correlation id per request.

## Integration contracts

- Text search adapter contract: accepts normalized text query and branch kind, returns `CandidateHit` with `source_branch`, text match evidence and raw score.
- Vector search adapter contract: accepts vector query or query embedding, returns `CandidateHit` with vector score and model/index version.
- Artifact adapter contract: `open(artifact_id)` only succeeds for `ACTIVE` artifacts unless explicit maintenance mode.
- Evidence reader contract: returns safe evidence summary and internal evidence ref; raw media path is not exported by default.

## Cross-module transaction boundaries

| Boundary | Modules | Rule |
|---|---|---|
| Corpus import | `dataset_catalog` | Corpus and video records commit together. |
| Artifact publish | branch module + `index_registry` | Branch writes temp artifact; registry validates and atomically marks active. |
| Query run | `query_planner`, `retrieval_fusion` | Query session stores artifact versions before branch search starts. |
| Fusion run | `retrieval_fusion` | Raw hits and ranked candidates persist under same fusion config version. |
| Evaluation run | `evaluation_ops`, `retrieval_fusion` | Evaluation stores query set, artifact versions and metrics snapshot. |

## Target application structure

Current verified code only has `backend/src/aic_pipeline/__init__.py`. Target inferred structure:

```text
backend/src/aic_pipeline/
  domain/
  modules/
    dataset_catalog/
    keyframe_pipeline/
    asr_pipeline/
    ocr_pipeline/
    feature_pipeline/
    index_registry/
    query_planner/
    retrieval_fusion/
    task_solvers/
    evaluation_ops/
  adapters/
    filesystem/
    text_index/
    vector_index/
    media/
  api/
  cli/
  config/
```

## BRDS traceability

Every module row above includes `FR-*`/`BR-*`/`AC-*` traces. No technical module in this file is intended without a BRDS trace.

