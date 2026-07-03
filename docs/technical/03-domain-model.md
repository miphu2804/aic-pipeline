# Technical 03 - Domain model

## Aggregates and entities

| Aggregate | Entities/value objects | Owner module | Key invariants | Trace |
|---|---|---|---|---|
| `Corpus` | `CorpusManifest`, `VideoAsset`, `SourceMetadata` | `dataset_catalog` | Corpus version immutable once `READY`; video IDs unique per corpus. | FR-01, BR-02 |
| `FrameCatalog` | `Keyframe`, `FrameLocator` | `keyframe_pipeline` | Keyframe locator resolves to one video and timestamp. | FR-02, BR-01 |
| `TextEvidence` | `TranscriptSegment`, `OCRBlock`, `TextIndexDocument` | `asr_pipeline`, `ocr_pipeline` | Text docs keep source branch and evidence ref. | FR-03, FR-04, BR-03 |
| `VisualEvidence` | `FeatureVector`, `VisualAttribute` | `feature_pipeline` | Vector dimension and model version match artifact manifest. | FR-05, FR-06, BR-11 |
| `ArtifactRegistry` | `IndexArtifact`, `ArtifactManifest`, `ActiveArtifactPointer` | `index_registry` | Only one active artifact per branch/config scope unless explicitly versioned. | FR-14, BR-12 |
| `QueryRun` | `QuerySession`, `NormalizedQuery`, `RetrievalPlan` | `query_planner` | Task type determines required inputs and output contract. | FR-07, BR-07 |
| `CandidateSet` | `CandidateHit`, `RankedCandidate`, `FusionRun` | `retrieval_fusion` | Ranked candidate retains source hit/evidence breakdown. | FR-08, FR-09, BR-04 |
| `TaskOutput` | `TaskSubmission`, `TemporalEvent`, `TemporalSequence`, `VQAAnswer`, `VisualQuery` | `task_solvers` | Output must reference the same query session and candidate/evidence. | FR-10..FR-12, FR-15 |
| `Evaluation` | `FeedbackRecord`, `EvaluationRun`, `MetricSnapshot` | `evaluation_ops` | Feedback never mutates index artifact content. | FR-13, BR-10 |

## Value objects

| Value object | Fields | Validation | Trace |
|---|---|---|---|
| `FrameLocator` | `video_id`, `frame_id`, `timestamp_ms` | Non-empty IDs, timestamp non-negative, maps to known video/keyframe when required. | BR-02 |
| `TimeRange` | `start_ms`, `end_ms` | `0 <= start_ms < end_ms`; within video duration if known. | FR-03, FR-11 |
| `BoundingBox` | `x`, `y`, `width`, `height`, `coordinate_space` | Positive dimensions, within image bounds when image size known. | FR-04 |
| `ScoreBreakdown` | branch scores, fusion score, weights version | All scores finite; weights version present. | FR-09, BR-05 |
| `EvidenceRef` | `kind`, `source_id`, `summary`, `safe_preview_ref` | Source exists; safe response excludes private raw path by default. | BR-04, BR-13 |
| `ArtifactVersion` | `artifact_id`, `schema_version`, `model_version`, `config_hash` | Non-empty and compatible with adapter. | BR-11 |
| `TaskType` | enum | One of `TEXTUAL_KIS`, `VQA`, `TRAKE`, `VISUAL_KIS`. | BR-07 |

## Domain events

| Event | Emitted by | Payload | Consumers | Trace |
|---|---|---|---|---|
| `CorpusImported` | `dataset_catalog` | corpus id, version, video count | index jobs, audit | FR-01 |
| `KeyframesPrepared` | `keyframe_pipeline` | corpus id, keyframe count, coverage | branch index jobs | FR-02 |
| `IndexBranchBuilt` | branch modules | artifact id, branch, stats | `index_registry` | FR-03..FR-06 |
| `ArtifactPublished` | `index_registry` | active artifact id, previous id | query planner, health | FR-14 |
| `QueryPlanned` | `query_planner` | query id, task type, branch plan | retrieval fusion | FR-07 |
| `FusionCompleted` | `retrieval_fusion` | query id, candidate count, config version | task solvers, evaluation | FR-09 |
| `TaskOutputCreated` | `task_solvers` | query id, task type, output ref | API/UI, feedback | FR-10..FR-12 |
| `FeedbackRecorded` | `evaluation_ops` | feedback id, target id, label | evaluation reports | FR-13 |

## Lifecycle semantics

- `Corpus` is append-by-version, not in-place edited after `READY`.
- `IndexArtifact` is immutable after publish. Rebuild creates a new artifact.
- `QuerySession` is tied to active artifact versions captured at planning time.
- `FeedbackRecord` can influence future evaluation/fusion config, but cannot rewrite historical `FusionRun`.
- `TaskSubmission` is an internal draft/export object, not a guarantee of official contest submission format.

## Owner mapping

| Entity | Owner module | Writes from | Reads from |
|---|---|---|---|
| `CorpusManifest` | `dataset_catalog` | import command | all pipeline jobs |
| `Keyframe` | `keyframe_pipeline` | keyframe job | OCR, feature, retrieval evidence |
| `TranscriptSegment` | `asr_pipeline` | ASR job | text search, VQA evidence |
| `OCRBlock` | `ocr_pipeline` | OCR job | text search, VQA evidence |
| `FeatureVector` | `feature_pipeline` | embedding job | vector search |
| `IndexArtifact` | `index_registry` | publish command | query planner, health |
| `QuerySession` | `query_planner` | query submit | retrieval, task solvers, evaluation |
| `RankedCandidate` | `retrieval_fusion` | fusion run | task solvers, UI/API, evaluation |
| `VQAAnswer` | `task_solvers` | VQA command | UI/API, evaluation |
| `FeedbackRecord` | `evaluation_ops` | feedback command | evaluation reports |

## BRDS traceability

Technical aggregates derive from `docs/brds/06-domain-model.md` and map to FR-01 through FR-15, BR-02 through BR-14.

