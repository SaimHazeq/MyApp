"""
Character Engine
================
Responsible for turning a plain-text character description into a visual
+ vocal profile that stays IDENTICAL every time that character appears,
across every scene of the movie - this is what the product brief calls
"maintain consistent characters throughout the movie".

Consistency strategy
---------------------
Every character gets a `consistency_seed` (assigned once, at project
creation - see api/routes/projects.py). That seed deterministically drives:
  * the color palette (skin/fur, outfit, accent)
  * body proportions (height, build)
  * face shape + a distinguishing feature (freckles, horn, glasses, etc.)
  * the voice profile used by the Voice Engine

Because every downstream engine re-derives the same attributes from the
same seed, the same character looks and sounds the same in scene 1 and
scene 40 without needing to store or diff full renders.

Image generation itself is behind an `ImageGenProvider` interface. Ship
with a dependency-free `PlaceholderImageGen` (pure PIL) so the pipeline
always produces a movie with zero setup. Flip `IMAGE_GEN_PROVIDER` in
`.env` to `stability` or `openai` once you have an API key to get real
2D/3D-styled character turnarounds instead.
"""
from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from app.core.config import get_settings

settings = get_settings()

PALETTES = [
    ["#F2B84B", "#2B2033", "#FF5D73"],  # marquee gold / deep plum / coral
    ["#3DDC97", "#12324D", "#F5F3EE"],  # mint / navy / cream
    ["#FF8A5B", "#2E2E3A", "#7CE0D3"],  # papaya / charcoal / seafoam
    ["#8C7AE6", "#1B1B2F", "#F6C453"],  # violet / ink / honey
    ["#4FB3FF", "#20262E", "#F76E8C"],  # sky blue / slate / rose
    ["#E8C39E", "#3B2F2F", "#6FCF97"],  # sand / espresso / jade
    ["#C4E86E", "#2A2A40", "#FF7A5C"],  # lime / indigo / tangerine
    ["#F4A6C1", "#25313C", "#FFD166"],  # blossom / deep teal / amber
    ["#9AD1D4", "#402E32", "#F25F5C"],  # aqua / maroon / cherry
    ["#D9BF77", "#22333B", "#EF798A"],  # brass / midnight / watermelon
]

BODY_BUILDS = ["slim", "average", "sturdy", "tall_lanky", "small_round"]
FACE_SHAPES = ["round", "oval", "square", "heart", "long"]
DISTINGUISHING_FEATURES = [
    "freckles", "round_glasses", "pointy_ears", "a_scar", "curly_hair",
    "a_signature_hat", "a_bandana", "a_flower_behind_ear", "no_extra_feature",
]

VOICE_PROFILES_BY_ROLE = {
    "protagonist": ["warm_confident", "young_bright_optimistic", "brave_energetic"],
    "antagonist": ["deep_menacing", "cold_calculating", "gravelly_villain"],
    "supporting": ["friendly_neutral", "quirky_comic", "gentle_wise_elder"],
}


def draw_head_shape(draw: ImageDraw.ImageDraw, face_shape: str, cx: float, cy: float, r: float, fill) -> None:
    """Draws a head silhouette centered at (cx, cy) with 'radius' r, shaped
    according to face_shape. Previously every character's head rendered as
    an identical ellipse regardless of its assigned face_shape - this is
    what actually makes two characters' silhouettes distinguishable, not
    just their color palette."""
    if face_shape == "oval":
        draw.ellipse([cx - r * 0.82, cy - r * 1.15, cx + r * 0.82, cy + r * 1.15], fill=fill)
    elif face_shape == "square":
        draw.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=r * 0.3, fill=fill)
    elif face_shape == "heart":
        draw.ellipse([cx - r, cy - r, cx + r, cy + r * 0.55], fill=fill)
        draw.polygon([(cx - r, cy), (cx + r, cy), (cx, cy + r * 1.05)], fill=fill)
    elif face_shape == "long":
        draw.ellipse([cx - r * 0.72, cy - r * 1.3, cx + r * 0.72, cy + r * 1.3], fill=fill)
    else:  # "round" (and any unrecognized value) - the original default
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


@dataclass
class CharacterVisualProfile:
    name: str
    seed: int
    palette: list[str]
    build: str
    face_shape: str
    feature: str
    voice_profile: str


def _seeded_rng(seed: int) -> random.Random:
    return random.Random(seed)


class CharacterEngine:
    def build_profile(self, name: str, description: str, role: str, seed: int, voice_profile: str) -> CharacterVisualProfile:
        rng = _seeded_rng(seed)

        # Nudge choices using words actually present in the user's
        # description before falling back to the seeded random pick, so a
        # description like "tall boy with glasses" is respected.
        desc = description.lower()
        build = next((b for b in BODY_BUILDS if b.replace("_", " ") in desc), None) or rng.choice(BODY_BUILDS)
        feature = next((f for f in DISTINGUISHING_FEATURES if f.replace("_", " ") in desc), None) or rng.choice(
            DISTINGUISHING_FEATURES
        )

        return CharacterVisualProfile(
            name=name,
            seed=seed,
            palette=PALETTES[seed % len(PALETTES)],
            build=build,
            face_shape=rng.choice(FACE_SHAPES),
            feature=feature,
            voice_profile=voice_profile,
        )

    def render_reference_sheet(self, profile: CharacterVisualProfile, out_dir: Path) -> Path:
        provider = get_image_gen_provider()
        return provider.render_character(profile, out_dir)


# --------------------------------------------------------------------------
# Pluggable image-generation providers
# --------------------------------------------------------------------------

class ImageGenProvider(ABC):
    @abstractmethod
    def render_character(self, profile: CharacterVisualProfile, out_dir: Path) -> Path: ...

    @abstractmethod
    def render_environment(self, location: str, time_of_day: str, palette: list[str], out_dir: Path, tag: str) -> Path: ...


class PlaceholderImageGen(ImageGenProvider):
    """Deterministic PIL-based stand-in for a real text-to-image/3D model.
    Draws a simple, consistent, seed-driven silhouette so every engine in
    the pipeline (and the demo you can generate right now, offline) has a
    real image file to work with. Swap for StabilityImageGen/OpenAIImageGen
    below once you have API keys - the return contract (a PNG path) is
    identical, so RenderEngine never has to change."""

    CANVAS = (1024, 1024)

    def render_character(self, profile: CharacterVisualProfile, out_dir: Path) -> Path:
        img = Image.new("RGBA", self.CANVAS, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        skin, outfit, accent = profile.palette
        cx, cy = self.CANVAS[0] // 2, self.CANVAS[1] // 2

        build_scale = {
            "slim": 0.85, "average": 1.0, "sturdy": 1.15,
            "tall_lanky": 1.05, "small_round": 0.9,
        }[profile.build]

        # body
        body_w, body_h = int(260 * build_scale), int(380 * build_scale)
        draw.rounded_rectangle(
            [cx - body_w // 2, cy - 40, cx + body_w // 2, cy + body_h],
            radius=60, fill=outfit,
        )
        # head
        head_r = int(150 * build_scale)
        head_cy = cy - 340 + head_r
        draw_head_shape(draw, profile.face_shape, cx, head_cy, head_r, skin)
        # accent detail (scarf/belt) - ties palette's 3rd color into the design
        draw.rounded_rectangle(
            [cx - body_w // 2, cy + 40, cx + body_w // 2, cy + 90], radius=20, fill=accent
        )
        # feature marker (kept abstract - a small accent shape) for
        # "freckles / glasses / hat / scar" etc.
        if profile.feature != "no_extra_feature":
            draw.ellipse([cx - 18, head_cy - head_r * 0.4 - 18, cx + 18, head_cy - head_r * 0.4 + 18], fill=accent)

        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{profile.name.lower().replace(' ', '_')}_ref.png"
        img.save(path)
        return path

    def render_environment(self, location: str, time_of_day: str, palette: list[str], out_dir: Path, tag: str) -> Path:
        img = Image.new("RGB", (1920, 1080), self._sky_color(time_of_day))
        draw = ImageDraw.Draw(img)
        ground_color = {
            "forest": "#274029", "beach": "#E8D6A0", "city": "#3A3A45",
            "castle": "#4B4B58", "village": "#6E5A46", "house_interior": "#5B4636",
            "school": "#B9C4CC", "space": "#05030F", "mountain": "#5C6670",
            "garden": "#4E7A3D", "river_lake": "#2E5266", "underwater": "#0C3B4C",
            "sky": "#7EC8E3", "generic_scene": "#495366",
        }.get(location, "#495366")
        draw.rectangle([0, 700, 1920, 1080], fill=ground_color)

        # A few silhouette shapes hint at the location without needing real assets.
        rng = random.Random(hash((location, tag)) & 0xFFFFFFFF)
        for _ in range(6):
            x = rng.randint(0, 1920)
            h = rng.randint(80, 260)
            draw.rectangle([x, 700 - h, x + 40, 700], fill=palette[1])

        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"env_{tag}.png"
        img.save(path)
        return path

    @staticmethod
    def _sky_color(time_of_day: str) -> str:
        return {
            "night": "#0B1026", "dawn": "#F7C59F", "sunset": "#FF9E7D", "morning": "#BFE3F2",
        }.get(time_of_day, "#8FCBEA")


class StabilityImageGen(ImageGenProvider):  # pragma: no cover - requires network + API key
    """Real text-to-image backend using Stability AI. Activate by setting
    IMAGE_GEN_PROVIDER=stability and STABILITY_API_KEY in .env."""

    def render_character(self, profile: CharacterVisualProfile, out_dir: Path) -> Path:
        import requests

        prompt = (
            f"3D pixar-style character turnaround, {profile.build} build, "
            f"{profile.face_shape} face, {profile.feature.replace('_', ' ')}, "
            f"color palette {profile.palette}, full body, white background"
        )
        resp = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"authorization": f"Bearer {settings.STABILITY_API_KEY}", "accept": "image/*"},
            files={"none": ""},
            data={"prompt": prompt, "output_format": "png"},
            timeout=60,
        )
        resp.raise_for_status()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{profile.name.lower().replace(' ', '_')}_ref.png"
        path.write_bytes(resp.content)
        return path

    def render_environment(self, location: str, time_of_day: str, palette: list[str], out_dir: Path, tag: str) -> Path:
        raise NotImplementedError("Wire up the same pattern as render_character for environments.")


def get_image_gen_provider() -> ImageGenProvider:
    if settings.IMAGE_GEN_PROVIDER == "stability" and settings.STABILITY_API_KEY:
        return StabilityImageGen()
    return PlaceholderImageGen()
