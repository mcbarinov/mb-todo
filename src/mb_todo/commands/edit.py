"""Edit an existing todo."""

import json
import logging
import time
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import _UNSET, Priority
from mb_todo.utils import compute_tags

logger = logging.getLogger(__name__)


def edit(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
    *,
    title: Annotated[str | None, typer.Option("--title", help="New title.")] = None,
    body: Annotated[str | None, typer.Option("--body", help="New body.")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority", "-P", help="New priority.")] = None,
    project: Annotated[str | None, typer.Option("--project", "-p", help="New project (empty string to unset).")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", "-t", help="Replace all tags (repeatable).")] = None,
    add_tag: Annotated[list[str] | None, typer.Option("--add-tag", help="Add tags (repeatable).")] = None,
    remove_tag: Annotated[list[str] | None, typer.Option("--remove-tag", help="Remove tags (repeatable).")] = None,
) -> None:
    """Edit a todo. At least one option is required."""
    app = use_context(ctx)

    # Check at least one option provided
    has_changes = any(opt is not None for opt in (title, body, priority, project, tag, add_tag, remove_tag))
    if not has_changes:
        app.out.print_error_and_exit("NO_CHANGES", "At least one option is required.")

    # Check tag conflict
    if tag is not None and (add_tag is not None or remove_tag is not None):
        app.out.print_error_and_exit("TAG_CONFLICT", "--tag cannot be used with --add-tag or --remove-tag.")

    # Fetch and validate todo exists
    todo = app.db.fetch_todo(todo_id)
    if todo is None:
        app.out.print_error_and_exit("TODO_NOT_FOUND", f"Todo #{todo_id} does not exist.")

    # Validate and prepare title
    if title is not None:
        title = title.strip()
        if not title:
            app.out.print_error_and_exit("VALIDATION_ERROR", "Title must not be empty.")

    # Validate and prepare project
    db_project: object = _UNSET
    if project is not None:
        project = project.strip()
        if project == "":
            db_project = None  # unset project
        else:
            if not app.db.project_exists(project):
                app.out.print_error_and_exit("PROJECT_NOT_FOUND", f"Project '{project}' does not exist.")
            db_project = project

    # Compute tags
    final_tags = compute_tags(todo, tag=tag, add_tag=add_tag, remove_tag=remove_tag)

    now = int(time.time())
    app.db.update_todo(
        todo_id,
        updated_at=now,
        title=title,
        body=body if body is not None else _UNSET,
        priority=priority,
        project=db_project,
        tags=json.dumps(final_tags) if final_tags is not None else None,
    )

    app.out.print_todo_edited(todo_id)
    logger.info("Todo edited id=%d", todo_id)
