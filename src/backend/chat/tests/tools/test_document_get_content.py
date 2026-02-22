"""Tests for document_get_content tool — Feature 12: Document Tools."""

import io
from unittest import mock

import pytest
from django.core.files.storage import default_storage

from chat.tools.document_get_content import document_get_content
from chat.tools.exceptions import ModelCannotRetry


@pytest.fixture()
def mocked_context():
    ctx = mock.Mock()
    ctx.deps = mock.Mock()
    ctx.deps.conversation = mock.Mock()
    return ctx


def _make_attachment(file_name="doc.txt", key="attachments/doc.txt", content_type="text/plain", size=50):
    att = mock.Mock()
    att.file_name = file_name
    att.key = key
    att.content_type = content_type
    att.size = size
    return att


@pytest.mark.asyncio
async def test_returns_content(settings, mocked_context):
    """Should return full text content of a matching document."""
    settings.DOCUMENT_CONTENT_MAX_SIZE = 10000
    att = _make_attachment()

    mocked_context.deps.conversation.attachments.filter.return_value.first.return_value = att

    with mock.patch.object(
        default_storage, "open",
        return_value=io.BytesIO(b"Hello world"),
    ):
        result = await document_get_content(mocked_context, document_name="doc.txt")

    assert result.return_value == "Hello world"
    assert result.metadata["document_name"] == "doc.txt"


@pytest.mark.asyncio
async def test_truncates_with_max_length(settings, mocked_context):
    """Should truncate content when max_length is specified."""
    settings.DOCUMENT_CONTENT_MAX_SIZE = 10000
    att = _make_attachment()

    mocked_context.deps.conversation.attachments.filter.return_value.first.return_value = att

    with mock.patch.object(
        default_storage, "open",
        return_value=io.BytesIO(b"A" * 500),
    ):
        result = await document_get_content(mocked_context, document_name="doc.txt", max_length=100)

    assert len(result.return_value) < 500
    assert "truncated" in result.return_value


@pytest.mark.asyncio
async def test_document_not_found_raises(mocked_context):
    """Should raise ModelCannotRetry when document not found."""
    mocked_context.deps.conversation.attachments.filter.return_value.first.return_value = None
    mocked_context.deps.conversation.attachments.filter.return_value.values_list.return_value = ["other.pdf"]

    with pytest.raises(ModelCannotRetry, match="No text content found"):
        await document_get_content(mocked_context, document_name="missing.txt")


@pytest.mark.asyncio
async def test_too_large_raises(settings, mocked_context):
    """Should raise ModelCannotRetry when document exceeds size limit."""
    settings.DOCUMENT_CONTENT_MAX_SIZE = 100
    att = _make_attachment(size=999)

    mocked_context.deps.conversation.attachments.filter.return_value.first.return_value = att

    with pytest.raises(ModelCannotRetry, match="too large"):
        await document_get_content(mocked_context, document_name="doc.txt")
