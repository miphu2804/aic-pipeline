# Technical 07 - State machines

## State persistence owners

| Lifecycle | Persistence owner | Guard functions |
|---|---|---|
| `CorpusAsset` | `dataset_catalog` | `can_publish_corpus`, `can_archive_corpus` |
| `IndexRun` | `index_registry` | `can_start_index_run`, `can_finish_index_run`, `can_cancel_index_run` |
| `IndexArtifact` | `index_registry` | `can_publish_artifact`, `can_deprecate_artifact` |
| `QuerySession` | `query_planner` | `can_start_query`, `can_combine_results`, `can_finish_query` |
| `Submission` | `task_solvers` | `can_create_submission`, `can_export_submission` |
| `Answer` | `task_solvers` | `can_answer_vqa`, `can_mark_unanswered` |
| `Feedback` | `evaluation_ops` | `can_record_feedback`, `can_apply_feedback` |

## Technical transition table

| Lifecycle | From | To | Guard function | Error code | Side effects | BRDS Trace |
|---|---|---|---|---|---|---|
| `CorpusAsset` | `DRAFT` | `READY` | `can_publish_corpus` | `MANIFEST_INVALID` | Commit corpus version. | FR-01, BR-02 |
| `CorpusAsset` | `READY` | `ARCHIVED` | `can_archive_corpus` | `CORPUS_IN_USE` | Mark read-only. | FR-14 |
| `IndexRun` | `QUEUED` | `RUNNING` | `can_start_index_run` | `PIPELINE_CONFIG_INVALID` | Start branch jobs. | FR-02..FR-06 |
| `IndexRun` | `RUNNING` | `SUCCEEDED` | `can_finish_index_run` | `ARTIFACT_MANIFEST_INVALID` | Publish active artifacts. | BR-11, BR-12 |
| `IndexRun` | `RUNNING` | `FAILED` | unconditional on fatal branch failure | `INDEX_BRANCH_FAILED` | Preserve previous active artifact. | NFR-09 |
| `IndexRun` | `RUNNING` | `CANCELLED` | `can_cancel_index_run` | `CANCEL_NOT_ALLOWED` | Cleanup temp artifacts. | FR-14 |
| `IndexArtifact` | `BUILDING` | `ACTIVE` | `can_publish_artifact` | `INDEX_VERSION_MISMATCH` | Switch active pointer. | FR-14 |
| `IndexArtifact` | `BUILDING` | `FAILED` | unconditional on build failure | `INDEX_BRANCH_FAILED` | Store failure metadata. | AC-14 |
| `IndexArtifact` | `ACTIVE` | `DEPRECATED` | `can_deprecate_artifact` | `ARTIFACT_REPLACEMENT_INVALID` | Stop serving new queries. | BR-12 |
| `QuerySession` | `DRAFT` | `RUNNING` | `can_start_query` | `TASK_CONTRACT_INVALID` | Store artifact versions. | FR-07 |
| `QuerySession` | `DRAFT` | `REJECTED` | unconditional on validation fail | `QUERY_INVALID` | Store reject reason. | BR-07 |
| `QuerySession` | `RUNNING` | `COMBINING` | `can_combine_results` | `NO_USABLE_BRANCH_HITS` | Persist raw hits. | FR-08 |
| `QuerySession` | `COMBINING` | `READY` | `can_finish_query` | `EVIDENCE_MISSING` | Persist ranked candidates. | FR-09 |
| `QuerySession` | `COMBINING` | `READY_WITH_WARNINGS` | `can_finish_query_with_warnings` | `PARTIAL_INDEX_RESULT` | Persist warnings. | NFR-09 |
| `QuerySession` | `RUNNING` | `FAILED` | unconditional on no active index | `NO_ACTIVE_INDEX` | Store failure. | AC-08 |
| `Submission` | `DRAFT` | `READY` | `can_create_submission` | `CANONICAL_LOCATOR_MISSING` | Store selected locator. | FR-10 |
| `Submission` | `READY` | `EXPORTED` | `can_export_submission` | `SUBMISSION_FORMAT_INVALID` | Audit export. | AC-10 |
| `Answer` | `DRAFT` | `ANSWERED` | `can_answer_vqa` | `INSUFFICIENT_EVIDENCE` | Store answer/evidence. | FR-12 |
| `Answer` | `DRAFT` | `UNANSWERED` | `can_mark_unanswered` | `INSUFFICIENT_EVIDENCE` | Store reason. | BR-09 |
| `Feedback` | `NEW` | `APPLIED_TO_RUN` | `can_apply_feedback` | `FEEDBACK_TARGET_INVALID` | Include in evaluation report. | FR-13 |
| `Feedback` | `NEW` | `IGNORED` | unconditional on duplicate/invalid target | `FEEDBACK_DUPLICATE` | Preserve audit. | BR-10 |

## Invalid transition policy

- Domain services must reject transitions not listed here with `INVALID_STATE_TRANSITION`.
- Guard functions return structured reason codes, not boolean-only failure.
- State transition tests must assert both allowed and forbidden paths.

## BRDS traceability

This file mirrors `docs/brds/05-state-machine.md` and implements BR-01, BR-02, BR-07, BR-08, BR-09, BR-11 and BR-12.

