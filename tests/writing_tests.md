# Writing Tests Notes

## Roles
- **Test Author** — primary test author crafting fixtures and pytest cases, responsible for aligning with the agreed minimalist-yet-complete test plan.
- **Test Reviewer** — reviewer ensuring adherence to coding standards, pytest conventions, and completeness; flags missing coverage or style violations before implementation proceeds.

## Context Sources to Read
- `README.md`, `poetry_migration_strategy.md`, and `poetry_migration_runbook.md` for migration goals, current status (as of 2025-10-30), and process details.
- `migrate_repo.py` for script behaviour: analysis, conversion, check execution, git commits, manifest updates. Pay attention to helper ordering, environment handling, and subprocess boundaries.
- `poetry_to_uv_manifest.yaml` to confirm repository status expectations against the runbook when updating tests or behaviour.
- `CODE_STANDARDS.md` plus the Python coding/testing standards supplied in-session (PEP 8, Python 3.13 typing, ≤5 line test functions, naming conventions, mocking rules).
- Current `tests/test_migrate_repo.py` to understand outstanding review feedback (warning assertions, commit command verification, ensuring `commit_changes` invocation, add convert_pyproject failure path test, run_checks success path).

## Functional Coverage Expectations
- Tests are to be Authoritative.
- Re-list the concrete behaviours before coding: analysis pipeline (`analyze_repo`), version validation, dependency formatting branches (simple/git/path), tool configuration toggles, project section build, conversion success/failure, cleanup of Poetry artefacts, run-check orchestration, commit/manifest updates, and CLI entrypoint flow.
- Mirror every happy path with matching `_fail` tests that assert the precise exception the function should raise. Use `pytest.raises(..., match=r"...")` for those cases; reserve non-exception assertions for success tests only.
- Mirror each happy path with explicit edge-path tests: e.g. `validate_version_constraint` returning `None`, `convert_pyproject` returning `False`, `run_checks` propagating failure, `migrate_repo` exiting early on missing repos or failed conversion.
- Exercise edge cases around module conflicts, async/type flags, and dependency stubs to prove tool configuration logic toggles the right options and notes.
- Assert warnings, returned tuples, and status codes precisely in success tests; failures must verify exceptions, not fallback values.
- Cover side-effect expectations on the happy path: rewritten `pyproject.toml` content via `tomlkit.loads`, `.python-version` creation, `git add`/`git commit` invocations, manifest updates, and that `commit_changes` is called from the orchestration path.

## Key Instructions & Concerns
- Target Python 3.13; add `from __future__ import annotations` to new modules, prefer modern typing features.
- Every test function must remain ≤5 lines (fixtures + asserts; move setup into fixtures/parametrization).
- Test naming format: `test__{function}__{case}__{success|fail}`, with failure cases defined before success cases.
- Keep tests function to 5 lines or less as a discipline to ensure testing exactly one thing and the use of `fixtures` and `pytest.mark.parametrize`.
- Use `fixtures` to share setup code; test functions to assert the precise exception the function should exibit.
- Use `pytest.mark.parametrize` for value permutations; avoid loops/conditionals inside tests
- Validate warnings for path dependencies (both `develop=true` and absolute path messages).
- Ensure `commit_changes` test asserts both `git add` and `git commit` invocations and manifest updates.
- Confirm `migrate_repo` happy path checks that `commit_changes` is invoked; add coverage for migration failure when `convert_pyproject` returns `False` and for `run_checks` success propagation.
- Maintain isolation from external side effects: mock subprocess, git, and filesystem writes beyond temp directories.
- Remember to run `uv run ruff check`, `uv run mypy …`, and `uv run pytest` once implementation resumes.

Keep this file updated as responsibilities or outstanding review items change, so the next session can pick up without re-reading every artifact.
