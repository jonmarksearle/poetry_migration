#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import yaml
from typing import Any, Dict, List
import tomlkit

def run_cmd(cmd: List[str], cwd: str | Path) -> bool:
    try:
        subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {' '.join(cmd)}:")
        print(e.stderr)
        return False

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
            python_version = constraint.replace("^", ">=").replace("~", ">=")
            if not python_version.endswith(".*"):
                project["requires-python"] = f"{python_version}, <4.0"
            continue
        
        if isinstance(constraint, str):
            version = constraint.replace("^", ">=").replace("~", ">=")
            if not version.endswith(".*"):
                if version.startswith(">="):
                    major = int(version.split(".")[0].replace(">=", "")) + 1
                    version = f"{version}, <{major}.0.0"
            deps.append(f"{dep} {version}")
        elif isinstance(constraint, dict):
            extras = constraint.get("extras", [])
            version = constraint.get("version", "").replace("^", ">=").replace("~", ">=")
            if extras:
                if not version.endswith(".*"):
                    if version.startswith(">="):
                        major = int(version.split(".")[0].replace(">=", "")) + 1
                        version = f"{version}, <{major}.0.0"
                deps.append(f"{dep}[{','.join(extras)}] {version}")
            else:
                deps.append(f"{dep} {version}")
    
    project["dependencies"] = sorted(deps)
    
    # Dev dependencies
    dev_deps = []
    for group_name, group in poetry_config.get("group", {}).items():
        if "dependencies" in group:
            for dep, constraint in group["dependencies"].items():
                version = constraint.replace("^", ">=").replace("~", ">=")
                if not version.endswith(".*"):
                    if version.startswith(">="):
                        major = int(version.split(".")[0].replace(">=", "")) + 1
                        version = f"{version}, <{major}.0.0"
                dev_deps.append(f"{dep} {version}")
    
    # Add standard dev tools
    dev_deps.extend([
        'pytest >=7.4.4, <8.0.0',
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

def migrate_repo(repo_path: str) -> int:
    repo = Path(repo_path).resolve()
    if not repo.exists():
        print(f"Repository {repo} does not exist")
        return 1
    
    print(f"Migrating {repo}")
    
    # Check for uncommitted changes
    if run_cmd(["git", "diff", "--quiet"], repo) is False:
        print("Repository has uncommitted changes")
        return 1
    
    # Backup and convert pyproject.toml
    if not convert_pyproject(repo):
        return 1
    
    # Create .python-version
    python_version = "3.12"  # Default to 3.12
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
    
    cmds = [
        ["uv", "sync", "--refresh"],
        ["uv", "sync", "--group", "dev"],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "mypy", "."],
        ["uv", "run", "pytest"]
    ]
    
    for cmd in cmds:
        if not run_cmd(cmd, repo):
            success = False
            break
    
    # Commit changes if successful
    if success:
        run_cmd(["git", "add", "pyproject.toml", ".python-version"], repo)
        run_cmd(["git", "commit", "-m", "chore: migrate from poetry to uv"], repo)
        update_manifest(repo, "migrated", "Converted to uv with dev tooling; all checks passing.")
        print("Migration successful")
        return 0
    
    print("Migration failed")
    return 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: migrate_repo.py <repo_path>")
        sys.exit(1)
    
    sys.exit(migrate_repo(sys.argv[1]))
