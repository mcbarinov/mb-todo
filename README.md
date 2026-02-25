# mb-todo

CLI-first todo manager. Data stored locally in SQLite. All GUIs (Raycast extension, etc.) interact through CLI commands with `--json` flag — CLI is the single source of truth.

## Data Model

### Project

| Field | Type                 | Description  |
|-------|----------------------|--------------|
| name  | TEXT NOT NULL PRIMARY KEY | Project name |

### Todo

| Field      | Type                                                                      | Nullable | Description                          |
|------------|---------------------------------------------------------------------------|----------|--------------------------------------|
| id         | INTEGER PRIMARY KEY AUTOINCREMENT                                         | NO       | Short numeric ID for CLI ergonomics  |
| title      | TEXT NOT NULL                                                             | NO       | Todo title                           |
| body       | TEXT                                                                      | YES      | Extended description                 |
| closed     | INTEGER NOT NULL DEFAULT 0 CHECK (closed IN (0, 1))                      | NO       | 0 = open, 1 = closed                |
| priority   | TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low','medium','high'))| NO       | Priority level                       |
| project    | TEXT REFERENCES projects(name) ON UPDATE CASCADE ON DELETE RESTRICT       | YES      | Project name (direct FK)             |
| tags       | TEXT NOT NULL DEFAULT '[]'                                                | NO       | JSON array of tag strings            |
| created_at | INTEGER NOT NULL                                                         | NO       | Unix timestamp                       |
| closed_at  | INTEGER                                                                  | YES      | Unix timestamp, set on close         |
| updated_at | INTEGER NOT NULL                                                         | NO       | Unix timestamp, set to created_at on insert |

### Indices

```sql
CREATE INDEX idx_todos_closed ON todos(closed);
CREATE INDEX idx_todos_project ON todos(project) WHERE project IS NOT NULL;
```

### Design Decisions

- **Integer IDs** — CLI ergonomics (`mb-todo close 42`)
- **Projects as name-only table** — a project is just a label picked from a list; no metadata needed
- **Text FK for project** — eliminates JOINs, project name stored directly in todos
- **RESTRICT on project delete** — prevents orphaning; user must reassign todos first
- **CASCADE on project rename** — transparent propagation
- **Tags as JSON array** — simpler schema, queryable via `json_each()`, no junction table needed
- **updated_at NOT NULL** — set to `created_at` on insert, refreshed on update; "never modified" = `updated_at == created_at`
- **closed_at nullable** — set when closing, enables "done today/this week" queries
- **Priority defaults to `medium`**
- **Timestamps as unix seconds**
- **SQLite STRICT mode**
- **No due_date** — deferred; can add via migration later if needed

## CLI

### Global Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | | JSON output |
| `--data-dir PATH` | | Data directory (env: `MB_TODO_DATA_DIR`, default: `~/.local/mb-todo/`) |
| `--version` | | Print version and exit |

### Todo Commands

#### `mb-todo add <title>`

Create a new todo.

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--body` | | TEXT | Extended description |
| `--priority` | `-P` | low\|medium\|high | Priority level (default: medium) |
| `--project` | `-p` | TEXT | Assign to project |
| `--tag` | `-t` | TEXT (multiple) | Add tags (repeatable) |

#### `mb-todo list`

List todos. By default shows only open todos, sorted by updated_at (newest first).

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--closed` | | FLAG | Show only closed todos |
| `--all` | `-a` | FLAG | Show all todos (open + closed) |
| `--project` | `-p` | TEXT | Filter by project |
| `--priority` | `-P` | low\|medium\|high | Filter by priority |
| `--tag` | `-t` | TEXT | Filter by tag |
| `--sort` | `-s` | created\|priority\|updated | Sort order (default: updated) |
| `--limit` | `-n` | INT | Max number of results |

#### `mb-todo show <id>`

Show a single todo with all fields.

#### `mb-todo edit <id>`

Edit a todo. At least one option is required.

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--title` | | TEXT | New title |
| `--body` | | TEXT | New body |
| `--priority` | `-P` | low\|medium\|high | New priority |
| `--project` | `-p` | TEXT | New project (empty string to unset) |
| `--tag` | `-t` | TEXT (multiple) | Replace all tags (repeatable) |
| `--add-tag` | | TEXT (multiple) | Add tags (repeatable) |
| `--remove-tag` | | TEXT (multiple) | Remove tags (repeatable) |

Errors: `NO_CHANGES` if no options provided, `TAG_CONFLICT` if `--tag` used with `--add-tag`/`--remove-tag`.

#### `mb-todo close <id>`

Close a todo. Sets `closed = 1` and `closed_at` to current timestamp.

#### `mb-todo reopen <id>`

Reopen a closed todo. Sets `closed = 0` and `closed_at` to null.

#### `mb-todo delete <id>`

Permanently delete a todo. Asks for confirmation before deleting (interactive mode only).

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--yes` | `-y` | FLAG | Skip confirmation prompt |

### Project Commands

Subgroup: `mb-todo project <command>`

#### `mb-todo project list`

List all projects.

#### `mb-todo project add <name>`

Create a new project. Error: `PROJECT_EXISTS` if name is taken.

#### `mb-todo project rename <old> <new>`

Rename a project. All todos referencing the old name are updated automatically (CASCADE). Error: `PROJECT_EXISTS` if new name is taken.

#### `mb-todo project delete <name>`

Delete a project. Error: `PROJECT_HAS_TODOS` if any todos reference the project.

### JSON Envelope

All `--json` output uses a consistent envelope (matches mb-pomodoro):

```json
{"ok": true, "data": {...}}
{"ok": false, "error": "CODE", "message": "..."}
```

### Error Codes

| Code | Description |
|------|-------------|
| `TODO_NOT_FOUND` | Todo ID does not exist |
| `ALREADY_CLOSED` | Todo is already closed |
| `ALREADY_OPEN` | Todo is already open |
| `PROJECT_NOT_FOUND` | Project name does not exist |
| `AMBIGUOUS_PROJECT` | Partial project name matches multiple projects |
| `PROJECT_EXISTS` | Project name already taken |
| `PROJECT_HAS_TODOS` | Cannot delete project with assigned todos |
| `INVALID_PRIORITY` | Priority value not in (low, medium, high) |
| `NO_CHANGES` | `edit` called with no options |
| `TAG_CONFLICT` | `--tag` used together with `--add-tag`/`--remove-tag` |
| `VALIDATION_ERROR` | General input validation failure |
