import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.project import Character, Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectOut,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


def _get_owned_project(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new movie project in `draft` status. Call
    POST /generation/{project_id}/start afterwards to kick off the AI pipeline."""
    project = Project(
        owner_id=current_user.id,
        title=payload.title,
        prompt=payload.prompt,
        story=payload.story,
        dialogue=payload.dialogue,
        duration_minutes=payload.duration_minutes,
        animation_style=payload.animation_style,
        resolution=payload.resolution,
        voice_language=payload.voice_language,
        status="draft",
    )
    db.add(project)
    db.flush()  # obtain project.id before creating children

    for c in payload.characters:
        db.add(
            Character(
                project_id=project.id,
                name=c.name,
                description=c.description,
                role=c.role,
                voice_profile=c.voice_profile or _auto_voice_profile(c.role),
                consistency_seed=random.randint(1, 999_999),
            )
        )

    db.commit()
    db.refresh(project)
    return project


def _auto_voice_profile(role: str) -> str:
    return {
        "protagonist": "warm_confident",
        "antagonist": "deep_menacing",
        "supporting": "friendly_neutral",
    }.get(role, "friendly_neutral")


@router.get("", response_model=list[ProjectListItem])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .order_by(Project.updated_at.desc())
        .all()
    )


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_project(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user)
    if project.status not in ("draft", "failed", "completed"):
        raise HTTPException(status_code=400, detail="Cannot edit a project while it is generating")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_owned_project(db, project_id, current_user)
    db.delete(project)
    db.commit()
