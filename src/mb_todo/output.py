"""Structured output for CLI and JSON modes."""

# ruff: noqa: T201 -- this module is the output layer; print() is its sole mechanism for producing CLI output.

import dataclasses
import json
import logging
import sys
from typing import NoReturn

import typer
from rich.box import ROUNDED
from rich.console import Console
from rich.table import Table

from mb_todo.db import TodoRow
from mb_todo.utils import format_timestamp

logger = logging.getLogger(__name__)


class Output:
    """Handles all CLI output in JSON or human-readable format."""

    def __init__(self, *, json_mode: bool) -> None:
        """Initialize output handler.

        Args:
            json_mode: If True, output JSON envelopes; otherwise human-readable text.

        """
        self._json_mode = json_mode

    @property
    def json_mode(self) -> bool:
        """Whether output is in JSON mode."""
        return self._json_mode

    def _success(self, data: dict[str, object], message: str) -> None:
        """Print a success result in JSON or human-readable format."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": data}))
        else:
            print(message)

    def print_stub(self, message: str) -> None:
        """Print a stub/placeholder message."""
        self._success({"stub": True}, message)

    # --- Todos ---

    def print_todo(self, todo: TodoRow) -> None:
        """Print a single todo with all fields."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": {"todo": dataclasses.asdict(todo)}}))
            return

        table = Table(show_header=False, box=ROUNDED)
        table.add_column(style="bold cyan")
        table.add_column()

        table.add_row("ID", str(todo.id))
        table.add_row("Title", todo.title)
        table.add_row("Status", "closed" if todo.closed else "open")
        table.add_row("Priority", todo.priority)
        if todo.project:
            table.add_row("Project", todo.project)
        if todo.tags:
            table.add_row("Tags", ", ".join(todo.tags))
        if todo.body:
            table.add_row("Body", todo.body)
        table.add_row("Created", format_timestamp(todo.created_at))
        if todo.closed_at is not None:
            table.add_row("Closed", format_timestamp(todo.closed_at))
        table.add_row("Updated", format_timestamp(todo.updated_at))

        Console().print(table)

    def print_todo_added(self, todo_id: int, title: str) -> None:
        """Print success message for todo creation."""
        self._success({"id": todo_id, "title": title}, f"Todo #{todo_id} created: {title}")

    def print_todos_added(self, results: list[tuple[int, str, str]]) -> None:
        """Print success message for multiple todo creation. Each tuple is (id, title, project)."""
        if self._json_mode:
            data = [{"id": r[0], "title": r[1], "project": r[2]} for r in results]
            print(json.dumps({"ok": True, "data": data}))
        else:
            for todo_id, title, project in results:
                print(f"Todo #{todo_id} created: {title} ({project})")

    # --- Projects ---

    def print_project_added(self, name: str) -> None:
        """Print success message for project creation."""
        self._success({"name": name}, f"Project '{name}' created.")

    def print_projects(self, projects: list[str]) -> None:
        """Print project list."""
        self._success({"projects": projects}, "\n".join(projects) if projects else "No projects.")

    def print_todos(self, todos: list[TodoRow]) -> None:
        """Print todo list in JSON or human-readable format."""
        if self._json_mode:
            print(json.dumps({"ok": True, "data": {"todos": [dataclasses.asdict(t) for t in todos]}}))
            return

        if not todos:
            print("No todos.")
            return

        table = Table(box=ROUNDED, header_style="bold")
        table.add_column("ID")
        table.add_column("Project")
        table.add_column("Title")

        for todo in todos:
            priority_suffix = {"high": " H", "low": " L"}.get(todo.priority, "")
            table.add_row(f"{todo.id}{priority_suffix}", todo.project or "", todo.title)

        Console().print(table)

    def print_todo_edited(self, todo_id: int) -> None:
        """Print success message for todo edit."""
        self._success({"id": todo_id}, f"Todo #{todo_id} updated.")

    def print_todo_deleted(self, todo_id: int) -> None:
        """Print success message for todo deletion."""
        self._success({"id": todo_id}, f"Todo #{todo_id} deleted.")

    def print_todo_closed(self, todo_id: int) -> None:
        """Print success message for todo close."""
        self._success({"id": todo_id}, f"Todo #{todo_id} closed.")

    def print_todo_reopened(self, todo_id: int) -> None:
        """Print success message for todo reopen."""
        self._success({"id": todo_id}, f"Todo #{todo_id} reopened.")

    def print_error_and_exit(self, code: str, message: str) -> NoReturn:
        """Print an error in JSON or human-readable format and exit with code 1."""
        logger.error("Command error: [%s] %s", code, message)
        if self._json_mode:
            print(json.dumps({"ok": False, "error": code, "message": message}))
        else:
            print(f"Error: {message}", file=sys.stderr)
        raise typer.Exit(code=1)
