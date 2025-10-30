#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/poetry_migration/uv_migration_poetry.log"
REPO="/home/jon/Work/AjanCodesExamples/2024/python15"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

# Pre-flight check: ensure clean working tree
if [[ -n $(git status --porcelain) ]]; then
  echo "ERROR: Uncommitted changes detected in $REPO. Commit or stash first."
  exit 1
fi

unset VIRTUAL_ENV

cp pyproject.toml pyproject.poetry.bak
rm -f poetry.lock
rm -rf .venv

# Convert using the migration script
UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

if [ ! -f .python-version ]; then
  printf "3.12\n" > .python-version  # Using 3.12 as specified in original pyproject.toml
fi

echo "[python15] migration started: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

# Run deptry to audit dependencies
if ! UV_CACHE_DIR="$CACHE_DIR" uv run deptry .; then
  echo "[python15] deptry audit failed - missing or unused dependencies detected" >> "$LOG"
  exit 1
fi

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[python15] uv sync --group dev failed" >> "$LOG"
fi

# Find Python files to check
mapfile -t MYPY_TARGETS < <(find src -type f -name '*.py' 2>/dev/null)
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  mapfile -t MYPY_TARGETS < <(find . -maxdepth 1 -type f -name '*.py')
fi
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  MYPY_TARGETS=(.)
fi

PYTHON_BIN=".venv/bin/python"

if ! "$PYTHON_BIN" -m ruff check .; then
  echo "[python15] ruff check failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m mypy "${MYPY_TARGETS[@]}"; then
  echo "[python15] mypy failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m pytest; then
  echo "[python15] pytest failed" >> "$LOG"
fi

# Idempotent cleanup
rm -rf .venv .mypy_cache .ruff_cache .pytest_cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "[python15] migration complete: $(date -Is)" >> "$LOG"
