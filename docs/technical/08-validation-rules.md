# Technical 08 - Validation rules

## Validation strategy by layer

| Layer | Responsibility | Examples |
|---|---|---|
| Request/schema | Type, required fields, enum values, pagination, file reference shape. | task type enum, `top_k`, manifest columns |
| Auth/scope | Actor role, session ownership, capability permission. | can export submission, can publish artifact |
| State guard | Current lifecycle permits command. | artifact `BUILDING -> ACTIVE`, query `DRAFT -> RUNNING` |
| Domain/business | BRDS rules and invariants. | locator required, evidence required, TRAKE order |
| Adapter/runtime | External tool availability and artifact compatibility. | text index up, FAISS dimension match |

## Rule catalog

| Rule ID | Validation Rule | Trigger/Operation | Layer | Outcome On Fail | Error Code | Traces |
|---|---|---|---|---|---|---|
| VAL-01 | Manifest row has non-empty `video_id` and path. | Import corpus | Request/domain | Reject row or manifest. | `MANIFEST_INVALID` | BR-02, AC-01 |
| VAL-02 | `FrameLocator` resolves to known video/keyframe when user-facing. | Keyframe import, fusion, submission | Domain | Reject record/candidate. | `CANONICAL_LOCATOR_MISSING` | BR-02 |
| VAL-03 | Keyframe timestamp is non-negative and within video duration if known. | Keyframe build/import | Domain | Reject keyframe. | `KEYFRAME_OUT_OF_RANGE` | BR-01, AC-02 |
| VAL-04 | Artifact manifest includes branch, schema version, model/config version and path. | Publish artifact | Domain/adapter | Do not activate artifact. | `ARTIFACT_MANIFEST_INVALID` | BR-11 |
| VAL-05 | Vector dimension equals artifact manifest dimension. | Vector build/open | Adapter | Fail branch. | `VECTOR_DIMENSION_MISMATCH` | FR-05 |
| VAL-06 | OCR block references existing `keyframe_id`. | OCR build | Domain | Drop/reject OCR block. | `OCR_OUTPUT_UNMAPPED` | FR-04 |
| VAL-07 | Transcript segment has valid time range. | ASR build | Domain | Reject segment. | `TRANSCRIPT_SEGMENT_INVALID` | FR-03 |
| VAL-08 | Query task type matches input contract. | Submit query | Request/domain | Reject query. | `TASK_CONTRACT_INVALID` | BR-07, AC-07 |
| VAL-09 | Required active artifacts exist for selected branch policy. | Submit/retrieve query | Adapter/state | Fail or degraded warning. | `NO_ACTIVE_INDEX` | BR-12, AC-08 |
| VAL-10 | Raw hit has evidence ref and score. | Branch retrieval | Domain | Drop hit or mark warning. | `EVIDENCE_MISSING` | BR-04 |
| VAL-11 | Fusion config has valid weights and deterministic version. | Fusion | Domain | Fail fusion. | `FUSION_CONFIG_INVALID` | BR-05 |
| VAL-12 | TRAKE candidate sequence respects temporal order. | TRAKE assembly | Domain | Return no sequence. | `TRAKE_ORDER_NOT_FOUND` | BR-08 |
| VAL-13 | VQA answer has enough evidence refs. | VQA answer | Domain | Mark unanswered. | `INSUFFICIENT_EVIDENCE` | BR-09 |
| VAL-14 | Feedback target exists and belongs to query/evaluation scope. | Record feedback | Domain/scope | Reject feedback. | `FEEDBACK_TARGET_INVALID` | BR-10 |
| VAL-15 | Response/export does not include private raw paths unless local debug mode. | API response/export | Adapter/security | Strip or reject field. | `DATA_PATH_NOT_EXPORTABLE` | BR-13 |
| VAL-16 | Each branch hit keeps source branch, raw score and evidence before fusion. | Branch retrieval and fusion | Domain | Drop hit or fail fusion depending on policy. | `EVIDENCE_MISSING` | BR-03, BR-04 |
| VAL-17 | Duplicate or rebroadcast candidates keep duplicate group metadata before dedup/rerank. | Fusion/rerank | Domain | Keep alternatives with warning when ambiguity remains. | `DUPLICATE_GROUP_AMBIGUOUS` | BR-06 |

## Validation pipeline by operation

### Import corpus

1. Validate actor role.
2. Validate manifest schema.
3. Validate row identity and path.
4. Validate duplicate `video_id`.
5. Persist corpus transaction.

### Build/publish artifact

1. Validate actor role or system job request.
2. Validate corpus `READY`.
3. Validate branch config and model/config version.
4. Validate generated records.
5. Validate artifact manifest.
6. Publish active pointer atomically.

### Submit query

1. Validate actor session.
2. Validate task type and request schema.
3. Validate task-specific input.
4. Resolve active artifact versions.
5. Create `QuerySession RUNNING`.
6. Execute branch retrieval.
7. Validate hits/evidence.
8. Validate duplicate group metadata when candidates are visually/textually near-identical.
9. Fusion/rerank.

### Create KIS submission

1. Validate user owns query session.
2. Validate query is `READY`.
3. Validate candidate exists and has locator.
4. Create `Submission READY`.
5. Export only task output fields.

### Solve TRAKE

1. Validate task type.
2. Validate sub-event decomposition.
3. Retrieve per sub-event.
4. Validate candidate locator per event.
5. Validate temporal order.
6. Return ordered sequence or `TRAKE_ORDER_NOT_FOUND`.

### Answer VQA

1. Validate task type.
2. Retrieve candidates/evidence.
3. Validate evidence coverage.
4. Generate answer.
5. Validate answer references evidence.
6. Return `ANSWERED` or `UNANSWERED`.

## Determinism requirements

- Fusion config version must be stored with every `FusionRun`.
- Evaluation run must pin corpus, artifact versions and query set.
- Validation order must remain stable so tests can assert first failure code.

## BRDS traceability

Validation rules implement BR-01 through BR-14 and acceptance AC-01 through AC-15.
