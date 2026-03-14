"""Delete one or more todos."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)


def delete(
    ctx: typer.Context,
    todo_ids: Annotated[list[int], typer.Argument(help="Todo ID(s) to delete.")],
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
) -> None:
    """Permanently delete one or more todos."""
    app = use_context(ctx)

    # Single ID — preserve original behavior and JSON contract
    if len(todo_ids) == 1:
        todo_id = todo_ids[0]
        try:
            todo = app.service.get_todo(todo_id)
        except AppError as e:
            app.out.print_error_and_exit(e.code, e.message)
        if not yes and not app.out.json_mode:
            typer.confirm(f"Delete todo #{todo_id} '{todo.title}'?", abort=True)
        app.service.delete_todo(todo_id)
        app.out.print_todo_deleted(todo_id, todo.title)
        logger.info("Todo deleted id=%d", todo_id)
        return

    # Multiple IDs — resolve all first, then confirm, then delete best-effort
    todos: list[tuple[int, str]] = []
    resolve_errors: list[tuple[int, str, str]] = []
    for todo_id in todo_ids:
        try:
            todo = app.service.get_todo(todo_id)
            todos.append((todo_id, todo.title))
        except AppError as e:
            resolve_errors.append((todo_id, e.code, e.message))

    if not yes and not app.out.json_mode and todos:
        lines = "\n".join(f"  #{todo_id}: {title}" for todo_id, title in todos)
        typer.confirm(f"Delete {len(todos)} todos?\n{lines}\n", abort=True)

    results: list[tuple[int, str]] = []
    for todo_id, title in todos:
        app.service.delete_todo(todo_id)
        results.append((todo_id, title))
        logger.info("Todo deleted id=%d", todo_id)

    app.out.print_todos_deleted(results, resolve_errors)
    if resolve_errors:
        raise typer.Exit(1)
