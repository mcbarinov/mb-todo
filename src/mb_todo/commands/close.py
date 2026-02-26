"""Close a todo."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)


def close(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
) -> None:
    """Close a todo."""
    app = use_context(ctx)
    try:
        todo = app.service.get_todo(todo_id)
        app.service.close_todo(todo_id)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_todo_closed(todo_id, todo.title)
    logger.info("Todo closed id=%d", todo_id)
