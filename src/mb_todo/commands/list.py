"""List todos."""

from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import Priority, SortOrder


def list_(
    ctx: typer.Context,
    *,
    closed: Annotated[bool, typer.Option("--closed", help="Show only closed todos.")] = False,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Show all todos (open + closed).")] = False,
    project: Annotated[str | None, typer.Option("--project", "-p", help="Filter by project.")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority", "-P", help="Filter by priority.")] = None,
    tag: Annotated[str | None, typer.Option("--tag", "-t", help="Filter by tag.")] = None,
    sort: Annotated[SortOrder, typer.Option("--sort", "-s", help="Sort order (created, priority, updated).")] = "updated",
    limit: Annotated[int | None, typer.Option("--limit", "-n", help="Max number of results.")] = None,
) -> None:
    """List todos. By default shows only open todos."""
    app = use_context(ctx)

    # Validate limit
    if limit is not None and limit < 1:
        app.out.print_error_and_exit("VALIDATION_ERROR", "Limit must be a positive integer.")

    # Validate project exists
    if project is not None:
        project = project.strip()
        if not project:
            app.out.print_error_and_exit("VALIDATION_ERROR", "Project name must not be empty.")
        if not app.db.project_exists(project):
            app.out.print_error_and_exit("PROJECT_NOT_FOUND", f"Project '{project}' does not exist.")

    # Validate tag
    if tag is not None:
        tag = tag.strip()
        if not tag:
            app.out.print_error_and_exit("VALIDATION_ERROR", "Tag must not be empty.")

    # Determine closed filter: None = all, True = closed only, False = open only
    closed_filter: bool | None
    if all_:
        closed_filter = None
    elif closed:
        closed_filter = True
    else:
        closed_filter = False

    todos = app.db.fetch_todos(closed=closed_filter, project=project, priority=priority, tag=tag, sort=sort, limit=limit)
    app.out.print_todos(todos)
