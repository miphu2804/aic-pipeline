"""Benchmark: the paper's DAKE (U-CESE) vs. CADRE, logged to MLflow.

Runs both PRODUCTION selectors on the 60-clip MSR-VTT benchmark that the referee
(``prepare.py``) built, scores them with the same representativeness-under-budget
metric, and records one MLflow run per algorithm under the ``dake-vs-cadre``
experiment so the two can be compared side by side.

Run:
    cd backend
    uv run python auto-research/dake-cadre/benchmark.py
    uv run mlflow ui --backend-store-uri sqlite:///auto-research/dake-cadre/mlflow.db
"""

from __future__ import annotations

import os
import sys
import time

import mlflow
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "src"))  # production package
sys.path.insert(0, _HERE)  # prepare (the referee)

# The imports below must follow the sys.path setup above (hence isort is disabled).
# isort: off
from prepare import (
    BUDGET_LAMBDA,
    CLIPS,
    NUM_VIDEOS,
    SIG_GRID,
    TARGET_KEYFRAME_RATIO,
    _representativeness_error,
)
from keyframe_extraction.cadre import select_keyframes as cadre_select
from keyframe_extraction.dake import select_keyframes as dake_select

# isort: on


def _score(clip, indices: list[int]) -> dict:
    """Per-clip metrics using the referee's representativeness-under-budget formula."""
    n = int(clip.sizes.shape[0])
    indices = sorted({i for i in indices if 0 <= i < n})
    if not indices:
        return {
            "val_loss": 1.0 - BUDGET_LAMBDA,
            "rep_norm": 1.0,
            "budget_penalty": 0.0,
            "keyframes": 0,
            "used_ratio": 0.0,
        }
    rep = min(1.0, _representativeness_error(clip.feats, indices) / clip.norm)
    used = len(indices) / n
    over = max(0.0, used - TARGET_KEYFRAME_RATIO) / (2.0 * TARGET_KEYFRAME_RATIO)
    penalty = min(1.0, over)
    return {
        "val_loss": (1.0 - BUDGET_LAMBDA) * rep + BUDGET_LAMBDA * penalty,
        "rep_norm": rep,
        "budget_penalty": penalty,
        "keyframes": len(indices),
        "used_ratio": used,
    }


def _run_algorithm(name: str, selector) -> dict:
    """Apply ``selector`` (clip -> indices) across all clips; time it and aggregate."""
    per_clip = []
    total_select_s = 0.0
    for clip in CLIPS:
        t0 = time.perf_counter()
        indices = selector(clip)
        total_select_s += time.perf_counter() - t0
        per_clip.append(_score(clip, indices))

    agg = {
        f"{k}_mean": float(np.mean([c[k] for c in per_clip]))
        for k in ("val_loss", "rep_norm", "budget_penalty", "keyframes", "used_ratio")
    }
    agg["select_ms_per_clip"] = 1000.0 * total_select_s / len(CLIPS)
    return {"name": name, "aggregate": agg, "per_clip": per_clip}


def main() -> None:
    # DAKE (paper): top-rho% by JPEG-size steepness.  CADRE: representative frames
    # from the cheap colour signature.  Same keyframe budget for a fair comparison.
    algorithms = {
        "dake-ucese": lambda clip: dake_select(
            clip.sizes.tolist(), rho=TARGET_KEYFRAME_RATIO
        ),
        "cadre": lambda clip: cadre_select(clip.sig, ratio=TARGET_KEYFRAME_RATIO),
    }

    # MLflow 3 requires a database backend; keep everything local under the experiment.
    mlflow.set_tracking_uri(f"sqlite:///{os.path.join(_HERE, 'mlflow.db')}")
    experiment = "dake-vs-cadre"
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(
            experiment, artifact_location=f"file:{os.path.join(_HERE, 'mlartifacts')}"
        )
    mlflow.set_experiment(experiment)

    results = {}
    for name, selector in algorithms.items():
        out = _run_algorithm(name, selector)
        results[name] = out
        with mlflow.start_run(run_name=name):
            mlflow.log_params(
                {
                    "algorithm": name,
                    "keyframe_ratio": TARGET_KEYFRAME_RATIO,
                    "signature_grid": SIG_GRID if name == "cadre" else "n/a",
                    "signal": (
                        "colour-signature" if name == "cadre" else "jpeg-size-steepness"
                    ),
                    "num_videos": len(CLIPS),
                    "benchmark": f"MSR-VTT x{NUM_VIDEOS}",
                }
            )
            mlflow.log_metrics(out["aggregate"])
            mlflow.log_dict({"per_clip": out["per_clip"]}, "per_clip.json")

    _print_table(results)


def _print_table(results: dict) -> None:
    dake, cadre = results["dake-ucese"]["aggregate"], results["cadre"]["aggregate"]
    rows = [
        ("val_loss (lower=better)", "val_loss_mean", True),
        ("representativeness err", "rep_norm_mean", True),
        ("budget penalty", "budget_penalty_mean", True),
        ("keyframes / clip", "keyframes_mean", False),
        ("used ratio", "used_ratio_mean", False),
        ("select ms / clip", "select_ms_per_clip", False),
    ]
    print("\n" + "=" * 62)
    print(f"{'metric':<26}{'DAKE (U-CESE)':>13}{'CADRE':>11}{'Δ':>10}")
    print("-" * 62)
    for label, key, improves in rows:
        d, c = dake[key], cadre[key]
        delta = f"{c - d:+.4f}" if abs(c - d) < 100 else f"{c - d:+.1f}"
        print(f"{label:<26}{d:>13.4f}{c:>11.4f}{delta:>10}")
    drop = (
        100.0 * (dake["val_loss_mean"] - cadre["val_loss_mean"]) / dake["val_loss_mean"]
    )
    print("-" * 62)
    print(f"CADRE reduces val_loss by {drop:.1f}% vs the paper's DAKE.")
    print(
        "MLflow: uv run mlflow ui --backend-store-uri "
        "sqlite:///auto-research/dake-cadre/mlflow.db"
    )
    print("=" * 62)


if __name__ == "__main__":
    main()
