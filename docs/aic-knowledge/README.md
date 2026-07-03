# Knowledge Base cho `aic-pipeline`

Kho này gom phần tri thức nền cho dự án truy xuất multimedia phục vụ HCM AI Challenge 2026. Mục tiêu là tách rõ:

- những gì seminar nói chính thức;
- những gì có thể suy ra để dự đoán dạng đề bài;
- kiến trúc tham chiếu nên bám khi triển khai hệ thống trong repo này.

## Quy ước độ tin cậy

- `[Verified]`: xác nhận trực tiếp từ PDF seminar hoặc từ sơ đồ tham chiếu trong slide.
- `[Inferred]`: suy luận phục vụ thiết kế hệ thống hoặc dự đoán đề bài, không phải công bố chính thức của ban tổ chức.

## Nguồn chính

- `[Verified]` `/Users/miphu/Downloads/Seminar-HCMAIC26.pdf` (66 trang).
- `[Verified]` Sơ đồ IMSearch 2.0 trong seminar, trang PDF 44.
- `[Verified]` Tài liệu tham chiếu kiến trúc trong repo: `docs/reference-flow-ver-1.md`.

## Thứ tự đọc đề xuất

1. `01-seminar-hcmaic26-detailed.md`
2. `02-competition-query-catalog.md`
3. `03-aic-pipeline-architecture-notes.md`
4. `reference-flow-ver-1.md`

## 5 ý quan trọng nhất

- `[Verified]` Cuộc thi xoay quanh trợ lý ảo truy xuất thông tin chuyên sâu trên dữ liệu multimedia tin tức Việt Nam.
- `[Verified]` Bốn nhóm bài toán chính là `Textual KIS`, `Visual KIS`, `VQA`, `TRAKE`.
- `[Verified]` Dataset năm 2025 gồm hơn `1478` video, tổng thời lượng khoảng `300` giờ, với các chủ đề chính: tin tức, nấu ăn, dạy học online, trình diễn nghệ thuật.
- `[Verified]` Seminar nhấn mạnh phải giảm không gian truy vấn bằng `keyframes`, kết hợp `CLIP embedding`, `OCR`, `ASR`, `metadata`.
- `[Inferred]` Nếu chỉ muốn tối ưu theo lộ trình thi, nên ưu tiên `Textual KIS -> VQA/TRAKE -> Visual KIS`, vì `Visual KIS` chỉ xuất hiện ở vòng chung kết.
