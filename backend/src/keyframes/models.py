"""Shared data models for the keyframe pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

ReviewDecision = Literal["pending", "accepted", "rejected"]


def _path_from(value: str | Path) -> Path:
    return Path(value).expanduser()


def _metadata_from(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object")
    return dict(value)


@dataclass(frozen=True)
class VideoRecord:
    """One source video from a video database."""

    video_id: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "path": str(self.path),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        base_dir: Path | None = None,
    ) -> "VideoRecord":
        raw_path = payload.get("path") or payload.get("video_path")
        if not raw_path:
            raise ValueError("video record requires 'path' or 'video_path'")

        path = _path_from(raw_path)
        if not path.is_absolute() and base_dir is not None:
            path = base_dir / path

        video_id = payload.get("video_id") or payload.get("id")
        if not video_id:
            raise ValueError("manifest records require 'video_id' or 'id'")

        known_keys = {"id", "video_id", "path", "video_path", "metadata"}
        metadata = _metadata_from(payload.get("metadata"))
        metadata.update(
            {key: value for key, value in payload.items() if key not in known_keys}
        )
        return cls(video_id=str(video_id), path=path, metadata=metadata)


@dataclass(frozen=True)
class CandidateKeyframe:
    """Candidate frame produced by the semi-automatic selector."""

    candidate_id: str
    video_id: str
    video_path: Path
    timestamp_seconds: float
    image_path: Path
    source: str
    score: float | None = None
    decision: ReviewDecision = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_decision(self, decision: ReviewDecision) -> "CandidateKeyframe":
        return replace(self, decision=decision)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "video_id": self.video_id,
            "video_path": str(self.video_path),
            "timestamp_seconds": self.timestamp_seconds,
            "image_path": str(self.image_path),
            "source": self.source,
            "score": self.score,
            "decision": self.decision,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CandidateKeyframe":
        decision = payload.get("decision", "pending")
        if decision not in {"pending", "accepted", "rejected"}:
            raise ValueError(f"unknown review decision: {decision}")
        return cls(
            candidate_id=str(payload["candidate_id"]),
            video_id=str(payload["video_id"]),
            video_path=_path_from(payload["video_path"]),
            timestamp_seconds=float(payload["timestamp_seconds"]),
            image_path=_path_from(payload["image_path"]),
            source=str(payload["source"]),
            score=None if payload.get("score") is None else float(payload["score"]),
            decision=decision,
            metadata=_metadata_from(payload.get("metadata")),
        )


@dataclass(frozen=True)
class KeyframeRecord:
    """Final keyframe ready for downstream OCR/color/semantic blocks."""

    keyframe_id: str
    candidate_id: str
    video_id: str
    video_path: Path
    timestamp_seconds: float
    image_path: Path
    source: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyframe_id": self.keyframe_id,
            "candidate_id": self.candidate_id,
            "video_id": self.video_id,
            "video_path": str(self.video_path),
            "timestamp_seconds": self.timestamp_seconds,
            "image_path": str(self.image_path),
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KeyframeRecord":
        return cls(
            keyframe_id=str(payload["keyframe_id"]),
            candidate_id=str(payload["candidate_id"]),
            video_id=str(payload["video_id"]),
            video_path=_path_from(payload["video_path"]),
            timestamp_seconds=float(payload["timestamp_seconds"]),
            image_path=_path_from(payload["image_path"]),
            source=str(payload["source"]),
            score=None if payload.get("score") is None else float(payload["score"]),
            metadata=_metadata_from(payload.get("metadata")),
        )
