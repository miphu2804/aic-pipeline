# BRDS 07 - Non-functional requirements và risk

## Non-functional requirements

| ID | Nhóm | Requirement | Target hoặc acceptance signal | Trace |
|---|---|---|---|---|
| NFR-01 | Reproducibility | Mỗi index/evaluation run phải tái tạo được từ corpus version, config version và artifact manifest. | Có lineage report cho artifact active. | FR-01, FR-13, FR-14 |
| NFR-02 | Performance | Query online trên artifact active phải đủ nhanh cho tương tác. | Mục tiêu p95 dưới 3 giây cho top-k trên máy local mục tiêu, khi index đã build. | FR-08, FR-09 |
| NFR-03 | Evidence quality | Candidate user-facing phải có bằng chứng đủ đọc và score breakdown. | Candidate thiếu evidence bị cảnh báo hoặc hạ rank. | FR-09, FR-10, FR-12 |
| NFR-04 | Scale | Thiết kế phải phù hợp corpus cỡ hàng nghìn video và hàng trăm giờ nội dung. | Keyframe và index artifact không phụ thuộc scan full-frame online. | FR-02, FR-05 |
| NFR-05 | Operability | Lỗi pipeline phải có code, branch, artifact id và remediation hint. | Log structured cho indexing và query. | FR-14 |
| NFR-06 | Maintainability | Module v1 phải tách theo capability, không tạo microservice sớm khi chưa cần. | Một backend/local runtime có contract rõ là đủ cho MVP. | FR-14 |
| NFR-07 | Data safety | Raw media path và dữ liệu nội bộ không leak ra response/export ngoài phạm vi cần thiết. | API/UI chỉ trả locator và safe reference. | BR-13 |
| NFR-08 | Usability | Workflow query/review phải hỗ trợ thao tác nhanh kiểu thi VBS. | Candidate có preview/evidence và submission draft ít bước. | FR-10, FR-15 |
| NFR-09 | Fault tolerance | Lỗi một branch không làm mất artifact active cũ và có thể cho kết quả degraded nếu còn branch usable. | Query trả warning thay vì fail toàn bộ khi policy cho phép. | FR-03..FR-08 |
| NFR-10 | Testability | Mọi rule và AC có scenario test hoặc checklist kiểm chứng. | `docs/technical/11-testing-plan.md` map đủ AC. | AC-01..AC-15 |

## Risk matrix

| Risk | Impact | Likelihood | Mitigation | Owner/Trigger |
|---|---|---|---|---|
| R-01 Duplicate/rebroadcast news làm candidate sai video | Cao | Cao | Dedup mềm, hiển thị alternative candidates, dùng timestamp/OCR/metadata để phân biệt. | Retrieval/Fusion, BR-06 |
| R-02 OCR chữ nhỏ hoặc vùng phụ bị miss | Cao | Cao | Lưu bbox/confidence, hỗ trợ rerank/crop future, không phụ thuộc semantic thuần. | OCR, NFR-03 |
| R-03 ASR sai với audio nhiễu hoặc nhiều người nói | Trung bình | Trung bình | Giữ confidence, cho exact/fuzzy text matching, kết hợp semantic/OCR. | ASR |
| R-04 Fine-grained visual attributes không được embedding chung bắt tốt | Cao | Cao | Thêm color/object branch và evidence rerank. | Signal Extraction, FR-06 |
| R-05 FAISS local không đủ filter phức tạp | Trung bình | Trung bình | Giữ abstraction artifact/index; nâng vector DB khi có nhu cầu rõ. | Maintainer |
| R-06 Query TRAKE tách event sai | Cao | Trung bình | Cho phép decomposition transparent, hiển thị sub-event evidence, benchmark riêng. | TRAKE |
| R-07 VQA answer hallucination | Cao | Trung bình | Evidence-first, trả `INSUFFICIENT_EVIDENCE` khi không đủ căn cứ. | VQA, BR-09 |
| R-08 Scope creep sang UI/microservice quá sớm | Trung bình | Cao | Giữ MVP retrieval core trước, UI nâng sau khi API/evidence ổn. | Maintainer |
| R-09 Competition format thay đổi | Cao | Trung bình | Giữ output adapter tách riêng và cập nhật khi có schema chính thức. | Maintainer |

## Risk monitoring notes

- Theo dõi top failure categories sau mỗi evaluation run: `text_miss`, `visual_miss`, `duplicate_confusion`, `temporal_order_fail`, `vqa_unsupported`.
- Với mỗi branch index, log coverage: số video thành công, số keyframe/segment có evidence, tỷ lệ record rỗng.
- Không nâng cấp stack vì giả định scale; chỉ nâng khi metric hoặc workflow chứng minh bottleneck.

