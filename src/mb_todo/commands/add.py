"""Add a new todo."""

import logging
from typing import Annotated

import typer

from mb_todo.app_context import use_context
from mb_todo.db import Priority
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)


def add(
    ctx: typer.Context,
    title: Annotated[str, typer.Argument(help="Todo title.")],
    *,
    body: Annotated[str | None, typer.Option("--body", help="Extended description.")] = None,
    priority: Annotated[Priority, typer.Option("--priority", "-P", help="Priority level.")] = "medium",
    project: Annotated[
        str | None, typer.Option("--project", "-p", help="Assign to project (partial name ok, comma-separated for multiple).")
    ] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", "-t", help="Add tags (repeatable).")] = None,
) -> None:
    """Create a new todo."""
    app = use_context(ctx)

    # Comma-separated projects: create one todo per project
    project_queries = [p.strip() for p in project.split(",") if p.strip()] if project and "," in project else None

    try:
        if project_queries:
            results = app.service.add_todo_for_projects(
                title=title, body=body, priority=priority, project_queries=project_queries, tags=tag
            )
            app.out.print_todos_added(results)
            logger.info("Todos added for %d projects", len(results))
        else:
            todo_id, clean_title = app.service.add_todo(
                title=title, body=body, priority=priority, project_query=project, tags=tag
            )
            app.out.print_todo_added(todo_id, clean_title)
            logger.info("Todo added id=%d title=%r", todo_id, clean_title)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
