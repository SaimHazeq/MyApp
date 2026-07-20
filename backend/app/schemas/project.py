from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


ANIMATION_STYLES = [
    "3d_pixar",       # rounded, warm, Pixar/Dreamworks-like
    "3d_stylized",    # bold stylized 3D, Arcane-ish
    "3d_realistic",   # semi-realistic 3D
    "anime_3d",       # cel-shaded anime-3D hybrid
    "claymation",     # stop-motion clay look
]


class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    role: str = Field(default="supporting")  # protagonist | antagonist | supporting
    voice_profile: Optional[str] = None       # e.g. "young_female_warm" - auto-picked if omitted


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str
    role: str
    voice_profile: str
    reference_image_path: str = ""


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    prompt: str = Field(default="", max_length=4000)
    story: str = Field(min_length=1, max_length=20000)
    dialogue: str = Field(default="", max_length=20000)
    characters: List[CharacterIn] = Field(default_factory=list)
    duration_minutes: float = Field(default=2.0, ge=0.5, le=30)
    animation_style: str = Field(default="3d_pixar")
    resolution: str = Field(default="1920x1080")
    voice_language: str = Field(default="en-US")


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    prompt: Optional[str] = None
    story: Optional[str] = None
    dialogue: Optional[str] = None
    duration_minutes: Optional[float] = None
    animation_style: Optional[str] = None
    resolution: Optional[str] = None


class SceneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    index: int
    text: str
    location: str
    emotion: str
    camera_movement: str
    duration_seconds: float
    sfx_tags: list
    music_mood: str
    status: str
    image_path: str = ""
    clip_path: str = ""


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    prompt: str
    story: str
    dialogue: str
    animation_style: str
    duration_minutes: float
    resolution: str
    status: str
    current_stage: str
    progress_percent: int
    error_message: str
    thumbnail_path: str
    video_path: str
    subtitle_path: str
    created_at: datetime
    updated_at: datetime
    characters: List[CharacterOut] = []


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    status: str
    progress_percent: int
    animation_style: str
    duration_minutes: float
    thumbnail_path: str
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    scenes: List[SceneOut] = []
