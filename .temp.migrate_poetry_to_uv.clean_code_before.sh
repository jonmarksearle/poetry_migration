#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="$HOME/Work/AjanCodesExamples/2024/clean_code/before"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

unset VIRTUAL_ENV

cp pyproject.toml pyproject.poetry.bak
rm -f poetry.lock
rm -rf .venv

if grep -q "\[tool.poetry\]" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .
fi

if [ ! -f .python-version ]; then
  printf "3.11\n" > .python-version
fi

echo "[clean_code_before] migration started: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[clean_code_before] uv sync --group dev failed" >> "$LOG"
fi

mapfile -t MYPY_TARGETS < <(find src -type f -name '*.py' 2>/dev/null)
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  mapfile -t MYPY_TARGETS < <(find . -maxdepth 1 -type f -name '*.py')
fi
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  MYPY_TARGETS=(.)
fi

PYTHON_BIN=".venv/bin/python"

if ! "$PYTHON_BIN" -m ruff check .; then
  echo "[clean_code_before] ruff check failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m mypy "${MYPY_TARGETS[@]}"; then
  echo "[clean_code_before] mypy failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m pytest; then
  echo "[clean_code_before] pytest failed" >> "$LOG"
fi

echo "[clean_code_before] migration complete: $(date -Is)" >> "$LOG"
