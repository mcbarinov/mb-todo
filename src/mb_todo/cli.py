"""CLI entry point for mb-todo."""

import os
from pathlib import Path
from typing import Annotated

import typer
from mm_clikit import TyperPlus

from mb_todo.app_context import AppContext
from mb_todo.commands.add import add
from mb_todo.commands.close import close
from mb_todo.commands.delete import delete
from mb_todo.commands.edit import edit
from mb_todo.commands.list import list_
from mb_todo.commands.project import project_app
from mb_todo.commands.reopen import reopen
from mb_todo.commands.show import show
from mb_todo.config import Config
from mb_todo.db import Db
from mb_todo.log import setup_logging
from mb_todo.output import Output
from mb_todo.service import TodoService

app = TyperPlus(package_name="mb-todo")


@app.callback()
def main(
    ctx: typer.Context,
    *,
    json_output: Annotated[bool, typer.Option("--json", help="Output results as JSON.")] = False,
    data_dir: Annotated[
        Path | None,
        typer.Option("--data-dir", help="Application data directory. Env: MB_TODO_DATA_DIR."),
    ] = None,
) -> None:
    """CLI-first todo manager."""
    if data_dir is not None:
        resolved_dir: Path | None = data_dir.resolve()
    elif env_dir := os.environ.get("MB_TODO_DATA_DIR"):
        resolved_dir = Path(env_dir).resolve()
    else:
        resolved_dir = None
    cfg = Config.build(resolved_dir)
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    setup_logging(cfg.log_path)
    db = Db(cfg.db_path)
    ctx.call_on_close(db.close)
    service = TodoService(db)
    ctx.obj = AppContext(out=Output(json_mode=json_output), service=service, cfg=cfg)


app.command(aliases=["a"])(add)
app.command(name="list", aliases=["l", "ls"])(list_)
app.command(aliases=["s"])(show)
app.command(aliases=["e"])(edit)
app.command(aliases=["c"])(close)
app.command(aliases=["r"])(reopen)
app.command(aliases=["rm"])(delete)
app.add_typer(project_app, name="project", aliases=["p"], help="Manage projects.")
