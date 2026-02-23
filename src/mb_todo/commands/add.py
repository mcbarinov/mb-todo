"""Add a new todo."""

import json
import logging
import time
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import Priority
from mb_todo.utils import normalize_tags

logger = logging.getLogger(__name__)


def add(
    ctx: typer.Context,
    title: Annotated[str, typer.Argument(help="Todo title.")],
    *,
    body: Annotated[str | None, typer.Option("--body", help="Extended description.")] = None,
    priority: Annotated[Priority, typer.Option("--priority", "-P", help="Priority level.")] = "medium",
    project: Annotated[str | None, typer.Option("--project", "-p", help="Assign to project.")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", "-t", help="Add tags (repeatable).")] = None,
) -> None:
    """Create a new todo."""
    app = use_context(ctx)

    # Validate title
    title = title.strip()
    if not title:
        app.out.print_error_and_exit("VALIDATION_ERROR", "Title must not be empty.")

    # Validate project exists
    if project is not None:
        project = project.strip()
        if not project:
            app.out.print_error_and_exit("VALIDATION_ERROR", "Project name must not be empty.")
        if not app.db.project_exists(project):
            app.out.print_error_and_exit("PROJECT_NOT_FOUND", f"Project '{project}' does not exist.")

    # Normalize tags
    tags = normalize_tags(tag) if tag else []

    now = int(time.time())
    todo_id = app.db.insert_todo(
        title=title,
        body=body,
        priority=priority,
        project=project,
        tags=json.dumps(tags),
        created_at=now,
        updated_at=now,
    )

    app.out.print_todo_added(todo_id, title)
    logger.info("Todo added id=%d title=%r", todo_id, title)
