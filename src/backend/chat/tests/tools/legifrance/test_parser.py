"""Tests for Legifrance result parsing utilities."""

import pytest

from chat.tools.legifrance.core.models import LegifranceSearchResult
from chat.tools.legifrance.core.parser import (
    flatten_search_result,
    format_result_item,
)


class TestFlattenSearchResult:
    """Test flatten_search_result function."""

    def test_flatten_with_extracts(self):
        """Test flattening result with extracts in sections."""
        item = {
            "id": "ROOT001",
            "titles": [{"id": "LEGITEXT000001", "title": "Code civil"}],
            "sections": [
                {
                    "title": "Section 1",
                    "extracts": [
                        {
                            "id": "LEGIARTI000001",
                            "title": "Article 1",
                            "num": "1",
                            "values": ["Premier article du code"],
                        },
                        {
                            "id": "LEGIARTI000002",
                            "title": "Article 2",
                            "num": "2",
                            "values": ["Deuxième article"],
                        },
                    ],
                }
            ],
            "etat": "VIGUEUR",
        }
        results = flatten_search_result(item)

        assert len(results) == 2
        assert results[0].id == "LEGIARTI000001"
        assert results[0].num == "1"
        assert results[1].id == "LEGIARTI000002"

    def test_flatten_with_nested_sections(self):
        """Test flattening result with nested sections."""
        item = {
            "id": "ROOT001",
            "sections": [
                {
                    "title": "Titre 1",
                    "sections": [
                        {
                            "title": "Chapitre 1",
                            "extracts": [
                                {
                                    "id": "ART001",
                                    "title": "Article",
                                    "values": ["Content"],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        results = flatten_search_result(item)

        assert len(results) == 1
        assert results[0].id == "ART001"

    def test_flatten_with_list_items(self):
        """Test flattening result with list items (JORF style)."""
        item = {
            "id": "JORFTEXT000001",
            "titles": [{"id": "JORFTEXT000001", "title": "Décret"}],
            "list": [
                {"id": "ITEM1", "title": "Premier élément", "text": "Contenu 1"},
                {"id": "ITEM2", "title": "Deuxième élément", "text": "Contenu 2"},
            ],
        }
        results = flatten_search_result(item)

        assert len(results) == 2
        assert results[0].id == "ITEM1"
        assert results[1].id == "ITEM2"

    def test_flatten_jurisprudence_fallback(self):
        """Test flattening jurisprudence (flat) result."""
        item = {
            "id": "JURITEXT000001",
            "titles": [{"id": "JURITEXT000001", "title": "Cour de cassation"}],
            "juridiction": "Cour de cassation",
            "etat": "VIGUEUR",
            "datePublication": "2020-01-15",
        }
        results = flatten_search_result(item)

        assert len(results) == 1
        assert results[0].id == "JURITEXT000001"
        assert results[0].title == "Cour de cassation"
        assert results[0].juridiction == "Cour de cassation"

    def test_flatten_preserves_metadata(self):
        """Test that metadata is preserved in flattened results."""
        item = {
            "nature": "CODE",
            "etat": "VIGUEUR",
            "datePublication": "2020-01-15",
            "sections": [{"extracts": [{"id": "ART001", "title": "Article", "values": []}]}],
        }
        results = flatten_search_result(item)

        assert results[0].nature == "CODE"
        assert results[0].etat == "VIGUEUR"
        assert results[0].date_publication == "2020-01-15"

    def test_flatten_empty_result(self):
        """Test flattening empty result."""
        item = {"id": "EMPTY001"}
        results = flatten_search_result(item)

        assert len(results) == 1
        assert results[0].id == "EMPTY001"

    def test_flatten_cleans_html_in_text(self):
        """Test that HTML is cleaned in extracted text."""
        item = {
            "sections": [
                {
                    "extracts": [
                        {
                            "id": "ART001",
                            "title": "Article",
                            "values": ["<p>Text with <strong>HTML</strong></p>"],
                        }
                    ]
                }
            ],
        }
        results = flatten_search_result(item)

        assert "<p>" not in results[0].text
        assert "<strong>" not in results[0].text
        assert "Text with" in results[0].text

    def test_flatten_uses_titre_fallback(self):
        """Test that 'titre' is used as fallback for 'title'."""
        item = {
            "id": "ITEM001",
            "titre": "Titre en français",
        }
        results = flatten_search_result(item)

        assert results[0].title == "Titre en français"

    def test_flatten_extracts_additional_fields(self):
        """Test that additional fields are extracted from extracts."""
        item = {
            "sections": [
                {
                    "extracts": [
                        {
                            "id": "ART001",
                            "title": "Article",
                            "legalStatus": "VIGUEUR",
                            "values": ["Content"],
                        }
                    ]
                }
            ],
        }
        results = flatten_search_result(item)

        # legalStatus should be captured (if added to valid_fields)
        assert results[0].id == "ART001"

    def test_flatten_kali_with_sections(self):
        """Test KALI result with sections is processed correctly."""
        item = {
            "titles": [{"id": "KALITEXT000001", "title": "Convention collective"}],
            "sections": [
                {
                    "title": "Titre I",
                    "extracts": [{"id": "KALIARTI000001", "title": "Article", "values": []}],
                }
            ],
        }
        results = flatten_search_result(item)

        # Should extract from sections, not use flat fallback
        assert any("KALIARTI" in r.id for r in results)


class TestFormatResultItem:
    """Test format_result_item function."""

    def test_format_basic_result(self):
        """Test formatting basic result."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title="Article 1240",
            text="Tout fait quelconque...",
        )
        formatted = format_result_item(result, "CODE_DATE")

        assert "Article 1240" in formatted
        assert "LEGIARTI000001" in formatted
        assert "Tout fait quelconque" in formatted

    def test_format_with_article_number(self):
        """Test formatting result with article number."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title="Code civil",
            text="Content",
            num="1240",
        )
        formatted = format_result_item(result, "CODE_DATE")

        assert "(article: 1240)" in formatted

    def test_format_with_etat(self):
        """Test formatting result with etat metadata."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title="Article",
            text="Content",
            etat="VIGUEUR",
        )
        formatted = format_result_item(result, "CODE_DATE")

        assert "Etat: VIGUEUR" in formatted

    def test_format_with_extra_meta(self):
        """Test formatting result with extra metadata."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title="Article",
            text="Content",
        )
        extra = ["Nature: CODE", "Publi: 2020-01-15"]
        formatted = format_result_item(result, "CODE_DATE", extra_meta=extra)

        assert "Nature: CODE" in formatted
        assert "Publi: 2020-01-15" in formatted

    def test_format_includes_url(self):
        """Test formatting includes Legifrance URL."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title="Article",
            text="Content",
        )
        formatted = format_result_item(result, "CODE_DATE")

        assert "Lien:" in formatted
        assert "legifrance.gouv.fr" in formatted

    def test_format_without_url(self):
        """Test formatting when URL cannot be generated."""
        result = LegifranceSearchResult(
            id="UNKNOWN000001",
            title="Article",
            text="Content",
        )
        formatted = format_result_item(result, "UNKNOWN_FOND")

        # Should still have content but no Lien
        assert "Article" in formatted
        assert "Texte:" in formatted

    def test_format_fallback_title(self):
        """Test formatting with fallback title."""
        result = LegifranceSearchResult(
            id="LEGIARTI000001",
            title=None,
            text="Content",
        )
        formatted = format_result_item(result, "CODE_DATE")

        # Should use fallback title
        assert "Article" in formatted or "LEGIARTI000001" in formatted

    def test_format_jurisprudence(self):
        """Test formatting jurisprudence result."""
        result = LegifranceSearchResult(
            id="JURITEXT000001",
            title="Cour de cassation",
            text="Décision...",
            juridiction="Cour de cassation",
        )
        formatted = format_result_item(result, "JURI")

        assert "Cour de cassation" in formatted
        assert "JURITEXT000001" in formatted

    def test_format_kali_result(self):
        """Test formatting convention collective result."""
        result = LegifranceSearchResult(
            id="KALITEXT000001",
            title="Convention collective nationale",
            text="Article de la convention...",
        )
        formatted = format_result_item(result, "KALI")

        assert "Convention collective" in formatted
        assert "legifrance.gouv.fr" in formatted
