"""Tests for Legifrance input validation models."""

import pytest
from pydantic import ValidationError

from chat.tools.legifrance.core.inputs import (
    EtatTexte,
    GetDocumentInput,
    Juridiction,
    ListCodesInput,
    SearchAdminInput,
    SearchCodeArticleInput,
    SearchCodesLoisInput,
    SearchConventionsInput,
    SearchJurisprudenceInput,
    SortOrder,
    TypeSourceAdmin,
    TypeSourceCode,
    TypeSourceConvention,
    validate_input,
)


class TestSearchCodesLoisInput:
    """Test SearchCodesLoisInput validation."""

    def test_valid_input(self):
        """Test valid input passes validation."""
        inp = SearchCodesLoisInput(
            query="article 1240",
            type_source=TypeSourceCode.CODE,
            code_name="Code civil",
            date="2024-01-15",
        )
        assert inp.query == "article 1240"
        assert inp.type_source == TypeSourceCode.CODE
        assert inp.date == "2024-01-15"

    def test_empty_query_fails(self):
        """Test empty query raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SearchCodesLoisInput(query="", code_name="Code civil")
        assert "query" in str(exc_info.value).lower()

    def test_whitespace_query_fails(self):
        """Test whitespace-only query raises validation error."""
        with pytest.raises(ValidationError):
            SearchCodesLoisInput(query="   ", code_name="Code civil")

    def test_invalid_date_format(self):
        """Test invalid date format raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SearchCodesLoisInput(query="test", date="15/01/2024")
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_invalid_date_value(self):
        """Test invalid date value raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SearchCodesLoisInput(query="test", date="2024-02-30")
        assert "invalide" in str(exc_info.value).lower()

    def test_invalid_type_source(self):
        """Test invalid type_source raises validation error."""
        with pytest.raises(ValidationError):
            SearchCodesLoisInput(query="test", type_source="INVALID")

    def test_query_stripped(self):
        """Test query whitespace is stripped."""
        inp = SearchCodesLoisInput(query="  test query  ")
        assert inp.query == "test query"


class TestSearchJurisprudenceInput:
    """Test SearchJurisprudenceInput validation."""

    def test_valid_input(self):
        """Test valid input passes validation."""
        inp = SearchJurisprudenceInput(
            query="responsabilité",
            date="2024-01-15",
            juridiction=Juridiction.JUDICIAIRE,
            sort=SortOrder.DATE_DESC,
        )
        assert inp.query == "responsabilité"
        assert inp.juridiction == Juridiction.JUDICIAIRE
        assert inp.sort == SortOrder.DATE_DESC

    def test_invalid_juridiction(self):
        """Test invalid juridiction raises validation error."""
        with pytest.raises(ValidationError):
            SearchJurisprudenceInput(query="test", juridiction="INVALID")

    def test_all_juridiction_values(self):
        """Test all valid juridiction values."""
        for jur in Juridiction:
            inp = SearchJurisprudenceInput(query="test", juridiction=jur)
            assert inp.juridiction == jur

    def test_all_sort_values(self):
        """Test all valid sort values."""
        for sort in SortOrder:
            inp = SearchJurisprudenceInput(query="test", sort=sort)
            assert inp.sort == sort


class TestSearchConventionsInput:
    """Test SearchConventionsInput validation."""

    def test_valid_input(self):
        """Test valid input passes validation."""
        inp = SearchConventionsInput(
            query="salaire minimum",
            type_source=TypeSourceConvention.KALI,
            idcc="1090",
        )
        assert inp.query == "salaire minimum"
        assert inp.idcc == "1090"

    def test_invalid_idcc_format(self):
        """Test non-numeric IDCC raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SearchConventionsInput(query="test", idcc="ABC")
        assert "IDCC" in str(exc_info.value)

    def test_valid_idcc_numeric(self):
        """Test numeric IDCC is accepted."""
        inp = SearchConventionsInput(query="test", idcc="1234")
        assert inp.idcc == "1234"

    def test_etat_texte_values(self):
        """Test valid etat_texte values."""
        for etat in EtatTexte:
            inp = SearchConventionsInput(query="test", etat_texte=etat)
            assert inp.etat_texte == etat


class TestSearchAdminInput:
    """Test SearchAdminInput validation."""

    def test_valid_input(self):
        """Test valid input passes validation."""
        inp = SearchAdminInput(
            query="décret",
            source=TypeSourceAdmin.JORF,
            nor="ECOX2300001A",
        )
        assert inp.query == "décret"
        assert inp.source == TypeSourceAdmin.JORF

    def test_all_source_values(self):
        """Test all valid source values."""
        for src in TypeSourceAdmin:
            inp = SearchAdminInput(query="test", source=src)
            assert inp.source == src

    def test_nor_format_validation(self):
        """Test NOR format validation (12 chars)."""
        # Valid NOR
        inp = SearchAdminInput(query="test", nor="ECOX2300001A")
        assert inp.nor == "ECOX2300001A"

        # Invalid NOR (wrong length)
        with pytest.raises(ValidationError) as exc_info:
            SearchAdminInput(query="test", nor="ABC")
        assert "NOR" in str(exc_info.value)

    def test_nor_uppercased(self):
        """Test NOR is uppercased."""
        inp = SearchAdminInput(query="test", nor="ecox2300001a")
        assert inp.nor == "ECOX2300001A"


class TestGetDocumentInput:
    """Test GetDocumentInput validation."""

    def test_valid_legiarti(self):
        """Test valid LEGIARTI ID passes."""
        inp = GetDocumentInput(article_id="LEGIARTI000006417749")
        assert inp.article_id == "LEGIARTI000006417749"

    def test_valid_juritext(self):
        """Test valid JURITEXT ID passes."""
        inp = GetDocumentInput(article_id="JURITEXT000007023001")
        assert inp.article_id == "JURITEXT000007023001"

    def test_valid_numeric_id(self):
        """Test numeric ID (for circulaires) passes."""
        inp = GetDocumentInput(article_id="12345")
        assert inp.article_id == "12345"

    def test_empty_id_fails(self):
        """Test empty ID raises validation error."""
        with pytest.raises(ValidationError):
            GetDocumentInput(article_id="")

    def test_invalid_prefix_fails(self):
        """Test invalid prefix raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GetDocumentInput(article_id="INVALID000001")
        assert "Format" in str(exc_info.value)

    def test_id_uppercased(self):
        """Test ID is uppercased."""
        inp = GetDocumentInput(article_id="legiarti000006417749")
        assert inp.article_id == "LEGIARTI000006417749"

    def test_all_valid_prefixes(self):
        """Test all valid ID prefixes."""
        prefixes = [
            "LEGIARTI",
            "LEGITEXT",
            "JURITEXT",
            "CETATEXT",
            "CONSTEXT",
            "JUFITEXT",
            "CNILTEXT",
            "ACCOTEXT",
            "JORFTEXT",
            "JORFARTI",
            "KALITEXT",
            "KALIARTI",
        ]
        for prefix in prefixes:
            inp = GetDocumentInput(article_id=f"{prefix}000000001")
            assert inp.article_id.startswith(prefix)


class TestSearchCodeArticleInput:
    """Test SearchCodeArticleInput validation."""

    def test_valid_input(self):
        """Test valid input passes validation."""
        inp = SearchCodeArticleInput(code_name="Code civil", article_num="1240")
        assert inp.code_name == "Code civil"
        assert inp.article_num == "1240"

    def test_empty_code_name_fails(self):
        """Test empty code_name raises validation error."""
        with pytest.raises(ValidationError):
            SearchCodeArticleInput(code_name="", article_num="1240")

    def test_empty_article_num_fails(self):
        """Test empty article_num raises validation error."""
        with pytest.raises(ValidationError):
            SearchCodeArticleInput(code_name="Code civil", article_num="")

    def test_complex_article_num(self):
        """Test complex article numbers pass."""
        inp = SearchCodeArticleInput(code_name="Code civil", article_num="L123-4-5")
        assert inp.article_num == "L123-4-5"


class TestListCodesInput:
    """Test ListCodesInput validation."""

    def test_empty_code_name_allowed(self):
        """Test empty code_name is allowed."""
        inp = ListCodesInput(code_name="")
        assert inp.code_name == ""

    def test_code_name_stripped(self):
        """Test code_name whitespace is stripped."""
        inp = ListCodesInput(code_name="  urbanisme  ")
        assert inp.code_name == "urbanisme"


class TestValidateInputHelper:
    """Test validate_input helper function."""

    def test_valid_input_returns_model(self):
        """Test valid input returns validated model."""
        result = validate_input(
            SearchCodesLoisInput,
            query="test",
            code_name="Code civil",
        )
        assert isinstance(result, SearchCodesLoisInput)
        assert result.query == "test"

    def test_invalid_input_raises_value_error(self):
        """Test invalid input raises ValueError with friendly message."""
        with pytest.raises(ValueError) as exc_info:
            validate_input(SearchCodesLoisInput, query="", code_name="Code civil")
        assert "Paramètres invalides" in str(exc_info.value)

    def test_error_message_contains_field(self):
        """Test error message mentions the invalid field."""
        with pytest.raises(ValueError) as exc_info:
            validate_input(SearchConventionsInput, query="test", idcc="ABC")
        error_msg = str(exc_info.value)
        assert "IDCC" in error_msg


class TestEnums:
    """Test enum string values."""

    def test_type_source_code_values(self):
        """Test TypeSourceCode enum values."""
        assert TypeSourceCode.CODE.value == "CODE"
        assert TypeSourceCode.CODE_DATE.value == "CODE_DATE"
        assert TypeSourceCode.LODA.value == "LODA"

    def test_juridiction_values(self):
        """Test Juridiction enum values."""
        assert Juridiction.JUDICIAIRE.value == "JUDICIAIRE"
        assert Juridiction.ADMINISTRATIF.value == "ADMINISTRATIF"
        assert Juridiction.CONSTITUTIONNEL.value == "CONSTITUTIONNEL"
        assert Juridiction.FINANCIER.value == "FINANCIER"

    def test_sort_order_values(self):
        """Test SortOrder enum values."""
        assert SortOrder.PERTINENCE.value == "PERTINENCE"
        assert SortOrder.DATE_DESC.value == "DATE_DESC"
        assert SortOrder.DATE_ASC.value == "DATE_ASC"
