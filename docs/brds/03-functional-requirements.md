# BRDS 03 - Functional requirements

## Module summary

| Module | Business Goal | Actors | States Affected | Key Rules | Acceptance |
|---|---|---|---|---|---|
| Dataset & Asset Catalog | Quản lý corpus video, metadata, keyframe identity. | `PipelineOperator`, `SystemJob` | `CorpusAsset`, `IndexRun` | BR-01, BR-02, BR-11 | AC-01, AC-02 |
| Signal Extraction | Tạo ASR, OCR, semantic, color/object evidence. | `SystemJob` | `IndexRun`, `IndexArtifact` | BR-03, BR-11, BR-12 | AC-03..AC-06 |
| Query Understanding | Chuẩn hóa task/query và chọn nhánh retrieval. | `CompetitorUser`, `SystemJob` | `QuerySession` | BR-07 | AC-07 |
| Retrieval & Fusion | Fan-out, combine, rerank, giữ evidence. | `SystemJob` | `QuerySession`, `CandidateReview` | BR-03..BR-06 | AC-08, AC-09 |
| Task Solvers | Giải Textual KIS, TRAKE, VQA, Visual KIS. | `CompetitorUser`, `SystemJob` | `Submission`, `Answer`, `Sequence` | BR-07..BR-09 | AC-10..AC-12, AC-15 |
| Evaluation & Operations | Ghi feedback, benchmark, health, artifact lineage. | `Evaluator`, `Maintainer`, `SystemJob` | `Feedback`, `EvaluationRun`, `IndexArtifact` | BR-10..BR-12 | AC-13, AC-14 |

## Dataset & Asset Catalog

### FR-01 - Import dataset manifest

- Actor: `PipelineOperator`.
- Preconditions: raw video hoặc metadata file đã có trên máy local.
- Behavior: hệ thống nhận manifest chứa `video_id`, đường dẫn video, metadata, thời lượng nếu có, và kiểm tra ID trùng, path thiếu, schema sai.
- Inputs: manifest file hoặc directory scan config.
- Outputs: corpus catalog versioned, danh sách lỗi theo dòng nếu reject.
- Rejections: thiếu `video_id`, path không tồn tại, ID trùng, metadata không parse được.
- State impact: `CorpusAsset: DRAFT -> READY` khi hợp lệ.
- Data touched: `VideoAsset`, `SourceMetadata`, `CorpusManifest`.
- Audit/observability: ghi import run id, số video hợp lệ, số record bị reject.
- Traces: BR-02, BR-11, AC-01, NFR-01.

### FR-02 - Tạo hoặc import keyframe map

- Actor: `SystemJob`.
- Preconditions: `CorpusAsset` ở `READY`.
- Behavior: tạo hoặc import keyframe, gán mỗi keyframe về `video_id`, `frame_id`, `timestamp_ms`, `keyframe_path`.
- Inputs: video asset, keyframe selection config hoặc thư mục keyframe có sẵn.
- Outputs: `Keyframe` catalog và map temporal.
- Rejections: keyframe không map được video, timestamp ngoài duration, path ảnh thiếu.
- State impact: `IndexRun: QUEUED -> RUNNING -> SUCCEEDED/FAILED`.
- Data touched: `Keyframe`, `FrameLocator`.
- Audit/observability: số keyframe/video, tỷ lệ giảm frame, lỗi theo video.
- Traces: BR-01, BR-02, AC-02, NFR-02.

## Signal Extraction

### FR-03 - ASR transcript extraction và indexing

- Actor: `SystemJob`.
- Preconditions: audio/video asset có thể đọc hoặc transcript external được cung cấp.
- Behavior: trích transcript theo segment, chuẩn hóa text, lưu segment và đẩy vào text index.
- Inputs: audio path, ASR config, language config.
- Outputs: `TranscriptSegment`, ASR text index artifact.
- Rejections: audio không đọc được, transcript rỗng toàn bộ, artifact version thiếu.
- State impact: `IndexArtifact: BUILDING -> ACTIVE/FAILED`.
- Data touched: `TranscriptSegment`, `TextIndexDocument`.
- Audit/observability: word count, segment count, failed videos, ASR model version.
- Traces: BR-03, BR-11, BR-12, AC-03, NFR-09.

### FR-04 - OCR scene text extraction và indexing

- Actor: `SystemJob`.
- Preconditions: keyframe catalog đã sẵn sàng.
- Behavior: detect và recognize text trên keyframe, lưu bounding box, confidence, raw text, normalized text, rồi index cho search.
- Inputs: keyframe image, OCR config.
- Outputs: `OCRBlock`, OCR text index artifact.
- Rejections: keyframe image lỗi, OCR output không map được `frame_id`, artifact version thiếu.
- State impact: `IndexArtifact: BUILDING -> ACTIVE/FAILED`.
- Data touched: `OCRBlock`, `TextIndexDocument`.
- Audit/observability: OCR block count, empty frame rate, confidence distribution.
- Traces: BR-03, BR-11, BR-12, AC-04, NFR-03.

### FR-05 - Semantic embedding và vector indexing

- Actor: `SystemJob`.
- Preconditions: keyframe catalog đã sẵn sàng.
- Behavior: encode keyframe thành semantic embedding, lưu vector artifact và index nearest-neighbor.
- Inputs: keyframe image, embedding model config.
- Outputs: `FeatureVector`, semantic FAISS index artifact.
- Rejections: vector dimension mismatch, missing keyframe, model config không versioned.
- State impact: `IndexArtifact: BUILDING -> ACTIVE/FAILED`.
- Data touched: `FeatureVector`, `VectorIndex`.
- Audit/observability: vector count, dimension, model id, index build time.
- Traces: BR-03, BR-11, BR-12, AC-05, NFR-04.

### FR-06 - Color/object attribute extraction

- Actor: `SystemJob`.
- Preconditions: keyframe catalog đã sẵn sàng.
- Behavior: trích dominant color và object/attribute signal ở mức đủ dùng để filter/rerank.
- Inputs: keyframe image, color/object config.
- Outputs: `VisualAttribute`, optional color vector index.
- Rejections: attribute không map được keyframe, config thiếu color space.
- State impact: `IndexArtifact: BUILDING -> ACTIVE/FAILED`.
- Data touched: `VisualAttribute`, `FeatureVector`.
- Audit/observability: color histogram coverage, object label count, low-confidence rate.
- Traces: BR-03, BR-11, AC-06, NFR-03.

## Query Understanding

### FR-07 - Intake và normalize competition query

- Actor: `CompetitorUser`.
- Preconditions: ít nhất một index active phù hợp task type.
- Behavior: nhận task type `TEXTUAL_KIS`, `VQA`, `TRAKE`, hoặc `VISUAL_KIS`; chuẩn hóa query text, filters, sub-events, hoặc query media.
- Inputs: task type, query text, optional filters, optional image/clip.
- Outputs: `QuerySession` với normalized query và retrieval plan.
- Rejections: task type không hỗ trợ, query rỗng, filter sai schema, query media thiếu cho Visual KIS.
- State impact: `QuerySession: DRAFT -> RUNNING/REJECTED`.
- Data touched: `QuerySession`, `NormalizedQuery`.
- Audit/observability: task type, selected branches, validation failures.
- Traces: BR-07, AC-07, NFR-08.

## Retrieval & Fusion

### FR-08 - Multi-index retrieval fan-out

- Actor: `SystemJob`.
- Preconditions: `QuerySession` hợp lệ và có index active.
- Behavior: chạy query song song hoặc tuần tự qua text index và vector index phù hợp, giữ score/evidence theo branch.
- Inputs: normalized query, active index set.
- Outputs: raw hit lists theo branch.
- Rejections: index unavailable, index version mismatch, branch timeout vượt cấu hình.
- State impact: `QuerySession: RUNNING -> COMBINING/FAILED`.
- Data touched: `IndexArtifact`, `CandidateHit`.
- Audit/observability: latency từng branch, hit count, branch errors.
- Traces: BR-03, BR-04, BR-11, AC-08, NFR-02.

### FR-09 - Combine, deduplicate và rerank candidates

- Actor: `SystemJob`.
- Preconditions: có ít nhất một raw hit list.
- Behavior: merge hit theo `video_id/frame_id/timestamp_ms`, deduplicate video gần giống, tính score tổng deterministic và giữ evidence.
- Inputs: raw hit lists, fusion config, optional feedback weights.
- Outputs: ranked candidate list.
- Rejections: không có hit nào, candidate không có locator canonical, fusion config invalid.
- State impact: `QuerySession: COMBINING -> READY/READY_WITH_WARNINGS`.
- Data touched: `CandidateHit`, `RankedCandidate`, `FusionRun`.
- Audit/observability: score breakdown, dedup decisions, fusion config version.
- Traces: BR-04, BR-05, BR-06, AC-09, NFR-03.

## Task Solvers

### FR-10 - Textual KIS result review và submission draft

- Actor: `CompetitorUser`.
- Preconditions: ranked results ready.
- Behavior: hiển thị candidate và evidence để chọn `VideoId`, `FrameId`; hỗ trợ copy/export submission draft nội bộ.
- Inputs: ranked candidates.
- Outputs: selected `VideoId`, `FrameId`, optional timestamp.
- Rejections: candidate không có canonical locator, session hết hạn.
- State impact: `Submission: DRAFT -> READY`.
- Data touched: `TaskSubmission`, `CandidateReview`.
- Audit/observability: selected candidate rank, evidence viewed.
- Traces: BR-02, BR-07, AC-10, NFR-08.

### FR-11 - TRAKE temporal retrieval và alignment

- Actor: `SystemJob`.
- Preconditions: query type `TRAKE`, retrieval core available.
- Behavior: tách query thành sub-events, retrieve candidate cho từng event, chọn chuỗi frame theo thứ tự thời gian trong cùng video hoặc theo rule cấu hình.
- Inputs: multi-event query text, ordering constraints.
- Outputs: ordered frame sequence với evidence từng event.
- Rejections: không tách được event, không có chuỗi thỏa thứ tự, frame locator thiếu.
- State impact: `QuerySession: COMBINING -> READY/READY_WITH_WARNINGS`.
- Data touched: `TemporalEvent`, `TemporalSequence`.
- Audit/observability: sub-event count, candidate count/event, reject reason.
- Traces: BR-08, AC-11, NFR-03.

### FR-12 - VQA retrieve-first answer

- Actor: `SystemJob`.
- Preconditions: query type `VQA`, ranked candidates hoặc retrieval plan available.
- Behavior: retrieve candidate, extract OCR/ASR/object/visual evidence, sinh answer ngắn và link evidence.
- Inputs: question text, optional constraints.
- Outputs: answer text, confidence, evidence references.
- Rejections: evidence không đủ, answer không map được candidate, question unsupported.
- State impact: `Answer: DRAFT -> ANSWERED/UNANSWERED`.
- Data touched: `VQAAnswer`, `EvidenceReference`.
- Audit/observability: evidence used, answer confidence, unsupported pattern.
- Traces: BR-09, AC-12, NFR-03.

### FR-15 - Visual KIS query extension

- Actor: `CompetitorUser`.
- Preconditions: visual query support enabled và semantic vector index active.
- Behavior: nhận ảnh hoặc clip ngắn, encode cùng không gian embedding với keyframe, search near-duplicate/semantic candidate và mở rộng temporal neighborhood.
- Inputs: image/clip query, optional crop/region metadata.
- Outputs: candidate `VideoId`, `FrameId` với visual similarity evidence.
- Rejections: media type unsupported, vector index missing, clip quá dài so với config.
- State impact: `QuerySession: DRAFT -> RUNNING -> READY`.
- Data touched: `VisualQuery`, `CandidateHit`.
- Audit/observability: media hash, embedding model version, nearest-neighbor score.
- Traces: BR-07, AC-15, NFR-08.

## Evaluation & Operations

### FR-13 - Feedback và evaluation loop

- Actor: `Evaluator`, `CompetitorUser`.
- Preconditions: có query session hoặc benchmark query set.
- Behavior: ghi label đúng/sai, selected rank, notes; chạy evaluation report cho query set.
- Inputs: relevance label, ground truth nếu có, selected candidate.
- Outputs: evaluation run report và feedback records.
- Rejections: label thiếu query/session, ground truth sai schema.
- State impact: `Feedback: NEW -> APPLIED_TO_RUN`.
- Data touched: `FeedbackRecord`, `EvaluationRun`.
- Audit/observability: metric top-k, failure category, run config.
- Traces: BR-10, AC-13, NFR-01.

### FR-14 - Artifact lineage, health và operations

- Actor: `Maintainer`, `SystemJob`.
- Preconditions: pipeline config tồn tại.
- Behavior: expose trạng thái artifact active, version model/index, health của text/vector index, và local runbook.
- Inputs: config path, artifact registry.
- Outputs: health summary, lineage report, actionable error.
- Rejections: artifact manifest thiếu, config version không tương thích.
- State impact: `IndexArtifact: ACTIVE -> DEPRECATED` khi thay thế.
- Data touched: `ArtifactManifest`, `PipelineConfig`, `HealthCheck`.
- Audit/observability: structured logs, correlation id, active artifact version.
- Traces: BR-11, BR-12, AC-14, NFR-05, NFR-06.

