"""Unit tests for migrate_repo.py."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import tomlkit

from migrate_repo import (
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


@pytest.fixture
def sample_poetry_project(tmp_path):
    """Create minimal Poetry project structure."""
    (tmp_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "test-project"
version = "0.1.0"
[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.31.0"
""")
    return tmp_path


@pytest.fixture
def sample_poetry_config():
    """Minimal Poetry configuration dict."""
    return {
        "name": "test-project",
        "version": "0.1.0",
        "dependencies": {
            "python": "^3.12",
            "requests": "^2.31.0"
        }
    }


@pytest.fixture
def repo_analysis():
    """Base RepoAnalysis instance for testing."""
    return RepoAnalysis(
        duplicate_deps=frozenset(),
        invalid_versions=(),
        module_conflicts=(),
        missing_stubs=(),
        has_async=False,
        has_type_annotations=False,
        has_long_lines=False,
        python_versions=(">=3.12",)
    )


@pytest.fixture
def git_tracking():
    """Track git commands and manifest updates."""
    return {"commands": [], "manifest": []}


@pytest.fixture
def mock_git(monkeypatch, git_tracking):
    """Setup git command mocking."""
    monkeypatch.setattr(
        "migrate_repo.run_cmd",
        lambda cmd, *args: git_tracking["commands"].append(cmd) or (True, "")
    )
    monkeypatch.setattr(
        "migrate_repo.update_manifest",
        lambda path, status, notes: git_tracking["manifest"].append((status, notes))
    )


@pytest.fixture
def analysis_with_features(repo_analysis):
    """RepoAnalysis with all features enabled."""
    return replace(repo_analysis,
        has_async=True,
        has_type_annotations=True,
        module_conflicts=(("test", "before/test.py"),))


@pytest.fixture
def git_dependency():
    """Sample git dependency config."""
    return {
        "git": "https://github.com/user/repo.git",
        "rev": "main",
        "extras": ["test"]
    }


@pytest.fixture
def path_dependency():
    """Sample path dependency config."""
    return {"path": "../pkg", "develop": True}


@pytest.fixture
def mock_path_resolve(monkeypatch):
    """Mock Path.resolve."""
    with monkeypatch.context() as m:
        m.setattr(Path, "resolve", lambda _: Path("/abs/path/to/pkg"))
        yield


def test__analyze_repo__with_poetry_project__success(sample_poetry_project):
    """Test analyzing Poetry project returns correct RepoAnalysis."""
    analysis = analyze_repo(sample_poetry_project)
    assert isinstance(analysis, RepoAnalysis)
    assert analysis.python_versions == (">=3.12",)


@pytest.mark.parametrize("constraint,expected", [
    ("^1.2.3", ">=1.2.3, <2.0"),
    ("~2.0", ">=2.0.0, <3.0"),
    (">=3.0.*", ">=3.0.0, <4.0"),
    (">=bad", None)
])
def test__validate_version_constraint__with_various_inputs__matches_expected(constraint, expected):
    """Test version constraint validation."""
    assert validate_version_constraint(constraint) == expected


def test__extract_python_version__with_version_spec__returns_major_minor(repo_analysis):
    """Test Python version extraction from version spec."""
    analysis = replace(repo_analysis, python_versions=(">=3.11",))
    assert extract_python_version(analysis) == "3.11"


def test__format_dependency__with_simple_version__formats_correctly():
    """Test simple dependency string formatting."""
    assert format_dependency("requests", "^2.31.0", Path()) == "requests >=2.31.0, <3.0"


def test__format_dependency__with_git_source__formats_correctly(git_dependency):
    """Test git dependency formatting."""
    expected = "mypackage[test] @ git+https://github.com/user/repo.git@main"
    assert format_dependency("mypackage", git_dependency, Path()) == expected


def test__format_dependency__with_path_source__formats_and_warns(mock_path_resolve, path_dependency, capfd):
    """Test path dependency formatting and warning capture."""
    result = format_dependency("localpackage", path_dependency, Path("/repo"))
    assert result == "localpackage @ file:///abs/path/to/pkg"
    assert "Warning: localpackage has develop=true" in capfd.readouterr().out


def test__configure_tools__with_features_enabled__sets_correct_config(analysis_with_features):
    """Test tool configuration with features enabled."""
    result = configure_tools(Path(), analysis_with_features)
    assert result["tool"]["mypy"]["warn_unused_awaits"] is True
    assert result["tool"]["mypy"]["strict"] is True


def test__build_project_section__with_poetry_config__generates_correct_structure(sample_poetry_config, repo_analysis, tmp_path):
    """Test project section generation from Poetry config."""
    result = build_project_section(sample_poetry_config, repo_analysis, tmp_path)
    assert result["requires-python"] == ">=3.12, <4.0"


def test__convert_pyproject__without_poetry_config__fail(tmp_path):
    """Test conversion fails without Poetry config."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    assert convert_pyproject(tmp_path, repo_analysis()) is False


def test__convert_pyproject__with_poetry_config__success(monkeypatch, sample_poetry_project):
    """Test successful pyproject.toml conversion."""
    sentinel = {"project": {"name": "test"}}
    monkeypatch.setattr("migrate_repo.build_new_pyproject", lambda *args: sentinel)
    assert convert_pyproject(sample_poetry_project, repo_analysis()) is True
    assert tomlkit.loads((sample_poetry_project / "pyproject.toml").read_text()) == sentinel


@pytest.fixture
def mock_failed_command(monkeypatch):
    """Mock failed command execution."""
    monkeypatch.setattr(
        "migrate_repo.run_cmd",
        lambda *args, **kwargs: (False, "Command failed: error details")
    )


def test__run_checks__with_command_failure__propagates_error(mock_failed_command):
    """Test check failure propagation."""
    success, error = run_checks(Path(), ("test.py",))
    assert not success
    assert "Command failed: error details" in error


def test__commit_changes__with_repo__calls_git_and_updates_manifest(mock_git, git_tracking, repo_analysis, tmp_path):
    """Test git commands and manifest updates."""
    commit_changes(tmp_path, repo_analysis)
    assert ["git", "add", "pyproject.toml", ".python-version", "uv.lock"] in git_tracking["commands"]
    assert git_tracking["manifest"][0][0] == "migrated"


def test__migrate_repo__with_missing_path__returns_failure():
    """Test handling of missing repo path."""
    assert migrate_repo("/nonexistent/path") == ExitCode.FAILURE


@pytest.fixture
def mock_successful_migration(monkeypatch, repo_analysis):
    """Mock successful migration steps."""
    monkeypatch.setattr("migrate_repo.analyze_repo", lambda *args: repo_analysis)
    monkeypatch.setattr("migrate_repo.convert_pyproject", lambda *args: True)
    monkeypatch.setattr("migrate_repo.run_checks", lambda *args: (True, ""))
    monkeypatch.setattr("migrate_repo.commit_changes", lambda *args: None)


def test__migrate_repo__with_valid_repo__success(mock_successful_migration, tmp_path):
    """Test successful end-to-end migration."""
    assert migrate_repo(str(tmp_path)) == ExitCode.SUCCESS
