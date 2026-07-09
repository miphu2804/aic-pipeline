# DAKE-CADRE Auto-Research Program

## Goal

Improve the paper's DAKE keyframe extractor (U-CESE Algorithm 1) by growing a named
module — **CADRE: Change-point Anchored Density-adaptive Representative Extraction** —
inside `train.py`, and prove each step on REAL MSR-VTT video via a
representativeness-under-budget metric.

Baseline (the paper, iteration 0): `val_loss = 0.6195`.
Reference points on the same metric: uniform@3% ≈ 0.363, random@3% ≈ 0.431,
all-frames ≈ 0.351 (pure budget penalty).  **U-CESE is worse than uniform** because
size-steepness clusters keyframes at motion/transition frames, which are blurry and
non-representative — CADRE's job is to spread coverage while staying content-adaptive.

## Contract

| File | Who edits it |
|---|---|
| `prepare.py` | **Human only — READ-ONLY for the agent.** Real MSR-VTT clips + metric. |
| `train.py` | **Agent edits this.** One idea per iteration; grow the `cadre()` module. |
| `program.md` | Human tweaks (operating manual). |

## Metric (in prepare.py — do not edit)

```
val_loss = (1 - LAMBDA) * representativeness_error_norm  +  LAMBDA * budget_penalty
         = 0.65 * rep_norm + 0.35 * budget_penalty         (LAMBDA = 0.35)
```

- **rep_norm** ∈ [0,1]: mean over all frames of the distance (in 8×8×3 thumbnail
  space) to the nearest selected keyframe, normalised by each clip's feature spread.
  Lower = the keyframes represent the whole clip better.
- **budget_penalty** ∈ [0,1]: 0 at/under 3% of frames, ramps to 1.0 at 9%.
- **PRIMARY_DIRECTION = "min"** → lower val_loss = better.
- The algorithm sees only per-frame JPEG **sizes** (+ fps).  It never sees the
  thumbnails, so a size-only selector has an inherent floor — get as close as possible.

## Run command

```bash
cd backend
uv run python auto-research/dake-cadre/train.py > auto-research/dake-cadre/run.log 2>&1
grep "^val_loss:\|^peak_mem_mb:" auto-research/dake-cadre/run.log
```

Empty grep → crash → `tail -n 50 run.log`, fix trivially or discard.

## THE LOOP (run forever until human interrupts)

```
LOOP:
  1. git status — working tree clean except train.py (cache/run.log/results.tsv are ignored).
  2. Edit train.py with ONE experimental idea (see Idea Pool).
  3. git commit -am "<idea in imperative form>"
  4. uv run python auto-research/dake-cadre/train.py > auto-research/dake-cadre/run.log 2>&1
  5. grep "^val_loss:" run.log  — empty → crash → tail, fix or discard.
  6. Append a row to results.tsv (untracked → survives revert).
  7. val_loss < current_best → KEEP (advance). Else → git reset --hard HEAD~1.
  8. Repeat.
```

## Idea Pool for CADRE (ordered by expected impact)

### Tier 1 — spread coverage (fix U-CESE clustering; biggest expected win)
- [ ] **min-gap dedup**: after top-k steepness, if two picks are within G frames keep
      the higher-steepness one; refill budget from the next-best spread-out frames.
- [ ] **density floor**: guarantee ≥1 keyframe every L seconds regardless of steepness.
- [ ] **adaptive threshold**: select frames with steepness > mean + k·std (per-clip),
      instead of a global top-rho%.

### Tier 2 — CADRE core: shot-anchored representative selection
- [ ] **shot partition + midpoint**: cut the clip at steepness peaks; pick each shot's
      temporal midpoint (settled, non-transition frame) rather than the boundary.
- [ ] **in-shot stability anchor**: within each shot pick the local size-variance
      minimum (the most "settled" frame) as the representative.
- [ ] **density-adaptive shots**: split shots longer than L seconds into sub-segments,
      one anchor each.

### Tier 3 — signal enrichment (size-only)
- [ ] **log-ratio hybrid**: fuse |log(s_j/s_i)| (scale-invariant) with U-CESE steepness.
- [ ] **exponential smoothing** of the size curve before steepness.
- [ ] **multi-scale window**: combine window=2 and window=5 steepness.

### Tier 4 — redundancy control
- [ ] **size-signature dedup**: drop an anchor whose local size profile is within ε of
      the previous kept anchor.
- [ ] **budget-aware pruning**: when over budget, drop the anchors whose removal least
      increases representativeness (greedy).

## Rules
- ONE idea per commit. No bundling.
- Simplicity wins ties — a gain from deleting code is a strong keep.
- Never edit prepare.py.  Never stop to ask "should I continue?" — loop forever.
- Keep the `val_loss:` / `peak_mem_mb:` print lines in train.py.
