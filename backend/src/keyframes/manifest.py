"""JSONL manifest helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Protocol, TypeVar

from keyframes.models import CandidateKeyframe, KeyframeRecord


class JsonSerializable(Protocol):
    def to_dict(self) -> dict[str, object]: ...


T = TypeVar("T")


def write_jsonl(path: Path, rows: Iterable[JsonSerializable]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row.to_dict(), ensure_ascii=False))
            file.write("\n")


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            rows.append(payload)
    return rows


def read_candidate_manifest(path: Path) -> list[CandidateKeyframe]:
    return [CandidateKeyframe.from_dict(row) for row in read_jsonl(path)]


def read_keyframe_manifest(path: Path) -> list[KeyframeRecord]:
    return [KeyframeRecord.from_dict(row) for row in read_jsonl(path)]


def write_candidate_manifest(path: Path, rows: Iterable[CandidateKeyframe]) -> None:
    write_jsonl(path, rows)


def write_keyframe_manifest(path: Path, rows: Iterable[KeyframeRecord]) -> None:
    write_jsonl(path, rows)


def load_review_decisions(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    decisions: dict[str, str] = {}
    for candidate in read_candidate_manifest(path):
        decisions[candidate.candidate_id] = candidate.decision
    return decisions
