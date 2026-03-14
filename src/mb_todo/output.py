"""Structured output for CLI and JSON modes."""

import dataclasses
import logging
from typing import NoReturn

from mm_clikit import DualModeOutput
from rich.box import ROUNDED
from rich.table import Table

from mb_todo.db import TodoRow
from mb_todo.utils import format_timestamp

logger = logging.getLogger(__name__)


class Output(DualModeOutput):
    """Handles all CLI output in JSON or human-readable format."""

    # --- Todos ---

    def print_todo(self, todo: TodoRow) -> None:
        """Print a single todo with all fields."""
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

        self.output(json_data={"todo": dataclasses.asdict(todo)}, display_data=table)

    def print_todo_added(self, todo_id: int, title: str) -> None:
        """Print success message for todo creation."""
        self.output(json_data={"id": todo_id, "title": title}, display_data=f"Todo #{todo_id} created: {title}")

    def print_todos_added(self, results: list[tuple[int, str, str]]) -> None:
        """Print success message for multiple todo creation. Each tuple is (id, title, project)."""
        todos = [{"id": r[0], "title": r[1], "project": r[2]} for r in results]
        lines = "\n".join(f"Todo #{todo_id} created: {title} ({project})" for todo_id, title, project in results)
        self.output(json_data={"todos": todos}, display_data=lines)

    # --- Projects ---

    def print_project_added(self, name: str) -> None:
        """Print success message for project creation."""
        self.output(json_data={"name": name}, display_data=f"Project '{name}' created.")

    def print_project_deleted(self, name: str, deleted_todos: int) -> None:
        """Print success message for project deletion."""
        suffix = f" ({deleted_todos} todos removed)" if deleted_todos else ""
        self.output(json_data={"name": name, "deleted_todos": deleted_todos}, display_data=f"Project '{name}' deleted.{suffix}")

    def print_project_renamed(self, old_name: str, new_name: str) -> None:
        """Print success message for project rename."""
        self.output(
            json_data={"old_name": old_name, "new_name": new_name}, display_data=f"Project '{old_name}' renamed to '{new_name}'."
        )

    def print_projects(self, projects: list[str]) -> None:
        """Print project list."""
        self.output(json_data={"projects": projects}, display_data="\n".join(projects) if projects else "No projects.")

    def print_todos(self, todos: list[TodoRow]) -> None:
        """Print todo list in JSON or human-readable format."""
        if not todos:
            self.output(json_data={"todos": []}, display_data="No todos.")
            return

        table = Table(box=ROUNDED, header_style="bold")
        table.add_column("ID")
        table.add_column("Project")
        table.add_column("Title")

        for todo in todos:
            priority_suffix = {"high": " H", "low": " L"}.get(todo.priority, "")
            table.add_row(f"{todo.id}{priority_suffix}", todo.project or "", todo.title)

        self.output(json_data={"todos": [dataclasses.asdict(t) for t in todos]}, display_data=table)

    def print_todo_edited(self, todo_id: int) -> None:
        """Print success message for todo edit."""
        self.output(json_data={"id": todo_id}, display_data=f"Todo #{todo_id} updated.")

    def print_todo_deleted(self, todo_id: int, title: str) -> None:
        """Print success message for todo deletion."""
        self.output(json_data={"id": todo_id, "title": title}, display_data=f"Deleted #{todo_id}: {title}")

    def print_todo_closed(self, todo_id: int, title: str) -> None:
        """Print success message for todo close."""
        self.output(json_data={"id": todo_id, "title": title}, display_data=f"Closed #{todo_id}: {title}")

    def print_todo_reopened(self, todo_id: int, title: str) -> None:
        """Print success message for todo reopen."""
        self.output(json_data={"id": todo_id, "title": title}, display_data=f"Reopened #{todo_id}: {title}")

    def print_error_and_exit(self, code: str, message: str) -> NoReturn:
        """Print an error in JSON or human-readable format and exit with code 1."""
        logger.error("Command error: [%s] %s", code, message)
        super().print_error_and_exit(code, message)
