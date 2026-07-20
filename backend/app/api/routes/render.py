from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.services.rendering.render_engine import RenderEngine

router = APIRouter(prefix="/render", tags=["Rendering & Export"])

EXPORT_PRESETS = {
    "mp4_1080p": {"container": "mp4", "resolution": "1920x1080", "label": "MP4 - 1080p (recommended)"},
    "mp4_720p": {"container": "mp4", "resolution": "1280x720", "label": "MP4 - 720p (smaller file)"},
    "mp4_4k": {"container": "mp4", "resolution": "3840x2160", "label": "MP4 - 4K (studio quality)"},
}


class ExportRequest(BaseModel):
    preset: str = "mp4_1080p"
    burn_in_subtitles: bool = False


class ExportResponse(BaseModel):
    project_id: str
    video_path: str
    subtitle_path: str
    preset: str


@router.get("/presets")
def list_presets():
    return EXPORT_PRESETS


@router.post("/{project_id}/export", response_model=ExportResponse)
def export_movie(
    project_id: str,
    payload: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-package the already-rendered movie into a chosen export preset
    (resolution/container), optionally burning subtitles into the video
    instead of shipping them as a sidecar .srt file."""
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if project.status != "completed" or not project.video_path:
        raise HTTPException(status_code=400, detail="Movie has not finished rendering yet")
    if payload.preset not in EXPORT_PRESETS:
        raise HTTPException(status_code=400, detail="Unknown export preset")

    engine = RenderEngine()
    out_video, out_srt = engine.export(
        project=project,
        preset=EXPORT_PRESETS[payload.preset],
        burn_in_subtitles=payload.burn_in_subtitles,
    )

    return ExportResponse(
        project_id=project.id,
        video_path=out_video,
        subtitle_path=out_srt,
        preset=payload.preset,
    )
