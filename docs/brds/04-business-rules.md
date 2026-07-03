# BRDS 04 - Business rules

## Evaluation order

Khi nhiều rule cùng áp dụng, hệ thống xử lý theo thứ tự:

1. Validate identity và scope dữ liệu: BR-02, BR-11.
2. Validate task/query/output contract: BR-07.
3. Validate index availability và branch eligibility: BR-03, BR-12.
4. Execute retrieval/fusion với evidence preservation: BR-04, BR-05, BR-06.
5. Apply task-specific guard: BR-08 cho TRAKE, BR-09 cho VQA.
6. Record feedback/evaluation không làm thay đổi raw artifact: BR-10.

## Rule catalog

| Rule ID | Applies When | Condition | Decision | Rejection/Reason Code | State/Data Impact | Traces |
|---|---|---|---|---|---|---|
| BR-01 | Keyframe preparation | Mọi retrieval frame-level phải dùng keyframe hoặc neighborhood map, không scan full-frame thô trong online query. | Chỉ index/search đơn vị keyframe v1. | `KEYFRAME_MAP_REQUIRED` | `Keyframe` là đơn vị chính. | FR-02, AC-02 |
| BR-02 | Manifest, candidate, submission | Mọi record có thể submit phải resolve được `video_id`, `frame_id`, `timestamp_ms`. | Reject record/candidate thiếu locator. | `CANONICAL_LOCATOR_MISSING` | Bảo toàn output KIS. | FR-01, FR-02, FR-10 |
| BR-03 | Indexing và retrieval | OCR/ASR text index và semantic/color vector index là tín hiệu hạng nhất, không được merge mất source. | Lưu branch source riêng. | `INDEX_BRANCH_UNAVAILABLE` | `CandidateHit` giữ `source_branch`. | FR-03..FR-08 |
| BR-04 | Fusion | Mọi hit trước khi combine phải giữ score gốc, rank gốc và evidence. | Fusion chỉ thêm score tổng, không xóa evidence. | `EVIDENCE_MISSING` | `RankedCandidate` có score breakdown. | FR-08, FR-09 |
| BR-05 | Rerank | Với cùng input và config version, fusion/rerank phải deterministic. | Score tổng dùng config versioned. | `FUSION_CONFIG_INVALID` | Evaluation reproducible. | FR-09, FR-13 |
| BR-06 | Duplicate/rebroadcast handling | Nhiều video hoặc frame gần giống nhau có thể xuất hiện. | Deduplicate mềm nhưng vẫn giữ alternative candidates. | `DUPLICATE_GROUP_AMBIGUOUS` | Candidate có duplicate group. | FR-09 |
| BR-07 | Query intake | Task type quyết định input hợp lệ và output kỳ vọng. | Reject query không khớp task contract. | `TASK_CONTRACT_INVALID` | `QuerySession` `REJECTED`. | FR-07, FR-10..FR-15 |
| BR-08 | TRAKE | Chuỗi TRAKE phải giữ thứ tự temporal đã mô tả. | Chỉ accept sequence tăng theo timestamp trong scope video/segment hợp lệ. | `TRAKE_ORDER_NOT_FOUND` | `TemporalSequence` có guard result. | FR-11 |
| BR-09 | VQA | Answer phải dựa trên evidence từ candidate hoặc text/object evidence đã retrieve. | Không sinh answer khi evidence không đủ. | `INSUFFICIENT_EVIDENCE` | `Answer` `UNANSWERED`. | FR-12 |
| BR-10 | Feedback | Feedback/evaluation không được mutate raw index hoặc raw media. | Ghi feedback record riêng, chỉ dùng trong run/config sau. | `FEEDBACK_TARGET_INVALID` | Tách `FeedbackRecord` khỏi artifact. | FR-13 |
| BR-11 | Artifact version | Artifact index phải có manifest, model/config version, schema version. | Reject artifact thiếu hoặc mismatch. | `INDEX_VERSION_MISMATCH` | Artifact không được active nếu invalid. | FR-01..FR-06, FR-14 |
| BR-12 | Offline/online separation | Online query chỉ dùng artifact active; indexing chạy offline và publish atomically. | Không đọc artifact đang `BUILDING`. | `ARTIFACT_NOT_ACTIVE` | `ACTIVE` artifact cũ còn dùng được. | FR-03..FR-08, FR-14 |
| BR-13 | Dataset locality | Raw media và private dataset path không được leak vào response người dùng nếu không cần. | Response chỉ trả locator và safe path/reference nội bộ. | `DATA_PATH_NOT_EXPORTABLE` | Giảm rủi ro lộ dữ liệu. | FR-10, FR-14 |
| BR-14 | Evidence-first UX | Mọi kết quả user-facing phải ưu tiên bằng chứng hơn mô tả chung chung. | Candidate thiếu evidence bị hạ rank hoặc cảnh báo. | `LOW_EVIDENCE_CANDIDATE` | UI/API hiển thị evidence summary. | FR-09, FR-10, FR-12 |

## Reason code policy

- Reason code phải ổn định để test và logging có thể assert.
- Reason code nghiệp vụ nằm trong BRDS; mapping HTTP/exception nằm trong technical design.
- Nếu một operation fail nhiều rule, trả rule đầu tiên theo evaluation order, kèm danh sách warning không chặn nếu có.

