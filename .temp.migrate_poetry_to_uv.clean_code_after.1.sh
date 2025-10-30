#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="$HOME/Work/AjanCodesExamples/2024/clean_code/after"
CACHE_DIR="$HOME/Work/.cache/uv"

cd "$REPO"

unset VIRTUAL_ENV

rm -rf .venv
rm -f uv.lock

echo "[clean_code_after] second pass: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh
UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[clean_code_after] uv sync --group dev failed" >> "$LOG"

PYTHON_BIN=".venv/bin/python"

if ! "$PYTHON_BIN" -m ruff check .; then
  echo "[clean_code_after] ruff check failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m mypy .; then
  echo "[clean_code_after] mypy failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m pytest; then
  echo "[clean_code_after] pytest failed" >> "$LOG"
fi

echo "[clean_code_after] second pass complete: $(date -Is)" >> "$LOG"
