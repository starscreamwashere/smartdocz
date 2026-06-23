"""SmartDocZ FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import analytics, chat, files, sessions, users
from app.schemas import HealthOut

logger = logging.getLogger("smartdocz")

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON 500 for any unhandled error.

    This handler runs inside the CORS middleware, so the response keeps its
    Access-Control-Allow-Origin header — otherwise the browser misreports a
    server error as a CORS failure.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health", response_model=HealthOut, tags=["health"])
def health() -> HealthOut:
    return HealthOut(status="ok")


app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(analytics.router)
