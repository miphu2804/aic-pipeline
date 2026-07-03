"""Small ffmpeg/ffprobe adapter used by the keyframe selector."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when ffmpeg or ffprobe cannot complete a command."""


@dataclass(frozen=True)
class DetectedScene:
    timestamp_seconds: float
    score: float | None


_METADATA_FRAME_RE = re.compile(
    r"frame:\s*(?P<frame>\d+)\s+pts:\s*(?P<pts>-?\d+)\s+"
    r"pts_time:\s*(?P<time>[-+0-9.eE]+)"
)
_METADATA_SCORE_RE = re.compile(r"lavfi\.scene_score=(?P<score>[-+0-9.eE]+)")
_SHOWINFO_RE = re.compile(r"showinfo.*pts_time:\s*(?P<time>[-+0-9.eE]+)")


def ensure_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise FFmpegError(f"required binary not found on PATH: {binary}")


def probe_duration(
    video_path: Path,
    *,
    ffprobe_binary: str = "ffprobe",
) -> float | None:
    ensure_binary(ffprobe_binary)
    command = [
        ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    result = _run(command)
    payload = json.loads(result.stdout or "{}")
    duration = payload.get("format", {}).get("duration")
    if duration in {None, "N/A"}:
        return None
    return float(duration)


def detect_scene_changes(
    video_path: Path,
    *,
    threshold: float,
    ffmpeg_binary: str = "ffmpeg",
) -> list[DetectedScene]:
    """Return scene-change timestamps detected by ffmpeg's scene score."""

    ensure_binary(ffmpeg_binary)
    filter_graph = (
        f"select=gt(scene\\,{threshold}),metadata=print:file=-,showinfo"
    )
    command = [
        ffmpeg_binary,
        "-nostdin",
        "-hide_banner",
        "-i",
        str(video_path),
        "-vf",
        filter_graph,
        "-an",
        "-f",
        "null",
        "-",
    ]
    result = _run(command)
    return _parse_scene_output(f"{result.stdout}\n{result.stderr}")


def extract_frame_at(
    video_path: Path,
    *,
    timestamp_seconds: float,
    output_path: Path,
    image_quality: int = 2,
    overwrite: bool = False,
    ffmpeg_binary: str = "ffmpeg",
) -> Path:
    ensure_binary(ffmpeg_binary)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return output_path

    attempts = _timestamp_attempts(timestamp_seconds)
    last_error: FFmpegError | None = None
    for timestamp in attempts:
        command = [
            ffmpeg_binary,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-ss",
            f"{timestamp:.3f}",
            "-frames:v",
            "1",
            "-q:v",
            str(image_quality),
            "-y" if overwrite else "-n",
            str(output_path),
        ]
        try:
            _run(command)
        except FFmpegError as exc:
            last_error = exc
            continue
        if output_path.exists():
            return output_path

    if last_error is not None:
        raise last_error
    raise FFmpegError(f"ffmpeg did not create frame: {output_path}")


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-8:]
        detail = "\n".join(tail)
        raise FFmpegError(f"command failed ({result.returncode}): {detail}")
    return result


def _timestamp_attempts(timestamp_seconds: float) -> list[float]:
    attempts = [max(0.0, timestamp_seconds)]
    for offset in (0.25, 0.5, 1.0):
        fallback = max(0.0, timestamp_seconds - offset)
        if fallback not in attempts:
            attempts.append(fallback)
    return attempts


def _parse_scene_output(output: str) -> list[DetectedScene]:
    scenes: list[DetectedScene] = []
    pending_timestamp: float | None = None
    pending_score: float | None = None
    showinfo_timestamps: list[float] = []

    for line in output.splitlines():
        frame_match = _METADATA_FRAME_RE.search(line)
        if frame_match:
            if pending_timestamp is not None:
                scenes.append(DetectedScene(pending_timestamp, pending_score))
            pending_timestamp = float(frame_match.group("time"))
            pending_score = None
            continue

        score_match = _METADATA_SCORE_RE.search(line)
        if score_match and pending_timestamp is not None:
            pending_score = float(score_match.group("score"))
            continue

        showinfo_match = _SHOWINFO_RE.search(line)
        if showinfo_match:
            showinfo_timestamps.append(float(showinfo_match.group("time")))

    if pending_timestamp is not None:
        scenes.append(DetectedScene(pending_timestamp, pending_score))

    if not scenes:
        scenes = [DetectedScene(timestamp, None) for timestamp in showinfo_timestamps]

    return _dedupe_scenes(scenes)


def _dedupe_scenes(scenes: list[DetectedScene]) -> list[DetectedScene]:
    deduped: list[DetectedScene] = []
    seen: set[int] = set()
    for scene in sorted(scenes, key=lambda item: item.timestamp_seconds):
        bucket = int(round(scene.timestamp_seconds * 1000))
        if bucket in seen:
            continue
        seen.add(bucket)
        deduped.append(scene)
    return deduped
