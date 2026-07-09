"""DAKE-VBS experiment — the agent edits ONLY this file.

Baseline: U-CESE steepness algorithm (Algorithm 1 from the paper), rho-based selection.

Experiment log (newest first):
  - [baseline] rho=0.02, window=3, no floor sampling

To run:
    cd backend
    uv run python auto-research/dake-vbs/train.py > auto-research/dake-vbs/run.log 2>&1
"""
from __future__ import annotations

import math
import sys
import time

sys.path.insert(0, "src")  # so keyframe_extraction.* imports work

from prepare import TIME_BUDGET_SECONDS, SEED, evaluate  # noqa: E402


# ---------------------------------------------------------------------------
# Algorithm — edit this section freely
# ---------------------------------------------------------------------------

def calculate_steepness(s_i: float, s_j: float, i: int, j: int, s_max: float) -> float:
    """Normalised rate of change between two frames (U-CESE eq. 4.1)."""
    if s_max <= 0:
        return 0.0
    delta = 100.0 * abs((s_j - s_i) / s_max)
    d = abs(j - i)
    if d == 0:
        return 1.0 if delta > 0 else 0.0
    return delta / math.sqrt(d**2 + delta**2)


def dake_vbs(
    sizes: list[int],
    *,
    rho: float = 0.02,
    window: int = 3,
    warmup: int = 0,
) -> list[int]:
    """Baseline U-CESE Algorithm 1: select top rho*n frames by steepness.

    Parameters
    ----------
    sizes   : per-frame JPEG sizes
    rho     : fraction of frames to select (0 < rho <= 1)
    window  : forward neighbour window for steepness averaging
    warmup  : skip the first N frames (I-frame codec transient avoidance)
    """
    n = len(sizes)
    if n < 2:
        return []

    s_max = max(sizes)
    scored: list[tuple[int, float]] = []
    for i in range(n - 1):
        total = 0.0
        count = 0
        for j in range(i + 1, min(n, i + window + 1)):
            total += calculate_steepness(sizes[i], sizes[j], i, j, s_max)
            count += 1
        scored.append((i, total / count if count > 0 else 0.0))

    eligible = [(idx, s) for idx, s in scored if idx >= warmup]
    if not eligible:
        return []

    eligible.sort(key=lambda x: x[1], reverse=True)
    k = max(1, int(rho * n))
    selected = sorted(idx for idx, _ in eligible[:k])
    return selected


# ---------------------------------------------------------------------------
# Timed runner — do NOT remove the val_loss / peak_mem_mb print lines
# ---------------------------------------------------------------------------

def run() -> None:
    deadline = time.time() + TIME_BUDGET_SECONDS

    # Wrap algorithm so evaluate() can call it with just (sizes,).
    def algorithm(sizes: list[int]) -> list[int]:
        return dake_vbs(sizes, rho=0.02, window=3, warmup=0)

    # Repeat evaluation until the time budget is exhausted (ensures
    # each experiment consumes the same wall-clock slot).
    val_loss = 1.0
    iterations = 0
    while time.time() < deadline:
        val_loss = evaluate(algorithm)
        iterations += 1

    print(f"val_loss: {val_loss:.6f}")
    print(f"peak_mem_mb: 0")   # no GPU/model — memory not a concern
    print(f"iterations: {iterations}", file=sys.stderr)


if __name__ == "__main__":
    run()
