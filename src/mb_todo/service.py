"""Business logic layer between CLI commands and the database."""

import json
import time

from mb_todo.db import UNSET, Db, Priority, SortOrder, TodoRow
from mb_todo.errors import AppError
from mb_todo.utils import compute_tags, match_projects, normalize_tags


class TodoService:
    """Orchestrates business rules, validation, and database operations."""

    def __init__(self, db: Db) -> None:
        """Initialize with a database instance.

        Args:
            db: Database access object.

        """
        self._db = db

    # --- Todo ---

    def add_todo(
        self,
        *,
        title: str,
        body: str | None,
        priority: Priority,
        project_query: str | None,
        tags: list[str] | None,
    ) -> tuple[int, str]:
        """Create a new todo. Returns (id, title).

        Validates title non-empty, resolves project query, normalizes tags.
        """
        title = title.strip()
        if not title:
            raise AppError("VALIDATION_ERROR", "Title must not be empty.")

        project = self.resolve_project(project_query) if project_query is not None else None

        final_tags = normalize_tags(tags) if tags else []
        now = int(time.time())
        tags_json = json.dumps(final_tags)
        todo_id = self._db.insert_todo(
            title=title,
            body=body,
            priority=priority,
            project=project,
            tags=tags_json,
            created_at=now,
            updated_at=now,
        )
        return todo_id, title

    def list_todos(
        self,
        *,
        closed: bool | None,
        project_query: str | None,
        priority: Priority | None,
        tag: str | None,
        sort: SortOrder,
        limit: int | None,
    ) -> list[TodoRow]:
        """List todos with optional filtering, sorting, and limit."""
        if limit is not None and limit < 1:
            raise AppError("VALIDATION_ERROR", "Limit must be a positive integer.")

        project = self.resolve_project(project_query) if project_query is not None else None

        if tag is not None:
            tag = tag.strip()
            if not tag:
                raise AppError("VALIDATION_ERROR", "Tag must not be empty.")

        return self._db.fetch_todos(closed=closed, project=project, priority=priority, tag=tag, sort=sort, limit=limit)

    def get_todo(self, todo_id: int) -> TodoRow:
        """Fetch a single todo by ID. Raises AppError if not found."""
        todo = self._db.fetch_todo(todo_id)
        if todo is None:
            raise AppError("TODO_NOT_FOUND", f"Todo #{todo_id} does not exist.")
        return todo

    def edit_todo(
        self,
        todo_id: int,
        *,
        title: str | None,
        body: str | None,
        priority: Priority | None,
        project_query: str | None,
        tag: list[str] | None,
        add_tag: list[str] | None,
        remove_tag: list[str] | None,
    ) -> None:
        """Edit a todo. Validates inputs, resolves project query, computes tags."""
        # Check at least one option provided
        has_changes = any(opt is not None for opt in (title, body, priority, project_query, tag, add_tag, remove_tag))
        if not has_changes:
            raise AppError("NO_CHANGES", "At least one option is required.")

        # Check tag conflict
        if tag is not None and (add_tag is not None or remove_tag is not None):
            raise AppError("TAG_CONFLICT", "--tag cannot be used with --add-tag or --remove-tag.")

        todo = self.get_todo(todo_id)

        # Validate title
        if title is not None:
            title = title.strip()
            if not title:
                raise AppError("VALIDATION_ERROR", "Title must not be empty.")

        # Resolve project (empty string unsets)
        db_project: object = UNSET
        if project_query is not None:
            project_query = project_query.strip()
            db_project = None if project_query == "" else self.resolve_project(project_query)

        # Compute tags
        final_tags = compute_tags(todo, tag=tag, add_tag=add_tag, remove_tag=remove_tag)

        now = int(time.time())
        self._db.update_todo(
            todo_id,
            updated_at=now,
            title=title,
            body=body if body is not None else UNSET,
            priority=priority,
            project=db_project,
            tags=json.dumps(final_tags) if final_tags is not None else None,
        )

    def close_todo(self, todo_id: int) -> None:
        """Close a todo. Raises AppError if not found or already closed."""
        todo = self.get_todo(todo_id)
        if todo.closed:
            raise AppError("ALREADY_CLOSED", f"Todo #{todo_id} is already closed.")
        now = int(time.time())
        self._db.close_todo(todo_id, closed_at=now)

    def reopen_todo(self, todo_id: int) -> None:
        """Reopen a todo. Raises AppError if not found or already open."""
        todo = self.get_todo(todo_id)
        if not todo.closed:
            raise AppError("ALREADY_OPEN", f"Todo #{todo_id} is already open.")
        now = int(time.time())
        self._db.reopen_todo(todo_id, updated_at=now)

    def delete_todo(self, todo_id: int) -> None:
        """Delete a todo by ID. Raises AppError if not found."""
        self.get_todo(todo_id)
        self._db.delete_todo(todo_id)

    # --- Project ---

    def add_project(self, name: str) -> None:
        """Create a new project. Raises AppError if name empty or duplicate."""
        name = name.strip()
        if not name:
            raise AppError("VALIDATION_ERROR", "Project name must not be empty.")
        if not self._db.insert_project(name):
            raise AppError("PROJECT_EXISTS", f"Project '{name}' already exists.")

    def list_projects(self) -> list[str]:
        """Return all project names."""
        return self._db.fetch_projects()

    def resolve_project(self, query: str) -> str:
        """Resolve a partial project name (case-insensitive substring) to an exact match.

        Raises AppError if query empty, no match, or ambiguous.
        """
        query = query.strip()
        if not query:
            raise AppError("VALIDATION_ERROR", "Project name must not be empty.")
        matches = match_projects(query, self._db.fetch_projects())
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise AppError("PROJECT_NOT_FOUND", f"No project matching '{query}'.")
        raise AppError("AMBIGUOUS_PROJECT", f"'{query}' matches multiple projects: {', '.join(matches)}.")
