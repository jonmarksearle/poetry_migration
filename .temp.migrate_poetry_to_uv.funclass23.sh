#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="$HOME/Work/AjanCodesExamples/2023/funclass"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

cp pyproject.toml pyproject.poetry.bak
rm -f poetry.lock
rm -rf .venv

UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

if [ ! -f .python-version ]; then
  printf "3.11\n" > .python-version
fi

echo "[funclass23] migration started: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[funclass23] uv sync --group dev failed" >> "$LOG"
fi

if ! UV_CACHE_DIR="$CACHE_DIR" uv run ruff check .; then
  echo "[funclass23] ruff check failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run mypy .; then
  echo "[funclass23] mypy failed" >> "$LOG"
fi
if ! UV_CACHE_DIR="$CACHE_DIR" uv run pytest; then
  echo "[funclass23] pytest failed" >> "$LOG"
fi
echo "[funclass23] migration complete: $(date -Is)" >> "$LOG"
