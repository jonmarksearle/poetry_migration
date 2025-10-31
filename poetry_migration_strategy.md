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
1. **Repository Analysis**:
   - Scan for duplicate dependencies
   - Validate version constraints
   - Check for module name conflicts
   - Identify missing type stubs
   - Detect async code usage
   - Check type annotation usage
   - Analyze line lengths
   - Determine Python version requirements

2. **Smart Tool Configuration**:
   - Configure mypy based on code analysis:
     - Strict mode for typed code
     - Async checks for async code
     - Module exclusions for before/after examples
   - Configure ruff based on code style:
     - Line length limits
     - Directory exclusions
   - Add missing type stubs automatically

3. **Dependency Management**:
   - Normalize version constraints
   - Remove duplicate dependencies
   - Add missing type stub packages
   - Preserve existing dev dependencies
   - Add standard dev tools

4. **Error Prevention**:
   - Pre-migration analysis to catch issues
   - Automatic tool configuration
   - Version constraint normalization
   - Type stub detection and installation

## 4. Migration Script

The migration process is automated through `migrate_repo.py` which:

1. **Analysis Phase**:
   ```python
   analysis = analyze_repo(repo_path)
   # Checks for:
   # - Duplicate dependencies
   # - Invalid versions
   # - Module conflicts
   # - Missing type stubs
   # - Async code
   # - Type annotations
   # - Line lengths
   ```

2. **Tool Configuration**:
   ```python
   tool_config = configure_tools(repo_path, analysis)
   # Configures:
   # - mypy settings based on code
   # - ruff settings based on style
   # - pytest settings (standard)
   ```

3. **Dependency Management**:
   ```python
   deps = normalize_dependencies(poetry_config, analysis)
   # - Normalizes version constraints
   # - Adds missing type stubs
   # - Removes duplicates
   # - Preserves existing dev deps
   ```

4. **Migration Execution**:
   ```python
   success = migrate_repo(repo_path)
   # - Converts pyproject.toml
   # - Creates .python-version
   # - Runs all checks
   # - Commits changes
   ```

## 5. Success Criteria

A repository is considered successfully migrated when:
1. Pre-migration analysis shows no critical issues
2. pyproject.toml uses PEP621 format
3. All dependencies are properly declared
4. Tools are configured based on code analysis
5. All checks pass:
   - `uv sync --refresh`
   - `uv sync --group dev`
   - `uv run deptry .`
   - `uv run ruff check .`
   - `uv run mypy .`
   - `uv run pytest`
6. Changes are committed
7. Manifest is updated

## 6. Background Reading
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal: <https://peps.python.org/pep-0735/>
- Deptry documentation: <https://github.com/fpgmaas/deptry>

---
*Last updated: 2025-10-30*
