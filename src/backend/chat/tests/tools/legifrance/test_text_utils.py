"""Tests for Legifrance text utilities."""

import pytest

from chat.tools.legifrance.core.text_utils import clean_text


class TestCleanText:
    """Test clean_text function."""

    def test_clean_text_empty(self):
        """Test cleaning empty text."""
        assert clean_text("") == ""
        assert clean_text(None) == ""

    def test_clean_text_simple(self):
        """Test cleaning simple text."""
        assert clean_text("Hello world") == "Hello world"

    def test_clean_text_non_string(self):
        """Test cleaning non-string input."""
        assert clean_text(123) == "123"
        assert clean_text({"key": "value"}) == "{'key': 'value'}"

    def test_clean_text_removes_html_tags(self):
        """Test removing HTML tags."""
        html = "<p>Hello</p> <span>world</span>"
        result = clean_text(html)
        assert "<p>" not in result
        assert "<span>" not in result
        assert "Hello" in result
        assert "world" in result

    def test_clean_text_converts_br_to_newline(self):
        """Test converting br tags to newlines."""
        html = "Line 1<br>Line 2<br/>Line 3"
        result = clean_text(html)
        assert "\n" in result
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_clean_text_converts_p_tags(self):
        """Test converting p tags to double newlines."""
        html = "<p>Paragraph 1</p><p>Paragraph 2</p>"
        result = clean_text(html)
        assert "Paragraph 1" in result
        assert "Paragraph 2" in result

    def test_clean_text_converts_list_items(self):
        """Test converting list items to markdown."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = clean_text(html)
        assert "- Item 1" in result
        assert "- Item 2" in result

    def test_clean_text_unescapes_html_entities(self):
        """Test unescaping HTML entities."""
        html = "&amp; &lt; &gt; &nbsp;"
        result = clean_text(html)
        assert "&" in result
        assert "<" in result
        assert ">" in result

    def test_clean_text_unescapes_quotes(self):
        """Test unescaping quote entities."""
        html = "&#39;quoted&#39; &quot;double&quot;"
        result = clean_text(html)
        assert "'" in result
        assert '"' in result

    def test_clean_text_collapses_newlines(self):
        """Test collapsing multiple newlines."""
        text = "Line 1\n\n\n\n\nLine 2"
        result = clean_text(text)
        # Should have at most 2 consecutive newlines
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 2" in result

    def test_clean_text_normalizes_crlf(self):
        """Test normalizing CRLF to LF."""
        text = "Line 1\r\nLine 2\r\nLine 3"
        result = clean_text(text)
        assert "\r" not in result
        assert "\n" in result

    def test_clean_text_strips_whitespace(self):
        """Test stripping leading/trailing whitespace."""
        text = "   Hello world   "
        result = clean_text(text)
        assert result == "Hello world"

    def test_clean_text_real_legifrance_content(self):
        """Test with realistic Legifrance content."""
        html = """
        <p>Tout fait quelconque de l'homme, qui cause &agrave; autrui un dommage,
        oblige celui par la faute duquel il est arriv&eacute; &agrave; le r&eacute;parer.</p>
        <br/>
        <p>Article suivant...</p>
        """
        result = clean_text(html)
        assert "Tout fait quelconque" in result
        assert "<p>" not in result
        assert "<br" not in result
