# Poetry Migration Runbook

This runbook captures in-flight progress for migrating Poetry-based repositories to uv. Strategic context and the overall migration plan remain in `poetry_migration_strategy.md`.

## 1. Status Dashboard (updated 2025-10-30)

| Repository | Migration Date | Status | Notes |
| --- | --- | --- | --- |
| 2023/apitesting | 2025-10-30 | ✅ | Added httpx to dev deps; refactored db_update_item |
| 2023/funclass | 2025-10-30 | ✅ | Added Counter typing; smoke test keeps pytest happy |
| 2023/shellroast/after | 2025-10-30 | ✅ | Typed algorithm registry, added path-aware conftest |
| 2024/clean_code/after | 2025-10-30 | ✅ | Added python-dotenv + dev tooling |
| 2024/clean_code/before | 2025-10-30 | ✅ | Added dev tool deps, stubbed invoices import |
| 2024/func | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/func_design | 2025-10-30 | ✅ | Pinned 3.12, added dev tooling and generics coverage |
| 2024/funky/1_oo | 2025-10-30 | ✅ | Added deptry to dev dependencies |
| 2024/funky/2_functional | 2025-10-30 | ✅ | Added deptry to dev dependencies |
| 2024/funky/3_functional | 2025-10-30 | ✅ | Added deptry to dev dependencies |
| 2024/funky/4_functional | 2025-10-30 | ✅ | Added deptry to dev dependencies |
| 2024/gil | 2025-10-30 | ✅ | Converted to uv with dev tooling |
| 2024/pydantic_refresh | 2025-10-30 | ✅ | Mypy errors in example files are expected |
| 2024/python15 | 2025-10-30 | ✅ | Added types-requests for mypy |
| 2024/python_cli/notes | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/custom_exceptions | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/dependency_injection | 2025-10-30 | ✅ | Excluded before/ from mypy checks |
| 2024/tuesday_tips/fail_fast | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/fastapi_custom_exceptions | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/generics | 2025-10-30 | ✅ | Fixed duplicate pytest entry |
| 2024/tuesday_tips/invariant | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/jinja2 | 2025-10-30 | ✅ | Fixed duplicate pytest entry |
| 2024/tuesday_tips/openai | 2025-10-30 | ✅ | Fixed version constraints |
| 2024/tuesday_tips/poetry_tips | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2024/tuesday_tips/regex | 2025-10-30 | ✅ | Fixed version constraints |
| 2024/tuesday_tips/storing_credentials | 2025-10-30 | ✅ | Fixed version constraints |
| 2024/tuesday_tips/testing_async | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/gitbranch | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/sdk | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/simple | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/simple-pytest | 2025-10-30 | ✅ | Converted with standard dev tooling |

## 2. Migration Process

The migration is handled by the `migrate_repo_v2.py` script:

```bash
cd /home/jon/Work/poetry_migration
python migrate_repo_v2.py /path/to/repo
```

The script will:
1. Analyze repository:
   - Find duplicate dependencies
   - Validate version constraints
   - Check for module conflicts
   - Identify missing type stubs
   - Detect async code and type annotations
2. Configure tools based on analysis:
   - mypy settings for async/typed code
   - ruff settings for line length/excludes
   - Add missing type stubs
3. Convert pyproject.toml:
   - Preserve Python version
   - Normalize version constraints
   - Keep existing dev dependencies
   - Add standard dev tools
4. Run checks and commit changes

## 3. Common Issues & Solutions

1. **Duplicate Dependencies**
   - Issue: Same package in multiple dependency groups
   - Solution: Auto-detected and deduplicated

2. **Invalid Version Constraints**
   - Issue: Post-release versions, malformed constraints
   - Solution: Normalized to PEP 440 format

3. **Module Conflicts**
   - Issue: Same module name in before/after dirs
   - Solution: Auto-configured tool exclusions

4. **Missing Type Stubs**
   - Issue: Imports without type stubs
   - Solution: Auto-detected and added to dev deps

5. **Tool Configuration**
   - Issue: Generic tool settings
   - Solution: Configured based on code analysis

## 4. Commit Protocol

The script handles commits automatically:
1. Stages pyproject.toml, .python-version, uv.lock
2. Generates commit message with analysis details
3. Updates manifest with migration status

## 5. Edge Cases

1. **Before/After Examples**
   - Auto-detected through module conflict analysis
   - Tool configurations added automatically

2. **Multiple Python Versions**
   - Preserved from original pyproject.toml
   - Creates matching .python-version file

3. **Custom Dev Tools**
   - Preserved during migration
   - Standard tools added if missing

4. **Async Code**
   - Detected through AST analysis
   - mypy configured appropriately

5. **Type Annotations**
   - Usage detected automatically
   - Strict mypy mode enabled when found

## 6. Read-Up Before You Start
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal: <https://peps.python.org/pep-0735/>
- Deptry documentation: <https://github.com/fpgmaas/deptry>

## 7. Change Log
- **2025-10-30** – Added pre-migration analysis
- **2025-10-30** – Added smart tool configuration
- **2025-10-30** – Added dependency normalization
- **2025-10-30** – Added type stub detection
- **2025-10-30** – Added async code detection
- **2025-10-30** – Updated status dashboard

---
*Last updated: 2025-10-30*
