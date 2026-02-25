"""Show a single todo."""

from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.errors import AppError


def show(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
) -> None:
    """Show a single todo with all fields."""
    app = use_context(ctx)
    try:
        todo = app.service.get_todo(todo_id)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_todo(todo)
