---
name: taskana-tasks
description: Use when the user asks to check tasks, pick a task, mark tasks done, manage the task board, or asks "what should we work on?" / "что по задачам?" at the start of a session. Also handles Taskana onboarding, project init, and task assignment.
user-invocable: true
---

# Taskana Tasks Skill

## Activation — check environment in order

Run `taskana-cli status` to check everything at once. Then follow the appropriate flow:

### 1. CLI missing?

If `taskana-cli` is not found (`~/.local/bin/taskana-cli`):

```bash
curl -fsSL https://raw.githubusercontent.com/incadawr/skill.taskana-tasks/main/install.sh | bash
```

Tell the user to run this command. Do NOT run it yourself — let the user do it.

### 2. Token missing?

If `~/.config/taskana/token` does not exist and `TASKANA_TOKEN` is not set → **Auth flow**:

1. Tell the developer:
   ```
   Taskana token not found. Let's set it up — takes 30 seconds.

   1. Go to Taskana → Settings → API Tokens
   2. Create a new token
   3. Copy the token and paste it here
   ```
2. Wait for the user to paste the token.
3. Run `taskana-cli auth <token>` — this saves and verifies the token.
4. Continue.

### 3. Project not initialized?

If `.claude-team/taskana.json` does not exist → **Init flow**.

**IMPORTANT: You MUST complete ALL steps below before moving to work mode. Do NOT skip ahead to listing tasks.**

**Step 3a.** Run `taskana-cli workspaces` — list available workspaces.

- If exactly **one** workspace → use it automatically, proceed to 3b.
- If **multiple** → present as numbered list, ask user to pick one.

**Step 3b.** Run `taskana-cli projects <workspace_gid>` — list projects in the chosen workspace.

Present projects as a numbered list. Ask the user to pick a project by number.

**Step 3c.** Run `taskana-cli init-write <workspace_gid> <project_gid>` — creates `.claude-team/taskana.json`.

**Step 3d. STOP and ask about prefixes.** Ask:
> "Do you want to configure task prefixes? These are tags like `[AN]`, `[iOS]`, `[Backend]` used in task names. List the ones you want, or skip."

If yes → read `.claude-team/taskana.json`, add `"prefixes": [...]`, write it back.

**Step 3e. STOP and ask about phase tags.** Ask:
> "Do you want to configure phase tags? These group tasks by roadmap phase (e.g. `P0: Deploy`, `P1: MVP`). List the ones you want, or skip."

If yes → read `.claude-team/taskana.json`, add `"phases": [...]`, write it back.

**Step 3f. STOP and ask about workflow rules.** Ask:
> "Do you want to create workflow rules (.claude-team/RULES.md)? This defines how tasks are prioritized, what to show when you ask 'what to work on?', naming conventions, etc. I can generate a template — want to configure it?"

If yes → ask about their preferences (priority order, limits, naming) and generate `.claude-team/RULES.md`.

**Step 3g. STOP and ask about CLAUDE.md.** Ask:
> "Want me to add a taskana-tasks section to your project's CLAUDE.md? This helps Claude automatically offer to check/close tasks during work."

If yes → append to CLAUDE.md (create if missing):

```markdown
## Tasks

- Task management: Taskana — use `/taskana-tasks` skill or ask "what to work on?"
- After completing work on a task, offer to mark it done via taskana-tasks
- When creating new work items, offer to create a Taskana task
```

**Step 3h.** Tell the user: "Setup complete! Commit `.claude-team/` (and CLAUDE.md if updated) to your repo so the team gets the same config."

**Only after all steps above are done, proceed to work mode.**

### 4. Everything configured → work mode

Read `.claude-team/taskana.json` for project config.
If `.claude-team/RULES.md` exists, read it and follow the workflow rules defined there.
Rules override the defaults below.

## Session start (agents): resume first, then board

```bash
taskana-cli resume          # tasks the owner answered / returned and nobody picked up yet - answers inline
taskana-cli board           # then the whole roadmap
```

`resume` lists tasks whose last blocking question was answered or whose review was returned, with the owner's answer
(option + comment) or the return comment printed inline. **Handle these before taking new work.** Each entry ends with
`taskana-cli start <id>` - running it assigns the task to you, moves it to In Progress and **clears the resume flag**
(other sessions then stop seeing it). `resume --all` covers every project of the workspace.

## Priority = order in the column

**Next is ordered by priority: take the task from the top** (`board` / `list` print tasks in column order). Put a genuinely
urgent new task at the top with `taskana-cli move <id> Next --top`. Don't reorder the owner's order without reason.
Reorder with `move <id> [<section>] [--top | --bottom | --before <id> | --after <id>]` (section optional when staying in it).

## Milestones (этапы) — the roadmap

A project has an ordered list of milestones (the roadmap) and **one current milestone** = the slice being worked on now
(10–25 tasks). The backlog is everything without a milestone and never has to be emptied. Project-level fields: state
(`active|paused|frozen|archived`), stage (`idea|prototype|mvp|beta|released|maintenance`) and a one-line next step.

- **See it:** `taskana-cli milestones` (status + roadmap, `*` = current), `taskana-cli milestone <id>` (goal + tasks).
- **Take work from the current milestone:** `taskana-cli board --milestone current` — the top of Next among them first. A task in
  Next outside the current milestone is taken only when the current one has nothing left for an agent, or the owner says so.
- **New work:** in scope of the current milestone → `create ... --milestone current`; anything else (ideas, found bugs,
  "later") → plain `create` (backlog, no milestone). Don't widen the current slice silently.
- **Owner-only work** (keys, accounts, payments, a design decision with no options to pick, a manual test on a device):
  `create "..." --owner-task <minutes> [--milestone current]` — it goes to the owner's inbox with the minutes. Not for
  questions (use `ask`) and not for acceptance (use `submit`).
- **Last task of the current milestone accepted** → ask the owner with `ask`: close it and which milestone is next
  (options = the next planned ones from `milestones`). Close / activate only on the owner's answer:
  `milestone-close <id>`, `milestone-activate <id>`.
- Creating / reordering / editing milestones and `project-status --stage/--state/--next` change the owner's plan — only when
  the owner asked (e.g. "заведи этапы", migrating a project). Never delete milestones.
- Stages modelled as parent tasks with subtasks (old Bob Universe / anyworld style) are legacy; new projects use milestones.

## Review limit (тормоз долга приёмки)

Лимит открытых карточек приёмки на проект: 5 (переопределение — `reviewLimit` в `.claude-team/taskana.json`).
`reviews` / `inbox` показывают `X/limit`; `overview` и `list next` печатают `WARNING: Review limit reached`, а `start` без `--force`
завершается с кодом 2. **При достигнутом лимите не бери новую фичу.** Можно: работу без приёмки владельцем (ревизия веток,
тесты, доки) или остановиться и сказать владельцу, что приёмка ждёт. Задачи из `resume` (владелец ответил или вернул
карточку) `start` пускает и при лимите — их доделка сокращает долг. `--force` — только по слову владельца.

## Default workflow

### When developer asks "what to work on?" or similar:

```bash
taskana-cli overview
```

Present the results and ask what to pick.

### When starting a task:

```bash
taskana-cli start <id>            # assigns to current user + moves to In Progress
```

After starting, offer to set a time estimate:
> "How long do you estimate this task will take? (e.g. 2, 0.5, 4)"

If the developer gives an estimate:
```bash
taskana-cli estimate <id> <hours>
```

### When completing a task:

Agent work goes through the owner's acceptance: use `taskana-cli submit` (see "Finishing work" below), not `done`.
`done` is for tasks that need no acceptance:

```bash
taskana-cli done <id>             # marks completed + moves to Done
```

### When creating a task:

Use prefixes from `taskana.json` config if defined:

```bash
taskana-cli create "[Prefix] Task name" --notes "details"
```

### Blockers: ask the owner with `ask` (not comment + move)

When you cannot continue without the owner's decision, create a structured **question** instead of a free-text comment
and a manual move to "Waiting Owner". The task parks itself in the project's `Waiting Owner` section (if it exists),
the owner sees the question on the «Вопросы» screen and answers with one click.

```bash
taskana-cli ask <task_id> "Which queue do we use for workers?" \
    --option "A: BullMQ | already in the stack" --option "B: pg-boss" --option "C: own cron" \
    --recommend A --context "Short background: constraints, what you tried, what depends on it" \
    --agent "claude · <session label>"
```

- Give 2-4 concrete options (`KEY: label | description`). **Every option MUST have a description** — what choosing it leads to
  and what it costs (time, risk, lock-in). The owner decides from these lines without opening the code; the CLI warns
  when a description is missing.
- Always `--recommend` one option. **`--context` must say (1) what this question blocks** (which task/stage, what waits
  behind it) **and (2) why you recommend that option.** Keep it short; no repo archaeology.
- One decision = one question. Several open questions on a task are fine.
- Then **move on to another task** — do not wait or poll in a loop.
- Withdraw a question that became irrelevant: `taskana-cli withdraw <qid>`.

**At the start of every session** check for answers before picking work:

```bash
taskana-cli questions --answered --since 1d    # answers since yesterday (or since your last session)
taskana-cli questions                          # still-open questions of this project
```

An answer is a chosen option and/or a free-text comment («B, but without X») — read both. The same answer is also posted to the
task as a comment `ОТВЕТ: <key> — <label>. Комментарий: …`, and the task returns to its previous section automatically
(a task that came from Backlog, or from "Waiting Owner" itself, is lifted to "Next") and is flagged **resume-ready**: it appears
in `taskana-cli resume` with the answer inline until someone runs `taskana-cli start <id>`.
Apply the decision, then continue the task (`taskana-cli start <id>`).

### Finishing work: submit for review with `submit` (not a free-form ПРИЕМКА comment)

When the work is ready for the owner's acceptance, submit a structured **review card**. The task moves to "Review"; the owner
sees the checklist, run instructions and estimated time in the Taskana task page and in the «Мне на решение» screen, and accepts
or returns it with one click.

```bash
taskana-cli submit <task_id> \
    --check "Настройки → новый переключатель «Тёмная тема» виден" --check "После перезагрузки страницы он остаётся включённым" \
    --how "Стенд: http://localhost:5173 (docker compose up -d --build), вход test@taskana.test / testtest. Проверено мной: unit-тесты 42/42" \
    --branch feature/123-toggle --commits a1b2c3,d4e5f6 --minutes 10 \
    --agent "claude · <session label>"
```

**The card is read by the owner, not by a developer.** Write it in Russian (the owner's language), from the owner's point of view:
- `--check` (repeatable, 1-3 items): what the owner does with their hands/eyes and what they should see - one action + expected
  result each, in plain words. No source paths, CLI flags or grep commands when they can be avoided. The first check may say what
  changed for the owner in 1-2 phrases ("Теперь …").
- If there is nothing for the owner to look at (internal/CLI/infra change you already verified), say so plainly:
  `--check "Смотреть нечего: проверено мной - <что именно>. Достаточно принять"`, and `--minutes 1`.
- `--how`: where to look (stand URL, test account, device) plus how YOU verified it (tests, commands, branch details). Internal
  details go here, not into `--check`.
- `--minutes`: the **owner's** time to accept (not yours); the inbox sums it so the owner can plan "I have 90 minutes".
- `--branch` / `--commits`: where the code is (comma separated commits). Submitting again replaces a pending card (new round).
- Do NOT also write a free-form `ПРИЕМКА:` comment - `submit` posts one automatically.
- Do NOT `done` the task yourself; the owner accepts: `taskana-cli accept <id> [--comment]` / `taskana-cli return <id> --comment "..."`.

**A returned review is not a failure**: the task goes back to In Progress, the owner's comment (`ВОЗВРАТ: ...`) is on the task,
and it shows in `taskana-cli resume` (also `taskana-cli reviews --returned`). Fix the points, `start` the task, `submit` again.

What waits for the owner overall: `taskana-cli inbox` (bound project) / `taskana-cli inbox --all-projects`; pending reviews:
`taskana-cli reviews [--all]`.

### Dashboards: assemble a roadmap dashboard for a project

The roadmap itself lives in milestones (see "Milestones" above; the project's «Роадмап» tab in the UI). The dashboard below
is for projects that still keep stages as parent tasks, or for extra charts.

Works with the normal API token (no web session needed). Widgets compute their data live; the owner sees the dashboard in the
project's «Dashboard» view. Typical roadmap dashboard (stages = parent tasks R1..R6 with subtasks, columns = sections):

```bash
taskana-cli dashboard create "Roadmap"                      # bound to the current project; prints the dashboard id
D=<id>
# Stage progress: one widget per stage (parent task id) -> total / completed / incomplete of its subtasks
taskana-cli widget add $D task_count --title "R1 — Foundation" --parent <R1_task_id> --x 0 --y 0 --w 4 --h 2
taskana-cli widget add $D task_count --title "R2 — API"        --parent <R2_task_id> --x 4 --y 0 --w 4 --h 2
# ...one per stage, 3 per row (grid is 12 columns wide)
# Review column: how many tasks wait for acceptance
taskana-cli widget add $D task_count --title "Awaiting review" --section "Review" --x 0 --y 2 --w 4 --h 2
taskana-cli widget add $D task_count --title "Waiting for the owner" --section "Waiting Owner" --x 4 --y 2 --w 4 --h 2
# Overall distribution and momentum
taskana-cli widget add $D tasks_by_section --title "Tasks by column" --x 0 --y 4 --w 6 --h 4
taskana-cli widget add $D completion_over_time --title "Completed, 30 days" --config '{"days":30}' --x 6 --y 4 --w 6 --h 4
taskana-cli dashboard show $D                               # check the result; `widget data <id>` prints a widget's numbers
```

- Widget types: `task_count`, `tasks_by_section`, `tasks_by_assignee`, `tasks_by_priority`, `completion_over_time`,
  `upcoming_deadlines`, `recently_completed`. Filters via `--section`, `--parent`, or `--config` JSON
  (`sectionId`, `parentTaskId`, `assigneeId`, `includeCompleted`, `days`, `limit`).
- Rearrange with `widget move <id> --x --y --w --h`; remove with `widget remove <id>`.
- **Open questions are not a widget type yet.** They are shown in the project's Overview («Открытые вопросы») and on the
  «Вопросы» screen; the "Waiting for the owner" count widget above is the dashboard-level proxy.
- Do not create a second dashboard when one exists: `taskana-cli dashboard list` first.

## CLI reference

```
Setup:
  taskana-cli auth <token> [--target <name>]   Save token (per-target with --target)
  taskana-cli init                             List workspaces & projects
  taskana-cli init-write <ws_gid> <proj_gid>   Write .claude-team/taskana.json
  taskana-cli status                           Check configuration
  taskana-cli update                           Update CLI + skill
  taskana-cli whoami                           Current user info
  taskana-cli workspaces                       List workspaces
  taskana-cli projects [ws_gid]                List projects
  taskana-cli users [ws_gid]                   List workspace users

Tasks:
  taskana-cli list [section]                   List tasks (filter by section)
  taskana-cli show <id>                        Task details
  taskana-cli my                               My assigned tasks
  taskana-cli search <query>                   Search by name
  taskana-cli overview                         Dashboard: my + todo + review + progress
  taskana-cli board [--milestone <id|current|none>]  Board view (by section); list takes --milestone too
  taskana-cli create <name> [options]          Create task
      --section <name>                         Section (default: Backlog)
      --notes <text>                           Description
      --due <YYYY-MM-DD>                       Due date
      --assign <user>                          Assign ("me", name, email)
      --watch <user>                           Add watcher (repeatable)
      --milestone <id|current>                 Into a milestone (default: backlog, no milestone)
      --owner-task <minutes>                   Owner-only work, shows in the owner's inbox with the minutes
  taskana-cli done <id>                        Complete + move to Done
  taskana-cli start <id>                       Assign to me + In Progress
  taskana-cli move <id> [<section>] [--top|--bottom|--before <id>|--after <id>]
                                               Move to section / reorder inside the column (order = priority)
  taskana-cli assign <id> <user>               Assign ("me", name, email)
  taskana-cli unassign <id>                    Remove assignee
  taskana-cli due <id> <date>                  Set due date (YYYY-MM-DD / "clear")
  taskana-cli rename <id> <name>               Rename task
  taskana-cli reopen <id>                      Reopen completed task
  taskana-cli description <id> <text>          Update description (markdown → rich text)
  taskana-cli comment <id> <text> [--pin]      Add comment (--pin to pin)
  taskana-cli comments <id>                    List comments on task
  taskana-cli history <id>                     Full activity log (all events)

Milestones and project status:
  taskana-cli milestones [--brief]             Project status + roadmap (* = current), progress done/total
  taskana-cli milestone <id>                   Milestone: goal, done-when, tasks
  taskana-cli milestone-create <name> [--goal X] [--done-when X] [--target YYYY-MM-DD] [--before|--after <id>] [--activate]
  taskana-cli milestone-edit <id> [--name X] [--goal X] [--done-when X] [--target YYYY-MM-DD|clear]
  taskana-cli milestone-move <id> --before <id> | --after <id>
  taskana-cli milestone-activate <id> [--previous planned|done]
  taskana-cli milestone-close <id> [--dropped]
  taskana-cli milestone-set <task_id>... <id|current|none>
  taskana-cli project-status [--state X] [--stage X|none] [--next "..."]

Subtasks:
  taskana-cli subtasks <id>                    List subtasks
  taskana-cli subtask <id> <name>              Create subtask

Watchers:
  taskana-cli watch <id> [user]                Add watcher ("me" default)
  taskana-cli unwatch <id> [user]              Remove watcher

Tags:
  taskana-cli tags <id>                        List tags
  taskana-cli tag <id> <name>                  Add tag (creates if needed)
  taskana-cli untag <id> <name>                Remove tag

Attachments:
  taskana-cli attachments <id>                 List attachments on task
  taskana-cli download <attachment_id> [--output path]  Download attachment
  taskana-cli upload <id> <file_path>          Upload file as attachment

Dependencies:
  taskana-cli deps <id>                        Blocked by (dependencies)
  taskana-cli dep <id> <dep_id>                Add dependency
  taskana-cli undep <id> <dep_id>              Remove dependency
  taskana-cli blocks <id>                      Blocking (dependents)
  taskana-cli block <id> <dep_id>              Add dependent
  taskana-cli unblock <id> <dep_id>            Remove dependent

Custom fields:
  taskana-cli custom-fields                    List project fields
  taskana-cli custom-field-create <name> <type>  Create (text/number/enum/date)
  taskana-cli task-fields <id>                 Field values on task
  taskana-cli task-field-set <id> <fld> <val>  Set field value
  taskana-cli estimate <id> <hours>            Set estimate (auto-creates field)

Sections:
  taskana-cli sections                         List sections
  taskana-cli section-create <name>            Create section
  taskana-cli section-rename <old> <new>       Rename section
  taskana-cli section-delete <name>            Delete section
  taskana-cli section-move <name> --before|--after <other>  Reorder section

Questions (blockers for the owner):
  taskana-cli ask <id> "question" --option "A: label" --option "B: label | note"
        [--recommend B] [--context "..."] [--no-free-text] [--agent <label>]   Ask; task parks in "Waiting Owner"
  taskana-cli questions [--open|--answered|--all-statuses] [--since <iso|2h|1d>] [--all]
                                               List questions of the bound project (--all: whole workspace)
  taskana-cli answer <qid> [<key>] [--comment "..."]   Answer: option and/or comment
  taskana-cli withdraw <qid>                   Withdraw an open question

Review / inbox / resume:
  taskana-cli submit <id> --check "..." [--check "..."] --how "..." [--branch X] [--commits a,b] [--minutes N] [--agent <label>]
                                               Submit for review (moves to Review)
  taskana-cli reviews [--returned] [--all]     Pending reviews (--returned: returned, not yet picked up)
  taskana-cli accept <id> [--comment "..."]    Accept (owner): task -> Done
  taskana-cli return <id> --comment "..."      Return (owner): task -> In Progress, comment required
  taskana-cli inbox [--all-projects]           Questions + reviews waiting for the owner, total minutes
  taskana-cli resume [--all]                   Answered/returned tasks nobody picked up yet (answers inline)
  taskana-cli start <id> [--force]             ... also clears the resume flag; exit 2 if the review limit is reached

Dashboards (API token is enough):
  taskana-cli dashboard list [--all]           Dashboards of the project (--all: workspace)
  taskana-cli dashboard show <id>              Dashboard with widgets
  taskana-cli dashboard create <name> [--workspace-wide] | delete <id>
  taskana-cli widget add <dashboard_id> <type> [--title T] [--section <name>] [--parent <task_id>]
        [--config '{"days":14}'] [--x N] [--y N] [--w N] [--h N]
  taskana-cli widget move <id> [--x N] [--y N] [--w N] [--h N]   |   widget remove <id>   |   widget data <id>

Project:
  taskana-cli members                          List members
  taskana-cli project-create <name> [--workspace <gid>] [--team <gid>]

Global flags:
  --target <name>    Use specific backend
  --target all       Execute on all backends
  --project <gid>    Override projectId (work with different project)
```

## Important

- Always use the CLI tool, not raw curl, for Taskana operations.
- The CLI reads `.claude-team/taskana.json` from the project and `~/.config/taskana/token` for auth (without a project config: `tokens/personal` -> `token` -> `TASKANA_TOKEN`, default server taskana.papabuba.ru; `project-create` needs `--base-url`).
- Task IDs are Taskana GIDs (numbers).
- `start` auto-assigns the task to the current developer.
- Do NOT create config files for the user during init — use `taskana-cli init-write` instead.
