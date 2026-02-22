"""Tool to retrieve the full text content of a document."""

import logging
from typing import Optional

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models import Q

from asgiref.sync import sync_to_async
from pydantic_ai import RunContext
from pydantic_ai.messages import ToolReturn

from chat.tools.exceptions import ModelCannotRetry

logger = logging.getLogger(__name__)


@sync_to_async
def _read_text_attachment(attachment):
    """Read the text content of an attachment from storage."""
    with default_storage.open(attachment.key) as f:
        return f.read().decode("utf-8")


async def document_get_content(
    ctx: RunContext,
    *,
    document_name: str,
    max_length: Optional[int] = None,
) -> ToolReturn:
    """
    Retrieve the full text content of a document by its name.
    Use this tool when the user wants to extract, read, or see the full text
    of a document (not just search for specific passages).

    For searching specific passages, use document_search_rag instead.
    For summarizing, use summarize instead.

    Args:
        document_name: The name (or partial name) of the document to retrieve.
        max_length: Optional maximum number of characters to return.
            If the document is longer, it will be truncated with a note.

    Examples:
        - "Extract the text from this file" -> get_document_content(document_name="file.pdf")
        - "Show me the content of report.pdf" -> get_document_content(document_name="report.pdf")
        - "Read this document" -> get_document_content(document_name="document.pdf")
    """
    try:
        # Look for text/* attachments matching the name (includes .pdf.md conversions)
        attachment = await sync_to_async(
            lambda: ctx.deps.conversation.attachments.filter(
                Q(file_name__icontains=document_name) | Q(key__icontains=document_name),
                content_type__startswith="text/",
            ).first()
        )()

        if not attachment:
            # List available documents to help the LLM
            available = await sync_to_async(list)(
                ctx.deps.conversation.attachments.filter(
                    Q(conversion_from__isnull=True) | Q(conversion_from=""),
                ).values_list("file_name", flat=True)
            )
            raise ModelCannotRetry(
                f"No text content found for document '{document_name}'. "
                f"Available documents: {', '.join(available) if available else 'none'}. "
                "If this is an image, use image_ocr instead."
            )

        # Check size against threshold before reading
        max_size = settings.DOCUMENT_CONTENT_MAX_SIZE
        if attachment.size and attachment.size > max_size:
            raise ModelCannotRetry(
                f"Document '{attachment.file_name}' is too large "
                f"({attachment.size:,} bytes, limit is {max_size:,} bytes). "
                "Use document_search_rag to search for specific passages instead, "
                "or use summarize to get a summary."
            )

        content = await _read_text_attachment(attachment)

        if max_length and len(content) > max_length:
            content = content[:max_length]
            content += f"\n\n[... truncated at {max_length} characters]"

        logger.info(
            "[get_document_content] Retrieved %d characters from '%s'",
            len(content),
            attachment.file_name,
        )

        return ToolReturn(
            return_value=content,
            metadata={"document_name": attachment.file_name},
        )

    except (ModelCannotRetry,):
        raise
    except Exception as exc:
        logger.exception("Error retrieving document content: %s", exc)
        raise ModelCannotRetry(
            f"Failed to retrieve document content: {type(exc).__name__}. "
            "Explain this to the user."
        ) from exc
