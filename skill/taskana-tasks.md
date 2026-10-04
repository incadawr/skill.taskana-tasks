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
task as a comment `ОТВЕТ: <key> — <label>. Комментарий: …`, and the task returns to its previous section automatically.
Apply the decision, then continue the task (`taskana-cli start <id>`).

### Dashboards: assemble a roadmap dashboard for a project

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
  taskana-cli board                            Board view (by section)
  taskana-cli create <name> [options]          Create task
      --section <name>                         Section (default: Backlog)
      --notes <text>                           Description
      --due <YYYY-MM-DD>                       Due date
      --assign <user>                          Assign ("me", name, email)
      --watch <user>                           Add watcher (repeatable)
  taskana-cli done <id>                        Complete + move to Done
  taskana-cli start <id>                       Assign to me + In Progress
  taskana-cli move <id> <section>              Move to section
  taskana-cli assign <id> <user>               Assign ("me", name, email)
  taskana-cli unassign <id>                    Remove assignee
  taskana-cli due <id> <date>                  Set due date (YYYY-MM-DD / "clear")
  taskana-cli rename <id> <name>               Rename task
  taskana-cli reopen <id>                      Reopen completed task
  taskana-cli description <id> <text>          Update description (markdown → rich text)
  taskana-cli comment <id> <text> [--pin]      Add comment (--pin to pin)
  taskana-cli comments <id>                    List comments on task
  taskana-cli history <id>                     Full activity log (all events)

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
- The CLI reads `.claude-team/taskana.json` from the project and `~/.config/taskana/token` for auth.
- Task IDs are Taskana GIDs (numbers).
- `start` auto-assigns the task to the current developer.
- Do NOT create config files for the user during init — use `taskana-cli init-write` instead.
