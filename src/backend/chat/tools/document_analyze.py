"""Analysis tool for comparing and cross-referencing documents."""

import logging
from enum import Enum

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q

from asgiref.sync import sync_to_async
from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ToolReturn

from chat.agents.summarize import SummarizationAgent
from chat.tools.exceptions import ModelCannotRetry
from chat.tools.utils import last_model_retry_soft_fail

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """Types of document analysis."""

    COMPARE = "compare"  # Compare documents, find similarities and differences
    MATCH = "match"  # Evaluate how well documents match (CV vs job posting)
    COMPLIANCE = "compliance"  # Check if a document complies with a reference
    EXTRACT = "extract"  # Extract and compare specific information
    CROSS_REFERENCE = "cross_reference"  # Cross-reference information between documents


ANALYSIS_PROMPTS = {
    AnalysisType.COMPARE: (
        "Compare the following documents and provide a detailed analysis:\n"
        "- Identify key similarities between the documents\n"
        "- Highlight important differences\n"
        "- Note any contradictions or inconsistencies\n"
        "- Summarize the main points of each document\n"
    ),
    AnalysisType.MATCH: (
        "Evaluate how well these documents match each other:\n"
        "- Identify matching elements and requirements met\n"
        "- List missing elements or gaps\n"
        "- Provide a compatibility score or assessment\n"
        "- Suggest improvements or areas to address\n"
        "Common use cases: CV vs job posting, proposal vs requirements, etc.\n"
    ),
    AnalysisType.COMPLIANCE: (
        "Check if the first document complies with the reference document(s):\n"
        "- List requirements from the reference document(s)\n"
        "- Check each requirement against the main document\n"
        "- Identify compliant and non-compliant elements\n"
        "- Provide recommendations for achieving compliance\n"
    ),
    AnalysisType.EXTRACT: (
        "Extract and compare specific information from these documents:\n"
        "- Identify common data points across documents\n"
        "- Create a comparison table or structured summary\n"
        "- Highlight variations in the extracted information\n"
        "Common use cases: comparing prices, dates, terms across documents.\n"
    ),
    AnalysisType.CROSS_REFERENCE: (
        "Cross-reference information between these documents:\n"
        "- Find connections and references between documents\n"
        "- Verify consistency of shared information\n"
        "- Identify information present in one but missing in others\n"
        "- Build a unified view from all sources\n"
    ),
}


@sync_to_async
def read_document_content(doc):
    """Read document content asynchronously."""
    with default_storage.open(doc.key) as f:
        return doc.file_name, f.read().decode("utf-8")


@last_model_retry_soft_fail
async def document_analyze(  # pylint: disable=too-many-locals
    ctx: RunContext,
    *,
    document_names: list[str],
    analysis_type: str = "compare",
    instructions: str | None = None,
) -> ToolReturn:
    """
    Analyze multiple documents together to compare, match, or cross-reference them.
    Use this tool when the user wants to analyze relationships between documents.

    This tool is designed for tasks like:
    - Comparing a CV with a job posting to evaluate candidate fit
    - Comparing multiple contracts or quotes to find differences
    - Checking if a document complies with a reference/specification
    - Extracting and comparing specific information across documents
    - Cross-referencing information between related documents

    Args:
        document_names: List of document names to analyze (at least 2 required).
            Use list_documents tool first to get exact document names.
        analysis_type: Type of analysis to perform:
            - "compare": Find similarities and differences between documents
            - "match": Evaluate how well documents match (e.g., CV vs job posting)
            - "compliance": Check if a document complies with reference documents
            - "extract": Extract and compare specific information
            - "cross_reference": Cross-reference information between documents
        instructions: Optional specific instructions for the analysis
            (e.g., "Focus on technical skills", "Compare prices only")

    Examples:
        - CV vs Job posting: document_analyze(document_names=["cv.pdf", "job.pdf"], analysis_type="match")
        - Compare contracts: document_analyze(document_names=["v1.pdf", "v2.pdf"], analysis_type="compare")
        - Check compliance: document_analyze(document_names=["report.pdf", "specs.pdf"], analysis_type="compliance")
    """
    try:
        # Validate analysis type
        try:
            analysis_type_enum = AnalysisType(analysis_type.lower())
        except ValueError:
            valid_types = [t.value for t in AnalysisType]
            raise ModelCannotRetry(
                f"Invalid analysis_type '{analysis_type}'. "
                f"Valid types are: {', '.join(valid_types)}. "
                "You must explain this to the user."
            )

        # Require at least 2 documents for analysis
        if not document_names or len(document_names) < 2:
            raise ModelCannotRetry(
                "At least 2 documents are required for analysis. "
                "You must explain this to the user and ask them to specify "
                "which documents to analyze using list_documents tool."
            )

        # Get documents from conversation
        attachment_filter = ctx.deps.conversation.attachments.filter(
            content_type__startswith="text/",
        )

        # Filter to only the specified documents
        name_filter = Q()
        for name in document_names:
            name_filter |= Q(file_name__icontains=name) | Q(key__icontains=name)
        attachment_filter = attachment_filter.filter(name_filter)

        text_attachments = await sync_to_async(list)(attachment_filter)

        if len(text_attachments) < 2:
            found_names = [doc.file_name for doc in text_attachments]
            raise ModelCannotRetry(
                f"Could not find enough documents matching {document_names}. "
                f"Found only: {found_names if found_names else 'none'}. "
                "You must explain this to the user and suggest using list_documents "
                "to see available documents."
            )

        # Check cumulative size against threshold before reading
        max_size = settings.DOCUMENT_CONTENT_MAX_SIZE
        cumulative_size = sum(doc.size or 0 for doc in text_attachments)
        if cumulative_size > max_size:
            doc_sizes = [
                f"{doc.file_name} ({doc.size or 0:,} bytes)"
                for doc in text_attachments
            ]
            raise ModelCannotRetry(
                f"The cumulative size of the selected documents ({cumulative_size:,} bytes) "
                f"exceeds the limit ({max_size:,} bytes). "
                f"Documents: {', '.join(doc_sizes)}. "
                "Use document_search_rag to search for specific passages in each document, "
                "or use summarize to get summaries first, then analyze the summaries."
            )

        # Read document contents
        documents = [await read_document_content(doc) for doc in text_attachments]

        logger.info(
            "[analyze] Starting %s analysis of %d documents: %s",
            analysis_type_enum.value,
            len(documents),
            [doc[0] for doc in documents],
        )

        # Build the analysis prompt
        base_prompt = ANALYSIS_PROMPTS.get(analysis_type_enum, ANALYSIS_PROMPTS[AnalysisType.COMPARE])

        # Prepare document context
        documents_context = "\n\n---\n\n".join(
            f"## Document: {doc_name}\n\n{doc_content}"
            for doc_name, doc_content in documents
        )

        # Build final prompt
        analysis_prompt = (
            f"You are an expert document analyst. Perform a {analysis_type_enum.value} analysis.\n\n"
            f"{base_prompt}\n"
        )

        if instructions:
            analysis_prompt += f"\nSpecific instructions: {instructions}\n"

        analysis_prompt += (
            f"\n### Documents to analyze:\n\n{documents_context}\n\n"
            "### Your Analysis:\n"
            "Provide a well-structured analysis in markdown format. "
            "Be thorough but concise. Use headers, bullet points, and tables where appropriate."
        )

        logger.debug("[analyze] Prompt length: %d chars", len(analysis_prompt))

        # Use the summarization agent for analysis (it's a general-purpose LLM agent)
        analysis_agent = SummarizationAgent()

        try:
            result = await analysis_agent.run(analysis_prompt, usage=ctx.usage)
        except Exception as exc:
            logger.warning("Error during document analysis: %s", exc, exc_info=True)
            raise ModelRetry("An error occurred while analyzing the documents.") from exc

        analysis_result = (result.output or "").strip()

        if not analysis_result:
            raise ModelRetry("The analysis produced an empty result.")

        logger.debug("[analyze] Analysis complete, result length: %d chars", len(analysis_result))

        return ToolReturn(
            return_value=analysis_result,
            metadata={
                "sources": {doc[0] for doc in documents},
                "analysis_type": analysis_type_enum.value,
            },
        )

    except (ModelCannotRetry, ModelRetry):
        raise
    except Exception as exc:
        logger.exception("Unexpected error in document_analyze: %s", exc)
        raise ModelCannotRetry(
            f"An unexpected error occurred during document analysis: {type(exc).__name__}. "
            "You must explain this to the user."
        ) from exc
