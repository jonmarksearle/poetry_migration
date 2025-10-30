#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="$HOME/Work/AjanCodesExamples/2024/func_design"
CACHE_DIR="$HOME/Work/.cache/uv"

cd "$REPO"

unset VIRTUAL_ENV

echo "[func_design] validation pass: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh
UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev

PYTHON_BIN=".venv/bin/python"

"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m mypy .
"$PYTHON_BIN" -m pytest

echo "[func_design] validation complete: $(date -Is)" >> "$LOG"
