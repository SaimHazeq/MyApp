"""
Voice Engine
============
Turns a dialogue line into a narrated audio clip for a specific character's
`voice_profile`, and returns a viseme envelope (mouth-openness over time)
that the Lip Sync Engine maps onto the character's face rig.

Real providers (ElevenLabs / OpenAI TTS) are one config change away - see
`get_voice_provider()`. Until a key is supplied, `PlaceholderVoiceProvider`
synthesizes a lightweight procedural "scratch dialogue" track (a well
established animation-production technique: studios record cheap scratch
VO, sometimes even wordless guide tracks, to time out a scene before the
final cast is recorded) so every project can be previewed end-to-end with
zero setup and zero API cost.
"""
from __future__ import annotations

import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.config import get_settings

settings = get_settings()
SAMPLE_RATE = 22050

VOICE_PITCH_HZ = {
    "warm_confident": 165, "young_bright_optimistic": 230, "brave_energetic": 190,
    "deep_menacing": 95, "cold_calculating": 110, "gravelly_villain": 85,
    "friendly_neutral": 175, "quirky_comic": 250, "gentle_wise_elder": 130,
}


@dataclass
class VisemeFrame:
    time: float       # seconds
    mouth_open: float  # 0..1


@dataclass
class VoiceClip:
    audio_path: Path
    duration_seconds: float
    visemes: list[VisemeFrame]


class VoiceProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice_profile: str, out_path: Path) -> VoiceClip: ...


class PlaceholderVoiceProvider(VoiceProvider):
    def synthesize(self, text: str, voice_profile: str, out_path: Path) -> VoiceClip:
        words = text.split() or ["..."]
        base_hz = VOICE_PITCH_HZ.get(voice_profile, 170)

        samples: list[np.ndarray] = []
        visemes: list[VisemeFrame] = []
        t_cursor = 0.0
        rng = np.random.default_rng(abs(hash(text)) % (2**32))

        for word in words:
            syllables = max(1, (len(word) + 2) // 3)
            for _ in range(syllables):
                dur = rng.uniform(0.12, 0.22)
                n = int(SAMPLE_RATE * dur)
                t = np.linspace(0, dur, n, endpoint=False)

                pitch_jitter = base_hz * rng.uniform(0.92, 1.08)
                # A couple of harmonics stand in for vowel formants.
                tone = (
                    0.6 * np.sin(2 * np.pi * pitch_jitter * t)
                    + 0.25 * np.sin(2 * np.pi * pitch_jitter * 2 * t)
                    + 0.15 * np.sin(2 * np.pi * pitch_jitter * 3 * t)
                )
                envelope = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6  # smooth in/out
                syllable = tone * envelope * 0.5
                samples.append(syllable.astype(np.float32))

                mouth_open = float(np.clip(envelope.mean() * rng.uniform(0.8, 1.1), 0, 1))
                visemes.append(VisemeFrame(time=round(t_cursor, 3), mouth_open=round(mouth_open, 2)))
                t_cursor += dur

            gap = rng.uniform(0.05, 0.1)
            samples.append(np.zeros(int(SAMPLE_RATE * gap), dtype=np.float32))
            visemes.append(VisemeFrame(time=round(t_cursor, 3), mouth_open=0.0))
            t_cursor += gap

        audio = np.concatenate(samples) if samples else np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
        _write_wav(out_path, audio)

        return VoiceClip(audio_path=out_path, duration_seconds=t_cursor, visemes=visemes)


class ElevenLabsVoiceProvider(VoiceProvider):  # pragma: no cover - requires network + API key
    """Real neural TTS. Activate with VOICE_PROVIDER=elevenlabs + ELEVENLABS_API_KEY."""

    VOICE_ID_BY_PROFILE = {
        # Map your own cloned/library voice IDs here per profile.
        "warm_confident": "21m00Tcm4TlvDq8ikWAM",
    }

    def synthesize(self, text: str, voice_profile: str, out_path: Path) -> VoiceClip:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        voice_id = self.VOICE_ID_BY_PROFILE.get(voice_profile, "21m00Tcm4TlvDq8ikWAM")
        audio_bytes = b"".join(client.text_to_speech.convert(voice_id=voice_id, text=text))
        out_path.write_bytes(audio_bytes)

        duration = _probe_duration(out_path)
        # A production system would request viseme/timestamp data from the
        # provider (many TTS APIs expose phoneme timing) instead of this
        # even envelope; kept simple here as the integration seam.
        visemes = [VisemeFrame(time=round(t, 2), mouth_open=0.6) for t in np.arange(0, duration, 0.08)]
        return VoiceClip(audio_path=out_path, duration_seconds=duration, visemes=visemes)


def get_voice_provider() -> VoiceProvider:
    if settings.VOICE_PROVIDER == "elevenlabs" and settings.ELEVENLABS_API_KEY:
        return ElevenLabsVoiceProvider()
    return PlaceholderVoiceProvider()


def _write_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm16 = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())


def _probe_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def concatenate_voice_clips(entries: list[dict], out_path: Path, gap: float = 0.35) -> list[VisemeFrame]:
    """Combines multiple already-synthesized line clips into one continuous
    track (with `gap` seconds of silence between lines) and returns a single
    viseme timeline spanning the whole thing.

    `entries` is a list of dicts with at least `path` (a wav written by
    `synthesize_line`), `duration`, `visemes`, and `start_offset` (the
    cumulative time, in seconds, at which that line begins - the caller is
    responsible for computing these consistently, e.g. by accumulating
    `duration + gap` across entries in order).

    This is what lets a scene with several lines of back-and-forth dialogue
    end up with ALL of it audible and lip-synced, instead of only the first
    line (see MoviePipeline._generate_voice)."""
    segments: list[np.ndarray] = []
    combined_visemes: list[VisemeFrame] = []
    silence_samples = int(SAMPLE_RATE * gap)

    for entry in entries:
        with wave.open(str(entry["path"]), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
        segments.append(pcm)
        segments.append(np.zeros(silence_samples, dtype=np.float32))

        for v in entry["visemes"]:
            combined_visemes.append(
                VisemeFrame(time=round(entry["start_offset"] + v.time, 3), mouth_open=v.mouth_open)
            )
        combined_visemes.append(
            VisemeFrame(time=round(entry["start_offset"] + entry["duration"], 3), mouth_open=0.0)
        )

    combined_audio = np.concatenate(segments) if segments else np.zeros(1, dtype=np.float32)
    _write_wav(out_path, combined_audio)
    return combined_visemes


class VoiceEngine:
    def __init__(self) -> None:
        self.provider = get_voice_provider()

    def synthesize_line(self, text: str, voice_profile: str, out_path: Path) -> VoiceClip:
        return self.provider.synthesize(text, voice_profile, out_path)
