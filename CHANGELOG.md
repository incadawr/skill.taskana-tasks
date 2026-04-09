# Changelog

## 1.1.0 (2026-04-09)
- Add attachment support: `attachments`, `download`, `upload` commands
- List attachments on tasks, download by ID, upload files via multipart

## 1.0.1 (2026-04-03)
- Remove multi-target prompt injection from `cmd_overview` (irrelevant in Taskana-only fork)
- Update CLAUDE.md with architecture docs and commands section

## 1.0.0 (2026-04-03)
- Initial release — fork of skill.asana-tasks v1.3.4 for Taskana-only use
- Hardcoded base URL: https://taskana.tgai.app/api/1.0
- Token: ~/.config/taskana/token
- Config: .claude-team/taskana.json
- CLI: taskana-cli
- All features from asana-cli: tasks, sections, custom fields, estimate, comments, search, dependencies, tags
