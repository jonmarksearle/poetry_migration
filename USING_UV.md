# Using uv: Setup, Migration, and Daily Workflow

This guide shows how to standardise on [uv](https://docs.astral.sh/uv/), move existing projects across gradually, and keep day-to-day work frictionless. The instructions apply to Wordcount and the rest of your repositories.

---

## 1. Install uv and Python 3.13 (once)

Add the uv directory definitions to your shell profile **once** so every command shares the same
paths. If they are not already present, append the block below to `~/.bashrc` (or whichever profile you use):
```bash
grep -q 'UV_INSTALL_DIR' ~/.bashrc || cat <<'EOF' >> ~/.bashrc
export UV_INSTALL_DIR=$HOME/Work/.local/bin
export UV_DATA_DIR=$HOME/Work/.local/share/uv
export UV_CACHE_DIR=$HOME/Work/.cache/uv
export UV_CONFIG_DIR=$HOME/Work/.config/uv
EOF
source ~/.bashrc
```

With the environment prepared, install uv:
```bash
mkdir -p "$UV_INSTALL_DIR" "$UV_DATA_DIR" "$UV_CACHE_DIR" "$UV_CONFIG_DIR"
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.13
```

This keeps the uv binary, its cache, and managed interpreters on `/home/jon/Work` (the `/dev/sda1`
volume) so hard links into project checkouts stay on the same filesystem. Maintain narrow symlinks
from `~/.local/bin/*` back to their `~/Work/.local/bin/*` counterparts to preserve PATH stability:
```bash
mkdir -p ~/.local/bin
ln -sf "$UV_INSTALL_DIR/uv" ~/.local/bin/uv
ln -sf "$UV_INSTALL_DIR/uvx" ~/.local/bin/uvx
```
Repeat the `ln -sf` pattern for any other uv-managed tools you install later (e.g. `python`, `ruff`, `ipython`).

Verify everything resolves from the Work volume:
```bash
command -v uv
df --output=source,target "$UV_INSTALL_DIR/uv"
```

Pin 3.13 as your personal default so every new `uv run` or `uv init` inherits it:
```bash
uv python pin --global 3.13
```
(This writes `~/.python-version`.)

---

## 2. Configure uv defaults

Create `~/.config/uv/uv.toml` to capture your preferred template for `uv init` and friends:
```toml
[init]
package = "auto"         # library vs app detection
vcs = "git"
build-backend = "uv"
managed-python = true
python = "3.13"
author-from = "git"
```
Adjust as needed (see `uv init --help` for all keys). With this in place, `uv init my-new-project` automatically sets up the layout you expect.

---

## 3. Adjust your shell for global tools

Run once:
```bash
uv python update-shell --shell bash
```
Copy the emitted snippet into `~/.bashrc` and reload your shell. This adds uv’s shim directory to `PATH`, so global commands automatically use uv.

Install the tools you want available everywhere (these land in `~/Work/.local/bin`, with matching
symlinks in `~/.local/bin` if you keep PATH compatibility as suggested above):
```bash
uv tool install ipython
uv tool install ruff
uv tool install mypy
```
Now typing `python`, `ipython`, `ruff`, or `mypy` runs the uv-managed versions (no virtualenv activation).

If a legacy virtualenv is ever active (e.g. `VIRTUAL_ENV=/home/jon/.venv/python312`), clear it before running uv:
```bash
unset VIRTUAL_ENV
```
You can wrap that in an alias: `alias uvpy='unset VIRTUAL_ENV && uv run'`.

### Cleaning up existing virtualenv auto-activation

Your current `~/.bashrc` sources `py312` at startup, which reasserts the old interpreter. To let uv handle the default version:
1. Edit `~/.bashrc` and locate the line near the end that reads `py312` (and any aliases that automatically call it).
2. Comment it out or wrap it in a function so it only runs when explicitly requested.
   ```bash
   # Old behaviour (remove or comment out)
   # py312

   # Optional helper if you still need quick access to that environment
   alias py312='unset VIRTUAL_ENV && source ~/.venv/python312/bin/activate'
   ```
3. Reload your shell (`source ~/.bashrc`) or open a new terminal. From now on, typing `python` uses the uv-managed interpreter you pinned globally.

To remove legacy virtualenvs entirely:
```bash
rm -rf ~/.venv/python311 ~/.venv/python312
```
You can recreate them later with `uv venv --python 3.13` inside any project if you still need isolated environments. uv-managed tools and per-project pins make separate user-level venvs unnecessary.

### Decommission `py311`/`py312` aliases and helpers

Retire the legacy helpers so shells don’t accidentally re-enable those virtualenvs:
1. Open `~/.bashrc` and delete the aliases `py311`/`py312` plus any chained aliases that invoke them (`d1`, `d2`, `ml`, `m1`, `m2`, `yt`, `ytt`, `acg`, `ideas`, and the `ytcd()` function).
2. Replace them with uv-native shortcuts if you still want quick jumps, for example:
   ```bash
   alias d1='cd ~/Work/1_datalake/ && unset VIRTUAL_ENV && uv run python'
   ```
   or keep them as simple `cd` helpers and run `uv run …` manually.
3. Remove `pip-review` (or other pip-only tooling) from global aliases such as `update`; rely on `uv python upgrade`/`uv tool upgrade` instead.
4. After editing, reload the profile and confirm no references remain:
   ```bash
   source ~/.bashrc
   rg -n 'py31[12]' ~/.bashrc
   ```
   The final command should produce no matches. If it does, repeat the cleanup until all references are gone.

### Purge legacy site-packages and CPython installs

Once every workflow uses uv, remove the pip-installed library trees and restrict Python versions to
3.12–3.14:
1. Reinstall any global tools you still need via uv (e.g. `uv tool install ipython`, `uv tool install pytest`, `uv tool install playwright`, `uv tool install yt-dlp`). This replaces scripts that currently live under `~/.local/bin`.
2. Remove the old user-site directories and helper headers:
   ```bash
   find ~/.local/lib -maxdepth 1 -type d -regex '.*/python3\.1[01]' -exec rm -rf {} +
   rm -rf ~/.local/include/python3.10
   find ~/.local/bin -maxdepth 1 \( -type f -o -type l \) -regex '.*/python3\.1[01]' -exec rm -f {} +
   find ~/.local/bin -maxdepth 1 \( -type f -o -type l \) -regex '.*/pip3?(\.1[01])?' -exec rm -f {} +
   ```
   Inspect any remaining `~/.local/bin/*` scripts; delete those that belonged to the retired installs or recreate them with uv tools.
3. If pipx-managed virtualenvs must transition to uv, reinstall those tools with `uv tool install` and remove the corresponding `~/.local/pipx/venvs/<name>` directories; otherwise, leave pipx in place for the few binaries that need it.
4. Align uv-managed interpreters with your target set:
   ```bash
   uv python list
   uv python uninstall <version>   # run once per interpreter below 3.12 (use the exact version from the list)
   uv python install 3.12 3.13 3.14
   uv python pin --global 3.13
   ```
5. Confirm only uv-provided executables remain:
   ```bash
   which python
   which pip || echo "pip now provided via uv (use 'uv pip ...')"
   uv python list
   ```

---

## 4. Working in a uv project

For a repository already using uv (especially after reinstalling uv or cleaning global caches):
```bash
rm -rf .venv            # remove stale environment built against the old install (safe to rerun)
uv venv                 # recreate .venv tied to the project’s pin
uv pip install -e .     # install project and cache tooling (uses hard links from the uv cache)

uv run ruff check
uv run mypy tools/search.py
uv run pytest
```
`uv run` automatically selects the interpreter from `.python-version` or `pyproject.toml`. No need to pass `--python` unless you’re overriding on purpose.

To pin a project that doesn’t have a version yet:
```bash
uv python pin 3.13
```
This writes `.python-version`; commit it alongside `pyproject.toml` so teammates use the same interpreter.

---

## 5. Migration plan for existing repositories

1. **Inventory** projects under `~/Work`: note which use pip, poetry, Docker images, etc.
2. **Stabilise each repo**:
   - Add/verify `pyproject.toml` with `requires-python = ">=3.13"`.
   - Run `rm -rf .venv && uv venv` (or `uv venv --clear`) and `uv pip install -e . --refresh`; solve missing dependencies.
   - Create or update `uv.lock` (`uv pip sync --refresh`) so the cache uses hard links on the new install.
3. **Replace old workflows**:
   - Swap `pip install`/`pipenv`/`poetry` commands in README/Makefiles for `uv pip`/`uv run`.
   - Update CI to install uv (`curl … | sh`), `uv pip install -e .`, then use `uv run` for lint/type/test.
   - For Dockerfiles, install uv inside the image and rely on `uv pip install --python 3.13 ...`.
4. **Shell aliases**: replace any `alias foo='cd repo && py312'` with `alias foo='cd repo && unset VIRTUAL_ENV && uv run ...'` once the repo is migrated.
5. **Docs**: add a repo-specific snippet (borrow from this file) so contributors know to use uv.
6. **Gradual rollout**: prioritise active repos; archive or leave older ones until needed.

---

## 6. Day-to-day reminders
- Global tools (`python`, `ipython`, etc.) now come from uv’s shims. If you upgrade Python, run `uv python install 3.14` and `uv python pin --global 3.14`; Tools installed with `uv tool install` automatically follow.
- Projects stay isolated via `.python-version`/`pyproject.toml`. `uv run` respects those pins even if the global version differs.
- If a command complains about missing modules, install them via `uv pip install ...` (or `uv pip install --dev ...` when dev extras are defined).
- `uv python list` shows all interpreters you’ve installed; `uv python update-shell --shell bash` prints the PATH snippet again if needed.

---

---

## Updating uv itself

uv records installation details in `~/.config/uv/uv-receipt.json`. If you see `uv self update` report that the binary came from the standalone installer, rerun:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
This reinstalls uv in `~/Work/.local/bin`, after which `uv python upgrade --all` and `uv tool upgrade --all` (as used in your `update` alias) keep interpreters and tools current. Re-create the symlinks
in `~/.local/bin` if you removed them during reinstall.

## 7. Reference material
- Official docs: <https://docs.astral.sh/uv/> – landing page for guides and CLI reference.
- CLI reference: <https://docs.astral.sh/uv/reference/cli/> – details for `uv init`, `uv python`, etc.
- Blog introduction: <https://astral.sh/blog/uv> – rationale and feature overview from Astral.
- “uv Basics” article: <https://astral.sh/uv/guides/python-projects/> – step-by-step tutorial on creating and running projects.
- “uv for existing projects” guide: <https://astral.sh/uv/guides/migrating/> – covers migration patterns and common pitfalls.

With this setup:
- Typing `python` or `ipython` anywhere uses the uv-managed version you pinned once.
- Each repository dictates its own interpreter and dependencies through uv config files.
- Switching projects or running CI becomes a matter of the same three commands: `uv venv`, `uv pip install -e .`, and `uv run <tool>`.

Follow the migration plan incrementally and, over time, every repo under `~/Work` will share a consistent, low-maintenance workflow.
