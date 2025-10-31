# Migrating to uv on `/home/jon/Work`

This planning document walks through the full migration from today’s mixed Python setup (system interpreters, legacy `~/.venv` directories, pip-installed tools) to a uv-first workflow located entirely under `/home/jon/Work`. uv is a standalone Python package, environment, and version manager that replaces tools like `pip`, `pipx`, `virtualenv`, and `pyenv` with a single fast binary.citeturn7search0

Follow each phase sequentially, pausing at the checkpoints before moving on. The goal is a no-surprises rollout: every binary, managed interpreter, cache, and project environment will be owned by uv on the Work volume.

---

## Phase 0 – Audit and Back Up (Current State Snapshot)

1. Back up key dotfiles and virtual environments so you can roll back if needed:
   ```bash
   cp ~/.bashrc ~/.bashrc.before-uv.$(date +%Y%m%d)
   cp -r ~/.venv ~/.venv.before-uv.$(date +%Y%m%d)
   ```
2. Inventory active interpreters and environments:
   ```bash
   which -a python python3
   ls ~/.venv
   uv python list --only-installed || true
   ```
3. Capture the global scripts you rely on:
   ```bash
   ls ~/.local/bin
   ```
   You will reinstall any keepers with `uv tool install` in Phase 4.

---

## Phase 1 – Prepare uv Directories on `/home/jon/Work`

1. Create the directories that will host uv-managed binaries, interpreters, tools, and caches:
   ```bash
   mkdir -p ~/Work/.local/bin \
            ~/Work/.local/share/uv/python \
            ~/Work/.local/share/uv/tools \
            ~/Work/.cache/uv
   ```
2. Add the following block near the top of `~/.bashrc` (after prompt or shell options) so every shell honours the Work-volume locations:
   ```bash
   export UV_CACHE_DIR=$HOME/Work/.cache/uv
   export UV_PYTHON_INSTALL_DIR=$HOME/Work/.local/share/uv/python
   export UV_PYTHON_BIN_DIR=$HOME/Work/.local/bin
   export UV_TOOL_DIR=$HOME/Work/.local/share/uv/tools
   export UV_TOOL_BIN_DIR=$HOME/Work/.local/bin
   ```
   These environment variables control where uv stores its cache, managed interpreters, and tool executables.citeturn2search0
3. Reload the shell (`source ~/.bashrc`) and confirm each variable points to `/home/jon/Work/...`:
   ```bash
   env | grep '^UV_'
   ```

---

## Phase 2 – Install or Reinstall uv on the Work Volume

1. Remove any existing uv binaries in `~/.local/bin` to avoid shadowing:
   ```bash
   rm -f ~/.local/bin/uv ~/.local/bin/uvx
   ```
2. Reinstall uv using the standalone installer, directing the binary to `~/Work/.local/bin`:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$HOME/Work/.local/bin sh
   ```
   The installer honours `UV_INSTALL_DIR`, letting you choose the destination path.citeturn7search3
3. Recreate symlinks so existing scripts that rely on `~/.local/bin` still work:
   ```bash
   mkdir -p ~/.local/bin
   ln -sf ~/Work/.local/bin/uv ~/.local/bin/uv
   ln -sf ~/Work/.local/bin/uvx ~/.local/bin/uvx
   ```
4. Verify the binary resolves to the Work volume and note the version for future upgrades:
   ```bash
   command -v uv
   df --output=source,target "$(command -v uv)"
   uv --version
   ```
   (The installer ships a single static binary; `uv --version` confirms the expected release.)citeturn7search0

Checkpoint: `command -v uv` should show `/home/jon/Work/.local/bin/uv`.

---

## Phase 3 – Shell Integration and Global Interpreter Pin

1. Open `~/.bashrc` and disable legacy auto-activation:
   - Comment out or remove lines that source `py311`, `py312`, or similar virtualenv helpers.
   - Replace aliases like `alias d1='cd ... && py312'` with uv-based equivalents (e.g., `alias d1='cd ~/Work/1_datalake && uv run python'`).
   - Update your `update` alias to drop `pip-review`; Phase 4 provides the uv replacement.
   - After editing, reload with `source ~/.bashrc` and run `rg -n 'py31[12]' ~/.bashrc` to confirm nothing auto-activates the old virtualenvs.
2. Run uv’s shell helper and append the emitted PATH snippet (if it isn’t already present):
   ```bash
   uv python update-shell --shell bash
   ```
   This ensures the configured Python bin directory stays on your PATH, even when you change `UV_PYTHON_BIN_DIR`.citeturn4search0
3. Install and pin Python 3.13 globally so new projects inherit it:
   ```bash
   uv python install 3.13
   uv python pin --global 3.13
   ```
   The `--global` pin writes `.python-version` into uv’s configuration directory (XDG-compliant), providing a default whenever a project pin is absent.citeturn3search1turn3search4
4. Restart your shell and confirm `python` points to uv’s managed interpreter:
   ```bash
   python -V
   which python
   df --output=source,target "$(which python)"
   ```
5. Capture user defaults for new projects by creating `~/.config/uv/uv.toml`:
   ```toml
   [init]
   package = "auto"
   vcs = "git"
   build-backend = "uv"
   managed-python = true
   python = "3.13"
   author-from = "git"
   ```
   uv discovers this file automatically and applies the settings to future `uv init` runs.citeturn2search4

Checkpoint: `python -V` should report CPython 3.13.x from `/home/jon/Work/.local/share/uv/python`.

---

## Phase 4 – Reinstall Global Tools with uv

1. Reinstall everyday CLI tools under uv’s management:
   ```bash
   uv tool install ipython ruff mypy pytest
   uv tool install playwright yt-dlp
   ```
   `uv tool install` creates isolated tool environments and places shims in `UV_TOOL_BIN_DIR`, keeping them consistent across projects.citeturn7search0
2. Review the installed tools:
   ```bash
   uv tool list
   ```
3. Replace the old maintenance alias with uv-native upgrades:
   ```bash
   alias update='sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y && sudo npm update -g && flatpak update -y && uv python upgrade --all && uv tool upgrade --all'
   ```
   These commands upgrade uv-managed interpreters and tools without touching system Python.citeturn3search8turn4search0
4. Reload your shell and spot-check:
   ```bash
   type ipython
   type update
   ```

Checkpoint: `uv tool list` should show your CLI tools installed under `/home/jon/Work/.local/share/uv/tools`.

---

## Phase 5 – Retire Legacy Virtualenvs and Interpreters

1. Ensure no session has an active virtualenv (`echo $VIRTUAL_ENV` should be empty). If needed, run `unset VIRTUAL_ENV`. Consider adding `alias uvpy='unset VIRTUAL_ENV && uv run'` for convenience.
2. Remove obsolete user-level virtualenvs and Python scripts:
   ```bash
   rm -rf ~/.venv/python311 ~/.venv/python312
   find ~/.local/lib -maxdepth 1 -type d -regex '.*/python3\.1[01]' -exec rm -rf {} +
   find ~/.local/bin -maxdepth 1 \( -type f -o -type l \) -regex '.*/python3\.1[01]' -exec rm -f {} +
   find ~/.local/bin -maxdepth 1 \( -type f -o -type l \) -regex '.*/pip3?(\.1[01])?' -exec rm -f {} +
   ```
3. Uninstall legacy uv-managed interpreters below 3.12 to free space:
   ```bash
   uv python list --only-installed
   uv python uninstall 3.11 3.10 3.9 || true
   ```
   Managed interpreters live under `UV_PYTHON_INSTALL_DIR`, so uninstalls reclaim space on `/home/jon/Work`.citeturn3search6

Checkpoint: `uv python list --only-installed` should list only 3.12+ CPython builds (plus any new betas you intentionally installed).

---

## Phase 6 – Migrate Each Repository (Repeatable Loop)

Use this loop for Wordcount and every other active repo:

1. Ensure the repo has a `pyproject.toml`. Set `requires-python = ">=3.13"` and, if helpful, add a `[tool.uv]` section for project-specific defaults.
2. Remove any existing `.venv`:
   ```bash
   rm -rf .venv
   ```
3. Sync from scratch with uv. This creates `.venv`, refreshes `uv.lock`, and removes stray packages:
   ```bash
   UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --refresh
   ```
   `uv sync` performs an exact install aligned with the lockfile; the `--refresh` flag updates cached wheels as needed.citeturn5search0turn5search2
4. Run quality gates through uv so they honour project pins:
   ```bash
   uv run ruff check
   uv run mypy
   uv run pytest
   ```
5. Commit the updated `uv.lock`, `.python-version` (if newly pinned), and documentation changes once tests pass.
6. Update project docs, Makefiles, CI pipelines, and shell scripts to use `uv sync`, `uv run`, and the shared `UV_CACHE_DIR` prefix instead of `pip install` or `poetry`.

Checkpoint per repo: `uv run python -V` should match the project’s `.python-version`, and `uv run pytest` should pass without activating legacy environments.

---

## Phase 7 – Final System Verification

1. Confirm shell shims point to uv-managed executables:
   ```bash
   which python pip ipython
   ```
2. Inspect installed interpreters and tools:
   ```bash
   uv python list --only-installed
   uv tool list
   ```
3. Open a new terminal and run:
   ```bash
   uv run python -V
   uv sync --check
   ```
   This catches lingering PATH issues or stale lockfiles.
4. Update CI scripts to install uv with the same `UV_INSTALL_DIR=$HOME/Work/.local/bin` pattern and to run `uv sync --locked` for reproducibility.citeturn5search4

Checkpoint: All terminals start without auto-activating old virtualenvs, and uv commands run without warnings about mismatched paths.

---

## Phase 8 – Day-to-Day Workflow After Migration

- Use `uv sync` (optionally with `--all-extras`, `--group`, or `--check`) whenever dependencies change; it recreates `.venv` automatically and keeps it aligned with `uv.lock`.citeturn5search2turn5search5
- Run tooling through uv (`uv run ruff`, `uv run mypy`, `uv run pytest`) so commands respect project pins and share the global cache.citeturn7search0
- Add dependencies with `uv add <package>` or edit `pyproject.toml` and rerun `uv sync`.
- For one-off tools, use `uvx <tool>` or `uv tool run <name>` to avoid polluting project environments.citeturn7search0
- Keep global tooling current via the `update` alias (`uv python upgrade --all && uv tool upgrade --all`).citeturn3search8turn4search0

---

## Phase 9 – Maintaining uv Itself

- Periodically reinstall uv with the standalone installer (same `UV_INSTALL_DIR` command) or run `uv self update` if you leave the binary in place.citeturn7search1turn7search3
- After upgrades, confirm the pinned interpreter still resolves correctly:
  ```bash
  uv python list --only-installed
  python -V
  ```
- If you ever change `UV_PYTHON_BIN_DIR` or `UV_TOOL_BIN_DIR`, rerun `uv python update-shell` and `uv tool update-shell` to refresh PATH entries.citeturn4search0

---

## Appendix – Quick Reference

- Install uv to `/home/jon/Work/.local/bin`:\
  `curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$HOME/Work/.local/bin sh`citeturn7search3
- Redirect caches, interpreters, and tools to `/home/jon/Work`:\
  export `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `UV_PYTHON_BIN_DIR`, `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR`.citeturn2search0
- Pin global interpreter:\
  `uv python install 3.13 && uv python pin --global 3.13`.citeturn3search1
- Recreate project environments:\
  `UV_CACHE_DIR=$HOME/Work/.cache/uv uv sync --refresh`.citeturn5search2
- Keep tools current:\
  `uv python upgrade --all && uv tool upgrade --all`.citeturn3search8

With these phases complete, uv owns every interpreter, cache, and CLI, all rooted under `/home/jon/Work`. The migration plan doubles as a checklist—run it step by step and the transition from the old Python setup to a uv-only workflow will stay controlled and predictable.
