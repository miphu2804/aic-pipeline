from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app_config import app_config

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pipeline API",
    description="Local-first backend for the retrieval pipeline.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    logger.debug("Health endpoint accessed")
    return {
        "status": "ok",
        "service": "pipeline",
    }


def serve() -> None:
    log_level = app_config.PIPELINE_LOG_LEVEL.upper()
    logging.basicConfig(level=log_level)
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, log_level=log_level)


if __name__ == "__main__":
    serve()
