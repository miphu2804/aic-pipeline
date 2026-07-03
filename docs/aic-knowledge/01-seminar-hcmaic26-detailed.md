# Phân tích chi tiết `Seminar-HCMAIC26.pdf`

## Phạm vi tài liệu

- `[Verified]` Nguồn duy nhất của tài liệu này là `/Users/miphu/Downloads/Seminar-HCMAIC26.pdf`.
- `[Verified]` PDF có `66` trang, tiêu đề `Seminar-HCMAIC26`, được tạo ngày `2026-07-03`.
- `[Verified]` Mọi kết luận bên dưới đều bám theo nội dung PDF; phần nào suy ra thêm sẽ được gắn nhãn `[Inferred]`.

## Tóm tắt điều hành

- `[Verified]` Chủ đề cuộc thi là xây dựng trợ lý ảo thông minh để phân tích và truy xuất thông tin chuyên sâu trong dữ liệu lớn multimedia, gồm hình ảnh, âm thanh và văn bản.
- `[Verified]` Phạm vi dữ liệu là tin tức từ các báo và đài truyền hình tại Việt Nam.
- `[Verified]` Seminar không chỉ giới thiệu đề bài mà còn định hướng tư duy hệ thống: dùng `keyframes` để giảm tải, dùng `embedding` cho semantic retrieval, dùng `OCR/ASR` để giải bài toán text-heavy, và kết hợp nhiều index thay vì một đường truy vấn duy nhất.
- `[Verified]` Seminar tham chiếu trực tiếp các hệ thống retrieval đã thi ở `VBS` và `LSC`, trong đó nổi bật là `IMSearch 2.0` và `VideoEase`.

## 1. Tổng quan cuộc thi

### 1.1 Thông điệp cốt lõi

- `[Verified][PDF tr. 4]` Chủ đề: trợ lý ảo thông minh hỗ trợ phân tích và truy xuất thông tin chuyên sâu trong dữ liệu lớn multimedia.
- `[Verified][PDF tr. 4]` Mục tiêu: xây dựng giải pháp xử lý đồng thời `hình ảnh`, `âm thanh`, `văn bản`.
- `[Verified][PDF tr. 4]` Phạm vi: dữ liệu tin tức từ báo và đài tại Việt Nam.
- `[Verified][PDF tr. 4]` Hình thức thi: cá nhân hoặc đội, tối đa `5` thành viên.

### 1.2 Timeline

- `[Verified][PDF tr. 6]` Hạn đăng ký: đến hết ngày `15/06/2026`.
- `[Verified][PDF tr. 6]` Tập huấn thí sinh dự thi: dự kiến trong `tháng 6-7/2026`.
- `[Verified][PDF tr. 6]` Vòng sơ tuyển hội thi: dự kiến `tháng 8/2026`.
- `[Verified][PDF tr. 6]` Vòng chung kết và tổng kết: dự kiến `tháng 9-10/2026`.

## 2. Bài toán và thể thức thi

### 2.1 Định vị bài toán

- `[Verified][PDF tr. 9]` Seminar nói rõ thể thức thi gần với hai sân chơi lâu năm là `Video Browser Showdown (VBS)` và `Lifelog Search Challenge (LSC)`.
- `[Verified][PDF tr. 8]` Slide "Yêu cầu bài toán" hiển thị một giao diện truy vấn kiểu browser, cho thấy ngữ cảnh của bài toán là tìm kiếm tương tác, không phải chỉ nộp batch offline.

### 2.2 Bốn dạng query chính thức

#### Textual KIS

- `[Verified][PDF tr. 10]` `Know-Item Search (KIS)` dạng textual yêu cầu mô tả sự kiện bằng văn bản rồi tìm đúng video hoặc đoạn video khớp.
- `[Verified][PDF tr. 11]` Ví dụ minh họa là một tin về phóng tàu vũ trụ tư nhân, đầu clip có 4 phi hành gia mặc áo đen, nhiệm vụ nghiên cứu cực quang. Đầu ra là `VideoId` và `FrameId`.
- `[Inferred]` Đây là bài toán retrieval đa tín hiệu, vì mô tả có thể phụ thuộc cả bối cảnh ảnh, nội dung ASR và chữ trên màn hình.

#### Visual KIS

- `[Verified][PDF tr. 10, 12]` `Visual KIS` nhận vào một đoạn video ngắn hoặc một vài frame, đầu ra vẫn là `VideoId` và `FrameId` gốc.
- `[Inferred]` Bài này cần ưu tiên `near-duplicate retrieval`, `embedding similarity`, và định vị shot chính xác hơn là search bằng từ khóa.

#### VQA

- `[Verified][PDF tr. 10, 13]` `Visual Question Answering` nhận vào câu hỏi về nội dung video và trả lời bằng text.
- `[Verified][PDF tr. 13]` Ví dụ seminar nêu câu hỏi đếm số người trên sân khấu ở phân cảnh cuối của bản tin về hát bội.
- `[Inferred]` Retrieval vẫn là bước đầu; sau đó mới tới answer generation hoặc heuristic reasoning.

#### TRAKE

- `[Verified][PDF tr. 10, 14, 15]` `Temporal Retrieval and Alignment of Key Events` yêu cầu tìm một chuỗi frame tương ứng với nhiều khoảnh khắc quan trọng theo đúng thứ tự thời gian.
- `[Verified][PDF tr. 14]` Ví dụ seminar là video nấu ăn, với chuỗi sự kiện: cắt nấm, cắt củ năng, cắt đậu hủ, rồi đặt chảo lên bếp và bật lửa.
- `[Inferred]` Đây là bài toán decomposition: cần tách query thành các sub-events rồi ghép lại theo trật tự thời gian.

### 2.3 Cấu trúc các vòng thi

- `[Verified][PDF tr. 16]` Vòng loại có nhiều vòng online, gồm `Textual KIS`, `VQA`, `TRAKE`, và được đánh giá theo `độ chính xác`.
- `[Verified][PDF tr. 16]` Vòng chung kết offline gồm `Textual KIS`, `Visual KIS`, `VQA`, `TRAKE`, và được đánh giá theo cả `độ chính xác` lẫn `tốc độ tìm kiếm`.
- `[Inferred]` Tốc độ ở vòng chung kết làm cho việc tiền xử lý offline, tổ chức index và UI retrieval trở thành yêu cầu bắt buộc, không phải nice-to-have.

## 3. Dữ liệu cuộc thi

### 3.1 Thành phần dữ liệu

- `[Verified][PDF tr. 18]` Seminar liệt kê 5 nhóm dữ liệu: `Videos`, `Keyframes`, `Objects`, `CLIP Features`, `Metadata (from YouTube)`.

### 3.2 Video corpus

- `[Verified][PDF tr. 19]` Chủ đề video gồm `tin tức`, `nấu ăn`, `dạy học online`, `trình diễn nghệ thuật`.
- `[Verified][PDF tr. 19]` Mỗi video dài từ `30 giây` đến `30 phút`.
- `[Verified][PDF tr. 19]` Bộ dữ liệu 2025 có hơn `1478` video, tổng thời lượng khoảng `300` giờ.

### 3.3 Keyframes

- `[Verified][PDF tr. 21]` Dùng toàn bộ `38 triệu` frame là không cần thiết và gây vấn đề tốc độ.
- `[Verified][PDF tr. 21]` Seminar khẳng định chỉ cần các frame "khác biệt" nhau để truy vấn.
- `[Verified][PDF tr. 21]` Ví dụ minh họa: `7 keyframes` đại diện cho dải frame `11450 -> 11570`, giúp giảm hơn `96%` số lượng frame cần truy vấn.
- `[Inferred]` Đây là quyết định kiến trúc quan trọng nhất cho indexing: mọi bước nặng nên chạy trên keyframe thay vì full-frame.

### 3.4 Object detection

- `[Verified][PDF tr. 22]` Seminar dùng `FasterRCNN + InceptionResNetV2` huấn luyện trên `Open Images V4`.
- `[Verified][PDF tr. 22]` Khả năng phát hiện khoảng `600` loại object.
- `[Inferred]` Object detection hữu ích cho query có người, phương tiện, vật thể sân khấu, đồ nấu ăn, bảng lớp học, đạo cụ biểu diễn.

### 3.5 CLIP features

- `[Verified][PDF tr. 23]` CLIP feature là embedding của keyframes.
- `[Verified][PDF tr. 23]` Slide mô tả embedding như vector nhiều chiều biểu diễn quan hệ ngữ nghĩa.
- `[Verified][PDF tr. 24]` PDF nói rõ CLIP đưa ảnh và text vào một `shared latent space`.
- `[Inferred]` Đây là nền tảng cho `semantic text-to-image retrieval`, đặc biệt quan trọng với `Textual KIS` và `Visual KIS`.

### 3.6 Metadata

- `[Verified][PDF tr. 26]` Metadata lấy từ YouTube và có dạng record chứa ít nhất: `author`, `channel_id`, `channel_url`, `description`, `keywords`, `length`, `publish_date`, `thumbnail_url`, `title`, `watch_url`.
- `[Inferred]` Metadata nên được coi là tín hiệu hỗ trợ, không phải nguồn chính, vì query thường hỏi nội dung frame/segment chứ không chỉ title video.

## 4. Hướng tiếp cận mà seminar gợi ý

### 4.1 Quy trình tư duy

- `[Verified][PDF tr. 28-31, 43, 57, 60]` Seminar lặp lại cùng một khung làm việc:
  - `Problem Understanding`
  - `Exploratory Data Analysis (EDA)`
  - `Survey`
  - `Baseline Selection`
  - `Result Analysis`
  - `Improve Baseline`
- `[Inferred]` Đây là quy trình nên dùng cho dự án này vì repo hiện còn rất sớm, chưa nên nhảy ngay vào tối ưu model.

### 4.2 Quan sát dữ liệu và benchmark

- `[Verified][PDF tr. 32-33]` Seminar có bước phân tích chủ đề video và chỉ ra hiện tượng một số bản tin bị chiếu lại nhiều lần.
- `[Inferred]` Việc lặp bản tin tạo ra rủi ro false positive giữa các video rất giống nhau; cần segment-level metadata hoặc rerank theo timestamp/context.

### 4.3 Survey phương pháp

- `[Verified][PDF tr. 35]` Các nhóm phương pháp được survey gồm `Embedding Based`, `Scene Text Recognition`, `Automatic Speech Recognition`, `Object Detection`, `Sketch-Based Search`.
- `[Verified][PDF tr. 36]` Có tham chiếu `V-FIRST 2.0`.
- `[Verified][PDF tr. 38-39]` Seminar nhắc tới các khả năng mà đội thi khác hỗ trợ: `Text queries`, `Object/Color Filtering`, `Temporal queries`, `Multilingual queries`, `image sub-regions`, `color texture features`.
- `[Verified][PDF tr. 39]` Có tham chiếu `PraK Tool V3`.
- `[Verified][PDF tr. 44-45]` Hai hệ thống được đưa ra làm reference chính là `IMSearch 2.0` và `VideoEase at VBS2025`.

### 4.4 Hướng pipeline offline

- `[Verified][PDF tr. 46-47]` Seminar tách riêng `Offline Process - Keyframes selection`.
- `[Verified][PDF tr. 48]` Bước kế tiếp là `Offline Process - Encoding Embedding`.
- `[Verified][PDF tr. 49-51]` Bước thứ ba là `Offline Process - Indexing`, có thảo luận rõ về `vector database`.
- `[Verified][PDF tr. 53-54]` Với OCR, seminar nêu hai hướng:
  - `Embedding based (SBERT, ...)`
  - `Text based`
- `[Verified][PDF tr. 54]` Slide text-based hiển thị ví dụ `MongoDB` và `Elasticsearch`.

### 4.5 Kiến trúc retrieval tham chiếu

- `[Verified][PDF tr. 44]` Sơ đồ `IMSearch 2.0` là nguồn tham chiếu trực tiếp cho `docs/reference-flow-ver-1.md`.
- `[Verified][PDF tr. 45]` `VideoEase` dùng `keyframe images`, `image embeddings`, metadata (`objects`, `OCR`, `colours`) và một tầng `filtering/ranking` phía sau `Milvus`.
- `[Inferred]` Hai slide này cho thấy seminar nghiêng về kiến trúc `multi-index`, không phải một embedding store duy nhất.

### 4.6 Các failure cases seminar nhấn mạnh

- `[Verified][PDF tr. 58]` Ví dụ khó: nhận biết một bức tranh có chữ `Lộc` trong bối cảnh người đàn ông đang vẽ tranh cát. Đây là case khó về `small OCR / fine-grained text localization`.
- `[Verified][PDF tr. 59]` Ví dụ khó khác: phân biệt người áo vàng viền đen đang trả lời phỏng vấn với một người áo tương tự ở phía sau đang đóng gói thực phẩm màu đỏ sẫm cam. Đây là case khó về `fine-grained visual attributes`.
- `[Inferred]` Hai case này là bằng chứng mạnh rằng semantic embedding thuần sẽ không đủ; phải có `OCR`, `color`, `region-level cues`, hoặc rerank chi tiết.

### 4.7 Thử nghiệm mô hình

- `[Verified][PDF tr. 61-62]` Seminar kết bằng nhóm thử nghiệm `SOTA models` cho `Embedding`, `Automatic Speech Recognition`, `Optical Character Recognition`, `Object Detection`.
- `[Verified]` PDF không chốt một model bắt buộc cho từng nhóm ngoài các ví dụ tham chiếu trong slide kiến trúc.

## 5. Điều seminar nói rõ và điều seminar chưa chốt

### Seminar nói rõ

- `[Verified]` Task taxonomy chính thức.
- `[Verified]` Round format và tiêu chí chấm ở mức cao.
- `[Verified]` Dạng dữ liệu đầu vào và nhu cầu giảm tải bằng keyframes.
- `[Verified]` Hướng kiến trúc retrieval nhiều tầng, kết hợp text index và vector index.

### Seminar chưa chốt

- `[Verified]` Không có công thức metric chi tiết cho từng task trong PDF.
- `[Verified]` Không có public leaderboard hoặc baseline score trong PDF.
- `[Verified]` Không có yêu cầu bắt buộc phải dùng model, DB, framework cụ thể nào.
- `[Verified]` Không có đặc tả API, schema submission hay format package giao bài trong PDF.

## 6. Kết luận áp vào dự án

- `[Inferred]` Muốn bám sát seminar, dự án không nên mở đầu bằng chat assistant tổng quát, mà nên xây trước `retrieval core`.
- `[Inferred]` Thứ tự hợp lý là:
  1. keyframe pipeline;
  2. CLIP/semantic vector index;
  3. OCR + text index;
  4. ASR + transcript index;
  5. rerank và temporal grouping;
  6. VQA/TRAKE orchestration.
- `[Inferred]` `Visual KIS` có thể lùi sau `Textual KIS` trong roadmap triển khai vì không xuất hiện ở vòng loại.
