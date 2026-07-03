# Technical 01 - Roles and permissions

## Access model

V1 dùng role nội bộ ở mức application/session, chưa yêu cầu SSO hoặc multi-tenant auth. Khi triển khai API thật, authorization phải nằm trước domain command và audit sensitive action.

## Permission matrix

| Capability | CompetitorUser | PipelineOperator | Evaluator | Maintainer | SystemJob | Notes/Scope | Traces |
|---|---|---|---|---|---|---|---|
| Import corpus manifest | No | Yes | No | Yes | No | Chỉ operator/maintainer tạo corpus version. | FR-01 |
| Run keyframe/index jobs | No | Yes | No | Yes | Yes | SystemJob chạy theo request đã validate. | FR-02..FR-06 |
| Publish active artifact | No | Yes | No | Yes | Yes | Cần artifact manifest hợp lệ. | FR-14, BR-11 |
| Submit query | Yes | Yes | Yes | Yes | No | Evaluator dùng cho benchmark. | FR-07 |
| View ranked candidates | Yes | Yes | Yes | Yes | No | Scope theo query session hoặc evaluation run. | FR-09, FR-10 |
| Export submission draft | Yes | No | No | Yes | No | Chỉ export locator/answer, không export raw data path. | FR-10, BR-13 |
| Create feedback label | Yes | No | Yes | Yes | No | Feedback không mutate raw index. | FR-13, BR-10 |
| Run evaluation report | No | No | Yes | Yes | Yes | Query set phải versioned. | FR-13 |
| View health/lineage | No | Yes | Yes | Yes | Yes | Không expose private path quá mức. | FR-14, BR-13 |
| Change pipeline config | No | No | No | Yes | No | Config version mới cần compatibility check. | FR-14, BR-11 |

## Scope constraints

- `CompetitorUser` chỉ truy cập query session, candidate và submission draft thuộc session hiện tại.
- `Evaluator` được đọc query/evaluation data nhưng không được publish artifact.
- `PipelineOperator` được chạy job và xem health nhưng không sửa code/config schema.
- `Maintainer` là role duy nhất được đổi config/schema và deprecate artifact.
- `SystemJob` không có quyền tự tạo policy; chỉ thực thi command đã authorize.

## Account/session provisioning rules

| Rule | Description | Trace |
|---|---|---|
| RP-01 | Local MVP có thể dùng profile config thay vì user database. | NFR-06 |
| RP-02 | Mọi command mutating phải có `actor_id`, `role`, `correlation_id`. | FR-14 |
| RP-03 | Session hết hạn không được export submission draft. | FR-10 |
| RP-04 | SystemJob phải ghi `requested_by` từ command gốc. | FR-14 |

## Sensitive action guardrails

| Action | Guardrail | Minimum audit payload | Trace |
|---|---|---|---|
| Publish artifact | Validate manifest, schema, model/config version, artifact status. | actor, artifact_id, previous_active, new_active, config_version | BR-11, BR-12 |
| Deprecate artifact | Require Maintainer or explicit operator command when replacement exists. | actor, artifact_id, reason | FR-14 |
| Export submission | Ensure locator/answer contract is valid and no raw private path leaks. | actor, query_id, task_type, selected_locator, rank | BR-02, BR-13 |
| Apply feedback to evaluation | Ensure feedback target exists and run config version is recorded. | actor, feedback_id, evaluation_run_id, label | BR-10 |

## Authorization decision pattern

1. Authenticate or load local profile.
2. Validate role can execute capability.
3. Validate scope: corpus, artifact, session or evaluation run.
4. Validate state guard from `docs/technical/07-state-machines.md`.
5. Execute command inside documented transaction boundary.
6. Write audit/log event for sensitive action.

## BRDS traceability

This file implements FR-10, FR-13, FR-14, BR-10, BR-11, BR-13, NFR-06 and NFR-07.

