"""Application configuration, loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/smartdocz"

    # Clerk
    clerk_secret_key: str = ""
    clerk_issuer: str = ""
    clerk_authorized_parties: str = "http://localhost:3000"

    # CORS
    frontend_origins: str = "http://localhost:3000"

    # LLM / vector (placeholders for later milestones)
    google_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "gemini"
    chroma_persist_dir: str = "./chroma_data"
    qdrant_api_key: str = ""
    qdrant_url: str = ""
    embedding_model: str = ""
    redis_url: str = ""
    langsmith_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def authorized_parties(self) -> list[str]:
        return [p.strip() for p in self.clerk_authorized_parties.split(",") if p.strip()]

    @property
    def jwks_url(self) -> str:
        issuer = self.clerk_issuer.rstrip("/")
        return f"{issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
