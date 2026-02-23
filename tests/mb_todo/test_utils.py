"""Tests for mb_todo.utils."""

import time

import pytest

from mb_todo.db import TodoRow
from mb_todo.utils import compute_tags, format_timestamp, normalize_tags


def _make_todo(tags: list[str] | None = None) -> TodoRow:
    """Create a TodoRow with sensible defaults."""
    return TodoRow(
        id=1,
        title="t",
        body=None,
        closed=False,
        priority="medium",
        project=None,
        tags=tags or [],
        created_at=0,
        closed_at=None,
        updated_at=0,
    )


class TestNormalizeTags:
    """Test tag normalization: stripping, dedup, empty removal."""

    def test_empty_list(self):
        """Empty input returns empty output."""
        assert normalize_tags([]) == []

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is removed."""
        assert normalize_tags(["  foo  ", "bar "]) == ["foo", "bar"]

    def test_removes_empties(self):
        """Empty and whitespace-only strings are removed."""
        assert normalize_tags(["", "  ", "a"]) == ["a"]

    def test_deduplicates_preserving_order(self):
        """Duplicates are removed; first occurrence wins."""
        assert normalize_tags(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_mixed(self):
        """Combined: whitespace, empties, duplicates."""
        assert normalize_tags(["  a", "", "b ", "a", " ", "b"]) == ["a", "b"]


class TestComputeTags:
    """Test tag computation for the edit command."""

    def test_no_options_returns_none(self):
        """No tag options → None (no change)."""
        assert compute_tags(_make_todo(["x"]), tag=None, add_tag=None, remove_tag=None) is None

    def test_replace_all(self):
        """--tag replaces all tags."""
        result = compute_tags(_make_todo(["old"]), tag=["new1", "new2"], add_tag=None, remove_tag=None)
        assert result == ["new1", "new2"]

    def test_replace_normalizes(self):
        """--tag result is normalized."""
        result = compute_tags(_make_todo(), tag=["  a ", "a", ""], add_tag=None, remove_tag=None)
        assert result == ["a"]

    def test_add_only(self):
        """--add-tag appends to current tags."""
        result = compute_tags(_make_todo(["a"]), tag=None, add_tag=["b", "c"], remove_tag=None)
        assert result == ["a", "b", "c"]

    def test_remove_only(self):
        """--remove-tag removes from current tags."""
        result = compute_tags(_make_todo(["a", "b", "c"]), tag=None, add_tag=None, remove_tag=["b"])
        assert result == ["a", "c"]

    def test_add_and_remove(self):
        """--add-tag and --remove-tag combined."""
        result = compute_tags(_make_todo(["a", "b"]), tag=None, add_tag=["c"], remove_tag=["a"])
        assert result == ["b", "c"]

    def test_add_deduplicates_with_existing(self):
        """--add-tag with existing tag gets deduplicated."""
        result = compute_tags(_make_todo(["a", "b"]), tag=None, add_tag=["a", "c"], remove_tag=None)
        assert result == ["a", "b", "c"]

    def test_remove_nonexistent_tag(self):
        """Removing a tag that doesn't exist is a no-op."""
        result = compute_tags(_make_todo(["a"]), tag=None, add_tag=None, remove_tag=["z"])
        assert result == ["a"]


class TestFormatTimestamp:
    """Test unix timestamp formatting."""

    @pytest.fixture(autouse=True)
    def _set_utc(self, monkeypatch):
        """Force UTC timezone for deterministic output."""
        monkeypatch.setenv("TZ", "UTC")
        time.tzset()

    def test_epoch_zero(self):
        """Unix epoch 0 → 1970-01-01 00:00:00."""
        assert format_timestamp(0) == "1970-01-01 00:00:00"

    def test_known_timestamp(self):
        """Known timestamp produces expected string."""
        # 2024-01-15 11:30:00 UTC
        assert format_timestamp(1705318200) == "2024-01-15 11:30:00"

    @pytest.mark.parametrize("ts", [0, 1_000_000_000, 1_700_000_000])
    def test_format_pattern(self, ts):
        """Output always matches YYYY-MM-DD HH:MM:SS pattern."""
        result = format_timestamp(ts)
        parts = result.split(" ")
        assert len(parts) == 2
        assert len(parts[0].split("-")) == 3
        assert len(parts[1].split(":")) == 3
