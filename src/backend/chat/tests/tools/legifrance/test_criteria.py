"""Tests for Legifrance search criteria builders."""

import pytest

from chat.tools.legifrance.core.criteria import (
    SearchCriterion,
    SearchField,
    SearchFilter,
    build_default_criteria,
)


class TestSearchCriterion:
    """Test SearchCriterion dataclass."""

    def test_create_criterion(self):
        """Test creating a search criterion."""
        criterion = SearchCriterion(
            typeRecherche="EXACTE",
            valeur="article 1240",
        )
        assert criterion.typeRecherche == "EXACTE"
        assert criterion.valeur == "article 1240"
        assert criterion.operateur == "ET"  # default
        assert criterion.proximite is None  # default

    def test_create_criterion_with_all_fields(self):
        """Test creating criterion with all fields."""
        criterion = SearchCriterion(
            typeRecherche="UN_DES_MOTS",
            valeur="responsabilité civile",
            operateur="OU",
            proximite=5,
        )
        assert criterion.typeRecherche == "UN_DES_MOTS"
        assert criterion.operateur == "OU"
        assert criterion.proximite == 5

    def test_to_dict_basic(self):
        """Test converting criterion to dict without proximite."""
        criterion = SearchCriterion(
            typeRecherche="EXACTE",
            valeur="test",
        )
        d = criterion.to_dict()
        assert d == {
            "typeRecherche": "EXACTE",
            "valeur": "test",
            "operateur": "ET",
        }
        assert "proximite" not in d

    def test_to_dict_with_proximite(self):
        """Test converting criterion to dict with proximite."""
        criterion = SearchCriterion(
            typeRecherche="UN_DES_MOTS",
            valeur="test",
            proximite=3,
        )
        d = criterion.to_dict()
        assert d["proximite"] == 3


class TestSearchField:
    """Test SearchField dataclass."""

    def test_create_field(self):
        """Test creating a search field."""
        criteria = [
            SearchCriterion(typeRecherche="EXACTE", valeur="test"),
        ]
        field = SearchField(typeChamp="ALL", criteres=criteria)
        assert field.typeChamp == "ALL"
        assert len(field.criteres) == 1
        assert field.operateur == "ET"  # default

    def test_to_dict(self):
        """Test converting field to dict."""
        criteria = [
            SearchCriterion(typeRecherche="EXACTE", valeur="test1"),
            SearchCriterion(typeRecherche="UN_DES_MOTS", valeur="test2"),
        ]
        field = SearchField(typeChamp="TITLE", criteres=criteria, operateur="OU")
        d = field.to_dict()

        assert d["typeChamp"] == "TITLE"
        assert d["operateur"] == "OU"
        assert len(d["criteres"]) == 2
        assert d["criteres"][0]["valeur"] == "test1"
        assert d["criteres"][1]["valeur"] == "test2"


class TestSearchFilter:
    """Test SearchFilter dataclass."""

    def test_create_filter_with_valeurs(self):
        """Test creating filter with values."""
        f = SearchFilter(facette="NOM_CODE", valeurs=["Code civil", "Code pénal"])
        assert f.facette == "NOM_CODE"
        assert f.valeurs == ["Code civil", "Code pénal"]
        assert f.singleDate is None

    def test_create_filter_with_single_date(self):
        """Test creating filter with single date."""
        f = SearchFilter(facette="DATE_VERSION", singleDate=1609459200000)
        assert f.facette == "DATE_VERSION"
        assert f.singleDate == 1609459200000
        assert f.valeurs is None

    def test_to_dict_with_valeurs(self):
        """Test converting filter with valeurs to dict."""
        f = SearchFilter(facette="ETAT", valeurs=["VIGUEUR"])
        d = f.to_dict()
        assert d == {"facette": "ETAT", "valeurs": ["VIGUEUR"]}
        assert "singleDate" not in d

    def test_to_dict_with_single_date(self):
        """Test converting filter with singleDate to dict."""
        f = SearchFilter(facette="DATE_DECISION", singleDate=1609459200000)
        d = f.to_dict()
        assert d == {"facette": "DATE_DECISION", "singleDate": 1609459200000}
        assert "valeurs" not in d

    def test_to_dict_with_both(self):
        """Test converting filter with both values to dict."""
        f = SearchFilter(
            facette="CUSTOM",
            valeurs=["value1"],
            singleDate=1609459200000,
        )
        d = f.to_dict()
        assert d["facette"] == "CUSTOM"
        assert d["valeurs"] == ["value1"]
        assert d["singleDate"] == 1609459200000


class TestBuildDefaultCriteria:
    """Test build_default_criteria function."""

    def test_build_default_criteria_all_field(self):
        """Test building criteria for ALL field."""
        criteria = build_default_criteria("test query")
        assert len(criteria) == 1

        field = criteria[0]
        assert field.typeChamp == "ALL"
        assert len(field.criteres) == 1

        criterion = field.criteres[0]
        assert criterion.typeRecherche == "UN_DES_MOTS"
        assert criterion.valeur == "test query"
        assert criterion.proximite == 2

    def test_build_default_criteria_custom_field(self):
        """Test building criteria for custom field."""
        criteria = build_default_criteria("test", search_field="TITLE")
        assert len(criteria) == 1

        field = criteria[0]
        assert field.typeChamp == "TITLE"
        assert len(field.criteres) == 1

        # Custom field should not have proximite
        criterion = field.criteres[0]
        assert criterion.proximite is None

    def test_build_default_criteria_custom_operator(self):
        """Test building criteria with custom operator."""
        criteria = build_default_criteria("test", operator="OU")
        assert criteria[0].operateur == "OU"
        assert criteria[0].criteres[0].operateur == "OU"

    def test_build_default_criteria_returns_list(self):
        """Test that build_default_criteria always returns a list."""
        criteria = build_default_criteria("")
        assert isinstance(criteria, list)
