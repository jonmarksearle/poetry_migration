# CODE_STANDARDS

This file is the single source of truth for coding standards for all projects under `~/Work`. All project `CODE_STANDARDS.md` files should be symlinks to this file.

## Tooling and Versions

- Python 3.13; follow PEP 8.
- Use `ruff` for linting and formatting (run via `uvx ruff`).
- Use `mypy` for type checking (run via `uvx mypy ...`).
- Use `pytest` for testing (run via `uvx pytest`).
- Add `from __future__ import annotations` to new modules.
- Prefer Python 3.13 typing features when they clarify intent (PEP 695 generics, `typing.TypeAliasType`, `typing.override`, `typing.final`).

## Language and Naming

- Use Australian English in docs, comments, logs, tests, and identifiers where appropriate (e.g., behaviour, colour).
- Favour meaningful names over explanatory comments.

## Program Structure

- Keep code minimal, readable, and testable.
- Use meaningful names over comments.
- Functions are small (<10 lines), prefer early returns, avoid nesting (Never Nester).
- Break up nested loops or conditionals into helper functions.
- Order functions top‑down in call order. A function appears before the first function that calls it.
- Group a function’s helper functions immediately above that function.
- Use one‑line docstrings for all non‑helper functions; for helper functions use one‑line docstrings only when behaviour is non‑obvious or the helper exceeds 5 lines.
- Each function has a single responsibility. Do either business logic or exception management, never both—use helpers to separate concerns.
- Prefer list/dict/set comprehensions over loops because they result in clearer, more functional code; use helper functions in comprehensions where nessasary. Avoid `.append()` / `.extend()` in new code unless there is no other reasonable alternative and the user agrees explicitly.
- Prefer generators over comprehensions where posible because it results in clearer, more functional, and more performant code.
- When accumulating values, prefer functional patterns (generators, comprehensions, `tuple(...)`, `itertools`) over in-place mutation of lists.
- Prefer tuples over lists where possible because they are immutable and faster.

## Side Effects and Errors

- Prefer pure functions; avoid mutation; introduce mutation only when it is vital for clarity.
- Keep side effects (I/O, logging, DB access) out of core logic; isolate side‑effectful code.
- Isolate exception handling in dedicated helpers; prefer pass‑through otherwise.
- Favour inline imports; use constructor injection to improve flexibility without harming clarity.
- define and use decorators when it makes the code clearer.
- define and use context managers when ever posible.
- only allow one line in a try/except block; create helper functions.
- only allow one or none try/except block per function.
- only use try/except blocks when you absolutly need to handel the exception, or it is vital to add more contextual information to the exception for debugging.

## Types and Interfaces

- Use precise type hints; avoid `Any` unless unavoidable.
- Use `typing.Protocol` for interfaces.
- Use `@dataclass(frozen=True)` or `namedtuple` for immutability.
- Use `typing.TypedDict` for simple structured dictionaries.
- Use `typing.Protocol` for interfaces; prefer `@dataclass(frozen=True)`, `enum.StrEnum`, and immutable collections (`tuple`, `collections.abc.Sequence`) for fixed data.

## Async and Concurrency

- Use `async`/`await` only when concurrency is required.
- In asyncio code, prefer `asyncio.TaskGroup` for parallel tasks.
- When asyncio is unsuitable, use threads/`concurrent.futures`.

## Standard Library First

- Prefer modern stdlib utilities (e.g., `itertools`, `math`, `pathlib`, etc.) over ad‑hoc implementations.

## TDD Quality Gate

- Practice strict TDD using the organisation terminology: GREEN -> RED -> GREEN -> REFACTOR.
  1. GREEN baseline: all tests pass and code is clean enough to change.
  2. RED: write a new test that fails to define desired behaviour.
  3. GREEN: implement the minimal code to make the new test pass, keeping all tests green.
  4. REFACTOR: improve design and readability while tests stay green.
- Only write code required to make failing tests pass.
- Every committed Python module must be covered by tests. If a new `.py` file lacks tests, add tests that cover its full behaviour.
- At every state transition run: `uvx ruff format`, `uvx ruff check`, `uvx mypy …`, `uvx pytest`.

## TTD Roles

  a. **Analyst** Interviews the user and writes the feature requirements, specifications, and test case outlins / bdd documents;
  b. **Test Author** writes focused pytest cases and fixtures; 
  c. **Test Reviewer** ensures adherence to standards and completeness;
  d. **Code Author** implements the code based on a single failing test;
  e. **Code Reviewer** ensures adherence to standards and completeness;
  f. **Refactorer** refactors the code to improve design and readability while tests stay green.

  Each feature is implemented in sequence: a -> b -> c -> d -> e -> f -> a

## Pytest Conventions

- Test behaviour, not implementation details.
- Naming: `test__{function}__{case}__{success|fail}` with failure tests listed first.
- Use raw strings in `pytest.raises(..., match=r"…")` when asserting error text.
- Separate success and failure tests; failure tests first.
- Use fixtures and `@pytest.mark.parametrize`; avoid loops/conditionals in tests.

## Writing Tests

- Coverage: Treat tests as the authoritative spec. Enumerate behaviours before coding; mirror every happy path with a corresponding fail test using `pytest.raises(..., match=r"…")`, and add explicit edge‑case tests.
- Size and focus: Keep each test function very small (≈ ≤5 executable lines); move setup into fixtures/parametrisation.
- Side effects: Assert side‑effects on success paths where relevant (files written, subprocess calls, logs). Use temporary paths and mocks; isolate from network, git, and real filesystem writes.
- Tools and gates: Target Python 3.13 with modern typing. Maintain GREEN -> RED -> GREEN -> REFACTOR cadence; run `uvx ruff format`, `uvx ruff check --fix`, `uvx ruff check`, `uvx mypy …`, and `uvx pytest` at each transition.

## Mocking and Dependency Injection

- Mock only at external boundaries (e.g., AWS, DB) when it is the clearest option.
- Use dependency injection to improve clarity.
- Avoid mocking internals unless no clearer option exists.
- Prefer `unittest.mock` for mocking.
