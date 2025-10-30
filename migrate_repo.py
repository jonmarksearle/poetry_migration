#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys
import yaml
import tomlkit
from typing import Any, Dict, List, Optional

UV_PATH = "/home/jon/Work/.local/bin/uv"

def run_cmd(cmd: List[str], cwd: str | Path, env: Dict[str, str] | None = None) -> bool:
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
    with open(repo_path / "pyproject.toml") as f:
        doc = tomlkit.parse(f.read())
    
    # Check for Poetry configuration
    if "tool" in doc and "poetry" in doc["tool"]:
        return False
    
    # Check for UV configuration
    if "project" in doc and "dependency-groups" in doc:
        return True
    
    return False

def get_python_version(poetry_config: Dict[str, Any]) -> str:
    """Extract Python version from Poetry configuration."""
    if "dependencies" not in poetry_config:
        return ">=3.12, <4.0"
    
    python_constraint = poetry_config["dependencies"].get("python", "^3.12")
    version = str(python_constraint).replace("^", ">=").replace("~", ">=")
    if version.endswith(".*"):
        version = version[:-2]
    
    if not version.endswith(".0"):
        version = f"{version}.0"
    
    major = int(version.split(".")[0].replace(">=", "")) + 1
    return f"{version}, <{major}.0"

def normalize_version(constraint: Any) -> str:
    """Convert Poetry version constraint to PEP 440 format."""
    version = str(constraint).replace("^", ">=").replace("~", ">=")
    if version.endswith(".*"):
        version = version[:-2]
    
    if not version.endswith(".0"):
        version = f"{version}.0"
    
    if version.startswith(">="):
        major = int(version.split(".")[0].replace(">=", "")) + 1
        version = f"{version}, <{major}.0"
    
    return version

def get_dev_dependencies(poetry_config: Dict[str, Any]) -> List[str]:
    """Extract dev dependencies from Poetry configuration."""
    dev_deps = []
    
    # Get dependencies from dev group
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
    
    # Add standard dev tools
    dev_deps.extend([
        'pytest >=7.4.4, <8.0.0',
        'ruff >=0.1.3, <0.2.0',
        'mypy >=1.6.1, <2.0.0',
        'deptry >=0.14.2, <0.15.0'
    ])
    
    return sorted(dev_deps)

def add_tool_config(doc: Dict[str, Any], tool: str, error_msg: str) -> None:
    """Add tool-specific configuration after a check failure."""
    if tool == "mypy":
        if "tool" not in doc:
            doc["tool"] = {}
        if "mypy" not in doc["tool"]:
            doc["tool"]["mypy"] = {}
        
        if "before/" in error_msg:
            doc["tool"]["mypy"]["exclude"] = ["before/.*"]
        if "Library stubs not installed for" in error_msg:
            pkg = error_msg.split('"')[1]
            if "dependency-groups" in doc:
                doc["dependency-groups"]["dev"].append(f"types-{pkg} >=2.0.0, <3.0.0")
                doc["dependency-groups"]["dev"].sort()
    
    elif tool == "ruff":
        if "tool" not in doc:
            doc["tool"] = {}
        if "ruff" not in doc["tool"]:
            doc["tool"]["ruff"] = {}
            doc["tool"]["ruff"]["line-length"] = 100
            if "before/" in error_msg:
                doc["tool"]["ruff"]["exclude"] = ["before"]

def convert_pyproject(repo_path: Path) -> bool:
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
            python_version = get_python_version(poetry_config)
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
    dev_deps = get_dev_dependencies(poetry_config)
    if dev_deps:
        new_doc["dependency-groups"] = {"dev": dev_deps}
    
    new_doc["project"] = project
    
    with open(repo_path / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(new_doc))
    
    return True

def update_manifest(repo_path: Path, status: str, notes: str) -> None:
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
    repo = Path(repo_path).resolve()
    if not repo.exists():
        print(f"Repository {repo} does not exist")
        return 1
    
    print(f"Migrating {repo}")
    
    if is_already_migrated(repo):
        print("Repository is already migrated to UV")
        return 0
    
    # Backup and convert pyproject.toml
    if not convert_pyproject(repo):
        return 1
    
    # Create .python-version
    with open(repo / "pyproject.toml") as f:
        doc = tomlkit.parse(f.read())
        python_version = doc["project"]["requires-python"].split(",")[0].replace(">=", "")
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
            tool = cmd[2] if len(cmd) > 2 else None
            if tool in ["ruff", "mypy"]:
                with open(repo / "pyproject.toml") as f:
                    doc = tomlkit.parse(f.read())
                add_tool_config(doc, tool, error_output)
                with open(repo / "pyproject.toml", "w") as f:
                    f.write(tomlkit.dumps(doc))
                try:
                    subprocess.run(cmd, cwd=repo, check=True, capture_output=True, text=True, env=env)
                except subprocess.CalledProcessError:
                    success = False
                    break
            else:
                success = False
                break
    
    # Commit changes if successful
    if success:
        run_cmd(["git", "add", "pyproject.toml", ".python-version", "uv.lock"], repo)
        run_cmd(["git", "commit", "-m", "chore: migrate from poetry to uv"], repo)
        update_manifest(repo, "migrated", "Converted to uv with dev tooling; all checks passing.")
        print("Migration successful")
        return 0
    
    print("Migration failed")
    print(error_output)
    return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: migrate_repo.py <repo_path>")
        sys.exit(1)
    
    sys.exit(migrate_repo(sys.argv[1]))
