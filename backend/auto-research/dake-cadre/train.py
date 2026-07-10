"""DAKE-CADRE experiment — the agent edits ONLY this file.

Baseline = faithful U-CESE Algorithm 1 (the paper's DAKE): per-frame JPEG-size
steepness, select the top-rho% frames by steepness.  The research goal is to beat
this paper baseline on the real MSR-VTT representativeness metric by adding the
named CADRE module (Change-point Anchored Density-adaptive Representative Extraction).

Experiment log (newest first):
  - [iter 9] DACS arc-length init replaces greedy facility-location + random restarts.
             The clip is split into k segments of equal *accumulated visual change*
             (arc length in signature space) and each segment's centroid frame seeds
             the local search.  This is "dynamic-aware" sampling (busy stretches get
             more segments, static stretches fewer); it ties the champion while
             deleting two components (facility-location + restarts).
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


def _arclength_init(sig: np.ndarray, k: int) -> list[int]:
    """Dynamic-aware init: split the clip into k segments of equal *accumulated visual
    change* and take each segment's centroid-nearest frame.

    Consecutive-frame signature distances are the clip's per-frame "visual velocity".
    Their cumulative sum is a content-arc-length; cutting it into k equal pieces places
    more segments where content moves fast and fewer where it is static — the essence of
    dynamic-aware keyframing.  Each segment contributes its most central (settled) frame,
    which represents that stretch better than the arc-length crossing point.  O(n), no
    distance matrix — a much cheaper seed than greedy facility-location.
    """
    n = len(sig)
    if k <= 1 or n == 0:
        return [0] if n else []
    step = np.zeros(n)
    step[1:] = np.linalg.norm(sig[1:] - sig[:-1], axis=1)
    arc = np.cumsum(step)
    total = float(arc[-1])
    if total <= 1e-9:  # static clip → fall back to uniform temporal spacing
        stride = max(1, n // k)
        return sorted(set(range(stride // 2, n, stride)))
    edges = total * np.arange(k + 1) / k
    seg = np.clip(np.searchsorted(edges, arc, side="right") - 1, 0, k - 1)
    init: list[int] = []
    for s in range(k):
        members = np.where(seg == s)[0]
        if members.size:
            centroid = sig[members].mean(axis=0)
            init.append(
                int(members[np.linalg.norm(sig[members] - centroid, axis=1).argmin()])
            )
    return sorted(set(init))


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


def dacs(
    sizes: list[int],
    sig: np.ndarray,
    fps: float,
    *,
    rho: float = TARGET_KEYFRAME_RATIO,
    kmax_mul: float = 3.0,
    warmup: int = 0,
) -> list[int]:
    """DACS — Dynamic-Aware Coverage Sampling (the iter-9 champion selector).

    Grew out of CADRE inside this loop, one component per iteration; iter 9 swapped the
    greedy facility-location seed for the arc-length seed, so the champion is now
    DACS-based (hence the name). The paper's size-only signal tops out around uniform
    sampling (~0.363); this selects on the cheap 4x4 colour signature instead.

    [iter 4] Budget = ceil(rho * n): keeping the fractional keyframe (int() dropped it)
             lands squarely on the rep/budget optimum instead of overshooting.
    [iter 5] Teitz-Bart local search refines the seed set past its 1-optimal floor.
    [iter 7] Density-adaptive budget: instead of a fixed count, grow the keyframe set
             and keep the size that minimises rep+budget on the signature — busy clips
             get more keyframes, static clips fewer.
    [iter 9] DACS arc-length seeding (``_arclength_init``) replaces greedy
             facility-location + random restarts: the seed already respects the clip's
             temporal/shot structure, so one local search per size matches the old
             multi-restart search with far less machinery.
    """
    n = len(sizes)
    if n < 2:
        return list(range(n))

    sig = np.asarray(sig, dtype=np.float64)
    dist = _pairwise_dist(sig)
    norm = float(np.linalg.norm(sig - sig.mean(axis=0), axis=1).mean()) or 1.0

    kmax = min(n, max(2, math.ceil(rho * n * kmax_mul)))
    best_sel, best_val = [0], math.inf
    for k in range(1, kmax + 1):
        sel = _local_search(dist, _arclength_init(sig, k))
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
        return dacs(sizes, sig, fps, rho=TARGET_KEYFRAME_RATIO, kmax_mul=3.0, warmup=0)

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
