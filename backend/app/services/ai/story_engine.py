"""
Story Engine
============
Turns free-form story text + dialogue into a structured list of scenes that
the rest of the pipeline (character engine, environment engine, animation
engine, voice engine, audio engine, render engine) can consume.

This is a deterministic, rule-based implementation (keyword/heuristic NLP)
so the whole pipeline runs with zero external dependencies and zero API
keys. If OPENAI_API_KEY is configured, `LLMStoryEngine` below sends the same
job to an LLM for materially better scene/emotion/camera reasoning and
returns the identical data shape - nothing downstream needs to change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

# --- Keyword lexicons -------------------------------------------------------

LOCATION_KEYWORDS = {
    "forest": ["forest", "woods", "trees", "tree", "jungle", "wood"],
    "castle": ["castle", "palace", "throne", "kingdom", "fortress"],
    "beach": ["beach", "shore", "sand", "ocean", "sea", "waves"],
    "city": ["city", "street", "alley", "downtown", "rooftop", "skyscraper", "town"],
    "village": ["village", "town square", "market"],
    "house_interior": ["house", "kitchen", "bedroom", "living room", "attic", "hallway",
                        "room", "door", "window", "table", "sofa", "apartment", "home"],
    "school": ["school", "classroom", "college", "university"],
    "space": ["space", "spaceship", "galaxy", "planet", "starship", "asteroid", "rocket", "alien", "orbit"],
    "mountain": ["mountain", "cliff", "peak", "cave", "cavern", "hill", "rocks"],
    "garden": ["garden", "meadow", "field", "flowers", "farm"],
    "river_lake": ["river", "lake", "stream", "waterfall", "creek", "bridge", "bank"],
    "underwater": ["underwater", "reef", "seabed", "coral reef"],
    "sky": ["sky", "clouds", "flying", "air"],
    "building_interior": ["building", "laboratory", "lab", "warehouse", "factory", "machine",
                           "machines", "workshop", "museum", "library", "office", "tower",
                           "basement", "chamber", "corridor"],
    "playground_park": ["playground", "park", "swing", "slide", "sandbox"],
    "vehicle_scene": ["road", "highway", "train station", "airport", "harbor", "dock",
                       "car", "truck", "train", "station"],
    "snow_scene": ["snow", "ice", "arctic", "winter", "blizzard", "frost"],
    "desert_scene": ["desert", "dune", "oasis"],
}

TIME_KEYWORDS = {
    "night": ["night", "midnight", "moon", "stars", "dark"],
    "dawn": ["dawn", "sunrise", "early morning"],
    "sunset": ["sunset", "dusk", "twilight"],
    "morning": ["morning"],
}

EMOTION_LEXICON = {
    "joyful": ["laugh", "happy", "smile", "joy", "delight", "cheer", "excited", "celebrat",
               "wonderful", "amazing", "cheerful", "giggle"],
    "sad": ["cry", "tears", "sad", "sorrow", "lonely", "grief", "miss"],
    "tense": ["fear", "scared", "danger", "chase", "run", "hide", "threat", "nervous",
              "worried", "anxious", "alarm", "urgent"],
    "angry": ["angry", "furious", "shout", "rage", "yell"],
    "romantic": ["in love", "romance", "kiss", "warm embrace"],
    "epic": ["battle", "fight", "roar", "explosion", "hero", "victory", "power"],
    "calm": ["peaceful", "quiet", "gentle breeze", "rest", "calm"],
    "wonder": ["curious", "wonder", "amazed", "mysterious", "discover", "explore", "strange", "glowing"],
}

# Exactly the sound-effect categories requested by the product brief.
SFX_LEXICON = {
    "footsteps": ["walk", "walked", "step", "steps", "ran", "running", "crept", "tiptoe"],
    "rain": ["rain", "raining", "drizzle", "downpour"],
    "thunder": ["thunder", "lightning", "storm"],
    "wind": ["wind", "breeze", "gust", "gale"],
    "birds": ["bird", "birds", "chirp", "sparrow", "eagle", "owl"],
    "explosions": ["explosion", "explode", "blast", "bomb", "boom"],
    "doors": ["door", "knock", "creak", "slam"],
    "vehicles": ["car", "truck", "train", "ship", "boat", "plane", "engine", "spaceship"],
    "animals": ["dog", "cat", "lion", "wolf", "horse", "roar", "bark", "growl", "howl"],
}

CAMERA_CYCLE = ["static", "pan", "zoom_in", "dolly", "zoom_out"]
ACTION_VERBS = ["ran", "chased", "jumped", "flew", "fought", "fight", "raced", "leapt", "attacked", "escaped"]

# --- Screenplay-style script parsing ----------------------------------------
# Real scripts look like:
#   Scene 1 — Den at the forest edge, before the storm
#   SFX: Soft morning forest sounds.
#   MOTHER FOX (gentle): Fira, stay close.
#   NARRATOR (optional): Fira had always listened more than leapt.
# The previous parser only understood a bare "NAME: line" and had no idea
# what to do with the parenthetical delivery note, the SFX cue, or the
# scene header - it silently dropped every character line whose name was
# followed by "(...)", and misread "SFX:" as a character named SFX.
SCENE_HEADER_RE = re.compile(r"^\s*scene\s+\d+\s*[-\u2013\u2014:]\s*(.*)$", re.IGNORECASE)
SFX_LINE_RE = re.compile(r"^\s*sfx\s*:\s*(.+)$", re.IGNORECASE)
NARRATOR_LINE_RE = re.compile(r"^\s*narrator\s*(?:\([^)]*\))?\s*:\s*(.+)$", re.IGNORECASE)
END_CARD_RE = re.compile(r"^\s*end title card\s*:\s*(.+)$", re.IGNORECASE)
# group 1 = character name, group 2 = optional parenthetical delivery note
# (discarded), group 3 = the spoken line.
CHARACTER_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 '\-]{0,39}?)\s*(?:\(([^)]*)\))?\s*:\s*(.+)$")


@dataclass
class DialogueLine:
    character_name: str
    text: str


@dataclass
class ScenePlan:
    index: int
    text: str
    location: str
    time_of_day: str
    emotion: str
    camera_movement: str
    duration_seconds: float
    sfx_tags: list[str]
    music_mood: str
    dialogue_lines: list[DialogueLine] = field(default_factory=list)


def _split_paragraphs(story: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", story.strip()) if p.strip()]
    return paras


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s]


def _chunk_into_scenes(story: str, target_scene_count: int) -> list[str]:
    """Prefer the author's own paragraph breaks as scene boundaries. If the
    story is a single block of text, group sentences evenly instead."""
    paragraphs = _split_paragraphs(story)
    if len(paragraphs) >= 2:
        return paragraphs

    sentences = _split_sentences(story)
    if not sentences:
        return [story]

    target_scene_count = max(1, min(target_scene_count, len(sentences)))
    per_scene = max(1, round(len(sentences) / target_scene_count))
    chunks = [
        " ".join(sentences[i:i + per_scene])
        for i in range(0, len(sentences), per_scene)
    ]
    return chunks


def _count_keyword(lowered_text: str, keyword: str) -> int:
    """Word-boundary match so 'love' doesn't fire on 'loved'/'glove', 'ran'
    doesn't fire inside 'orange', etc. Keyword may be a multi-word phrase
    (e.g. 'warm embrace'), which \\b still anchors correctly at each end."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return len(re.findall(pattern, lowered_text))


def _detect(text: str, lexicon: dict[str, list[str]], default: str) -> str:
    lowered = text.lower()
    scores = {key: sum(_count_keyword(lowered, kw) for kw in kws) for key, kws in lexicon.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else default


def _detect_sfx(text: str) -> list[str]:
    lowered = text.lower()
    tags = [tag for tag, kws in SFX_LEXICON.items() if any(_count_keyword(lowered, kw) for kw in kws)]
    return tags


def _detect_camera(text: str, index: int) -> str:
    lowered = text.lower()
    if any(_count_keyword(lowered, v) for v in ACTION_VERBS):
        return "dolly"
    if index == 0:
        return "pan"  # establishing shot for the opening scene
    return CAMERA_CYCLE[index % len(CAMERA_CYCLE)]


def _parse_dialogue_block(dialogue: str) -> list[DialogueLine]:
    """Parses a FLAT dialogue script (no explicit 'Scene N' headers) where
    each line looks like 'NAME: line' or 'NAME (delivery note): line'.
    SFX:/NARRATOR:/scene-header/title-card lines are recognized and handled
    rather than being misparsed as a character literally named e.g. 'SFX'."""
    lines = []
    for raw_line in dialogue.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        if SFX_LINE_RE.match(raw_line) or SCENE_HEADER_RE.match(raw_line) or END_CARD_RE.match(raw_line):
            continue
        narrator_match = NARRATOR_LINE_RE.match(raw_line)
        if narrator_match:
            lines.append(DialogueLine(character_name="Narrator", text=narrator_match.group(1).strip()))
            continue
        match = CHARACTER_LINE_RE.match(raw_line)
        if match:
            lines.append(DialogueLine(character_name=match.group(1).strip(), text=match.group(3).strip()))
    return lines


def _parse_structured_script(text: str) -> list[dict]:
    """Parses a screenplay-style script with explicit 'Scene N —' headers
    into per-scene blocks: {header, sfx_hints, narrator_lines, dialogue}.

    This is the authoritative path when present: the user has already told
    us exactly where each scene starts and what's said in it, which beats
    guessing scene boundaries from prose and fuzzy-matching a flat dialogue
    list back onto them by character name. Returns [] if no 'Scene N'
    header is found anywhere, which tells the caller to fall back to
    free-form paragraph splitting - plain prose input (no explicit scene
    markup) keeps working exactly as before."""
    blocks: list[dict] = []
    current: Optional[dict] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = SCENE_HEADER_RE.match(line)
        if header_match:
            current = {"header": header_match.group(1).strip(), "sfx_hints": [], "narrator_lines": [], "dialogue": []}
            blocks.append(current)
            continue

        if current is None:
            continue  # ignore any preamble before the first "Scene N" header

        sfx_match = SFX_LINE_RE.match(line)
        if sfx_match:
            current["sfx_hints"].append(sfx_match.group(1).strip())
            continue

        narrator_match = NARRATOR_LINE_RE.match(line)
        if narrator_match:
            current["narrator_lines"].append(narrator_match.group(1).strip())
            continue

        if END_CARD_RE.match(line):
            continue  # title card text isn't a scene element

        char_match = CHARACTER_LINE_RE.match(line)
        if char_match:
            current["dialogue"].append((char_match.group(1).strip(), char_match.group(3).strip()))
            continue

        # Unrecognized line inside a scene (e.g. a wrapped continuation) -
        # fold it into the header/description text rather than dropping it.
        current["header"] += " " + line

    return blocks


def _scenes_from_structured_blocks(blocks: list[dict], total_seconds: float) -> list[ScenePlan]:
    combined_texts = []
    for b in blocks:
        parts = [b["header"], *b["narrator_lines"], *b["sfx_hints"], *[t for _, t in b["dialogue"]]]
        combined_texts.append(" ".join(p for p in parts if p))

    durations = _duration_per_scene(combined_texts, total_seconds)

    scenes: list[ScenePlan] = []
    for i, (block, text) in enumerate(zip(blocks, combined_texts)):
        emotion = _detect(text, EMOTION_LEXICON, default="neutral")
        dialogue_lines = [DialogueLine(character_name=name, text=t) for name, t in block["dialogue"]]
        for narr_text in block["narrator_lines"]:
            dialogue_lines.append(DialogueLine(character_name="Narrator", text=narr_text))

        scenes.append(
            ScenePlan(
                index=i,
                text=text,
                location=_detect(text, LOCATION_KEYWORDS, default="generic_scene"),
                time_of_day=_detect(text, TIME_KEYWORDS, default="day"),
                emotion=emotion,
                camera_movement=_detect_camera(text, i),
                duration_seconds=durations[i],
                sfx_tags=_detect_sfx(text),
                music_mood=emotion,
                dialogue_lines=dialogue_lines,
            )
        )
    return scenes


def _assign_dialogue_to_scenes(scenes_text: list[str], dialogue_lines: list[DialogueLine]) -> list[list[DialogueLine]]:
    """Assigns each parsed dialogue line to a scene.

    Groups lines by character (preserving script order within each group),
    finds every scene that mentions that character by name, and distributes
    that character's lines proportionally across those scenes in order -
    e.g. a character with 4 lines appearing in 2 scenes gets lines 1-2 in
    the first scene and lines 3-4 in the second, instead of every one of
    their lines collapsing into whichever scene mentions them first.
    Characters never mentioned by name in the narration (or an empty story)
    have their lines spread evenly across the whole scene sequence, so
    nothing is ever silently dropped."""
    n_scenes = len(scenes_text)
    assigned: list[list[DialogueLine]] = [[] for _ in range(n_scenes)]
    if n_scenes == 0:
        return assigned

    by_character: dict[str, list[DialogueLine]] = {}
    order: list[str] = []
    for line in dialogue_lines:
        key = line.character_name.lower()
        if key not in by_character:
            by_character[key] = []
            order.append(key)
        by_character[key].append(line)

    for key in order:
        lines = by_character[key]
        mention_scenes = [i for i, text in enumerate(scenes_text) if key in text.lower()]
        if not mention_scenes:
            mention_scenes = list(range(n_scenes))

        for idx, line in enumerate(lines):
            bucket = mention_scenes[min(len(mention_scenes) - 1, (idx * len(mention_scenes)) // len(lines))]
            assigned[bucket].append(line)

    return assigned


def _duration_per_scene(scenes_text: list[str], total_seconds: float) -> list[float]:
    word_counts = [max(1, len(t.split())) for t in scenes_text]
    total_words = sum(word_counts)
    raw = [total_seconds * (wc / total_words) for wc in word_counts]
    clamped = [max(3.0, min(20.0, d)) for d in raw]

    # Re-normalize so the sum still matches the user's requested runtime.
    scale = total_seconds / sum(clamped) if sum(clamped) else 1
    return [round(d * scale, 1) for d in clamped]


class StoryEngine:
    """Rule-based story analysis & scene splitter (offline, deterministic)."""

    def analyze(
        self,
        story: str,
        dialogue: str,
        duration_minutes: float,
        character_names: Optional[list[str]] = None,
    ) -> list[ScenePlan]:
        total_seconds = max(10.0, duration_minutes * 60)

        # Prefer an explicit, user-authored script (scene headers + per-scene
        # SFX/dialogue) when present - it's authoritative and beats guessing
        # scene boundaries from prose and fuzzy-matching dialogue onto them.
        structured = _parse_structured_script(dialogue) if dialogue.strip() else []
        if not structured:
            structured = _parse_structured_script(story) if story.strip() else []
        if structured:
            return _scenes_from_structured_blocks(structured, total_seconds)

        # Aim for one scene roughly every 8-12 seconds of runtime.
        target_scene_count = max(3, round(total_seconds / 10))

        scenes_text = _chunk_into_scenes(story, target_scene_count)
        durations = _duration_per_scene(scenes_text, total_seconds)
        dialogue_lines = _parse_dialogue_block(dialogue) if dialogue.strip() else []
        assigned_dialogue = _assign_dialogue_to_scenes(scenes_text, dialogue_lines)

        scenes: list[ScenePlan] = []
        for i, text in enumerate(scenes_text):
            emotion = _detect(text, EMOTION_LEXICON, default="neutral")
            scenes.append(
                ScenePlan(
                    index=i,
                    text=text,
                    location=_detect(text, LOCATION_KEYWORDS, default="generic_scene"),
                    time_of_day=_detect(text, TIME_KEYWORDS, default="day"),
                    emotion=emotion,
                    camera_movement=_detect_camera(text, i),
                    duration_seconds=durations[i],
                    sfx_tags=_detect_sfx(text),
                    music_mood=emotion,
                    dialogue_lines=assigned_dialogue[i],
                )
            )
        return scenes


def get_story_engine() -> StoryEngine:
    """Factory used by the pipeline. Swaps in an LLM-backed engine
    automatically once an OpenAI key is configured, with an identical
    return type so nothing else in the pipeline has to change."""
    if settings.OPENAI_API_KEY:
        try:
            from app.services.ai.llm_story_engine import LLMStoryEngine
            return LLMStoryEngine()
        except Exception:  # pragma: no cover - safe fallback
            pass
    return StoryEngine()
