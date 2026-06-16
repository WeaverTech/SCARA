# SCARA

## Cursor Cloud specific instructions

### Current repository state

As of this branch, `main` is an **empty scaffold**: the only tracked file is
`README.md` (containing `# SCARA`). There is no application code, no dependency
manifest (no `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`,
`Cargo.toml`, etc.), no setup script, no Dockerfile, and no
`.cursor/environment.json`. Consequently there is nothing to install, lint,
test, build, or run yet.

Active implementation work appears to live on parallel feature branches (for
example `cursor/scara-project-bootstrap-*`, `cursor/scara-project-scaffold-*`,
`cursor/scara-robot-v1-*`), not on `main`. If you need the real project, inspect
those branches; do not assume `main` contains runnable code.

### Baseline toolchain available in the VM

The Cloud Agent VM ships with these preinstalled (no install step required):

- Node `v22.14.0`, npm `10.9.7`, pnpm `10.33.3`, yarn `1.22.22`
- Python `3.12.3`, pip `24.0` (`uv` is **not** installed)
- Go `1.22.2`, Rust/Cargo `1.83.0`, Java (OpenJDK) `21`
- gcc `13.3.0`, cmake `3.28.3`
- Docker is **not** installed

### When real code lands on this branch

The startup update script is intentionally a guarded, idempotent installer that
runs the matching package manager **only if** a known manifest is present
(`package.json` → install via the detected JS package manager,
`requirements.txt`/`pyproject.toml` → pip). When you introduce a concrete stack,
update the startup update script to match the chosen toolchain and replace this
section with real lint/test/build/run instructions.
