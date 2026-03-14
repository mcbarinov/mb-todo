"""Project management commands."""

import logging
from typing import Annotated

import typer
from mm_clikit import TyperPlus

from mb_todo.app_context import use_context
from mb_todo.errors import AppError

logger = logging.getLogger(__name__)

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


@project_app.command(aliases=["r"])
def rename(
    ctx: typer.Context,
    old: Annotated[str, typer.Argument(help="Current project name.")],
    new: Annotated[str, typer.Argument(help="New project name.")],
) -> None:
    """Rename a project."""
    app = use_context(ctx)
    try:
        app.service.rename_project(old, new)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_project_renamed(old.strip(), new.strip())
    logger.info("Project renamed old=%r new=%r", old, new)


@project_app.command(name="delete")
def delete(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Project name (exact match).")],
    *,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt.")] = False,
    with_todos: Annotated[bool, typer.Option("--with-todos", help="Also delete all todos assigned to this project.")] = False,
) -> None:
    """Delete a project."""
    app = use_context(ctx)
    if not yes and not app.out.json_mode:
        msg = f"Delete project '{name}' and all its todos?" if with_todos else f"Delete project '{name}'?"
        typer.confirm(msg, abort=True)
    try:
        deleted_todos = app.service.delete_project(name, with_todos=with_todos)
    except AppError as e:
        app.out.print_error_and_exit(e.code, e.message)
    app.out.print_project_deleted(name, deleted_todos)
    logger.info("Project deleted name=%r deleted_todos=%d", name, deleted_todos)
