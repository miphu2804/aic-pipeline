from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    PIPELINE_METADATA_DB_URL: str = "sqlite:///./data/pipeline_metadata.db"
    PIPELINE_ARTIFACT_DIR: Path = Path("artifacts")
    PIPELINE_MEDIA_ROOT: Path | None = None
    PIPELINE_TEXT_INDEX_URL: str = "http://localhost:7700"
    PIPELINE_VECTOR_INDEX_DIR: Path = Path("artifacts/vector-index")
    PIPELINE_LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


app_config = AppConfig()
