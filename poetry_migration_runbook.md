# Poetry Migration Runbook

This runbook captures in-flight progress, operational procedures, and edge cases for migrating Poetry-based repositories to uv. Strategic context and the overall migration plan remain in `migratingPoetryReposToUV.md`.

## 1. Status Dashboard (updated 2025-10-30)

| Repository | Migration Date | Time | `uv sync` | `uv run ruff` | `uv run mypy` | `uv run pytest` | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023/apitesting | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Added `httpx` to `dependency-groups.dev`; refactored `db_update_item` to accept `ItemUpdate`. |
| 2023/classguide | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Added `test_smoke.py`; removed unused SMTP variable. |
| 2023/doc | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | License recorded as `{text = "MTI"}`; added `test_smoke.py`. |
| 2023/funclass | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Added Counter typing; smoke test keeps pytest happy; mypy targets src modules. |
| 2023/shellroast/after | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Typed algorithm registry, added path-aware conftest + smoke test for encode/decode roundtrip. |
| 2024/clean_code/after | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Slugged project name, added python-dotenv + dev tooling, smoke tests for invoice orchestration. |
| 2024/clean_code/before | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Renamed package, added dev tool deps, stubbed invoices import, and added payment-intent smoke test. |
| 2024/func_design | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Converted to hatch/uv, pinned 3.12, added dev tooling and generics/options smoke coverage. |
| 2024/func | 2025-10-30 | — | ✅ | ✅ | ✅ | ✅ | Slugged project name, scripted entrypoint, importlib-based smoke tests, 3.12 toolchain. |

Update this table after each migration, including failures (use ❌ and note remediation).

## 2. Helper Script Template

Create a per-repo helper script in `/home/jon/Work` using the template below. Replace `<REPO_PATH>` with the absolute path to the repository and `<REPO_NAME>` with the short tag used in log messages.

Always generate the script via the environment-variable pattern shown here (e.g., `export FILE=".temp.migrate_poetry_to_uv.<repo>.sh" && cat <<'EOF' > "$FILE"`). This keeps transient helpers discoverable and documents their provenance in the shell history.

```bash
export FILE=".temp.migrate_poetry_to_uv.<REPO_NAME>.sh" && cat <<'EOS' > "$FILE"
#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Work/uv_migration_poetry.log"
REPO="<REPO_PATH>"
CACHE_DIR="$HOME/Work/.cache/uv"
CONVERTER="/home/jon/Work/scripts/convert_poetry_to_uv.py"

cd "$REPO"

unset VIRTUAL_ENV

cp pyproject.toml pyproject.poetry.bak
rm -f poetry.lock
rm -rf .venv

UV_CACHE_DIR="$CACHE_DIR" uv run --with tomlkit python "$CONVERTER" .

if [ ! -f .python-version ]; then
  printf "3.11\n" > .python-version
fi

echo "[<REPO_NAME>] migration started: $(date -Is)" >> "$LOG"

UV_CACHE_DIR="$CACHE_DIR" uv sync --refresh

if grep -q "\[dependency-groups\]" pyproject.toml && grep -q "dev\s*=\s*" pyproject.toml; then
  UV_CACHE_DIR="$CACHE_DIR" uv sync --group dev || echo "[<REPO_NAME>] uv sync --group dev failed" >> "$LOG"
fi

mapfile -t MYPY_TARGETS < <(find src -type f -name '*.py' 2>/dev/null)
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  mapfile -t MYPY_TARGETS < <(find . -maxdepth 1 -type f -name '*.py')
fi
if [ "${#MYPY_TARGETS[@]}" -eq 0 ]; then
  MYPY_TARGETS=(.)
fi

PYTHON_BIN=".venv/bin/python"

if ! "$PYTHON_BIN" -m ruff check .; then
  echo "[<REPO_NAME>] ruff check failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m mypy "${MYPY_TARGETS[@]}"; then
  echo "[<REPO_NAME>] mypy failed" >> "$LOG"
fi

if ! "$PYTHON_BIN" -m pytest; then
  echo "[<REPO_NAME>] pytest failed" >> "$LOG"
fi

echo "[<REPO_NAME>] migration complete: $(date -Is)" >> "$LOG"
EOS

bash "$FILE"
```

Usage pattern:

1. Generate the script with the template above and review it before execution.
2. Execute `bash .temp.migrate_poetry_to_uv.<repo>.sh`.
3. Address logged failures immediately; rerun the script until all checks pass.
4. Keep scripts for reruns until the corresponding repo is fully migrated or superseded by automation.

## 3. Standard Operating Procedure

1. **Prepare**
   - Copy `pyproject.toml` to `pyproject.poetry.bak`.
   - Delete `poetry.lock` and any repository-local `.venv`.
2. **Convert**
   - Run the helper script (or `scripts/convert_poetry_to_uv.py` directly for ad-hoc work).
   - Review the resulting `pyproject.toml` and ensure `[project]`, `[dependency-groups]`, and `[build-system]` look correct.
3. **Stabilize**
   - Install missing dependencies (e.g., `httpx` for FastAPI tests) in the appropriate group.
   - Add smoke tests when a repo lacks test coverage (example: `test_smoke.py`).
   - Refactor code as needed to satisfy ruff/mypy/pytest.
4. **Document**
   - Record results in the status dashboard above.
   - Update repo-level README/CI instructions to use `uv` instead of Poetry.
   - Add new edge cases or learnings to Section 5 of this runbook.
5. **Commit**
   - Follow the commit protocol in Section 4.
6. **Iterate**
   - After each repository (or small batch), reassess converter behaviour.
   - Update this runbook with new procedures; only update `migratingPoetryReposToUV.md` when the overarching strategy changes.

## 4. Commit Protocol

1. Ensure `git status` shows only the active repo plus intentional `poetry.lock` removal.
2. Confirm `uv sync`, `uv run ruff`, `uv run mypy`, and `uv run pytest` succeed.
3. Stage repo-scoped files: `pyproject.toml`, `uv.lock`, `.python-version`, and any code/test modifications.
4. Leave `.bak` artifacts untracked unless there is a specific reason to commit them.
5. Commit with `migrate <repo> from poetry to uv`; create follow-up commits for additional fixes (e.g., tests or lint refactors).
6. Push after each batch to maintain an auditable history.

## 5. Edge Cases & Adjustments

- **License strings**: Converter wraps plain-text licenses as `{text = "..."}` to satisfy Hatch.
- **Missing README**: Converter skips `readme` keys when the referenced file does not exist, preventing Hatch build errors.
- **Flat-layout projects**: Helper ensures `[tool.hatch.build.targets.wheel].include = ["*.py", "**/*.py"]` when no importable package is found.
- **FastAPI test clients**: Add `httpx` (or other required extras) to `dependency-groups.dev` so pytest discovers the client.
- **Smoke tests**: Repos without tests (e.g., documentation or tutorial code) should receive a simple import/placeholder test to keep pytest green.
- **mypy package targets**: When projects expose modules directly under `src/`, prefer running `uv run mypy src/*.py` (or a broader glob) to avoid the "no .py[i] files" exit code.
- **Src layout pytest pathing**: If the package isn’t yet installed as a module, add a `tests/conftest.py` that prepends `<repo>/src` to `sys.path` so pytest can import the package until packaging is formalised.
- **Circular imports in legacy demos**: When tests trigger import cycles (e.g., `invoices` ↔ `processing`), inject lightweight stubs in `tests/` to satisfy type hints without executing the full module graph.
- **Git dependencies**: Poetry-style git dependencies carry over; confirm `rev`/`tag` pins and adjust if uv surfaces warnings.
- **Path dependencies**: Replace `develop = true` with `editable = true` when the converter surfaces local path deps.
- Capture new edge cases here as they appear.

## 6. Read-Up Before You Start
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal (explains uv group semantics): <https://peps.python.org/pep-0735/>
- Migrate-to-uv tool overview: <https://github.com/mkniewallner/migrate-to-uv>
- Hatch build targets (wheel include and path rules): <https://hatch.pypa.io/latest/config/build/>

## 7. Success & Rollback Criteria

**Success**
- `uv sync --refresh` (and relevant `uv sync --group ...`) complete.
- `uv run ruff`, `uv run mypy`, and `uv run pytest` all green.
- Updated `pyproject.toml`, `uv.lock`, `.python-version`, and tests committed.

**Rollback**
- If a migration exceeds two focused hours without green checks, capture the current state in a commit noting outstanding failures, then move to the next repo.
- Restore `pyproject.toml` from `pyproject.poetry.bak` only when explicitly abandoning a migration.
- Recreate `poetry.lock` from version control if a full rollback is required.
- Clean up `uv.lock`, `.python-version`, and migration-specific changes when reverting.
- Document the blockers and follow-up plan in this runbook before returning to the repo.

## 8. Documentation Follow-up Checklist
- [ ] Update repo READMEs/CI instructions to the `uv` workflow immediately after migration.
- [ ] Maintain `poetry_to_uv_status.md` with per-repo lint/type/test outcomes.
- [ ] Extend `poetry_to_uv_migration_guide.md` when the converter or helper scripts gain new behaviour.
- [ ] Review this runbook weekly during active migration sprints.

## 9. Change Log
- **2025-10-30** – Initial runbook extracted from `migratingPoetryReposToUV.md`; populated with first three migrations and operational procedures.
    
## 10. Read-Up Before You Start
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal (uv behaviour reference): <https://peps.python.org/pep-0735/>
- Migrate-to-uv tool overview: <https://github.com/mkniewallner/migrate-to-uv>
- Hatch build targets (wheel include rules): <https://hatch.pypa.io/latest/config/build/>
