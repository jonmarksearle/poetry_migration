# Migrating Poetry Repositories to uv

## 1. Rationale
- Consolidate all Python tooling around uv for consistent interpreter management, dependency resolution, and caching on `/home/jon/Work`.
- Eliminate Poetry’s virtualenvs/lockfiles to simplify CI/CD, reduce duplicate caches, and align with the migration plan already used for uv-native projects.
- Resolve the drift between Poetry metadata and actual code: many demos lack dev extras or pin outdated dependencies; uv forces explicit PEP 621 metadata.

## 2. Objectives
- Convert every Poetry-based repository under `/home/jon/Work` (excluding Docker-only projects like `1-mtdatalake`, `2-mtdatalake`) to PEP 621 `[project]` metadata consumable by uv.
- Replace `poetry.lock` with `uv.lock`, remove stray `.venv` directories, and ensure `uv sync` succeeds on a clean checkout.
- Update docs, scripts, and CI to use `uv sync`, `uv run`, and the Work-volume installer.
- Capture a repeatable process (automation + checklist) so future repos can be converted without reinventing the steps.

## 3. Strategy
1. **Inventory & Tiering**:
   - Tier 1: simple apps/libs (no extras, minimal dev deps).
   - Tier 2: extras/dev groups/dev tooling (FastAPI demos, lint/test stacks).
   - Tier 3: projects with Poetry-only plugins or custom build steps—handle individually.
2. **Metadata Conversion**:
   - For Tier 1 repos consider `uvx migrate-to-uv` to bootstrap conversion; fall back to a custom `tomlkit` script for complex cases.
   - Programmatically translate `[tool.poetry]` to `[project]` (PEP 621) while preserving comments.
   - Convert dependency version constraints (caret/tilde/star) to explicit PEP 508 ranges.
   - Map Poetry dependency groups (`tool.poetry.group.*`) to `[dependency-groups]`; reserve `[project.optional-dependencies]` for install-time extras only.
   - Persist tool configurations (`tool.ruff`, `tool.pytest.ini_options`) unchanged.
3. **Automation**:
   - Generate audit logs for each conversion (before/after `pyproject.toml`, command output).
   - When creating helper scripts, always use the `export FILE=".temp.migrate_poetry_to_uv.<repo>.sh" && cat <<'EOF' > "$FILE"` pattern so shell history and cleanup remain consistent.
   - Include Poetry script entry points: map `[tool.poetry.scripts]` → `[project.scripts]` during conversion.
   - Normalize `requires-python` (e.g., `^3.10` → `>=3.10`) while noting any upper bounds explicitly if needed.
   - Allow per-project overrides (skip/force groups) via a manifest file.
4. **Verification**:
   - Run `uv sync --refresh`, then `uv sync --group dev[,test,…]` as defined in each project.
   - Run `uv run ruff check`, `uv run mypy .`, `uv run pytest` and collect failures.
5. **Documentation & CI**:
   - Update README/Makefile/CI to replace `poetry` commands with `uv` equivalents.
   - Append migration notes to `MigratingToUV.md` and track per-repo status in a spreadsheet/log.

## 4. Plan of Record

### Phase 0 – Preparation (1 day)
- [x] Generate list of Poetry projects (`rg "\[tool\.poetry\]"`) and persist as `poetry_projects_2025-10-30.txt`.
- [ ] Snapshot each target repo (`git status`, `cp pyproject.toml pyproject.poetry.bak`).
- [x] Create `poetry_to_uv_manifest.yaml` to mark special cases (e.g., skip, custom extras).
- [ ] Set up automation virtualenv (use existing uv install).

-
### Phase 1 – Metadata Conversion Script (1–2 days)
- [ ] Implement `scripts/convert_poetry_to_uv.py`:
  - Parse `pyproject.toml` with `tomlkit` (preserve formatting/comments).
  - Build `[project]` from Poetry metadata (name, version, description, readme, python constraint).
   - Convert caret/tilde dependency specs to explicit `>=,<` ranges; for `requires-python` prefer open upper bounds (e.g., `^3.10` → `>=3.10`).
  - Map `tool.poetry.group.*.dependencies` into `[dependency-groups]` (e.g., `dev`, `test`).
  - Map `tool.poetry.extras` to `[project.optional-dependencies]` and `tool.poetry.scripts` to `[project.scripts]`.
  - Preserve/define `[build-system]` (`hatchling` for libraries, or keep existing backend).
  - If conflicting keys exist (e.g., `[project]` already present), log and skip.
  - Write new `pyproject.toml`, keep backup as `.poetry-backup`.
- [ ] Add dry-run mode for verification.

### Phase 2 – Batch Conversion (2–3 days)
- [ ] For Tier 1 projects, run script in batch:
  - `python scripts/convert_poetry_to_uv.py <repo>`.
  - Delete `poetry.lock`, `.venv/`.
  - `UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --refresh`.
  - `UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --group dev` (add other groups as defined).
  - `uv run ruff check`, `uv run mypy .`, `uv run pytest`. Log results.
- [ ] Commit new `pyproject.toml`, `uv.lock`, `.python-version` (if project-specific) per repo.
- [ ] Document any lint/test failures needing code changes.

### Phase 3 – Handle Complex Repos (3–5 days as needed)
- [ ] For Tier 2/3, adjust script or handle manually:
  - Confirm extras remain under `[project.optional-dependencies]`; keep dev/test tooling in `[dependency-groups]`.
  - For FastAPI/ML demos, ensure dependency groups (`dev`, `test`, etc.) are defined and instruct contributors to run `uv sync --group dev[,test]` as appropriate.
  - Evaluate whether `uvx migrate-to-uv` can bootstrap conversion before applying manual tweaks.
  - If a Poetry plugin is irreplaceable, consider leaving repo on Poetry with documentation.
- [ ] Update Dockerfiles/CI to run uv commands.

### Phase 4 – Validation & Cleanup (1 day)
- [ ] Run the chunked uv migration scripts to confirm `uv sync` + tooling succeed project-wide.
- [ ] Update aggregate log (`poetry_to_uv_status.md`) summarizing remaining work.
- [ ] Remove global Poetry installs (`pipx uninstall poetry`) once confirmed unused.
- [ ] Archive backups (`pyproject.poetry.bak`) or keep under version control for reference.

## 5. Detailed Instructions

1. **Identify Poetry Projects**
   ```bash
   find /home/jon/Work -name pyproject.toml \
     -not -path '*/.venv/*' -not -path '*/node_modules/*' \
     -exec bash -c 'grep -q "\[tool\.poetry\]" "$0" && echo "$0"' {} \; \
     | tee poetry_projects.txt
   ```

2. **Back Up and Prepare**
   ```bash
   while read -r file; do
     dir=$(dirname "$file")
     cp "$file" "$dir/pyproject.poetry.bak"
     rm -f "$dir/poetry.lock"
     rm -rf "$dir/.venv"
   done < poetry_projects.txt
   ```

3. **Convert Metadata**
   ```bash
   # Simple cases
   uvx migrate-to-uv /home/jon/Work/AjanCodesExamples/2023/apitesting

   # Complex cases (custom groups/extras)
   python scripts/convert_poetry_to_uv.py /home/jon/Work/AjanCodesExamples/2023/apitesting
   ```
   Expectation:
   - `[tool.poetry]` replaced by `[project]` with caret/tilde versions expanded.
   - Dev/test dependencies moved into `[dependency-groups]` (e.g., `dev`, `test`).
   - Extras remain under `[project.optional-dependencies]`.
   - `tool.poetry.scripts` copied to `[project.scripts]`.
   - Existing `build-system` retained or set to `hatchling` for libraries.

4. **Pin Project Interpreter**
   ```bash
   cd /home/jon/Work/AjanCodesExamples/2023/apitesting
   echo "3.13" > .python-version  # adjust per project as needed
   ```

5. **Run uv Sync + Tooling**
   ```bash
   cd /home/jon/Work/AjanCodesExamples/2023/apitesting
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --refresh
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --group dev  # add --group dev,test if multiple groups
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv run ruff check
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv run mypy .
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv run pytest
   ```
   Log failures in `uv_migration_poetry.log` for follow-up.

6. **Update Documentation & CI**
   - Replace `poetry install` / `poetry run` with `uv sync` / `uv run` in READMEs.
   - Ensure CI uses:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     uv sync --frozen
     uv run pytest
     ```

7. **Track Progress**
   - Maintain `poetry_to_uv_status.md` with columns: repo, converted (Y/N), lint result, mypy result, pytest result, notes.
   - Use chunked scripts (already created) to re-run migrations after fixes: `sh .temp.bash.uv_lock_chunk_aa.sh`, etc.

8. **Post-migration Cleanup**
   - Once all conversions succeed, remove Poetry-specific tooling/scripts.
   - Keep `pyproject.poetry.bak` for reference or delete after verification.
   - Update `MigratingToUV.md` with a section linking to this document and summarizing the Poetry conversion journey.

## 6. Runbook & Operational Tracking
- Active execution notes, helper script templates, status tables, and edge cases now live in `poetry_migration_runbook.md`.
- Update that runbook after each repository migration; update this strategy document only when the overall plan changes.


## 7. Background to Read-Up Before You Start
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal (uv behaviour reference): <https://peps.python.org/pep-0735/>
- Migrate-to-uv tool overview: <https://github.com/mkniewallner/migrate-to-uv>
- Hatch build targets (wheel include rules): <https://hatch.pypa.io/latest/config/build/>


---
*Last updated: 2025-10-30 (strategy doc split from runbook)*
