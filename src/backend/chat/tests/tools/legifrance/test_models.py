"""Tests for Legifrance data models."""

import pytest

from chat.tools.legifrance.core import (
    LegifranceCodeInfo,
    LegifranceDocument,
    LegifranceSearchResult,
)
from chat.tools.legifrance.exceptions import (
    LegifranceDocumentNotFoundError,
    LegifranceParseError,
)


class TestLegifranceSearchResult:
    """Test LegifranceSearchResult dataclass."""

    def test_create_minimal(self):
        """Test creating with minimal required fields."""
        result = LegifranceSearchResult(id="LEGIARTI001", title="Test", text="Content")
        assert result.id == "LEGIARTI001"
        assert result.title == "Test"
        assert result.text == "Content"
        assert result.num is None
        assert result.etat is None

    def test_create_full(self):
        """Test creating with all fields."""
        result = LegifranceSearchResult(
            id="LEGIARTI001",
            title="Article 1240",
            text="Tout fait quelconque...",
            num="1240",
            etat="VIGUEUR",
            nature="CODE",
            date_publication="2020-01-01",
            date_signature="2019-12-01",
            juridiction="Cour de cassation",
            raw={"key": "value"},
        )
        assert result.num == "1240"
        assert result.etat == "VIGUEUR"
        assert result.raw == {"key": "value"}


class TestLegifranceCodeInfo:
    """Test LegifranceCodeInfo dataclass."""

    def test_create_code_info(self):
        """Test creating code info."""
        code = LegifranceCodeInfo(
            id="1", title="Code civil", etat="VIGUEUR", cid="LEGITEXT000006070721"
        )
        assert code.id == "1"
        assert code.title == "Code civil"
        assert code.cid == "LEGITEXT000006070721"


class TestLegifranceDocument:
    """Test LegifranceDocument dataclass and from_raw method."""

    def test_create_document(self):
        """Test creating document directly."""
        doc = LegifranceDocument(
            id="LEGIARTI001",
            title="Article 1240",
            text="Content here",
            date="2020-01-01",
            url="https://legifrance.gouv.fr/...",
        )
        assert doc.id == "LEGIARTI001"
        assert doc.title == "Article 1240"

    def test_from_raw_with_article(self, sample_document_response):
        """Test parsing standard article response."""
        doc = LegifranceDocument.from_raw(sample_document_response, "LEGIARTI000032041571")
        assert doc.id == "LEGIARTI000032041571"
        assert "1240" in doc.title
        assert doc.text is not None

    def test_from_raw_null_article(self):
        """Test parsing response with null article."""
        with pytest.raises(LegifranceDocumentNotFoundError):
            LegifranceDocument.from_raw({"article": None}, "LEGIARTI999")

    def test_from_raw_none_data(self):
        """Test parsing None data."""
        with pytest.raises(LegifranceDocumentNotFoundError):
            LegifranceDocument.from_raw(None, "LEGIARTI999")

    def test_from_raw_invalid_format(self):
        """Test parsing invalid response format."""
        with pytest.raises(LegifranceParseError):
            LegifranceDocument.from_raw({"article": "not a dict"}, "LEGIARTI999")

    def test_from_raw_juri_structure(self):
        """Test parsing jurisprudence structure with text wrapper."""
        data = {
            "text": {
                "id": "JURITEXT000001",
                "titre": "Cour de cassation - 2020",
                "text": "Decision content here",
                "juridictionJudiciaire": "Cour de cassation",
                "dateDecision": "2020-01-15",
            }
        }
        doc = LegifranceDocument.from_raw(data, "JURITEXT000001")
        assert doc.id == "JURITEXT000001"
        assert "Cour de cassation" in doc.title

    def test_from_raw_acco_structure(self):
        """Test parsing ACCO structure with acco wrapper."""
        data = {
            "acco": {
                "id": "ACCOTEXT000001",
                "titre": "Accord d'entreprise",
                "attachment": {"content": "Agreement content"},
            }
        }
        doc = LegifranceDocument.from_raw(data, "ACCOTEXT000001")
        assert doc.id == "ACCOTEXT000001"
        assert "Agreement content" in doc.text

    def test_from_raw_structured_text(self):
        """Test parsing structured text (Code with sections)."""
        data = {
            "id": "LEGITEXT000001",
            "titre": "Code civil",
            "nature": "CODE",
            "sections": [{"title": "Titre 1"}, {"title": "Titre 2"}],
            "articles": [{"num": "1", "content": "Article 1 content"}],
        }
        doc = LegifranceDocument.from_raw(data, "LEGITEXT000001")
        assert doc.id == "LEGITEXT000001"
        assert "Structure Document" in doc.text
        assert "Titre 1" in doc.text

    def test_from_raw_with_url_builder(self, sample_document_response):
        """Test parsing with custom URL builder."""

        def mock_url_builder(rid, fond):
            return f"https://test.com/{rid}"

        doc = LegifranceDocument.from_raw(
            sample_document_response, "LEGIARTI000032041571", url_builder=mock_url_builder
        )
        assert doc.url == "https://test.com/LEGIARTI000032041571"

    def test_from_raw_timestamp_date(self):
        """Test parsing date from timestamp."""
        data = {
            "article": {
                "id": "LEGIARTI001",
                "titre": "Test Article",
                "text": "Content",
                "dateDebut": 1609459200000,  # 2021-01-01
            }
        }
        doc = LegifranceDocument.from_raw(data, "LEGIARTI001")
        assert "2021" in doc.date

    def test_from_raw_fallback_title_from_juri_fields(self):
        """Test fallback title construction from jurisprudence fields."""
        data = {
            "id": "JURITEXT001",
            "juridiction": "Cour de cassation",
            "chambre": "Chambre civile 1",
            "dateDecision": "2020-01-15",
            "text": "Decision text",
        }
        doc = LegifranceDocument.from_raw(data, "JURITEXT001")
        assert "Cour de cassation" in doc.title

    def test_from_raw_jorf_list_structure(self):
        """Test parsing JORF list structure."""
        data = {"id": "JORFTEXT001", "list": [{"id": "1"}, {"id": "2"}, {"id": "3"}]}
        doc = LegifranceDocument.from_raw(data, "JORFTEXT001")
        assert "Structure JORF" in doc.text
        assert "3" in doc.text  # Element count
