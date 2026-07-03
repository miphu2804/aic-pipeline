"""Video database discovery and manifest loading."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from keyframes.models import VideoRecord

VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
}

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def load_video_database(
    source: str | Path,
    *,
    recursive: bool = True,
    require_exists: bool = True,
) -> list[VideoRecord]:
    """Load a video database from a directory, JSON manifest, or JSONL manifest."""

    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"video database does not exist: {path}")

    if path.is_dir():
        records = discover_videos(path, recursive=recursive)
    elif path.suffix.lower() == ".jsonl":
        records = _load_jsonl_manifest(path)
    elif path.suffix.lower() == ".json":
        records = _load_json_manifest(path)
    else:
        raise ValueError(
            "video database must be a directory, .json manifest, or .jsonl manifest"
        )

    if require_exists:
        missing = [record.path for record in records if not record.path.exists()]
        if missing:
            preview = ", ".join(str(item) for item in missing[:3])
            raise FileNotFoundError(f"manifest references missing video(s): {preview}")

    return records


def discover_videos(root: Path, *, recursive: bool = True) -> list[VideoRecord]:
    pattern = "**/*" if recursive else "*"
    videos = sorted(
        path
        for path in root.glob(pattern)
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    return [
        VideoRecord(
            video_id=make_video_id(path, base_dir=root),
            path=path,
            metadata={"relative_path": str(path.relative_to(root))},
        )
        for path in videos
    ]


def make_video_id(path: Path, *, base_dir: Path | None = None) -> str:
    try:
        label_path = path.relative_to(base_dir) if base_dir else path.name
    except ValueError:
        label_path = path.name

    stem = _SLUG_RE.sub("-", str(label_path.with_suffix(""))).strip("-").lower()
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    if not stem:
        stem = "video"
    return f"{stem}-{digest}"


def _load_jsonl_manifest(path: Path) -> list[VideoRecord]:
    records: list[VideoRecord] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
            records.append(_record_from_manifest_payload(payload, base_dir=path.parent))
    return records


def _load_json_manifest(path: Path) -> list[VideoRecord]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        raw_records = payload.get("videos")
        if raw_records is None:
            raw_records = payload.get("items")
    else:
        raw_records = payload

    if not isinstance(raw_records, list):
        raise ValueError("JSON manifest must be a list or an object with 'videos'")

    return [
        _record_from_manifest_payload(row, base_dir=path.parent) for row in raw_records
    ]


def _record_from_manifest_payload(payload: Any, *, base_dir: Path) -> VideoRecord:
    if isinstance(payload, str):
        video_path = Path(payload)
        if not video_path.is_absolute():
            video_path = base_dir / video_path
        return VideoRecord(
            video_id=make_video_id(video_path, base_dir=base_dir),
            path=video_path,
        )
    if not isinstance(payload, dict):
        raise ValueError("manifest video rows must be strings or objects")

    if not payload.get("video_id") and not payload.get("id"):
        raw_path = payload.get("path") or payload.get("video_path")
        if not raw_path:
            raise ValueError("manifest video object requires a path")
        video_path = Path(raw_path)
        if not video_path.is_absolute():
            video_path = base_dir / video_path
        payload = dict(payload)
        payload["video_id"] = make_video_id(video_path, base_dir=base_dir)

    return VideoRecord.from_dict(payload, base_dir=base_dir)


def iter_video_paths(records: Iterable[VideoRecord]) -> Iterable[Path]:
    for record in records:
        yield record.path
