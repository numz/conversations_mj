"""Tests for Legifrance URL generation utilities."""

import pytest

from chat.tools.legifrance.core.urls import get_legifrance_url


class TestGetLegifranceUrl:
    """Test get_legifrance_url function."""

    def test_empty_rid_returns_empty(self):
        """Test empty RID returns empty string."""
        assert get_legifrance_url("", "CODE_DATE") == ""
        assert get_legifrance_url(None, "CODE_DATE") == ""

    def test_legiarti_url(self):
        """Test LEGIARTI (code article) URL generation."""
        url = get_legifrance_url("LEGIARTI000006417749", "CODE_DATE")
        assert "legifrance.gouv.fr" in url
        assert "codes/article_lc" in url
        assert "LEGIARTI000006417749" in url

    def test_legitext_url(self):
        """Test LEGITEXT (code texte) URL generation."""
        url = get_legifrance_url("LEGITEXT000006070721", "CODE_DATE")
        assert "legifrance.gouv.fr" in url
        assert "codes/texte_lc" in url
        assert "LEGITEXT000006070721" in url

    def test_juritext_url_by_prefix(self):
        """Test JURITEXT URL generation by prefix."""
        url = get_legifrance_url("JURITEXT000007026421", "")
        assert "legifrance.gouv.fr" in url
        assert "juri" in url.lower()
        assert "JURITEXT000007026421" in url

    def test_juritext_url_by_fond(self):
        """Test jurisprudence URL generation by fond."""
        url = get_legifrance_url("SOMETEXT123", "JURI")
        assert "juri" in url.lower()

    def test_cetatext_url(self):
        """Test CETATEXT (Conseil d'Etat) URL generation."""
        url = get_legifrance_url("CETATEXT000001", "")
        assert "legifrance.gouv.fr" in url
        assert "ceta" in url.lower()

    def test_cetat_fond_url(self):
        """Test CETAT fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "CETAT")
        assert "ceta" in url.lower()

    def test_constext_url(self):
        """Test CONSTEXT (Conseil Constitutionnel) URL generation."""
        url = get_legifrance_url("CONSTEXT000001", "")
        assert "legifrance.gouv.fr" in url
        assert "cons" in url.lower()

    def test_constit_fond_url(self):
        """Test CONSTIT fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "CONSTIT")
        assert "cons" in url.lower()

    def test_jufitext_url(self):
        """Test JUFITEXT (juridictions financières) URL generation."""
        url = get_legifrance_url("JUFITEXT000001", "")
        assert "jufi" in url.lower()

    def test_jufi_fond_url(self):
        """Test JUFI fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "JUFI")
        assert "jufi" in url.lower()

    def test_cniltext_url(self):
        """Test CNILTEXT (CNIL decisions) URL generation."""
        url = get_legifrance_url("CNILTEXT000001", "")
        assert "cnil" in url.lower()

    def test_cnil_fond_url(self):
        """Test CNIL fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "CNIL")
        assert "cnil" in url.lower()

    def test_accotext_url(self):
        """Test ACCOTEXT (accords entreprise) URL generation."""
        url = get_legifrance_url("ACCOTEXT000001", "")
        assert "acco" in url.lower()

    def test_acco_fond_url(self):
        """Test ACCO fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "ACCO")
        assert "acco" in url.lower()

    def test_jorftext_url(self):
        """Test JORFTEXT (Journal Officiel) URL generation."""
        url = get_legifrance_url("JORFTEXT000001", "")
        assert "jorf" in url.lower()

    def test_jorf_fond_url(self):
        """Test JORF fond URL generation."""
        url = get_legifrance_url("SOMETEXT", "JORF")
        assert "jorf" in url.lower()

    def test_jorfarti_url(self):
        """Test JORFARTI URL generation."""
        url = get_legifrance_url("JORFARTI000001", "")
        assert "jorf" in url.lower()

    def test_kalitext_url(self):
        """Test KALITEXT (conventions collectives) URL generation."""
        url = get_legifrance_url("KALITEXT000001", "")
        assert "conv_coll" in url.lower()
        assert "KALITEXT000001" in url

    def test_kaliarti_url(self):
        """Test KALIARTI (convention articles) URL generation."""
        url = get_legifrance_url("KALIARTI000001", "")
        assert "conv_coll" in url.lower()
        assert "article" in url.lower()

    def test_circ_fond_url(self):
        """Test CIRC (circulaires) fond URL generation."""
        url = get_legifrance_url("12345", "CIRC")
        assert "circulaire" in url.lower()  # UI path is "circulaire/id"

    def test_loda_fond_url(self):
        """Test LODA fond URL generation with LEGIARTI ID (uses codes path)."""
        # LEGIARTI IDs are code articles and take precedence over fond
        url = get_legifrance_url("LEGIARTI000001", "LODA_DATE")
        assert "codes/article_lc" in url.lower()
        assert "LEGIARTI000001" in url

    def test_loda_fond_url_generic_id(self):
        """Test LODA fond URL generation with generic ID."""
        url = get_legifrance_url("SOMETEXT000001", "LODA_DATE")
        assert "loda" in url.lower()

    def test_cehr_url(self):
        """Test CEHR (CEDH) URL generation."""
        url = get_legifrance_url("CEHR000001", "")
        assert "ceta" in url.lower()

    def test_unknown_id_returns_empty(self):
        """Test unknown ID prefix with unknown fond returns empty."""
        url = get_legifrance_url("UNKNOWN000001", "UNKNOWN_FOND")
        assert url == ""

    def test_url_contains_base(self):
        """Test all URLs contain the base Legifrance URL."""
        test_cases = [
            ("LEGIARTI000001", "CODE_DATE"),
            ("LEGITEXT000001", "CODE"),
            ("JURITEXT000001", "JURI"),
            ("KALITEXT000001", "KALI"),
        ]
        for rid, fond in test_cases:
            url = get_legifrance_url(rid, fond)
            if url:
                assert "legifrance.gouv.fr" in url
