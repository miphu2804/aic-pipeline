"""End-to-end workflow from video database to final keyframes."""

from __future__ import annotations

import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from keyframes.config import FinalizationConfig, SelectionConfig
from keyframes.manifest import (
    load_review_decisions,
    read_candidate_manifest,
    write_candidate_manifest,
    write_keyframe_manifest,
)
from keyframes.models import CandidateKeyframe, KeyframeRecord
from keyframes.selector import SemiAutomaticKeyframeSelector
from keyframes.video_database import load_video_database


@dataclass(frozen=True)
class WorkflowResult:
    output_dir: Path
    candidates_manifest: Path
    keyframes_manifest: Path | None
    candidate_count: int
    keyframe_count: int


class KeyframeWorkflow:
    """Coordinates candidate extraction, review manifests, and final export."""

    def __init__(
        self,
        *,
        selection_config: SelectionConfig | None = None,
        finalization_config: FinalizationConfig | None = None,
    ) -> None:
        self.selection_config = selection_config or SelectionConfig()
        self.finalization_config = finalization_config or FinalizationConfig()

    def prepare(
        self,
        video_database: str | Path,
        output_dir: str | Path,
        *,
        recursive: bool = True,
    ) -> WorkflowResult:
        output_path = Path(output_dir).expanduser()
        manifest_path = output_path / "manifests" / "candidate_keyframes.jsonl"
        decisions = load_review_decisions(manifest_path)

        records = load_video_database(video_database, recursive=recursive)
        selector = SemiAutomaticKeyframeSelector(self.selection_config)
        candidates: list[CandidateKeyframe] = []
        for video in records:
            for candidate in selector.extract(video, output_path / "candidates"):
                decision = decisions.get(candidate.candidate_id)
                if decision in {"pending", "accepted", "rejected"}:
                    candidate = candidate.with_decision(decision)
                candidates.append(candidate)

        write_candidate_manifest(manifest_path, candidates)
        return WorkflowResult(
            output_dir=output_path,
            candidates_manifest=manifest_path,
            keyframes_manifest=None,
            candidate_count=len(candidates),
            keyframe_count=0,
        )

    def finalize(
        self,
        review_manifest: str | Path,
        output_dir: str | Path,
    ) -> WorkflowResult:
        output_path = Path(output_dir).expanduser()
        manifest_path = Path(review_manifest).expanduser()
        candidates = read_candidate_manifest(manifest_path)
        selected = self._select_reviewed_candidates(candidates)
        keyframes = self._export_keyframes(selected, output_path / "keyframes")
        keyframes_manifest = output_path / "manifests" / "keyframes.jsonl"
        write_keyframe_manifest(keyframes_manifest, keyframes)

        return WorkflowResult(
            output_dir=output_path,
            candidates_manifest=manifest_path,
            keyframes_manifest=keyframes_manifest,
            candidate_count=len(candidates),
            keyframe_count=len(keyframes),
        )

    def run(
        self,
        video_database: str | Path,
        output_dir: str | Path,
        *,
        recursive: bool = True,
    ) -> WorkflowResult:
        prepared = self.prepare(video_database, output_dir, recursive=recursive)
        return self.finalize(prepared.candidates_manifest, prepared.output_dir)

    def _select_reviewed_candidates(
        self,
        candidates: list[CandidateKeyframe],
    ) -> list[CandidateKeyframe]:
        selected_by_video: dict[str, list[CandidateKeyframe]] = defaultdict(list)
        for candidate in candidates:
            if candidate.decision == "rejected":
                continue
            if candidate.decision == "pending":
                if self.finalization_config.pending_policy == "reject":
                    continue
            selected_by_video[candidate.video_id].append(candidate)

        selected: list[CandidateKeyframe] = []
        for video_id in sorted(selected_by_video):
            group = sorted(
                selected_by_video[video_id],
                key=lambda item: item.timestamp_seconds,
            )
            max_per_video = self.finalization_config.max_keyframes_per_video
            if max_per_video is not None and len(group) > max_per_video:
                ranked = sorted(group, key=_candidate_rank, reverse=True)[
                    :max_per_video
                ]
                group = sorted(ranked, key=lambda item: item.timestamp_seconds)
            selected.extend(group)
        return selected

    def _export_keyframes(
        self,
        candidates: list[CandidateKeyframe],
        keyframes_root: Path,
    ) -> list[KeyframeRecord]:
        keyframes: list[KeyframeRecord] = []
        for candidate in candidates:
            keyframe_id = make_keyframe_id(candidate)
            output_path = keyframes_root / candidate.video_id / f"{keyframe_id}.jpg"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if self.finalization_config.overwrite or not output_path.exists():
                shutil.copy2(candidate.image_path, output_path)
            keyframes.append(
                KeyframeRecord(
                    keyframe_id=keyframe_id,
                    candidate_id=candidate.candidate_id,
                    video_id=candidate.video_id,
                    video_path=candidate.video_path,
                    timestamp_seconds=candidate.timestamp_seconds,
                    image_path=output_path,
                    source=candidate.source,
                    score=candidate.score,
                    metadata={
                        **candidate.metadata,
                        "review_decision": candidate.decision,
                    },
                )
            )
        return keyframes


def make_keyframe_id(candidate: CandidateKeyframe) -> str:
    millis = int(round(candidate.timestamp_seconds * 1000))
    return f"{candidate.video_id}_keyframe_t{millis:010d}"


def _candidate_rank(candidate: CandidateKeyframe) -> tuple[int, float, float]:
    priority = {"accepted": 3, "pending": 2, "rejected": 0}.get(candidate.decision, 0)
    source_priority = {"scene": 3, "seed": 2, "periodic": 1}.get(candidate.source, 0)
    score = candidate.score if candidate.score is not None else 0.0
    return priority + source_priority, score, -candidate.timestamp_seconds
