#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="$HOME/Work/AjanCodesExamples/2024/func"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="$HOME/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

unset VIRTUAL_ENV

if [ ! -f pyproject.poetry.bak ]; then
  cp pyproject.toml pyproject.poetry.bak
fi
rm -f poetry.lock
rm -rf .venv

UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

printf "3.12\n" > .python-version

echo "[func] migration started: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[func] uv sync --group dev failed" >> "$LOG"
fi

PYTHON_BIN=".venv/bin/python"

if ! "$PYTHON_BIN" -m ruff check .; then
  echo "[func] ruff check failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m mypy .; then
  echo "[func] mypy failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m pytest; then
  echo "[func] pytest failed" >> "$LOG"
fi

echo "[func] migration complete: $(date -Is)" >> "$LOG"
