# Poetry to UV Migration Documentation

This repository contains all documentation, runbooks, tracking artifacts, and migration scripts for migrating Poetry-based Python projects to UV.

## Key Documents

- **poetry_migration_strategy.md** — High-level migration strategy and phased plan
- **poetry_migration_runbook.md** — Operational runbook with per-repo status tracking and helper script templates
- **poetry_to_uv_manifest.yaml** — Machine-readable manifest of all repos

## Tracking Files

- **poetry_projects.txt** — List of Poetry-based projects
- **uv_lock_projects.txt** — List of projects with uv.lock files

## Migration Scripts & Logs

- `.temp.migrate_poetry_to_uv.<repo>.<number>.sh` — Versioned migration scripts per repo
- `.temp.migrate_poetry_to_uv.<repo>.<number>.<timestamp>.log` — Execution logs for forensic analysis

## Maintenance

- Update runbook after each repo migration
- Commit changes with descriptive messages
- Keep manifest in sync with actual repo states
- Migration scripts and logs are version controlled for traceability

## Conventions

- Use Australian English spelling across docs, comments, test names, and messages.

## Other Files (no need to read)

- **migratingPoetryReposToUV-reflactions-and-suggestions.md** — Retrospective analysis and recommendations
- **USING_UV.md** — initial file for uv migration, scoping, setup, and usage
- **poetry_to_uv_migration_guide.md** — Technical migration guide
- **poetry_to_uv_migration.txt** — Migration pre-planning directory scans
- **poetry_projects_2025-10-30.txt** — List of Poetry-based projects
- **poetry_projects.txt** — List of Poetry-based projects
- **.temp.migrate_to_poetry_migration.sh** — Migration script
- **.temp.migrate_to_poetry_migration.1761816698.log** — Migration script log
