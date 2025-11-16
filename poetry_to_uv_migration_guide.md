# Poetry to UV Migration Guide

Based on research from multiple sources, here's the practical guide for migrating your Poetry projects to uv.

## Quick Migration (Automated)

The easiest path is using the `migrate-to-uv` tool:

```bash
cd your-poetry-project
uvx migrate-to-uv
```

This handles:
- Converting Poetry metadata to uv format
- Preserving dependency versions
- Generating `uv.lock` file
- Maintaining dependency groups

### Common Options

```bash
# Dry run to preview changes
uvx migrate-to-uv --dry-run

# Skip lock file generation (do it manually later)
uvx migrate-to-uv --skip-lock

# Keep original Poetry config for comparison
uvx migrate-to-uv --keep-current-data

# Handle dependency groups (choose one strategy)
uvx migrate-to-uv --dependency-groups-strategy set-default-groups
uvx migrate-to-uv --dependency-groups-strategy include-in-dev
uvx migrate-to-uv --dependency-groups-strategy merge-into-dev
uvx migrate-to-uv --dependency-groups-strategy keep-existing
```

## Manual Migration (More Control)

If you want more control or the automated tool doesn't work:

### Step 1: Use PDM's Import Tool

```bash
uvx pdm import pyproject.toml
```

This converts Poetry format to PDM format (which is close to uv).

### Step 2: Clean Up pyproject.toml

Remove these sections:
- All `[tool.poetry]` sections
- All `[tool.poetry.group.*]` sections
- `[tool.pdm.build]` section
- Old `[build-system]` section (if not using a specific build backend)

### Step 3: Rename and Reorganize

1. Rename `[tool.pdm.dev-dependencies]` → `[dependency-groups]`
2. Move `[dependency-groups]` below `[project]`
3. Reorder version constraints for readability: `>=5.1.3, <6.0.0` instead of `<6.0.0,>=5.1.3`

### Step 4: Optional - Configure Default Groups

Add this to prevent installing all groups by default:

```toml
[tool.uv]
default-groups = []
```

Then explicitly install groups when needed:
```bash
uv sync --group dev
uv sync --group prod
```

### Step 5: Recreate Environment

```bash
rm -rf .venv poetry.lock
uv sync
```

## Key Differences: Poetry vs UV

### Dependency Groups

**Poetry:**
```toml
[tool.poetry.group.dev]
optional = true

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
```

**UV:**
```toml
[dependency-groups]
dev = [
    "pytest >=8.0.0, <9.0.0",
]
```

### Version Constraints

**Poetry:** Uses caret (`^`) and tilde (`~`) operators
- `^1.2.3` means `>=1.2.3, <2.0.0`
- `~1.2.3` means `>=1.2.3, <1.3.0`

**UV:** Uses explicit ranges
- `>=1.2.3, <2.0.0`

### Build Backend

**Poetry:**
```toml
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**UV (default):**
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Or omit entirely if not publishing a package.

## Private Package Repositories

If using private indexes, set environment variables:

```bash
export UV_INDEX_COMPANY_REPO_USERNAME=<username>
export UV_INDEX_COMPANY_REPO_PASSWORD=<password>
```

Then run migration.

## Verification Steps

After migration:

1. **Check pyproject.toml** - Verify all dependencies are present
2. **Test installation** - `uv sync`
3. **Run tests** - `uvx pytest`
4. **Check scripts** - Verify any `[project.scripts]` entries work
5. **Verify extras** - Test optional dependencies: `uv sync --extra duckdb`

## Common Issues

### Issue: "No `project` table found"
**Solution:** Ensure you have a `[project]` section with at least `name` and `version`.

### Issue: Maturin or other build backends
**Solution:** Keep your original `[build-system]` section, don't let PDM override it.

### Issue: pip not available
**Solution:** uv doesn't install pip by default and you don't need it, use add. Add it if needed:
`uv add ...`
Or:
`uv add ... --dev`

### Issue: Pre-commit hooks fail
**Solution:** Update `.pre-commit-config.yaml` to use uv:
```yaml
- repo: local
  hooks:
    - id: pytest
      name: pytest
      entry: uvx pytest
      language: system
      pass_filenames: false
```

## UV Commands Cheat Sheet

```bash
# Install dependencies
uv sync

# Install with specific groups
uv sync --group dev --group test

# Install with extras
uv sync --extra postgres

# Add a dependency
uv add requests

# Add a dev dependency
uv add pytest --dev

# Remove a dependency
uv remove requests

# Run a command in the environment
uv run python script.py
uvx pytest

# Update dependencies
uv lock --upgrade

# Run without installing (like npx)
uvx black .
```

## Why Migrate?

1. **Speed** - uv is 10-100x faster than Poetry for dependency resolution
2. **Standards** - Uses PEP 621 (pyproject.toml standard)
3. **Simplicity** - Single tool for Python versions, venvs, and packages
4. **Compatibility** - Works with existing pip/PyPI ecosystem
5. **Active Development** - Backed by Astral (makers of Ruff)

## When NOT to Migrate

- Your team is happy with Poetry and has no issues
- You rely on Poetry plugins or specific Poetry features
- You're publishing packages and Poetry's build system works perfectly
- Migration would disrupt active development cycles

## Resources

- Official uv docs: https://docs.astral.sh/uv/
- migrate-to-uv tool: https://github.com/mkniewallner/migrate-to-uv
- Python Developer Tooling Handbook: https://pydevtools.com/handbook/
