#!/bin/sh
set -eu
cd /home/jon/Work
LOG=/home/jon/Work/uv_migration_20251030021925.log
touch ""
find . -name pyproject.toml   -not -path './1-mtdatalake*'   -not -path './2-mtdatalake*'   -not -path './.*'   -not -path '*/.venv/*'   -not -path '*/site-packages/*'   -not -path '*/node_modules/*'   -not -path '*/build/*'   -not -path '*/dist/*'   | sort -u   | while IFS= read -r file; do
    dir=
    dir=.
    printf '\n=== %s ===\n' "" | tee -a ""
    if [ ! -d "" ]; then
      printf 'Directory missing, skipping\n' | tee -a ""
      continue
    fi
    if [ -d "/.venv" ]; then
      rm -rf "/.venv"
    fi
    if (cd "" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv sync --refresh >> "" 2>&1); then
      printf 'uv sync ok\n' | tee -a ""
    else
      printf 'uv sync failed\n' | tee -a ""
      continue
    fi
    if (cd "" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run ruff check >> "" 2>&1); then
      printf 'ruff ok\n' | tee -a ""
    else
      printf 'ruff failed\n' | tee -a ""
    fi
    if (cd "" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run mypy . >> "" 2>&1); then
      printf 'mypy ok\n' | tee -a ""
    else
      printf 'mypy failed\n' | tee -a ""
    fi
    if (cd "" && VIRTUAL_ENV= UV_CACHE_DIR=/home/jon/Work/.cache/uv uv run pytest >> "" 2>&1); then
      printf 'pytest ok\n' | tee -a ""
    else
      printf 'pytest failed\n' | tee -a ""
    fi
  done
printf '\nDetailed log: %s\n' ""
