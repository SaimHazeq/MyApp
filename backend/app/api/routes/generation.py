from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.generation import GenerationStartResponse, GenerationStatus, PIPELINE_STAGES
from app.workers.generation_worker import enqueue_generation, cancel_generation

router = APIRouter(prefix="/generation", tags=["Generation"])

_STAGE_LABELS = dict(PIPELINE_STAGES)


def _get_owned_project(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/{project_id}/start", response_model=GenerationStartResponse)
def start_generation(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Kick off the full AI movie pipeline for a project:
    story analysis -> characters -> environments -> animation ->
    voice + lip sync -> music/SFX -> final render.

    Runs asynchronously; poll GET /generation/{project_id}/status
    (or open a websocket at /ws/generation/{project_id}) to track progress.
    """
    project = _get_owned_project(db, project_id, current_user)

    if project.status in ("queued", "analyzing_story", "generating_characters",
                           "generating_environments", "animating", "generating_voice",
                           "generating_audio", "rendering"):
        raise HTTPException(status_code=400, detail="Generation already in progress")

    if not project.story.strip():
        raise HTTPException(status_code=400, detail="Project has no story text to generate from")

    project.status = "queued"
    project.progress_percent = 0
    project.current_stage = "queued"
    project.error_message = ""
    db.commit()

    enqueue_generation(project_id)

    return GenerationStartResponse(project_id=project_id, status="queued")


@router.get("/{project_id}/status", response_model=GenerationStatus)
def get_status(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lightweight polling endpoint for the Generation Progress screen.
    The frontend polls this every ~1.5s while status is not terminal."""
    project = _get_owned_project(db, project_id, current_user)
    return GenerationStatus(
        project_id=project.id,
        status=project.status,
        current_stage=project.current_stage,
        current_stage_label=_STAGE_LABELS.get(project.current_stage, project.current_stage),
        progress_percent=project.progress_percent,
        error_message=project.error_message,
        video_path=project.video_path or None,
        subtitle_path=project.subtitle_path or None,
    )


@router.post("/{project_id}/cancel", response_model=GenerationStatus)
def cancel(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user)
    cancel_generation(project_id)
    project.status = "failed"
    project.error_message = "Cancelled by user"
    db.commit()
    db.refresh(project)
    return GenerationStatus(
        project_id=project.id,
        status=project.status,
        current_stage=project.current_stage,
        current_stage_label=_STAGE_LABELS.get(project.current_stage, project.current_stage),
        progress_percent=project.progress_percent,
        error_message=project.error_message,
    )
