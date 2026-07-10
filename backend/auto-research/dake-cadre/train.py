"""DAKE-CADRE experiment — the agent edits ONLY this file.

Baseline = faithful U-CESE Algorithm 1 (the paper's DAKE): per-frame JPEG-size
steepness, select the top-rho% frames by steepness.  The research goal is to beat
this paper baseline on the real MSR-VTT representativeness metric by adding the
named CADRE module (Change-point Anchored Density-adaptive Representative Extraction).

Experiment log (newest first):
  - [baseline] U-CESE top-rho% steepness, rho=0.03 window=3 warmup=0

To run:
    cd backend
    uv run python auto-research/dake-cadre/train.py > auto-research/dake-cadre/run.log 2>&1
"""

from __future__ import annotations

import math
import sys
import time

import numpy as np

sys.path.insert(0, "auto-research/dake-cadre")

from prepare import (  # noqa: E402  # isort:skip
    BUDGET_LAMBDA,
    TARGET_KEYFRAME_RATIO,
    TIME_BUDGET_SECONDS,
    evaluate,
)


# ---------------------------------------------------------------------------
# Algorithm — edit this section freely
# ---------------------------------------------------------------------------
def _steepness(s_i: float, s_j: float, i: int, j: int, s_max: float) -> float:
    """U-CESE normalized rate of change in JPEG size between two frames (paper 4.1)."""
    if s_max <= 0:
        return 0.0
    delta = 100.0 * abs((s_j - s_i) / s_max)
    d = abs(j - i)
    if d == 0:
        return 1.0 if delta > 0 else 0.0
    return delta / math.sqrt(d * d + delta * delta)


def _frame_steepness(sizes: list[int], window: int = 3) -> list[float]:
    """Per-frame steepness: average S(i, j) over a forward window (U-CESE Algorithm 1).

    Returns a list of length n; the final frame (no forward neighbours) gets 0.
    """
    n = len(sizes)
    if n < 2:
        return [0.0] * n
    s_max = max(sizes)
    out = [0.0] * n
    for i in range(n - 1):
        total = 0.0
        count = 0
        for j in range(i + 1, min(n, i + window + 1)):
            total += _steepness(sizes[i], sizes[j], i, j, s_max)
            count += 1
        out[i] = total / count if count else 0.0
    return out


def dake_ucese(
    sizes: list[int],
    fps: float,
    *,
    rho: float = TARGET_KEYFRAME_RATIO,
    window: int = 3,
    warmup: int = 0,
) -> list[int]:
    """Paper baseline: select the top rho-fraction of frames by U-CESE steepness."""
    n = len(sizes)
    if n < 2:
        return list(range(n))

    scored = list(enumerate(_frame_steepness(sizes, window)))
    eligible = [(i, s) for i, s in scored if i >= warmup]
    if not eligible:
        return [0]

    k = max(1, int(rho * n))
    eligible.sort(key=lambda x: x[1], reverse=True)
    return sorted(i for i, _ in eligible[:k])


def _pairwise_dist(sig: np.ndarray) -> np.ndarray:
    """Euclidean distance matrix over the per-frame coarse signatures."""
    gram = sig @ sig.T
    sq = np.diag(gram)
    return np.sqrt(np.clip(sq[:, None] - 2.0 * gram + sq[None, :], 0.0, None))


def _facility_location(dist: np.ndarray, k: int) -> list[int]:
    """Greedy facility-location: pick k frames minimising the mean distance from every
    frame to its nearest selected frame.

    This is the representativeness objective the referee scores, approximated online
    with the classic greedy (each step adds the frame that most reduces the mean
    nearest-neighbour distance).  Seed = the medoid (frame nearest all others).
    """
    start = int(dist.mean(axis=1).argmin())
    selected = [start]
    nearest = dist[start].copy()
    while len(selected) < k:
        nxt = int(np.minimum(nearest[None, :], dist).mean(axis=1).argmin())
        if nxt in selected:
            break
        selected.append(nxt)
        nearest = np.minimum(nearest, dist[nxt])
    return selected


def _local_search(dist: np.ndarray, selected: list[int], rounds: int = 4) -> list[int]:
    """Teitz-Bart local search: repeatedly replace one selected frame with the frame
    that most lowers the mean nearest-neighbour distance, until no swap helps.

    Greedy facility-location is only 1-optimal; a few swap rounds reach a much better
    local optimum (and, empirically here, below the greedy representativeness floor).
    """
    n = dist.shape[0]
    sel = list(selected)
    cur = dist[:, sel].min(axis=1).mean()
    for _ in range(rounds):
        improved = False
        for slot in range(len(sel)):
            others = sel[:slot] + sel[slot + 1 :]
            base = dist[:, others].min(axis=1) if others else np.full(n, dist.max())
            # For each candidate column c, mean over frames of min(base, dist[:, c]).
            cand = np.minimum(base[:, None], dist).mean(axis=0)
            cand[others] = np.inf  # never duplicate an existing keyframe
            best = int(cand.argmin())
            if cand[best] < cur - 1e-12:
                sel[slot], cur = best, float(cand[best])
                improved = True
        if not improved:
            break
    return sorted(set(sel))


def cadre(
    sizes: list[int],
    sig: np.ndarray,
    fps: float,
    *,
    rho: float = TARGET_KEYFRAME_RATIO,
    kmax_mul: float = 3.0,
    warmup: int = 0,
) -> list[int]:
    """CADRE — Change-point Anchored Density-adaptive Representative Extraction.

    Built incrementally by the autoresearch loop, one component per iteration.
    The paper's size-only signal tops out around uniform sampling (~0.363); CADRE
    instead selects on the cheap 4x4 colour signature the decoder yields for free.

    [iter 2] Facility-location core: greedily choose the k frames that best represent
             the whole clip in signature space.
    [iter 4] Budget = ceil(rho * n): keeping the fractional keyframe (int() dropped it)
             lands squarely on the rep/budget optimum instead of overshooting.
    [iter 5] Teitz-Bart local search refines the greedy set past its 1-optimal floor.
    [iter 7] Density-adaptive budget: instead of a fixed count, grow the keyframe set
             and keep the size that minimises rep+budget on the signature — busy clips
             get more keyframes, static clips fewer.
    """
    n = len(sizes)
    if n < 2:
        return list(range(n))

    sig = np.asarray(sig, dtype=np.float64)
    dist = _pairwise_dist(sig)
    norm = float(np.linalg.norm(sig - sig.mean(axis=0), axis=1).mean()) or 1.0

    kmax = min(n, max(2, math.ceil(rho * n * kmax_mul)))
    order = _facility_location(dist, kmax)

    best_sel, best_val = order[:1], math.inf
    for k in range(1, len(order) + 1):
        sel = _local_search(dist, order[:k])
        rep = min(1.0, dist[:, sel].min(axis=1).mean() / norm)
        over = max(0.0, len(sel) / n - rho) / (2.0 * rho)
        val = (1.0 - BUDGET_LAMBDA) * rep + BUDGET_LAMBDA * min(1.0, over)
        if val < best_val:
            best_val, best_sel = val, sel
    return best_sel


# ---------------------------------------------------------------------------
# Timed runner — do NOT remove the val_loss / peak_mem_mb print lines
# ---------------------------------------------------------------------------
def run() -> None:
    deadline = time.time() + TIME_BUDGET_SECONDS

    def algorithm(sizes: list[int], sig, fps: float) -> list[int]:
        return cadre(sizes, sig, fps, rho=TARGET_KEYFRAME_RATIO, kmax_mul=3.0, warmup=0)

    val_loss = 1.0
    iterations = 0
    while time.time() < deadline:
        val_loss = evaluate(algorithm)
        iterations += 1

    print(f"val_loss: {val_loss:.6f}")
    print("peak_mem_mb: 0")  # size-only algorithm, no model — memory is not a concern
    print(f"iterations: {iterations}", file=sys.stderr)


if __name__ == "__main__":
    run()
