#!/bin/sh
set -eu
cd /home/jon/Work
LOG="/home/jon/Work/uv_migration_uv_lock_chunk_aa.log"
touch "$LOG"
while IFS= read -r lockfile; do
  dir=$(dirname "$lockfile")
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
  printf '\n' | tee -a "$LOG"
done < uv_lock_chunk_aa
printf '\nDetailed log: %s\n' "$LOG"
