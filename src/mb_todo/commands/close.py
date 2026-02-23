"""Close a todo."""

import logging
import time
from typing import Annotated

import typer

from mb_todo.app_context import use_context

logger = logging.getLogger(__name__)


def close(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
) -> None:
    """Close a todo."""
    app = use_context(ctx)
    todo = app.db.fetch_todo(todo_id)
    if todo is None:
        app.out.print_error_and_exit("TODO_NOT_FOUND", f"Todo #{todo_id} does not exist.")
    if todo.closed:
        app.out.print_error_and_exit("ALREADY_CLOSED", f"Todo #{todo_id} is already closed.")
    now = int(time.time())
    app.db.close_todo(todo_id, closed_at=now)
    app.out.print_todo_closed(todo_id)
    logger.info("Todo closed id=%d", todo_id)
