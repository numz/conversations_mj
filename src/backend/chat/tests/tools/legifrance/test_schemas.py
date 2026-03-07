"""Tests for Legifrance Pydantic schemas."""

import pytest
from pydantic import ValidationError

from chat.tools.legifrance.core.schemas import (
    AccoResponse,
    ArticleData,
    ArticleResponse,
    CodeListItem,
    CodeListResponse,
    GenericDocumentResponse,
    JurisprudenceResponse,
    OAuthResponse,
    SearchResponse,
    SearchResult,
    SearchResultExtract,
    SearchResultSection,
    SearchResultTitle,
    validate_code_list_response,
    validate_document_response,
    validate_oauth_response,
    validate_search_response,
)


class TestOAuthResponse:
    """Test OAuthResponse Pydantic model."""

    def test_valid_oauth_response(self, sample_oauth_response):
        """Test parsing valid OAuth response."""
        response = OAuthResponse.model_validate(sample_oauth_response)
        assert response.access_token == "new_test_token"
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_oauth_response_minimal(self):
        """Test OAuth response with only required field."""
        data = {"access_token": "token123"}
        response = OAuthResponse.model_validate(data)
        assert response.access_token == "token123"
        assert response.token_type == "bearer"  # default
        assert response.expires_in == 3600  # default

    def test_oauth_response_missing_token(self):
        """Test OAuth response validation fails without token."""
        with pytest.raises(ValidationError):
            OAuthResponse.model_validate({})

    def test_validate_oauth_response_helper(self, sample_oauth_response):
        """Test helper function."""
        response = validate_oauth_response(sample_oauth_response)
        assert response.access_token == "new_test_token"


class TestSearchResponse:
    """Test SearchResponse Pydantic model."""

    def test_valid_search_response(self, sample_search_results):
        """Test parsing valid search response."""
        data = {"results": sample_search_results}
        response = SearchResponse.model_validate(data)
        assert len(response.results) == 1
        assert response.results[0].id == "LEGIARTI000006417749"

    def test_empty_search_response(self):
        """Test parsing empty search response."""
        data = {"results": []}
        response = SearchResponse.model_validate(data)
        assert response.results == []

    def test_search_response_with_total(self):
        """Test parsing search response with total count."""
        data = {"results": [], "totalResultNumber": 42}
        response = SearchResponse.model_validate(data)
        assert response.totalResultNumber == 42

    def test_validate_search_response_helper(self, sample_search_results):
        """Test helper function."""
        data = {"results": sample_search_results}
        response = validate_search_response(data)
        assert len(response.results) == 1


class TestSearchResult:
    """Test SearchResult Pydantic model."""

    def test_valid_search_result(self, sample_search_results):
        """Test parsing valid search result."""
        result = SearchResult.model_validate(sample_search_results[0])
        assert result.id == "LEGIARTI000006417749"
        assert result.etat == "VIGUEUR"
        assert result.nature == "CODE"
        assert len(result.titles) == 1
        assert len(result.sections) == 1

    def test_search_result_minimal(self):
        """Test search result with minimal fields."""
        data = {"id": "TEST123"}
        result = SearchResult.model_validate(data)
        assert result.id == "TEST123"
        assert result.titles == []
        assert result.sections == []


class TestSearchResultTitle:
    """Test SearchResultTitle Pydantic model."""

    def test_title_with_title_field(self):
        """Test title with 'title' field."""
        data = {"id": "1", "title": "Code civil"}
        title = SearchResultTitle.model_validate(data)
        assert title.display_title == "Code civil"

    def test_title_with_titre_field(self):
        """Test title with 'titre' field."""
        data = {"id": "1", "titre": "Code pénal"}
        title = SearchResultTitle.model_validate(data)
        assert title.display_title == "Code pénal"

    def test_title_prefers_title_over_titre(self):
        """Test title prefers 'title' over 'titre'."""
        data = {"id": "1", "title": "Title", "titre": "Titre"}
        title = SearchResultTitle.model_validate(data)
        assert title.display_title == "Title"


class TestSearchResultSection:
    """Test SearchResultSection Pydantic model."""

    def test_section_with_extracts(self, sample_search_results):
        """Test section with extracts."""
        section_data = sample_search_results[0]["sections"][0]
        section = SearchResultSection.model_validate(section_data)
        assert section.title == "Des contrats et des obligations conventionnelles en général"
        assert len(section.extracts) == 1
        assert section.extracts[0].num == "1240"


class TestSearchResultExtract:
    """Test SearchResultExtract Pydantic model."""

    def test_extract_parsing(self, sample_search_results):
        """Test extract parsing."""
        extract_data = sample_search_results[0]["sections"][0]["extracts"][0]
        extract = SearchResultExtract.model_validate(extract_data)
        assert extract.id == "LEGIARTI000032041571"
        assert extract.num == "1240"
        assert extract.legalStatus == "VIGUEUR"
        assert len(extract.values) == 1


class TestArticleResponse:
    """Test ArticleResponse Pydantic model."""

    def test_article_response_with_article(self, sample_document_response):
        """Test parsing article response."""
        response = ArticleResponse.model_validate(sample_document_response)
        article = response.get_article()
        assert article is not None
        assert article.id == "LEGIARTI000032041571"
        assert article.num == "1240"

    def test_article_response_with_result_wrapper(self):
        """Test parsing article response with 'result' wrapper."""
        data = {"result": {"id": "TEST123", "title": "Test Article", "text": "Content"}}
        response = ArticleResponse.model_validate(data)
        article = response.get_article()
        assert article is not None
        assert article.id == "TEST123"

    def test_article_response_empty(self):
        """Test empty article response."""
        data = {}
        response = ArticleResponse.model_validate(data)
        assert response.get_article() is None


class TestArticleData:
    """Test ArticleData Pydantic model."""

    def test_article_data_display_properties(self):
        """Test ArticleData display properties."""
        data = {"id": "TEST123", "title": "Title here", "text": "Text content"}
        article = ArticleData.model_validate(data)
        assert article.display_title == "Title here"
        assert article.display_text == "Text content"

    def test_article_data_fallback_fields(self):
        """Test ArticleData with alternate field names."""
        data = {"id": "TEST123", "titre": "Titre ici", "texte": "Contenu texte"}
        article = ArticleData.model_validate(data)
        assert article.display_title == "Titre ici"
        assert article.display_text == "Contenu texte"


class TestJurisprudenceResponse:
    """Test JurisprudenceResponse Pydantic model."""

    def test_jurisprudence_response(self):
        """Test parsing jurisprudence response."""
        data = {
            "text": {
                "id": "JURITEXT000001",
                "titre": "Décision Cour de cassation",
                "juridictionJudiciaire": "Cour de cassation",
                "dateDecision": "2020-01-15",
            }
        }
        response = JurisprudenceResponse.model_validate(data)
        assert response.text is not None
        assert response.text.id == "JURITEXT000001"
        assert response.text.display_juridiction == "Cour de cassation"


class TestAccoResponse:
    """Test AccoResponse Pydantic model."""

    def test_acco_response(self):
        """Test parsing ACCO response."""
        data = {
            "acco": {
                "id": "ACCOTEXT000001",
                "titre": "Accord d'entreprise",
                "attachment": {"content": "Agreement content here"},
            }
        }
        response = AccoResponse.model_validate(data)
        assert response.acco is not None
        assert response.acco.id == "ACCOTEXT000001"
        assert response.acco.attachment.content == "Agreement content here"


class TestCodeListResponse:
    """Test CodeListResponse Pydantic model."""

    def test_code_list_response(self, sample_code_list_results):
        """Test parsing code list response."""
        data = {"results": sample_code_list_results}
        response = CodeListResponse.model_validate(data)
        assert len(response.results) == 2
        assert response.results[0].display_title == "Code civil"
        assert response.results[1].display_title == "Code pénal"

    def test_validate_code_list_response_helper(self, sample_code_list_results):
        """Test helper function."""
        data = {"results": sample_code_list_results}
        response = validate_code_list_response(data)
        assert len(response.results) == 2


class TestCodeListItem:
    """Test CodeListItem Pydantic model."""

    def test_code_list_item(self, sample_code_list_results):
        """Test parsing code list item."""
        item = CodeListItem.model_validate(sample_code_list_results[0])
        assert item.id == "1"
        assert item.display_title == "Code civil"
        assert item.cid == "LEGITEXT000006070721"
        assert item.etat == "VIGUEUR"


class TestGenericDocumentResponse:
    """Test GenericDocumentResponse Pydantic model."""

    def test_article_wrapper(self, sample_document_response):
        """Test parsing with article wrapper."""
        response = GenericDocumentResponse.model_validate(sample_document_response)
        doc_data = response.get_document_data()
        assert doc_data is not None
        assert doc_data["id"] == "LEGIARTI000032041571"

    def test_text_wrapper(self):
        """Test parsing with text wrapper."""
        data = {"text": {"id": "JURITEXT000001", "titre": "Decision"}}
        response = GenericDocumentResponse.model_validate(data)
        doc_data = response.get_document_data()
        assert doc_data is not None
        assert doc_data["id"] == "JURITEXT000001"

    def test_acco_wrapper(self):
        """Test parsing with acco wrapper."""
        data = {"acco": {"id": "ACCOTEXT000001", "titre": "Accord"}}
        response = GenericDocumentResponse.model_validate(data)
        doc_data = response.get_document_data()
        assert doc_data is not None
        assert doc_data["id"] == "ACCOTEXT000001"

    def test_direct_structure(self):
        """Test parsing direct structured response."""
        data = {
            "id": "LEGITEXT000001",
            "titre": "Code civil",
            "nature": "CODE",
            "sections": [{"title": "Section 1"}],
        }
        response = GenericDocumentResponse.model_validate(data)
        doc_data = response.get_document_data()
        assert doc_data is not None
        assert doc_data["id"] == "LEGITEXT000001"

    def test_validate_document_response_helper(self, sample_document_response):
        """Test helper function."""
        response = validate_document_response(sample_document_response)
        assert response.get_document_data() is not None
