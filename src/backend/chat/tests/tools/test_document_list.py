"""Tests for document_list tool — Feature 12: Document Tools."""

from unittest import mock

import pytest
from pydantic_ai import RunContext

from chat.tools.document_list import document_list


@pytest.fixture()
def mocked_context():
    mock_ctx = mock.Mock(spec=RunContext)
    mock_ctx.deps = mock.Mock()
    mock_ctx.deps.conversation = mock.Mock()
    return mock_ctx


@pytest.mark.asyncio
async def test_returns_documents_list(mocked_context):
    """Should return indexed document list ordered by created_at."""
    mocked_context.deps.conversation.attachments.filter.return_value.values.return_value.order_by.return_value = [
        {"file_name": "a.txt", "content_type": "text/plain", "size": 100, "created_at": "2025-01-01"},
        {"file_name": "b.md", "content_type": "text/markdown", "size": 200, "created_at": "2025-01-02"},
    ]

    result = await document_list(mocked_context)

    docs = result.return_value["documents"]
    assert len(docs) == 2
    assert docs[0]["index"] == 1
    assert docs[0]["name"] == "a.txt"
    assert docs[1]["index"] == 2
    assert docs[1]["size_bytes"] == 200
    assert result.return_value["total"] == 2


@pytest.mark.asyncio
async def test_empty_conversation(mocked_context):
    """Should return message when no documents found."""
    mocked_context.deps.conversation.attachments.filter.return_value.values.return_value.order_by.return_value = []

    result = await document_list(mocked_context)

    assert result.return_value["documents"] == []
    assert "No documents" in result.return_value["message"]


@pytest.mark.asyncio
async def test_filters_text_content_type(mocked_context):
    """Should filter by content_type__startswith='text/'."""
    mocked_context.deps.conversation.attachments.filter.return_value.values.return_value.order_by.return_value = []

    await document_list(mocked_context)

    mocked_context.deps.conversation.attachments.filter.assert_called_once_with(
        content_type__startswith="text/",
    )


@pytest.mark.asyncio
async def test_exception_returns_error(mocked_context):
    """Should catch exceptions and return error dict."""
    mocked_context.deps.conversation.attachments.filter.side_effect = RuntimeError("db error")

    result = await document_list(mocked_context)

    assert "error" in result.return_value
    assert result.return_value["documents"] == []
