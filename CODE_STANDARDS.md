### Python Coding Standards

- Target: Python 3.13. Follow PEP 8. Use `ruff` for linting and formatting (via `uv run`); `Pylance` is optional and not preferred.
- Keep code minimal, readable, and testable.
- Add `from __future__ import annotations` to new modules and prefer Python 3.13 typing features (PEP 695 generics, `typing.TypeAliasType`, `typing.override`, `typing.final`) where they clarify intent.
- Language: Australian English spelling across docs, comments, log/test messages, and identifiers where appropriate (e.g., behaviour, colour).
- Prefer `@dataclass(frozen=True)`, `enum.StrEnum`, or typed immutable collections (`tuple`, `collections.abc.Sequence`) for fixed data.
- Functions: ≤10 lines, prefer early returns, avoid nesting ("Never Nester").
- Only use multi-line docstrings for API functions where logic or parameters are not obvious.
- A function must appear before the first function that calls it.
- Order functions by the order they are called in the main execution flow (top-down).
- All helper functions used by a function must appear as a group immediately before that function.
- Use list/dict comprehensions over loops, unless less readable.
- Use meaningful names over comments.
- Use 1-line docstrings for helper functions only when behaviour is non-obvious.
- Use 1-line docstrings for all non-helper functions, and helper functions > 5 lines.
- Use precise type hints. Avoid `Any` unless unavoidable.
- Use `typing.Protocol` for interfaces.
- Functions must follow the Single Responsibility Principle: perform exactly one concern. A function handles business logic or exception management, never both. Split work into helpers when needed.
- Prefer pattern matching (`match`/`case`) when it simplifies branching; keep cases small and pure.
- Prefer pure functions. Use mutable state only if clearer.
- Keep side effects (I/O, logging, DB access) out of core logic functions.
- Isolate side effects from logic.
- Isolate exception handling into separate functions. Prefer pass-through.
- Inline imports by default; constructor injection only if it improves flexibility without degrading clarity.
- Async/await only used when required for concurrency; if using asyncio in 3.13, prefer `asyncio.TaskGroup` for parallel tasks. Use threading and `concurrent.futures` when asyncio is not suitable.
- Use stdlib helpers introduced in 3.13 (`itertools.batched`, `math.nextafter`, `pathlib.Path.walk`, etc.) instead of ad-hoc implementations when appropriate.

### TDD and Testing Rules

- Strict TDD: test-first → make fail → pass test → all pass → refactor → repeat.
- Only write code to make failing tests pass.
- Code must be covered by tests.
- Run the quality gate with `uv run ruff check`, `uv run mypy …`, `uv run pytest` at every state transition.

### Pytest Conventions

- Test behaviour, not implementation.
- Test naming: `test__{function}__{case}__{success|fail}` with failure tests listed first.
- Use raw strings in `pytest.raises(..., match=r"…")` for clarity when asserting error text.
- Separate success vs failure tests; failure tests first.
- Use fixtures and `@pytest.mark.parametrize`; no loops/conditionals in tests.

### Mocking & DI

- Mock only at external boundaries (e.g. AWS, DB) if simple and clear.
- Use DI only when it improves clarity.
- Avoid mocking internals unless no clearer option exists.
- Prefer `unittest.mock` for mocking.
