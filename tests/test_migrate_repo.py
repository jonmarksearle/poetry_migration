"""Unit tests for migrate_repo.py."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterator, TypedDict
import sys

import pytest
import tomlkit
from typer.testing import CliRunner

sys.path.append(str(Path(__file__).resolve().parent.parent))

import migrate_repo as migrate_repo_module

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
    log_info,
    log_warning,
    log_error,
    log_rich,
)


class GitTracking(TypedDict):
    commands: list[list[str]]
    manifest: list[tuple[str, str]]


EXPECTED_CHECK_COMMANDS = [
    [UV_PATH, "run", "ruff", "check", "."],
    [UV_PATH, "run", "mypy", "src/app.py"],
    [UV_PATH, "run", "pytest"],
]

BASE_SYNC_COMMANDS = [
    [UV_PATH, "sync", "--refresh"],
    [UV_PATH, "sync", "--group", "dev"],
]

EXPECTED_GIT_COMMANDS = [
    ["git", "add", "pyproject.toml", ".python-version", "uv.lock"],
    ["git", "commit", "-m", "chore: migrate from poetry to uv\n\nconverted with standard configuration"],
]

EXPECTED_MANIFEST_ENTRY = ("migrated", "converted with standard configuration")

FEATURE_COMMIT_NOTES = "excluded before/ directory; added type stubs: httpx, sqlalchemy; configured async mypy checks; enabled strict mypy mode"


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
def mock_path_resolve(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with monkeypatch.context() as ctx:
        ctx.setattr(Path, "resolve", lambda _: Path("/abs/path/to/pkg"))
        yield


@pytest.fixture
def git_tracking() -> GitTracking:
    return {"commands": [], "manifest": []}


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def console_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, object]]]:
    calls: list[tuple[str, dict[str, object]]] = []

    def record(message: str, **kwargs: object) -> None:
        calls.append((message, kwargs))

    monkeypatch.setattr(migrate_repo_module.console, "print", record)
    return calls


@pytest.fixture
def mock_git(monkeypatch: pytest.MonkeyPatch, git_tracking: GitTracking) -> None:
    def record_cmd(cmd: list[str], *_args, **_kwargs) -> tuple[bool, str]:
        git_tracking["commands"].append(cmd)
        return True, ""

    def record_manifest(_path: Path, status: str, notes: str) -> None:
        git_tracking["manifest"].append((status, notes))

    monkeypatch.setattr("migrate_repo.run_cmd", record_cmd)
    monkeypatch.setattr("migrate_repo.update_manifest", record_manifest)


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
def converted_pyproject(sample_poetry_project: Path, repo_analysis: RepoAnalysis):
    assert convert_pyproject(sample_poetry_project, repo_analysis)
    return tomlkit.loads((sample_poetry_project / "pyproject.toml").read_text())


@pytest.fixture
def run_cmd_env_records(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], Path, dict[str, str] | None]]:
    records: list[tuple[list[str], Path, dict[str, str] | None]] = []

    def record(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[bool, str]:
        records.append((cmd, cwd, env))
        return True, ""

    monkeypatch.setattr("migrate_repo.run_cmd", record)
    monkeypatch.setattr("migrate_repo.get_uv_cache_env", lambda: {"UV_CACHE_DIR": "cache"})
    return records


@pytest.fixture
def removal_tracker(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    removed: list[Path] = []
    monkeypatch.setattr("migrate_repo.remove_path", lambda path: removed.append(path))
    return removed


@pytest.fixture
def already_migrated_repo(monkeypatch: pytest.MonkeyPatch, repo_analysis: RepoAnalysis, tmp_path: Path) -> tuple[Path, dict[str, int]]:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    calls = {"commit": 0}
    monkeypatch.setattr("migrate_repo.analyze_repo", lambda *_: repo_analysis)
    monkeypatch.setattr("migrate_repo.is_already_migrated", lambda *_: True)
    monkeypatch.setattr("migrate_repo.commit_changes", lambda *_: calls.__setitem__("commit", calls["commit"] + 1))
    return tmp_path, calls


def test__validate_version_constraint__with_invalid_version__fail() -> None:
    assert validate_version_constraint(">=bad") is None


@pytest.mark.parametrize(
    ("constraint", "expected"),
    [
        pytest.param("^1.2.3", ">=1.2.3.0, <2.0", id="caret"),
        pytest.param("~2.0", ">=2.0, <3.0", id="tilde"),
        pytest.param(">=3.0.*", ">=3.0, <4.0", id="wildcard"),
    ],
)
def test__validate_version_constraint__with_supported_ranges__success(constraint: str, expected: str) -> None:
    assert validate_version_constraint(constraint) == expected


def test__analyze_repo__with_poetry_project__success(sample_poetry_project: Path) -> None:
    analysis = analyze_repo(sample_poetry_project)
    assert isinstance(analysis, RepoAnalysis)
    assert analysis.python_versions == (">=3.12", "<4.0")


def test__analyze_repo__without_pyproject__fail(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"pyproject.toml"):
        analyze_repo(tmp_path)


def test__extract_python_version__with_version_spec__success(repo_analysis: RepoAnalysis) -> None:
    analysis = replace(repo_analysis, python_versions=(">=3.11",))
    assert extract_python_version(analysis) == "3.11"


def test__format_dependency__with_path_source__success(mock_path_resolve: None, path_dependency: dict[str, object], capsys: pytest.CaptureFixture[str]) -> None:
    result = format_dependency("localpackage", path_dependency, Path("/repo"))
    out = capsys.readouterr().out.strip().splitlines()
    assert result == "localpackage @ file:///abs/path/to/pkg"
    assert out == [
        "Warning: localpackage has develop=true (editable), converting to regular install",
        "Warning: localpackage path dependency uses absolute path, not portable across machines",
    ]


def test__format_dependency__with_simple_version__success() -> None:
    assert format_dependency("requests", "^2.31.0", Path()) == "requests >=2.31.0, <3.0"


def test__format_dependency__with_git_source__success(git_dependency: dict[str, object]) -> None:
    expected = "mypackage[test] @ git+https://github.com/user/repo.git@main"
    assert format_dependency("mypackage", git_dependency, Path()) == expected


def test__configure_tools__with_features_enabled__success(analysis_with_features: RepoAnalysis) -> None:
    result = configure_tools(Path(), analysis_with_features)
    assert result["tool"]["mypy"]["warn_unused_awaits"] and result["tool"]["mypy"]["strict"]
    assert result["tool"]["ruff"]["exclude"] == ["before"]


def test__build_project_section__with_poetry_config__success(sample_poetry_config: dict[str, object], repo_analysis: RepoAnalysis, tmp_path: Path) -> None:
    result = build_project_section(sample_poetry_config, repo_analysis, tmp_path)
    assert result["requires-python"] == ">=3.12.0, <4.0"
    assert result["dependencies"] == ["requests >=2.31.0, <3.0"]


def test__convert_pyproject__without_poetry_config__fail(tmp_path: Path, repo_analysis: RepoAnalysis, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    assert convert_pyproject(tmp_path, repo_analysis) is False
    assert "No Poetry configuration found" in capsys.readouterr().out


def test__convert_pyproject__with_poetry_config__success(converted_pyproject) -> None:
    assert converted_pyproject["project"]["name"] == "test-project"
    assert "dev" in converted_pyproject["dependency-groups"]
    assert "ruff" in converted_pyproject["tool"]


def test__run_checks__with_command_failure__fail(mock_failed_command: None) -> None:
    success, error = run_checks(Path(), ("test.py",))
    assert not success and "Command failed: error details" in error


def test__run_checks__with_python_files__success(mock_checks_success: list[list[str]]) -> None:
    success, error = run_checks(Path("/repo"), ("src/app.py",))
    assert success and error == ""
    assert mock_checks_success == BASE_SYNC_COMMANDS + EXPECTED_CHECK_COMMANDS


def test__run_checks__without_python_files__runs_sync_only__success(mock_checks_success: list[list[str]]) -> None:
    success, error = run_checks(Path("/repo"), ())
    assert success and error == ""
    assert mock_checks_success == BASE_SYNC_COMMANDS


def test__run_checks__with_env_configured__propagates_cache__success(run_cmd_env_records: list[tuple[list[str], Path, dict[str, str] | None]]) -> None:
    success, error = run_checks(Path("/repo"), ())
    _, cwd, env = run_cmd_env_records[0]
    assert success and error == ""
    assert env is not None and env["UV_CACHE_DIR"] == "cache" and cwd == Path("/repo")


def test__commit_changes__with_repo__success(mock_git: None, git_tracking: GitTracking, repo_analysis: RepoAnalysis, tmp_path: Path) -> None:
    commit_changes(tmp_path, repo_analysis)
    assert git_tracking["commands"] == EXPECTED_GIT_COMMANDS
    assert git_tracking["manifest"][0] == EXPECTED_MANIFEST_ENTRY


def test__commit_changes__with_feature_flags__records_notes__success(mock_git: None, git_tracking: GitTracking, analysis_with_features: RepoAnalysis, tmp_path: Path) -> None:
    commit_changes(tmp_path, analysis_with_features)
    assert git_tracking["commands"][1][3].endswith(FEATURE_COMMIT_NOTES)
    assert git_tracking["manifest"][0] == ("migrated", FEATURE_COMMIT_NOTES)


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
    assert (tmp_path / ".python-version").read_text().strip() == "3.12"
    assert mock_successful_migration["commit"] == 1


def test__migrate_repo__with_valid_repo_removes_poetry_artefacts__success(mock_successful_migration: dict[str, int], removal_tracker: list[Path], tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n")
    (tmp_path / "poetry.lock").write_text("")
    (tmp_path / ".venv").mkdir()
    assert migrate_repo(str(tmp_path)) == ExitCode.SUCCESS
    assert {path.name for path in removal_tracker} == {"poetry.lock", ".venv"}


def test__migrate_repo__with_already_migrated_repo__success(already_migrated_repo: tuple[Path, dict[str, int]]) -> None:
    repo_path, calls = already_migrated_repo
    assert migrate_repo(str(repo_path)) == ExitCode.SUCCESS
    assert calls["commit"] == 0


def test__cli__with_missing_args__fail(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(migrate_repo_module.app, [])
    assert result.exit_code == 2


def test__cli__with_repo__success(monkeypatch: pytest.MonkeyPatch, cli_runner: CliRunner) -> None:
    monkeypatch.setattr("migrate_repo.migrate_repo", lambda path: ExitCode.SUCCESS)
    result = cli_runner.invoke(migrate_repo_module.app, ["/repo"])
    assert result.exit_code == 0
def test__log_info__prints_cyan__success(console_spy: list[tuple[str, dict[str, object]]]) -> None:
    log_info("hello")
    assert console_spy == [("hello", {"style": "cyan"})]


def test__log_warning__prints_yellow__success(console_spy: list[tuple[str, dict[str, object]]]) -> None:
    log_warning("warn")
    assert console_spy == [("warn", {"style": "yellow"})]


def test__log_error__prints_red__success(console_spy: list[tuple[str, dict[str, object]]]) -> None:
    log_error("boom")
    assert console_spy == [("boom", {"style": "red"})]


def test__log_rich__prints_markup__success(console_spy: list[tuple[str, dict[str, object]]]) -> None:
    log_rich("[bold]hi[/bold]")
    assert console_spy == [("[bold]hi[/bold]", {"markup": True})]
