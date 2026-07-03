# AIC Pipeline Backend

Python backend initialized with `uv` and Python 3.11.3.

## Setup

```sh
cd backend
uv sync
```

## Run

```sh
uv run aic-pipeline
```

## Check

```sh
uv run black --check src tests
uv run isort --check-only src tests
uv run pytest
```

## Pre-commit

```sh
cd backend
uv run pre-commit install --config ../.pre-commit-config.yaml
```
