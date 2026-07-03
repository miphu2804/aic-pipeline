# Ghi chú kiến trúc cho `aic-pipeline`

## Mục tiêu tài liệu

- `[Verified]` Tài liệu này bám theo seminar và `docs/reference-flow-ver-1.md`.
- `[Inferred]` Mục đích là biến kiến trúc tham chiếu thành lộ trình triển khai thực dụng cho repo hiện tại, không thiết kế thừa ngay nhiều tầng chưa cần thiết.

## 1. Điều nên xem là MVP của dự án

### MVP vòng loại

- `[Verified]` Vòng loại chỉ cần `Textual KIS`, `VQA`, `TRAKE`.
- `[Inferred]` MVP hợp lý cho repo là:
  - index keyframe;
  - semantic retrieval cho text-to-frame;
  - OCR text search;
  - ASR transcript search;
  - temporal grouping đủ dùng cho TRAKE;
  - tầng answer đơn giản cho VQA.

### Phase sau MVP

- `[Verified]` `Visual KIS` chỉ có ở vòng chung kết.
- `[Inferred]` Có thể đưa `Visual KIS`, fine-grained rerank, user-feedback loop và UI browser tương tác sang phase 2.

## 2. Các slice triển khai nên tách

| Slice | Trạng thái | Kết quả đầu ra mong muốn |
| --- | --- | --- |
| Dataset manifest | `[Inferred]` | danh mục video, metadata, đường dẫn raw asset |
| Keyframe pipeline | `[Inferred]` | keyframe images + map về video/frame/time |
| Semantic index | `[Inferred]` | embedding của keyframes + index FAISS |
| OCR pipeline | `[Inferred]` | text OCR theo keyframe + text index |
| ASR pipeline | `[Inferred]` | transcript theo segment + text index |
| Retrieval fan-out | `[Inferred]` | truy vấn vào nhiều index rồi hợp nhất |
| Temporal grouping | `[Inferred]` | ghép frame thành sequence cho TRAKE |
| VQA answer layer | `[Inferred]` | trả lời text trên top-k candidate |

## 3. Tối thiểu cần lưu cho mỗi keyframe

- `[Inferred]` `video_id`
- `[Inferred]` `frame_id`
- `[Inferred]` `timestamp_ms`
- `[Inferred]` `keyframe_path`
- `[Inferred]` `clip_embedding`
- `[Inferred]` `ocr_text`
- `[Inferred]` `asr_window_id` hoặc link tới segment transcript gần nhất
- `[Inferred]` `dominant_colors`
- `[Inferred]` `detected_objects`
- `[Inferred]` `source_metadata_ref`

## 4. Luồng truy vấn nên bám theo task

### Textual KIS

- `[Inferred]` Query text đi vào semantic encoder.
- `[Inferred]` Đồng thời query text nên đi qua nhánh text matching cho OCR/ASR nếu có từ khóa rõ ràng.
- `[Inferred]` Kết quả hợp nhất cần rerank theo:
  - mức khớp semantic;
  - exact text hit;
  - temporal proximity;
  - metadata consistency.

### VQA

- `[Inferred]` Bước 1: retrieve candidate frame hoặc segment.
- `[Inferred]` Bước 2: extract evidence từ OCR/object/ASR.
- `[Inferred]` Bước 3: sinh câu trả lời ngắn.
- `[Inferred]` Nếu câu hỏi có từ khóa thời gian như "cuối cùng", "đầu tiên", "sau đó", cần filter theo vị trí trong video trước khi answer.

### TRAKE

- `[Inferred]` Tách query thành nhiều sub-event.
- `[Inferred]` Tìm top-k cho từng sub-event.
- `[Inferred]` Chọn chuỗi candidate tôn trọng thứ tự thời gian và khoảng cách hợp lý.

### Visual KIS

- `[Inferred]` Encode query image/clip bằng cùng embedding model với keyframes.
- `[Inferred]` Sau vector search nên mở rộng ra lân cận temporal để tìm frame đúng nhất nếu query nằm giữa hai keyframe.

## 5. Các quyết định công nghệ ở mức v1

- `[Verified]` Sơ đồ IMSearch dùng `Meilisearch` cho transcript/OCR text và `FAISS` cho semantic/color feature.
- `[Verified]` Slide OCR text-based cũng nhắc `MongoDB` và `Elasticsearch` như lựa chọn lưu text.
- `[Inferred]` Với repo này, bản v1 nên ưu tiên:
  - `FAISS` cho vector search vì đơn giản, nhẹ, phù hợp giai đoạn đầu;
  - một text index riêng cho `OCR` và `ASR`;
  - metadata lưu cùng manifest thay vì dựng ngay một service riêng.
- `[Inferred]` Chỉ nên đưa vector DB hoặc search cluster đầy đủ khi dữ liệu và UI tương tác chứng minh cần thêm scale hoặc filtering phức tạp.

## 6. Rủi ro kỹ thuật cần chặn sớm

- `[Verified]` Duplicate news segments làm kết quả retrieval dễ lẫn giữa nhiều video gần như giống nhau.
- `[Verified]` OCR nhỏ hoặc bị che khuất sẽ làm text branch yếu nếu không có detector tốt.
- `[Verified]` Fine-grained attributes khó cho embedding chung.
- `[Inferred]` Nếu chỉ index top-level frame embedding mà không lưu text/object/color phụ trợ, chất lượng cho KIS và TRAKE sẽ tụt mạnh.

## 7. Backlog rất ngắn nhưng đúng trọng tâm

1. `[Inferred]` Dựng manifest video + metadata.
2. `[Inferred]` Dựng pipeline keyframe và bảng map `video/frame/timestamp`.
3. `[Inferred]` Sinh semantic embedding và FAISS index.
4. `[Inferred]` Sinh OCR/ASR và text index.
5. `[Inferred]` Tạo retrieval API tối thiểu cho `Textual KIS`.
6. `[Inferred]` Thêm temporal grouping cho `TRAKE`.
7. `[Inferred]` Thêm answer layer cho `VQA`.
8. `[Inferred]` Mở rộng `Visual KIS`.
