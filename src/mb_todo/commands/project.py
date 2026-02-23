"""Project management commands."""

from typing import Annotated

import typer
from mm_clikit import TyperPlus

from mb_todo.app_context import use_context

project_app = TyperPlus()


@project_app.command(aliases=["a"])
def add(ctx: typer.Context, name: Annotated[str, typer.Argument(help="Project name.")]) -> None:
    """Create a new project."""
    app = use_context(ctx)
    name = name.strip()
    if not name:
        app.out.print_error_and_exit("VALIDATION_ERROR", "Project name must not be empty.")
    if not app.db.insert_project(name):
        app.out.print_error_and_exit("PROJECT_EXISTS", f"Project '{name}' already exists.")
    app.out.print_project_added(name)


@project_app.command(name="list", aliases=["l", "ls"])
def list_(ctx: typer.Context) -> None:
    """List all projects."""
    app = use_context(ctx)
    app.out.print_projects(app.db.fetch_projects())
