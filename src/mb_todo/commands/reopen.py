"""Reopen a todo."""

import logging
import time
from typing import Annotated

import typer

from mb_todo.app_context import use_context

logger = logging.getLogger(__name__)


def reopen(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
) -> None:
    """Reopen a closed todo."""
    app = use_context(ctx)
    todo = app.db.fetch_todo(todo_id)
    if todo is None:
        app.out.print_error_and_exit("TODO_NOT_FOUND", f"Todo #{todo_id} does not exist.")
    if not todo.closed:
        app.out.print_error_and_exit("ALREADY_OPEN", f"Todo #{todo_id} is already open.")
    now = int(time.time())
    app.db.reopen_todo(todo_id, updated_at=now)
    app.out.print_todo_reopened(todo_id)
    logger.info("Todo reopened id=%d", todo_id)
