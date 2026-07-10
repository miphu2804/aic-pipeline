# Progress Log

### [2026-07-10] — [Feature] DACS dynamic-aware selector + portable autoresearch referee

**Done:**
- Continued the DAKE-CADRE autoresearch loop with a focus on a *simpler* algorithm at
  the same performance (the metric is already at its generalisation floor, so the lever
  is simplicity, not a better optimiser).
- **Iteration 9 (kept):** replaced CADRE's greedy facility-location seed + random
  restarts with **DACS** (Dynamic-Aware Coverage Sampling) — split each clip into `k`
  segments of equal *accumulated visual change* (content arc-length in signature space)
  and seed the local search with each segment's centroid frame. Busy stretches get more
  keyframes, static stretches fewer. Ties/edges the champion (`0.312769 → 0.312739` on
  the referee) while deleting two components. This is exactly the branch's
  "dynamic-aware" idea and directly answers "simple algorithm, best performance".
- Made the autoresearch referee **runnable without MSR-VTT**: `prepare.py` now imports
  PyAV lazily and, when `data/msrvtt/videos/` is absent, builds a seeded numpy-only
  SYNTHETIC benchmark that reproduces the real metric's structure (temporal coherence,
  uneven shots, weak size signal, 4×4→8×8 generalisation gap). Metric formula and
  algorithm interface unchanged. Reference points track the real referee (uniform ≈
  all-frames ≈ 0.35, DAKE ≈ 0.50).
- Ported DACS to production (`cadre.arc_length_seed`, `cadre.select_keyframes_dacs`,
  `extractor.extract_keyframes_dacs`). The pure `O(n)` form needs **no distance matrix**
  (good for long videos); `refine=True` reaches CADRE quality from the cheaper seed
  (`0.3138` vs facility-location `0.3141` on the referee). CADRE is left as the
  real-data-validated default; DACS is the simple/fast alternative.

**Selector comparison (synthetic referee, lower is better):**

| selector | val_loss | cost |
| --- | --- | --- |
| DAKE U-CESE (paper) | 0.5009 | O(n) |
| uniform @3% | 0.3446 | O(n) |
| DACS fast (`refine=False`) | 0.3284 | **O(n), no distance matrix** |
| production CADRE (facility-loc + LS) | 0.3141 | O(n²) |
| DACS refined (`refine=True`) | 0.3138 | O(n²) |
| CADRE champion (loop) | 0.3128 | O(n²) |
| DACS + LS + adaptive budget (loop iter 9) | 0.3127 | O(n²) |

**Changed files:**
- `backend/auto-research/dake-cadre/prepare.py` — modified (synthetic fallback, lazy av)
- `backend/auto-research/dake-cadre/train.py` — modified (iter 9 DACS seed)
- `backend/src/keyframe_extraction/cadre.py` — modified (`arc_length_seed`, `select_keyframes_dacs`)
- `backend/src/keyframe_extraction/extractor.py` — modified (`extract_keyframes_dacs`, `_decode_signatures`)
- `backend/tests/unit/keyframe_extraction/test_cadre.py` / `test_extractor.py` — new DACS tests

**Caveat:** iteration-9 and DACS numbers are on the *synthetic* fallback referee (this
container has no MSR-VTT). They must be re-confirmed on real MSR-VTT before DACS replaces
CADRE as the production default. See `auto-research/dake-cadre/experiment-handoff.md`.

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
