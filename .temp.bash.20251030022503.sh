#!/bin/sh
set -eu
cd /home/jon/Work
LOG="/home/jon/Work/uv_migration_20251030022503.log"
touch "$LOG"
find . -name pyproject.toml   -not -path './1-mtdatalake*'   -not -path './2-mtdatalake*'   -not -path './.*'   -not -path '*/.venv/*'   -not -path '*/site-packages/*'   -not -path '*/node_modules/*'   -not -path '*/build/*'   -not -path '*/dist/*'   | sort -u   | while IFS= read -r file; do
    dir=$(dirname "$file")
    printf '\n=== %s ===\n' "$dir" | tee -a "$LOG"
    if [ ! -d "$dir" ]; then
      printf 'Directory missing, skipping\n' | tee -a "$LOG"
      continue
    fi
    if [ -d "$dir/.venv" ]; then
      rm -rf "$dir/.venv"
    fi
    if (cd "$dir" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv sync --refresh >> "$LOG" 2>&1); then
      printf 'uv sync ok\n' | tee -a "$LOG"
    else
      printf 'uv sync failed\n' | tee -a "$LOG"
      continue
    fi
    if (cd "$dir" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run ruff check >> "$LOG" 2>&1); then
      printf 'ruff ok\n' | tee -a "$LOG"
    else
      printf 'ruff failed\n' | tee -a "$LOG"
    fi
    if (cd "$dir" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run mypy . >> "$LOG" 2>&1); then
      printf 'mypy ok\n' | tee -a "$LOG"
    else
      printf 'mypy failed\n' | tee -a "$LOG"
    fi
    if (cd "$dir" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run pytest >> "$LOG" 2>&1); then
      printf 'pytest ok\n' | tee -a "$LOG"
    else
      printf 'pytest failed\n' | tee -a "$LOG"
    fi
  done
printf '\nDetailed log: %s\n' "$LOG"
