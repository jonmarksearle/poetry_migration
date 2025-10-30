# Migrating Poetry Repositories to uv — Reflections and Suggestions (2025-10-30)

This document captures an exhaustive retrospective on the most recent migration wave (clean_code before/after, func_design, func) as well as the supporting documentation and tooling work that accompanied it. The goal is to surface every notable observation—good, bad, and unresolved—and lay out concrete recommendations to improve both the pace and reliability of the remaining migrations.

## 1. Context Snapshot
- Timeframe examined: 2025-10-30 (Wave 1 Tier 1 follow-up runs).
- Repositories migrated in this tranche: `2024/clean_code/before`, `2024/clean_code/after`, `2024/func_design`, `2024/func`.
- Tooling stack: helper shell scripts (`.temp.migrate_poetry_to_uv.<repo>.sh` pattern), `scripts/convert_poetry_to_uv.py`, uv 0.4.x with Python 3.11/3.12 interpreters, and local smoke tests added per repo.
- Documentation touched: `poetry_migration_runbook.md`, `migratingPoetryReposToUV.md`, `poetry_to_uv_manifest.yaml` (mirrored into `poetry_migration_docs/` for version control), `uv_migration_poetry.log` for operational traces.
- Git state: working within `AjanCodesExamples` repo which already has pre-existing large-scale deletions (`poetry.lock` across many repos) and numerous `.bak` artifacts tracked as untracked files.

## 2. Highlights — What Worked
1. **Helper Script Convention**
   - The enforced `export FILE=".temp.migrate_poetry_to_uv.<repo>.sh" && cat <<'EOF' > "$FILE"` pattern gives repeatability, embeds steps in shell history, and leaves a re-runnable artifact for troubleshooting.
   - Running these scripts ensured uv sync, ruff, mypy, and pytest commands all ran in the repo-local `.venv`, isolating migrations per project.

2. **Doc Synchronisation Discipline**
   - After every repo migration, the runbook table and manifest entries were immediately updated (and mirrored into `poetry_migration_docs/`). This prevented drift between operational status and upstream documentation.

3. **Smoke Test Additions**
   - Introducing targeted smoke tests (`tests/test_smoke.py`) caught missing runtime deps (e.g., `python-dotenv`) and guaranteed minimal behaviour coverage post-migration.

4. **Iterative Logging**
   - `uv_migration_poetry.log` provided at-a-glance proof of retries/failures, which is invaluable when reconciling why certain repos took longer (e.g., `clean_code_after` initial mypy and pytest misses).

5. **Consistent Interpreter Pinning**
   - Writing `.python-version` explicitly (3.11 vs 3.12) eliminated ambiguity about which interpreter uv should provision, which in turn kept tooling output stable across runs.

## 3. Pain Points & Friction Areas
### 3.1 Automation Gaps
- **Converter script limitations**
  - `scripts/convert_poetry_to_uv.py` failed on `tomlkit.inline_table(scripts)` because the helper expects no positional arguments. Result: manual rewrite of `pyproject.toml` for `2024/func`. This class of issue will recur for any repo with `[tool.poetry.scripts]` present until the converter is patched.
  - The converter does not slugify project names or auto-detect runtime dependencies missing from `[tool.poetry.dependencies]` (e.g., `python-dotenv`). These holes require manual inspection each time.

- **Single-pass assumption**
  - The helper script assumes adding `[dependency-groups]` is optional, so subsequent `uv sync --group dev` steps silently skip when the group is absent. For new conversions we expect dev tooling; when the converter leaves the group out, we only diagnose after ruff/mypy failure.

### 3.2 Git Hygiene Challenges
- Large numbers of pre-existing deletions and untracked `.bak` files made selective doc commits impossible without broader staging. Attempts to land doc-only updates were blocked, requiring piggybacking on migration commits.
- Divergence with `origin/main` (ahead 11/behind 10) creates risk if other collaborators attempt merges without rebasing. No automation currently alerts us before we accumulate too many local commits.

### 3.3 Documentation Workflow
- Maintaining root-level strategy/runbook files outside the `AjanCodesExamples` repo and mirroring into `poetry_migration_docs/` is fragile—easy to forget the copy step or to end up with stale checked-in mirrors.
- There is no automated diff or checksum to confirm the mirror copy happened before commit.

### 3.4 Logging & Telemetry
- `uv_migration_poetry.log` captures timestamps but no pass/fail status aside from free-form strings. Without structure, slicing by repo or determining final status requires manual inspection.
- Log entries accumulate across retries, making it hard to know at a glance which attempt succeeded vs failed without reading the entire sequence.

### 3.5 Dependency Detection
- Runtime deps (e.g., `python-dotenv`) missing from the original Poetry metadata surface only during test execution. There is no automated audit to compare code imports against declared deps.
- Dev tooling (ruff/mypy/pytest) must be manually injected into `[dependency-groups] dev` each time. Forgetting to do so yields “No module named ruff/mypy/pytest” errors which the helper logs but does not remediate.

### 3.6 Test & Fixture Strategy
- Many educational repos lack `src/` structure or package names, so tests import modules via dynamic `importlib`. This works but is brittle and verbose; better fixtures (e.g., `sys.path` augmentation) could simplify future tests.
- Some tests rely on real time or timezone expectations (e.g., `log_message` tests). We had to adjust to dynamic formatting to avoid timezone-specific breakage.

### 3.7 Operational Overhead
- Cleanup after each run (`rm -rf .venv .mypy_cache .ruff_cache .pytest_cache __pycache__`) is manual and easy to overlook without the dedicated `.temp.migrate_poetry_to_uv.<repo>.<n>.sh` script.
- Repeated copying of documentation files to `poetry_migration_docs/` consumes time and is error-prone.

## 4. Recommendations
### 4.1 Improve the Converter Tooling
1. **Fix inline table handling**
   - Update `PoetryToUvConverter` to convert `[tool.poetry.scripts]` using `tomlkit.inline_table()` correctly. Also ensure `tool.poetry.name` values get slugged automatically (lowercase, hyphenated).

2. **Optional slug enforcement & metadata audit**
   - Add a post-conversion validation step that warns when the resulting `[project]` name contains spaces or uppercase characters.

3. **Dependency auto-discovery**
   - Integrate a static scan (e.g., `uvx deptry` or a custom AST walker) post-conversion to flag imports not satisfied by the dependency list. This would have surfaced `python-dotenv` before pytest ran.

4. **Dev tooling templates**
   - Have the converter inject a default `[dependency-groups].dev` block with ruff/mypy/pytest unless the manifest says otherwise. Coupled with that, add `types-requests` / `types-<pkg>` heuristics when `requests` is present.

### 4.2 Harden the Helper Scripts
1. **Idempotent cleanup**
   - Include cache/`.venv` cleanup at the end of each helper script run by default.
2. **Structured exit reporting**
   - Emit JSON or key-value summary at the end of scripts for easier parsing (e.g., `RESULT=success|failure`, `FAILURES=ruff,mypy`).
3. **Automatic documentation sync**
   - Extend the helper to call a `sync_docs.sh` script whenever migration succeeds, copying the root docs into `poetry_migration_docs/`.

### 4.3 Address Git Hygiene
1. **Dedicated branch and periodic rebase**
   - Work on a feature branch (e.g., `uv-migration/wave1`) and rebase daily against `origin/main` to avoid diverging by double digits.
2. **Stash or relocate `.bak` artifacts**
   - Decide on policy: either commit `.poetry.bak` files (if needed) or move them into a separate tracked directory so they no longer appear as repo-wide untracked files.
3. **Batch removal commits**
   - Consolidate the mass `poetry.lock` deletions into intentional commits to reduce noise during subsequent status checks.

### 4.4 Enhance Logging & Observability
1. **Structured log format**
   - Switch `uv_migration_poetry.log` to CSV or JSON lines with columns `repo`, `step`, `status`, `timestamp`, `notes`.
2. **Summary CLI**
   - Provide a small Python script (`scripts/summarise_uv_log.py`) to print per-repo statuses and highlight outstanding failures.

### 4.5 Documentation Workflow Automation
1. **Single source of truth**
   - Move `migratingPoetryReposToUV.md` and `poetry_migration_runbook.md` into the repo (or symlink) to eliminate the copy step. Alternatively, create a `make sync-docs` target that both updates the root copy and stages the mirrored files.
2. **Checksum guardrails**
   - Add a pre-commit hook that compares the root doc with the mirrored doc and fails if they differ.

### 4.6 Testing Strategy Enhancements
1. **Fixtures for dynamic imports**
   - Introduce a reusable pytest fixture (e.g., `import_module(path)`) to centralise importlib logic; keep tests lean.
2. **Time handling utilities**
   - Provide helper functions for timestamp formatting to avoid timezone-specific assertions.

### 4.7 Operational cadence
1. **Daily stand-up log**
   - Append a short section in the runbook capturing daily status, blockers, and next repos. This will make it easier to resume after interruptions.
2. **Chunked tracking**
   - Group Wave 1 repos into smaller batches (3–4) and close them out completely (code + docs + commit) before starting the next, reducing cognitive load.

## 5. Immediate Action Items
| Priority | Action | Owner | Notes |
| --- | --- | --- | --- |
| High | Patch `convert_poetry_to_uv.py` to handle scripts/slugging and pre-populate dev groups | Tooling maintainer | Blocks future migrations with CLI entry points |
| High | Establish branch strategy + cleanup `.bak` policy | Repo maintainer | Prevents future commit churn |
| Medium | Automate doc mirroring via helper script | Ops | Saves ~2–3 minutes per repo and reduces human error |
| Medium | Convert `uv_migration_poetry.log` to structured format | Ops | Enables dashboarding and quick status summaries |
| Low | Create reusable pytest fixtures/utilities | Migration devs | Reduces repetitive code in smoke tests |

## 6. Lessons Learned
- Automation accelerates the easy 80%, but blind spots (scripts section, slugging, dev dependencies) can erase gains. Tools must mature as we encounter edge cases.
- Documentation discipline is paying dividends; however, every manual copy step is a future mistake waiting to happen. Automate before the footprint expands.
- Git hygiene is not optional. The longer we leave mass deletions and divergence unresolved, the harder it becomes to ship distinct pieces of work (like doc updates) independently.
- Tests are essential—even simplistic smoke tests—because they expose business logic gaps (missing dependencies, timezone assumptions) immediately.
- Logging without structure creates toil. Given the number of repos in the queue, we should invest in structured telemetry now to avoid a wall of inscrutable logs later.

## 7. Closing Thoughts
The migration effort is trending in the right direction: we now have a repeatable pattern (helper script + smoke tests + doc sync) and a clearer understanding of the failure modes. The next tranche should focus on strengthening automation, taming the git workspace, and reducing manual doc churn. Executing the recommendations above will shorten iteration cycles, reduce friction for future contributors, and keep the migration momentum alive.
