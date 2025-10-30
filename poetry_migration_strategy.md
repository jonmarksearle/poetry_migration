# Migrating Poetry Repositories to uv

## 1. Rationale
- Consolidate all Python tooling around uv for consistent interpreter management, dependency resolution, and caching on `/home/jon/Work`.
- Eliminate Poetry's virtualenvs/lockfiles to simplify CI/CD, reduce duplicate caches, and align with the migration plan already used for uv-native projects.
- Resolve the drift between Poetry metadata and actual code: many demos lack dev extras or pin outdated dependencies; uv forces explicit PEP621 metadata.

## 2. Objectives
- Convert every Poetry-based repository under `/home/jon/Work` (excluding Docker-only projects) to PEP621 `[project]` metadata consumable by uv.
- Replace `poetry.lock` with `uv.lock`, remove stray `.venv` directories, and ensure `uv sync` succeeds on a clean checkout.
- Update docs, scripts, and CI to use `uv sync`, `uv run`, and the Work-volume installer.
- Capture a repeatable process through automation so future repos can be converted without reinventing the steps.

## 3. Strategy
1. **Inventory & Tiering**:
   - Tier 1: simple apps/libs (no extras, minimal dev deps).
   - Tier 2: extras/dev groups/dev tooling (FastAPI demos, lint/test stacks).
   - Tier 3: projects with Poetry-only plugins or custom build steps—handle individually.

2. **Automation**:
   - Use `migrate_repo.py` script for consistent conversions
   - Script handles:
     - Metadata conversion from Poetry to PEP621
     - Version constraint normalization
     - Standard dev tooling injection
     - Dependency auditing with deptry
     - Code quality checks (ruff, mypy)
     - Git commits and manifest updates

3. **Verification**:
   - Run `uv sync --refresh`, then `uv sync --group dev[,test,…]` as defined
   - Run `uv run deptry .` to detect missing/unused dependencies
   - Run `uv run ruff check`, `uv run mypy .`, `uv run pytest`
   - Collect failures and address per-repo

4. **Documentation & CI**:
   - Update README/Makefile/CI to replace `poetry` commands with `uv`
   - Track per-repo status in manifest YAML

## 4. Migration Script

The migration process is automated through `migrate_repo.py` which:

1. Detects already migrated repositories
2. Converts pyproject.toml from Poetry to UV format:
   - Preserves metadata
   - Converts version constraints
   - Adds standard dev tools
   - Handles extras and groups
3. Creates .python-version file
4. Runs all checks (ruff, mypy, pytest)
5. Commits changes if successful
6. Updates the manifest

Usage:
```bash
cd /home/jon/Work/poetry_migration
python migrate_repo.py /path/to/repo
```

## 5. Success Criteria

A repository is considered successfully migrated when:
1. pyproject.toml uses PEP621 format
2. All dependencies are properly declared
3. Standard dev tools are configured
4. All checks pass:
   - `uv sync --refresh`
   - `uv sync --group dev`
   - `uv run deptry .`
   - `uv run ruff check .`
   - `uv run mypy .`
   - `uv run pytest`
5. Changes are committed
6. Manifest is updated

## 6. Background Reading
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal: <https://peps.python.org/pep-0735/>
- Deptry documentation: <https://github.com/fpgmaas/deptry>

---
*Last updated: 2025-10-30*
