#!/usr/bin/env python3
from __future__ import annotations

import ast
import itertools
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from enum import IntEnum
from pathlib import Path
from typing import Any

import tomlkit
import yaml

UV_PATH = "/home/jon/Work/.local/bin/uv"


class ExitCode(IntEnum):
    """Exit codes for migration script."""

    SUCCESS = 0
    FAILURE = 1


TYPED_PACKAGES = frozenset({
    "sqlalchemy",
    "pydantic",
    "fastapi",
    "starlette",
    "pytest",
    "click",
    "inject",
    "httpx",
    "jinja2",
    "aiohttp",
    "asyncpg",
    "typer",
    "rich",
    "uvicorn",
    "websockets",
})

BUILTIN_MODULES = frozenset({
    "os",
    "sys",
    "pathlib",
    "typing",
    "collections",
    "datetime",
    "json",
    "re",
    "time",
    "random",
    "math",
    "itertools",
    "functools",
})

type TomlDoc = dict[str, Any]


@dataclass(frozen=True)
class RepoAnalysis:
    """Analysis results for a repository."""

    duplicate_deps: frozenset[str]
    invalid_versions: tuple[tuple[str, str], ...]
    module_conflicts: tuple[tuple[str, str], ...]
    missing_stubs: tuple[str, ...]
    has_async: bool
    has_type_annotations: bool
    has_long_lines: bool
    python_versions: tuple[str, ...]


def extract_dep_name(dep: str) -> str:
    """Extract package name from dependency string."""
    return dep.split(" ")[0].split("[")[0]


def get_project_deps(doc: TomlDoc) -> tuple[str, ...]:
    """Get project dependencies."""
    return tuple(doc.get("project", {}).get("dependencies", []))


def get_dev_deps(doc: TomlDoc) -> tuple[str, ...]:
    """Get dev dependencies."""
    dev_groups = doc.get("dependency-groups", {})
    return tuple(dev_groups.get("dev", []))


def find_duplicates_in_sequence(names: tuple[str, ...]) -> frozenset[str]:
    """Find duplicate names in sequence."""
    seen: set[str] = set()
    duplicates = (name for name in names if name in seen or seen.add(name))
    return frozenset(duplicates)


def find_duplicate_dependencies(doc: TomlDoc) -> frozenset[str]:
    """Find duplicate dependencies in pyproject.toml."""
    all_deps = get_project_deps(doc) + get_dev_deps(doc)
    names = tuple(extract_dep_name(dep) for dep in all_deps)
    return find_duplicates_in_sequence(names)


def strip_version_markers(version: str) -> str:
    """Strip Poetry version markers."""
    v = version.replace("^", ">=").replace("~", ">=")
    v = v[:-2] if v.endswith(".*") else v
    return v.split(".post")[0] if ".post" in v else v


def ensure_patch_version(version: str) -> str:
    """Ensure version has patch number."""
    return f"{version}.0" if not version.endswith(".0") else version


def normalize_version_string(version: str) -> str:
    """Normalize version string to PEP 440 format."""
    return ensure_patch_version(strip_version_markers(version))


def add_upper_bound(version: str) -> str:
    """Add upper bound to version constraint."""
    major = int(version.split(".")[0].replace(">=", "")) + 1
    return f"{version}, <{major}.0"


def add_upper_bound_if_needed(normalized: str) -> str:
    """Add upper bound to version if it starts with >=."""
    if normalized.startswith(">="):
        return add_upper_bound(normalized)
    return normalized


def validate_version_constraint(version: str) -> str | None:
    """Validate and normalize version constraint."""
    try:
        normalized = normalize_version_string(version)
        return add_upper_bound_if_needed(normalized)
    except (ValueError, IndexError):
        return None


def extract_dep_version(dep: str) -> tuple[str, str]:
    """Extract name and version from dependency string."""
    parts = dep.split(" ", 1)
    return (parts[0], parts[1] if len(parts) > 1 else "")


def is_invalid_version(name: str, version: str) -> bool:
    """Check if version constraint is invalid."""
    return bool(version and not validate_version_constraint(version))


def validate_version_constraints(
    doc: TomlDoc,
) -> tuple[tuple[str, str], ...]:
    """Find invalid version constraints in pyproject.toml."""
    all_deps = get_project_deps(doc) + get_dev_deps(doc)
    name_versions = (extract_dep_version(dep) for dep in all_deps)
    invalid = ((n, v) for n, v in name_versions if is_invalid_version(n, v))
    return tuple(invalid)


def get_python_files(repo_path: Path) -> tuple[Path, ...]:
    """Get all Python files excluding .venv."""
    all_files = repo_path.glob("**/*.py")
    return tuple(p for p in all_files if ".venv" not in str(p))


def build_module_map(files: tuple[Path, ...]) -> dict[str, str]:
    """Build map of module names to file paths."""
    return {p.stem: str(p) for p in files}


def find_conflicts(
    files: tuple[Path, ...], module_map: dict[str, str]
) -> tuple[tuple[str, str], ...]:
    """Find conflicting module names."""
    conflicts = (
        (p.stem, str(p)) for p in files if module_map.get(p.stem) != str(p)
    )
    return tuple(conflicts)


def check_module_conflicts(repo_path: Path) -> tuple[tuple[str, str], ...]:
    """Find module name conflicts in the repository."""
    files = get_python_files(repo_path)
    module_map = build_module_map(files)
    return find_conflicts(files, module_map)


def read_file_as_syntax_tree(path: Path) -> ast.Module | None:
    """Read Python file and convert to Abstract Syntax Tree for analysis.
    
    Returns None if file cannot be read or parsed.
    """
    try:
        return ast.parse(path.read_text())
    except (OSError, SyntaxError):
        return None


def extract_module_root(full_name: str) -> str:
    """Extract root module name from dotted import path."""
    return full_name.split(".")[0]


def extract_import_names(tree: ast.Module) -> set[str]:
    """Extract import statement names."""
    imports = {
        extract_module_root(name.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    }
    return imports


def extract_from_import_names(tree: ast.Module) -> set[str]:
    """Extract from-import statement names."""
    from_imports = {
        extract_module_root(node.module)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    return from_imports


def extract_imports_from_ast(tree: ast.Module) -> frozenset[str]:
    """Extract top-level package names from AST."""
    imports = extract_import_names(tree)
    from_imports = extract_from_import_names(tree)
    return frozenset(imports | from_imports)


def extract_local_module_names(repo_path: Path) -> frozenset[str]:
    """Extract local module names from Python files in repo."""
    files = get_python_files(repo_path)
    modules = {f.stem for f in files}
    packages = {
        f.parent.name
        for f in files
        if f.name == "__init__.py" and f.parent != repo_path
    }
    return frozenset(modules | packages)


def is_local_module(module_name: str, repo_path: Path) -> bool:
    """Check if module is local to the repository.
    
    Scans actual Python files to detect local modules regardless
    of directory structure (src/, app/, nested packages, etc).
    """
    local_modules = extract_local_module_names(repo_path)
    return module_name in local_modules


def collect_all_imports(files: tuple[Path, ...]) -> set[str]:
    """Collect all imports from Python files."""
    all_imports: set[str] = set()
    for f in files:
        if tree := read_file_as_syntax_tree(f):
            all_imports.update(extract_imports_from_ast(tree))
    return all_imports


def filter_external_imports(
    imports: set[str], repo_path: Path
) -> set[str]:
    """Filter to external imports only."""
    external = imports - BUILTIN_MODULES - TYPED_PACKAGES
    return {m for m in external if not is_local_module(m, repo_path)}


def find_required_type_stubs(repo_path: Path) -> tuple[str, ...]:
    """Find imports that might need type stubs."""
    files = get_python_files(repo_path)
    all_imports = collect_all_imports(files)
    needs_stubs = filter_external_imports(all_imports, repo_path)
    return tuple(sorted(needs_stubs))


def has_async_node(tree: ast.Module) -> bool:
    """Check if AST contains async nodes."""
    async_types = (ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor)
    return any(isinstance(n, async_types) for n in ast.walk(tree))


def file_has_async_code(file: Path) -> bool:
    """Check if file contains async/await code."""
    tree = read_file_as_syntax_tree(file)
    return tree is not None and has_async_node(tree)


def has_async_code(repo_path: Path) -> bool:
    """Check if repository contains async/await code."""
    files = get_python_files(repo_path)
    return any(file_has_async_code(f) for f in files)


def file_has_type_annotations(file: Path) -> bool:
    """Check if file uses type annotations."""
    tree = read_file_as_syntax_tree(file)
    if tree is None:
        return False
    return any(is_annotation_node(n) for n in ast.walk(tree))


def has_type_annotations(repo_path: Path) -> bool:
    """Check if repository uses type annotations."""
    files = get_python_files(repo_path)
    return any(file_has_type_annotations(f) for f in files)


def check_line_length(line: str, max_length: int) -> bool:
    """Check if line exceeds max length."""
    return len(line.rstrip()) > max_length


def get_file_lines(file: Path) -> list[str]:
    """Get lines from file, return empty list on error."""
    try:
        return file.read_text().splitlines()
    except OSError:
        return []


def file_has_long_lines(file: Path, max_length: int) -> bool:
    """Check if file has long lines."""
    lines = get_file_lines(file)
    return any(check_line_length(line, max_length) for line in lines)


def has_long_lines(repo_path: Path, max_length: int = 88) -> bool:
    """Check if repository has lines longer than max_length."""
    files = get_python_files(repo_path)
    return any(file_has_long_lines(f, max_length) for f in files)


def load_toml(path: Path) -> TomlDoc:
    """Load TOML document from file."""
    return tomlkit.parse(path.read_text())


def extract_python_versions(doc: TomlDoc) -> tuple[str, ...]:
    """Extract Python version constraints from document."""
    project = doc.get("project", {})
    requires_python = project.get("requires-python", ">=3.12,<4.0")
    return tuple(v.strip() for v in requires_python.split(","))


def create_repo_analysis(
    doc: TomlDoc, repo_path: Path
) -> RepoAnalysis:
    """Create RepoAnalysis from document and path."""
    return RepoAnalysis(
        duplicate_deps=find_duplicate_dependencies(doc),
        invalid_versions=validate_version_constraints(doc),
        module_conflicts=check_module_conflicts(repo_path),
        missing_stubs=find_required_type_stubs(repo_path),
        has_async=has_async_code(repo_path),
        has_type_annotations=has_type_annotations(repo_path),
        has_long_lines=has_long_lines(repo_path),
        python_versions=extract_python_versions(doc),
    )


def analyze_repo(repo_path: Path) -> RepoAnalysis:
    """Analyze repository before migration."""
    doc = load_toml(repo_path / "pyproject.toml")
    return create_repo_analysis(doc, repo_path)


def build_async_mypy_config() -> dict[str, bool]:
    """Build mypy config for async code."""
    return {"strict_optional": True, "warn_unused_awaits": True}


def build_strict_mypy_config() -> dict[str, bool]:
    """Build strict mypy config."""
    return {"strict": True, "warn_return_any": True}


def get_async_config_keys() -> frozenset[str]:
    """Get mypy config keys for async code."""
    return frozenset({"strict_optional", "warn_unused_awaits"})


def get_strict_config_keys() -> frozenset[str]:
    """Get mypy config keys for strict mode."""
    return frozenset({"strict", "warn_return_any"})


def build_mypy_config(analysis: RepoAnalysis) -> dict[str, Any]:
    """Build mypy configuration based on analysis."""
    async_cfg = build_async_mypy_config() if analysis.has_async else {}
    strict_cfg = build_strict_mypy_config() if analysis.has_type_annotations else {}
    exclude_cfg = {"exclude": ["before/.*"]} if analysis.module_conflicts else {}
    return async_cfg | strict_cfg | exclude_cfg


def has_before_directory_conflicts(
    conflicts: tuple[tuple[str, str], ...]
) -> bool:
    """Check if any conflicts are in before/ directory."""
    return any("before/" in path for _, path in conflicts)


def build_ruff_config(analysis: RepoAnalysis) -> dict[str, Any]:
    """Build ruff configuration based on analysis."""
    line_cfg = {"line-length": 100} if analysis.has_long_lines else {}
    has_before = has_before_directory_conflicts(analysis.module_conflicts)
    exclude_cfg = {"exclude": ["before"]} if has_before else {}
    return line_cfg | exclude_cfg


def configure_tools(
    repo_path: Path, analysis: RepoAnalysis
) -> dict[str, Any]:
    """Configure tools based on repo analysis."""
    mypy_cfg = build_mypy_config(analysis)
    ruff_cfg = build_ruff_config(analysis)
    return {"tool": {"mypy": mypy_cfg, "ruff": ruff_cfg}}


def normalize_version(constraint: Any) -> str:
    """Convert Poetry version constraint to PEP 440 format."""
    normalized = normalize_version_string(str(constraint))
    if normalized.startswith(">="):
        return add_upper_bound(normalized)
    return normalized


def build_build_system() -> dict[str, Any]:
    """Build build-system section."""
    return {"requires": ["hatchling"], "build-backend": "hatchling.build"}


def build_wheel_config() -> dict[str, Any]:
    """Build wheel configuration."""
    return {"include": ["*.py", "**/*.py"]}


def build_hatch_config() -> dict[str, Any]:
    """Build hatch tool configuration."""
    return {
        "hatch": {"build": {"targets": {"wheel": build_wheel_config()}}}
    }


def format_author(author: str) -> dict[str, str]:
    """Format author string to dict."""
    return {"name": author.split("<")[0].strip()}


def extract_authors(poetry_config: dict[str, Any]) -> list[dict[str, str]]:
    """Extract and format authors."""
    authors_list = poetry_config.get("authors", [])
    return [format_author(a) for a in authors_list]


def extract_project_metadata(poetry_config: dict[str, Any]) -> dict[str, Any]:
    """Extract basic project metadata."""
    name = poetry_config.get("name", "").lower().replace(" ", "-")
    return {
        "name": name,
        "version": poetry_config.get("version", "0.1.0"),
        "description": poetry_config.get("description", ""),
        "authors": extract_authors(poetry_config),
    }


def format_dep_with_extras(dep: str, extras: list[str], version: str) -> str:
    """Format dependency with extras."""
    extras_str = ",".join(extras)
    return f"{dep}[{extras_str}] {version}"


def format_simple_dependency(dep: str, constraint: Any) -> str:
    """Format dependency with simple version constraint."""
    if not constraint:
        return dep
    return f"{dep} {normalize_version(constraint)}"


def has_non_version_keys(constraint: dict[str, Any]) -> bool:
    """Check if dict has path/git/url keys (non-version dependency)."""
    non_version_keys = {"path", "git", "url", "develop"}
    return any(key in constraint for key in non_version_keys)


def format_path_dependency(dep: str, constraint: dict[str, Any]) -> str:
    """Format path dependency to PEP 621 with absolute file URI."""
    path = Path(constraint["path"]).resolve()
    return f"{dep} @ {path.as_uri()}"


def format_git_dependency(dep: str, constraint: dict[str, Any]) -> str:
    """Format git dependency to PEP 621.
    
    Preserves rev/tag/branch if specified, otherwise no @ref suffix.
    """
    git_url = constraint["git"]
    ref = constraint.get("rev") or constraint.get("tag") or constraint.get("branch")
    if ref:
        return f"{dep} @ git+{git_url}@{ref}"
    return f"{dep} @ git+{git_url}"


def format_url_dependency(dep: str, constraint: dict[str, Any]) -> str:
    """Format url dependency to PEP 621."""
    url = constraint["url"]
    return f"{dep} @ {url}"


def format_non_version_dependency(
    dep: str, constraint: dict[str, Any]
) -> str:
    """Format path/git/url dependency to PEP 621."""
    if "path" in constraint:
        return format_path_dependency(dep, constraint)
    if "git" in constraint:
        return format_git_dependency(dep, constraint)
    if "url" in constraint:
        return format_url_dependency(dep, constraint)
    return dep


def format_dict_dependency(dep: str, constraint: dict[str, Any]) -> str:
    """Format dependency from dict constraint."""
    if has_non_version_keys(constraint):
        return format_non_version_dependency(dep, constraint)
    if "version" not in constraint:
        return dep
    version = normalize_version(constraint["version"])
    extras = constraint.get("extras", [])
    if extras:
        return format_dep_with_extras(dep, extras, version)
    return f"{dep} {version}"


def format_dependency(dep: str, constraint: Any) -> str:
    """Format a single dependency with version constraint.
    
    Handles version strings, dicts with version/extras, and
    path/git/url deps by converting to PEP 621 format.
    """
    if isinstance(constraint, dict):
        return format_dict_dependency(dep, constraint)
    return format_simple_dependency(dep, constraint)


def is_not_python_dep(dep_name: str) -> bool:
    """Check if dependency is not the Python version specifier."""
    return dep_name != "python"


def get_non_python_deps(
    deps_dict: dict[str, Any]
) -> tuple[tuple[str, Any], ...]:
    """Get all dependencies except Python version."""
    items = ((d, c) for d, c in deps_dict.items() if is_not_python_dep(d))
    return tuple(items)


def extract_dependencies(
    poetry_config: dict[str, Any],
) -> tuple[tuple[str, ...], str]:
    """Extract dependencies and Python version requirement."""
    deps_dict = poetry_config.get("dependencies", {})
    python_version = normalize_version(deps_dict.get("python", "^3.12"))
    dep_items = get_non_python_deps(deps_dict)
    deps = tuple(sorted(format_dependency(d, c) for d, c in dep_items))
    return deps, python_version


def get_all_group_deps(
    groups: dict[str, Any]
) -> tuple[tuple[str, Any], ...]:
    """Get all dependencies from all groups."""
    all_items = (
        (d, c)
        for g in groups.values()
        for d, c in g.get("dependencies", {}).items()
    )
    return tuple(all_items)


def extract_dev_dependencies(
    poetry_config: dict[str, Any],
) -> tuple[str, ...]:
    """Extract dev dependencies from Poetry groups."""
    groups = poetry_config.get("group", {})
    all_items = get_all_group_deps(groups)
    return tuple(format_dependency(d, c) for d, c in all_items)


def build_type_stub_deps(missing_stubs: tuple[str, ...]) -> tuple[str, ...]:
    """Build type stub dependency strings."""
    return tuple(f"types-{pkg} >=2.0.0, <3.0" for pkg in missing_stubs)


def build_standard_tool_deps() -> tuple[str, ...]:
    """Build standard development tool dependencies."""
    return (
        "pytest >=8.0.0, <9.0",
        "ruff >=0.1.3, <0.2.0",
        "mypy >=1.6.1, <2.0.0",
        "deptry >=0.14.2, <0.15.0",
    )


def filter_new_deps(
    deps: tuple[str, ...], existing_names: frozenset[str]
) -> tuple[str, ...]:
    """Filter deps to only those not in existing names."""
    return tuple(d for d in deps if extract_dep_name(d) not in existing_names)


def get_existing_dep_names(existing: tuple[str, ...]) -> frozenset[str]:
    """Get set of existing dependency names."""
    return frozenset(extract_dep_name(d) for d in existing)


def get_new_stubs(
    missing_stubs: tuple[str, ...], existing_names: frozenset[str]
) -> tuple[str, ...]:
    """Get new type stub dependencies."""
    stubs = build_type_stub_deps(missing_stubs)
    return filter_new_deps(stubs, existing_names)


def get_new_tools(existing_names: frozenset[str]) -> tuple[str, ...]:
    """Get new tool dependencies."""
    tools = build_standard_tool_deps()
    return filter_new_deps(tools, existing_names)


def build_dev_dependencies(
    poetry_config: dict[str, Any], analysis: RepoAnalysis
) -> tuple[str, ...]:
    """Build complete dev dependencies list.

    Includes deptry - not run during migration but useful for
    ongoing project maintenance to detect unused dependencies.
    """
    existing = extract_dev_dependencies(poetry_config)
    existing_names = get_existing_dep_names(existing)
    stubs = get_new_stubs(analysis.missing_stubs, existing_names)
    tools = get_new_tools(existing_names)
    return tuple(sorted(existing + stubs + tools))


def build_project_section(
    poetry_config: dict[str, Any], analysis: RepoAnalysis
) -> dict[str, Any]:
    """Build project section for pyproject.toml."""
    project = extract_project_metadata(poetry_config)
    deps, python_version = extract_dependencies(poetry_config)
    project["requires-python"] = python_version
    project["dependencies"] = list(deps)
    return project


def add_dev_groups(
    doc: TomlDoc, dev_deps: tuple[str, ...]
) -> None:
    """Add dependency groups to document."""
    if dev_deps:
        doc["dependency-groups"] = {"dev": list(dev_deps)}


def initialize_pyproject_doc() -> TomlDoc:
    """Initialize new pyproject.toml document."""
    doc = tomlkit.document()
    doc["build-system"] = build_build_system()
    doc["tool"] = build_hatch_config()
    return doc


def build_new_pyproject(
    poetry_config: dict[str, Any], analysis: RepoAnalysis, repo_path: Path
) -> TomlDoc:
    """Build new pyproject.toml structure."""
    new_doc = initialize_pyproject_doc()
    tool_config = configure_tools(repo_path, analysis)
    new_doc["tool"].update(tool_config["tool"])
    new_doc["project"] = build_project_section(poetry_config, analysis)
    dev_deps = build_dev_dependencies(poetry_config, analysis)
    add_dev_groups(new_doc, dev_deps)
    return new_doc


def write_toml(path: Path, doc: TomlDoc) -> None:
    """Write TOML document to file."""
    path.write_text(tomlkit.dumps(doc))


def has_poetry_config(doc: TomlDoc) -> bool:
    """Check if document has Poetry configuration."""
    return "tool" in doc and "poetry" in doc["tool"]


def convert_pyproject(repo_path: Path, analysis: RepoAnalysis) -> bool:
    """Convert pyproject.toml to UV format."""
    doc = load_toml(repo_path / "pyproject.toml")
    if not has_poetry_config(doc):
        print("No Poetry configuration found")
        return False
    poetry_config = doc["tool"]["poetry"]
    new_doc = build_new_pyproject(poetry_config, analysis, repo_path)
    write_toml(repo_path / "pyproject.toml", new_doc)
    return True


def get_manifest_path() -> Path:
    """Get path to migration manifest."""
    return Path.home() / "Work/poetry_migration/poetry_to_uv_manifest.yaml"


def load_manifest() -> dict[str, Any]:
    """Load migration manifest."""
    return yaml.safe_load(get_manifest_path().read_text())


def save_manifest(manifest: dict[str, Any]) -> None:
    """Save migration manifest."""
    manifest_yaml = yaml.dump(manifest, sort_keys=False)
    get_manifest_path().write_text(manifest_yaml)


def find_repo_in_manifest(
    manifest: dict[str, Any], rel_path: str
) -> dict[str, Any] | None:
    """Find repository entry in manifest."""
    matching = (repo for repo in manifest["repos"] if repo["path"] == rel_path)
    return next(matching, None)


def update_repo_entry(
    repo_entry: dict[str, Any], status: str, notes: str
) -> None:
    """Update repository entry with new status."""
    repo_entry["status"] = status
    repo_entry["last_updated"] = date.today().isoformat()
    repo_entry["notes"] = notes


def update_manifest(repo_path: Path, status: str, notes: str) -> None:
    """Update migration manifest."""
    manifest = load_manifest()
    rel_path = str(repo_path.relative_to(Path.home() / "Work"))
    repo_entry = find_repo_in_manifest(manifest, rel_path)
    if repo_entry:
        update_repo_entry(repo_entry, status, notes)
        save_manifest(manifest)


def find_python_files(repo_path: Path) -> tuple[str, ...]:
    """Find Python files in the repository."""
    files = get_python_files(repo_path)
    filtered = (p for p in files if "before/" not in str(p))
    return tuple(str(p.relative_to(repo_path)) for p in filtered)


def merge_env(env: dict[str, str] | None) -> dict[str, str]:
    """Merge environment variables with os.environ."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
        merged_env.pop("VIRTUAL_ENV", None)
    return merged_env


def execute_subprocess(
    cmd: list[str], cwd: Path, merged_env: dict[str, str]
) -> None:
    """Execute subprocess with given environment."""
    subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env=merged_env,
    )


def run_cmd(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None
) -> tuple[bool, str]:
    """Run command with environment variables."""
    try:
        execute_subprocess(cmd, cwd, merge_env(env))
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, f"Error running {' '.join(cmd)}:\n{e.stderr}"


def is_already_migrated(repo_path: Path) -> bool:
    """Check if repository is already migrated to UV."""
    doc = load_toml(repo_path / "pyproject.toml")
    has_poetry = has_poetry_config(doc)
    has_uv = "project" in doc and "dependency-groups" in doc
    return not has_poetry and has_uv


def print_analysis_header() -> None:
    """Print analysis results header."""
    print("\nAnalysis Results:")


def print_analysis_counts(analysis: RepoAnalysis) -> None:
    """Print analysis counts."""
    print(f"- Duplicate dependencies: {len(analysis.duplicate_deps)}")
    print(f"- Invalid versions: {len(analysis.invalid_versions)}")
    print(f"- Module conflicts: {len(analysis.module_conflicts)}")
    print(f"- Missing type stubs: {len(analysis.missing_stubs)}")


def print_analysis_flags(analysis: RepoAnalysis) -> None:
    """Print analysis boolean flags."""
    print(f"- Has async code: {analysis.has_async}")
    print(f"- Has type annotations: {analysis.has_type_annotations}")
    print(f"- Has long lines: {analysis.has_long_lines}")


def print_analysis_versions(analysis: RepoAnalysis) -> None:
    """Print Python versions."""
    versions_str = ", ".join(analysis.python_versions)
    print(f"- Python versions: {versions_str}\n")


def print_analysis_results(analysis: RepoAnalysis) -> None:
    """Print analysis results to console."""
    print_analysis_header()
    print_analysis_counts(analysis)
    print_analysis_flags(analysis)
    print_analysis_versions(analysis)


def extract_python_version(analysis: RepoAnalysis) -> str:
    """Extract major.minor Python version."""
    version = analysis.python_versions[0].replace(">=", "").strip()
    major, minor = version.split(".")[:2]
    return f"{major}.{minor}"


def create_python_version_file(repo_path: Path, version: str) -> None:
    """Create .python-version file."""
    (repo_path / ".python-version").write_text(f"{version}\n")


def remove_path(path: Path) -> None:
    """Remove file or directory."""
    if path.is_file():
        path.unlink()
    else:
        subprocess.run(["rm", "-rf", str(path)], check=True)


def clean_old_files(repo_path: Path) -> None:
    """Remove Poetry lock file and virtualenv."""
    for file in ("poetry.lock", ".venv"):
        path = repo_path / file
        if path.exists():
            remove_path(path)


def build_base_commands() -> tuple[list[str], ...]:
    """Build base sync commands."""
    return (
        [UV_PATH, "sync", "--refresh"],
        [UV_PATH, "sync", "--group", "dev"],
    )


def build_check_commands_list(
    python_files: tuple[str, ...]
) -> tuple[list[str], ...]:
    """Build check commands for Python files."""
    return (
        [UV_PATH, "run", "ruff", "check", "."],
        [UV_PATH, "run", "mypy", *python_files],
        [UV_PATH, "run", "pytest"],
    )


def build_check_commands(
    python_files: tuple[str, ...]
) -> tuple[list[str], ...]:
    """Build list of check commands to run."""
    base = build_base_commands()
    if not python_files:
        return base
    checks = build_check_commands_list(python_files)
    return base + checks


def get_uv_cache_env() -> dict[str, str]:
    """Get UV cache environment variable."""
    cache_dir = str(Path.home() / "Work/.cache/uv")
    return {"UV_CACHE_DIR": cache_dir}


def execute_check_commands(
    cmds: tuple[list[str], ...], repo_path: Path, env: dict[str, str]
) -> tuple[bool, str]:
    """Execute all check commands."""
    for cmd in cmds:
        success, error = run_cmd(cmd, repo_path, env)
        if not success:
            return False, error
    return True, ""


def run_checks(
    repo_path: Path, python_files: tuple[str, ...]
) -> tuple[bool, str]:
    """Run all checks and return success status and error output."""
    env = get_uv_cache_env()
    cmds = build_check_commands(python_files)
    return execute_check_commands(cmds, repo_path, env)


def build_note_for_conflicts() -> str:
    """Build note for module conflicts."""
    return "excluded before/ directory"


def build_note_for_stubs(stubs: tuple[str, ...]) -> str:
    """Build note for type stubs."""
    return f"added type stubs: {', '.join(stubs)}"


def build_note_for_async() -> str:
    """Build note for async configuration."""
    return "configured async mypy checks"


def build_note_for_strict() -> str:
    """Build note for strict mypy mode."""
    return "enabled strict mypy mode"


def find_conflict_notes(analysis: RepoAnalysis):
    """Generate notes for module conflicts."""
    if analysis.module_conflicts:
        yield build_note_for_conflicts()


def find_stub_notes(analysis: RepoAnalysis):
    """Generate notes for type stubs."""
    if analysis.missing_stubs:
        yield build_note_for_stubs(analysis.missing_stubs)


def find_async_notes(analysis: RepoAnalysis):
    """Generate notes for async configuration."""
    if analysis.has_async:
        yield build_note_for_async()


def find_strict_notes(analysis: RepoAnalysis):
    """Generate notes for strict mypy mode."""
    if analysis.has_type_annotations:
        yield build_note_for_strict()


def collect_commit_notes(analysis: RepoAnalysis) -> tuple[str, ...]:
    """Collect all commit notes."""
    return tuple(
        itertools.chain(
            find_conflict_notes(analysis),
            find_stub_notes(analysis),
            find_async_notes(analysis),
            find_strict_notes(analysis),
        )
    )


def build_commit_notes(analysis: RepoAnalysis) -> str:
    """Build commit notes from analysis results."""
    notes = collect_commit_notes(analysis)
    default = "converted with standard configuration"
    return "; ".join(notes) if notes else default


def commit_changes(repo_path: Path, analysis: RepoAnalysis) -> None:
    """Commit migration changes to git."""
    files = ["pyproject.toml", ".python-version", "uv.lock"]
    run_cmd(["git", "add", *files], repo_path)
    note = build_commit_notes(analysis)
    commit_msg = f"chore: migrate from poetry to uv\n\n{note}"
    run_cmd(["git", "commit", "-m", commit_msg], repo_path)
    update_manifest(repo_path, "migrated", note)


def perform_analysis(repo: Path) -> RepoAnalysis | None:
    """Perform repository analysis."""
    try:
        analysis = analyze_repo(repo)
        print_analysis_results(analysis)
        return analysis
    except Exception as e:
        print(f"Analysis failed: {e}")
        return None


def perform_migration(repo: Path, analysis: RepoAnalysis) -> bool:
    """Perform the migration steps."""
    if not convert_pyproject(repo, analysis):
        return False
    version = extract_python_version(analysis)
    create_python_version_file(repo, version)
    clean_old_files(repo)
    return True


def run_migration_checks(repo: Path) -> tuple[bool, str]:
    """Run checks after migration."""
    python_files = find_python_files(repo)
    return run_checks(repo, python_files)


def handle_migration_failure(error: str) -> int:
    """Handle migration failure."""
    print("Migration failed")
    print(error)
    return ExitCode.FAILURE


def handle_migration_success(repo: Path, analysis: RepoAnalysis) -> int:
    """Handle successful migration."""
    commit_changes(repo, analysis)
    print("Migration successful")
    return ExitCode.SUCCESS


def check_repo_exists(repo: Path) -> bool:
    """Check if repository exists."""
    if not repo.exists():
        print(f"Repository {repo} does not exist")
        return False
    return True


def check_already_migrated(repo: Path) -> bool:
    """Check if already migrated."""
    if is_already_migrated(repo):
        print("Repository is already migrated to UV")
        return True
    return False


def run_migration_and_checks(repo: Path, analysis: RepoAnalysis) -> int:
    """Run migration and checks, return result code."""
    if not perform_migration(repo, analysis):
        return ExitCode.FAILURE
    success, error = run_migration_checks(repo)
    return (
        handle_migration_success(repo, analysis)
        if success
        else handle_migration_failure(error)
    )


def handle_analysis_and_checks(
    repo: Path, analysis: RepoAnalysis | None
) -> int:
    """Handle analysis result and run migration checks."""
    if not analysis:
        return ExitCode.FAILURE
    if check_already_migrated(repo):
        return ExitCode.SUCCESS
    return run_migration_and_checks(repo, analysis)


def migrate_repo(repo_path: str) -> int:
    """Migrate repository to UV with analysis-based improvements."""
    repo = Path(repo_path).resolve()
    if not check_repo_exists(repo):
        return ExitCode.FAILURE
    print(f"Migrating {repo}")
    analysis = perform_analysis(repo)
    return handle_analysis_and_checks(repo, analysis)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: migrate_repo.py <repo_path>")
        sys.exit(1)
    sys.exit(migrate_repo(sys.argv[1]))
