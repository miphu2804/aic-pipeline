"""Command line interface for the keyframe workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from keyframes.config import FinalizationConfig, SelectionConfig
from keyframes.workflow import KeyframeWorkflow, WorkflowResult


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = args.handler(args)
    print(_format_result(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m keyframes",
        description="Semi-automatic video keyframe selection pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare",
        help="extract candidate keyframes and write a review manifest",
    )
    _add_video_database_args(prepare)
    _add_selection_args(prepare)
    prepare.set_defaults(handler=_handle_prepare)

    finalize = subparsers.add_parser(
        "finalize",
        help="export final keyframes from a reviewed candidate manifest",
    )
    finalize.add_argument("review_manifest", type=Path)
    finalize.add_argument("--output", required=True, type=Path)
    _add_finalization_args(finalize)
    finalize.set_defaults(handler=_handle_finalize)

    run = subparsers.add_parser(
        "run",
        help="prepare and finalize in one pass",
    )
    _add_video_database_args(run)
    _add_selection_args(run)
    _add_finalization_args(run)
    run.set_defaults(handler=_handle_run)
    return parser


def _add_video_database_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "video_database",
        type=Path,
        help="directory, JSON manifest, or JSONL manifest of videos",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--flat",
        action="store_true",
        help="disable recursive discovery when video_database is a directory",
    )


def _add_selection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    parser.add_argument("--periodic-interval", type=float, default=20.0)
    parser.add_argument("--min-spacing", type=float, default=2.0)
    parser.add_argument("--max-candidates-per-video", type=int, default=120)
    parser.add_argument("--image-quality", type=int, default=2)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--overwrite", action="store_true")


def _add_finalization_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--pending-policy",
        choices=["accept", "reject"],
        default="accept",
        help="how to handle pending rows in the review manifest",
    )
    parser.add_argument("--max-keyframes-per-video", type=int)
    parser.add_argument("--overwrite-final", action="store_true")


def _selection_config(args: argparse.Namespace) -> SelectionConfig:
    return SelectionConfig(
        scene_threshold=args.scene_threshold,
        periodic_interval_seconds=args.periodic_interval,
        min_spacing_seconds=args.min_spacing,
        max_candidates_per_video=args.max_candidates_per_video,
        image_quality=args.image_quality,
        overwrite=args.overwrite,
        ffmpeg_binary=args.ffmpeg,
        ffprobe_binary=args.ffprobe,
    )


def _finalization_config(args: argparse.Namespace) -> FinalizationConfig:
    return FinalizationConfig(
        pending_policy=args.pending_policy,
        max_keyframes_per_video=args.max_keyframes_per_video,
        overwrite=args.overwrite_final,
    )


def _handle_prepare(args: argparse.Namespace) -> WorkflowResult:
    workflow = KeyframeWorkflow(selection_config=_selection_config(args))
    return workflow.prepare(
        args.video_database,
        args.output,
        recursive=not args.flat,
    )


def _handle_finalize(args: argparse.Namespace) -> WorkflowResult:
    workflow = KeyframeWorkflow(finalization_config=_finalization_config(args))
    return workflow.finalize(args.review_manifest, args.output)


def _handle_run(args: argparse.Namespace) -> WorkflowResult:
    workflow = KeyframeWorkflow(
        selection_config=_selection_config(args),
        finalization_config=_finalization_config(args),
    )
    return workflow.run(
        args.video_database,
        args.output,
        recursive=not args.flat,
    )


def _format_result(result: WorkflowResult) -> str:
    lines = [
        f"output_dir={result.output_dir}",
        f"candidates={result.candidate_count}",
        f"candidates_manifest={result.candidates_manifest}",
    ]
    if result.keyframes_manifest is not None:
        lines.extend(
            [
                f"keyframes={result.keyframe_count}",
                f"keyframes_manifest={result.keyframes_manifest}",
            ]
        )
    return "\n".join(lines)
