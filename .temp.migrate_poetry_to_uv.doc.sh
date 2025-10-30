#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="/home/jon/Work/AjanCodesExamples/2023/doc"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

if [ ! -f .python-version ]; then
  printf "3.11\n" > .python-version
fi

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[doc] uv sync --group dev failed" >> "$LOG"
fi

if ! UV_CACHE_DIR="$CACHE_DIR" uv run ruff check src/**/*.py; then
  echo "[doc] ruff check failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run mypy src; then
  echo "[doc] mypy failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run pytest; then
  echo "[doc] pytest failed" >> "$LOG"
fi
