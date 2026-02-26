"""Tests for mb_todo.service.TodoService."""

import time
from collections.abc import Callable
from pathlib import Path

import pytest

from mb_todo.db import Db
from mb_todo.errors import AppError
from mb_todo.service import TodoService


@pytest.fixture
def db() -> Db:
    """Fresh in-memory database with migrations applied."""
    return Db(Path(":memory:"))


@pytest.fixture
def svc(db: Db) -> TodoService:
    """TodoService backed by an in-memory database."""
    return TodoService(db)


@pytest.fixture
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], None]:
    """Return a callable that freezes time.time() to a given unix timestamp."""

    def _freeze(ts: int) -> None:
        monkeypatch.setattr(time, "time", lambda: ts)

    return _freeze


def _add_todo(svc: TodoService, title: str = "Test todo", **kwargs: object) -> int:
    """Insert a todo via service and return its ID."""
    defaults: dict[str, object] = {"body": None, "priority": "medium", "project_query": None, "tags": None}
    defaults.update(kwargs)
    todo_id, _ = svc.add_todo(title=title, **defaults)  # type: ignore[arg-type]
    return todo_id


def _list_open(svc: TodoService) -> list[object]:
    """List open todos with default options."""
    return svc.list_todos(closed=False, project_query=None, priority=None, tag=None, sort="updated", limit=None)


# --- Todo: add ---


class TestAddTodo:
    """Test todo creation with validation and project resolution."""

    def test_basic(self, svc: TodoService) -> None:
        """Minimal todo created with defaults."""
        todo_id, title = svc.add_todo(title="Buy milk", body=None, priority="medium", project_query=None, tags=None)
        assert todo_id == 1
        assert title == "Buy milk"
        todo = svc.get_todo(todo_id)
        assert todo.priority == "medium"
        assert todo.tags == []
        assert todo.closed is False
        assert todo.body is None
        assert todo.project is None

    def test_all_fields(self, svc: TodoService) -> None:
        """Todo with body, priority, project, and tags."""
        svc.add_project("Work")
        todo_id, _ = svc.add_todo(
            title="Deploy", body="Deploy v2", priority="high", project_query="Work", tags=["deploy", "urgent"]
        )
        todo = svc.get_todo(todo_id)
        assert todo.body == "Deploy v2"
        assert todo.priority == "high"
        assert todo.project == "Work"
        assert todo.tags == ["deploy", "urgent"]

    def test_strips_title(self, svc: TodoService) -> None:
        """Leading/trailing whitespace stripped from title."""
        _, title = svc.add_todo(title="  Buy milk  ", body=None, priority="medium", project_query=None, tags=None)
        assert title == "Buy milk"

    @pytest.mark.parametrize("title", ["", "   ", "\t"])
    def test_blank_title(self, svc: TodoService, title: str) -> None:
        """Blank titles raise VALIDATION_ERROR."""
        with pytest.raises(AppError) as exc_info:
            svc.add_todo(title=title, body=None, priority="medium", project_query=None, tags=None)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_tags_normalized(self, svc: TodoService) -> None:
        """Tags are stripped, deduped, empties removed."""
        todo_id = _add_todo(svc, tags=["  a ", "b", "a", ""])
        todo = svc.get_todo(todo_id)
        assert todo.tags == ["a", "b"]

    def test_nonexistent_project(self, svc: TodoService) -> None:
        """Project query with no match raises PROJECT_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.add_todo(title="x", body=None, priority="medium", project_query="nope", tags=None)
        assert exc_info.value.code == "PROJECT_NOT_FOUND"

    def test_timestamps_set(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """created_at and updated_at set to current time."""
        frozen_time(1000)
        todo_id = _add_todo(svc)
        todo = svc.get_todo(todo_id)
        assert todo.created_at == 1000
        assert todo.updated_at == 1000


# --- Todo: add for projects ---


class TestAddTodoForProjects:
    """Test multi-project todo creation."""

    def test_creates_for_each_project(self, svc: TodoService) -> None:
        """One todo created per project."""
        svc.add_project("Alpha")
        svc.add_project("Beta")
        results = svc.add_todo_for_projects(
            title="Shared task", body=None, priority="medium", project_queries=["Alpha", "Beta"], tags=None
        )
        assert len(results) == 2
        assert results[0][2] == "Alpha"
        assert results[1][2] == "Beta"
        assert svc.get_todo(results[0][0]).project == "Alpha"
        assert svc.get_todo(results[1][0]).project == "Beta"

    def test_partial_match(self, svc: TodoService) -> None:
        """Project queries resolved via partial matching."""
        svc.add_project("Backend")
        svc.add_project("Frontend")
        results = svc.add_todo_for_projects(
            title="Deploy", body=None, priority="high", project_queries=["back", "front"], tags=None
        )
        assert len(results) == 2
        assert results[0][2] == "Backend"
        assert results[1][2] == "Frontend"

    def test_deduplicates_resolved(self, svc: TodoService) -> None:
        """Duplicate resolved projects create only one todo."""
        svc.add_project("Work")
        results = svc.add_todo_for_projects(
            title="Task", body=None, priority="medium", project_queries=["Work", "work"], tags=None
        )
        assert len(results) == 1
        assert results[0][2] == "Work"

    def test_fail_fast_on_invalid_project(self, svc: TodoService) -> None:
        """If any project query is invalid, no todos are created."""
        svc.add_project("Alpha")
        with pytest.raises(AppError) as exc_info:
            svc.add_todo_for_projects(title="Task", body=None, priority="medium", project_queries=["Alpha", "nope"], tags=None)
        assert exc_info.value.code == "PROJECT_NOT_FOUND"
        # No todos should have been created
        assert _list_open(svc) == []

    def test_blank_title(self, svc: TodoService) -> None:
        """Blank title raises VALIDATION_ERROR."""
        svc.add_project("Alpha")
        with pytest.raises(AppError) as exc_info:
            svc.add_todo_for_projects(title="  ", body=None, priority="medium", project_queries=["Alpha"], tags=None)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_same_timestamp(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """All todos share the same timestamp."""
        frozen_time(5000)
        svc.add_project("A")
        svc.add_project("B")
        results = svc.add_todo_for_projects(title="Task", body=None, priority="medium", project_queries=["A", "B"], tags=None)
        for todo_id, _, _ in results:
            todo = svc.get_todo(todo_id)
            assert todo.created_at == 5000
            assert todo.updated_at == 5000


# --- Todo: get ---


class TestGetTodo:
    """Test fetching a single todo by ID."""

    def test_existing(self, svc: TodoService) -> None:
        """Returns the todo when it exists."""
        todo_id = _add_todo(svc, title="Hello")
        todo = svc.get_todo(todo_id)
        assert todo.title == "Hello"

    def test_not_found(self, svc: TodoService) -> None:
        """Raises TODO_NOT_FOUND for nonexistent ID."""
        with pytest.raises(AppError) as exc_info:
            svc.get_todo(999)
        assert exc_info.value.code == "TODO_NOT_FOUND"


# --- Todo: list ---


class TestListTodos:
    """Test todo listing with filtering, sorting, and limits."""

    def test_empty(self, svc: TodoService) -> None:
        """No todos returns empty list."""
        assert _list_open(svc) == []

    def test_open_only(self, svc: TodoService) -> None:
        """closed=False excludes closed todos."""
        _add_todo(svc, title="open")
        closed_id = _add_todo(svc, title="closed")
        svc.close_todo(closed_id)
        result = _list_open(svc)
        assert len(result) == 1
        assert result[0].title == "open"

    def test_closed_only(self, svc: TodoService) -> None:
        """closed=True shows only closed todos."""
        _add_todo(svc, title="open")
        closed_id = _add_todo(svc, title="closed")
        svc.close_todo(closed_id)
        result = svc.list_todos(closed=True, project_query=None, priority=None, tag=None, sort="updated", limit=None)
        assert len(result) == 1
        assert result[0].title == "closed"

    def test_all(self, svc: TodoService) -> None:
        """closed=None shows all todos."""
        _add_todo(svc, title="open")
        closed_id = _add_todo(svc, title="closed")
        svc.close_todo(closed_id)
        result = svc.list_todos(closed=None, project_query=None, priority=None, tag=None, sort="updated", limit=None)
        assert len(result) == 2

    def test_filter_by_project(self, svc: TodoService) -> None:
        """Filter by project query (partial match resolved)."""
        svc.add_project("Backend")
        _add_todo(svc, title="with project", project_query="Backend")
        _add_todo(svc, title="no project")
        result = svc.list_todos(closed=False, project_query="back", priority=None, tag=None, sort="updated", limit=None)
        assert len(result) == 1
        assert result[0].title == "with project"

    def test_filter_by_priority(self, svc: TodoService) -> None:
        """Filter by exact priority."""
        _add_todo(svc, title="high", priority="high")
        _add_todo(svc, title="low", priority="low")
        result = svc.list_todos(closed=False, project_query=None, priority="high", tag=None, sort="updated", limit=None)
        assert len(result) == 1
        assert result[0].title == "high"

    def test_filter_by_tag(self, svc: TodoService) -> None:
        """Filter by tag uses json_each matching."""
        _add_todo(svc, title="tagged", tags=["work", "urgent"])
        _add_todo(svc, title="untagged")
        result = svc.list_todos(closed=False, project_query=None, priority=None, tag="work", sort="updated", limit=None)
        assert len(result) == 1
        assert result[0].title == "tagged"

    def test_limit(self, svc: TodoService) -> None:
        """Limit caps the result count."""
        for i in range(5):
            _add_todo(svc, title=f"todo {i}")
        result = svc.list_todos(closed=False, project_query=None, priority=None, tag=None, sort="updated", limit=2)
        assert len(result) == 2

    @pytest.mark.parametrize("limit", [0, -1])
    def test_invalid_limit(self, svc: TodoService, limit: int) -> None:
        """Non-positive limits raise VALIDATION_ERROR."""
        with pytest.raises(AppError) as exc_info:
            svc.list_todos(closed=False, project_query=None, priority=None, tag=None, sort="updated", limit=limit)
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_sort_by_priority(self, svc: TodoService) -> None:
        """Priority sort: high > medium > low."""
        _add_todo(svc, title="low", priority="low")
        _add_todo(svc, title="high", priority="high")
        _add_todo(svc, title="medium", priority="medium")
        result = svc.list_todos(closed=False, project_query=None, priority=None, tag=None, sort="priority", limit=None)
        assert [t.title for t in result] == ["high", "medium", "low"]

    def test_sort_by_created(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """Created sort: newest first."""
        frozen_time(1000)
        _add_todo(svc, title="first")
        frozen_time(2000)
        _add_todo(svc, title="second")
        result = svc.list_todos(closed=False, project_query=None, priority=None, tag=None, sort="created", limit=None)
        assert [t.title for t in result] == ["second", "first"]

    def test_empty_tag_raises(self, svc: TodoService) -> None:
        """Empty tag string raises VALIDATION_ERROR."""
        with pytest.raises(AppError) as exc_info:
            svc.list_todos(closed=False, project_query=None, priority=None, tag="  ", sort="updated", limit=None)
        assert exc_info.value.code == "VALIDATION_ERROR"


# --- Todo: edit ---


class TestEditTodo:
    """Test editing todo fields with validation and conflict detection."""

    def test_edit_title(self, svc: TodoService) -> None:
        """Title updated successfully."""
        todo_id = _add_todo(svc)
        svc.edit_todo(
            todo_id, title="New title", body=None, priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None
        )
        assert svc.get_todo(todo_id).title == "New title"

    def test_edit_priority(self, svc: TodoService) -> None:
        """Priority updated successfully."""
        todo_id = _add_todo(svc)
        svc.edit_todo(
            todo_id, title=None, body=None, priority="high", project_query=None, tag=None, add_tag=None, remove_tag=None
        )
        assert svc.get_todo(todo_id).priority == "high"

    def test_edit_body(self, svc: TodoService) -> None:
        """Body updated successfully."""
        todo_id = _add_todo(svc, body="old body")
        svc.edit_todo(
            todo_id, title=None, body="new body", priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None
        )
        assert svc.get_todo(todo_id).body == "new body"

    def test_set_project(self, svc: TodoService) -> None:
        """Project changed from one to another."""
        svc.add_project("Alpha")
        svc.add_project("Beta")
        todo_id = _add_todo(svc, project_query="Alpha")
        svc.edit_todo(
            todo_id, title=None, body=None, priority=None, project_query="Beta", tag=None, add_tag=None, remove_tag=None
        )
        assert svc.get_todo(todo_id).project == "Beta"

    def test_unset_project(self, svc: TodoService) -> None:
        """Empty string project_query unsets the project."""
        svc.add_project("Work")
        todo_id = _add_todo(svc, project_query="Work")
        svc.edit_todo(todo_id, title=None, body=None, priority=None, project_query="", tag=None, add_tag=None, remove_tag=None)
        assert svc.get_todo(todo_id).project is None

    def test_replace_tags(self, svc: TodoService) -> None:
        """--tag replaces all existing tags."""
        todo_id = _add_todo(svc, tags=["old1", "old2"])
        svc.edit_todo(
            todo_id, title=None, body=None, priority=None, project_query=None, tag=["new"], add_tag=None, remove_tag=None
        )
        assert svc.get_todo(todo_id).tags == ["new"]

    def test_add_and_remove_tags(self, svc: TodoService) -> None:
        """--add-tag and --remove-tag work together."""
        todo_id = _add_todo(svc, tags=["a", "b"])
        svc.edit_todo(
            todo_id, title=None, body=None, priority=None, project_query=None, tag=None, add_tag=["c"], remove_tag=["a"]
        )
        assert svc.get_todo(todo_id).tags == ["b", "c"]

    def test_no_changes(self, svc: TodoService) -> None:
        """All None options raises NO_CHANGES."""
        todo_id = _add_todo(svc)
        with pytest.raises(AppError) as exc_info:
            svc.edit_todo(
                todo_id, title=None, body=None, priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None
            )
        assert exc_info.value.code == "NO_CHANGES"

    @pytest.mark.parametrize(
        ("tag", "add_tag", "remove_tag"),
        [
            (["a"], ["b"], None),
            (["a"], None, ["b"]),
            (["a"], ["b"], ["c"]),
        ],
    )
    def test_tag_conflict(
        self, svc: TodoService, tag: list[str], add_tag: list[str] | None, remove_tag: list[str] | None
    ) -> None:
        """--tag with --add-tag or --remove-tag raises TAG_CONFLICT."""
        todo_id = _add_todo(svc)
        with pytest.raises(AppError) as exc_info:
            svc.edit_todo(
                todo_id, title=None, body=None, priority=None, project_query=None, tag=tag, add_tag=add_tag, remove_tag=remove_tag
            )
        assert exc_info.value.code == "TAG_CONFLICT"

    def test_empty_title(self, svc: TodoService) -> None:
        """Empty title raises VALIDATION_ERROR."""
        todo_id = _add_todo(svc)
        with pytest.raises(AppError) as exc_info:
            svc.edit_todo(
                todo_id, title="  ", body=None, priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None
            )
        assert exc_info.value.code == "VALIDATION_ERROR"

    def test_not_found(self, svc: TodoService) -> None:
        """Editing nonexistent todo raises TODO_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.edit_todo(999, title="x", body=None, priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None)
        assert exc_info.value.code == "TODO_NOT_FOUND"

    def test_updates_timestamp(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """Edit bumps updated_at."""
        frozen_time(1000)
        todo_id = _add_todo(svc)
        frozen_time(2000)
        svc.edit_todo(todo_id, title="new", body=None, priority=None, project_query=None, tag=None, add_tag=None, remove_tag=None)
        assert svc.get_todo(todo_id).updated_at == 2000


# --- Todo: close ---


class TestCloseTodo:
    """Test closing a todo."""

    def test_close(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """Open todo becomes closed with closed_at and updated_at set."""
        frozen_time(1000)
        todo_id = _add_todo(svc)
        frozen_time(2000)
        svc.close_todo(todo_id)
        todo = svc.get_todo(todo_id)
        assert todo.closed is True
        assert todo.closed_at == 2000
        assert todo.updated_at == 2000

    def test_already_closed(self, svc: TodoService) -> None:
        """Closing an already-closed todo raises ALREADY_CLOSED."""
        todo_id = _add_todo(svc)
        svc.close_todo(todo_id)
        with pytest.raises(AppError) as exc_info:
            svc.close_todo(todo_id)
        assert exc_info.value.code == "ALREADY_CLOSED"

    def test_not_found(self, svc: TodoService) -> None:
        """Closing nonexistent todo raises TODO_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.close_todo(999)
        assert exc_info.value.code == "TODO_NOT_FOUND"


# --- Todo: reopen ---


class TestReopenTodo:
    """Test reopening a closed todo."""

    def test_reopen(self, svc: TodoService, frozen_time: Callable[[int], None]) -> None:
        """Closed todo becomes open with closed_at cleared and updated_at bumped."""
        frozen_time(1000)
        todo_id = _add_todo(svc)
        frozen_time(2000)
        svc.close_todo(todo_id)
        frozen_time(3000)
        svc.reopen_todo(todo_id)
        todo = svc.get_todo(todo_id)
        assert todo.closed is False
        assert todo.closed_at is None
        assert todo.updated_at == 3000

    def test_already_open(self, svc: TodoService) -> None:
        """Reopening an already-open todo raises ALREADY_OPEN."""
        todo_id = _add_todo(svc)
        with pytest.raises(AppError) as exc_info:
            svc.reopen_todo(todo_id)
        assert exc_info.value.code == "ALREADY_OPEN"

    def test_not_found(self, svc: TodoService) -> None:
        """Reopening nonexistent todo raises TODO_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.reopen_todo(999)
        assert exc_info.value.code == "TODO_NOT_FOUND"


# --- Todo: delete ---


class TestDeleteTodo:
    """Test deleting a todo."""

    def test_delete(self, svc: TodoService) -> None:
        """Deleted todo no longer fetchable."""
        todo_id = _add_todo(svc)
        svc.delete_todo(todo_id)
        with pytest.raises(AppError) as exc_info:
            svc.get_todo(todo_id)
        assert exc_info.value.code == "TODO_NOT_FOUND"

    def test_not_found(self, svc: TodoService) -> None:
        """Deleting nonexistent todo raises TODO_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.delete_todo(999)
        assert exc_info.value.code == "TODO_NOT_FOUND"


# --- Project: add ---


class TestAddProject:
    """Test project creation."""

    def test_add(self, svc: TodoService) -> None:
        """Project created and appears in list."""
        svc.add_project("Work")
        assert "Work" in svc.list_projects()

    def test_duplicate(self, svc: TodoService) -> None:
        """Duplicate name raises PROJECT_EXISTS."""
        svc.add_project("Work")
        with pytest.raises(AppError) as exc_info:
            svc.add_project("Work")
        assert exc_info.value.code == "PROJECT_EXISTS"

    @pytest.mark.parametrize("name", ["", "   "])
    def test_blank_name(self, svc: TodoService, name: str) -> None:
        """Blank names raise VALIDATION_ERROR."""
        with pytest.raises(AppError) as exc_info:
            svc.add_project(name)
        assert exc_info.value.code == "VALIDATION_ERROR"


# --- Project: list ---


class TestListProjects:
    """Test project listing."""

    def test_empty(self, svc: TodoService) -> None:
        """No projects returns empty list."""
        assert svc.list_projects() == []

    def test_sorted(self, svc: TodoService) -> None:
        """Projects returned in alphabetical order."""
        svc.add_project("Zebra")
        svc.add_project("Alpha")
        assert svc.list_projects() == ["Alpha", "Zebra"]


# --- Project: resolve ---


class TestResolveProject:
    """Test partial project name resolution."""

    def test_exact_match(self, svc: TodoService) -> None:
        """Exact name returns that project."""
        svc.add_project("Backend")
        assert svc.resolve_project("Backend") == "Backend"

    def test_partial_match(self, svc: TodoService) -> None:
        """Substring match resolves to full name."""
        svc.add_project("Backend")
        assert svc.resolve_project("back") == "Backend"

    def test_ambiguous(self, svc: TodoService) -> None:
        """Multiple matches raises AMBIGUOUS_PROJECT."""
        svc.add_project("Backend")
        svc.add_project("Background")
        with pytest.raises(AppError) as exc_info:
            svc.resolve_project("back")
        assert exc_info.value.code == "AMBIGUOUS_PROJECT"

    def test_not_found(self, svc: TodoService) -> None:
        """No match raises PROJECT_NOT_FOUND."""
        with pytest.raises(AppError) as exc_info:
            svc.resolve_project("nope")
        assert exc_info.value.code == "PROJECT_NOT_FOUND"

    @pytest.mark.parametrize("query", ["", "   "])
    def test_blank_query(self, svc: TodoService, query: str) -> None:
        """Blank query raises VALIDATION_ERROR."""
        with pytest.raises(AppError) as exc_info:
            svc.resolve_project(query)
        assert exc_info.value.code == "VALIDATION_ERROR"
