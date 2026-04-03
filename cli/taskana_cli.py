#!/usr/bin/env python3
"""
taskana-cli — Taskana CLI for Claude Code skill.

Reads config from:
  1. .claude-team/taskana.json  (project binding — projectId, workspaceId)
  2. ~/.config/taskana/token    (personal access token)
  3. TASKANA_TOKEN env var      (fallback)

Usage:

  Setup:
    taskana-cli auth <token> [--target <name>]   Save token (per-target with --target)
    taskana-cli init                             List workspaces & projects for init
    taskana-cli init-write <ws_gid> <proj_gid>   Write .claude-team/taskana.json
    taskana-cli status                           Check configuration status
    taskana-cli update                           Update CLI + skill from GitHub
    taskana-cli whoami                           Show current user
    taskana-cli workspaces                       List available workspaces
    taskana-cli projects [ws_gid]                List projects in workspace
    taskana-cli users [ws_gid]                   List workspace users

  Tasks:
    taskana-cli list [section]                   List tasks (optionally filter by section name)
    taskana-cli show <id>                        Task details (notes, deps, tags, dates)
    taskana-cli my                               My assigned tasks
    taskana-cli search <query>                   Search tasks by name
    taskana-cli overview                         Dashboard: my + todo + review + in progress
    taskana-cli board                            Compact board view (grouped by section)
    taskana-cli create <name> [options]          Create task
        --section <name>                         Place in section (default: Backlog)
        --notes <text>                           Task description
        --due <YYYY-MM-DD>                       Due date
        --assign <user>                          Assign ("me", name, or email)
        --watch <user>                           Add watcher (repeatable)
    taskana-cli done <id>                        Mark completed + move to Done
    taskana-cli start <id>                       Assign to me + move to In Progress
    taskana-cli move <id> <section>              Move task to section
    taskana-cli assign <id> <user>               Assign ("me", name, or email)
    taskana-cli unassign <id>                    Remove assignee
    taskana-cli due <id> <date>                  Set due date (YYYY-MM-DD or "clear")
    taskana-cli rename <id> <name>               Rename task
    taskana-cli reopen <id>                      Reopen completed task
    taskana-cli description <id> <text>          Update description (markdown → rich text)
    taskana-cli comment <id> <text> [--pin]      Add comment (--pin to pin it)
    taskana-cli comments <id>                    List comments on task
    taskana-cli history <id>                     Show task activity log (all events)

  Subtasks:
    taskana-cli subtasks <id>                    List subtasks
    taskana-cli subtask <id> <name>              Create subtask

  Watchers:
    taskana-cli watch <id> [user]                Add watcher ("me" by default)
    taskana-cli unwatch <id> [user]              Remove watcher

  Tags:
    taskana-cli tags <id>                        List tags on task
    taskana-cli tag <id> <name>                  Add tag (creates if not found)
    taskana-cli untag <id> <name>                Remove tag

  Dependencies:
    taskana-cli deps <id>                        List dependencies (blocked by)
    taskana-cli dep <id> <dep_id>                Add dependency
    taskana-cli undep <id> <dep_id>              Remove dependency
    taskana-cli blocks <id>                      List dependents (blocking)
    taskana-cli block <id> <dep_id>              Add dependent
    taskana-cli unblock <id> <dep_id>            Remove dependent

  Custom fields:
    taskana-cli custom-fields                    List project custom fields
    taskana-cli custom-field-create <name> <type>  Create field (text, number, enum, date)
    taskana-cli task-fields <id>                 List custom field values on task
    taskana-cli task-field-set <id> <fld> <val>  Set custom field value
    taskana-cli estimate <id> <hours>            Set estimate (auto-creates field if missing)

  Sections:
    taskana-cli sections                         List sections
    taskana-cli section-create <name>            Create section
    taskana-cli section-rename <old> <new>       Rename section
    taskana-cli section-delete <name>            Delete section

  Project:
    taskana-cli members                          List project members
    taskana-cli project-create <name> [--workspace <gid>] [--team <gid>]

  Multi-target:
    taskana-cli add-target <name> <url> [--project <gid>] [--token <tok>]
    taskana-cli set-target-project <target> <gid>
    taskana-cli dismiss-multitarget              Don't ask about multi-target again

Global flags:
  --target <name>               Use specific target (from taskana.json targets)
  --target all                  Execute on all targets (dual write)
  --project <gid>               Override projectId (work with a different project)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

VERSION = "1.0.0"
DEFAULT_BASE_URL = "https://taskana.tgai.app/api/1.0"


def find_project_root():
    """Walk up from cwd to find .claude-team/taskana.json."""
    path = Path.cwd()
    while path != path.parent:
        config = path / ".claude-team" / "taskana.json"
        if config.exists():
            return path, config
        path = path.parent
    return None, None


def load_raw_config():
    """Load raw JSON from .claude-team/taskana.json."""
    _, config_path = find_project_root()
    if not config_path:
        return None
    with open(config_path) as f:
        return json.load(f)


def resolve_targets(raw_config, target_name=None):
    """Resolve config into list of (name, config) tuples based on target selection.

    Supports two config formats:
    - Legacy: { projectId, workspaceId, ... }
    - Multi:  { targets: { main: {...}, dev: {...} }, default: "main" }

    Returns list of (target_name, target_config) tuples.
    """
    if not raw_config:
        print("No .claude-team/taskana.json found in current or parent directories.")
        print("See: https://github.com/destruction-studio/skill.taskana-tasks#project-setup")
        sys.exit(1)

    # Legacy format (no targets key)
    if "targets" not in raw_config:
        base_url = raw_config.get("baseUrl", DEFAULT_BASE_URL)
        return [("default", {**raw_config, "baseUrl": base_url})]

    # Multi-target format
    targets = raw_config["targets"]
    default = raw_config.get("default", next(iter(targets)))

    if target_name == "all":
        return [(name, {**cfg, "baseUrl": cfg.get("baseUrl", DEFAULT_BASE_URL)})
                for name, cfg in targets.items()]

    name = target_name or default
    if name not in targets:
        print(f"Target '{name}' not found. Available: {', '.join(targets.keys())}", file=sys.stderr)
        sys.exit(1)

    cfg = targets[name]
    return [(name, {**cfg, "baseUrl": cfg.get("baseUrl", DEFAULT_BASE_URL)})]


def load_config(target_name=None):
    """Load config for default or specified target. Returns first target config."""
    raw = load_raw_config()
    resolved = resolve_targets(raw, target_name)
    return resolved[0][1]


def load_token(target_name=None):
    """Load token. Per-target file takes priority, then default file, then env var."""
    config_dir = Path.home() / ".config" / "taskana"

    # Per-target token file (highest priority for named targets)
    if target_name and target_name not in ("default", "all"):
        target_path = config_dir / "tokens" / target_name
        if target_path.exists():
            return target_path.read_text().strip()

    # Default token file
    token_path = config_dir / "token"
    if token_path.exists():
        return token_path.read_text().strip()

    # Env var as last resort
    token = os.environ.get("TASKANA_TOKEN")
    if token:
        return token.strip()

    return None


ACTIVE_BASE_URL = DEFAULT_BASE_URL


def is_taskana():
    """Always True — this is the Taskana-only CLI."""
    return True


def task_limit():
    """Taskana supports up to 500 per request."""
    return 500


def api(method, path, token, body=None, base_url=None):
    """Make API request. Auto-paginates list responses."""
    resolved_base = base_url or ACTIVE_BASE_URL
    url = f"{resolved_base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            items = result.get("data")

            # Auto-paginate list responses
            next_page = result.get("next_page")
            if next_page and isinstance(items, list):
                while next_page:
                    next_url = f"{resolved_base}{next_page['path']}"
                    req2 = urllib.request.Request(next_url, headers=headers, method="GET")
                    with urllib.request.urlopen(req2) as resp2:
                        result2 = json.loads(resp2.read().decode())
                        items.extend(result2.get("data", []))
                        next_page = result2.get("next_page")

            return items
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            errors = json.loads(error_body).get("errors", [])
            msg = errors[0]["message"] if errors else error_body
        except (json.JSONDecodeError, IndexError, KeyError):
            msg = error_body
        print(f"API Error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except (ConnectionError, OSError) as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_task_section(task):
    """Safely extract section info from task memberships. Handles None sections."""
    memberships = task.get("memberships") or [{}]
    if not memberships:
        return {}
    m = memberships[0] or {}
    return m.get("section") or {}


def get_sections(token, project_id):
    """Get project sections."""
    return api("GET", f"/projects/{project_id}/sections?opt_fields=name", token)


def find_section(token, project_id, name):
    """Find section by name (fuzzy match)."""
    sections = get_sections(token, project_id)
    lower = name.lower().replace(" ", "")
    for s in sections:
        if lower in s["name"].lower().replace(" ", ""):
            return s
    names = ", ".join(s["name"] for s in sections)
    print(f'Section "{name}" not found. Available: {names}', file=sys.stderr)
    sys.exit(1)


def get_me(token):
    """Get current user."""
    return api("GET", "/users/me?opt_fields=name,email,gid", token)


# --- Commands ---

def cmd_list(token, config, section_filter=None):
    project_id = config["projectId"]
    fields = "name,completed,assignee.name,memberships.section.name,tags.name"
    url = f"/projects/{project_id}/tasks?opt_fields={fields}&limit={task_limit()}"

    section = None
    if section_filter:
        section = find_section(token, project_id, section_filter)
        if is_taskana():
            url += f"&section={section['gid']}"

    tasks = api("GET", url, token)

    if section_filter:
        tasks = [t for t in tasks
                 if any(((m or {}).get("section") or {}).get("gid") == section["gid"]
                        for m in t.get("memberships", []))]

    # Group by section
    grouped = {}
    for t in tasks:
        sec = get_task_section(t).get("name", "No section")
        grouped.setdefault(sec, []).append(t)

    for sec, sec_tasks in grouped.items():
        if not section_filter:
            print(f"\n── {sec} ──")
        for t in sec_tasks:
            done = "✓" if t.get("completed") else " "
            assignee = t.get("assignee", {})
            assignee_name = f"  @{assignee['name']}" if assignee else ""
            print(f"[{done}] {t['gid']}  {t['name']}{assignee_name}")

    print(f"\nTotal: {len(tasks)} tasks")


def cmd_my(token, config):
    project_id = config["projectId"]
    me = get_me(token)
    fields = "name,completed,assignee.gid,memberships.section.name"
    url = f"/projects/{project_id}/tasks?opt_fields={fields}&limit={task_limit()}"
    if is_taskana():
        url += f"&assignee={me['gid']}"
    tasks = api("GET", url, token)

    my_tasks = [t for t in tasks
                if t.get("assignee") and t["assignee"].get("gid") == me["gid"]]

    if not my_tasks:
        print("No tasks assigned to you.")
        return

    for t in my_tasks:
        done = "✓" if t.get("completed") else " "
        sec = get_task_section(t).get("name", "")
        print(f"[{done}] {t['gid']}  {t['name']}  ({sec})")

    print(f"\nTotal: {len(my_tasks)} tasks")


def cmd_show(token, task_id):
    fields = "name,completed,notes,assignee.name,memberships.section.name,tags.name,created_at,modified_at,due_on,dependencies.name,dependents.name"
    t = api("GET", f"/tasks/{task_id}?opt_fields={fields}", token)

    print(f"Task: {t['name']}")
    print(f"ID: {t['gid']}")
    print(f"Status: {'Done' if t.get('completed') else 'Open'}")
    sec = get_task_section(t).get("name", "-")
    print(f"Section: {sec}")
    assignee = t.get("assignee")
    print(f"Assignee: {assignee['name'] if assignee else '-'}")
    tags = ", ".join(tag["name"] for tag in t.get("tags", [])) or "-"
    print(f"Tags: {tags}")
    if t.get("due_on"):
        print(f"Due: {t['due_on']}")
    print(f"Created: {(t.get('created_at') or '')[:10]}")
    print(f"Modified: {(t.get('modified_at') or '')[:10]}")
    deps = t.get("dependencies", [])
    if deps:
        print(f"Blocked by: {', '.join(d.get('name', d['gid']) for d in deps)}")
    dependents = t.get("dependents", [])
    if dependents:
        print(f"Blocking: {', '.join(d.get('name', d['gid']) for d in dependents)}")
    if t.get("notes"):
        print(f"\nNotes:\n{t['notes']}")


def cmd_done(token, config, task_id):
    project_id = config["projectId"]
    api("PUT", f"/tasks/{task_id}", token, {"data": {"completed": True}})
    sections = get_sections(token, project_id)
    done_sec = next((s for s in sections if "done" in s["name"].lower()), None)
    if done_sec:
        api("POST", f"/sections/{done_sec['gid']}/addTask", token, {"data": {"task": task_id}})
    print(f"Task {task_id} marked as done")


def cmd_start(token, config, task_id):
    project_id = config["projectId"]
    me = get_me(token)

    # Assign to current user
    api("PUT", f"/tasks/{task_id}", token, {"data": {"assignee": me["gid"]}})

    # Move to In Progress
    section = find_section(token, project_id, "in progress")
    api("POST", f"/sections/{section['gid']}/addTask", token, {"data": {"task": task_id}})

    print(f"Task {task_id} assigned to {me['name']}, moved to \"{section['name']}\"")


def cmd_move(token, config, task_id, section_name):
    project_id = config["projectId"]
    section = find_section(token, project_id, section_name)
    api("POST", f"/sections/{section['gid']}/addTask", token, {"data": {"task": task_id}})
    print(f"Task {task_id} moved to \"{section['name']}\"")


def cmd_create(token, config, name, section_name=None, notes=None, due=None,
               assign=None, watch=None):
    project_id = config["projectId"]
    sections = get_sections(token, project_id)

    section_gid = None
    if section_name:
        sec = find_section(token, project_id, section_name)
        section_gid = sec["gid"]
    else:
        backlog = next((s for s in sections if "backlog" in s["name"].lower()), None)
        if backlog:
            section_gid = backlog["gid"]

    body = {
        "data": {
            "name": name,
            "projects": [project_id],
        }
    }
    if notes:
        body["data"]["notes"] = notes
    if due:
        body["data"]["due_on"] = due
    if assign:
        user = resolve_user(token, config, assign)
        body["data"]["assignee"] = user["gid"]
    if section_gid:
        body["data"]["memberships"] = [{"project": project_id, "section": section_gid}]

    task = api("POST", "/tasks", token, body)
    print(f"Created: {task['gid']}  {task['name']}")

    if watch:
        for w in watch:
            user = resolve_user(token, config, w)
            api("POST", f"/tasks/{task['gid']}/addFollowers", token,
                {"data": {"followers": [user["gid"]]}})
            print(f"  Added watcher: {user['name']}")


def cmd_sections(token, config):
    sections = get_sections(token, config["projectId"])
    for s in sections:
        print(f"{s['gid']}  {s['name']}")


def cmd_section_create(token, config, name):
    project_id = config["projectId"]
    section = api("POST", f"/projects/{project_id}/sections", token,
                   {"data": {"name": name}})
    print(f"Created section: {section['gid']}  {section['name']}")


def cmd_section_rename(token, config, section_name, new_name):
    project_id = config["projectId"]
    section = find_section(token, project_id, section_name)
    api("PUT", f"/sections/{section['gid']}", token,
        {"data": {"name": new_name}})
    print(f"Section \"{section['name']}\" renamed to \"{new_name}\"")


def cmd_section_delete(token, config, section_name):
    project_id = config["projectId"]
    section = find_section(token, project_id, section_name)
    api("DELETE", f"/sections/{section['gid']}", token)
    print(f"Section \"{section['name']}\" deleted")


def cmd_search(token, config, query):
    workspace_id = config.get("workspaceId")
    project_id = config.get("projectId")
    matched = None

    if workspace_id and is_taskana():
        # Taskana: server-side search
        import urllib.parse
        encoded = urllib.parse.quote(query)
        search_url = f"/workspaces/{workspace_id}/tasks/search?text={encoded}&opt_fields=name,completed,memberships.section.name,assignee.name&limit=100"
        matched = api("GET", search_url, token)

    if matched is None and project_id:
        # Fallback: client-side filter
        fields = "name,completed,memberships.section.name,assignee.name"
        tasks = api("GET", f"/projects/{project_id}/tasks?opt_fields={fields}&limit={task_limit()}", token)
        lower = query.lower()
        matched = [t for t in tasks if lower in t["name"].lower()]

    if not matched:
        print("No tasks found")
        return

    for t in matched:
        done = "✓" if t.get("completed") else " "
        sec = get_task_section(t).get("name", "")
        print(f"[{done}] {t['gid']}  {t['name']}  ({sec})")

    print(f"\nFound: {len(matched)}")


def cmd_whoami(token):
    me = get_me(token)
    print(f"Name: {me['name']}")
    print(f"Email: {me.get('email', '-')}")
    print(f"GID: {me['gid']}")


def cmd_auth(token_value=None, target_name=None):
    """Save token. --target saves to per-target file, otherwise default."""
    config_dir = Path.home() / ".config" / "taskana"

    if target_name:
        token_dir = config_dir / "tokens"
        token_path = token_dir / target_name
    else:
        token_dir = config_dir
        token_path = token_dir / "token"

    if not token_value:
        print("No token provided.")
        print("Usage: taskana-cli auth <token> [--target <name>]")
        print("")
        print("To create a token:")
        print("  1. Go to Taskana → Settings → API Tokens")
        print("  2. Create a new token")
        print("  3. Copy the token")
        print("  4. Run: taskana-cli auth <your-token>")
        sys.exit(1)

    token_dir.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token_value.strip() + "\n")
    try:
        token_path.chmod(0o600)
    except OSError:
        pass

    # Verify token works — resolve base URL for target if possible
    if target_name:
        raw = load_raw_config()
        if raw and "targets" in raw and target_name in raw["targets"]:
            global ACTIVE_BASE_URL
            ACTIVE_BASE_URL = raw["targets"][target_name].get("baseUrl", DEFAULT_BASE_URL)
    me = get_me(token_value.strip())
    print(f"Token saved to {token_path}")
    print(f"Authenticated as: {me['name']} ({me.get('email', '-')})")


def cmd_workspaces(token):
    """List workspaces available to current user."""
    workspaces = api("GET", "/workspaces?opt_fields=name,gid", token)
    for ws in workspaces:
        print(f"{ws['gid']}  {ws['name']}")
    return workspaces


def cmd_projects(token, workspace_gid=None):
    """List projects in workspace."""
    if not workspace_gid:
        workspaces = api("GET", "/workspaces?opt_fields=name,gid", token)
        if len(workspaces) == 1:
            workspace_gid = workspaces[0]["gid"]
            print(f"Workspace: {workspaces[0]['name']}\n")
        else:
            print("Multiple workspaces found. Specify one:")
            for ws in workspaces:
                print(f"  {ws['gid']}  {ws['name']}")
            print("\nUsage: taskana-cli projects <workspace_gid>")
            return []

    projects = api(
        "GET",
        f"/workspaces/{workspace_gid}/projects?opt_fields=name,gid,archived&limit=100",
        token,
    )
    active = [p for p in projects if not p.get("archived")]
    for p in active:
        print(f"{p['gid']}  {p['name']}")
    print(f"\nTotal: {len(active)} projects")
    return active


def cmd_overview(token, config):
    """Single API call dashboard: my tasks, review, todo, in progress."""
    # Multi-target hint
    raw = load_raw_config()
    if raw and "targets" not in raw:
        root, _ = find_project_root()
        if root and not (root / ".claude-team" / ".multitarget-offered").exists():
            print("FOR CLAUDE: Single-target config detected. You MUST ask the user: 'Want to add another backend (e.g. Taskana) for dual-write?' Do NOT dismiss or skip without asking. Wait for user response.\n")

    project_id = config["projectId"]
    me = get_me(token)
    fields = "name,completed,assignee.gid,assignee.name,memberships.section.name,memberships.section.gid,due_on"
    url = f"/projects/{project_id}/tasks?opt_fields={fields}&limit={task_limit()}"
    if is_taskana():
        url += "&completed=false"
    tasks = api("GET", url, token)

    # Categorize
    my_tasks = []
    by_section = {}
    for t in tasks:
        if t.get("completed"):
            continue
        sec_name = get_task_section(t).get("name", "")
        by_section.setdefault(sec_name, []).append(t)
        if t.get("assignee") and t["assignee"].get("gid") == me["gid"]:
            my_tasks.append(t)

    def print_tasks(task_list, show_section=False):
        for t in task_list:
            parts = []
            if show_section:
                sec = get_task_section(t).get("name", "")
                if sec:
                    parts.append(sec)
            assignee = t.get("assignee")
            if assignee:
                parts.append(f"@{assignee['name']}")
            if t.get("due_on"):
                parts.append(f"due:{t['due_on']}")
            extra = f"  ({', '.join(parts)})" if parts else ""
            print(f"  [ ] {t['gid']}  {t['name']}{extra}")

    # My tasks (show section since they can be in different sections)
    print(f"\n── My Tasks ({len(my_tasks)}) ──")
    if my_tasks:
        print_tasks(my_tasks, show_section=True)
    else:
        print("  (none)")

    # Review / Test
    review_keys = [k for k in by_section if "review" in k.lower() or "test" in k.lower()]
    review_tasks = []
    for k in review_keys:
        review_tasks.extend(by_section[k])
    print(f"\n── Review / Test ({len(review_tasks)}) ──")
    if review_tasks:
        print_tasks(review_tasks)
    else:
        print("  (none)")

    # TODO
    todo_keys = [k for k in by_section if "todo" in k.lower().replace(" ", "")]
    todo_tasks = []
    for k in todo_keys:
        todo_tasks.extend(by_section[k])
    print(f"\n── TODO ({len(todo_tasks)}) ──")
    if todo_tasks:
        print_tasks(todo_tasks)
    else:
        print("  (none)")

    # In Progress
    progress_keys = [k for k in by_section if "progress" in k.lower()]
    progress_tasks = []
    for k in progress_keys:
        progress_tasks.extend(by_section[k])
    print(f"\n── In Progress ({len(progress_tasks)}) ──")
    if progress_tasks:
        print_tasks(progress_tasks)
    else:
        print("  (none)")

    # Bugs
    bug_keys = [k for k in by_section if "bug" in k.lower()]
    bug_tasks = []
    for k in bug_keys:
        bug_tasks.extend(by_section[k])
    if bug_tasks:
        print(f"\n── Bugs ({len(bug_tasks)}) ──")
        print_tasks(bug_tasks)


def cmd_users(token, workspace_gid=None):
    """List users in workspace."""
    if not workspace_gid:
        workspaces = api("GET", "/workspaces?opt_fields=name,gid", token)
        if len(workspaces) == 1:
            workspace_gid = workspaces[0]["gid"]
            print(f"Workspace: {workspaces[0]['name']}\n")
        else:
            print("Multiple workspaces found. Specify one:")
            for ws in workspaces:
                print(f"  {ws['gid']}  {ws['name']}")
            print("\nUsage: taskana-cli users <workspace_gid>")
            return
    users = api("GET",
                f"/workspaces/{workspace_gid}/users?opt_fields=name,email&limit=100",
                token)
    for u in users:
        print(f"  {u['gid']}  {u['name']} ({u.get('email', '-')})")
    print(f"\nTotal: {len(users)} users")


def cmd_project_create(token, name, workspace_gid=None, team_gid=None):
    """Create a new project in workspace."""
    if not workspace_gid:
        workspaces = api("GET", "/workspaces?opt_fields=name,gid,is_organization", token)
        if len(workspaces) == 1:
            workspace_gid = workspaces[0]["gid"]
            is_org = workspaces[0].get("is_organization", False)
        else:
            print("Multiple workspaces found. Specify one:")
            for ws in workspaces:
                print(f"  {ws['gid']}  {ws['name']}")
            print("\nUsage: taskana-cli project-create <name> --workspace <gid>")
            return
    else:
        ws = api("GET", f"/workspaces/{workspace_gid}?opt_fields=is_organization", token)
        is_org = ws.get("is_organization", False)

    # Organizations require a team
    if is_org and not team_gid:
        teams = api("GET", f"/organizations/{workspace_gid}/teams?opt_fields=name&limit=100", token)
        if len(teams) == 1:
            team_gid = teams[0]["gid"]
            print(f"Team: {teams[0]['name']}")
        else:
            print("Organization requires a team. Available teams:")
            for t in teams:
                print(f"  {t['gid']}  {t['name']}")
            print("\nUsage: taskana-cli project-create <name> --team <gid>")
            return

    data = {
        "name": name,
        "workspace": workspace_gid,
        "default_view": "board",
    }
    if team_gid:
        data["team"] = team_gid

    project = api("POST", "/projects", token, {"data": data})
    print(f"Created project: {project['gid']}  {project['name']}")


def cmd_init(token):
    """Initialize .claude-team/taskana.json in current directory."""
    config_dir = Path.cwd() / ".claude-team"
    config_path = config_dir / "taskana.json"

    if config_path.exists():
        print(f"Already initialized: {config_path}")
        with open(config_path) as f:
            config = json.load(f)
        print(json.dumps(config, indent=2))
        return

    # Get workspaces
    workspaces = api("GET", "/workspaces?opt_fields=name,gid", token)

    if len(workspaces) == 1:
        ws = workspaces[0]
        print(f"Workspace: {ws['name']} ({ws['gid']})")
    else:
        print("Available workspaces:")
        for ws in workspaces:
            print(f"  {ws['gid']}  {ws['name']}")
        print("\nMultiple workspaces found. Use 'taskana-cli projects <ws_gid>' to browse,")
        print("then create .claude-team/taskana.json manually.")
        return

    # List projects
    projects = api(
        "GET",
        f"/workspaces/{ws['gid']}/projects?opt_fields=name,gid,archived&limit=100",
        token,
    )
    active = [p for p in projects if not p.get("archived")]
    print(f"\nAvailable projects ({len(active)}):")
    for i, p in enumerate(active, 1):
        print(f"  {i}. {p['name']}  ({p['gid']})")

    print(f"\nTo complete init, provide the project number or GID.")
    print("The skill will handle the interactive selection.")

    # Output structured data for the skill to parse
    print("\n---PROJECTS_JSON---")
    print(json.dumps([{"gid": p["gid"], "name": p["name"]} for p in active]))
    print(f"---WORKSPACE_GID---")
    print(ws["gid"])


def cmd_init_write(workspace_gid, project_gid):
    """Write .claude-team/taskana.json with given IDs. Refuses to overwrite multi-target config."""
    config_dir = Path.cwd() / ".claude-team"
    config_path = config_dir / "taskana.json"

    # Refuse to overwrite multi-target config
    if config_path.exists():
        with open(config_path) as f:
            existing = json.load(f)
        if "targets" in existing:
            print("ERROR: Multi-target config exists. Use 'add-target' to add targets.", file=sys.stderr)
            print(f"Config: {config_path}", file=sys.stderr)
            sys.exit(1)

    config = {
        "projectId": project_gid,
        "workspaceId": workspace_gid,
    }

    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    print(f"Created {config_path}")
    print(json.dumps(config, indent=2))


def cmd_status():
    """Check configuration status."""
    # Token
    token = load_token()
    if token:
        try:
            me = get_me(token)
            print(f"Token: OK ({me['name']}, {me.get('email', '-')})")
        except SystemExit:
            print("Token: INVALID (API error)")
            token = None
    else:
        print("Token: NOT FOUND")
        print("  Run: taskana-cli auth <token>")

    # Project config
    root, config_path = find_project_root()
    if config_path:
        with open(config_path) as f:
            config = json.load(f)
        print(f"Config: {config_path}")
        print(f"  projectId: {config.get('projectId', '-')}")
        print(f"  workspaceId: {config.get('workspaceId', '-')}")
    else:
        print("Config: NOT FOUND (.claude-team/taskana.json)")
        print("  Run: taskana-cli init")

    # Rules
    if root:
        rules_path = root / ".claude-team" / "RULES.md"
        if rules_path.exists():
            print(f"Rules: {rules_path}")
        else:
            print("Rules: NOT FOUND (.claude-team/RULES.md) — using defaults")


def resolve_user(token, config, user_query):
    """Resolve user by 'me' or name/email search. Returns {gid, name}."""
    if user_query.lower() == "me":
        return get_me(token)
    workspace_id = config.get("workspaceId")
    if not workspace_id:
        print("workspaceId not found in .claude-team/taskana.json", file=sys.stderr)
        sys.exit(1)
    users = api(
        "GET",
        f"/workspaces/{workspace_id}/users?opt_fields=name,email&limit=100",
        token,
    )
    lower = user_query.lower()
    matched = [
        u for u in users
        if lower in u.get("name", "").lower() or lower in u.get("email", "").lower()
    ]
    if not matched:
        print(f"No user matching '{user_query}'", file=sys.stderr)
        sys.exit(1)
    if len(matched) > 1:
        print(f"Multiple users match '{user_query}':")
        for u in matched:
            print(f"  {u['gid']}  {u['name']} ({u.get('email', '-')})")
        sys.exit(1)
    return matched[0]


def cmd_assign(token, config, task_id, user_query):
    user = resolve_user(token, config, user_query)
    api("PUT", f"/tasks/{task_id}", token, {"data": {"assignee": user["gid"]}})
    print(f"Task {task_id} assigned to {user['name']}")


def cmd_unassign(token, task_id):
    api("PUT", f"/tasks/{task_id}", token, {"data": {"assignee": None}})
    print(f"Task {task_id} unassigned")


def cmd_watch(token, config, task_id, user_query="me"):
    user = resolve_user(token, config, user_query)
    api("POST", f"/tasks/{task_id}/addFollowers", token,
        {"data": {"followers": [user["gid"]]}})
    print(f"Added {user['name']} as watcher on task {task_id}")


def cmd_unwatch(token, config, task_id, user_query="me"):
    user = resolve_user(token, config, user_query)
    api("POST", f"/tasks/{task_id}/removeFollowers", token,
        {"data": {"followers": [user["gid"]]}})
    print(f"Removed {user['name']} as watcher from task {task_id}")


def cmd_due(token, task_id, date_str):
    due = None if date_str.lower() == "clear" else date_str
    api("PUT", f"/tasks/{task_id}", token, {"data": {"due_on": due}})
    if due:
        print(f"Task {task_id} due date set to {due}")
    else:
        print(f"Task {task_id} due date cleared")


def _apply_inline_md(text):
    """Apply inline markdown: **bold**, *italic*, `code`."""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def md_to_html(text):
    """Convert markdown to rich text HTML. No <br>/<p>/<div> — use \\n for line breaks."""
    import re
    lines = text.split("\n")
    result = []
    in_list = False
    for line in lines:
        # Skip empty lines
        if not line.strip():
            if in_list:
                result.append("</ul>")
                in_list = False
            continue
        # Headers: # → <h1>, ## → <h2>, ### and deeper → <strong>
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            if in_list:
                result.append("</ul>")
                in_list = False
            level = len(m.group(1))
            content = _apply_inline_md(m.group(2))
            if level == 1:
                result.append(f"<h1>{content}</h1>")
            elif level == 2:
                result.append(f"<h2>{content}</h2>")
            else:
                result.append(f"<strong>{content}</strong>")
            continue
        # List items — apply inline formatting to content
        m = re.match(r'^[\-\*]\s+(.+)$', line)
        if m:
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{_apply_inline_md(m.group(1))}</li>")
            continue
        # Non-list line closes list
        if in_list:
            result.append("</ul>")
            in_list = False
        result.append(_apply_inline_md(line))
    if in_list:
        result.append("</ul>")
    return "\n".join(result)


def cmd_comment(token, task_id, text, pin=False):
    has_md = any(text.lstrip().startswith(c) for c in ("#", "-", "*")) or "**" in text or "`" in text
    if has_md:
        html = md_to_html(text)
        data = {"html_text": f"<body>{html}</body>"}
    else:
        data = {"text": text}
    if pin:
        data["is_pinned"] = True
    story = api("POST", f"/tasks/{task_id}/stories", token, {"data": data})
    pinned = " (pinned)" if pin else ""
    print(f"Comment added to task {task_id}{pinned}")


def cmd_subtasks(token, task_id):
    fields = "name,completed,assignee.name,due_on"
    subtasks = api("GET", f"/tasks/{task_id}/subtasks?opt_fields={fields}", token)
    if not subtasks:
        print("No subtasks")
        return
    for t in subtasks:
        done = "✓" if t.get("completed") else " "
        assignee = t.get("assignee")
        extra = f"  @{assignee['name']}" if assignee else ""
        if t.get("due_on"):
            extra += f"  due:{t['due_on']}"
        print(f"[{done}] {t['gid']}  {t['name']}{extra}")
    print(f"\nTotal: {len(subtasks)} subtasks")


def cmd_subtask_create(token, parent_id, name):
    task = api("POST", f"/tasks/{parent_id}/subtasks", token,
               {"data": {"name": name}})
    print(f"Created subtask: {task['gid']}  {task['name']}")


def cmd_tags_list(token, task_id):
    fields = "tags.name"
    t = api("GET", f"/tasks/{task_id}?opt_fields={fields}", token)
    tags = t.get("tags", [])
    if not tags:
        print("No tags")
        return
    for tag in tags:
        print(f"  {tag['gid']}  {tag['name']}")


def cmd_tag_add(token, config, task_id, tag_name):
    workspace_id = config.get("workspaceId")
    # Search for existing tag
    tags = api("GET",
               f"/workspaces/{workspace_id}/tags?opt_fields=name&limit=100",
               token)
    lower = tag_name.lower()
    found = next((t for t in tags if t["name"].lower() == lower), None)
    if not found:
        found = api("POST", "/tags", token,
                     {"data": {"name": tag_name, "workspace": workspace_id}})
        print(f"Created tag: {found['name']}")
    api("POST", f"/tasks/{task_id}/addTag", token,
        {"data": {"tag": found["gid"]}})
    print(f"Tag '{found['name']}' added to task {task_id}")


def cmd_tag_remove(token, task_id, tag_name):
    fields = "tags.name"
    t = api("GET", f"/tasks/{task_id}?opt_fields={fields}", token)
    lower = tag_name.lower()
    found = next((tg for tg in t.get("tags", []) if tg["name"].lower() == lower), None)
    if not found:
        print(f"Tag '{tag_name}' not found on this task", file=sys.stderr)
        sys.exit(1)
    api("POST", f"/tasks/{task_id}/removeTag", token,
        {"data": {"tag": found["gid"]}})
    print(f"Tag '{found['name']}' removed from task {task_id}")


def cmd_deps(token, task_id):
    """List dependencies (tasks this task is blocked by)."""
    deps = api("GET", f"/tasks/{task_id}/dependencies?opt_fields=name,completed", token)
    if not deps:
        print("No dependencies")
        return
    for t in deps:
        done = "✓" if t.get("completed") else " "
        print(f"  [{done}] {t['gid']}  {t.get('name', '?')}")
    print(f"\nBlocked by: {len(deps)} tasks")


def cmd_dep_add(token, task_id, dep_id):
    api("POST", f"/tasks/{task_id}/addDependencies", token,
        {"data": {"dependencies": [dep_id]}})
    print(f"Task {task_id} now blocked by {dep_id}")


def cmd_dep_remove(token, task_id, dep_id):
    api("POST", f"/tasks/{task_id}/removeDependencies", token,
        {"data": {"dependencies": [dep_id]}})
    print(f"Dependency {dep_id} removed from task {task_id}")


def cmd_blocks(token, task_id):
    """List dependents (tasks that this task is blocking)."""
    deps = api("GET", f"/tasks/{task_id}/dependents?opt_fields=name,completed", token)
    if not deps:
        print("No dependents")
        return
    for t in deps:
        done = "✓" if t.get("completed") else " "
        print(f"  [{done}] {t['gid']}  {t.get('name', '?')}")
    print(f"\nBlocking: {len(deps)} tasks")


def cmd_block_add(token, task_id, dep_id):
    api("POST", f"/tasks/{task_id}/addDependents", token,
        {"data": {"dependents": [dep_id]}})
    print(f"Task {task_id} now blocking {dep_id}")


def cmd_block_remove(token, task_id, dep_id):
    api("POST", f"/tasks/{task_id}/removeDependents", token,
        {"data": {"dependents": [dep_id]}})
    print(f"Dependent {dep_id} removed from task {task_id}")


def cmd_rename(token, task_id, name):
    api("PUT", f"/tasks/{task_id}", token, {"data": {"name": name}})
    print(f"Task {task_id} renamed to \"{name}\"")


def cmd_reopen(token, config, task_id):
    api("PUT", f"/tasks/{task_id}", token, {"data": {"completed": False}})
    print(f"Task {task_id} reopened")


def cmd_description(token, task_id, text):
    has_md = any(text.lstrip().startswith(c) for c in ("#", "-", "*")) or "**" in text or "`" in text
    if has_md:
        html = md_to_html(text)
        api("PUT", f"/tasks/{task_id}", token,
            {"data": {"html_notes": f"<body>{html}</body>"}})
    else:
        api("PUT", f"/tasks/{task_id}", token, {"data": {"notes": text}})
    print(f"Task {task_id} description updated")


def cmd_history(token, task_id):
    stories = api("GET",
                   f"/tasks/{task_id}/stories?opt_fields=created_by.name,created_at,text,type,resource_subtype",
                   token)
    if not stories:
        print("No activity")
        return
    for s in stories:
        date = (s.get("created_at") or "")[:16].replace("T", " ")
        who = s.get("created_by", {}).get("name", "?")
        text = (s.get("text") or "").replace("\n", " ")
        if len(text) > 120:
            text = text[:117] + "..."
        print(f"  {date}  {who}: {text}")


def cmd_comments(token, task_id):
    """List comments on a task (excluding system activity)."""
    stories = api("GET",
                   f"/tasks/{task_id}/stories?opt_fields=created_by.name,created_at,text,type,resource_subtype,is_pinned",
                   token)
    if not stories:
        print("No comments")
        return
    comments = [s for s in stories if s.get("type") == "comment" or s.get("resource_subtype") == "comment_added"]
    if not comments:
        print("No comments")
        return
    for c in comments:
        date = (c.get("created_at") or "")[:16].replace("T", " ")
        who = c.get("created_by", {}).get("name", "?")
        pinned = " [pinned]" if c.get("is_pinned") else ""
        print(f"── {who}  {date}{pinned} ──")
        print(c.get("text") or "(empty)")
        print()
    print(f"Total: {len(comments)} comments")


def cmd_members(token, config):
    project_id = config["projectId"]
    members = api("GET",
                   f"/projects/{project_id}/members?opt_fields=name,email",
                   token)
    if not members:
        print("No members")
        return
    for m in members:
        print(f"  {m['gid']}  {m['name']} ({m.get('email', '-')})")
    print(f"\nTotal: {len(members)} members")


def cmd_custom_fields(token, config):
    """List custom fields for the project."""
    project_id = config["projectId"]
    fields = api("GET", f"/projects/{project_id}/custom_fields", token)
    if not fields:
        print("No custom fields")
        return
    for f in fields:
        ftype = f.get("type") or f.get("fieldType") or "?"
        print(f"  {f['gid']}  {f['name']}  ({ftype})")
    print(f"\nTotal: {len(fields)} fields")


def cmd_custom_field_create(token, config, name, field_type):
    """Create a custom field on the project."""
    project_id = config["projectId"]
    field = api("POST", f"/projects/{project_id}/custom_fields", token,
                {"data": {"name": name, "type": field_type}})
    print(f"Created field: {field['gid']}  {field['name']}  ({field_type})")


def cmd_task_fields(token, task_id):
    """List custom field values for a task."""
    values = api("GET", f"/tasks/{task_id}/custom_fields", token)
    if not values:
        print("No custom field values")
        return
    for v in values:
        name = v.get("name", v.get("gid", "?"))
        val = v.get("value") or v.get("display_value") or v.get("text_value") or "-"
        print(f"  {v['gid']}  {name}: {val}")


def cmd_task_field_set(token, task_id, field_id, value):
    """Set a custom field value on a task."""
    api("PUT", f"/tasks/{task_id}/custom_fields/{field_id}", token,
        {"data": {"value": value}})
    print(f"Field {field_id} set to \"{value}\" on task {task_id}")


def cmd_estimate(token, config, task_id, hours):
    """Set estimate on a task. Auto-creates Estimate field if missing."""
    project_id = config["projectId"]
    fields = api("GET", f"/projects/{project_id}/custom_fields", token)
    estimate_field = next(
        (f for f in (fields or []) if f["name"].lower() == "estimate"), None)
    if not estimate_field:
        estimate_field = api("POST", f"/projects/{project_id}/custom_fields", token,
                             {"data": {"name": "Estimate", "type": "number"}})
        print(f"Created field: Estimate ({estimate_field['gid']})")
    api("PUT", f"/tasks/{task_id}/custom_fields/{estimate_field['gid']}", token,
        {"data": {"value": hours}})
    print(f"Task {task_id} estimate set to {hours}h")


def cmd_board(token, config):
    project_id = config["projectId"]
    sections = get_sections(token, project_id)
    fields = "name,completed,assignee.name,due_on"
    tasks = api("GET", f"/projects/{project_id}/tasks?opt_fields={fields},memberships.section.gid&limit={task_limit()}", token)

    for sec in sections:
        sec_tasks = [t for t in tasks
                     if any((m.get("section") or {}).get("gid") == sec["gid"]
                            for m in t.get("memberships", []))]
        if not sec_tasks:
            continue
        print(f"\n┌─ {sec['name']} ({len(sec_tasks)}) ─")
        for t in sec_tasks:
            done = "✓" if t.get("completed") else " "
            parts = []
            assignee = t.get("assignee")
            if assignee:
                parts.append(f"@{assignee['name']}")
            if t.get("due_on"):
                parts.append(t["due_on"])
            extra = f"  ({', '.join(parts)})" if parts else ""
            print(f"│ [{done}] {t['name']}{extra}")
        print("└─")


def cmd_add_target(token, name, base_url, project_gid=None, target_token=None):
    """Add a new target to .claude-team/taskana.json, migrating from legacy if needed.
    Auto-resolves workspaceId. If --project given, fully configures in one call.
    If --token given, saves per-target token."""
    root, config_path = find_project_root()
    if not config_path:
        print("No .claude-team/taskana.json found.", file=sys.stderr)
        sys.exit(1)

    base_url = base_url.rstrip("/")

    # Save per-target token if provided
    if target_token:
        token_dir = Path.home() / ".config" / "taskana" / "tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        token_path = token_dir / name
        token_path.write_text(target_token.strip() + "\n")
        try:
            token_path.chmod(0o600)
        except OSError:
            pass
        token = target_token.strip()
        print(f"Token saved to {token_path}")
    else:
        # Try per-target token file
        per_target = Path.home() / ".config" / "taskana" / "tokens" / name
        if per_target.exists():
            token = per_target.read_text().strip()

    # Verify connection
    print(f"Connecting to {base_url}...")
    me = api("GET", "/users/me?opt_fields=name,email,gid", token, base_url=base_url)
    print(f"Authenticated as: {me['name']} ({me.get('email', '-')})")

    # Resolve workspace
    workspaces = api("GET", "/workspaces?opt_fields=name,gid", token, base_url=base_url)
    if not workspaces:
        print("No workspaces found.", file=sys.stderr)
        sys.exit(1)
    if len(workspaces) == 1:
        ws = workspaces[0]
    else:
        print("\nAvailable workspaces:")
        for w in workspaces:
            print(f"  {w['gid']}  {w['name']}")
        print("\nMultiple workspaces. Specify with --workspace.")
        sys.exit(1)
    print(f"Workspace: {ws['name']} ({ws['gid']})")

    # List projects
    projects = api("GET",
        f"/workspaces/{ws['gid']}/projects?opt_fields=name,gid,archived&limit=100",
        token, base_url=base_url)
    active = [p for p in projects if not p.get("archived")]
    print(f"\nAvailable projects ({len(active)}):")
    for i, p in enumerate(active, 1):
        print(f"  {i}. {p['name']}  ({p['gid']})")

    # Read existing config
    with open(config_path) as f:
        raw = json.load(f)

    # Migrate legacy → multi-target
    if "targets" not in raw:
        legacy = {k: v for k, v in raw.items() if k not in ("prefixes", "phases")}
        legacy.setdefault("baseUrl", DEFAULT_BASE_URL)
        top_level = {k: v for k, v in raw.items() if k in ("prefixes", "phases")}
        raw = {
            **top_level,
            "targets": {"main": legacy},
            "default": "main",
        }
        # Copy default token to per-target file
        default_token_path = Path.home() / ".config" / "taskana" / "token"
        main_token_path = Path.home() / ".config" / "taskana" / "tokens" / "main"
        if default_token_path.exists() and not main_token_path.exists():
            main_token_path.parent.mkdir(parents=True, exist_ok=True)
            main_token_path.write_text(default_token_path.read_text())
            try:
                main_token_path.chmod(0o600)
            except OSError:
                pass
            print("Copied default token → ~/.config/taskana/tokens/main")

    # Add new target
    target_data = {
        "baseUrl": base_url,
        "workspaceId": ws["gid"],
    }

    if project_gid:
        # Validate project exists
        found = next((p for p in active if p["gid"] == project_gid), None)
        if not found:
            print(f"Project {project_gid} not found in workspace.", file=sys.stderr)
            sys.exit(1)
        target_data["projectId"] = project_gid
        print(f"\nProject: {found['name']} ({found['gid']})")
    else:
        print("\nFOR CLAUDE: Ask user to pick a project number. Then re-run: taskana-cli add-target {name} {base_url} --project <gid>")

    raw["targets"][name] = target_data

    with open(config_path, "w") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if project_gid:
        print(f"\nTarget '{name}' fully configured.")
    else:
        print(f"\nTarget '{name}' added (no project yet).")
    print(f"Config: {config_path}")


def cmd_set_target_project(target_name, project_gid):
    """Set projectId for a target in multi-target config."""
    _, config_path = find_project_root()
    if not config_path:
        print("No .claude-team/taskana.json found.", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        raw = json.load(f)

    if "targets" not in raw or target_name not in raw["targets"]:
        print(f"Target '{target_name}' not found in config.", file=sys.stderr)
        sys.exit(1)

    raw["targets"][target_name]["projectId"] = project_gid

    with open(config_path, "w") as f:
        json.dump(raw, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Target '{target_name}' projectId set to {project_gid}")


def cmd_dismiss_multitarget():
    """Create .multitarget-offered flag to suppress the hint."""
    root, _ = find_project_root()
    if not root:
        print("No .claude-team/ found.", file=sys.stderr)
        sys.exit(1)
    flag = root / ".claude-team" / ".multitarget-offered"
    flag.touch()
    print("Multi-target hint dismissed.")


def cmd_update():
    """Update CLI and skill from GitHub."""
    api_url = "https://api.github.com/repos/incadawr/skill.taskana-tasks/contents"
    raw_url = "https://raw.githubusercontent.com/incadawr/skill.taskana-tasks/main"
    cli_dest = Path.home() / ".local" / "bin" / "taskana-cli"
    skill_dest = Path.home() / ".claude" / "skills" / "taskana-tasks" / "SKILL.md"

    print(f"Current version: {VERSION}")
    print("Checking for updates...")

    # Fetch remote version via GitHub API (no CDN cache)
    try:
        req = urllib.request.Request(
            f"{api_url}/VERSION",
            headers={"Accept": "application/vnd.github.raw"},
        )
        with urllib.request.urlopen(req) as resp:
            remote_version = resp.read().decode().strip()
    except Exception as e:
        print(f"Failed to check version: {e}", file=sys.stderr)
        sys.exit(1)

    if remote_version == VERSION:
        print(f"Already up to date (v{VERSION})")
        return

    print(f"Updating: v{VERSION} → v{remote_version}")

    # Download new CLI via API (no cache)
    try:
        req = urllib.request.Request(
            f"{api_url}/cli/taskana_cli.py",
            headers={"Accept": "application/vnd.github.raw"},
        )
        with urllib.request.urlopen(req) as resp:
            remote_cli = resp.read().decode()
    except Exception as e:
        print(f"Failed to download CLI: {e}", file=sys.stderr)
        sys.exit(1)

    # Update CLI
    cli_dest.parent.mkdir(parents=True, exist_ok=True)
    cli_dest.write_text(remote_cli)
    cli_dest.chmod(0o755)
    print(f"  CLI updated: {cli_dest}")

    # Update skill via API (no cache)
    try:
        req = urllib.request.Request(
            f"{api_url}/skill/taskana-tasks.md",
            headers={"Accept": "application/vnd.github.raw"},
        )
        with urllib.request.urlopen(req) as resp:
            remote_skill = resp.read().decode()
        skill_dest.parent.mkdir(parents=True, exist_ok=True)
        skill_dest.write_text(remote_skill)
        print(f"  Skill updated: {skill_dest}")
    except Exception as e:
        print(f"  Skill update failed: {e}", file=sys.stderr)

    # Update timestamp
    ts_path = Path.home() / ".config" / "taskana" / "last-version-check"
    ts_path.parent.mkdir(parents=True, exist_ok=True)
    ts_path.write_text(str(int(__import__("time").time())) + "\n")

    print(f"\nDone! Restart Claude Code to pick up skill changes.")


# --- Main ---

def run_for_targets(target_name, fn):
    """Run a function for each resolved target. Sets ACTIVE_BASE_URL globally."""
    global ACTIVE_BASE_URL
    raw = load_raw_config()
    targets = resolve_targets(raw, target_name)
    multi = len(targets) > 1
    for tgt_name, tgt_config in targets:
        ACTIVE_BASE_URL = tgt_config["baseUrl"]
        if multi:
            print(f"\n═══ {tgt_name} ═══")
        fn(tgt_config)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return

    global ACTIVE_BASE_URL

    # Extract global flags before command parsing
    target_name = None
    project_override = None
    filtered_args = []
    i = 0
    while i < len(args):
        if args[i] == "--target":
            i += 1
            target_name = args[i] if i < len(args) else None
        elif args[i] == "--project":
            i += 1
            project_override = args[i] if i < len(args) else None
        else:
            filtered_args.append(args[i])
        i += 1
    args = filtered_args

    if args[0] == "--version":
        print(VERSION)
        # Quick update check via GitHub API
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/incadawr/skill.taskana-tasks/contents/VERSION",
                headers={"Accept": "application/vnd.github.raw"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                remote = resp.read().decode().strip()
            if remote != VERSION:
                print(f"  Update available: v{VERSION} → v{remote}")
                print("  Run: taskana-cli update")
        except Exception:
            pass
        return

    if args[0] == "update":
        cmd_update()
        return

    # auth doesn't need existing token
    if args[0] == "auth":
        cmd_auth(args[1] if len(args) > 1 else None, target_name=target_name)
        return

    # status works with or without token
    if args[0] == "status":
        cmd_status()
        return

    # Local config commands — no token needed
    if args[0] == "set-target-project":
        if len(args) < 3:
            print("Usage: taskana-cli set-target-project <target_name> <project_gid>", file=sys.stderr)
            sys.exit(1)
        cmd_set_target_project(args[1], args[2])
        return
    if args[0] == "dismiss-multitarget":
        cmd_dismiss_multitarget()
        return

    # Resolve effective target name from config default if not specified
    effective_target = target_name
    if not effective_target:
        raw = load_raw_config()
        if raw and "targets" in raw:
            effective_target = raw.get("default", next(iter(raw["targets"])))

    # Load token (per-target if specified)
    token = load_token(effective_target)
    if not token:
        print("No Taskana token found.")
        print("Run: taskana-cli auth <token>")
        print("Get a token at: Taskana → Settings → API Tokens")
        sys.exit(1)

    # Resolve base URL for pre-config commands (from --target or config default)
    raw_pre = load_raw_config()
    if raw_pre and "targets" in raw_pre:
        resolve_name = target_name if (target_name and target_name != "all") else raw_pre.get("default", next(iter(raw_pre["targets"])))
        if resolve_name in raw_pre["targets"]:
            ACTIVE_BASE_URL = raw_pre["targets"][resolve_name].get("baseUrl", DEFAULT_BASE_URL)

    # Commands that need token but NOT project config
    if args[0] == "whoami":
        cmd_whoami(token)
        return
    if args[0] == "workspaces":
        cmd_workspaces(token)
        return
    if args[0] == "projects":
        cmd_projects(token, args[1] if len(args) > 1 else None)
        return
    if args[0] == "users":
        cmd_users(token, args[1] if len(args) > 1 else None)
        return
    if args[0] == "project-create":
        if len(args) < 2:
            print("Usage: taskana-cli project-create <name> [--workspace <gid>] [--team <gid>]", file=sys.stderr)
            sys.exit(1)
        name_parts = []
        ws_gid = None
        team_gid = None
        i = 1
        while i < len(args):
            if args[i] in ("--workspace", "-w"):
                i += 1
                ws_gid = args[i] if i < len(args) else None
            elif args[i] in ("--team", "-t"):
                i += 1
                team_gid = args[i] if i < len(args) else None
            else:
                name_parts.append(args[i])
            i += 1
        cmd_project_create(token, " ".join(name_parts), ws_gid, team_gid)
        return
    if args[0] == "add-target":
        if len(args) < 3:
            print("Usage: taskana-cli add-target <name> <base_url> [--project <gid>]", file=sys.stderr)
            print("Example: taskana-cli add-target taskana https://taskana.example.com/api/1.0 --project 12")
            sys.exit(1)
        at_name = args[1]
        at_url = args[2]
        at_project = project_override
        at_token = None
        i = 3
        while i < len(args):
            if args[i] in ("--token", "-t"):
                i += 1
                at_token = args[i] if i < len(args) else None
            i += 1
        cmd_add_target(token, at_name, at_url, at_project, at_token)
        return
    if args[0] == "init":
        cmd_init(token)
        return
    if args[0] == "init-write":
        if len(args) < 3:
            print("Usage: taskana-cli init-write <workspace_gid> <project_gid>", file=sys.stderr)
            sys.exit(1)
        cmd_init_write(args[1], args[2])
        return

    # Commands that need project config — resolve targets
    raw = load_raw_config()
    targets = resolve_targets(raw, target_name)

    # Block --target all for ID-dependent commands (IDs differ between backends)
    if target_name == "all" and len(targets) > 1:
        id_commands = {"show", "done", "start", "move", "assign", "unassign",
                       "watch", "unwatch", "due", "comment", "subtasks", "subtask",
                       "tags", "tag", "untag", "deps", "dep", "undep",
                       "blocks", "block", "unblock", "rename", "reopen",
                       "description", "history", "comments", "task-fields", "task-field-set",
                       "estimate"}
        if args[0] in id_commands:
            print(f"ERROR: '--target all' cannot be used with '{args[0]}' — task IDs differ between backends.", file=sys.stderr)
            print("Use '--target <name>' to specify which backend.", file=sys.stderr)
            sys.exit(1)

    multi = len(targets) > 1
    for tgt_idx, (tgt_name, config) in enumerate(targets):
        if project_override:
            config = {**config, "projectId": project_override}
        ACTIVE_BASE_URL = config["baseUrl"]
        # Load per-target token
        tgt_token = load_token(tgt_name)
        if not tgt_token:
            if multi:
                print(f"\n═══ {tgt_name} ═══")
                print(f"  (skipped — no token for {tgt_name})")
                continue
            else:
                print(f"No token found for target '{tgt_name}'.", file=sys.stderr)
                sys.exit(1)

        if multi:
            print(f"\n═══ {tgt_name} ═══")

        cmd = args[0]

        if multi:
            try:
                _run_command(cmd, args, tgt_token, config)
            except (SystemExit, Exception) as e:
                print(f"  (skipped — error on {tgt_name})")
        else:
            _run_command(cmd, args, tgt_token, config)

    return


def _run_command(cmd, args, token, config):
    """Execute a single command against one target."""
    # Commands that need projectId
    needs_project = {"list", "ls", "my", "overview", "board", "sections",
                     "section-create", "section-rename", "section-delete",
                     "members", "search", "find", "create", "add",
                     "custom-fields", "custom-field-create", "estimate"}
    if cmd in needs_project and not config.get("projectId"):
        print(f"ERROR: No projectId configured for this target.", file=sys.stderr)
        print("Run: taskana-cli set-target-project <target> <gid>", file=sys.stderr)
        sys.exit(1)

    if cmd in ("list", "ls"):
        cmd_list(token, config, args[1] if len(args) > 1 else None)
    elif cmd == "my":
        cmd_my(token, config)
    elif cmd == "show":
        if len(args) < 2:
            print("Usage: taskana-cli show <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_show(token, args[1])
    elif cmd == "done":
        if len(args) < 2:
            print("Usage: taskana-cli done <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_done(token, config, args[1])
    elif cmd == "start":
        if len(args) < 2:
            print("Usage: taskana-cli start <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_start(token, config, args[1])
    elif cmd == "move":
        if len(args) < 3:
            print("Usage: taskana-cli move <task_id> <section>", file=sys.stderr)
            sys.exit(1)
        cmd_move(token, config, args[1], " ".join(args[2:]))
    elif cmd in ("create", "add"):
        if len(args) < 2:
            print("Usage: taskana-cli create <name> [--section X] [--notes X] [--due X] [--assign X] [--watch X]", file=sys.stderr)
            sys.exit(1)
        name_parts = []
        section = None
        notes = None
        due = None
        assign = None
        watch = []
        i = 1
        while i < len(args):
            if args[i] in ("--section", "-s"):
                i += 1
                section = args[i] if i < len(args) else None
            elif args[i] in ("--notes", "-n"):
                i += 1
                notes = args[i] if i < len(args) else None
            elif args[i] in ("--due", "-d"):
                i += 1
                due = args[i] if i < len(args) else None
            elif args[i] in ("--assign", "-a"):
                i += 1
                assign = args[i] if i < len(args) else None
            elif args[i] in ("--watch", "-w"):
                i += 1
                if i < len(args):
                    watch.append(args[i])
            else:
                name_parts.append(args[i])
            i += 1
        cmd_create(token, config, " ".join(name_parts), section, notes, due,
                   assign, watch or None)
    elif cmd == "sections":
        cmd_sections(token, config)
    elif cmd == "section-create":
        if len(args) < 2:
            print("Usage: taskana-cli section-create <name>", file=sys.stderr)
            sys.exit(1)
        cmd_section_create(token, config, " ".join(args[1:]))
    elif cmd == "section-rename":
        if len(args) < 3:
            print("Usage: taskana-cli section-rename <section> <new_name>", file=sys.stderr)
            sys.exit(1)
        cmd_section_rename(token, config, args[1], " ".join(args[2:]))
    elif cmd == "section-delete":
        if len(args) < 2:
            print("Usage: taskana-cli section-delete <section>", file=sys.stderr)
            sys.exit(1)
        cmd_section_delete(token, config, " ".join(args[1:]))
    elif cmd in ("search", "find"):
        if len(args) < 2:
            print("Usage: taskana-cli search <query>", file=sys.stderr)
            sys.exit(1)
        cmd_search(token, config, " ".join(args[1:]))
    elif cmd == "assign":
        if len(args) < 3:
            print("Usage: taskana-cli assign <task_id> <user|me>", file=sys.stderr)
            sys.exit(1)
        cmd_assign(token, config, args[1], " ".join(args[2:]))
    elif cmd == "unassign":
        if len(args) < 2:
            print("Usage: taskana-cli unassign <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_unassign(token, args[1])
    elif cmd == "watch":
        if len(args) < 2:
            print("Usage: taskana-cli watch <task_id> [user|me]", file=sys.stderr)
            sys.exit(1)
        cmd_watch(token, config, args[1], args[2] if len(args) > 2 else "me")
    elif cmd == "unwatch":
        if len(args) < 2:
            print("Usage: taskana-cli unwatch <task_id> [user|me]", file=sys.stderr)
            sys.exit(1)
        cmd_unwatch(token, config, args[1], args[2] if len(args) > 2 else "me")
    elif cmd == "due":
        if len(args) < 3:
            print("Usage: taskana-cli due <task_id> <YYYY-MM-DD|clear>", file=sys.stderr)
            sys.exit(1)
        cmd_due(token, args[1], args[2])
    elif cmd == "comment":
        if len(args) < 3:
            print("Usage: taskana-cli comment <task_id> <text> [--pin]", file=sys.stderr)
            sys.exit(1)
        pin = "--pin" in args
        text_parts = [a for a in args[2:] if a != "--pin"]
        cmd_comment(token, args[1], " ".join(text_parts), pin=pin)
    elif cmd == "subtasks":
        if len(args) < 2:
            print("Usage: taskana-cli subtasks <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_subtasks(token, args[1])
    elif cmd == "subtask":
        if len(args) < 3:
            print("Usage: taskana-cli subtask <parent_id> <name>", file=sys.stderr)
            sys.exit(1)
        cmd_subtask_create(token, args[1], " ".join(args[2:]))
    elif cmd == "tags":
        if len(args) < 2:
            print("Usage: taskana-cli tags <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_tags_list(token, args[1])
    elif cmd == "tag":
        if len(args) < 3:
            print("Usage: taskana-cli tag <task_id> <tag_name>", file=sys.stderr)
            sys.exit(1)
        cmd_tag_add(token, config, args[1], " ".join(args[2:]))
    elif cmd == "untag":
        if len(args) < 3:
            print("Usage: taskana-cli untag <task_id> <tag_name>", file=sys.stderr)
            sys.exit(1)
        cmd_tag_remove(token, args[1], " ".join(args[2:]))
    elif cmd == "deps":
        if len(args) < 2:
            print("Usage: taskana-cli deps <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_deps(token, args[1])
    elif cmd == "dep":
        if len(args) < 3:
            print("Usage: taskana-cli dep <task_id> <dependency_id>", file=sys.stderr)
            sys.exit(1)
        cmd_dep_add(token, args[1], args[2])
    elif cmd == "undep":
        if len(args) < 3:
            print("Usage: taskana-cli undep <task_id> <dependency_id>", file=sys.stderr)
            sys.exit(1)
        cmd_dep_remove(token, args[1], args[2])
    elif cmd == "blocks":
        if len(args) < 2:
            print("Usage: taskana-cli blocks <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_blocks(token, args[1])
    elif cmd == "block":
        if len(args) < 3:
            print("Usage: taskana-cli block <task_id> <dependent_id>", file=sys.stderr)
            sys.exit(1)
        cmd_block_add(token, args[1], args[2])
    elif cmd == "unblock":
        if len(args) < 3:
            print("Usage: taskana-cli unblock <task_id> <dependent_id>", file=sys.stderr)
            sys.exit(1)
        cmd_block_remove(token, args[1], args[2])
    elif cmd == "rename":
        if len(args) < 3:
            print("Usage: taskana-cli rename <task_id> <new_name>", file=sys.stderr)
            sys.exit(1)
        cmd_rename(token, args[1], " ".join(args[2:]))
    elif cmd == "reopen":
        if len(args) < 2:
            print("Usage: taskana-cli reopen <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_reopen(token, config, args[1])
    elif cmd == "description":
        if len(args) < 3:
            print("Usage: taskana-cli description <task_id> <text>", file=sys.stderr)
            sys.exit(1)
        cmd_description(token, args[1], " ".join(args[2:]))
    elif cmd == "history":
        if len(args) < 2:
            print("Usage: taskana-cli history <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_history(token, args[1])
    elif cmd == "comments":
        if len(args) < 2:
            print("Usage: taskana-cli comments <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_comments(token, args[1])
    elif cmd == "overview":
        cmd_overview(token, config)
    elif cmd == "members":
        cmd_members(token, config)
    elif cmd == "board":
        cmd_board(token, config)
    elif cmd == "custom-fields":
        cmd_custom_fields(token, config)
    elif cmd == "custom-field-create":
        if len(args) < 3:
            print("Usage: taskana-cli custom-field-create <name> <type>", file=sys.stderr)
            print("Types: text, number, enum, date", file=sys.stderr)
            sys.exit(1)
        cmd_custom_field_create(token, config, args[1], args[2])
    elif cmd == "task-fields":
        if len(args) < 2:
            print("Usage: taskana-cli task-fields <task_id>", file=sys.stderr)
            sys.exit(1)
        cmd_task_fields(token, args[1])
    elif cmd == "task-field-set":
        if len(args) < 4:
            print("Usage: taskana-cli task-field-set <task_id> <field_id> <value>", file=sys.stderr)
            sys.exit(1)
        cmd_task_field_set(token, args[1], args[2], " ".join(args[3:]))
    elif cmd == "estimate":
        if len(args) < 3:
            print("Usage: taskana-cli estimate <task_id> <hours>", file=sys.stderr)
            sys.exit(1)
        cmd_estimate(token, config, args[1], args[2])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print("Run 'taskana-cli help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
