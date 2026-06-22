"""Clerk authentication — validates the session JWT and resolves the app user.

Flow (per the Backend Schema / Auth Requirements docs):

    User Login → Clerk Session Token → FastAPI Validation → Authorized Request

The frontend attaches the Clerk session JWT as `Authorization: Bearer <token>`.
We verify the RS256 signature against Clerk's JWKS, check the issuer and
expiry, then upsert the user into Postgres keyed by the `sub` (Clerk user id).
"""
from __future__ import annotations

from typing import Annotated

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import User

# PyJWKClient caches signing keys internally, so a module-level client is fine.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER is not configured on the backend.",
        )
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.jwks_url)
    return _jwks_client


def _decode_token(token: str, settings: Settings) -> dict:
    try:
        signing_key = _get_jwks_client(settings).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer or None,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Clerk includes `azp` (authorized party). Enforce it when configured.
    allowed = settings.authorized_parties
    azp = claims.get("azp")
    if allowed and azp is not None and azp not in allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token authorized party is not allowed.",
        )
    return claims


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


def _fetch_clerk_profile(clerk_user_id: str, settings: Settings) -> tuple[str | None, str | None]:
    """Best-effort fetch of email + full name from the Clerk Backend API.

    Returns (email, full_name). Never raises — auth must not depend on it.
    """
    if not settings.clerk_secret_key:
        return None, None
    try:
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None, None

    email = None
    primary_id = data.get("primary_email_address_id")
    for addr in data.get("email_addresses", []):
        if addr.get("id") == primary_id:
            email = addr.get("email_address")
            break
    if email is None and data.get("email_addresses"):
        email = data["email_addresses"][0].get("email_address")

    name = " ".join(p for p in [data.get("first_name"), data.get("last_name")] if p)
    return email, (name or None)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """FastAPI dependency: verify the Clerk token and return the app `User`.

    Upserts the user on first request so downstream tables can reference them.
    """
    token = _bearer_token(authorization)
    claims = _decode_token(token, settings)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject (sub) claim.",
        )

    user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user is None:
        email, full_name = _fetch_clerk_profile(clerk_user_id, settings)
        user = User(clerk_user_id=clerk_user_id, email=email, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
