"""Show a single todo."""

from typing import Annotated

import typer

from mb_todo.app_context import use_context


def show(
    ctx: typer.Context,
    todo_id: Annotated[int, typer.Argument(help="Todo ID.")],
) -> None:
    """Show a single todo with all fields."""
    app = use_context(ctx)
    todo = app.db.fetch_todo(todo_id)
    if todo is None:
        app.out.print_error_and_exit("TODO_NOT_FOUND", f"Todo #{todo_id} does not exist.")
    app.out.print_todo(todo)
