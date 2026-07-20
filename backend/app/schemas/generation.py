from typing import Optional

from pydantic import BaseModel


# Canonical pipeline stages, in execution order. The frontend's
# GenerationProgressScreen renders one film-strip "sprocket hole" per stage.
PIPELINE_STAGES = [
    ("queued", "Queued"),
    ("analyzing_story", "Analyzing story & splitting scenes"),
    ("generating_characters", "Generating 3D characters"),
    ("generating_environments", "Building environments"),
    ("generating_voice", "Generating AI voices & lip sync data"),
    ("animating", "Animating actions, camera moves & lip sync"),
    ("generating_audio", "Composing music & sound effects"),
    ("rendering", "Rendering final video"),
    ("completed", "Completed"),
]


class GenerationStartResponse(BaseModel):
    project_id: str
    status: str
    message: str = "Generation started"


class GenerationStatus(BaseModel):
    project_id: str
    status: str
    current_stage: str
    current_stage_label: str
    progress_percent: int
    error_message: str = ""
    video_path: Optional[str] = None
    subtitle_path: Optional[str] = None


class StageUpdate(BaseModel):
    stage_key: str
    label: str
    percent: int
    detail: Optional[str] = None
