import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api.routes import auth as auth_routes
from .api.routes import papers as papers_routes
from .api.routes import keywords as keywords_routes
from .api.routes import settings as settings_routes
from .api.routes import feedback as feedback_routes
from .api.routes import digest as digest_routes
from .api.routes import fulltext as fulltext_routes

app = FastAPI(title="Paper Digest", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(papers_routes.router)
app.include_router(keywords_routes.router)
app.include_router(settings_routes.router)
app.include_router(feedback_routes.router)
app.include_router(digest_routes.router)
app.include_router(fulltext_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve frontend in single-container mode (SKIP_FRONTEND_SERVE != "1")
if os.environ.get("SKIP_FRONTEND_SERVE") != "1":
    FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

    if FRONTEND_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(request, full_path: str):
            file_path = FRONTEND_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIR / "index.html")
