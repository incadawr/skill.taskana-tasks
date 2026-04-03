# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**skill.taskana-tasks** — Taskana CLI + Claude Code skill. Fork of skill.asana-tasks for Taskana-only use.
Repo: https://github.com/incadawr/skill.taskana-tasks
Current version: see `VERSION` file (bump both `VERSION` and `cli/taskana_cli.py:VERSION` on every release).

## Structure

```
cli/taskana_cli.py          ← Python CLI, zero dependencies (stdlib only)
skill/taskana-tasks.md      ← Claude Code skill (activation flow, CLI reference, workflow rules)
install.sh                  ← Installs CLI + skill to ~/.local/bin and ~/.claude/skills
CHANGELOG.md                ← Version history (update on every release!)
VERSION                     ← Version file (used by auto-update)
```

## Architecture — 4 layers

1. **CLI** (`cli/taskana_cli.py`) — generic CRUD for Taskana API, no project knowledge
2. **Skill** (`skill/taskana-tasks.md`) — workflow logic for Claude, reads project config
3. **Project config** (`.claude-team/taskana.json`) — committed to user's repo, binds to project(s)
4. **Personal tokens** — `~/.config/taskana/token` (default) + `~/.config/taskana/tokens/<target>` (per-target)

## Key differences from skill.asana-tasks

- Hardcoded base URL: `https://taskana.tgai.app/api/1.0`
- Token: `~/.config/taskana/token` (not asana)
- Config: `.claude-team/taskana.json` (not asana.json)
- CLI binary: `taskana-cli` (not asana-cli)
- `is_taskana()` always returns True
- `task_limit()` always returns 500

## Release workflow

**Every release must:**
1. Bump `VERSION` in `cli/taskana_cli.py` (string constant)
2. Bump `VERSION` file (root, single line)
3. Update `CHANGELOG.md` with entry
4. Syntax check: `python3 -c "import py_compile; py_compile.compile('cli/taskana_cli.py', doraise=True)"`
5. `git add -A && git commit -m "v<version>: <description>" && git push`
6. Test: `taskana-cli update` from another project

**Version naming:**
- Patch (x.y.Z) — bugfix, small change
- Minor (x.Y.0) — new command, feature
- Major (X.0.0) — breaking change, major refactor

## Conventions

- **Language:** Python 3, stdlib only (`urllib`, `json`, `pathlib`) — no pip dependencies
- **Style:** PEP 8, 4 spaces indent
- **CLI output:** Plain text, human-readable, parseable by Claude
- **Config format:** JSON for `taskana.json`, Markdown for `RULES.md`
- **Cross-platform:** macOS, Linux, WSL
- **Error handling:** `api()` calls `sys.exit(1)` on HTTP/network errors. Multi-target loop catches all exceptions.

## Key design rules

- CLI must work standalone (without Claude)
- CLI must have zero external dependencies — only Python stdlib
- Skill must self-bootstrap: detect missing CLI → install, detect missing token → onboard
- Token is never stored in project files
- `start` command auto-assigns task to current user
- `init-write` refuses to overwrite multi-target config
- `--target all` blocked for ID-dependent commands (IDs differ between backends)
- Per-target token takes priority over default token
- Rich text: no `<br>`, no `<p>`, use `\n` for line breaks, `<body>` wrapper required

## Taskana API specifics

Taskana (https://taskana.tgai.app) — Asana-compatible API at `/api/1.0/`.

- `section: null` in memberships for tasks without section (CLI handles via `get_task_section()`)
- No pagination on compat API (use `limit` param on `/projects/:gid/tasks`)
- Search: `/workspaces/:gid/tasks/search?text=` — LIKE-based, limit 100
- Task limit on `/projects/:gid/tasks`: configurable via query param (CLI uses 500)
- Server-side filters: `completed=`, `section=`, `assignee=` on project tasks endpoint
- Custom fields: `/projects/:gid/custom_fields`, `/tasks/:gid/custom_fields`

## Testing

```bash
python3 cli/taskana_cli.py help
python3 cli/taskana_cli.py --version
python3 cli/taskana_cli.py status
python3 cli/taskana_cli.py whoami
python3 cli/taskana_cli.py overview
python3 cli/taskana_cli.py search "test"
```
