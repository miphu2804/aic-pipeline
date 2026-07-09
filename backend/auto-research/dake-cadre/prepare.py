"""DAKE-CADRE Experiment Harness — READ-ONLY for the agent (the referee).

This replaces the earlier synthetic dake-vbs referee (which saturated at
val_loss=0.0) with a metric grounded in REAL video data: the MSR-VTT clips in
``data/msrvtt/videos/``.

Three clearly-marked blocks (only a human edits this file):

  (A) DATA     — sample K real MSR-VTT clips; cache per-frame JPEG sizes (the DAKE
                 input signal) and per-frame content thumbnails (the metric's
                 ground-truth descriptor).  Cached once to disk.
  (B) METRIC   — representativeness-under-budget.  A keyframe set is good when every
                 frame is close (in thumbnail feature space) to some selected
                 keyframe, using only a small fraction of frames.  This is the
                 classic unsupervised video-summarisation objective (cf. VSUMM).
  (C) CONSTANTS — TIME_BUDGET_SECONDS, SEED, PRIMARY_DIRECTION, budget target.

Why this metric cannot be trivially saturated
---------------------------------------------
The algorithm (train.py) only sees per-frame JPEG *sizes* — a cheap proxy that is
correlated with, but not equal to, visual content change.  The metric measures
representativeness in *thumbnail* space.  So there is an inherent performance floor:
no size-only selector can perfectly minimise content representativeness error.  The
loop's job is to get as close to that floor as possible, cheaply.

val_loss = (1 - LAMBDA) * representativeness_error_norm  +  LAMBDA * budget_penalty
PRIMARY_DIRECTION = "min"   → lower is better.
"""

from __future__ import annotations

import glob
import os
import pickle
import random
import sys
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

import av
import numpy as np

# ---------------------------------------------------------------------------
# (C) CONSTANTS — do NOT change these in train.py
# ---------------------------------------------------------------------------
TIME_BUDGET_SECONDS: int = 25
SEED: int = 42
PRIMARY_DIRECTION: str = "min"

NUM_VIDEOS: int = 60  # how many MSR-VTT clips form the benchmark
MAX_FRAMES: int = 320  # cap per clip (stride-subsample longer clips)
THUMB_GRID: int = 8  # 8x8x3 = 192-d content descriptor — the METRIC feature
SIG_GRID: int = 4  # 4x4x3 = 48-d coarse signature handed to the ALGORITHM
JPEG_QSCALE: int = 2  # ffmpeg mjpeg qscale (matches production extractor)

# Keyframe budget: selecting more than this fraction of frames is penalised.
TARGET_KEYFRAME_RATIO: float = 0.03
# Convex weight between the two objectives (0 = pure representativeness,
# 1 = pure budget).  0.35 keeps representativeness dominant while making the
# frame count matter.
BUDGET_LAMBDA: float = 0.35

_HERE = os.path.dirname(os.path.abspath(__file__))
_VIDEO_GLOB = os.path.join(_HERE, "..", "..", "..", "data", "msrvtt", "videos", "*.mp4")
_CACHE_PATH = os.path.join(
    _HERE,
    "cache",
    f"feats_k{NUM_VIDEOS}_m{MAX_FRAMES}_t{THUMB_GRID}_g{SIG_GRID}_s{SEED}.pkl",
)


# ---------------------------------------------------------------------------
# (A) DATA — real MSR-VTT clips, cached once
# ---------------------------------------------------------------------------
@dataclass
class Clip:
    name: str
    sizes: np.ndarray  # int32 [n]   — per-frame JPEG byte size (the paper's DAKE input)
    sig: np.ndarray  # float32 [n, 48] — per-frame coarse colour signature (CADRE input)
    feats: (
        np.ndarray
    )  # float32 [n, 192] — per-frame 8x8 thumbnail (METRIC ground truth)
    fps: float
    norm: float  # per-clip representativeness normaliser (feature spread)


def _thumbnail(rgb: np.ndarray, g: int = THUMB_GRID) -> np.ndarray:
    """Downsample an HxWx3 uint8 frame to a normalised g*g*3 descriptor.

    A tiny thumbnail preserves coarse colour *and* spatial layout, which makes it a
    strong cheap signature for near-duplicate / representativeness comparisons.
    """
    rows = np.stack([r.mean(axis=0) for r in np.array_split(rgb, g, axis=0)])
    small = np.stack([c.mean(axis=1) for c in np.array_split(rows, g, axis=1)], axis=1)
    return (small.reshape(-1) / 255.0).astype(np.float32)


def _encode_clip(path: str) -> Clip | None:
    """Decode one clip → (JPEG sizes, thumbnails).  Returns None on failure."""
    with av.open(path) as container:
        stream = container.streams.video[0]
        cc = stream.codec_context
        fps = float(stream.average_rate) if stream.average_rate else 25.0

        n_total = stream.frames or 0
        stride = max(1, (n_total + MAX_FRAMES - 1) // MAX_FRAMES) if n_total else 1

        encoder = av.CodecContext.create("mjpeg", "w")
        encoder.width, encoder.height = cc.width, cc.height
        encoder.pix_fmt = "yuvj420p"
        encoder.time_base = Fraction(1, 1000)
        encoder.options = {"qscale": str(JPEG_QSCALE)}

        sizes: list[int] = []
        feats: list[np.ndarray] = []
        sigs: list[np.ndarray] = []
        for i, frame in enumerate(container.decode(stream)):
            if i % stride:
                continue
            jf = frame.reformat(format="yuvj420p")
            jf.pts = len(sizes)
            jf.time_base = encoder.time_base
            sizes.append(sum(pk.size for pk in encoder.encode(jf)))
            rgb = frame.to_ndarray(format="rgb24")
            feats.append(_thumbnail(rgb, THUMB_GRID))  # metric feature
            sigs.append(_thumbnail(rgb, SIG_GRID))  # coarse signature for the algorithm

    if len(sizes) < 4:
        return None

    feat_arr = np.stack(feats)
    spread = float(np.linalg.norm(feat_arr - feat_arr.mean(axis=0), axis=1).mean())
    return Clip(
        name=os.path.basename(path),
        sizes=np.asarray(sizes, dtype=np.int32),
        sig=np.stack(sigs),
        feats=feat_arr,
        fps=fps / stride,
        norm=spread if spread > 1e-6 else 1.0,
    )


def _build_clips() -> list[Clip]:
    paths = sorted(glob.glob(_VIDEO_GLOB))
    if not paths:
        raise FileNotFoundError(f"No MSR-VTT videos found at {_VIDEO_GLOB}")
    rng = random.Random(SEED)
    chosen = rng.sample(paths, min(NUM_VIDEOS, len(paths)))
    clips: list[Clip] = []
    for i, p in enumerate(sorted(chosen)):
        clip = _encode_clip(p)
        if clip is not None:
            clips.append(clip)
        print(f"  [{i + 1}/{len(chosen)}] {os.path.basename(p)}", file=sys.stderr)
    return clips


def _to_records(clips: list[Clip]) -> list[dict]:
    return [
        {
            "name": c.name,
            "sizes": c.sizes,
            "sig": c.sig,
            "feats": c.feats,
            "fps": c.fps,
            "norm": c.norm,
        }
        for c in clips
    ]


def load_clips() -> list[Clip]:
    """Load the cached benchmark clips, building + caching them on first call.

    The cache stores plain dicts (builtins + numpy arrays only) so it unpickles
    identically whether prepare is imported as a module or run as ``__main__``.
    """
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, "rb") as fh:
            records = pickle.load(fh)
        return [Clip(**r) for r in records]
    clips = _build_clips()
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    with open(_CACHE_PATH, "wb") as fh:
        pickle.dump(_to_records(clips), fh)
    return clips


# Materialised once at import (fast after the cache exists).
CLIPS: list[Clip] = load_clips()


# ---------------------------------------------------------------------------
# (B) METRIC
# ---------------------------------------------------------------------------
def _representativeness_error(feats: np.ndarray, selected: list[int]) -> float:
    """Mean over all frames of the distance to the nearest selected keyframe."""
    sel = feats[selected]  # [k, d]
    # Squared euclidean via (a-b)^2 = |a|^2 + |b|^2 - 2 a.b, then min over keyframes.
    d2 = (
        (feats * feats).sum(axis=1, keepdims=True)
        - 2.0 * feats @ sel.T
        + (sel * sel).sum(axis=1)[None, :]
    )
    nearest = np.sqrt(np.clip(d2.min(axis=1), 0.0, None))
    return float(nearest.mean())


def evaluate(
    algorithm: Callable[[list[int], np.ndarray, float], list[int]],
    clips: list[Clip] | None = None,
) -> float:
    """Run ``algorithm`` on every clip and return val_loss (lower is better).

    Parameters
    ----------
    algorithm:
        Callable ``(sizes, sig, fps) -> selected_frame_indices``:
          * ``sizes`` — per-frame JPEG byte sizes (the paper's DAKE signal),
          * ``sig``   — per-frame coarse colour signature, float32 [n, 48]
            (a cheap descriptor the production decoder can compute for free),
          * ``fps``   — the (possibly strided) frame rate.
        The algorithm never sees the 8x8 metric feature, so a coarse-signature
        selector still faces a real generalisation gap to the representativeness floor.
    """
    if clips is None:
        clips = CLIPS

    losses: list[float] = []
    for clip in clips:
        n = int(clip.sizes.shape[0])
        selected = algorithm(clip.sizes.tolist(), clip.sig, clip.fps)
        # Sanitise: unique, in-range, sorted.
        selected = sorted({i for i in selected if 0 <= i < n})

        if not selected:
            losses.append(1.0 - BUDGET_LAMBDA)  # empty output = worst coverage
            continue

        rep = _representativeness_error(clip.feats, selected) / clip.norm
        rep = min(1.0, max(0.0, rep))

        used_ratio = len(selected) / n
        # Linear ramp: no penalty at/under target, full penalty at 3x target.
        over = max(0.0, used_ratio - TARGET_KEYFRAME_RATIO) / (
            2.0 * TARGET_KEYFRAME_RATIO
        )
        budget_penalty = min(1.0, over)

        losses.append((1.0 - BUDGET_LAMBDA) * rep + BUDGET_LAMBDA * budget_penalty)

    return float(np.mean(losses)) if losses else 1.0


# ---------------------------------------------------------------------------
# Sanity-check when run directly: verify the metric orders selectors sensibly.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tot_frames = sum(int(c.sizes.shape[0]) for c in CLIPS)
    print(
        f"loaded {len(CLIPS)} clips, {tot_frames} frames "
        f"(avg {tot_frames / max(len(CLIPS), 1):.0f}/clip)"
    )

    def sel_none(sizes, sig, fps):
        return []

    def sel_all(sizes, sig, fps):
        return list(range(len(sizes)))

    def sel_first(sizes, sig, fps):
        return [0]

    def sel_uniform(sizes, sig, fps):
        n = len(sizes)
        k = max(1, int(TARGET_KEYFRAME_RATIO * n))
        step = max(1, n // k)
        return list(range(step // 2, n, step))

    def sel_random(sizes, sig, fps):
        n = len(sizes)
        k = max(1, int(TARGET_KEYFRAME_RATIO * n))
        rng = random.Random(SEED)
        return sorted(rng.sample(range(n), min(k, n)))

    for name, fn in [
        ("none      ", sel_none),
        ("all_frames", sel_all),
        ("first_only", sel_first),
        ("random@3% ", sel_random),
        ("uniform@3%", sel_uniform),
    ]:
        print(f"  {name}: val_loss={evaluate(fn):.4f}")
    print("prepare.py OK — real MSR-VTT referee ready.")
