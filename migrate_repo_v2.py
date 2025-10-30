#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys
import yaml
import tomlkit
import ast
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

UV_PATH = "/home/jon/Work/.local/bin/uv"

@dataclass
class RepoAnalysis:
    """Analysis results for a repository."""
    duplicate_deps: List[str]
    invalid_versions: List[Tuple[str, str]]
    module_conflicts: List[Tuple[str, str]]
    missing_stubs: List[str]
    has_async: bool
    has_type_annotations: bool
    has_long_lines: bool
    python_versions: List[str]

def find_duplicate_dependencies(doc: Dict[str, Any]) -> List[str]:
    """Find duplicate dependencies in pyproject.toml."""
    deps = set()
    duplicates = []
    
    if "project" in doc and "dependencies" in doc["project"]:
        for dep in doc["project"]["dependencies"]:
            name = dep.split(" ")[0].split("[")[0]
            if name in deps:
                duplicates.append(name)
            deps.add(name)
    
    if "dependency-groups" in doc and "dev" in doc["dependency-groups"]:
        for dep in doc["dependency-groups"]["dev"]:
            name = dep.split(" ")[0].split("[")[0]
            if name in deps:
                duplicates.append(name)
            deps.add(name)
    
    return duplicates

def validate_version_constraint(version: str) -> Optional[str]:
    """Validate and normalize version constraint."""
    try:
        version = str(version).replace("^", ">=").replace("~", ">=")
        if version.endswith(".*"):
            version = version[:-2]
        
        if ".post" in version:
            version = version.split(".post")[0]
        
        if not version.endswith(".0"):
            version = f"{version}.0"
        
        if version.startswith(">="):
            major = int(version.split(".")[0].replace(">=", "")) + 1
            version = f"{version}, <{major}.0"
        
        return version
    except (ValueError, IndexError):
        return None

def validate_version_constraints(doc: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Find invalid version constraints in pyproject.toml."""
    invalid = []
    
    if "project" in doc and "dependencies" in doc["project"]:
        for dep in doc["project"]["dependencies"]:
            name = dep.split(" ")[0]
            version = " ".join(dep.split(" ")[1:])
            if not validate_version_constraint(version):
                invalid.append((name, version))
    
    if "dependency-groups" in doc and "dev" in doc["dependency-groups"]:
        for dep in doc["dependency-groups"]["dev"]:
            name = dep.split(" ")[0]
            version = " ".join(dep.split(" ")[1:])
            if not validate_version_constraint(version):
                invalid.append((name, version))
    
    return invalid

def check_module_conflicts(repo_path: Path) -> List[Tuple[str, str]]:
    """Find module name conflicts in the repository."""
    conflicts = []
    modules = {}
    
    for path in repo_path.glob("**/*.py"):
        if ".venv" in str(path):
            continue
        
        module_name = path.stem
        if module_name in modules:
            conflicts.append((module_name, str(path)))
        else:
            modules[module_name] = str(path)
    
    return conflicts

def find_required_type_stubs(repo_path: Path) -> List[str]:
    """Find imports that might need type stubs."""
    imports = set()
    
    for path in repo_path.glob("**/*.py"):
        if ".venv" in str(path):
            continue
        
        try:
            with open(path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except:
            continue
    
    # Common packages that don't need stubs
    builtin_packages = {
        "os", "sys", "pathlib", "typing", "collections", "datetime",
        "json", "re", "time", "random", "math", "itertools", "functools"
    }
    
    return sorted(imports - builtin_packages)

def has_async_code(repo_path: Path) -> bool:
    """Check if repository contains async/await code."""
    for path in repo_path.glob("**/*.py"):
        if ".venv" in str(path):
            continue
        
        try:
            with open(path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor)):
                    return True
        except:
            continue
    
    return False

def has_type_annotations(repo_path: Path) -> bool:
    """Check if repository uses type annotations."""
    for path in repo_path.glob("**/*.py"):
        if ".venv" in str(path):
            continue
        
        try:
            with open(path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.AnnAssign) or (
                    isinstance(node, ast.FunctionDef) and node.returns
                ):
                    return True
        except:
            continue
    
    return False

def has_long_lines(repo_path: Path, max_length: int = 88) -> bool:
    """Check if repository has lines longer than max_length."""
    for path in repo_path.glob("**/*.py"):
        if ".venv" in str(path):
            continue
        
        try:
            with open(path) as f:
                for line in f:
                    if len(line.rstrip()) > max_length:
                        return True
        except:
            continue
    
    return False

def analyze_repo(repo_path: Path) -> RepoAnalysis:
    """Analyze repository before migration."""
    with open(repo_path / "pyproject.toml") as f:
        doc = tomlkit.parse(f.read())
    
    return RepoAnalysis(
        duplicate_deps=find_duplicate_dependencies(doc),
        invalid_versions=validate_version_constraints(doc),
        module_conflicts=check_module_conflicts(repo_path),
        missing_stubs=find_required_type_stubs(repo_path),
        has_async=has_async_code(repo_path),
        has_type_annotations=has_type_annotations(repo_path),
        has_long_lines=has_long_lines(repo_path),
        python_versions=[v.strip() for v in doc.get("project", {}).get("requires-python", ">=3.12,<4.0").split(",")]
    )

def configure_tools(repo_path: Path, analysis: RepoAnalysis) -> Dict[str, Any]:
    """Configure tools based on repo analysis."""
    config: Dict[str, Any] = {"tool": {}}
    
    # Configure mypy
    mypy_config = {}
    if analysis.has_async:
        mypy_config["strict_optional"] = True
        mypy_config["warn_unused_awaits"] = True
    if analysis.has_type_annotations:
        mypy_config["strict"] = True
        mypy_config["warn_return_any"] = True
    if analysis.module_conflicts:
        mypy_config["exclude"] = ["before/.*"]
    config["tool"]["mypy"] = mypy_config
    
    # Configure ruff
    ruff_config = {}
    if analysis.has_long_lines:
        ruff_config["line-length"] = 100
    if any("before/" in conflict[1] for conflict in analysis.module_conflicts):
        ruff_config["exclude"] = ["before"]
    config["tool"]["ruff"] = ruff_config
    
    return config

def normalize_version(constraint: Any) -> str:
    """Convert Poetry version constraint to PEP 440 format."""
    version = str(constraint).replace("^", ">=").replace("~", ">=")
    if version.endswith(".*"):
        version = version[:-2]
    
    if ".post" in version:
        version = version.split(".post")[0]
    
    if not version.endswith(".0"):
        version = f"{version}.0"
    
    if version.startswith(">="):
        major = int(version.split(".")[0].replace(">=", "")) + 1
        version = f"{version}, <{major}.0"
    
    return version

def convert_pyproject(repo_path: Path, analysis: RepoAnalysis) -> bool:
    """Convert pyproject.toml to UV format with analysis-based improvements."""
    with open(repo_path / "pyproject.toml") as f:
        doc = tomlkit.parse(f.read())
    
    if "tool" not in doc or "poetry" not in doc["tool"]:
        print("No Poetry configuration found")
        return False

    poetry_config = doc["tool"]["poetry"]
    
    # Create new pyproject.toml structure
    new_doc = tomlkit.document()
    
    # Build section
    new_doc["build-system"] = {
        "requires": ["hatchling"],
        "build-backend": "hatchling.build"
    }
    new_doc["tool"] = {"hatch": {"build": {"targets": {"wheel": {"include": ["*.py", "**/*.py"]}}}}}
    
    # Add tool configurations
    tool_config = configure_tools(repo_path, analysis)
    new_doc["tool"].update(tool_config["tool"])
    
    # Project section
    project: Dict[str, Any] = {}
    
    # Basic metadata
    name = poetry_config.get("name", "").lower().replace(" ", "-")
    project["name"] = name
    project["version"] = poetry_config.get("version", "0.1.0")
    project["description"] = poetry_config.get("description", "")
    
    # Authors
    authors = poetry_config.get("authors", [])
    project["authors"] = [{"name": author.split("<")[0].strip()} for author in authors]
    
    # Dependencies
    deps = []
    for dep, constraint in poetry_config.get("dependencies", {}).items():
        if dep == "python":
            python_version = normalize_version(constraint)
            project["requires-python"] = python_version
            continue
        
        if isinstance(constraint, dict):
            extras = constraint.get("extras", [])
            version = constraint.get("version", "")
            version = normalize_version(version)
            if extras:
                deps.append(f"{dep}[{','.join(extras)}] {version}")
            else:
                deps.append(f"{dep} {version}")
        else:
            version = normalize_version(constraint)
            deps.append(f"{dep} {version}")
    
    project["dependencies"] = sorted(deps)
    
    # Dev dependencies
    dev_deps = []
    for group_name, group in poetry_config.get("group", {}).items():
        if "dependencies" in group:
            for dep, constraint in group["dependencies"].items():
                if isinstance(constraint, dict):
                    version = constraint.get("version", "")
                    extras = constraint.get("extras", [])
                    version = normalize_version(version)
                    if extras:
                        dep = f"{dep}[{','.join(extras)}]"
                else:
                    version = normalize_version(constraint)
                dev_deps.append(f"{dep} {version}")
    
    # Add missing type stubs
    for pkg in analysis.missing_stubs:
        if any(dep.startswith(f"types-{pkg} ") for dep in dev_deps):
            continue
        dev_deps.append(f"types-{pkg} >=2.0.0, <3.0")
    
    # Add standard dev tools
    dev_deps.extend([
        'pytest >=8.0.0, <9.0',
        'ruff >=0.1.3, <0.2.0',
        'mypy >=1.6.1, <2.0.0',
        'deptry >=0.14.2, <0.15.0'
    ])
    
    if dev_deps:
        new_doc["dependency-groups"] = {"dev": sorted(dev_deps)}
    
    new_doc["project"] = project
    
    with open(repo_path / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(new_doc))
    
    return True

def update_manifest(repo_path: Path, status: str, notes: str) -> None:
    """Update migration manifest."""
    manifest_path = Path.home() / "Work/poetry_migration/poetry_to_uv_manifest.yaml"
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    rel_path = repo_path.relative_to(Path.home() / "Work")
    for repo in manifest["repos"]:
        if repo["path"] == str(rel_path):
            repo["status"] = status
            repo["last_updated"] = "2025-10-30"
            repo["notes"] = notes
            break
    
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, sort_keys=False)

def find_python_files(repo_path: Path) -> List[str]:
    """Find Python files in the repository."""
    python_files = []
    for path in repo_path.glob("**/*.py"):
        if ".venv" not in str(path) and "before/" not in str(path):
            python_files.append(str(path.relative_to(repo_path)))
    return python_files

def migrate_repo(repo_path: str) -> int:
    """Migrate repository to UV with analysis-based improvements."""
    repo = Path(repo_path).resolve()
    if not repo.exists():
        print(f"Repository {repo} does not exist")
        return 1
    
    print(f"Migrating {repo}")
    
    # Analyze repository
    try:
        analysis = analyze_repo(repo)
        print("\nAnalysis Results:")
        print(f"- Duplicate dependencies: {len(analysis.duplicate_deps)}")
        print(f"- Invalid versions: {len(analysis.invalid_versions)}")
        print(f"- Module conflicts: {len(analysis.module_conflicts)}")
        print(f"- Missing type stubs: {len(analysis.missing_stubs)}")
        print(f"- Has async code: {analysis.has_async}")
        print(f"- Has type annotations: {analysis.has_type_annotations}")
        print(f"- Has long lines: {analysis.has_long_lines}")
        print(f"- Python versions: {', '.join(analysis.python_versions)}\n")
    except Exception as e:
        print(f"Analysis failed: {e}")
        return 1
    
    if is_already_migrated(repo):
        print("Repository is already migrated to UV")
        return 0
    
    # Convert pyproject.toml
    if not convert_pyproject(repo, analysis):
        return 1
    
    # Create .python-version
    python_version = analysis.python_versions[0].replace(">=", "").strip()
    major, minor = python_version.split(".")[:2]
    python_version = f"{major}.{minor}"
    (repo / ".python-version").write_text(f"{python_version}\n")
    
    # Clean up old files
    for file in ["poetry.lock", ".venv"]:
        path = repo / file
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                subprocess.run(["rm", "-rf", str(path)], check=True)
    
    # Install dependencies and run checks
    env = {"UV_CACHE_DIR": str(Path.home() / "Work/.cache/uv")}
    success = True
    error_output = ""
    
    cmds = [
        [UV_PATH, "sync", "--refresh"],
        [UV_PATH, "sync", "--group", "dev"]
    ]
    
    # Find Python files
    python_files = find_python_files(repo)
    if python_files:
        cmds.extend([
            [UV_PATH, "run", "ruff", "check", "."],
            [UV_PATH, "run", "mypy"] + python_files,
            [UV_PATH, "run", "pytest"]
        ])
    
    for cmd in cmds:
        try:
            result = subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True, env=env)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr
            success = False
            break
    
    # Commit changes if successful
    if success:
        run_cmd(["git", "add", "pyproject.toml", ".python-version", "uv.lock"], repo)
        notes = []
        if analysis.module_conflicts:
            notes.append("excluded before/ directory")
        if analysis.missing_stubs:
            notes.append(f"added type stubs: {', '.join(analysis.missing_stubs)}")
        if analysis.has_async:
            notes.append("configured async mypy checks")
        if analysis.has_type_annotations:
            notes.append("enabled strict mypy mode")
        note = "; ".join(notes) if notes else "converted with standard configuration"
        
        run_cmd(["git", "commit", "-m", f"chore: migrate from poetry to uv\n\n{note}"], repo)
        update_manifest(repo, "migrated", note)
        print("Migration successful")
        return 0
    
    print("Migration failed")
    print(error_output)
    return 1

def run_cmd(cmd: List[str], cwd: str | Path, env: Dict[str, str] | None = None) -> bool:
    """Run command with environment variables."""
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
            if "VIRTUAL_ENV" in merged_env:
                del merged_env["VIRTUAL_ENV"]
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, env=merged_env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {' '.join(cmd)}:")
        print(e.stderr)
        return False

def is_already_migrated(repo_path: Path) -> bool:
    """Check if repository is already migrated to UV."""
    with open(repo_path / "pyproject.toml") as f:
        doc = tomlkit.parse(f.read())
    
    # Check for Poetry configuration
    if "tool" in doc and "poetry" in doc["tool"]:
        return False
    
    # Check for UV configuration
    if "project" in doc and "dependency-groups" in doc:
        return True
    
    return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: migrate_repo.py <repo_path>")
        sys.exit(1)
    
    sys.exit(migrate_repo(sys.argv[1]))
