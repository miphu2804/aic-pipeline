"""Semi-automatic keyframe candidate selection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from keyframes.config import SelectionConfig
from keyframes.ffmpeg import detect_scene_changes, extract_frame_at, probe_duration
from keyframes.models import CandidateKeyframe, VideoRecord


@dataclass(frozen=True)
class CandidateEvent:
    timestamp_seconds: float
    source: str
    score: float | None = None


class SemiAutomaticKeyframeSelector:
    """Build candidate frames from scene changes plus coverage sampling."""

    def __init__(self, config: SelectionConfig | None = None) -> None:
        self.config = config or SelectionConfig()

    def plan(self, video: VideoRecord) -> list[CandidateEvent]:
        duration = probe_duration(
            video.path,
            ffprobe_binary=self.config.ffprobe_binary,
        )
        scene_events = [
            CandidateEvent(scene.timestamp_seconds, "scene", scene.score)
            for scene in detect_scene_changes(
                video.path,
                threshold=self.config.scene_threshold,
                ffmpeg_binary=self.config.ffmpeg_binary,
            )
        ]
        events = [CandidateEvent(0.0, "seed", 1.0)]
        events.extend(scene_events)
        events.extend(self._periodic_events(duration))
        return merge_candidate_events(
            events,
            min_spacing_seconds=self.config.min_spacing_seconds,
            max_events=self.config.max_candidates_per_video,
        )

    def extract(
        self,
        video: VideoRecord,
        candidates_root: Path,
    ) -> list[CandidateKeyframe]:
        events = self.plan(video)
        output_dir = candidates_root / video.video_id
        candidates: list[CandidateKeyframe] = []
        for event in events:
            candidate_id = make_candidate_id(video.video_id, event)
            image_path = output_dir / f"{candidate_id}.jpg"
            extract_frame_at(
                video.path,
                timestamp_seconds=event.timestamp_seconds,
                output_path=image_path,
                image_quality=self.config.image_quality,
                overwrite=self.config.overwrite,
                ffmpeg_binary=self.config.ffmpeg_binary,
            )
            candidates.append(
                CandidateKeyframe(
                    candidate_id=candidate_id,
                    video_id=video.video_id,
                    video_path=video.path,
                    timestamp_seconds=event.timestamp_seconds,
                    image_path=image_path,
                    source=event.source,
                    score=event.score,
                    metadata={"selector": "scene_plus_periodic"},
                )
            )
        return candidates

    def _periodic_events(self, duration: float | None) -> list[CandidateEvent]:
        if duration is None or duration <= 0:
            return []

        interval = self.config.periodic_interval_seconds
        count = max(0, math.floor(duration / interval))
        events = [
            CandidateEvent(index * interval, "periodic", 0.0)
            for index in range(1, count + 1)
        ]
        tail_margin = min(1.0, max(0.1, interval / 2))
        tail = max(0.0, duration - tail_margin)
        if tail > 0 and (
            not events or tail - events[-1].timestamp_seconds > interval / 2
        ):
            events.append(CandidateEvent(tail, "periodic", 0.0))
        return events


def merge_candidate_events(
    events: list[CandidateEvent],
    *,
    min_spacing_seconds: float,
    max_events: int | None = None,
) -> list[CandidateEvent]:
    """Deduplicate nearby candidates while preferring scene changes."""

    merged: list[CandidateEvent] = []
    for event in sorted(events, key=lambda item: item.timestamp_seconds):
        if event.timestamp_seconds < 0:
            continue

        nearby_index = _find_nearby_index(merged, event, min_spacing_seconds)
        if nearby_index is None:
            merged.append(event)
            continue

        current = merged[nearby_index]
        if _event_rank(event) > _event_rank(current):
            merged[nearby_index] = event

    merged = sorted(merged, key=lambda item: item.timestamp_seconds)
    if max_events is not None and len(merged) > max_events:
        ranked = sorted(merged, key=_event_rank, reverse=True)[:max_events]
        merged = sorted(ranked, key=lambda item: item.timestamp_seconds)
    return merged


def make_candidate_id(video_id: str, event: CandidateEvent) -> str:
    millis = int(round(event.timestamp_seconds * 1000))
    return f"{video_id}_{event.source}_t{millis:010d}"


def _find_nearby_index(
    events: list[CandidateEvent],
    candidate: CandidateEvent,
    min_spacing_seconds: float,
) -> int | None:
    for index, event in enumerate(events):
        if (
            abs(event.timestamp_seconds - candidate.timestamp_seconds)
            < min_spacing_seconds
        ):
            return index
    return None


def _event_rank(event: CandidateEvent) -> tuple[int, float, float]:
    priority = {"scene": 3, "seed": 2, "periodic": 1}.get(event.source, 0)
    score = event.score if event.score is not None else 0.0
    return priority, score, -event.timestamp_seconds
