"""
Audio Engine
============
Builds the full audio bed for a scene:
  1. background score - a generative chord pad whose scale/tempo matches
     the scene's detected emotion
  2. ambience - a continuous low-level bed for the location (wind, birds...)
  3. discrete sound effects - footsteps, rain, thunder, wind, birds,
     explosions, doors, vehicles, animals - exactly the categories in the
     product brief, triggered by keywords the Story Engine found in the text
  4. the character dialogue (voice track) from the Voice Engine

...then mixes all four into one scene-length WAV that the Render Engine
muxes against the video.

Everything here is pure numpy DSP so it runs with zero external services.
`MUSIC_PROVIDER=elevenlabs` (see get_music_provider) is the seam for
swapping in a real generative-music/SFX API later without touching the
mixing logic below.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.services.ai.voice_engine import SAMPLE_RATE, _write_wav

settings = get_settings()

# --- Music theory: pick a scale + tempo per emotion -------------------------

NOTE_HZ = {  # one octave, A3-based, just for simple pad chords
    "A": 220.00, "B": 246.94, "C": 261.63, "D": 293.66,
    "E": 329.63, "F": 349.23, "G": 392.00,
}

MOOD_SCALES = {
    "joyful": (["C", "E", "G"], 128),
    "sad": (["A", "C", "E"], 66),
    "tense": (["A", "B", "D"], 100),
    "angry": (["D", "F", "A"], 140),
    "romantic": (["F", "A", "C"], 80),
    "epic": (["D", "F", "G"], 118),
    "calm": (["C", "E", "G"], 70),
    "neutral": (["C", "E", "G"], 90),
}


def _tone(freq: float, duration: float, amp: float = 0.2, harmonics: tuple[float, ...] = (1.0, 0.5, 0.25)) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    wave_sum = sum(h * np.sin(2 * np.pi * freq * (i + 1) * t) for i, h in enumerate(harmonics))
    return (amp * wave_sum / sum(harmonics)).astype(np.float32)


def _fade(signal: np.ndarray, fade_s: float = 0.05) -> np.ndarray:
    n = min(int(SAMPLE_RATE * fade_s), len(signal) // 2)
    if n <= 0:
        return signal
    ramp = np.linspace(0, 1, n)
    signal = signal.copy()
    signal[:n] *= ramp
    signal[-n:] *= ramp[::-1]
    return signal


def _noise(duration: float, amp: float = 0.2, lowpass: float | None = None) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    noise = np.random.default_rng().normal(0, 1, n).astype(np.float32)
    if lowpass:
        # crude single-pole low-pass filter for a softer, less harsh noise bed
        alpha = lowpass
        for i in range(1, len(noise)):
            noise[i] = alpha * noise[i - 1] + (1 - alpha) * noise[i]
    return amp * noise / (np.abs(noise).max() + 1e-6)


def synthesize_music(mood: str, duration: float) -> np.ndarray:
    notes, bpm = MOOD_SCALES.get(mood, MOOD_SCALES["neutral"])
    beat = 60 / bpm
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    t_cursor = 0.0
    i = 0
    while t_cursor < duration:
        note = notes[i % len(notes)]
        chord_dur = beat * 2
        chord = _tone(NOTE_HZ[note], chord_dur, amp=0.12) + _tone(NOTE_HZ[note] * 1.5, chord_dur, amp=0.06)
        chord = _fade(chord, 0.08)
        start = int(t_cursor * SAMPLE_RATE)
        end = min(start + len(chord), len(out))
        out[start:end] += chord[: end - start]
        t_cursor += chord_dur
        i += 1
    return out


def synthesize_ambience(tags: list[str], duration: float) -> np.ndarray:
    bed = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    for tag in tags:
        bed += _sfx_generators.get(tag, lambda d: np.zeros(int(SAMPLE_RATE * d), dtype=np.float32))(duration) * 0.4
    return bed


# --- Individual sound-effect synthesizers (the exact list from the brief) --

def _sfx_footsteps(duration: float) -> np.ndarray:
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    step_interval = 0.45
    t = 0.0
    while t < duration:
        thump = _noise(0.08, amp=0.5, lowpass=0.6) * np.linspace(1, 0, int(SAMPLE_RATE * 0.08))
        start = int(t * SAMPLE_RATE)
        end = min(start + len(thump), len(out))
        out[start:end] += thump[: end - start]
        t += step_interval
    return out


def _sfx_rain(duration: float) -> np.ndarray:
    return _noise(duration, amp=0.25, lowpass=0.15)


def _sfx_thunder(duration: float) -> np.ndarray:
    rumble = _noise(min(duration, 2.5), amp=0.5, lowpass=0.85)
    crack = _tone(60, 0.3, amp=0.6, harmonics=(1, 0.7, 0.4)) * np.linspace(1, 0, int(SAMPLE_RATE * 0.3))
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    out[: len(rumble)] += rumble
    out[: len(crack)] += crack
    return out


def _sfx_wind(duration: float) -> np.ndarray:
    base = _noise(duration, amp=0.2, lowpass=0.5)
    n = len(base)
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * np.linspace(0, duration, n))
    return base * lfo


def _sfx_birds(duration: float) -> np.ndarray:
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    rng = np.random.default_rng()
    t = 0.0
    while t < duration:
        chirp_dur = 0.15
        n = int(SAMPLE_RATE * chirp_dur)
        tt = np.linspace(0, chirp_dur, n)
        freq_sweep = rng.uniform(1800, 2600) + 800 * np.sin(2 * np.pi * 6 * tt)
        chirp = 0.15 * np.sin(2 * np.pi * freq_sweep * tt) * np.sin(np.pi * tt / chirp_dur)
        start = int(t * SAMPLE_RATE)
        end = min(start + n, len(out))
        out[start:end] += chirp[: end - start]
        t += rng.uniform(0.6, 1.8)
    return out


def _sfx_explosions(duration: float) -> np.ndarray:
    boom_dur = min(duration, 1.2)
    n = int(SAMPLE_RATE * boom_dur)
    sub = _tone(45, boom_dur, amp=0.7, harmonics=(1, 0.3)) * np.linspace(1, 0, n) ** 2
    crackle = _noise(boom_dur, amp=0.6, lowpass=0.2) * np.linspace(1, 0, n)
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    out[:n] += sub + crackle
    return out


def _sfx_doors(duration: float) -> np.ndarray:
    creak_dur = min(duration, 0.6)
    n = int(SAMPLE_RATE * creak_dur)
    t = np.linspace(0, creak_dur, n)
    sweep = 300 - 120 * t / creak_dur
    creak = 0.2 * np.sign(np.sin(2 * np.pi * sweep * t)) * np.linspace(1, 0.3, n)
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    out[:n] += creak
    return out


def _sfx_vehicles(duration: float) -> np.ndarray:
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n)
    engine = 0.15 * (np.sign(np.sin(2 * np.pi * 55 * t)) * 0.5 + np.sin(2 * np.pi * 110 * t) * 0.5)
    tremolo = 0.85 + 0.15 * np.sin(2 * np.pi * 8 * t)
    return (engine * tremolo).astype(np.float32)


def _sfx_animals(duration: float) -> np.ndarray:
    bark_dur = min(duration, 0.35)
    n = int(SAMPLE_RATE * bark_dur)
    t = np.linspace(0, bark_dur, n)
    pitch_env = 220 * np.exp(-3 * t)
    bark = 0.3 * np.sign(np.sin(2 * np.pi * pitch_env * t)) * np.sin(np.pi * t / bark_dur)
    out = np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)
    out[:n] += bark
    return out


_sfx_generators = {
    "footsteps": _sfx_footsteps,
    "rain": _sfx_rain,
    "thunder": _sfx_thunder,
    "wind": _sfx_wind,
    "birds": _sfx_birds,
    "explosions": _sfx_explosions,
    "doors": _sfx_doors,
    "vehicles": _sfx_vehicles,
    "animals": _sfx_animals,
}


class AudioEngine:
    """Mixes voice + music + ambience + SFX into one scene-length WAV."""

    def mix_scene_audio(
        self,
        duration: float,
        music_mood: str,
        sfx_tags: list[str],
        ambience_tags: list[str],
        voice_path: Path | None,
        out_path: Path,
    ) -> Path:
        n_samples = int(SAMPLE_RATE * duration)
        mix = np.zeros(n_samples, dtype=np.float32)

        music = synthesize_music(music_mood, duration)
        mix[: len(music)] += music[:n_samples] * 0.55

        ambience = synthesize_ambience(ambience_tags, duration)
        mix[: len(ambience)] += ambience[:n_samples] * 0.5

        for tag in sfx_tags:
            gen = _sfx_generators.get(tag)
            if not gen:
                continue
            sfx = gen(min(duration, 3.0))
            mix[: len(sfx)] += sfx * 0.8

        if voice_path and voice_path.exists():
            voice = _read_wav(voice_path)
            end = min(len(voice), n_samples)
            mix[:end] += voice[:end] * 1.0

        # Normalize to avoid clipping after mixing many layers.
        peak = np.abs(mix).max()
        if peak > 0.98:
            mix = mix / peak * 0.98

        _write_wav(out_path, mix)
        return out_path


def _read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        n = wf.getnframes()
        raw = wf.readframes(n)
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
    return pcm
