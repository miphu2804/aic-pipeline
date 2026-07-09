import math


def calculate_steepness(s_i: float, s_j: float, i: int, j: int, s_max: float) -> float:
    """Normalized rate of change in JPEG size between two frames (U-CESE 4.1)."""
    if s_max <= 0:
        raise ValueError(f"s_max must be positive, got {s_max}")
    delta = 100.0 * abs((s_j - s_i) / s_max)
    d = abs(j - i)
    if d == 0:
        return 1.0 if delta > 0 else 0.0
    return delta / math.sqrt(d**2 + delta**2)


def compute_frame_steepness(
    sizes: list[int], window: int = 3
) -> list[tuple[int, float]]:
    """Compute per-frame steepness by averaging S(i,j) over a forward window.

    Algorithm 1 from U-CESE: for each frame i, average steepness over
    j = i+1 to min(n, i+window).  Returns (frame_index, steepness) pairs
    for frames 0..n-2 (the last frame has no forward neighbors).
    """
    n = len(sizes)
    if n < 2:
        return []

    s_max = max(sizes)
    result: list[tuple[int, float]] = []
    for i in range(n - 1):
        total = 0.0
        count = 0
        for j in range(i + 1, min(n, i + window + 1)):
            total += calculate_steepness(sizes[i], sizes[j], i, j, s_max)
            count += 1
        result.append((i, total / count))
    return result


def select_keyframes(sizes: list[int], rho: float, warmup: int = 0) -> list[int]:
    """Select keyframe indices using Algorithm 1 from U-CESE paper.

    Computes per-frame steepness using a local forward window, ranks all
    frames globally, and returns the top floor(rho * n) indices sorted by
    frame order.

    ``warmup`` excludes the first N frames from ranking to avoid
    I-frame codec transients that inflate steepness at the start of a
    video.  Those frames are still used when computing steepness of
    later frames — they are only excluded from the candidate pool.
    """
    if not sizes:
        return []

    scored = compute_frame_steepness(sizes)
    if not scored:
        return []

    eligible = [(idx, s) for idx, s in scored if idx >= warmup]
    if not eligible:
        return []

    eligible.sort(key=lambda x: x[1], reverse=True)
    k = max(1, int(rho * len(scored)))
    selected = sorted(idx for idx, _ in eligible[:k])
    return selected
