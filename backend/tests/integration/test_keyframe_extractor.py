"""Integration test for KeyframeExtractor end-to-end with a synthetic video.

Builds an in-memory video (no fixture files committed to the repo) with a
known complexity pattern so we can assert deterministic extraction behaviour:
  - frames 0-4: flat (solid gray) → minimal JPEG size, low steepness
  - frames 5-9: noisy (random pixels) → large JPEG size, high steepness at frame 5

JPEG size of a solid-color frame is near-constant regardless of luminance value
(DCT of a flat block collapses to one DC coefficient). Random-pixel frames have
high spatial frequency → hard to compress → large JPEG → steepness fires.
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import av
import pytest

from keyframe_extraction.extractor import KeyframeExtractor

_RNG_SEED = 42


def _flat_frame(pts: int) -> av.VideoFrame:
    frame = av.VideoFrame(64, 64, "yuv420p")
    for plane in frame.planes:
        plane.update(bytes([128]) * plane.buffer_size)
    frame.pts = pts
    return frame


def _noisy_frame(pts: int, rng: random.Random) -> av.VideoFrame:
    frame = av.VideoFrame(64, 64, "yuv420p")
    for plane in frame.planes:
        plane.update(bytes([rng.randint(0, 255) for _ in range(plane.buffer_size)]))
    frame.pts = pts
    return frame


def _make_synthetic_video(path: Path, n_frames: int = 10) -> None:
    rng = random.Random(_RNG_SEED)
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=25)
        stream.width = 64
        stream.height = 64
        stream.pix_fmt = "yuv420p"
        stream.options = {"crf": "0"}

        for i in range(n_frames):
            frame = (
                _flat_frame(pts=i)
                if i < n_frames // 2
                else _noisy_frame(pts=i, rng=rng)
            )
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("video") / "test.mp4"
    _make_synthetic_video(path, n_frames=10)
    return path


def test_extract_keyframes_returns_candidates(synthetic_video: Path) -> None:
    # rho=0.3 on a 10-frame video → k=3 candidates; warmup_seconds=0 avoids
    # excluding all frames from a short synthetic clip.
    extractor = KeyframeExtractor(rho=0.3, warmup_seconds=0.0)
    candidates = extractor.extract_keyframes(synthetic_video)
    assert len(candidates) >= 1


def test_extract_keyframes_candidates_are_in_temporal_order(
    synthetic_video: Path,
) -> None:
    # U-CESE Algorithm 1 returns indices sorted by frame position, not steepness rank.
    extractor = KeyframeExtractor(rho=0.3, warmup_seconds=0.0)
    candidates = extractor.extract_keyframes(synthetic_video)
    indices = [c.frame_index for c in candidates]
    assert indices == sorted(indices)


def test_extract_keyframes_detects_complexity_boundary(synthetic_video: Path) -> None:
    extractor = KeyframeExtractor(rho=0.3, warmup_seconds=0.0)
    candidates = extractor.extract_keyframes(synthetic_video)
    indices = [c.frame_index for c in candidates]
    # flat→noisy jump at frame 5 must produce a large steepness, triggering selection
    assert any(4 <= idx <= 6 for idx in indices)


def test_extract_keyframes_all_timestamps_are_non_negative(
    synthetic_video: Path,
) -> None:
    extractor = KeyframeExtractor(rho=0.3, warmup_seconds=0.0)
    candidates = extractor.extract_keyframes(synthetic_video)
    assert all(c.timestamp_seconds >= 0 for c in candidates)


def test_extract_keyframes_jpeg_sizes_are_positive(synthetic_video: Path) -> None:
    extractor = KeyframeExtractor(rho=0.3, warmup_seconds=0.0)
    candidates = extractor.extract_keyframes(synthetic_video)
    assert all(c.jpeg_size > 0 for c in candidates)
