"""Tool to list documents available in a conversation."""

import logging

from asgiref.sync import sync_to_async
from pydantic_ai import RunContext
from pydantic_ai.messages import ToolReturn

logger = logging.getLogger(__name__)


async def document_list(ctx: RunContext) -> ToolReturn:
    """
    List all documents available in this conversation.
    Use this tool when you need to know which documents are available,
    their exact names, or when the user asks about their uploaded documents.

    Returns a list of documents with their names, types and sizes, ordered by upload date.
    The first document in the list is the oldest, the last is the most recent.

    Examples of when to use this tool:
    - "What documents do I have?" -> call list_documents first
    - "Summarize the last document" -> call list_documents to find the most recent one
    - "Summarize document number 3" -> call list_documents to get the ordered list
    """
    try:
        attachments = await sync_to_async(list)(
            ctx.deps.conversation.attachments.filter(
                content_type__startswith="text/",
            )
            .values("file_name", "content_type", "size", "created_at")
            .order_by("created_at")
        )

        if not attachments:
            return ToolReturn(
                return_value={
                    "documents": [],
                    "message": "No documents found in this conversation.",
                }
            )

        documents = [
            {
                "index": idx + 1,
                "name": a["file_name"],
                "type": a["content_type"],
                "size_bytes": a["size"],
            }
            for idx, a in enumerate(attachments)
        ]

        logger.debug("[list_documents] Found %d documents", len(documents))

        return ToolReturn(
            return_value={
                "documents": documents,
                "total": len(documents),
            }
        )

    except Exception as exc:
        logger.exception("Error listing documents: %s", exc)
        return ToolReturn(
            return_value={
                "error": f"Failed to list documents: {type(exc).__name__}",
                "documents": [],
            }
        )
