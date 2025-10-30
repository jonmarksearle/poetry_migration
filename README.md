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
