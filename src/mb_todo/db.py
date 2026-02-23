"""Database connection and schema management."""

import json
import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

_UNSET = object()
"""Sentinel to distinguish 'not provided' from None for nullable fields."""

Priority = Literal["low", "medium", "high"]
SortOrder = Literal["created", "priority", "updated"]


@dataclass(frozen=True, slots=True)
class TodoRow:
    """Typed representation of a todo row from the database."""

    id: int
    title: str
    body: str | None
    closed: bool
    priority: Priority
    project: str | None
    tags: list[str]
    created_at: int
    closed_at: int | None
    updated_at: int


# --- Migrations ---


def _migrate_v1(conn: sqlite3.Connection) -> None:
    """Create initial schema: projects and todos tables with indices."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT NOT NULL PRIMARY KEY
        ) STRICT;

        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT,
            closed INTEGER NOT NULL DEFAULT 0 CHECK (closed IN (0, 1)),
            priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
            project TEXT REFERENCES projects(name) ON UPDATE CASCADE ON DELETE RESTRICT,
            tags TEXT NOT NULL DEFAULT '[]',
            created_at INTEGER NOT NULL,
            closed_at INTEGER,
            updated_at INTEGER NOT NULL
        ) STRICT;

        CREATE INDEX IF NOT EXISTS idx_todos_closed ON todos(closed);
        CREATE INDEX IF NOT EXISTS idx_todos_project ON todos(project) WHERE project IS NOT NULL;
    """)


# Indexed by position: _MIGRATIONS[0] = v1, _MIGRATIONS[1] = v2, etc.
# user_version=0 means no migrations applied.
_MIGRATIONS: tuple[Callable[[sqlite3.Connection], None], ...] = (_migrate_v1,)


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run all pending schema migrations based on PRAGMA user_version."""
    current_version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    for i, migrate_fn in enumerate(_MIGRATIONS):
        target_version = i + 1
        if current_version < target_version:
            migrate_fn(conn)
            conn.execute(f"PRAGMA user_version = {target_version}")
            logger.info("Applied migration v%d (%s)", target_version, migrate_fn.__doc__)


class Db:
    """Database access object holding a SQLite connection."""

    @staticmethod
    def _row_to_todo(row: sqlite3.Row) -> TodoRow:
        """Convert a database row to a TodoRow dataclass."""
        return TodoRow(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            closed=bool(row["closed"]),
            priority=row["priority"],
            project=row["project"],
            tags=json.loads(row["tags"]),
            created_at=row["created_at"],
            closed_at=row["closed_at"],
            updated_at=row["updated_at"],
        )

    def __init__(self, db_path: Path) -> None:
        """Open a SQLite connection with WAL mode, busy timeout, foreign keys, and run pending migrations.

        Args:
            db_path: Path to the SQLite database file.

        """
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        _run_migrations(self._conn)

    # --- Projects ---

    def insert_project(self, name: str) -> bool:
        """Insert a new project. Returns False on duplicate (IntegrityError)."""
        try:
            self._conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
            self._conn.commit()
        except sqlite3.IntegrityError:
            return False
        return True

    def fetch_projects(self) -> list[str]:
        """Return all project names ordered alphabetically."""
        rows = self._conn.execute("SELECT name FROM projects ORDER BY name").fetchall()
        return [row[0] for row in rows]

    def project_exists(self, name: str) -> bool:
        """Check whether a project with the given name exists."""
        row = self._conn.execute("SELECT 1 FROM projects WHERE name = ?", (name,)).fetchone()
        return row is not None

    # --- Todos ---

    def insert_todo(
        self,
        *,
        title: str,
        body: str | None,
        priority: Priority,
        project: str | None,
        tags: str,
        created_at: int,
        updated_at: int,
    ) -> int:
        """Insert a new todo and return its ID."""
        cursor = self._conn.execute(
            "INSERT INTO todos (title, body, priority, project, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, body, priority, project, tags, created_at, updated_at),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def fetch_todos(
        self,
        *,
        closed: bool | None,
        project: str | None,
        priority: Priority | None,
        tag: str | None,
        sort: SortOrder,
        limit: int | None,
    ) -> list[TodoRow]:
        """Fetch todos with optional filtering, sorting, and limit.

        Args:
            closed: None = all, True = closed only, False = open only.
            project: Filter by exact project name.
            priority: Filter by exact priority.
            tag: Filter by tag (uses json_each on tags column).
            sort: Sort order -- created, priority, or updated.
            limit: Max rows to return. None = unlimited.

        """
        clauses: list[str] = []
        params: list[object] = []

        if closed is not None:
            clauses.append("closed = ?")
            params.append(1 if closed else 0)

        if project is not None:
            clauses.append("project = ?")
            params.append(project)

        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority)

        if tag is not None:
            clauses.append("EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value = ?)")
            params.append(tag)

        where = " AND ".join(clauses) if clauses else "1"

        if sort == "priority":
            order = "CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"
        elif sort == "created":
            order = "created_at DESC"
        else:
            order = "updated_at DESC"

        columns = "id, title, body, closed, priority, project, tags, created_at, closed_at, updated_at"
        sql = "SELECT " + columns + " FROM todos WHERE " + where + " ORDER BY " + order  # noqa: S608 -- all interpolated parts are hardcoded strings; user input goes through params  # nosec B608

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_todo(row) for row in rows]

    def fetch_todo(self, todo_id: int) -> TodoRow | None:
        """Fetch a single todo by ID. Returns None if not found."""
        row = self._conn.execute(
            "SELECT id, title, body, closed, priority, project, tags, created_at, closed_at, updated_at FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_todo(row)

    def delete_todo(self, todo_id: int) -> None:
        """Delete a todo by ID."""
        self._conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self._conn.commit()

    def close_todo(self, todo_id: int, closed_at: int) -> None:
        """Close a todo by setting closed=1 and recording the closed timestamp."""
        self._conn.execute(
            "UPDATE todos SET closed = 1, closed_at = ?, updated_at = ? WHERE id = ?",
            (closed_at, closed_at, todo_id),
        )
        self._conn.commit()

    def reopen_todo(self, todo_id: int, updated_at: int) -> None:
        """Reopen a todo by setting closed=0 and clearing closed_at."""
        self._conn.execute(
            "UPDATE todos SET closed = 0, closed_at = NULL, updated_at = ? WHERE id = ?",
            (updated_at, todo_id),
        )
        self._conn.commit()

    def update_todo(
        self,
        todo_id: int,
        *,
        updated_at: int,
        title: str | None = None,
        body: object = _UNSET,
        priority: Priority | None = None,
        project: object = _UNSET,
        tags: str | None = None,
    ) -> None:
        """Update a todo's fields dynamically. Only provided fields are changed.

        Args:
            todo_id: ID of the todo to update.
            updated_at: New updated_at timestamp (always set).
            title: New title (None = not changing).
            body: New body (_UNSET = not changing, None = clear body).
            priority: New priority (None = not changing).
            project: New project (_UNSET = not changing, None = unset project).
            tags: New tags as JSON string (None = not changing).

        """
        clauses: list[str] = ["updated_at = ?"]
        params: list[object] = [updated_at]

        if title is not None:
            clauses.append("title = ?")
            params.append(title)
        if body is not _UNSET:
            clauses.append("body = ?")
            params.append(body)
        if priority is not None:
            clauses.append("priority = ?")
            params.append(priority)
        if project is not _UNSET:
            clauses.append("project = ?")
            params.append(project)
        if tags is not None:
            clauses.append("tags = ?")
            params.append(tags)

        sql = "UPDATE todos SET " + ", ".join(clauses) + " WHERE id = ?"  # noqa: S608 -- all interpolated parts are hardcoded strings; user input goes through params  # nosec B608
        params.append(todo_id)
        self._conn.execute(sql, params)
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()
