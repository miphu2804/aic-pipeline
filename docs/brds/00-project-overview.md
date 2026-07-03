# BRDS 00 - Tổng quan dự án

## Phạm vi

Tài liệu này mô tả yêu cầu nghiệp vụ cho `aic-pipeline` phiên bản pipeline v1, phục vụ bài toán truy xuất multimedia tương tự Video Browser Showdown trong ngữ cảnh HCM AI Challenge 2026.

Pipeline v1 tập trung vào hướng tiếp cận trong sơ đồ tham chiếu: tách `Indexing Phase` và `Searching Phase`, kết hợp text index cho `OCR/ASR` với vector index cho `semantic/color feature`, rồi hợp nhất và rerank kết quả.

## Nguồn và trạng thái bằng chứng

| Nguồn | Quan sát | Trạng thái claim | Ảnh hưởng tài liệu |
|---|---|---|---|
| `docs/aic-knowledge/01-seminar-hcmaic26-detailed.md` | Seminar công bố 4 nhóm task: `Textual KIS`, `Visual KIS`, `VQA`, `TRAKE`; dữ liệu là multimedia tin tức Việt Nam; cần keyframe, OCR, ASR, embedding. | Verified trong repo | BRDS scope, FR, NFR, roadmap |
| `docs/aic-knowledge/reference-flow-ver-1.md` | Sơ đồ IMSearch 2.0 tách text index và vector index, dùng Meilisearch và FAISS ở mức tham chiếu. | Verified trong repo | Module, workflow, state, technical design |
| Ảnh pipeline do người dùng cung cấp | Có `Indexing Phase`, `Searching Phase`, ASR, OCR, color, semantic, combined results, rerank, UI. | Verified từ prompt | Product flow v1 |
| `backend/README.md`, `backend/pyproject.toml` | Backend hiện là Python 3.11.3 với `uv`, dependency runtime chưa có, script `aic-pipeline`. | Verified trong repo | Local setup, runtime boundary |
| `backend/src/aic_pipeline/__init__.py` | Entrypoint hiện chỉ in greeting mẫu. | Verified trong repo | Code implementation chưa có module nghiệp vụ |
| Module pipeline trong tài liệu này | Dataset manifest, keyframe, ASR, OCR, semantic vector, fusion, TRAKE, VQA, UI/evaluation. | Inferred từ seminar và sơ đồ | Requirements và technical design v1 |

## Mục tiêu sản phẩm

Xây dựng pipeline truy xuất multimedia có thể giúp đội thi tìm đúng `VideoId` và `FrameId` hoặc trả lời câu hỏi trong thời gian ngắn, bằng cách tiền xử lý dữ liệu offline thành nhiều index độc lập và cung cấp luồng truy vấn online có hợp nhất bằng chứng.

## Bối cảnh nghiệp vụ

HCM AI Challenge 2026 có định hướng gần với VBS/LSC, nơi người thi cần duyệt và truy xuất thông tin từ kho video lớn trong thời gian giới hạn. Query có thể dựa trên mô tả bằng văn bản, hình ảnh mẫu, câu hỏi về nội dung video, hoặc chuỗi sự kiện cần đúng thứ tự thời gian.

## Mục tiêu nghiệp vụ

| Mục tiêu | Mô tả | Trace |
|---|---|---|
| BO-01 | Giảm không gian tìm kiếm từ video/frame thô xuống keyframe và segment có thể truy vấn nhanh. | FR-01, FR-02, NFR-02 |
| BO-02 | Hỗ trợ nhiều tín hiệu retrieval thay vì phụ thuộc một model embedding duy nhất. | FR-03, FR-04, FR-05, FR-06 |
| BO-03 | Cho phép truy vấn tương tác theo phong cách VBS với bằng chứng rõ ràng. | FR-07, FR-08, FR-09, FR-10 |
| BO-04 | Bao phủ MVP vòng loại gồm `Textual KIS`, `VQA`, `TRAKE`. | FR-10, FR-11, FR-12 |
| BO-05 | Để ngỏ đường nâng cấp cho `Visual KIS` và browser UI vòng chung kết. | FR-15 |

## Mục tiêu vận hành

| Mục tiêu | Mô tả | Trace |
|---|---|---|
| OP-01 | Mỗi artifact index phải tái tạo được từ manifest, cấu hình model và phiên bản pipeline. | BR-11, NFR-01 |
| OP-02 | Mỗi kết quả retrieval phải giữ được nguồn điểm số và bằng chứng. | BR-04, AC-09 |
| OP-03 | Pipeline phải chấp nhận chạy lại từng nhánh ASR/OCR/vector khi nhánh khác lỗi. | BR-12, NFR-09 |
| OP-04 | Tối ưu cho workflow cục bộ trước, chưa bắt buộc microservice hoặc cloud. | NFR-06 |

## Tín hiệu thành công

| Tín hiệu | Kỳ vọng v1 |
|---|---|
| Search correctness | Trên tập kiểm thử nhỏ, query Textual KIS trả về candidate đúng trong top-k có bằng chứng text hoặc visual. |
| Retrieval latency | Search top-k đã index trả kết quả đủ dùng cho thao tác tương tác, mục tiêu p95 dưới 3 giây trên máy local mục tiêu. |
| Evidence quality | Candidate hiển thị `video_id`, `frame_id`, `timestamp_ms`, score từng nhánh, OCR/ASR hit hoặc semantic/color evidence. |
| TRAKE readiness | Query nhiều sự kiện tạo được chuỗi frame đúng thứ tự thời gian hoặc trả lỗi có lý do. |
| VQA readiness | Câu trả lời text có liên kết tới candidate/evidence dùng để suy luận. |

## Ranh giới sản phẩm

### Trong phạm vi v1

- Offline indexing cho manifest video, keyframe, ASR, OCR, semantic vector, color/object attribute ở mức tối thiểu.
- Online retrieval fan-out vào text index và vector index.
- Fusion/rerank deterministic để phục vụ đánh giá.
- API hoặc service contract cho Textual KIS, TRAKE, VQA.
- Ghi nhận feedback/evaluation run để cải thiện trọng số và lỗi truy xuất.

### Ngoài phạm vi v1

- Huấn luyện model SOTA từ đầu.
- Microservice phân tán hoặc cloud deployment bắt buộc.
- Full browser UI hoàn chỉnh như hệ thống thi chính thức.
- Realtime video ingestion.
- Tự động nộp bài vào cổng thi nếu format chưa được ban tổ chức công bố.

### Phạm vi tương lai

- Visual KIS bằng ảnh/clip query.
- Region-level retrieval cho crop nhỏ, chữ nhỏ, thuộc tính fine-grained.
- User feedback rerank học trọng số tự động.
- UI keyboard-first cho vòng chung kết offline.

## Product statement

`aic-pipeline` là pipeline truy xuất multimedia cho HCM AIC 2026, ưu tiên tiền xử lý offline thành nhiều index có thể tái tạo và cung cấp truy vấn online hợp nhất bằng chứng để giải Textual KIS, VQA và TRAKE trước, sau đó mở rộng Visual KIS.

