# Catalog các dạng đề bài có thể ra

## Mục đích

- `[Verified]` Seminar chỉ công bố chính thức 4 nhóm task: `Textual KIS`, `Visual KIS`, `VQA`, `TRAKE`.
- `[Inferred]` Tài liệu này mở rộng từ 4 nhóm đó để liệt kê các họ đề bài nhiều khả năng xuất hiện, dựa trên domain dữ liệu và các failure case seminar đã nhấn mạnh.

## 1. Khung chính thức

| Task chính thức | Trạng thái | Đầu ra |
| --- | --- | --- |
| Textual KIS | `[Verified]` | `VideoId`, `FrameId` |
| Visual KIS | `[Verified]` | `VideoId`, `FrameId` |
| VQA | `[Verified]` | Chuỗi text trả lời |
| TRAKE | `[Verified]` | Chuỗi frame theo thứ tự thời gian |

## 2. Các họ đề bài nhiều khả năng xuất hiện

### 2.1 Textual KIS

| Họ đề bài | Độ tin cậy | Tín hiệu chính nên dùng | Vì sao có khả năng cao |
| --- | --- | --- | --- |
| Tìm cảnh theo mô tả tổng quát của sự kiện | `[Inferred]` | CLIP/semantic embedding + metadata | Đúng với định nghĩa KIS textual trong seminar |
| Tìm cảnh có người/vật thể/hành động đặc thù | `[Inferred]` | Object detection + semantic retrieval | Dataset có tin tức, nấu ăn, biểu diễn |
| Tìm cảnh dựa trên chữ trên màn hình | `[Inferred]` | OCR + text index + region rerank | Seminar nêu rõ OCR là một nhánh độc lập và có case chữ `Lộc` rất khó |
| Tìm cảnh dựa trên lời thoại/phát thanh | `[Inferred]` | ASR + transcript index | Sơ đồ IMSearch có hẳn nhánh audio/ASR |
| Tìm cảnh bằng màu sắc, trang phục, chi tiết fine-grained | `[Inferred]` | Dominant color + semantic rerank + crop-level cues | Seminar cho ví dụ áo vàng viền đen và thực phẩm màu đỏ sẫm |
| Tìm giữa các video gần giống nhau | `[Inferred]` | timestamp, show title, OCR lower-third, segment grouping | Seminar có cảnh báo bản tin phát lại nhiều lần |

### 2.2 Visual KIS

| Họ đề bài | Độ tin cậy | Tín hiệu chính nên dùng | Ghi chú |
| --- | --- | --- | --- |
| Tìm đúng frame gốc từ một frame mẫu | `[Inferred]` | image embedding similarity | case chuẩn của visual search |
| Tìm đoạn gốc từ clip con ngắn | `[Inferred]` | shot-level embedding + temporal locality | cần map clip sang segment/video |
| Tìm theo crop hoặc vùng ảnh nhỏ | `[Inferred]` | local features / OCR vùng / object regions | seminar survey nhắc `image sub-regions` |
| Tìm frame cùng cảnh nhưng khác thời điểm rất gần | `[Inferred]` | keyframe neighborhood expansion | tránh miss vì keyframe sampling |

### 2.3 VQA

| Họ đề bài | Độ tin cậy | Tín hiệu chính nên dùng | Ghi chú |
| --- | --- | --- | --- |
| Đếm số người/vật trong cảnh cụ thể | `[Inferred]` | object detection + scene localization | ví dụ chính thức của seminar là đếm người trên sân khấu |
| Đọc chữ hoặc biển/bảng để trả lời | `[Inferred]` | OCR + answer extraction | phù hợp dữ liệu tin tức và dạy học |
| Hỏi thuộc tính trực quan | `[Inferred]` | semantic retrieval + attribute rerank | áo màu gì, vật nào xuất hiện, ai đứng ở đâu |
| Hỏi ở phân cảnh cuối/đầu | `[Inferred]` | retrieval + temporal slicing | seminar ví dụ "phân cảnh cuối cùng" |

### 2.4 TRAKE

| Họ đề bài | Độ tin cậy | Tín hiệu chính nên dùng | Ghi chú |
| --- | --- | --- | --- |
| Chuỗi bước nấu ăn | `[Inferred]` | action/event retrieval + temporal ordering | ví dụ chính thức của seminar |
| Chuỗi thao tác trong dạy học hoặc biểu diễn | `[Inferred]` | semantic sub-event search | hợp với domain online teaching / performing arts |
| Chuỗi diễn biến trong bản tin hiện trường | `[Inferred]` | ASR + semantic + shot boundaries | cần gắn mốc theo narrative |

## 3. Ma trận theo domain dữ liệu

| Domain | Dạng đề dễ xuất hiện | Tín hiệu retrieval quan trọng |
| --- | --- | --- |
| Tin tức | anchor, lower-third, hiện trường, người phát biểu, biển bảng, xe cộ, địa điểm | OCR, ASR, object detection, semantic |
| Nấu ăn | nguyên liệu, thao tác cắt/xào/nêm, dụng cụ bếp, thứ tự bước | semantic, object, temporal alignment |
| Dạy học online | giáo viên, slide, bảng, text trên màn hình | OCR, semantic, metadata |
| Trình diễn nghệ thuật | sân khấu, diễn viên, trang phục, đạo cụ, khán giả | semantic, color, object detection |

## 4. Bẫy đề bài seminar đã chỉ ra

- `[Verified]` Bản tin có thể bị chiếu lại nhiều lần.
- `[Verified]` OCR nhỏ hoặc nằm trong vùng phụ của frame có thể làm semantic retrieval thất bại.
- `[Verified]` Thuộc tính tinh như màu áo, viền cổ áo, món hàng ở nền sau có thể khiến model chung không đủ tốt.
- `[Inferred]` Query dạng nhiều điều kiện nối với nhau sẽ cần `fan-out` qua nhiều index rồi hợp nhất kết quả thay vì chỉ search một nơi.

## 5. Checklist tín hiệu theo task

| Task | Tín hiệu ưu tiên 1 | Tín hiệu ưu tiên 2 | Tín hiệu ưu tiên 3 |
| --- | --- | --- | --- |
| Textual KIS | semantic embedding | OCR/ASR text matching | color/object rerank |
| Visual KIS | image embedding | local region/object match | temporal neighborhood |
| VQA | candidate retrieval | OCR/object reasoning | answer synthesis |
| TRAKE | sub-event retrieval | temporal ordering | consistency rerank |

## 6. Ưu tiên thực thi cho dự án

- `[Verified]` Vòng loại không có `Visual KIS`.
- `[Inferred]` Nếu cần tối ưu theo giá trị sớm, nên tập trung:
  1. `Textual KIS`
  2. `TRAKE`
  3. `VQA`
  4. `Visual KIS`
- `[Inferred]` `Textual KIS` là nền móng tốt nhất vì nó buộc dự án phải dựng hầu hết các index cốt lõi: semantic, OCR, ASR, metadata.
