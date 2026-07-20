from fastapi import APIRouter

from app.api.routes import auth, projects, generation, render, storage, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(generation.router)
api_router.include_router(render.router)
api_router.include_router(storage.router)
api_router.include_router(settings.router)
