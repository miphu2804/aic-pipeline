# BRDS 01 - Stakeholders và phạm vi

## Stakeholder matrix

| Stakeholder | Mục tiêu | Trách nhiệm | Tín hiệu thành công |
|---|---|---|---|
| Thí sinh/đội thi | Tìm đúng video/frame hoặc câu trả lời nhanh trong phiên thi. | Cấu hình query, duyệt candidate, chọn submission. | Nhiều query đúng trong top-k, ít thao tác thừa. |
| Người vận hành pipeline | Chuẩn bị dữ liệu và index trước phiên thi. | Import manifest, chạy indexing, kiểm tra artifact. | Index hoàn tất, có log lỗi rõ, có thể rerun nhánh lỗi. |
| Người đánh giá nội bộ | Đo chất lượng retrieval trên query mẫu. | Tạo query set, chấm relevance, phân tích failure. | Có report top-k, latency, failure categories. |
| Maintainer dự án | Giữ codebase đơn giản, có module rõ, có test. | Bảo trì contracts, schema, local setup. | Thêm module mới không phá traceability và pipeline cũ. |
| Hệ thống tự động | Chạy job offline/online theo cấu hình. | Validate input, ghi log, bảo toàn artifact. | Job deterministic, lỗi có code, không làm hỏng artifact cũ. |

## Actor matrix

| Actor | Năng lực | Ràng buộc | Dữ liệu chạm tới | Trace |
|---|---|---|---|---|
| `CompetitorUser` | Gửi query, duyệt kết quả, gửi feedback, tạo submission nội bộ. | Chỉ thao tác trên session của đội. | Query, candidate, feedback, submission draft. | FR-07, FR-10, FR-11, FR-12 |
| `PipelineOperator` | Import dataset, chạy index, kiểm tra index health. | Không sửa raw media ngoài manifest. | Video manifest, index run, artifact. | FR-01..FR-06, FR-14 |
| `Evaluator` | Chạy benchmark, nhập ground truth hoặc label relevance. | Không thay đổi raw index. | Query set, evaluation run, relevance label. | FR-13 |
| `Maintainer` | Cấu hình model/index, migration, schema. | Mọi thay đổi phải giữ version và rollback artifact. | Config, schema, pipeline version. | FR-14, NFR-06 |
| `SystemJob` | Thực thi indexing/retrieval async. | Chạy theo config đã validate. | Artifact, logs, metrics. | FR-02..FR-09 |

## In-scope MVP

| Phạm vi | Mô tả | Trace |
|---|---|---|
| Dataset manifest | Khai báo video, metadata, đường dẫn asset, checksum tùy chọn. | FR-01, AC-01 |
| Keyframe map | Sinh hoặc import keyframe với map `video_id/frame_id/timestamp_ms`. | FR-02, AC-02 |
| Text evidence | ASR transcript và OCR text có thể search độc lập. | FR-03, FR-04, AC-03, AC-04 |
| Vector evidence | Semantic embedding và color/object feature có thể search/filter. | FR-05, FR-06, AC-05, AC-06 |
| Retrieval fan-out | Một query có thể chạy song song qua nhiều index. | FR-08, AC-08 |
| Fusion/rerank | Hợp nhất score theo công thức versioned và giải thích được. | FR-09, AC-09 |
| Textual KIS | Trả candidate `VideoId`, `FrameId` và bằng chứng. | FR-10, AC-10 |
| TRAKE | Tách sự kiện, retrieve từng event, chọn chuỗi theo thứ tự thời gian. | FR-11, AC-11 |
| VQA | Retrieve-first, trả answer text kèm evidence. | FR-12, AC-12 |
| Evaluation loop | Ghi feedback, benchmark query set, báo cáo lỗi. | FR-13, AC-13 |

## Out-of-scope MVP

- Huấn luyện ASR/OCR/embedding model từ đầu.
- UI thi đấu đầy đủ với mọi thao tác như VBS chính thức.
- Multi-tenant authentication phức tạp.
- Distributed queue, autoscaling, cloud object storage bắt buộc.
- Tự động suy luận đáp án VQA không cần evidence.
- Query bằng video clip/crop trong MVP nếu chưa cần cho vòng loại.

## Future scope

| Phạm vi tương lai | Lý do | Trace |
|---|---|---|
| Visual KIS | Có thể xuất hiện ở vòng chung kết, cần image/clip query. | FR-15, AC-15 |
| Region-level rerank | Chặn lỗi chữ nhỏ, crop nhỏ, thuộc tính fine-grained. | NFR-03, R-04 |
| Interactive browser UI | Cải thiện tốc độ thao tác khi thi offline. | NFR-08 |
| Learning-to-rank từ feedback | Tối ưu fusion/rerank sau khi có label đủ lớn. | FR-13 |
| Vector DB nâng cao | Khi FAISS local không đủ filtering/scale. | NFR-04 |

## Ranh giới tích hợp

| Chủ đề | Quyết định v1 |
|---|---|
| Model providers | Thiết kế theo adapter, nhưng v1 chỉ cần một cấu hình model active cho mỗi nhánh. |
| Text index | Yêu cầu index riêng cho OCR/ASR; Meilisearch là lựa chọn tham chiếu từ sơ đồ, chưa phải dependency đã cài. |
| Vector index | FAISS là lựa chọn tham chiếu v1; artifact phải có manifest/version. |
| Metadata | Lưu cùng manifest và metadata store nội bộ, chưa cần service riêng. |
| Dữ liệu thô | Raw media là input bất biến; pipeline chỉ ghi artifact dẫn xuất. |
| Quyền thao tác | V1 có thể dùng role nội bộ qua config/session, chưa cần SSO. |

