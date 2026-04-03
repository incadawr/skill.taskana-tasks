# CLAUDE.md

## Project Overview

**skill.taskana-tasks** — Taskana CLI + Claude Code skill. Fork of skill.asana-tasks for Taskana-only use.
Repo: https://github.com/incadawr/skill.taskana-tasks

## Structure

```
cli/taskana_cli.py          ← Python CLI, zero dependencies (stdlib only)
skill/taskana-tasks.md      ← Claude Code skill
install.sh                  ← Installs CLI + skill
CHANGELOG.md                ← Version history
VERSION                     ← Version file (used by auto-update)
```

## Key differences from skill.asana-tasks

- Hardcoded base URL: `https://taskana.tgai.app/api/1.0`
- Token: `~/.config/taskana/token` (not asana)
- Config: `.claude-team/taskana.json` (not asana.json)
- CLI binary: `taskana-cli` (not asana-cli)
- `is_taskana()` always returns True
- `task_limit()` always returns 500

## Conventions

- **Language:** Python 3, stdlib only — no pip dependencies
- **Config format:** JSON for `taskana.json`
- **Cross-platform:** macOS, Linux, WSL

## Release workflow

1. Bump `VERSION` in `cli/taskana_cli.py` + `VERSION` file
2. Update `CHANGELOG.md`
3. Syntax check: `python3 -c "import py_compile; py_compile.compile('cli/taskana_cli.py', doraise=True)"`
