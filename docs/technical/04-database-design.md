# Technical 04 - Database and artifact design

## Storage choice and rationale

V1 target is local-first:

- Metadata/control-plane store: SQLite or equivalent embedded database. This is inferred because Python includes SQLite support and repo has no runtime DB dependency yet.
- Vector artifact store: FAISS index files plus manifest, inferred from reference flow.
- Text index store: Meilisearch or equivalent text index, inferred from reference flow. If Meilisearch is not introduced yet, a simpler local text search adapter can satisfy the same contract for samples.
- Large media/artifacts: filesystem paths referenced by manifest.

These choices are target design, not verified installed dependencies.

## Data access pattern

- Domain modules read/write through repositories owned by their module.
- Search adapters own interaction with FAISS/text index internals.
- Application services depend on module interfaces, not direct table/index internals.
- Artifact manifests are read before opening any index file/service.

## Logical schema

| Table/Collection | Owner Module | Key Columns | Constraints | Indexes | Writes From | Reads From | Traces |
|---|---|---|---|---|---|---|---|
| `corpus_manifests` | `dataset_catalog` | `corpus_id`, `version`, `status`, `schema_version`, `created_at` | unique `(corpus_id, version)` | status, created_at | import manifest | all jobs | FR-01 |
| `video_assets` | `dataset_catalog` | `video_id`, `corpus_id`, `path`, `duration_ms`, `metadata_ref` | unique `(corpus_id, video_id)`, path required | corpus_id, video_id | import manifest | keyframe, ASR | FR-01, BR-02 |
| `source_metadata` | `dataset_catalog` | `metadata_id`, `video_id`, `title`, `description`, `publish_date` | video exists | video_id, publish_date | import manifest | retrieval evidence | FR-01 |
| `keyframes` | `keyframe_pipeline` | `keyframe_id`, `video_id`, `frame_id`, `timestamp_ms`, `path` | unique locator per corpus, timestamp >= 0 | video_id, timestamp_ms | keyframe job | OCR, vector, retrieval | FR-02, BR-01 |
| `transcript_segments` | `asr_pipeline` | `segment_id`, `video_id`, `start_ms`, `end_ms`, `text`, `confidence` | valid time range | video_id, start_ms | ASR job | text index, VQA | FR-03 |
| `ocr_blocks` | `ocr_pipeline` | `ocr_block_id`, `keyframe_id`, `bbox`, `text`, `confidence` | keyframe exists | keyframe_id, confidence | OCR job | text index, VQA | FR-04 |
| `visual_attributes` | `feature_pipeline` | `keyframe_id`, `color_tags`, `object_labels`, `confidence` | keyframe exists | color_tags, object_labels | feature job | retrieval/fusion | FR-06 |
| `index_artifacts` | `index_registry` | `artifact_id`, `branch`, `status`, `path`, `schema_version`, `model_version`, `config_hash` | active artifact manifest valid | branch, status | publish command | query planner | FR-14, BR-11 |
| `query_sessions` | `query_planner` | `query_id`, `task_type`, `status`, `raw_query`, `normalized_query`, `artifact_versions` | task type enum | task_type, status | query submit | retrieval, API | FR-07 |
| `candidate_hits` | `retrieval_fusion` | `hit_id`, `query_id`, `source_branch`, `locator`, `raw_score`, `evidence_ref` | locator required for user-facing hits | query_id, source_branch | branch search | fusion, evaluation | FR-08, BR-04 |
| `ranked_candidates` | `retrieval_fusion` | `candidate_id`, `query_id`, `rank`, `locator`, `fusion_score`, `score_breakdown` | unique `(query_id, rank)` | query_id, rank | fusion | task solvers, API | FR-09 |
| `task_outputs` | `task_solvers` | `output_id`, `query_id`, `task_type`, `status`, `payload`, `evidence_refs` | output matches task type | query_id, task_type | task solvers | API/evaluation | FR-10..FR-12, FR-15 |
| `feedback_records` | `evaluation_ops` | `feedback_id`, `query_id`, `target_id`, `label`, `note`, `created_at` | target exists | query_id, label | feedback command | evaluation | FR-13, BR-10 |
| `evaluation_runs` | `evaluation_ops` | `run_id`, `query_set_ref`, `config_version`, `artifact_versions`, `metrics` | config version required | created_at | evaluation command | reports | FR-13 |

## Artifact layout

Target inferred layout:

```text
artifacts/
  corpora/<corpus_id>/<version>/manifest.json
  keyframes/<corpus_id>/<run_id>/
  text-index/<branch>/<artifact_id>/manifest.json
  vector-index/<branch>/<artifact_id>/manifest.json
  vector-index/<branch>/<artifact_id>/index.faiss
  eval/<run_id>/report.json
```

## Indexes supporting query patterns

| Query pattern | Required index |
|---|---|
| Find video/keyframe by locator | `keyframes(video_id, frame_id)`, `keyframes(video_id, timestamp_ms)` |
| Search OCR/ASR text | text index branch documents plus metadata store lookup |
| Semantic top-k | FAISS semantic index keyed by `keyframe_id` |
| Color/object filter | `visual_attributes` tags plus optional color vector index |
| Query result page | `ranked_candidates(query_id, rank)` |
| Evaluation by run | `evaluation_runs(created_at)`, `feedback_records(query_id)` |

## Concurrency and capacity guardrails

- Only `index_registry` can switch an artifact to `ACTIVE`.
- Online query opens a snapshot of artifact versions captured during `QuerySession` creation.
- Index build writes to temp path and publishes atomically.
- Large vectors/images remain in artifact files, not copied into metadata rows.
- Retain previous active artifact until replacement is verified.

## Migration/bootstrap approach

- Schema migrations should be versioned and run before CLI/API startup.
- Bootstrap local dev with a small sample corpus, synthetic keyframes and fixture OCR/ASR/vector docs.
- Backfill jobs must create new artifacts instead of mutating active artifacts in place.

## Retention policy

| Data | Retention v1 |
|---|---|
| Raw media | Managed outside pipeline, referenced by manifest. |
| Active artifacts | Keep current and previous active version per branch. |
| Failed temp artifacts | Keep until debug TTL or manual cleanup. |
| Query sessions | Keep during evaluation cycle; allow cleanup by run/corpus. |
| Feedback/evaluation | Keep with query set/config version for reproducibility. |

## BRDS traceability

Storage design covers FR-01 through FR-14, BR-02 through BR-13, NFR-01, NFR-04 and NFR-09.

