"""Application context shared across CLI commands."""

from dataclasses import dataclass

import typer

from mb_todo.config import Config
from mb_todo.db import Db
from mb_todo.output import Output
from mb_todo.utils import match_projects


@dataclass(frozen=True, slots=True)
class AppContext:
    """Shared application state passed through Typer context."""

    out: Output
    db: Db
    cfg: Config

    def resolve_project(self, query: str) -> str:
        """Resolve a partial project name to an exact match, or exit with error."""
        matches = match_projects(query, self.db.fetch_projects())
        if len(matches) == 1:
            return matches[0]
        if not matches:
            self.out.print_error_and_exit("PROJECT_NOT_FOUND", f"No project matching '{query}'.")
        self.out.print_error_and_exit("AMBIGUOUS_PROJECT", f"'{query}' matches multiple projects: {', '.join(matches)}.")


def use_context(ctx: typer.Context) -> AppContext:
    """Extract application context from Typer context."""
    result: AppContext = ctx.obj
    return result
