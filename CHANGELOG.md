# Changelog

## 1.5.0 (2026-10-07)
- Milestones (roadmap; server: Taskana with milestones, task 3765): `milestones [--brief]`, `milestone <id>`,
  `milestone-create`, `milestone-edit`, `milestone-move`, `milestone-activate [--previous planned|done]`,
  `milestone-close [--dropped]`, `milestone-set <task_id>... <id|current|none>`
- `project-status [--state] [--stage] [--next]`: project state, stage and next step
- `create --milestone <id|current>`, `create --owner-task <minutes>` (owner-only work in the owner's inbox)
- `list` / `board --milestone <id|current|none>`; cards show `[milestone]`; `board` now prints task ids
- `show`: milestone and owner-task minutes; `inbox`: owner tasks per project and in the total
- Skill: section "Milestones" - take work from the current milestone, out-of-scope work goes to the backlog,
  owner-only work = `--owner-task`, last task of a milestone -> ask the owner what's next

## 1.4.4 (2026-10-07)
- Review limit: 5 pending review cards per project (override: `reviewLimit` in `.claude-team/taskana.json`)
- `overview` / `list next`: WARNING when the bound project's pending reviews >= limit; `start` exits 2 without `--force`, except tasks in the resume queue (answered / returned)
  (check runs before any write)
- `reviews` / `inbox` show `X/limit` for the bound project
- Skill: section "Review limit" - don't take new feature work at the limit

## 1.4.3 (2026-10-05)
- `move <id> [<section>] [--top | --bottom | --before <id> | --after <id>]`: order tasks inside a column (priority = order,
  top of Next = most important); section optional when only reordering; uses `insert_before` / `insert_after` of addTask
- Skill: rule "take from the top of Next; urgent new task -> `move <id> Next --top`; don't reorder the owner's order without reason"

## 1.4.2 (2026-10-05)
- Skill: review cards (`submit`) are written for the owner - in Russian, 1-3 plain checks with expected result, internal details
  go to `--how`; "nothing to look at, verified by me" cards are explicit
- No project config + no token: say "folder is not bound to a Taskana project" (worktree hint) instead of "No Taskana token found"

## 1.4.1 (2026-10-05)
- Drop the old server (taskana.tgai.app): DEFAULT_BASE_URL is now https://taskana.papabuba.ru/api/1.0
- No project config (.claude-team/taskana.json): whoami/workspaces/projects/users/init use the default server,
  token order tokens/personal -> token -> TASKANA_TOKEN, and print the server to stderr
- `project-create` without a project config refuses unless `--base-url <url>` is passed explicitly (new global flag)

## 1.4.0 (2026-10-04)
- Add structured review: `submit <id> --check ... --how ... [--branch] [--commits] [--minutes]` (moves to Review),
  `reviews [--returned] [--all]`, `accept <id> [--comment]`, `return <id> --comment`
- Add `inbox [--all-projects]` (open questions + reviews waiting for the owner, estimated minutes) and
  `resume [--all]` (tasks the owner answered / returned that nobody picked up, answers inline)
- `start` now also clears the task's resume flag (ignored on older servers)
- Skill: session start = `resume` then `board`; agents `submit` instead of a free-form ПРИЕМКА comment; returned reviews flow
- Requires Taskana with reviews / inbox / resume API (branch feature/3759-3764-3903-review-inbox)

## 1.3.0 (2026-10-04)
- Add dashboards: `dashboard list|show|create|delete`, widgets: `widget add|move|remove|data`
  (all widget types of the Taskana dashboards module; `--section` / `--parent` filters for stage progress and Review column).
  Requires Taskana with dashboards under `/api/1.0` (API-token access)
- `ask` warns (does not fail) when an option has no description or `--context` is missing
- Skill: rule that every option has a description, `--context` = what it blocks + why the recommendation;
  how to assemble a roadmap dashboard

## 1.2.0 (2026-10-04)
- Add blocking questions: `ask`, `questions [--open|--answered|--all-statuses] [--since] [--all]`, `answer`, `withdraw`
  (requires Taskana with the questions API; answer = option and/or comment)
- Add `section-move <name> --before|--after <other>` (uses `POST /projects/:id/sections/insert`)
- Fix `section-delete` and other bodiless calls failing with 400 "Body cannot be empty": no JSON Content-Type without a body
- `find_section` prefers an exact name match over a substring match
- Skill: agent flow for blockers (ask instead of comment + move; check `questions --answered` at session start)

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
