"""Unit tests for migrate_repo.py."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))

from migrate_repo import (
    UV_PATH,
    RepoAnalysis,
    ExitCode,
    analyze_repo,
    validate_version_constraint,
    extract_python_version,
    format_dependency,
    configure_tools,
    build_project_section,
    convert_pyproject,
    run_checks,
    commit_changes,
    migrate_repo,
)


EXPECTED_CHECK_COMMANDS = [
    [UV_PATH, "run", "ruff", "check", "."],
    [UV_PATH, "run", "mypy", "src/app.py"],
    [UV_PATH, "run", "pytest"],
]

EXPECTED_GIT_COMMANDS = [
    ["git", "add", "pyproject.toml", ".python-version", "uv.lock"],
    ["git", "commit", "-m", "chore: migrate from poetry to uv\n\nconverted with standard configuration"],
]

EXPECTED_MANIFEST_ENTRY = ("migrated", "converted with standard configuration")


@pytest.fixture
def sample_poetry_project(tmp_path: Path) -> Path:
    project = tmp_path / "pyproject.toml"
    project.write_text(
        """
[tool.poetry]
name = "test-project"
version = "0.1.0"
[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.31.0"
""".strip()
    )
    return tmp_path


@pytest.fixture
def sample_poetry_config() -> dict[str, object]:
    return {
        "name": "test-project",
        "version": "0.1.0",
        "dependencies": {"python": "^3.12", "requests": "^2.31.0"},
    }


@pytest.fixture
def repo_analysis() -> RepoAnalysis:
    return RepoAnalysis(
        duplicate_deps=frozenset(),
        invalid_versions=(),
        module_conflicts=(),
        missing_stubs=(),
        has_async=False,
        has_type_annotations=False,
        has_long_lines=False,
        python_versions=(">=3.12",),
    )


@pytest.fixture
def analysis_with_features(repo_analysis: RepoAnalysis) -> RepoAnalysis:
    return replace(
        repo_analysis,
        has_async=True,
        has_type_annotations=True,
        module_conflicts=(("test", "before/test.py"),),
        missing_stubs=("httpx", "sqlalchemy"),
    )


@pytest.fixture
def git_dependency() -> dict[str, object]:
    return {
        "git": "https://github.com/user/repo.git",
        "rev": "main",
        "extras": ["test"],
    }


@pytest.fixture
def path_dependency() -> dict[str, object]:
    return {"path": "../pkg", "develop": True}


@pytest.fixture
def mock_path_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as ctx:
        ctx.setattr(Path, "resolve", lambda _: Path("/abs/path/to/pkg"))
        yield


@pytest.fixture
def git_tracking() -> dict[str, list[object]]:
    return {"commands": [], "manifest": []}


@pytest.fixture
def mock_git(monkeypatch: pytest.MonkeyPatch, git_tracking: dict[str, list[object]]) -> None:
    monkeypatch.setattr(
        "migrate_repo.run_cmd",
        lambda cmd, *_args, **_kwargs: git_tracking["commands"].append(cmd) or (True, ""),
    )
    monkeypatch.setattr(
        "migrate_repo.update_manifest",
        lambda path, status, notes: git_tracking["manifest"].append((status, notes)),
    )


@pytest.fixture
def mock_failed_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "migrate_repo.run_cmd",
        lambda *_args, **_kwargs: (False, "Command failed: error details"),
    )


@pytest.fixture
def mock_successful_migration(
    monkeypatch: pytest.MonkeyPatch, repo_analysis: RepoAnalysis
) -> dict[str, int]:
    calls = {"commit": 0}
    monkeypatch.setattr("migrate_repo.analyze_repo", lambda *_: repo_analysis)
    monkeypatch.setattr("migrate_repo.convert_pyproject", lambda *_: True)
    monkeypatch.setattr("migrate_repo.run_checks", lambda *_: (True, ""))
    monkeypatch.setattr("migrate_repo.commit_changes", lambda *_: calls.__setitem__("commit", calls["commit"] + 1))
    return calls


@pytest.fixture
def mock_checks_success(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    commands: list[list[str]] = []

    def record(cmd: list[str], *_args, **_kwargs) -> tuple[bool, str]:
        commands.append(cmd)
        return True, ""

    monkeypatch.setattr("migrate_repo.run_cmd", record)
    monkeypatch.setattr("migrate_repo.get_uv_cache_env", lambda: {"UV_CACHE_DIR": "cache"})
    return commands


@pytest.fixture
def toml_writer_spy(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    written: dict[str, object] = {}
    monkeypatch.setattr("migrate_repo.write_toml", lambda path, doc: written.update({"path": path, "doc": doc}))
    return written


def test__validate_version_constraint__with_invalid_version__fail() -> None:
    assert validate_version_constraint(">=bad") is None


@pytest.mark.parametrize(
    ("constraint", "expected"),
    [
        ("^1.2.3", ">=1.2.3.0, <2.0"),
        ("~2.0", ">=2.0, <3.0"),
        (">=3.0.*", ">=3.0, <4.0"),
    ],
)
def test__validate_version_constraint__with_supported_ranges__success(constraint: str, expected: str) -> None:
    assert validate_version_constraint(constraint) == expected


def test__analyze_repo__with_poetry_project__success(sample_poetry_project: Path) -> None:
    analysis = analyze_repo(sample_poetry_project)
    assert isinstance(analysis, RepoAnalysis)
    assert analysis.python_versions == (">=3.12", "<4.0")


def test__extract_python_version__with_version_spec__success(repo_analysis: RepoAnalysis) -> None:
    analysis = replace(repo_analysis, python_versions=(">=3.11",))
    assert extract_python_version(analysis) == "3.11"


def test__format_dependency__with_path_source__success(mock_path_resolve: None, path_dependency: dict[str, object], capsys: pytest.CaptureFixture[str]) -> None:
    result = format_dependency("localpackage", path_dependency, Path("/repo"))
    out = capsys.readouterr().out
    assert result == "localpackage @ file:///abs/path/to/pkg"
    assert "develop=true" in out and "absolute path" in out


def test__format_dependency__with_simple_version__success() -> None:
    assert format_dependency("requests", "^2.31.0", Path()) == "requests >=2.31.0, <3.0"


def test__format_dependency__with_git_source__success(git_dependency: dict[str, object]) -> None:
    expected = "mypackage[test] @ git+https://github.com/user/repo.git@main"
    assert format_dependency("mypackage", git_dependency, Path()) == expected


def test__configure_tools__with_features_enabled__success(analysis_with_features: RepoAnalysis) -> None:
    result = configure_tools(Path(), analysis_with_features)
    assert result["tool"]["mypy"]["warn_unused_awaits"] and result["tool"]["mypy"]["strict"]


def test__build_project_section__with_poetry_config__success(sample_poetry_config: dict[str, object], repo_analysis: RepoAnalysis, tmp_path: Path) -> None:
    result = build_project_section(sample_poetry_config, repo_analysis, tmp_path)
    assert result["requires-python"] == ">=3.12.0, <4.0"


def test__convert_pyproject__without_poetry_config__fail(tmp_path: Path, repo_analysis: RepoAnalysis) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    assert convert_pyproject(tmp_path, repo_analysis) is False


def test__convert_pyproject__with_poetry_config__success(monkeypatch: pytest.MonkeyPatch, sample_poetry_project: Path, repo_analysis: RepoAnalysis, toml_writer_spy: dict[str, object]) -> None:
    sentinel = {"project": {"name": "test"}}
    monkeypatch.setattr("migrate_repo.build_new_pyproject", lambda *_: sentinel)
    assert convert_pyproject(sample_poetry_project, repo_analysis)
    assert toml_writer_spy == {"path": sample_poetry_project / "pyproject.toml", "doc": sentinel}


def test__run_checks__with_command_failure__fail(mock_failed_command: None) -> None:
    success, error = run_checks(Path(), ("test.py",))
    assert not success and "Command failed: error details" in error


def test__run_checks__with_python_files__success(mock_checks_success: list[list[str]]) -> None:
    success, error = run_checks(Path("/repo"), ("src/app.py",))
    assert success and error == ""
    assert mock_checks_success[-3:] == EXPECTED_CHECK_COMMANDS


def test__commit_changes__with_repo__success(mock_git: None, git_tracking: dict[str, list[object]], repo_analysis: RepoAnalysis, tmp_path: Path) -> None:
    commit_changes(tmp_path, repo_analysis)
    assert git_tracking["commands"] == EXPECTED_GIT_COMMANDS
    assert git_tracking["manifest"][0] == EXPECTED_MANIFEST_ENTRY


def test__migrate_repo__with_missing_path__fail() -> None:
    assert migrate_repo("/nonexistent/path") == ExitCode.FAILURE


def test__migrate_repo__with_conversion_failure__fail(monkeypatch: pytest.MonkeyPatch, repo_analysis: RepoAnalysis, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    monkeypatch.setattr("migrate_repo.analyze_repo", lambda *_: repo_analysis)
    monkeypatch.setattr("migrate_repo.convert_pyproject", lambda *_: False)
    assert migrate_repo(str(tmp_path)) == ExitCode.FAILURE


def test__migrate_repo__with_valid_repo__success(mock_successful_migration: dict[str, int], tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    assert migrate_repo(str(tmp_path)) == ExitCode.SUCCESS
    assert mock_successful_migration["commit"] == 1
