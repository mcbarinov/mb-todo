"""Pure utility functions."""

from datetime import UTC, datetime

from mb_todo.db import TodoRow


def normalize_tags(raw: list[str]) -> list[str]:
    """Strip whitespace, remove empties, deduplicate preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for tag in raw:
        stripped = tag.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            result.append(stripped)
    return result


def compute_tags(
    todo: TodoRow, *, tag: list[str] | None, add_tag: list[str] | None, remove_tag: list[str] | None
) -> list[str] | None:
    """Compute the final tags list, or None if tags are unchanged."""
    if tag is not None:
        return normalize_tags(tag)
    if add_tag or remove_tag:
        current = list(todo.tags)
        if remove_tag:
            to_remove = {t.strip() for t in remove_tag}
            current = [t for t in current if t not in to_remove]
        if add_tag:
            current.extend(add_tag)
        return normalize_tags(current)
    return None


def match_projects(query: str, projects: list[str]) -> list[str]:
    """Find projects matching a partial name (case-insensitive substring).

    Exact match (case-sensitive) takes priority and returns immediately.
    """
    if query in projects:
        return [query]
    query_lower = query.lower()
    return [p for p in projects if query_lower in p.lower()]


def format_timestamp(ts: int) -> str:
    """Convert a unix timestamp to local human-readable datetime string."""
    return datetime.fromtimestamp(ts, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S")
