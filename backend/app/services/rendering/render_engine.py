"""
Render Engine
=============
The last mile of the pipeline. Takes the per-scene silent video clips
(Animation Engine) and per-scene mixed audio (Audio Engine), and produces
one finished MP4 with:
  * dialogue + music + SFX muxed onto every scene
  * all scenes concatenated in story order
  * a synchronized .srt subtitle file (auto-generated from scene/dialogue
    text and each scene's timing)
  * a thumbnail image for the My Movies gallery

Also exposes `export()` for the Export screen: re-encode to a chosen
resolution/container, optionally burning subtitles into the picture.

Uses the `ffmpeg` CLI directly (available on virtually any host, no extra
Python deps) rather than a heavier library, so this module has the fewest
possible moving parts in production.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from app.models.project import Project, Scene


def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class RenderEngine:
    def mux_scene(self, silent_video_path: Path, audio_path: Path, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(silent_video_path),
            "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    def concatenate(self, scene_clip_paths: list[Path], out_path: Path, tmp_dir: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        list_file = tmp_dir / "concat_list.txt"
        list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_clip_paths))

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    def generate_thumbnail(self, video_path: Path, out_path: Path, at_seconds: float = 0.5) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-ss", str(at_seconds), "-i", str(video_path),
            "-frames:v", "1", str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    def generate_subtitles(self, scenes: list[Scene], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        cursor = 0.0
        counter = 1

        for scene in scenes:
            dialogue = scene.dialogue_lines or []
            has_real_timing = all("start" in d and "end" in d for d in dialogue) if dialogue else False

            if has_real_timing:
                # Real timestamps from the Voice Engine (relative to this
                # scene's start) - captions land exactly when each line is
                # actually heard in the mixed audio.
                captions = [
                    (d["start"], d["end"], f"{d['character_name']}: {d['text']}" if d.get("character_name") else d["text"])
                    for d in dialogue
                ]
            elif dialogue:
                # Fallback only: dialogue exists without timing info (e.g. a
                # scene skipped voice synthesis). Spread evenly rather than
                # dropping the lines.
                per_caption = scene.duration_seconds / max(1, len(dialogue))
                captions = [
                    (i * per_caption, (i + 1) * per_caption,
                     f"{d['character_name']}: {d['text']}" if d.get("character_name") else d["text"])
                    for i, d in enumerate(dialogue)
                ]
            else:
                captions = [(0.0, scene.duration_seconds, scene.text[:120])]

            for rel_start, rel_end, caption in captions:
                start, end = cursor + rel_start, cursor + rel_end
                lines.append(str(counter))
                lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
                lines.append(caption)
                lines.append("")
                counter += 1

            cursor += scene.duration_seconds

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def export(self, project: Project, preset: dict, burn_in_subtitles: bool = False) -> tuple[str, str]:
        src_video = Path(project.video_path)
        target_w, target_h = preset["resolution"].split("x")
        export_dir = src_video.parent / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        out_video = export_dir / f"export_{preset['resolution']}{'_subbed' if burn_in_subtitles else ''}.mp4"

        vf = f"scale={target_w}:{target_h}"
        cmd = ["ffmpeg", "-y", "-i", str(src_video)]

        if burn_in_subtitles and project.subtitle_path and Path(project.subtitle_path).exists():
            vf += f",subtitles={Path(project.subtitle_path).as_posix()}"

        cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", str(out_video)]
        subprocess.run(cmd, check=True, capture_output=True)

        return str(out_video), project.subtitle_path
