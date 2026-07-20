# AI Cartoon Movie Maker

Turn a title, prompt, story, dialogue and character descriptions into a fully
produced 3D-style animated movie — story analysis, consistent characters,
environments, cinematic camera moves, lip-synced AI voices, generative
music/ambience/SFX, and a rendered MP4 with subtitles — all through a web
app with a FastAPI backend.

A sample generated movie (produced entirely by this codebase, no external
services, no GPU) is included at `docs/sample_output/demo_movie.mp4`.

---

## 1. What's real vs. placeholder in this build

This repo is a complete, working, end-to-end system: every screen, every
API route, the database, auth, job orchestration and the full 8-stage AI
pipeline actually run. Two categories of engine sit behind clean interfaces:

| Layer | Default (zero setup, zero cost) | Swap in for production quality |
|---|---|---|
| Story analysis | Deterministic keyword/heuristic scene splitter | `OPENAI_API_KEY` → LLM-based `LLMStoryEngine` (already wired in `story_engine.py`) |
| Character/environment art | Procedural PIL shapes, seeded for consistency | `STABILITY_API_KEY` / `IMAGE_GEN_PROVIDER=stability` (or wire Midjourney/Runway/Meshy for real 3D) |
| Voice | Procedural "scratch dialogue" tones (a real animation-industry placeholder technique) with word/syllable-timed visemes | `ELEVENLABS_API_KEY` / `VOICE_PROVIDER=elevenlabs` (or Azure/OpenAI TTS) |
| Music & SFX | Procedural numpy synthesis (chord pads, footsteps, rain, thunder, wind, birds, explosions, doors, vehicles, animals) | Swap `audio_engine.py` generators for a licensed SFX library or a generative-audio API |
| Animation / rendering | PIL compositing + Ken Burns camera moves + ffmpeg encoding | Swap `animation_engine.py` for a Blender/Unreal/text-to-video pipeline |

Every provider is behind an abstract interface (`ImageGenProvider`,
`VoiceProvider`, etc.) with a single settings flag to flip in `.env` — see
`backend/app/core/config.py`. Nothing else in the codebase needs to change.
This means the app is genuinely usable today (you can generate and download
a real movie right now with zero API keys), and upgrades to
photoreal/professional output as you add provider keys.

---

## 2. Tech stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (SQLite by default, swap
the URL for Postgres/MySQL), JWT auth (python-jose + passlib/bcrypt),
numpy/Pillow/ffmpeg for the offline generation engines.

**Frontend:** React 18 + Vite, React Router, Zustand (lightweight global
state), Tailwind CSS, lucide-react icons, axios.

**Infra:** Docker + docker-compose for one-command local deployment.

---

## 3. Project structure

```
aicartoon-movie-maker/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── core/                   # config, database, security (JWT/hashing)
│   │   ├── models/                 # SQLAlchemy models: User, Project, Character, Scene
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── api/routes/             # auth, projects, generation, render, storage, settings
│   │   ├── services/
│   │   │   ├── ai/                 # story, character, environment, voice, lipsync, audio engines
│   │   │   ├── animation/          # camera moves + compositing + lip sync frames
│   │   │   ├── rendering/          # mux/concat/subtitles/thumbnail/export
│   │   │   └── pipeline.py         # orchestrates every stage end-to-end
│   │   ├── workers/                # background job runner (thread pool, Celery-ready)
│   │   └── utils/                  # file handling, logging
│   └── storage/                    # generated projects/renders/temp (gitignored)
├── frontend/
│   └── src/
│       ├── screens/                # Splash, Login, Home, CreateMovie, GenerationProgress,
│       │                           # MyMovies, Preview, Export, Settings
│       ├── widgets/                # reusable components (Button, Card, MovieCard, AppShell, ...)
│       ├── services/               # API clients (auth, project, generation, settings)
│       ├── state/                  # Auth context + Zustand stores
│       ├── theme/                  # design tokens + dark/light ThemeProvider
│       ├── models/                 # JSDoc type definitions
│       └── utils/                  # constants, validators, hooks
└── docs/
    └── sample_output/              # a real generated demo movie + assets
```

---

## 4. Running locally

### Option A — Docker (recommended)

```bash
cp backend/.env.example backend/.env      # edit SECRET_KEY at minimum
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend docs (Swagger): http://localhost:8000/docs

### Option B — Manual

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # edit SECRET_KEY at minimum
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Visit http://localhost:5173.

> Requires `ffmpeg` on the backend host (`apt install ffmpeg` / `brew install ffmpeg`).
> The Docker image installs it automatically.

---

## 5. Enabling real AI providers

Edit `backend/.env`:

```bash
OPENAI_API_KEY=sk-...
IMAGE_GEN_PROVIDER=stability
STABILITY_API_KEY=sk-...
VOICE_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=...
```

Restart the backend. No code changes needed — `get_story_engine()`,
`get_image_gen_provider()` and `get_voice_provider()` pick the real
implementation automatically whenever the corresponding key is present.

---

## 6. Security notes

- Passwords are bcrypt-hashed (`passlib`); JWT access (24h) + refresh (14d)
  tokens; all project/render/storage routes require a valid bearer token
  and verify resource ownership.
- Uploaded character reference images are validated by content-type and
  size-limited; file paths are sanitized against traversal (`safe_join`).
- Set a real `SECRET_KEY` (`openssl rand -hex 32`) before deploying.
- CORS origins are explicit (`CORS_ORIGINS` in `.env`) — no wildcard in production.

## 7. Testing & scaling notes

- The generation worker runs in-process via a `ThreadPoolExecutor` so the
  whole app works with zero extra infrastructure. For multi-machine scale,
  flip `USE_CELERY=true` and see the commented Celery task in
  `app/workers/generation_worker.py`.
- Swap `DATABASE_URL` to Postgres for production; SQLAlchemy models need no
  changes.
- See `docs/ARCHITECTURE.md` for the full pipeline walkthrough, data model,
  and a stage-by-stage description of what each AI engine does.
