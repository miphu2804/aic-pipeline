# Technical 09 - Error handling

## Goals

- Return stable reason codes that map to BRDS rules.
- Preserve enough context for debugging without leaking raw private paths.
- Allow degraded query results when branch failure policy permits.
- Make indexing failures actionable by branch and artifact.

## Error taxonomy

| Category | HTTP status target | Examples |
|---|---|---|
| Validation | 400 | invalid query, manifest schema, pagination |
| Auth/scope | 401/403 | missing role, forbidden capability |
| Not found | 404 | unknown corpus/query/artifact |
| Conflict/state | 409 | invalid state transition, artifact mismatch |
| Dependency/runtime | 424/503 | text index down, vector index missing |
| Internal | 500 | unexpected unhandled error |

## Standard error response envelope

```json
{
  "error": {
    "code": "TASK_CONTRACT_INVALID",
    "message": "Query input does not match task type.",
    "details": {
      "field": "task_type"
    },
    "correlation_id": "req_123"
  }
}
```

## Error code catalog

| Code | Status | Meaning | Raised By | User Message Guidance | Retry? | Traces |
|---|---|---|---|---|---|---|
| `AUTH_FORBIDDEN` | 403 | Actor lacks capability. | `api_ui_adapter` | Không có quyền thao tác này. | No | Technical 01 |
| `MANIFEST_INVALID` | 400 | Manifest schema/path/ID invalid. | `dataset_catalog` | Kiểm tra manifest và dòng lỗi. | After fix | FR-01, AC-01 |
| `CORPUS_NOT_READY` | 409 | Index requested before corpus ready. | `index_registry` | Import corpus trước khi index. | After state change | FR-02 |
| `CORPUS_IN_USE` | 409 | Cannot archive active corpus. | `dataset_catalog` | Corpus đang được artifact/query dùng. | After cleanup | FR-14 |
| `CANONICAL_LOCATOR_MISSING` | 409 | Candidate/output lacks locator. | `dataset_catalog`, `retrieval_fusion`, `task_solvers` | Candidate không đủ `VideoId/FrameId`. | No | BR-02 |
| `KEYFRAME_MAP_REQUIRED` | 409 | Search/index needs keyframe map. | `keyframe_pipeline` | Chạy/import keyframe trước. | After build | BR-01 |
| `KEYFRAME_OUT_OF_RANGE` | 400 | Keyframe timestamp invalid. | `keyframe_pipeline` | Kiểm tra timestamp/duration. | After fix | AC-02 |
| `ASR_INPUT_UNREADABLE` | 424 | Audio/video cannot be read. | `asr_pipeline` | Kiểm tra media/audio input. | After fix | FR-03 |
| `TRANSCRIPT_SEGMENT_INVALID` | 400 | ASR segment range invalid. | `asr_pipeline` | Kiểm tra transcript segment. | After fix | FR-03 |
| `OCR_OUTPUT_UNMAPPED` | 409 | OCR block does not map keyframe. | `ocr_pipeline` | Kiểm tra keyframe/OCR output. | After fix | FR-04 |
| `VECTOR_DIMENSION_MISMATCH` | 409 | Vector dimension does not match artifact. | `feature_pipeline` | Rebuild index với model/config đúng. | After rebuild | FR-05 |
| `ATTRIBUTE_CONFIG_INVALID` | 400 | Color/object config invalid. | `feature_pipeline` | Kiểm tra config attribute. | After fix | FR-06 |
| `ARTIFACT_MANIFEST_INVALID` | 409 | Artifact manifest incomplete/invalid. | `index_registry` | Artifact không được publish. | After rebuild | BR-11 |
| `ARTIFACT_NOT_ACTIVE` | 409 | Query attempted to use non-active artifact. | `index_registry` | Chọn artifact active hoặc publish lại. | After state change | BR-12 |
| `INDEX_VERSION_MISMATCH` | 409 | Artifact schema/model/config mismatch. | `index_registry`, adapters | Rebuild hoặc migration artifact. | After rebuild | BR-11 |
| `INDEX_BRANCH_FAILED` | 424 | Index branch build failed. | branch modules | Xem branch log và rerun. | Yes | NFR-09 |
| `INDEX_BRANCH_UNAVAILABLE` | 503 | Branch unavailable during query. | `retrieval_fusion` | Một nhánh index đang lỗi. | Yes | FR-08 |
| `NO_ACTIVE_INDEX` | 503 | No usable active index. | `query_planner` | Build/publish index trước. | After build | AC-08 |
| `NO_USABLE_BRANCH_HITS` | 404 | Retrieval returned no usable hits. | `retrieval_fusion` | Thử query khác hoặc kiểm index. | Maybe | FR-08 |
| `TASK_CONTRACT_INVALID` | 400 | Input does not match task type. | `query_planner` | Kiểm tra loại task và input. | After fix | BR-07 |
| `QUERY_INVALID` | 400 | Query body/filter invalid. | `query_planner` | Kiểm tra query/filter. | After fix | AC-07 |
| `QUERY_NOT_READY` | 409 | Results requested before query ready. | `api_ui_adapter` | Đợi query hoàn tất. | Yes | FR-09 |
| `EVIDENCE_MISSING` | 409 | Candidate lacks required evidence. | `retrieval_fusion` | Candidate bị loại hoặc cần rebuild evidence. | No | BR-04 |
| `FUSION_CONFIG_INVALID` | 400 | Fusion weights/config invalid. | `retrieval_fusion` | Kiểm tra fusion config. | After fix | BR-05 |
| `DUPLICATE_GROUP_AMBIGUOUS` | 200/206 | Candidate group contains near-duplicates that cannot be confidently collapsed. | `retrieval_fusion` | Hiển thị alternatives để user chọn. | No | BR-06 |
| `PARTIAL_INDEX_RESULT` | 206 | Result degraded because branch failed. | `retrieval_fusion` | Kết quả có warning. | Maybe | NFR-09 |
| `TRAKE_DECOMPOSITION_FAILED` | 400 | Cannot split TRAKE query. | `task_solvers` | Viết query thành chuỗi event rõ hơn. | After fix | FR-11 |
| `TRAKE_ORDER_NOT_FOUND` | 404 | No sequence respects temporal order. | `task_solvers` | Không tìm được chuỗi hợp lệ. | Maybe | BR-08 |
| `INSUFFICIENT_EVIDENCE` | 422 | VQA lacks evidence. | `task_solvers` | Không đủ căn cứ để trả lời. | Maybe | BR-09 |
| `VQA_UNSUPPORTED_QUESTION` | 400 | VQA pattern unsupported. | `task_solvers` | Câu hỏi chưa hỗ trợ trong v1. | After change | FR-12 |
| `SUBMISSION_FORMAT_INVALID` | 409 | Output does not match task contract. | `task_solvers` | Không export được output. | No | AC-10 |
| `FEEDBACK_TARGET_INVALID` | 400 | Feedback target missing/scope invalid. | `evaluation_ops` | Chọn candidate/query hợp lệ. | After fix | BR-10 |
| `EVALUATION_QUERYSET_INVALID` | 400 | Query set invalid. | `evaluation_ops` | Kiểm tra query set. | After fix | FR-13 |
| `DATA_PATH_NOT_EXPORTABLE` | 403 | Response would leak private path. | `api_ui_adapter` | Dùng safe reference. | No | BR-13 |
| `INVALID_STATE_TRANSITION` | 409 | Lifecycle transition not allowed. | domain services | Kiểm tra trạng thái hiện tại. | After state change | Technical 07 |

## Retry and idempotency policy

- Validation errors are not retried automatically.
- Branch runtime failures may retry within configured budget.
- Artifact publish is idempotent only when manifest hash and idempotency key match.
- Query branch failure can return degraded result if at least one branch is usable and task policy permits.

## Logging and audit correlation

Minimum log fields:

- `correlation_id`
- `actor_id`
- `role`
- `module`
- `operation`
- `state_from`, `state_to` when applicable
- `artifact_id`, `query_id`, `run_id` when applicable
- `error_code`
- safe remediation hint

## BRDS traceability

Error codes map to BR-01 through BR-14, AC-01 through AC-15 and NFR-05/NFR-09.
