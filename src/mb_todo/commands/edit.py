"""Edit an existing todo."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import Priority
from mb_todo.errors import AppError

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
    try:
        app.service.edit_todo(
            todo_id,
            title=title,
            body=body,
            priority=priority,
            project_query=project,
            tag=tag,
            add_tag=add_tag,
            remove_tag=remove_tag,
        )
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_todo_edited(todo_id)
    logger.info("Todo edited id=%d", todo_id)
