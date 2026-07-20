"""
Environment Engine
==================
Generates the background/set for each scene. Re-uses the same rendered
background whenever a location repeats later in the story (e.g. the hero
returns to the same forest in scene 8 as in scene 2) so the world stays
visually consistent, and layers in a location-appropriate ambient bed
(wind/birds/waves/traffic hum) that the Audio Engine mixes underneath the
scene-specific sound effects and music.
"""
from __future__ import annotations

from pathlib import Path

from app.services.ai.character_engine import get_image_gen_provider

AMBIENCE_BY_LOCATION = {
    "forest": ["wind", "birds"],
    "beach": ["wind"],
    "city": ["vehicles"],
    "castle": ["wind"],
    "village": ["birds"],
    "house_interior": [],
    "school": [],
    "space": [],
    "mountain": ["wind"],
    "garden": ["birds"],
    "river_lake": ["wind"],
    "underwater": [],
    "sky": ["wind"],
    "building_interior": [],
    "playground_park": ["birds"],
    "vehicle_scene": ["vehicles"],
    "snow_scene": ["wind"],
    "desert_scene": ["wind"],
    "generic_scene": [],
}


class EnvironmentEngine:
    def __init__(self) -> None:
        self.provider = get_image_gen_provider()
        self._cache: dict[str, Path] = {}

    def build_environment(
        self, location: str, time_of_day: str, palette: list[str], out_dir: Path, variation_key: str = ""
    ) -> Path:
        """Renders (and caches) one background per unique location. A real,
        named location (forest, castle, ...) is cached by location+time so
        repeat visits reuse the same art - that's intentional consistency.

        `generic_scene` is different: it means "the Story Engine couldn't
        classify this scene," NOT "this is the same place as every other
        unclassified scene." Caching it the same way collapsed every
        unrecognized scene in a movie onto one identical image - the exact
        cause of "every video looks the same" for stories whose vocabulary
        doesn't hit the location keyword list. So unclassified scenes are
        keyed by `variation_key` (the scene's own text) instead, giving each
        one its own distinct-but-reproducible look."""
        if location == "generic_scene" and variation_key:
            cache_key = f"{location}:{time_of_day}:{hash(variation_key) & 0xFFFFFFFF}"
        else:
            cache_key = f"{location}:{time_of_day}"

        if cache_key in self._cache and self._cache[cache_key].exists():
            return self._cache[cache_key]

        path = self.provider.render_environment(location, time_of_day, palette, out_dir, tag=cache_key)
        self._cache[cache_key] = path
        return path

    def ambience_for(self, location: str) -> list[str]:
        return AMBIENCE_BY_LOCATION.get(location, [])
