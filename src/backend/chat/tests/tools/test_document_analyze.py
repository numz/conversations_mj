"""Tests for document_analyze tool — Feature 12: Document Tools."""

import io
from unittest import mock

import pytest
from django.core.files.storage import default_storage
from pydantic_ai.exceptions import ModelRetry

from chat.tools.document_analyze import AnalysisType, document_analyze
from chat.tools.exceptions import ModelCannotRetry


@pytest.fixture()
def mocked_context():
    ctx = mock.Mock()
    ctx.deps = mock.Mock()
    ctx.deps.conversation = mock.Mock()
    ctx.usage = mock.Mock()
    ctx.retries = {}
    ctx.max_retries = 2
    ctx.tool_name = "analyze_documents"
    return ctx


def _make_attachment(file_name, content, size=None):
    att = mock.Mock()
    att.file_name = file_name
    att.key = f"attachments/{file_name}"
    att.content_type = "text/plain"
    att.size = size or len(content)
    att._content = content
    return att


# ------------------------------------------------------------------ #
# AnalysisType enum
# ------------------------------------------------------------------ #
class TestAnalysisType:
    def test_valid_types(self):
        assert AnalysisType("compare") == AnalysisType.COMPARE
        assert AnalysisType("match") == AnalysisType.MATCH
        assert AnalysisType("compliance") == AnalysisType.COMPLIANCE
        assert AnalysisType("extract") == AnalysisType.EXTRACT
        assert AnalysisType("cross_reference") == AnalysisType.CROSS_REFERENCE

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            AnalysisType("invalid")


# ------------------------------------------------------------------ #
# Validation tests (decorator catches ModelCannotRetry, returns string)
# ------------------------------------------------------------------ #
class TestDocumentAnalyzeValidation:
    @pytest.mark.asyncio
    async def test_invalid_analysis_type(self, mocked_context):
        result = await document_analyze(
            mocked_context,
            document_names=["a.txt", "b.txt"],
            analysis_type="bogus",
        )
        assert "Invalid analysis_type" in result

    @pytest.mark.asyncio
    async def test_less_than_two_documents(self, mocked_context):
        result = await document_analyze(
            mocked_context,
            document_names=["only_one.txt"],
            analysis_type="compare",
        )
        assert "At least 2 documents" in result

    @pytest.mark.asyncio
    async def test_empty_document_names(self, mocked_context):
        result = await document_analyze(
            mocked_context,
            document_names=[],
            analysis_type="compare",
        )
        assert "At least 2 documents" in result

    @pytest.mark.asyncio
    async def test_not_enough_documents_found(self, settings, mocked_context):
        settings.DOCUMENT_CONTENT_MAX_SIZE = 100000
        att = _make_attachment("a.txt", "content a")
        mocked_context.deps.conversation.attachments.filter.return_value.filter.return_value = [att]

        result = await document_analyze(
            mocked_context,
            document_names=["a.txt", "missing.txt"],
            analysis_type="compare",
        )
        assert "Could not find enough" in result

    @pytest.mark.asyncio
    async def test_cumulative_size_exceeds_limit(self, settings, mocked_context):
        settings.DOCUMENT_CONTENT_MAX_SIZE = 100
        att1 = _make_attachment("a.txt", "x" * 80, size=80)
        att2 = _make_attachment("b.txt", "y" * 80, size=80)
        mocked_context.deps.conversation.attachments.filter.return_value.filter.return_value = [att1, att2]

        result = await document_analyze(
            mocked_context,
            document_names=["a.txt", "b.txt"],
            analysis_type="compare",
        )
        assert "cumulative size" in result


# ------------------------------------------------------------------ #
# Success path
# ------------------------------------------------------------------ #
class TestDocumentAnalyzeSuccess:
    @pytest.mark.asyncio
    async def test_successful_analysis(self, settings, mocked_context):
        settings.DOCUMENT_CONTENT_MAX_SIZE = 100000
        att1 = _make_attachment("cv.txt", "Skills: Python, Django")
        att2 = _make_attachment("job.txt", "Required: Python, Flask")
        mocked_context.deps.conversation.attachments.filter.return_value.filter.return_value = [att1, att2]

        def _open_side_effect(key):
            if "cv.txt" in key:
                return io.BytesIO(b"Skills: Python, Django")
            return io.BytesIO(b"Required: Python, Flask")

        mock_agent_result = mock.Mock()
        mock_agent_result.output = "## Analysis\nBoth mention Python."

        with mock.patch.object(default_storage, "open", side_effect=_open_side_effect):
            with mock.patch("chat.tools.document_analyze.SummarizationAgent") as MockAgent:
                MockAgent.return_value.run = mock.AsyncMock(return_value=mock_agent_result)

                result = await document_analyze(
                    mocked_context,
                    document_names=["cv.txt", "job.txt"],
                    analysis_type="match",
                )

        assert "Analysis" in result.return_value
        assert "cv.txt" in result.metadata["sources"]
        assert "job.txt" in result.metadata["sources"]
        assert result.metadata["analysis_type"] == "match"

    @pytest.mark.asyncio
    async def test_custom_instructions_included(self, settings, mocked_context):
        settings.DOCUMENT_CONTENT_MAX_SIZE = 100000
        att1 = _make_attachment("a.txt", "content a")
        att2 = _make_attachment("b.txt", "content b")
        mocked_context.deps.conversation.attachments.filter.return_value.filter.return_value = [att1, att2]

        mock_agent_result = mock.Mock()
        mock_agent_result.output = "Result"

        def _open_side_effect(key):
            return io.BytesIO(b"text content")

        with mock.patch.object(default_storage, "open", side_effect=_open_side_effect):
            with mock.patch("chat.tools.document_analyze.SummarizationAgent") as MockAgent:
                mock_run = mock.AsyncMock(return_value=mock_agent_result)
                MockAgent.return_value.run = mock_run

                await document_analyze(
                    mocked_context,
                    document_names=["a.txt", "b.txt"],
                    analysis_type="compare",
                    instructions="Focus on pricing",
                )

                prompt_arg = mock_run.call_args[0][0]
                assert "Focus on pricing" in prompt_arg
