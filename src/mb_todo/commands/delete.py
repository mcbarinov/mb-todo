"""Delete a todo."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)


def delete(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Permanently delete a todo."""
    app = use_context(ctx)
    try:
        todo = app.service.get_todo(todo_id)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    if not yes and not app.out.json_mode:
        typer.confirm(f"Delete todo #{todo_id} '{todo.title}'?", abort=True)
    app.service.delete_todo(todo_id)
    app.out.print_todo_deleted(todo_id, todo.title)
    logger.info("Todo deleted id=%d", todo_id)
