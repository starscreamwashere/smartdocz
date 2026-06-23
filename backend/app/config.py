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

    # LLM / vector
    google_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: str = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection: str = "smartdocz_chunks"
    qdrant_api_key: str = ""
    qdrant_url: str = ""
    redis_url: str = ""
    langsmith_api_key: str = ""

    # RAG pipeline tuning
    chunk_size: int = 1000
    chunk_overlap: int = 150
    retrieval_top_k: int = 4
    max_upload_mb: float = 50.0  # TRD constraint
    upload_dir: str = "./uploads"

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
