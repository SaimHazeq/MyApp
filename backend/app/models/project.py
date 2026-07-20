import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    """A single movie project. Owns many Characters and Scenes."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    story: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    animation_style: Mapped[str] = mapped_column(String(64), default="3d_pixar")
    duration_minutes: Mapped[float] = mapped_column(Float, default=2.0)
    resolution: Mapped[str] = mapped_column(String(16), default="1920x1080")
    voice_language: Mapped[str] = mapped_column(String(16), default="en-US")

    # Lifecycle: draft -> queued -> analyzing_story -> generating_characters ->
    # generating_environments -> animating -> generating_voice -> generating_audio ->
    # rendering -> completed | failed
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    current_stage: Mapped[str] = mapped_column(String(64), default="")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, default="")

    thumbnail_path: Mapped[str] = mapped_column(String(512), default="")
    video_path: Mapped[str] = mapped_column(String(512), default="")
    subtitle_path: Mapped[str] = mapped_column(String(512), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner = relationship("User", back_populates="projects")
    characters = relationship(
        "Character", back_populates="project", cascade="all, delete-orphan", order_by="Character.created_at"
    )
    scenes = relationship(
        "Scene", back_populates="project", cascade="all, delete-orphan", order_by="Scene.index"
    )


class Character(Base):
    """A character profile. The seed/color/voice_id are re-used on every
    scene the character appears in so the model stays visually and vocally
    consistent throughout the movie."""

    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    role: Mapped[str] = mapped_column(String(64), default="supporting")  # protagonist | antagonist | supporting
    voice_profile: Mapped[str] = mapped_column(String(64), default="")   # e.g. "young_male_energetic"
    consistency_seed: Mapped[int] = mapped_column(Integer, default=0)
    reference_image_path: Mapped[str] = mapped_column(String(512), default="")
    traits: Mapped[dict] = mapped_column(JSON, default=dict)  # {"palette": [...], "build": "...", ...}

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="characters")


class Scene(Base):
    """One shot/beat of the story. The pipeline generates one background
    image, one audio mix and one short video clip per scene, then the
    render engine concatenates all scenes into the final movie."""

    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)

    index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(255), default="")
    time_of_day: Mapped[str] = mapped_column(String(32), default="day")
    emotion: Mapped[str] = mapped_column(String(32), default="neutral")
    camera_movement: Mapped[str] = mapped_column(String(32), default="static")  # pan | zoom_in | zoom_out | dolly | static
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0)

    character_ids: Mapped[list] = mapped_column(JSON, default=list)
    dialogue_lines: Mapped[list] = mapped_column(JSON, default=list)  # [{character_id, text, start, end}]
    sfx_tags: Mapped[list] = mapped_column(JSON, default=list)         # ["rain", "footsteps", ...]
    music_mood: Mapped[str] = mapped_column(String(32), default="neutral")

    status: Mapped[str] = mapped_column(String(32), default="pending")
    image_path: Mapped[str] = mapped_column(String(512), default="")
    voice_audio_path: Mapped[str] = mapped_column(String(512), default="")
    mixed_audio_path: Mapped[str] = mapped_column(String(512), default="")
    clip_path: Mapped[str] = mapped_column(String(512), default="")

    project = relationship("Project", back_populates="scenes")
