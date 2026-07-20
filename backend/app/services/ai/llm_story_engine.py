"""
Optional drop-in replacement for StoryEngine that delegates scene
splitting, emotion tagging and camera-direction reasoning to an LLM
(OpenAI) instead of the offline keyword heuristics. Returns the exact same
`ScenePlan`/`DialogueLine` shape, so `MoviePipeline` never needs to know
which engine produced the plan.

Only imported/instantiated when `OPENAI_API_KEY` is set (see
`story_engine.get_story_engine`), and any failure here silently falls back
to the offline `StoryEngine` so a bad key or a network blip never breaks
generation for the user.
"""
from __future__ import annotations

import json
from typing import Optional

from openai import OpenAI

from app.core.config import get_settings
from app.services.ai.story_engine import (
    DialogueLine,
    ScenePlan,
    StoryEngine,
    _duration_per_scene,
)

settings = get_settings()

SYSTEM_PROMPT = """You are a professional animated-film story editor. Break the
given story into cinematic scenes for a 3D animated movie. Respond ONLY with
JSON matching this schema:
{
  "scenes": [
    {
      "text": "scene description",
      "location": "one short location tag",
      "time_of_day": "day|night|dawn|sunset|morning",
      "emotion": "joyful|sad|tense|angry|romantic|epic|calm|neutral",
      "camera_movement": "static|pan|zoom_in|zoom_out|dolly",
      "sfx_tags": ["footsteps","rain","thunder","wind","birds","explosions","doors","vehicles","animals"],
      "dialogue": [{"character_name": "NAME", "text": "line"}]
    }
  ]
}
Only include sfx_tags that are actually implied by the scene. Keep the
number of scenes proportional to story length."""


class LLMStoryEngine(StoryEngine):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def analyze(
        self,
        story: str,
        dialogue: str,
        duration_minutes: float,
        character_names: Optional[list[str]] = None,
    ) -> list[ScenePlan]:
        total_seconds = max(10.0, duration_minutes * 60)
        user_prompt = (
            f"Characters: {', '.join(character_names or [])}\n\n"
            f"STORY:\n{story}\n\nDIALOGUE SCRIPT (if any):\n{dialogue}\n\n"
            f"Target total runtime: {total_seconds:.0f} seconds."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            data = json.loads(response.choices[0].message.content)
            raw_scenes = data["scenes"]
        except Exception:
            # Any parsing/API failure: fall back to the deterministic engine
            # rather than let the whole generation job fail.
            return StoryEngine().analyze(story, dialogue, duration_minutes, character_names)

        texts = [s.get("text", "") for s in raw_scenes]
        durations = _duration_per_scene(texts, total_seconds)

        scenes: list[ScenePlan] = []
        for i, s in enumerate(raw_scenes):
            dialogue_lines = [
                DialogueLine(character_name=d.get("character_name", "Narrator"), text=d.get("text", ""))
                for d in s.get("dialogue", [])
            ]
            scenes.append(
                ScenePlan(
                    index=i,
                    text=s.get("text", ""),
                    location=s.get("location", "generic_scene"),
                    time_of_day=s.get("time_of_day", "day"),
                    emotion=s.get("emotion", "neutral"),
                    camera_movement=s.get("camera_movement", "static"),
                    duration_seconds=durations[i],
                    sfx_tags=s.get("sfx_tags", []),
                    music_mood=s.get("emotion", "neutral"),
                    dialogue_lines=dialogue_lines,
                )
            )
        return scenes
