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
