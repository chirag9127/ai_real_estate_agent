from __future__ import annotations

import os
from collections.abc import AsyncGenerator  # noqa: TC003
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import (
    health,
    pipeline,
    rankings,
    requirements,
    review,
    search,
    send,
    transcripts,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Import models so Base.metadata knows about them
    import app.models  # noqa: F401

    create_tables()
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
app.include_router(transcripts.router, prefix=settings.api_prefix, tags=["transcripts"])
app.include_router(
    requirements.router, prefix=settings.api_prefix, tags=["requirements"]
)
app.include_router(pipeline.router, prefix=settings.api_prefix, tags=["pipeline"])
app.include_router(search.router, prefix=settings.api_prefix, tags=["search"])
app.include_router(rankings.router, prefix=settings.api_prefix, tags=["rankings"])
app.include_router(review.router, prefix=settings.api_prefix, tags=["review"])
app.include_router(send.router, prefix=settings.api_prefix, tags=["send"])
