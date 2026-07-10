# Experiment Handoff — DAKE → CADRE keyframe autoresearch

> Paste this whole file to a fresh agent to continue. It is self-contained: it explains
> the task, the current state, the 3-file loop contract, how to run it, what has been
> tried, and exactly what to do next. Work happens in `backend/`.

## 1. TL;DR

- **Goal:** improve the paper's DAKE keyframe extractor (U-CESE, JPEG-size steepness) by
  a named module **CADRE** (Content-Aware Density-adaptive Representative Extraction),
  measured on **real MSR-VTT video** via an autoresearch loop.
- **Status:** CADRE **converged at `val_loss = 0.2847`** vs DAKE baseline `0.6195`
  (**-54%**; uniform sampling reference `0.363`). We are at the floor of the current
  metric — further gains are ~0.001/iter. Everything is committed on branch
  `feat/dynamic-aware-keyframe-extraction`.
- **Two ways forward:** (A) keep micro-tuning the current metric (marginal), or
  (B) **upgrade the referee to a CLIP-embedding metric** for real, competition-relevant
  headroom (recommended — see §9).

## 2. The 3-file contract (autoresearch loop)

Dir: `backend/auto-research/dake-cadre/`

| File | Who edits | Role |
|---|---|---|
| `prepare.py` | **READ-ONLY for the agent** | The referee. Builds the 60-clip MSR-VTT benchmark, defines `evaluate(algorithm)` (the ground-truth metric) and the constants. Editing it = void experiment, UNLESS you are deliberately upgrading the metric (§9) — then treat it as a new referee version and re-baseline. |
| `train.py` | **The agent edits ONLY this** | The algorithm. One idea per iteration; keep if `val_loss` drops, else revert. |
| `program.md` | operating manual | Loop + idea pool. |

Also present: `benchmark.py` (MLflow DAKE-vs-CADRE), `results.tsv` (log), `CLAUDE.md`.

## 3. How to run the loop

```bash
cd backend
# one iteration:
uv run python auto-research/dake-cadre/train.py > auto-research/dake-cadre/run.log 2>&1
grep "^val_loss:" auto-research/dake-cadre/run.log        # empty ⇒ crash: tail run.log
```

Loop protocol (from `program.md`):
1. Edit `train.py` with ONE idea.
2. `git commit -am "feat(cadre): <idea>"`.
3. Run (above). Grep `val_loss`.
4. Append a row to `results.tsv` (it is git-ignored → survives revert).
5. `val_loss` < current best ⇒ **keep**; else `git reset --hard HEAD~1`.

**Fast-iteration trick (important):** `train.py` burns a fixed 25 s time budget per run.
To prototype many ideas cheaply, write a throwaway script that imports
`prepare.evaluate` and calls it directly (no budget) on candidate selectors, e.g.:

```python
import sys; sys.path.insert(0, "auto-research/dake-cadre")
from prepare import evaluate
def my_selector(sizes, sig, fps): ...      # returns list[int]
print(evaluate(my_selector))               # one number, sub-second
```

Only promote the winner into `train.py` for the official timed run + commit.

## 4. The metric (what `val_loss` means)

Plain words: *"Do the chosen keyframes represent the whole clip well, using few frames?"*

```
val_loss = (1 - LAMBDA) * rep_norm  +  LAMBDA * budget_penalty       # LAMBDA = 0.35
```

- `rep_norm` ∈ [0,1]: for every frame, distance to its **nearest selected keyframe** in
  **8×8×3 thumbnail** space, averaged, then divided by the clip's feature spread. Lower =
  keyframes cover the clip's content better.
- `budget_penalty` ∈ [0,1]: 0 at/under **3%** of frames, ramps linearly to 1.0 at 9%.
- `PRIMARY_DIRECTION = "min"`. Lower is better.
- **The algorithm never sees the 8×8 metric feature** — it only gets a coarser **4×4**
  signature (§5). That generalization gap is the performance floor; a 4×4-based selector
  cannot perfectly minimise an 8×8 objective. This is why the metric is not saturable to 0.

Reference points on this metric: `all-frames 0.351` (pure budget penalty), `uniform@3%
0.363`, `random@3% 0.431`, `DAKE/U-CESE 0.6195`, greedy 8×8 ceiling `~0.30`,
**CADRE 0.2847**.

## 5. Referee constants (`prepare.py`, do not edit unless upgrading metric)

```
TIME_BUDGET_SECONDS=25   SEED=42   PRIMARY_DIRECTION="min"
NUM_VIDEOS=60   MAX_FRAMES=320
THUMB_GRID=8    # 8×8×3=192-d  → the METRIC feature (clip.feats)
SIG_GRID=4      # 4×4×3=48-d   → the ALGORITHM signature (clip.sig)
TARGET_KEYFRAME_RATIO=0.03   BUDGET_LAMBDA=0.35
```

Data source: `data/msrvtt/videos/*.mp4` (7010 clips, 60 sampled by SEED). Features are
decoded once and cached to `cache/*.pkl` (~17 s first run). **If you change any referee
constant, delete `cache/*.pkl` so it rebuilds.**

**Algorithm interface** the loop must implement:
```python
algorithm(sizes: list[int], sig: np.ndarray[n, 48], fps: float) -> list[int]  # frame indices
```
`sizes` = per-frame JPEG byte size (the paper's DAKE signal, weak). `sig` = per-frame
4×4 colour signature (what CADRE actually uses). `evaluate` sanitises the returned
indices (unique, in-range, sorted).

## 6. What CADRE currently does (`train.py`, the `cadre()` function)

Selection on the 4×4 colour signature (NOT on JPEG size — that signal proved too weak):
1. `_pairwise_dist(sig)` → Euclidean distance matrix.
2. `_facility_location(dist, k)` → greedy k-medoid (minimise mean nearest-selected dist).
3. `_local_search(dist, sel)` → Teitz-Bart swap refinement (beats greedy 1-optimal floor).
4. **Density-adaptive budget (iter 7):** grow k from 1..ceil(3·rho·n), keep the size that
   minimises `(rep_on_sig + budget_penalty)` — busy clips get more keyframes, static
   clips fewer.
5. **Random restarts (iter 8):** a couple of random inits per size escape weak optima.

## 7. Results log (`results.tsv`)

```
iter  val_loss   idea                                                    keep
0     0.619522   baseline U-CESE top-rho% steepness (paper DAKE)         seed
1     0.414005   NMS spread on steepness signal                          KEEP
2     0.308679   CADRE facility-location on 4×4 colour signature         KEEP
3     0.306648   budget kmul=1.3 (int rule overshoots)                   KEEP
4     0.297227   budget = ceil(rho*n)                                    KEEP
5     0.288058   Teitz-Bart local search                                 KEEP
6     0.288058   restarts/L1/normalize/more-rounds — no gain             DISCARD
7     0.285957   density-adaptive budget (per-clip elbow)                KEEP
8     0.284700   random restarts per size                                KEEP  ← current best
```

## 8. Key findings (don't relearn these the hard way)

- **JPEG-size steepness is a poor representativeness proxy.** It clusters keyframes on
  blurry motion/transition frames → worse than uniform. Every size-only attempt to beat
  uniform failed. The win came from the cheap **colour signature** (near-free at decode).
- **Uniform temporal sampling is a strong baseline** (0.363) because MSR-VTT clips are
  short and temporally coherent. You must exploit content structure to beat it.
- **Facility-location + local search on the 4×4 signature ≈ the 8×8 optimum.** We are at
  the generalization floor; L1 distance, signature normalization, more local-search
  rounds, and PAM full-swap gave **no** improvement over Teitz-Bart.

## 9. What to do next

### Path A — squeeze the current metric (marginal, ~0.001/iter)
Only untried idea with a rationale: **change-point fusion (the "Change-point Anchored"
in CADRE's name).** Use U-CESE size-steepness to *force-include* the frame right after a
strong steepness spike (a hard cut the 4×4 signature may blur across), then let
facility-location fill the rest under the adaptive budget. Test via the fast explorer
first; expect small or no gain, but it completes the algorithm's namesake.

### Path B — upgrade the referee for REAL headroom (recommended)
Replace the 8×8-thumbnail representativeness with a **CLIP-embedding** metric, so
"representative" means *semantically* representative (much closer to the actual
competition retrieval objective). Concretely, in `prepare.py` (treat as referee v3):
- Per frame, compute a CLIP image embedding (use the `transformers` skill / a small
  open CLIP; cache it like the thumbnails). Keep the algorithm's cheap `sig` unchanged
  (or offer a slightly richer signature).
- `rep_norm` = mean nearest-keyframe **cosine distance in CLIP space**, normalised.
- Re-baseline uniform / DAKE / CADRE, then let the loop climb the new headroom.
- Even better (biggest payoff, more setup): download MSR-VTT captions and switch to a
  **text→frame retrieval recall@k** ground-truth metric — that is exactly what the AIC
  competition scores.

Whichever path: the metric is the lever. On the current thumbnail metric the loop is done.

## 10. Production deliverable (already shipped & tested)

- `backend/src/keyframe_extraction/cadre.py` — `select_keyframes(signatures, ratio)` plus
  `frame_signature`, `pairwise_distances`, `facility_location`, `local_search`. (Note:
  production ships the fixed-`ceil(ratio*n)` + local-search version = 0.288; the
  adaptive-k/restart tweaks live only in the experiment `train.py` — port them only if a
  future metric shows the gain is worth the added complexity.)
- `backend/src/keyframe_extraction/extractor.py` — `KeyframeExtractor.extract_keyframes_cadre(video_path)`.
- `backend/tests/unit/keyframe_extraction/test_cadre.py` (14 tests), `test_extractor.py`
  (integration on a generated clip). Run: `uv run pytest` (47 pass).
- `backend/auto-research/dake-cadre/benchmark.py` — logs DAKE vs CADRE to MLflow:
  `uv run python auto-research/dake-cadre/benchmark.py`
  `uv run mlflow ui --backend-store-uri sqlite:///auto-research/dake-cadre/mlflow.db`

## 11. Gotchas

- **Only edit `train.py`** in the loop. `prepare.py` is the referee (except deliberate
  metric upgrades in §9, which reset the baseline).
- **Git-ignored (must stay untracked):** `cache/`, `run.log`, `results.tsv`, `mlruns/`,
  `mlflow.db`, `mlartifacts/`. `results.tsv` MUST stay untracked so `git reset --hard`
  on a discarded iter never wipes the log.
- **black + isort conflict:** the backend has no `isort profile=black`, so multi-line
  imports fight between the two tools. Use module-style imports or a `# isort: off/on`
  block (see `benchmark.py`). A follow-up task exists to add `profile=black`.
- **Deps:** `numpy` is a prod dependency; `mlflow` is dev. Run everything via `uv run`.
- **Changing `SIG_GRID`/`THUMB_GRID`/`NUM_VIDEOS`** ⇒ delete `cache/*.pkl` to rebuild.
- Commit style: `type(scope): content`, e.g. `feat(cadre): ...` (enforced by review).

## 12. Git state

Branch `feat/dynamic-aware-keyframe-extraction`. Latest experiment commit:
`087afd3 feat(cadre): add random restarts per size ...`. The full CADRE story is in
`git log` (search `cadre`) and `docs/PROGRESS.md`.
