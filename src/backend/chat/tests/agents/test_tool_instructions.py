"""Tests for _match_tool_pattern() — Feature 7: Tool Instructions."""

import pytest

from chat.agents.conversation import _match_tool_pattern


class TestMatchToolPatternExact:
    """Exact-match patterns."""

    def test_exact_match_found(self):
        assert _match_tool_pattern("legifrance_search", ["legifrance_search", "web_search"]) is True

    def test_exact_match_not_found(self):
        assert _match_tool_pattern("legifrance_search", ["web_search", "calculator"]) is False

    def test_exact_match_single_tool(self):
        assert _match_tool_pattern("calc", ["calc"]) is True

    def test_exact_match_empty_list(self):
        assert _match_tool_pattern("any_tool", []) is False


class TestMatchToolPatternWildcard:
    """Wildcard patterns using fnmatch."""

    def test_wildcard_prefix_match(self):
        assert _match_tool_pattern("legifrance_*", ["legifrance_search", "web_search"]) is True

    def test_wildcard_no_match(self):
        assert _match_tool_pattern("legifrance_*", ["web_search", "calculator"]) is False

    def test_wildcard_matches_multiple(self):
        tools = ["legifrance_search", "legifrance_list", "web_search"]
        assert _match_tool_pattern("legifrance_*", tools) is True

    def test_wildcard_star_only_matches_all(self):
        assert _match_tool_pattern("*", ["any_tool"]) is True

    def test_wildcard_star_empty_list(self):
        assert _match_tool_pattern("*", []) is False

    def test_wildcard_question_mark(self):
        assert _match_tool_pattern("tool_?", ["tool_a", "tool_bb"]) is True


class TestMatchToolPatternDefault:
    """The special '_default' pattern."""

    def test_default_with_tools(self):
        assert _match_tool_pattern("_default", ["some_tool"]) is True

    def test_default_with_multiple_tools(self):
        assert _match_tool_pattern("_default", ["a", "b", "c"]) is True

    def test_default_with_empty_list(self):
        assert _match_tool_pattern("_default", []) is False
