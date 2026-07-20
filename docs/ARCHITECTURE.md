# Architecture

## 1. High-level flow

```
User (React SPA)
   │  fills in title, prompt, story, dialogue, characters, duration, style
   ▼
POST /api/v1/projects            → creates Project + Character rows (status=draft)
POST /api/v1/generation/{id}/start → enqueues MoviePipeline.run() on a worker thread
   │
   ▼
MoviePipeline (backend/app/services/pipeline.py)
   1. analyze_story          Story Engine        → Scene rows (location, emotion, camera, SFX, dialogue)
   2. generate_characters    Character Engine     → consistent visual profile + reference image per character
   3. generate_environments  Environment Engine    → one cached background image per unique location
   4. generate_voice         Voice Engine          → one WAV + viseme envelope per dialogue line
   5. animate                Animation Engine      → Lip Sync Engine quantizes visemes; Ken Burns camera
                                                       move; characters composited per frame; ffmpeg encodes
                                                       a silent clip per scene
   6. generate_audio         Audio Engine          → generative music bed + ambience + requested SFX +
                                                       dialogue mixed into one WAV per scene
   7. render                 Render Engine         → mux video+audio per scene, concatenate all scenes,
                                                       generate thumbnail + .srt subtitles
   8. completed               Project.video_path / .subtitle_path / .thumbnail_path set
   │
   ▼
Frontend polls GET /generation/{id}/status every ~1.5s → Generation Progress screen
   │  on completion
   ▼
GET /projects/{id}  → Preview screen streams the finished MP4 (auth'd blob fetch) + scene breakdown
   │
   ▼
POST /render/{id}/export → Export screen: re-encode to a resolution preset, optional subtitle burn-in
GET /storage/{id}/video  → download
```

## 2. Data model

- **User** — auth + `preferences` JSON (theme, default style, notification flags).
- **Project** — one movie: input fields (title/prompt/story/dialogue/style/duration), lifecycle
  `status`/`current_stage`/`progress_percent`, and output paths (video/thumbnail/subtitles).
- **Character** — belongs to a Project. `consistency_seed` (assigned once) deterministically
  drives the same palette/build/face/feature/voice every time that character is drawn — this is
  the mechanism behind "consistent characters throughout the movie."
- **Scene** — belongs to a Project, one row per story beat: location/time/emotion/camera move,
  `sfx_tags`, `music_mood`, `dialogue_lines` (character + text), and per-stage asset paths
  (image, voice, mixed audio, final clip) plus a `status` so partial progress is inspectable.

## 3. Why a rule-based pipeline by default

Photoreal 3D generation, professional voice cloning and licensed sound libraries all require
paid third-party services (GPU-hosted diffusion/3D models, neural TTS, music APIs) and API
keys that differ per deployment. Rather than hard-coding one vendor, every AI stage is an
abstract interface with:

1. a dependency-free, deterministic **placeholder implementation** (numpy/Pillow/ffmpeg only),
   so the product works immediately, end-to-end, in any environment — including ones with no
   internet access — and is free to run;
2. a **provider seam** (`get_story_engine()`, `get_image_gen_provider()`, `get_voice_provider()`)
   that automatically swaps in a real API-backed implementation the moment a key is configured,
   with an identical return type, so nothing downstream changes.

This mirrors how real animation studios work today: scratch dialogue and animatics (rough,
fast, free placeholders) are produced first to lock timing and story, then replaced with final
voice/art/animation later in the pipeline — the difference here is the "final" pass is a config
flag away instead of a re-shoot.

## 4. Character consistency mechanism

1. At project creation, each `Character` gets a random `consistency_seed` (an integer), stored once.
2. `CharacterEngine.build_profile(seed=...)` derives palette, build, face shape and a
   distinguishing feature **deterministically** from that seed (same seed → same outputs, every
   time, in every scene, across the whole movie).
3. The Animation Engine draws that same profile in every scene the character appears in;
   the Voice Engine uses the character's stored `voice_profile` for every line.
4. Environments follow the same idea: `EnvironmentEngine` caches one rendered background per
   unique `(location, time_of_day)` pair, so returning to "the forest" later in the story reuses
   the same art instead of regenerating a different-looking one.

## 5. Automatic scene splitting & sound design

`StoryEngine` (backend/app/services/ai/story_engine.py):
- Splits the story on paragraph breaks (or evenly by sentence count if the story is one block).
- Scores each scene's text against keyword lexicons to pick a **location**, **time of day**,
  and **emotion** (which also sets the music mood).
- Picks a **camera movement** (`static/pan/zoom_in/zoom_out/dolly`) — actions verbs bias toward
  `dolly`, the opening scene defaults to an establishing `pan`, otherwise cycles for variety.
- Scans for the exact SFX categories requested in the brief — **footsteps, rain, thunder, wind,
  birds, explosions, doors, vehicles, animal sounds** — via keyword matching, and separately adds
  location-based **ambience** (e.g. forest → wind+birds, city → traffic hum).
- Parses a `NAME: line` dialogue script and assigns each line to the scene that mentions that
  character (falling back to round-robin so no line is ever dropped).
- Distributes the user's requested runtime across scenes proportional to each scene's word count.

## 6. Lip sync

`VoiceEngine` returns a **viseme envelope** (mouth-openness sampled once per syllable) alongside
every synthesized line. `LipSyncEngine` resamples that envelope onto the movie's actual frame
rate and quantizes it into 4 mouth shapes (`closed/small/medium/wide`). `AnimationEngine` draws
the matching mouth shape on the speaking character every single frame — dialogue is
lip-synced automatically, with no manual keyframing, and the same resampling step works
identically if the Voice Engine is swapped for ElevenLabs/OpenAI TTS.

## 7. Audio mixing

Every scene gets one mixed WAV: a generative chord-pad music bed (scale + tempo chosen by
emotion), a continuous ambience bed, discrete SFX synthesized on demand from the Story
Engine's tags, and the dialogue track — summed with tuned gain levels and peak-normalized to
avoid clipping. The Render Engine muxes that mixed audio against the (silent) animated video
per scene, then concatenates all scenes and generates a synchronized `.srt` from each scene's
dialogue/timing.

## 9. Known limitation this pipeline actively guards against

Keyword-based scene classification can never cover every possible story. When the Story
Engine can't classify a scene's location, it's tagged `generic_scene` — but `generic_scene`
means "unclassified," not "the same place as every other unclassified scene." Early versions
of this pipeline cached `generic_scene` the same way as a real named location (by
`location:time_of_day`), which meant **every unclassified scene in a movie reused the exact
same background image** — for stories whose vocabulary didn't hit the keyword list, this could
mean 5+ of 8 scenes rendering pixel-identical, making very different stories look like "the
same video." Fixed by keying unclassified scenes off the scene's own text instead, so each one
gets its own distinct (if generic) look while real, named locations still correctly reuse their
art on repeat visits. Location/emotion/SFX keyword matching also switched from naive substring
checks to word-boundary regex, since substring matching caused false positives like "love"
firing inside "loved" or "glove".

## 10. Extending to real production quality

| Want | Change |
|---|---|
| Better scene/emotion reasoning | Set `OPENAI_API_KEY` — `LLMStoryEngine` takes over automatically |
| Real illustrated/3D characters | Implement another `ImageGenProvider` (Stability stub included) and set `IMAGE_GEN_PROVIDER` |
| Studio-quality voices | Set `ELEVENLABS_API_KEY` / `VOICE_PROVIDER=elevenlabs` |
| Licensed music/SFX | Replace the generator functions in `audio_engine.py` with library lookups or a generative-audio API |
| Full 3D animation | Replace `AnimationEngine._draw_character`/environment rendering with a Blender/Unreal/text-to-video call, keeping the same per-scene clip contract |
| Multi-machine scale | Set `USE_CELERY=true` and use the Celery task template in `generation_worker.py` |
