"""Runtime configuration for keyframe extraction."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SelectionConfig(BaseModel):
    """Controls the video-database to candidate-keyframe stage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scene_threshold: float = Field(
        default=0.35,
        description="FFmpeg scene-change threshold in the inclusive range [0, 1].",
    )
    periodic_interval_seconds: float = Field(
        default=20.0,
        description="Fallback sampling interval in seconds between candidate frames.",
    )
    min_spacing_seconds: float = Field(
        default=2.0,
        description="Minimum distance in seconds between two candidate frames.",
    )
    max_candidates_per_video: int | None = Field(
        default=120,
        description=(
            "Maximum candidate frames to keep for each video; null disables cap."
        ),
    )
    image_quality: int = Field(
        default=2,
        description=(
            "FFmpeg JPEG quality value passed to -q:v; lower is higher quality."
        ),
    )
    overwrite: bool = Field(
        default=False,
        description="Whether candidate JPEG files may overwrite existing files.",
    )
    ffmpeg_binary: str = Field(
        default="ffmpeg",
        description="Executable name or path used to extract frames and detect scenes.",
    )
    ffprobe_binary: str = Field(
        default="ffprobe",
        description="Executable name or path used to read video metadata.",
    )

    @field_validator("scene_threshold")
    @classmethod
    def validate_scene_threshold(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("scene_threshold must be finite")
        if not 0.0 <= value <= 1.0:
            raise ValueError("scene_threshold must be between 0 and 1")
        return value

    @field_validator("periodic_interval_seconds")
    @classmethod
    def validate_periodic_interval_seconds(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("periodic_interval_seconds must be finite")
        if value <= 0:
            raise ValueError("periodic_interval_seconds must be positive")
        return value

    @field_validator("min_spacing_seconds")
    @classmethod
    def validate_min_spacing_seconds(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("min_spacing_seconds must be finite")
        if value < 0:
            raise ValueError("min_spacing_seconds cannot be negative")
        return value

    @field_validator("max_candidates_per_video")
    @classmethod
    def validate_max_candidates_per_video(cls, value: int | None) -> int | None:
        return _validate_optional_positive_int(value, "max_candidates_per_video")

    @field_validator("image_quality")
    @classmethod
    def validate_image_quality(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("image_quality must be positive")
        return value

    @field_validator("ffmpeg_binary", "ffprobe_binary")
    @classmethod
    def validate_binary_name(cls, value: str) -> str:
        binary = value.strip()
        if not binary:
            raise ValueError("binary name cannot be empty")
        return binary


class FinalizationConfig(BaseModel):
    """Controls the reviewed-candidate to final-keyframe stage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pending_policy: Literal["accept", "reject"] = Field(
        default="accept",
        description="How pending review rows are handled during final keyframe export.",
    )
    max_keyframes_per_video: int | None = Field(
        default=None,
        description=(
            "Maximum final keyframes to export for each video; null disables cap."
        ),
    )
    overwrite: bool = Field(
        default=False,
        description="Whether final keyframe JPEG files may overwrite existing files.",
    )

    @field_validator("pending_policy", mode="before")
    @classmethod
    def validate_pending_policy(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("pending_policy must be a string")
        policy = value.strip().lower()
        if policy not in {"accept", "reject"}:
            raise ValueError("pending_policy must be 'accept' or 'reject'")
        return policy

    @field_validator("max_keyframes_per_video")
    @classmethod
    def validate_max_keyframes_per_video(cls, value: int | None) -> int | None:
        return _validate_optional_positive_int(value, "max_keyframes_per_video")


def _validate_optional_positive_int(value: int | None, field_name: str) -> int | None:
    if value is not None and value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return value
