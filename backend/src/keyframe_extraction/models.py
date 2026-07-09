from __future__ import annotations

from pydantic import BaseModel


class DakeKeyframeCandidate(BaseModel):
    """A frame selected by the U-CESE steepness algorithm."""

    frame_index: int
    timestamp_seconds: float
    jpeg_size: int
    steepness: float


class KeyframeExtractionResponse(BaseModel):
    frame_index: int
    timestamp: float
