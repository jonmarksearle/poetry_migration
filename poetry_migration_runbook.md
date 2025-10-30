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
| 2025/gitbranch | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/sdk | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/simple | 2025-10-30 | ✅ | Converted with standard dev tooling |
| 2025/simple-pytest | 2025-10-30 | ✅ | Converted with standard dev tooling |

## 2. Migration Process

The migration is handled by the `migrate_repo.py` script:

```bash
cd /home/jon/Work/poetry_migration
python migrate_repo.py /path/to/repo
```

The script will:
1. Check if repository is already migrated
2. Convert pyproject.toml to PEP621 format
3. Add standard dev tooling
4. Run dependency audit and code checks
5. Commit changes and update manifest

## 3. Common Issues & Solutions

1. **Duplicate Module Names**
   - Issue: mypy errors with "Duplicate module named X"
   - Solution: Script excludes before/ directory from mypy checks

2. **Missing Type Stubs**
   - Issue: mypy errors about missing stubs
   - Solution: Add required type stubs to dev dependencies

3. **Flat Directory Layout**
   - Issue: mypy can't find .py files
   - Solution: Script explicitly lists Python files for mypy

## 4. Commit Protocol

The script handles commits automatically:
1. Stages pyproject.toml, .python-version, uv.lock
2. Uses standard commit message: "chore: migrate from poetry to uv"
3. Updates manifest with migration status

## 5. Edge Cases

1. **Before/After Examples**
   - Exclude before/ directory from mypy
   - Only check after/ directory for type hints

2. **Multiple Python Versions**
   - Default to Python 3.12
   - Preserve original version constraints

3. **Custom Dev Tools**
   - Add standard tools (pytest, ruff, mypy, deptry)
   - Preserve existing dev dependencies

## 6. Read-Up Before You Start
- UV project documentation: <https://docs.astral.sh/uv/>
- PEP 621 – Project metadata: <https://peps.python.org/pep-0621/>
- PEP 735 – Dependency groups proposal: <https://peps.python.org/pep-0735/>
- Deptry documentation: <https://github.com/fpgmaas/deptry>

## 7. Change Log
- **2025-10-30** – Switched to automated migration using migrate_repo.py script
- **2025-10-30** – Updated status dashboard with all migrated repositories

---
*Last updated: 2025-10-30*
