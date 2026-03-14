"""Reopen one or more todos."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)


def reopen(
    ctx: typer.Context,
    todo_ids: Annotated[list[int], typer.Argument(help="Todo ID(s) to reopen.")],
) -> None:
    """Reopen one or more closed todos."""
    app = use_context(ctx)

    # Single ID — preserve original behavior and JSON contract
    if len(todo_ids) == 1:
        todo_id = todo_ids[0]
        try:
            todo = app.service.get_todo(todo_id)
            app.service.reopen_todo(todo_id)
        except AppError as e:
            app.out.print_error_and_exit(e.code, e.message)
        app.out.print_todo_reopened(todo_id, todo.title)
        logger.info("Todo reopened id=%d", todo_id)
        return

    # Multiple IDs — best-effort
    results: list[tuple[int, str]] = []
    errors: list[tuple[int, str, str]] = []
    for todo_id in todo_ids:
        try:
            todo = app.service.get_todo(todo_id)
            app.service.reopen_todo(todo_id)
            results.append((todo_id, todo.title))
            logger.info("Todo reopened id=%d", todo_id)
        except AppError as e:
            errors.append((todo_id, e.code, e.message))
            logger.warning("Failed to reopen todo id=%d: [%s] %s", todo_id, e.code, e.message)
    app.out.print_todos_reopened(results, errors)
    if errors:
        raise typer.Exit(1)
