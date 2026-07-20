"""
Movie Pipeline
==============
The single orchestrator that the background worker calls. Runs every
stage of the product brief in order, persisting progress to the `Project`
row after each stage so the Generation Progress screen can poll it:

  1. analyze_story          - split story into scenes, detect location/
                               emotion/camera/SFX per scene (Story Engine)
  2. generate_characters    - build a consistent visual+voice profile per
                               character and render a reference sheet
  3. generate_environments   - render (and cache/re-use) one background per
                               unique location
  4. generate_voice          - synthesize every dialogue line + viseme data
  5. animate                 - composite characters onto environments with
                               camera moves + automatic lip sync
  6. generate_audio          - mix music + ambience + SFX + dialogue per
                               scene
  7. render                  - mux, concatenate, subtitle, thumbnail
  8. completed
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.project import Character, Project, Scene
from app.services.ai.audio_engine import AudioEngine
from app.services.ai.character_engine import CharacterEngine, CharacterVisualProfile
from app.services.ai.environment_engine import EnvironmentEngine
from app.services.ai.lipsync_engine import LipSyncEngine
from app.services.ai.story_engine import get_story_engine
from app.services.ai.voice_engine import VoiceEngine, concatenate_voice_clips
from app.services.animation.animation_engine import AnimationEngine
from app.services.rendering.render_engine import RenderEngine
from app.utils.logger import logger

settings = get_settings()
FPS = settings.DEFAULT_FPS


class MoviePipeline:
    def __init__(self) -> None:
        self.character_engine = CharacterEngine()
        self.environment_engine = EnvironmentEngine()
        self.voice_engine = VoiceEngine()
        self.lipsync_engine = LipSyncEngine()
        self.audio_engine = AudioEngine()
        self.animation_engine = AnimationEngine()
        self.render_engine = RenderEngine()

    # -- public entrypoint ---------------------------------------------------

    def run(self, project_id: str, is_cancelled: Callable[[], bool]) -> None:
        db: Session = SessionLocal()
        try:
            project = db.get(Project, project_id)
            if not project:
                return

            if shutil.which("ffmpeg") is None:
                raise RuntimeError(
                    "ffmpeg was not found on this server. The animation and render "
                    "stages both shell out to the ffmpeg binary. Install it "
                    "(e.g. `apt install ffmpeg` / `brew install ffmpeg`) and restart "
                    "the backend, or use the provided Docker image, which installs "
                    "it automatically."
                )

            paths = self._project_paths(project.id)

            self._set_stage(db, project, "analyzing_story", 5)
            scenes = self._analyze_story(db, project)
            if is_cancelled():
                return

            self._set_stage(db, project, "generating_characters", 15)
            profiles_by_char_id = self._generate_characters(db, project, paths)
            if is_cancelled():
                return

            self._set_stage(db, project, "generating_environments", 25)
            env_path_by_scene = self._generate_environments(scenes, profiles_by_char_id, paths)
            if is_cancelled():
                return

            self._set_stage(db, project, "generating_voice", 40)
            voice_by_scene = self._generate_voice(db, scenes, profiles_by_char_id, paths)
            if is_cancelled():
                return

            self._set_stage(db, project, "animating", 60)
            silent_clip_by_scene = self._animate(
                scenes, profiles_by_char_id, env_path_by_scene, voice_by_scene, paths
            )
            if is_cancelled():
                return

            self._set_stage(db, project, "generating_audio", 78)
            mixed_audio_by_scene = self._generate_audio(db, scenes, voice_by_scene, paths)
            if is_cancelled():
                return

            self._set_stage(db, project, "rendering", 90)
            self._render_final(db, project, scenes, silent_clip_by_scene, mixed_audio_by_scene, paths)

            project.status = "completed"
            project.current_stage = "completed"
            project.progress_percent = 100
            db.commit()
            logger.info("Project {} rendered successfully -> {}", project.id, project.video_path)

        except Exception as exc:  # noqa: BLE001 - top-level job guard
            logger.exception("Pipeline failed for project {}", project_id)
            project = db.get(Project, project_id)
            if project:
                project.status = "failed"
                project.error_message = str(exc)
                db.commit()
        finally:
            db.close()

    # -- stage 1: story ------------------------------------------------------

    def _analyze_story(self, db: Session, project: Project) -> list[Scene]:
        db.query(Scene).filter(Scene.project_id == project.id).delete()
        db.flush()

        engine = get_story_engine()
        character_names = [c.name for c in project.characters]
        plans = engine.analyze(project.story, project.dialogue, project.duration_minutes, character_names)

        name_to_char = {c.name.lower(): c for c in project.characters}
        scenes: list[Scene] = []
        for plan in plans:
            dialogue_json = []
            mentioned_char_ids = []
            for line in plan.dialogue_lines:
                char = name_to_char.get(line.character_name.lower())
                dialogue_json.append(
                    {
                        "character_id": char.id if char else None,
                        "character_name": char.name if char else line.character_name,
                        "text": line.text,
                    }
                )
                if char and char.id not in mentioned_char_ids:
                    mentioned_char_ids.append(char.id)

            # Characters whose plain name appears in the narration text also
            # count as "on screen" for this scene, even with no dialogue.
            for char in project.characters:
                if char.name.lower() in plan.text.lower() and char.id not in mentioned_char_ids:
                    mentioned_char_ids.append(char.id)
            if not mentioned_char_ids and project.characters:
                mentioned_char_ids = [project.characters[0].id]

            scene = Scene(
                project_id=project.id,
                index=plan.index,
                text=plan.text,
                location=plan.location,
                time_of_day=plan.time_of_day,
                emotion=plan.emotion,
                camera_movement=plan.camera_movement,
                duration_seconds=plan.duration_seconds,
                character_ids=mentioned_char_ids,
                dialogue_lines=dialogue_json,
                sfx_tags=plan.sfx_tags,
                music_mood=plan.music_mood,
                status="planned",
            )
            db.add(scene)
            scenes.append(scene)

        db.commit()
        for s in scenes:
            db.refresh(s)
        return scenes

    # -- stage 2: characters --------------------------------------------------

    def _generate_characters(self, db: Session, project: Project, paths: dict) -> dict[str, CharacterVisualProfile]:
        profiles: dict[str, CharacterVisualProfile] = {}
        for char in project.characters:
            profile = self.character_engine.build_profile(
                name=char.name,
                description=char.description,
                role=char.role,
                seed=char.consistency_seed,
                voice_profile=char.voice_profile,
            )
            ref_path = self.character_engine.render_reference_sheet(profile, paths["characters"])
            char.reference_image_path = str(ref_path)
            profiles[char.id] = profile
        db.commit()
        return profiles

    # -- stage 3: environments -------------------------------------------------

    def _generate_environments(
        self, scenes: list[Scene], profiles: dict[str, CharacterVisualProfile], paths: dict
    ) -> dict[str, Path]:
        env_by_scene: dict[str, Path] = {}
        for scene in scenes:
            any_profile = next(iter(profiles.values()), None)
            palette = any_profile.palette if any_profile else ["#495366", "#222", "#F2B84B"]
            env_path = self.environment_engine.build_environment(
                scene.location, scene.time_of_day, palette, paths["environments"], variation_key=scene.text
            )
            env_by_scene[scene.id] = env_path
        return env_by_scene

    # -- stage 4: voice + lipsync data ----------------------------------------

    def _generate_voice(
        self, db: Session, scenes: list[Scene], profiles: dict[str, CharacterVisualProfile], paths: dict
    ) -> dict[str, dict]:
        """Synthesizes every dialogue line in a scene, then concatenates all
        of them (with a short pause between lines) into ONE continuous voice
        track for that scene, with a matching combined viseme timeline.

        Real per-line start/end timestamps are written back onto
        Scene.dialogue_lines so the subtitle generator uses actual timing
        instead of guessing. If the recorded dialogue runs longer than the
        scene's narration-based duration estimate, the scene is extended so
        audio is never truncated.

        Returns, per scene id: {"path": combined wav or None, "duration":
        total dialogue seconds, "visemes": combined viseme list, "entries":
        per-line clips with character_id + timing, used by the animation
        stage to know who is speaking at every point in the scene}."""
        voice_by_scene: dict[str, dict] = {}
        LINE_GAP = 0.35  # seconds of silence between consecutive lines in a scene

        for scene in scenes:
            scene_dir = paths["scenes"] / scene.id
            raw_lines = scene.dialogue_lines or []
            entries = []
            cursor = 0.0

            for i, line in enumerate(raw_lines):
                char_id = line.get("character_id")
                voice_profile = profiles[char_id].voice_profile if char_id in profiles else "friendly_neutral"
                out_path = scene_dir / f"voice_{i:02d}.wav"
                clip = self.voice_engine.synthesize_line(line["text"], voice_profile, out_path)

                entries.append(
                    {
                        "character_id": char_id,
                        "path": clip.audio_path,
                        "duration": clip.duration_seconds,
                        "visemes": clip.visemes,
                        "start_offset": cursor,
                    }
                )
                # Real timestamps, written back onto the stored line so
                # subtitles line up with what's actually spoken.
                line["start"] = round(cursor, 2)
                line["end"] = round(cursor + clip.duration_seconds, 2)
                cursor += clip.duration_seconds + LINE_GAP

            total_dialogue_duration = max(0.0, cursor - LINE_GAP) if entries else 0.0

            combined_path, combined_visemes = None, []
            if entries:
                combined_path = scene_dir / "voice_combined.wav"
                combined_visemes = concatenate_voice_clips(entries, combined_path, gap=LINE_GAP)

            # Never truncate dialogue: extend the scene if the recorded
            # lines run longer than the narration-based duration estimate.
            if total_dialogue_duration > scene.duration_seconds:
                scene.duration_seconds = round(total_dialogue_duration + 0.5, 1)

            scene.dialogue_lines = raw_lines  # persist the start/end timestamps just added
            voice_by_scene[scene.id] = {
                "path": combined_path,
                "duration": total_dialogue_duration,
                "visemes": combined_visemes,
                "entries": entries,
            }
            scene.status = "voiced"

        db.commit()
        return voice_by_scene

    # -- stage 5: animation + lip sync -----------------------------------------

    def _animate(
        self,
        scenes: list[Scene],
        profiles: dict[str, CharacterVisualProfile],
        env_by_scene: dict[str, Path],
        voice_by_scene: dict[str, dict],
        paths: dict,
    ) -> dict[str, Path]:
        clip_by_scene: dict[str, Path] = {}

        for scene in scenes:
            scene_dir = paths["scenes"] / scene.id
            on_screen = [(cid, profiles[cid]) for cid in (scene.character_ids or []) if cid in profiles]

            voice_data = voice_by_scene.get(scene.id) or {}
            entries = voice_data.get("entries", [])
            # Who is actually speaking at each moment in the scene, so the
            # right character's mouth animates as dialogue switches speaker
            # (instead of one fixed "speaker" moving their mouth all scene).
            speaker_timeline = [
                {"character_id": e["character_id"], "start": e["start_offset"], "end": e["start_offset"] + e["duration"]}
                for e in entries
                if e["character_id"]
            ]
            frame_visemes = self.lipsync_engine.build_frame_visemes(
                voice_data.get("visemes", []), scene.duration_seconds, FPS
            )

            out_path = scene_dir / "silent_clip.mp4"
            self.animation_engine.render_scene_clip(
                environment_path=env_by_scene[scene.id],
                on_screen_characters=on_screen,
                speaker_timeline=speaker_timeline,
                frame_visemes=frame_visemes,
                emotion=scene.emotion,
                camera_movement=scene.camera_movement,
                duration=scene.duration_seconds,
                fps=FPS,
                out_path=out_path,
                tmp_frames_dir=scene_dir / "frames",
            )
            clip_by_scene[scene.id] = out_path
            scene.image_path = str(env_by_scene[scene.id])
            scene.status = "animated"

        return clip_by_scene

    # -- stage 6: music/ambience/SFX mix ---------------------------------------

    def _generate_audio(
        self, db: Session, scenes: list[Scene], voice_by_scene: dict[str, dict], paths: dict
    ) -> dict[str, Path]:
        mixed_by_scene: dict[str, Path] = {}

        for scene in scenes:
            scene_dir = paths["scenes"] / scene.id
            voice_data = voice_by_scene.get(scene.id) or {}
            voice_path = voice_data.get("path")

            ambience_tags = self.environment_engine.ambience_for(scene.location)
            out_path = scene_dir / "mixed_audio.wav"
            self.audio_engine.mix_scene_audio(
                duration=scene.duration_seconds,
                music_mood=scene.music_mood,
                sfx_tags=scene.sfx_tags or [],
                ambience_tags=ambience_tags,
                voice_path=voice_path,
                out_path=out_path,
            )
            mixed_by_scene[scene.id] = out_path
            scene.mixed_audio_path = str(out_path)
            scene.voice_audio_path = str(voice_path) if voice_path else ""
            scene.status = "audio_ready"

        db.commit()
        return mixed_by_scene

    # -- stage 7: final render --------------------------------------------------

    def _render_final(
        self,
        db: Session,
        project: Project,
        scenes: list[Scene],
        silent_clip_by_scene: dict[str, Path],
        mixed_audio_by_scene: dict[str, Path],
        paths: dict,
    ) -> None:
        scene_final_clips: list[Path] = []
        for scene in scenes:
            scene_dir = paths["scenes"] / scene.id
            final_clip = scene_dir / "final_clip.mp4"
            self.render_engine.mux_scene(
                silent_clip_by_scene[scene.id], mixed_audio_by_scene[scene.id], final_clip
            )
            scene.clip_path = str(final_clip)
            scene.status = "rendered"
            scene_final_clips.append(final_clip)

        render_dir = paths["render"]
        final_video = render_dir / "final_movie.mp4"
        self.render_engine.concatenate(scene_final_clips, final_video, tmp_dir=paths["tmp"])

        thumbnail = render_dir / "thumbnail.png"
        self.render_engine.generate_thumbnail(final_video, thumbnail)

        subtitles = render_dir / "subtitles.srt"
        self.render_engine.generate_subtitles(scenes, subtitles)

        project.video_path = str(final_video)
        project.thumbnail_path = str(thumbnail)
        project.subtitle_path = str(subtitles)
        db.commit()

    # -- helpers ----------------------------------------------------------------

    def _project_paths(self, project_id: str) -> dict:
        root = settings.PROJECTS_DIR / project_id
        paths = {
            "root": root,
            "characters": root / "characters",
            "environments": root / "environments",
            "scenes": root / "scenes",
            "tmp": settings.TEMP_DIR / project_id,
            "render": settings.RENDERS_DIR / project_id,
        }
        for p in paths.values():
            p.mkdir(parents=True, exist_ok=True)
        return paths

    def _set_stage(self, db: Session, project: Project, stage: str, percent: int) -> None:
        project.status = stage
        project.current_stage = stage
        project.progress_percent = percent
        db.commit()
        logger.info("Project {} -> stage={} ({}%)", project.id, stage, percent)

    def _mark_cancelled(self, db: Session, project: Project) -> None:
        project.status = "failed"
        project.error_message = "Cancelled by user"
        db.commit()

    def cleanup_temp(self, project_id: str) -> None:
        tmp = settings.TEMP_DIR / project_id
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
