"""
Lip Sync Engine
===============
Takes the viseme envelope produced by the Voice Engine (mouth-openness
sampled at syllable resolution) and resamples it onto the movie's actual
frame rate, quantized into a small set of mouth shapes. The Animation
Engine then draws the matching mouth shape on every frame so dialogue is
synchronized to audio automatically - no manual keyframing required.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.ai.voice_engine import VisemeFrame

MOUTH_SHAPES = ["closed", "small", "medium", "wide"]


@dataclass
class FrameViseme:
    frame_index: int
    mouth_shape: str


def _quantize(mouth_open: float) -> str:
    if mouth_open < 0.1:
        return "closed"
    if mouth_open < 0.4:
        return "small"
    if mouth_open < 0.7:
        return "medium"
    return "wide"


class LipSyncEngine:
    def build_frame_visemes(self, visemes: list[VisemeFrame], duration: float, fps: int) -> list[FrameViseme]:
        total_frames = max(1, int(round(duration * fps)))
        if not visemes:
            return [FrameViseme(frame_index=i, mouth_shape="closed") for i in range(total_frames)]

        frames: list[FrameViseme] = []
        vi = 0
        for i in range(total_frames):
            t = i / fps
            while vi + 1 < len(visemes) and visemes[vi + 1].time <= t:
                vi += 1
            frames.append(FrameViseme(frame_index=i, mouth_shape=_quantize(visemes[vi].mouth_open)))
        return frames
