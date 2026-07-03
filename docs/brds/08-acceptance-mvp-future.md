# BRDS 08 - Acceptance, MVP, future scope

## Acceptance criteria

| AC ID | Module | Observable outcome | Negative paths | Traces |
|---|---|---|---|---|
| AC-01 | Dataset & Asset Catalog | Import manifest hợp lệ tạo `CorpusManifest READY` với video count và metadata summary. | Manifest thiếu `video_id`, path sai hoặc ID trùng bị reject với dòng lỗi. | FR-01, BR-02 |
| AC-02 | Dataset & Asset Catalog | Keyframe catalog có `keyframe_id`, `video_id`, `frame_id`, `timestamp_ms`, `path` và map được về video. | Keyframe thiếu locator hoặc timestamp ngoài duration bị reject. | FR-02, BR-01, BR-02 |
| AC-03 | ASR Indexing | Transcript segment search được bằng keyword và trả evidence gắn `video_id/time range`. | Audio lỗi hoặc transcript rỗng không publish artifact active. | FR-03, BR-03, BR-11 |
| AC-04 | OCR Indexing | OCR search trả text hit, bbox/confidence và keyframe locator. | OCR output không map keyframe bị reject khỏi index. | FR-04, BR-03, BR-11 |
| AC-05 | Semantic Vector Index | Text query semantic trả nearest keyframes với vector score và model version. | Vector dimension mismatch không được active artifact. | FR-05, BR-03, BR-11 |
| AC-06 | Color/Object Attribute | Query/filter màu hoặc object có thể ảnh hưởng rerank và hiển thị evidence. | Attribute confidence thấp được đánh dấu warning hoặc không dùng làm hard filter. | FR-06, BR-14 |
| AC-07 | Query Understanding | Query hợp lệ tạo retrieval plan theo task type và selected branches. | Query rỗng, task type sai, filter sai schema bị reject trước retrieval. | FR-07, BR-07 |
| AC-08 | Multi-index Retrieval | Một query fan-out qua các branch active, trả raw hit count và latency từng branch. | Index unavailable trả branch warning hoặc fail theo policy. | FR-08, BR-03, BR-12 |
| AC-09 | Fusion/Rerank | Ranked candidate có locator, fusion score, score breakdown và evidence refs. | Candidate thiếu locator/evidence không được xuất như result bình thường. | FR-09, BR-04, BR-05 |
| AC-10 | Textual KIS | User có thể chọn candidate và tạo output `VideoId`, `FrameId` từ ranked result. | Candidate thiếu locator hoặc session invalid không export được. | FR-10, BR-02 |
| AC-11 | TRAKE | Query nhiều event trả sequence có event order, locator từng event và evidence. | Không có chuỗi temporal hợp lệ trả reason `TRAKE_ORDER_NOT_FOUND`. | FR-11, BR-08 |
| AC-12 | VQA | Câu trả lời text có evidence refs và confidence. | Evidence thiếu trả `INSUFFICIENT_EVIDENCE` thay vì answer bịa. | FR-12, BR-09 |
| AC-13 | Evaluation Loop | Evaluation run báo top-k metric, selected rank, failure category và config version. | Feedback thiếu query/session bị reject. | FR-13, BR-10 |
| AC-14 | Operations | Health/lineage report liệt kê active artifacts, versions, branch status, errors. | Artifact manifest thiếu hoặc mismatch không được publish active. | FR-14, BR-11, BR-12 |
| AC-15 | Visual KIS Future | Khi enabled, image/clip query trả visual candidate và temporal neighborhood. | Media type unsupported hoặc vector index missing bị reject rõ reason. | FR-15, BR-07 |

## MVP scope

MVP gồm AC-01 đến AC-14, trong đó ưu tiên thực thi theo thứ tự:

1. AC-01, AC-02: manifest và keyframe map.
2. AC-05, AC-04, AC-03: semantic, OCR, ASR index.
3. AC-07, AC-08, AC-09: query, fan-out, fusion.
4. AC-10: Textual KIS.
5. AC-11, AC-12: TRAKE và VQA trên retrieval core.
6. AC-13, AC-14: evaluation và operations.

## Future scope

- AC-15 Visual KIS full support.
- Region/crop-level OCR và local feature search.
- UI browser keyboard-first cho vòng chung kết.
- Learning-to-rank từ feedback đủ lớn.
- Deployment/compose stack nếu local single-process không còn đủ.

## MVP exit indicators

| Indicator | Target |
|---|---|
| Dataset readiness | Có thể import corpus sample và tạo keyframe catalog không lỗi. |
| Retrieval readiness | Textual query trả top-k candidate từ ít nhất semantic + một text branch. |
| Evidence readiness | Mọi ranked candidate có score breakdown và evidence refs. |
| Task readiness | Có ít nhất một scenario demo cho Textual KIS, TRAKE và VQA. |
| Ops readiness | Artifact active có lineage report và rerun branch lỗi không xóa artifact cũ. |

## Documentation coverage check

| Module group | FR | BR | AC | NFR |
|---|---|---|---|---|
| Dataset & Asset Catalog | FR-01, FR-02 | BR-01, BR-02, BR-11 | AC-01, AC-02 | NFR-01, NFR-02, NFR-04 |
| Signal Extraction | FR-03, FR-04, FR-05, FR-06 | BR-03, BR-11, BR-12, BR-14 | AC-03, AC-04, AC-05, AC-06 | NFR-03, NFR-04, NFR-09 |
| Query Understanding | FR-07 | BR-07 | AC-07 | NFR-08 |
| Retrieval & Fusion | FR-08, FR-09 | BR-03, BR-04, BR-05, BR-06 | AC-08, AC-09 | NFR-02, NFR-03, NFR-09 |
| Task Solvers | FR-10, FR-11, FR-12, FR-15 | BR-02, BR-07, BR-08, BR-09 | AC-10, AC-11, AC-12, AC-15 | NFR-03, NFR-08 |
| Evaluation & Operations | FR-13, FR-14 | BR-10, BR-11, BR-12, BR-13 | AC-13, AC-14 | NFR-01, NFR-05, NFR-06, NFR-07, NFR-10 |

