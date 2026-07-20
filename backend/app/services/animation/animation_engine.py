"""
Animation Engine
================
Consumes one scene's environment image + the character profiles who appear
in it + the per-frame lip-sync visemes, and produces a silent (video-only)
clip with:
  * a cinematic camera move (pan / zoom-in / zoom-out / dolly / static),
    implemented as a classic Ken-Burns crop-and-scale over time
  * character bodies composited into the frame at consistent positions
  * a mouth shape per frame driven by the Lip Sync Engine (automatic lip
    sync - no manual keyframing)
  * a simple expression (eyebrow/eye treatment) driven by the scene's
    detected emotion

This module is the offline stand-in for a full 3D animation/rendering
engine (e.g. a Blender/Unreal pipeline or a text-to-video model). It uses
only PIL + numpy + the `ffmpeg` binary, so the whole movie pipeline can be
generated and previewed with no GPU and no external services. Swapping in
a real 3D engine later means replacing `_draw_character`/`_prepare_environment`
- the frame-timing, camera-move and lip-sync orchestration below stays the
same either way.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from app.services.ai.character_engine import CharacterVisualProfile, draw_head_shape
from app.services.ai.lipsync_engine import FrameViseme

WORKING_RESOLUTION = (960, 540)  # fast to render for previews; export upscales for final delivery

MOUTH_HEIGHT = {"closed": 4, "small": 12, "medium": 22, "wide": 34}

EMOTION_EYEBROW_ANGLE = {  # degrees of eyebrow tilt, purely a visual accent
    "joyful": -12, "sad": 14, "tense": 8, "angry": 20, "romantic": -8,
    "epic": 6, "calm": 0, "neutral": 0,
}


class AnimationEngine:
    def render_scene_clip(
        self,
        environment_path: Path,
        on_screen_characters: list[tuple[str, CharacterVisualProfile]],
        speaker_timeline: list[dict],
        frame_visemes: list[FrameViseme],
        emotion: str,
        camera_movement: str,
        duration: float,
        fps: int,
        out_path: Path,
        tmp_frames_dir: Path,
    ) -> Path:
        """`on_screen_characters` is a list of (character_id, profile) tuples
        for every character present in the scene. `speaker_timeline` is a
        list of {character_id, start, end} windows (in scene-relative
        seconds) saying who is actually talking when - the character whose
        window covers the current frame's timestamp gets the animated mouth
        shape from `frame_visemes`; everyone else stays closed-mouthed."""
        tmp_frames_dir.mkdir(parents=True, exist_ok=True)
        base_env = Image.open(environment_path).convert("RGB")
        total_frames = max(1, int(round(duration * fps)))

        for i in range(total_frames):
            progress = i / max(1, total_frames - 1)
            t = i / fps
            frame = self._apply_camera_move(base_env, camera_movement, progress)
            frame = frame.resize(WORKING_RESOLUTION)
            draw = ImageDraw.Draw(frame)

            active_speaker_id = next(
                (s["character_id"] for s in speaker_timeline if s["start"] <= t < s["end"]), None
            )

            visible = on_screen_characters[:3]  # keep the frame readable for a 3-shot max
            slot_width = WORKING_RESOLUTION[0] // max(1, len(visible))
            for idx, (char_id, profile) in enumerate(visible):
                is_speaking = char_id == active_speaker_id
                mouth_shape = frame_visemes[i].mouth_shape if is_speaking and i < len(frame_visemes) else "closed"
                cx = slot_width * idx + slot_width // 2
                self._draw_character(draw, profile, (cx, WORKING_RESOLUTION[1] - 40), mouth_shape, emotion)

            frame.save(tmp_frames_dir / f"frame_{i:05d}.png")

        self._encode_frames_to_video(tmp_frames_dir, fps, out_path)
        return out_path

    # -- camera ------------------------------------------------------------

    def _apply_camera_move(self, img: Image.Image, movement: str, progress: float) -> Image.Image:
        w, h = img.size
        if movement == "zoom_in":
            scale = 1.0 - 0.18 * progress
        elif movement == "zoom_out":
            scale = 0.82 + 0.18 * progress
        elif movement in ("pan", "dolly"):
            scale = 0.88 if movement == "pan" else 0.92 - 0.06 * progress
        else:  # static
            scale = 1.0

        crop_w, crop_h = int(w * scale), int(h * scale)
        if movement == "pan":
            max_x_offset = w - crop_w
            x0 = int(max_x_offset * progress)
        else:
            x0 = (w - crop_w) // 2
        y0 = (h - crop_h) // 2
        cropped = img.crop((x0, y0, x0 + crop_w, y0 + crop_h))
        return cropped.resize((w, h))

    # -- characters ----------------------------------------------------------

    def _draw_character(self, draw: ImageDraw.ImageDraw, profile: CharacterVisualProfile, base_xy: tuple[int, int], mouth_shape: str, emotion: str) -> None:
        skin, outfit, accent = profile.palette
        cx, base_y = base_xy
        scale = {"slim": 0.85, "average": 1.0, "sturdy": 1.15, "tall_lanky": 1.05, "small_round": 0.9}[profile.build]

        body_w, body_h = int(70 * scale), int(110 * scale)
        draw.rounded_rectangle(
            [cx - body_w // 2, base_y - body_h, cx + body_w // 2, base_y], radius=18, fill=outfit
        )
        head_r = int(38 * scale)
        head_cy = base_y - body_h - head_r
        draw_head_shape(draw, profile.face_shape, cx, head_cy, head_r, skin)

        # eyebrows tilt with emotion
        tilt = EMOTION_EYEBROW_ANGLE.get(emotion, 0)
        for side in (-1, 1):
            bx = cx + side * head_r * 0.45
            by = head_cy - head_r * 0.25
            dy = tilt * side * 0.3
            draw.line([(bx - 10, by + dy), (bx + 10, by - dy)], fill=(40, 30, 30), width=3)

        # eyes
        for side in (-1, 1):
            ex = cx + side * head_r * 0.45
            ey = head_cy - head_r * 0.05
            draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(30, 25, 25))

        # mouth (lip-synced)
        mh = MOUTH_HEIGHT[mouth_shape]
        mw = int(head_r * 0.7)
        my = head_cy + head_r * 0.4
        draw.ellipse([cx - mw // 2, my - mh // 2, cx + mw // 2, my + mh // 2], fill=(120, 40, 50))

        # accent detail ties the character's palette together
        draw.rectangle([cx - body_w // 2, base_y - 15, cx + body_w // 2, base_y - 5], fill=accent)

    # -- encoding ------------------------------------------------------------

    def _encode_frames_to_video(self, frames_dir: Path, fps: int, out_path: Path) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-framerate", str(fps),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
