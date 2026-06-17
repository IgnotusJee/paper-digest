from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import auth as auth_routes
from .api.routes import papers as papers_routes
from .api.routes import keywords as keywords_routes

app = FastAPI(title="Paper Digest", docs_url="/api/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # no cross-origin; Nginx serves frontend on same origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(papers_routes.router)
app.include_router(keywords_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
