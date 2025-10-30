#!/usr/bin/env bash
set -euo pipefail

REPO="$HOME/Work/AjanCodesExamples/2024/clean_code/after"

cd "$REPO"

rm -rf .venv .mypy_cache .ruff_cache .pytest_cache __pycache__
