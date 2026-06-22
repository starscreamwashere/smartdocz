"""SmartDocZ FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import analytics, chat, files, sessions, users
from app.schemas import HealthOut

settings = get_settings()

app = FastAPI(
    title="SmartDocZ API",
    version="0.1.0",
    description="AI document assistant backend (Milestone 1: setup + auth).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthOut, tags=["health"])
def health() -> HealthOut:
    return HealthOut(status="ok")


app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(analytics.router)
