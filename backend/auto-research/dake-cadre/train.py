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

sys.path.insert(0, "auto-research/dake-cadre")

from prepare import TARGET_KEYFRAME_RATIO, TIME_BUDGET_SECONDS, evaluate  # noqa: E402


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


# ---------------------------------------------------------------------------
# Timed runner — do NOT remove the val_loss / peak_mem_mb print lines
# ---------------------------------------------------------------------------
def run() -> None:
    deadline = time.time() + TIME_BUDGET_SECONDS

    def algorithm(sizes: list[int], fps: float) -> list[int]:
        return dake_ucese(sizes, fps, rho=TARGET_KEYFRAME_RATIO, window=3, warmup=0)

    val_loss = 1.0
    iterations = 0
    while time.time() < deadline:
        val_loss = evaluate(algorithm)
        iterations += 1

    print(f"val_loss: {val_loss:.6f}")
    print("peak_mem_mb: 0")   # size-only algorithm, no model — memory is not a concern
    print(f"iterations: {iterations}", file=sys.stderr)


if __name__ == "__main__":
    run()
