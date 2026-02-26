"""List todos."""

from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import Priority, SortOrder
from mb_todo.errors import AppError


def list_(
    ctx: typer.Context,
    *,
    closed: Annotated[bool, typer.Option("--closed", help="Show only closed todos.")] = False,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Show all todos (open + closed).")] = False,
    project: Annotated[str | None, typer.Option("--project", "-p", help="Filter by project (partial name ok).")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority", "-P", help="Filter by priority.")] = None,
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag.")] = None,
    sort: Annotated[SortOrder, typer.Option("--sort", "-s", help="Sort order (created, priority, updated).")] = "updated",
    limit: Annotated[int | None, typer.Option("--limit", "-n", help="Max number of results.")] = None,
) -> None:
    """List todos. By default shows only open todos."""
    app = use_context(ctx)

    # Determine closed filter: None = all, True = closed only, False = open only
    closed_filter: bool | None
    if all_:
        closed_filter = None
    elif closed:
        closed_filter = True
    else:
        closed_filter = False

    try:
        todos = app.service.list_todos(
            closed=closed_filter,
            project_query=project,
            priority=priority,
            tag=tag,
            sort=sort,
            limit=limit,
        )
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_todos(todos)
