"""DAKE-VBS Experiment Harness — READ-ONLY for the agent.

This is the referee:
  (A) DATA     — synthetic multi-scene videos with known ground-truth event frames
  (B) METRIC   — scene_coverage_score: recall of GT events minus budget penalty
  (C) CONSTANTS — TIME_BUDGET_SECONDS, SEED, PRIMARY_DIRECTION

Ground truth model
------------------
Each scenario has a list of "ground-truth event frames" — the exact frame indices
where a scene change (hard cut or significant content change) occurs.  A DAKE variant
"covers" an event if it selects at least one keyframe within ±COVERAGE_TOLERANCE_FRAMES
of the GT event index.

val_loss = 1.0 - scene_coverage_score
PRIMARY_DIRECTION = "min"  → minimize val_loss (maximize coverage)
"""
from __future__ import annotations

import math
import random
import struct
import time
from dataclasses import dataclass
from typing import Callable

# ---------------------------------------------------------------------------
# (C) CONSTANTS — do not change these in train.py
# ---------------------------------------------------------------------------
TIME_BUDGET_SECONDS: int = 30
SEED: int = 42
PRIMARY_DIRECTION: str = "min"

# A keyframe budget: if the algorithm selects more than this fraction of frames,
# add a penalty proportional to the excess.
KEYFRAME_BUDGET_RATIO: float = 0.05
BUDGET_PENALTY_WEIGHT: float = 0.15  # max penalty deducted from coverage score

# An event is "covered" if a keyframe lands within this many frames of the GT event.
COVERAGE_TOLERANCE_FRAMES: int = 3  # ~0.12 s at 25 fps

# ---------------------------------------------------------------------------
# (A) DATA — synthetic frame sequences with deterministic ground truth
# ---------------------------------------------------------------------------

def _flat_region(n: int, base_size: int = 800, noise: int = 20, rng: random.Random = None) -> list[int]:
    """Simulate a static shot: JPEG sizes vary only slightly."""
    rng = rng or random.Random(SEED)
    return [base_size + rng.randint(-noise, noise) for _ in range(n)]


def _noisy_region(n: int, base_size: int = 5000, noise: int = 500, rng: random.Random = None) -> list[int]:
    """Simulate a high-motion shot (action, cooking): large, variable JPEG sizes."""
    rng = rng or random.Random(SEED)
    return [base_size + rng.randint(-noise, noise) for _ in range(n)]


def _gradient_region(n: int, start: int, end: int) -> list[int]:
    """Simulate a gradual transition (pan, zoom, fade): linearly changing size."""
    return [int(start + (end - start) * i / max(n - 1, 1)) for i in range(n)]


@dataclass
class Scenario:
    name: str
    sizes: list[int]          # per-frame JPEG sizes (the DAKE input signal)
    gt_events: list[int]      # ground-truth event frame indices to cover
    fps: float = 25.0


def build_scenarios() -> list[Scenario]:
    """Construct deterministic multi-scene sequences mimicking AIC video types."""
    rng = random.Random(SEED)
    scenarios: list[Scenario] = []

    # --- Scenario 1: news bulletin with hard cuts ---
    # anchor (flat) → clip (noisy) → anchor (flat) → report (gradient) → anchor (flat)
    segs_1: list[tuple[list[int], list[int]]] = [
        (_flat_region(60, 900, 30, rng), []),           # frames 0–59, anchor
        (_noisy_region(5, 5500, 600, rng), [60]),       # frames 60–64, hard cut → clip
        (_flat_region(40, 1000, 40, rng), []),           # frames 65–104, back to anchor
        (_noisy_region(30, 4800, 700, rng), [105]),      # frames 105–134, hard cut → report
        (_gradient_region(20, 4800, 1200), [135]),       # frames 135–154, slow fade out
        (_flat_region(50, 850, 25, rng), []),            # frames 155–204, anchor closes
    ]
    sizes_1: list[int] = []
    events_1: list[int] = []
    for seg, evts in segs_1:
        events_1.extend([e for e in evts])
        sizes_1.extend(seg)
    scenarios.append(Scenario("news_hard_cuts", sizes_1, events_1))

    # --- Scenario 2: cooking video — frequent small changes ---
    # prep (moderate) → chop (high motion) → stir (high) → plating (moderate) → finish
    segs_2 = [
        (_flat_region(30, 2000, 300, rng), []),
        (_noisy_region(20, 6000, 800, rng), [30]),
        (_flat_region(15, 1800, 200, rng), [50]),
        (_noisy_region(25, 7000, 1000, rng), [65]),
        (_flat_region(10, 1600, 150, rng), [90]),
        (_noisy_region(30, 5500, 700, rng), [100]),
        (_flat_region(20, 2200, 250, rng), [130]),
    ]
    sizes_2: list[int] = []
    events_2: list[int] = []
    for seg, evts in segs_2:
        events_2.extend(evts)
        sizes_2.extend(seg)
    scenarios.append(Scenario("cooking_frequent_cuts", sizes_2, events_2, fps=25.0))

    # --- Scenario 3: long static anchor + single late cut (coverage stress-test) ---
    # 5 minutes of anchor talk, then one cut at the very end
    sizes_3 = _flat_region(300, 950, 30, rng) + _noisy_region(30, 5000, 500, rng)
    events_3 = [300]  # single event very late
    scenarios.append(Scenario("long_static_single_event", sizes_3, events_3, fps=25.0))

    # --- Scenario 4: online lecture — periodic content changes ---
    # slide show: slide stays flat for 8–15 seconds then jumps on slide change
    sizes_4: list[int] = []
    events_4: list[int] = []
    cursor = 0
    rng2 = random.Random(SEED + 1)
    for _ in range(8):  # 8 slides
        duration = rng2.randint(8, 15) * 25  # frames at 25 fps
        if cursor > 0:
            events_4.append(cursor)
        # slide is mostly flat with tiny variations; slide transition is a noisy burst
        sizes_4 += _noisy_region(3, 4000, 800, rng2) + _flat_region(duration - 3, 1100, 50, rng2)
        cursor += duration
    scenarios.append(Scenario("lecture_slides", sizes_4, events_4, fps=25.0))

    return scenarios


# Pre-build and cache so train.py can import directly.
SCENARIOS: list[Scenario] = build_scenarios()


# ---------------------------------------------------------------------------
# (B) METRIC
# ---------------------------------------------------------------------------

def evaluate(
    algorithm: Callable[[list[int]], list[int]],
    scenarios: list[Scenario] | None = None,
) -> float:
    """Run algorithm on all scenarios and return val_loss = 1 - coverage_score.

    Parameters
    ----------
    algorithm:
        Callable that receives a list of per-frame JPEG sizes and returns a list
        of selected frame indices (sorted, 0-based).
    scenarios:
        Defaults to the module-level SCENARIOS list.

    Returns
    -------
    float
        val_loss in [0, 1].  Lower is better.
    """
    if scenarios is None:
        scenarios = SCENARIOS

    total_events = 0
    covered_events = 0
    total_frames = 0
    total_selected = 0

    for sc in scenarios:
        selected = algorithm(sc.sizes)
        selected_set: set[int] = set(selected)
        n = len(sc.sizes)

        for gt in sc.gt_events:
            total_events += 1
            lo = max(0, gt - COVERAGE_TOLERANCE_FRAMES)
            hi = min(n - 1, gt + COVERAGE_TOLERANCE_FRAMES)
            if any(f in selected_set for f in range(lo, hi + 1)):
                covered_events += 1

        total_frames += n
        total_selected += len(selected)

    recall = covered_events / total_events if total_events > 0 else 0.0

    # Budget penalty: if over budget, penalise proportionally.
    used_ratio = total_selected / total_frames if total_frames > 0 else 0.0
    over_budget = max(0.0, used_ratio - KEYFRAME_BUDGET_RATIO)
    budget_penalty = min(BUDGET_PENALTY_WEIGHT, over_budget * BUDGET_PENALTY_WEIGHT / KEYFRAME_BUDGET_RATIO)

    coverage_score = max(0.0, recall - budget_penalty)
    return 1.0 - coverage_score


# ---------------------------------------------------------------------------
# Sanity-check when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    for sc in SCENARIOS:
        print(f"  {sc.name}: {len(sc.sizes)} frames, {len(sc.gt_events)} GT events")

    # Naive oracle: select exactly the GT event frames.
    def oracle(sizes: list[int], sc: Scenario = None) -> list[int]:
        return sc.gt_events if sc else []

    # Baseline: select every frame (100% budget → penalised).
    def all_frames(sizes: list[int]) -> list[int]:
        return list(range(len(sizes)))

    loss_all = evaluate(all_frames)
    print(f"baseline (all frames): val_loss={loss_all:.4f}")
    print("prepare.py OK — scenarios built, evaluate() works.")
