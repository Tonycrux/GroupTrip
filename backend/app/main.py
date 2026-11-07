from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import (
    activities,
    approvals,
    bootstrap,
    conditions,
    conflicts,
    destinations,
    members,
    plan,
    profile,
    ratings,
    recommendations,
    requests,
    revisions,
    study,
    trips,
    vetoes,
)
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    yield


app = FastAPI(title="GroupTrip API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "llm_provider": settings.llm_provider}


for module in (
    trips,
    members,
    profile,
    conditions,
    destinations,
    activities,
    ratings,
    recommendations,
    plan,
    revisions,
    vetoes,
    approvals,
    conflicts,
    requests,
    study,
    bootstrap,
):
    app.include_router(module.router)
