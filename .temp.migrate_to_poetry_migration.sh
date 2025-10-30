#!/usr/bin/env bash
set -euo pipefail

# Migration script to create poetry_migration/ doc repo
# This consolidates all Poetry→UV migration documentation into a single git-controlled location

WORK_DIR="/home/jon/Work"
TARGET_DIR="${WORK_DIR}/poetry_migration"
TIMESTAMP=$(date +%s)

echo "=== Poetry Migration Doc Repo Setup ==="
echo "Timestamp: $(date -Iseconds)"
echo ""

# Pre-flight check: ensure we're in the right place
cd "${WORK_DIR}"
echo "✓ Working directory: $(pwd)"
echo ""

# Step 1: Create target directory
echo "Step 1: Creating ${TARGET_DIR}..."
if [[ -d "${TARGET_DIR}" ]]; then
  echo "ERROR: ${TARGET_DIR} already exists. Aborting."
  exit 1
fi
mkdir -p "${TARGET_DIR}"
echo "✓ Directory created"
echo ""

# Step 2: Initialize git repo
echo "Step 2: Initializing git repository..."
cd "${TARGET_DIR}"
git init
git config user.name "Jon"
git config user.email "jonmarksearle@gmail.com"
echo "✓ Git initialized"
echo ""

# Step 3: Create .gitignore
echo "Step 3: Creating .gitignore..."
cat > .gitignore <<'EOF'
# Python artifacts
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Editor artifacts
.vscode/
.idea/
*.swp
*~
EOF
echo "✓ .gitignore created"
echo ""

# Step 4: Move documentation files
echo "Step 4: Moving documentation files..."
cd "${WORK_DIR}"

# Core strategy and runbook docs
mv -v migratingPoetryReposToUV.md "${TARGET_DIR}/"
mv -v migratingPoetryReposToUV-reflactions-and-suggestions.md "${TARGET_DIR}/"
mv -v poetry_migration_runbook.md "${TARGET_DIR}/"
mv -v poetry_to_uv_migration_guide.md "${TARGET_DIR}/"

# Manifest and tracking files
mv -v poetry_to_uv_manifest.yaml "${TARGET_DIR}/"
mv -v poetry_projects.txt "${TARGET_DIR}/"
mv -v poetry_projects_2025-10-30.txt "${TARGET_DIR}/"
mv -v uv_lock_projects.txt "${TARGET_DIR}/"

# Migration notes and artifacts
mv -v poetry_to_uv_migration.txt "${TARGET_DIR}/"

# Temp migration scripts and logs
echo "Moving temp migration scripts and logs..."
mv -v .temp.migrate_poetry_to_uv.*.sh "${TARGET_DIR}/" 2>/dev/null || echo "  (no .sh files found)"
mv -v .temp.migrate_poetry_to_uv.*.log "${TARGET_DIR}/" 2>/dev/null || echo "  (no .log files found)"

echo "✓ Documentation files moved"
echo ""

# Step 5: Create README
echo "Step 5: Creating README.md..."
cd "${TARGET_DIR}"
cat > README.md <<'EOF'
# Poetry to UV Migration Documentation

This repository contains all documentation, runbooks, tracking artifacts, and migration scripts for migrating Poetry-based Python projects to UV.

## Key Documents

- **migratingPoetryReposToUV.md** — High-level migration strategy and overview
- **migratingPoetryReposToUV-reflactions-and-suggestions.md** — Retrospective analysis and recommendations
- **poetry_migration_runbook.md** — Operational runbook with per-repo status tracking
- **poetry_to_uv_migration_guide.md** — Technical migration guide
- **poetry_to_uv_manifest.yaml** — Machine-readable manifest of all repos

## Tracking Files

- **poetry_projects.txt** — List of Poetry-based projects
- **uv_lock_projects.txt** — List of projects with uv.lock files
- **poetry_to_uv_migration.txt** — Migration notes

## Migration Scripts & Logs

- `.temp.migrate_poetry_to_uv.<repo>.<number>.sh` — Versioned migration scripts per repo
- `.temp.migrate_poetry_to_uv.<repo>.<number>.<timestamp>.log` — Execution logs for forensic analysis

## Maintenance

- Update runbook after each repo migration
- Commit changes with descriptive messages
- Keep manifest in sync with actual repo states
- Migration scripts and logs are version controlled for traceability
EOF
echo "✓ README.md created"
echo ""

# Step 6: Initial commit
echo "Step 6: Creating initial commit..."
git add .
git commit -m "Initial commit: Consolidate Poetry→UV migration documentation

Migrated from /home/jon/Work/:
- Strategy docs (migratingPoetryReposToUV.md, reflections)
- Runbook and guide
- Manifest and tracking files
- Created README and .gitignore

This establishes a single source of truth for migration docs,
decoupled from the AjanCodesExamples repo."
echo "✓ Initial commit created"
echo ""

# Step 7: Summary
echo "=== Migration Complete ==="
echo "Repository location: ${TARGET_DIR}"
echo "Git status:"
git log --oneline -1
echo ""
echo "Files in repo:"
ls -1
echo ""
echo "Next steps:"
echo "1. Review the migrated files"
echo "2. Update any scripts that reference old doc paths"
