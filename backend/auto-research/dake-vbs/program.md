# DAKE-VBS Auto-Research Program

## Goal

Iteratively improve the DAKE keyframe-extraction algorithm for Video Browser Showdown
(VBS) retrieval quality.  The metric is **scene coverage recall** — fraction of
known scene-change events covered by at least one selected keyframe, minus a
budget penalty for over-selecting.

## Contract

| File | Who edits it |
|---|---|
| `prepare.py` | **Human only — READ-ONLY for the agent.** Synthetic scenarios + ground truth. |
| `train.py` | **Agent edits this.** One idea per iteration. |
| `program.md` | Human tweaks (operating manual). |

## Metric

```
val_loss = 1.0 - max(0, recall - budget_penalty)
```

- **recall** = fraction of GT scene-change events detected within ±3 frames
- **budget_penalty** ≤ 0.15, proportional to how much over 5% of frames we select
- **PRIMARY_DIRECTION = "min"** → lower val_loss = better

## Run command

```bash
cd backend
uv run python auto-research/dake-vbs/train.py > auto-research/dake-vbs/run.log 2>&1
```

Check result:
```bash
grep "^val_loss:\|^peak_mem_mb:" auto-research/dake-vbs/run.log
```

Empty grep → crash. `tail -n 50 auto-research/dake-vbs/run.log`, fix if trivial, else discard.

## results.tsv columns

```
iteration \t val_loss \t idea \t keep
```

## THE LOOP (run forever until human interrupts)

```
LOOP:
  1. git status — confirm clean working tree.
  2. Edit train.py with ONE experimental idea (see Idea Pool below).
  3. git commit -am "<idea in imperative form>"
  4. Run:  uv run python auto-research/dake-vbs/train.py > auto-research/dake-vbs/run.log 2>&1
  5. grep "^val_loss:\|^peak_mem_mb:" auto-research/dake-vbs/run.log
     — Empty → crash → tail log, fix trivially or discard.
  6. Append row to results.tsv.
  7. If val_loss < current_best → KEEP (advance). Else → git reset --hard HEAD~1.
  8. Repeat.
```

## Idea Pool (ordered by expected impact, cross off as tried)

### Tier 1 — selection strategy (likely high impact)

- [ ] **tau threshold**: replace rho-ratio with an absolute steepness threshold `tau`.
      Select all frames with steepness > tau instead of top-rho%.  Adaptive count.
- [ ] **floor sampling**: guarantee at least 1 keyframe every K seconds regardless of
      steepness.  Prevents static-anchor coverage gaps.
- [ ] **tau + floor hybrid**: threshold for scene changes + periodic floor.  Likely the
      right long-term architecture.

### Tier 2 — signal enrichment

- [ ] **histogram change signal**: compute a simple per-bin histogram difference
      alongside JPEG steepness.  Fuse as weighted average.
- [ ] **size ratio signal**: use relative size ratio s_j/s_i instead of absolute delta.
      Scale-invariant across different video resolutions.
- [ ] **exponential smoothing**: smooth the steepness curve before thresholding to
      reduce spurious single-frame spikes.

### Tier 3 — post-selection cleanup

- [ ] **minimum gap deduplication**: if two selected frames are within G frames,
      keep only the one with higher steepness.  Avoids burst clusters at hard cuts.
- [ ] **first-frame guarantee**: always include frame 0 (or first post-warmup frame)
      so the video start is always covered.
- [ ] **warmup auto-detection**: set warmup = first frame whose size drops below
      mean/2, rather than a fixed seconds value.

### Tier 4 — window tuning

- [ ] **larger window (5)**: test window=5 for smoother steepness signal.
- [ ] **asymmetric window**: average both forward and backward neighbours.
- [ ] **weighted window**: weight j=i+1 > i+2 > i+3 (exponential decay).

## Rules

- ONE idea per commit.  No bundling.
- simplicity wins ties — a tiny gain from deleting code is a strong keep.
- Never edit prepare.py.
- Do NOT stop to ask "should I continue?" — loop forever.
- Out of ideas in the pool? Combine near-misses, tune params, invent new signals.
