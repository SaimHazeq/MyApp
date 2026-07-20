"""
AI Cartoon Movie Maker - FastAPI backend entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.utils.logger import logger

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Turn a prompt, story, characters and dialogue into a fully "
                 "produced 3D-style animated movie: AI story analysis, "
                 "consistent character generation, environments, camera "
                 "animation, lip-synced AI voices, generative music/SFX, "
                 "and final MP4 rendering with subtitles.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("{} backend started (env={})", settings.APP_NAME, settings.ENVIRONMENT)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on {} {}", request.method, request.url)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", tags=["Health"])
def root():
    return {"app": settings.APP_NAME, "status": "ok"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)
