from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.project import Character, Project
from app.models.user import User
from app.utils.file_utils import safe_join, save_upload

router = APIRouter(prefix="/storage", tags=["Storage"])
settings = get_settings()


def _owned_project_or_404(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("/{project_id}/video")
def download_video(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project_or_404(db, project_id, current_user)
    if not project.video_path or not Path(project.video_path).exists():
        raise HTTPException(status_code=404, detail="Video not ready yet")
    return FileResponse(
        project.video_path,
        media_type="video/mp4",
        filename=f"{project.title.replace(' ', '_')}.mp4",
    )


@router.get("/{project_id}/subtitles")
def download_subtitles(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project_or_404(db, project_id, current_user)
    if not project.subtitle_path or not Path(project.subtitle_path).exists():
        raise HTTPException(status_code=404, detail="Subtitles not ready yet")
    return FileResponse(
        project.subtitle_path,
        media_type="text/plain",
        filename=f"{project.title.replace(' ', '_')}.srt",
    )


@router.get("/{project_id}/thumbnail")
def download_thumbnail(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _owned_project_or_404(db, project_id, current_user)
    if not project.thumbnail_path or not Path(project.thumbnail_path).exists():
        raise HTTPException(status_code=404, detail="Thumbnail not ready yet")
    return FileResponse(project.thumbnail_path, media_type="image/png")


@router.post("/{project_id}/characters/{character_id}/reference-image")
async def upload_character_reference(
    project_id: str,
    character_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Optional: let a user upload a reference sketch/photo for a character
    so the character-generation engine can bias its design toward it."""
    project = _owned_project_or_404(db, project_id, current_user)
    character = db.get(Character, character_id)
    if not character or character.project_id != project.id:
        raise HTTPException(status_code=404, detail="Character not found")

    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(status_code=400, detail="Only PNG, JPEG or WEBP images are accepted")

    dest_dir = safe_join(settings.PROJECTS_DIR, project.id, "characters")
    path = await save_upload(file, dest_dir, max_mb=settings.MAX_UPLOAD_MB)

    character.reference_image_path = str(path)
    db.commit()

    return {"character_id": character.id, "reference_image_path": str(path)}
