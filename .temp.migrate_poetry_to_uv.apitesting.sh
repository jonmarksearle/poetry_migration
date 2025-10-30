#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="/home/jon/Work/AjanCodesExamples/2023/apitesting"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

if [ ! -f .python-version ]; then
  printf "3.11\n" > .python-version
fi

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh
UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[apitesting] uv sync --group dev failed" >> "$LOG"

if ! UV_CACHE_DIR="$CACHE_DIR" uv run ruff check; then
  echo "[apitesting] ruff check failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run mypy .; then
  echo "[apitesting] mypy failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run pytest; then
  echo "[apitesting] pytest failed" >> "$LOG"
fi
