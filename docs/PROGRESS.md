# Progress Log

### [2026-07-10 02:10 UTC+07:00] — [Feature] CADRE keyframe module + DAKE-vs-CADRE MLflow benchmark

**Done:**
- Improved the paper's DAKE keyframe extractor (U-CESE) by adding a named module,
  **CADRE** (Content-Aware Density-adaptive Representative Extraction), developed via an
  autoresearch loop on real MSR-VTT video (`data/msrvtt/videos/`, 60-clip benchmark).
- Rebuilt the autoresearch referee (`auto-research/dake-cadre/prepare.py`) around a
  real, non-saturable metric: representativeness-under-budget (VSUMM-style) on 8×8
  thumbnails, with a cheap 4×4 colour signature exposed to the algorithm.
- Loop result: val_loss **0.6195 → 0.2881** (uniform baseline 0.363). CADRE =
  facility-location + Teitz-Bart local search on the colour signature.
- Ported the winning algorithm to a tested production module and wired it into the
  extractor; added an MLflow benchmark that logs DAKE vs CADRE side by side
  (**CADRE cuts val_loss 53.7%**: 0.6215 → 0.2881, rep-error 0.956 → 0.428).

**Changed files:**
- `backend/src/keyframe_extraction/cadre.py` — created (CADRE algorithm, pure functions)
- `backend/src/keyframe_extraction/extractor.py` — modified (`extract_keyframes_cadre`)
- `backend/src/keyframe_extraction/models.py` — modified (`CadreKeyframe`)
- `backend/tests/unit/keyframe_extraction/test_cadre.py` — created (14 tests)
- `backend/tests/unit/keyframe_extraction/test_extractor.py` — modified (CADRE integration test)
- `backend/auto-research/dake-cadre/` — created (referee, train loop, MLflow benchmark)
- `backend/pyproject.toml` / `uv.lock` — numpy (prod), mlflow (dev)

**Flow explained:**
1. `prepare.py` samples 60 MSR-VTT clips → per-frame JPEG sizes (DAKE signal), 4×4
   colour signature (CADRE signal), 8×8 thumbnail (metric ground truth). Cached once.
2. `train.py` is the autoresearch loop's editable file; each iteration is one idea,
   kept only if `val_loss` improves, else `git reset --hard`.
3. Production `cadre.select_keyframes(signatures, ratio)` = greedy facility-location +
   local search → the `ceil(ratio·n)` most representative frames.
4. `benchmark.py` scores both production selectors and logs to MLflow
   (`sqlite:///auto-research/dake-cadre/mlflow.db`, experiment `dake-vs-cadre`).

**Key finding:** the paper's size-steepness signal is a *poor* representativeness proxy
(it clusters keyframes on blurry transition frames, worse than uniform sampling). A
near-free colour signature computed at the same decode step unlocks content-adaptive
selection that roughly halves the loss.
