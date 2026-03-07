"""Common test fixtures for Legifrance tools tests."""

from unittest.mock import Mock

import pytest
from pydantic_ai import RunContext, RunUsage


@pytest.fixture(autouse=True)
def legifrance_settings(settings):
    """Define Legifrance settings for tests."""
    settings.LEGIFRANCE_API_BASE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app"
    settings.LEGIFRANCE_OAUTH_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
    settings.LEGIFRANCE_CLIENT_ID = "test_client_id"
    settings.LEGIFRANCE_CLIENT_SECRET = "test_client_secret"
    settings.LEGIFRANCE_SSL_VERIFY = False
    settings.LEGIFRANCE_OAUTH_HOST = ""
    settings.LEGIFRANCE_API_HOST = ""
    settings.LEGIFRANCE_API_TOKEN = "test_token"
    return settings


@pytest.fixture(name="mocked_context")
def fixture_mocked_context():
    """Fixture for a mocked RunContext."""
    mock_ctx = Mock(spec=RunContext)
    mock_ctx.usage = RunUsage(input_tokens=0, output_tokens=0)
    mock_ctx.max_retries = 2
    mock_ctx.retries = {}
    mock_ctx.tool_name = "legifrance_test_tool"
    return mock_ctx


@pytest.fixture
def sample_search_results():
    """Sample search results from Legifrance API."""
    return [
        {
            "id": "LEGIARTI000006417749",
            "titles": [
                {"id": "LEGITEXT000006070721", "title": "Code civil", "cid": "LEGITEXT000006070721"}
            ],
            "sections": [
                {
                    "title": "Des contrats et des obligations conventionnelles en général",
                    "extracts": [
                        {
                            "id": "LEGIARTI000032041571",
                            "num": "1240",
                            "title": "Article 1240",
                            "legalStatus": "VIGUEUR",
                            "values": [
                                "Tout fait quelconque de l'homme, qui cause à autrui un dommage..."
                            ],
                        }
                    ],
                }
            ],
            "etat": "VIGUEUR",
            "nature": "CODE",
        }
    ]


@pytest.fixture
def sample_juri_results():
    """Sample jurisprudence results from Legifrance API."""
    return [
        {
            "id": "JURITEXT000007026421",
            "titles": [
                {"id": "JURITEXT000007026421", "title": "Cour de cassation, Chambre civile 1"}
            ],
            "juridiction": "Cour de cassation",
            "date": "2020-01-15",
            "etat": "VIGUEUR",
        }
    ]


@pytest.fixture
def sample_document_response():
    """Sample document response from Legifrance API."""
    return {
        "article": {
            "id": "LEGIARTI000032041571",
            "num": "1240",
            "title": "Article 1240",
            "text": "Tout fait quelconque de l'homme, qui cause à autrui un dommage, oblige celui par la faute duquel il est arrivé à le réparer.",
            "textTitles": [{"titre": "Code civil"}],
            "dateDebut": 1475366400000,
            "etat": "VIGUEUR",
        }
    }


@pytest.fixture
def sample_code_list_results():
    """Sample code list results from Legifrance API."""
    return [
        {"id": "1", "title": "Code civil", "cid": "LEGITEXT000006070721", "etat": "VIGUEUR"},
        {"id": "2", "title": "Code pénal", "cid": "LEGITEXT000006070719", "etat": "VIGUEUR"},
    ]


@pytest.fixture
def sample_oauth_response():
    """Sample OAuth token response."""
    return {"access_token": "new_test_token", "token_type": "bearer", "expires_in": 3600}
