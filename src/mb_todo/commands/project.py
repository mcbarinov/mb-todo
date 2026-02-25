"""Project management commands."""

from typing import Annotated

import typer
from mm_clikit import TyperPlus

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

project_app = TyperPlus()


@project_app.command(aliases=["a"])
def add(ctx: typer.Context, name: Annotated[str, typer.Argument(help="Project name.")]) -> None:
    """Create a new project."""
    app = use_context(ctx)
    try:
        app.service.add_project(name)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_project_added(name.strip())


@project_app.command(name="list", aliases=["l", "ls"])
def list_(ctx: typer.Context) -> None:
    """List all projects."""
    app = use_context(ctx)
    app.out.print_projects(app.service.list_projects())
