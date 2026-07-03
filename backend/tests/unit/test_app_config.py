from pathlib import Path

from src.app_config import AppConfig


def test_app_config_uses_local_defaults() -> None:
    config = AppConfig()

    assert config.PIPELINE_METADATA_DB_URL == "sqlite:///./data/pipeline_metadata.db"
    assert config.PIPELINE_ARTIFACT_DIR == Path("artifacts")
    assert config.PIPELINE_MEDIA_ROOT is None
    assert config.PIPELINE_TEXT_INDEX_URL == "http://localhost:7700"
    assert config.PIPELINE_VECTOR_INDEX_DIR == Path("artifacts/vector-index")
    assert config.PIPELINE_LOG_LEVEL == "INFO"
    assert not hasattr(config, "PIPELINE_ENV")
    assert not hasattr(config, "PIPELINE_DB_URL")
    assert not hasattr(config, "AIC_PIPELINE_ENV")


def test_env_example_documents_pipeline_settings() -> None:
    env_example = Path(__file__).resolve().parents[2] / ".env.example"

    content = env_example.read_text()

    assert "PIPELINE_METADATA_DB_URL=sqlite:///./data/pipeline_metadata.db" in content
    assert "PIPELINE_ARTIFACT_DIR=artifacts" in content
    assert "PIPELINE_MEDIA_ROOT=" in content
    assert "PIPELINE_TEXT_INDEX_URL=http://localhost:7700" in content
    assert "PIPELINE_VECTOR_INDEX_DIR=artifacts/vector-index" in content
    assert "PIPELINE_LOG_LEVEL=INFO" in content
    assert "PIPELINE_ENV" not in content
    assert "PIPELINE_DB_URL" not in content
    assert "AIC_PIPELINE" not in content
