# Technical 05 - API design

## API principles

- API shape is a target contract. Current repo has no web framework dependency.
- Base path: `/api/v1`.
- Every response includes `correlation_id`.
- Errors use the standard envelope in `09-error-handling.md`.
- User-facing result payloads must include safe evidence refs, not private raw paths.

## Response envelope

```json
{
  "data": {},
  "meta": {
    "correlation_id": "req_123",
    "artifact_versions": {}
  }
}
```

## Endpoint matrix

| Method | Path | Actor | Module | Request | Success Response | Error Codes | Traces |
|---|---|---|---|---|---|---|---|
| `POST` | `/corpora/import` | `PipelineOperator` | `dataset_catalog` | manifest path/body | corpus summary | `MANIFEST_INVALID`, `AUTH_FORBIDDEN` | FR-01, AC-01 |
| `GET` | `/corpora/{corpus_id}` | Operator/Evaluator/Maintainer | `dataset_catalog` | corpus id | corpus details | `RESOURCE_NOT_FOUND` | FR-01 |
| `POST` | `/index-runs` | `PipelineOperator` | branch modules, `index_registry` | corpus id, branches, config | index run id/status | `PIPELINE_CONFIG_INVALID`, `CORPUS_NOT_READY` | FR-02..FR-06 |
| `GET` | `/index-runs/{run_id}` | Operator/Maintainer | `index_registry` | run id | run status, branch stats | `RESOURCE_NOT_FOUND` | FR-14 |
| `GET` | `/artifacts/active` | Operator/Evaluator/Maintainer | `index_registry` | optional branch | active artifacts | `ARTIFACT_NOT_ACTIVE` | FR-14, AC-14 |
| `POST` | `/queries` | `CompetitorUser` | `query_planner`, `retrieval_fusion` | task type, query, filters | query id, status | `TASK_CONTRACT_INVALID`, `QUERY_INVALID`, `NO_ACTIVE_INDEX` | FR-07, FR-08 |
| `GET` | `/queries/{query_id}/results` | `CompetitorUser` | `retrieval_fusion` | pagination | ranked candidates | `RESOURCE_NOT_FOUND`, `QUERY_NOT_READY` | FR-09, FR-10 |
| `POST` | `/queries/{query_id}/kis-submission` | `CompetitorUser` | `task_solvers` | candidate id | submission draft | `CANONICAL_LOCATOR_MISSING`, `SUBMISSION_FORMAT_INVALID` | FR-10 |
| `POST` | `/queries/{query_id}/trake` | `CompetitorUser`/System | `task_solvers` | optional constraints | ordered sequence | `TRAKE_ORDER_NOT_FOUND` | FR-11 |
| `POST` | `/queries/{query_id}/vqa-answer` | `CompetitorUser`/System | `task_solvers` | answer config | answer with evidence | `INSUFFICIENT_EVIDENCE` | FR-12 |
| `POST` | `/queries/{query_id}/feedback` | Competitor/Evaluator | `evaluation_ops` | target, label, note | feedback record | `FEEDBACK_TARGET_INVALID` | FR-13 |
| `POST` | `/evaluation-runs` | `Evaluator` | `evaluation_ops` | query set, config | evaluation summary | `EVALUATION_QUERYSET_INVALID` | FR-13 |
| `GET` | `/health` | Operator/Maintainer | `evaluation_ops`, `index_registry` | none | health summary | none or degraded warnings | FR-14 |

## Pagination and list contract

| List endpoint | Default page size | Max page size | Default sort | Allowed filters | Empty behavior |
|---|---|---|---|---|---|
| `/queries/{query_id}/results` | 50 | 200 | `rank asc` | `source_branch`, `video_id`, `min_score` | Return empty `data` with query status. |
| `/index-runs` | 20 | 100 | `created_at desc` | `status`, `corpus_id`, `branch` | Return empty list. |
| `/evaluation-runs` | 20 | 100 | `created_at desc` | `query_set`, `config_version` | Return empty list. |

Invalid pagination returns `QUERY_PARAM_INVALID`.

## Core request examples

### Submit Textual KIS query

```json
{
  "task_type": "TEXTUAL_KIS",
  "query": {
    "text": "người đàn ông mặc áo vàng viền đen đang trả lời phỏng vấn"
  },
  "top_k": 100
}
```

### Candidate result

```json
{
  "candidate_id": "cand_001",
  "rank": 1,
  "locator": {
    "video_id": "L01_V001",
    "frame_id": "000123",
    "timestamp_ms": 42100
  },
  "fusion_score": 0.82,
  "score_breakdown": {
    "semantic": 0.76,
    "ocr": 0.31,
    "asr": 0.12,
    "color": 0.68
  },
  "evidence": [
    {
      "kind": "semantic",
      "summary": "visual-text embedding match",
      "source_ref": "vec_hit_001"
    }
  ]
}
```

### VQA answer response

```json
{
  "answer_id": "ans_001",
  "status": "ANSWERED",
  "answer_text": "Có 5 người.",
  "confidence": 0.71,
  "evidence_refs": ["cand_001", "ocr_204", "obj_117"]
}
```

## Idempotency and concurrency policy

- Import/index commands should accept optional `idempotency_key`.
- Query submit can be non-idempotent by default, but evaluation runs should store query set/config for reproducibility.
- Artifact publish is guarded by artifact manifest hash and active pointer version.
- Query uses artifact versions captured at planning time even if a newer artifact is published mid-query.

## API-level traceability

Every endpoint maps to one module in `02-module-breakdown.md` and error codes in `09-error-handling.md`.

