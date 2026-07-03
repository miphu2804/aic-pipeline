# BRDS 05 - State machine

## Canonical state list

| Lifecycle | States | Owner capability |
|---|---|---|
| `CorpusAsset` | `DRAFT`, `READY`, `ARCHIVED` | Dataset & Asset Catalog |
| `IndexRun` | `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED` | Signal Extraction |
| `IndexArtifact` | `BUILDING`, `ACTIVE`, `FAILED`, `DEPRECATED` | Operations |
| `QuerySession` | `DRAFT`, `RUNNING`, `COMBINING`, `READY`, `READY_WITH_WARNINGS`, `FAILED`, `REJECTED` | Query/Retrieval |
| `CandidateReview` | `UNSEEN`, `VIEWED`, `SELECTED`, `REJECTED` | Task Solvers |
| `Submission` | `DRAFT`, `READY`, `EXPORTED`, `VOIDED` | Task Solvers |
| `Answer` | `DRAFT`, `ANSWERED`, `UNANSWERED` | VQA |
| `Feedback` | `NEW`, `APPLIED_TO_RUN`, `IGNORED` | Evaluation |

## CorpusAsset transitions

| From | To | Trigger | Actor/System | Guard Condition | Side Effects | Reject Code | Traces |
|---|---|---|---|---|---|---|---|
| `DRAFT` | `READY` | Manifest validated | `PipelineOperator` | Tất cả video có canonical ID và path hợp lệ. | Tạo corpus version. | `MANIFEST_INVALID` | FR-01, BR-02 |
| `READY` | `ARCHIVED` | Corpus superseded | `Maintainer` | Không có index run đang dùng corpus làm active target. | Mark corpus read-only. | `CORPUS_IN_USE` | FR-14 |

## IndexRun transitions

| From | To | Trigger | Actor/System | Guard Condition | Side Effects | Reject Code | Traces |
|---|---|---|---|---|---|---|---|
| `QUEUED` | `RUNNING` | Worker starts job | `SystemJob` | Corpus ready, config valid. | Ghi start log. | `PIPELINE_CONFIG_INVALID` | FR-02..FR-06 |
| `RUNNING` | `SUCCEEDED` | All required branches complete | `SystemJob` | Artifact manifests valid. | Publish artifacts atomically. | `INDEX_VERSION_MISMATCH` | BR-11, BR-12 |
| `RUNNING` | `FAILED` | Required branch fails | `SystemJob` | Không recover được trong retry budget. | Giữ artifact active cũ. | `INDEX_BRANCH_FAILED` | NFR-09 |
| `RUNNING` | `CANCELLED` | Manual cancel | `PipelineOperator` | Job chưa publish active artifact mới. | Clean temp artifacts. | `CANCEL_NOT_ALLOWED` | FR-14 |

## IndexArtifact transitions

| From | To | Trigger | Actor/System | Guard Condition | Side Effects | Reject Code | Traces |
|---|---|---|---|---|---|---|---|
| `BUILDING` | `ACTIVE` | Publish artifact | `SystemJob` | Manifest, schema, model version hợp lệ. | Artifact có thể phục vụ query. | `ARTIFACT_MANIFEST_INVALID` | BR-11, BR-12 |
| `BUILDING` | `FAILED` | Build failure | `SystemJob` | Lỗi branch không recover. | Ghi error và path temp. | `INDEX_BRANCH_FAILED` | AC-14 |
| `ACTIVE` | `DEPRECATED` | Artifact replaced | `Maintainer` | Artifact mới đã active hoặc user xác nhận deprecate. | Không dùng cho query mới. | `ARTIFACT_REPLACEMENT_INVALID` | FR-14 |

## QuerySession transitions

| From | To | Trigger | Actor/System | Guard Condition | Side Effects | Reject Code | Traces |
|---|---|---|---|---|---|---|---|
| `DRAFT` | `RUNNING` | Query submitted | `CompetitorUser` | Task contract hợp lệ. | Tạo retrieval plan. | `TASK_CONTRACT_INVALID` | FR-07 |
| `DRAFT` | `REJECTED` | Validation fails | System | Query rỗng hoặc filter sai. | Lưu reason code. | `QUERY_INVALID` | BR-07 |
| `RUNNING` | `COMBINING` | Branch retrieval complete | `SystemJob` | Ít nhất một branch có hit hoặc warning. | Chuẩn bị fusion. | `INDEX_BRANCH_UNAVAILABLE` | FR-08 |
| `COMBINING` | `READY` | Fusion success | `SystemJob` | Candidate có evidence và locator. | Ranked list available. | `EVIDENCE_MISSING` | FR-09 |
| `COMBINING` | `READY_WITH_WARNINGS` | Partial result | `SystemJob` | Một số branch lỗi nhưng vẫn có result usable. | Gắn warnings. | `PARTIAL_INDEX_RESULT` | NFR-09 |
| `RUNNING` | `FAILED` | No usable branch | `SystemJob` | Không có index active hoặc timeout toàn bộ. | Error response. | `NO_ACTIVE_INDEX` | AC-08 |

## Submission transitions

| From | To | Trigger | Actor/System | Guard Condition | Side Effects | Reject Code | Traces |
|---|---|---|---|---|---|---|---|
| `DRAFT` | `READY` | User selects candidate | `CompetitorUser` | Candidate có `video_id/frame_id`. | Store selected candidate. | `CANONICAL_LOCATOR_MISSING` | FR-10 |
| `READY` | `EXPORTED` | User exports/copies answer | `CompetitorUser` | Output contract hợp lệ theo task. | Audit selected rank. | `SUBMISSION_FORMAT_INVALID` | AC-10 |
| `DRAFT` | `VOIDED` | Session discarded | `CompetitorUser` | No export performed. | Mark inactive. | none | FR-10 |

## Invalid transition policy

- Transition không có trong bảng phải bị reject bằng `INVALID_STATE_TRANSITION`.
- Không transition nào được xóa artifact active cũ nếu artifact mới chưa valid.
- Query failed không được mutate index, feedback hoặc raw media.

