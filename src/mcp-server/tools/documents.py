"""Document tools — access documents stored in S3 and search via Albert RAG API.

These tools operate on S3 object storage using the same credentials
as the Django backend, and use the Albert RAG API for semantic search.
They replicate the behavior of the backend tools in
``src/backend/chat/tools/document_*.py``.
"""

import logging
import os
from enum import Enum

import boto3
import botocore.client
from botocore.exceptions import ClientError
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

DOCUMENT_CONTENT_MAX_SIZE = int(
    os.environ.get("DOCUMENT_CONTENT_MAX_SIZE", "200000")
)

# S3 configuration — same env vars as the Django backend
S3_ENDPOINT_URL = os.environ.get("AWS_S3_ENDPOINT_URL", "")
S3_ACCESS_KEY_ID = os.environ.get("AWS_S3_ACCESS_KEY_ID", "")
S3_SECRET_ACCESS_KEY = os.environ.get("AWS_S3_SECRET_ACCESS_KEY", "")
S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "")
S3_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
S3_VERIFY = os.environ.get("AWS_S3_VERIFY", "true").lower() not in ("false", "0", "no")
S3_SIGNATURE_VERSION = os.environ.get("AWS_S3_SIGNATURE_VERSION", "s3v4")

# Albert RAG API — same env vars as the Django backend
ALBERT_API_URL = os.environ.get("ALBERT_API_URL", "https://albert.api.etalab.gouv.fr")
ALBERT_API_KEY = os.environ.get("ALBERT_API_KEY", "")
ALBERT_API_TIMEOUT = int(os.environ.get("ALBERT_API_TIMEOUT", "30"))


class AnalysisType(str, Enum):
    """Types of document analysis — mirrors backend AnalysisType."""

    COMPARE = "compare"
    MATCH = "match"
    COMPLIANCE = "compliance"
    EXTRACT = "extract"
    CROSS_REFERENCE = "cross_reference"


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


def _get_s3_client():
    """Create a boto3 S3 client with the configured credentials.

    Supports HCP (Hitachi Content Platform) via AWS_S3_VERIFY=false
    and custom signature versions.
    """
    kwargs = {
        "verify": S3_VERIFY,
        "config": botocore.client.Config(
            region_name=S3_REGION_NAME or None,
            signature_version=S3_SIGNATURE_VERSION,
        ),
    }
    if S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = S3_ENDPOINT_URL
    if S3_ACCESS_KEY_ID:
        kwargs["aws_access_key_id"] = S3_ACCESS_KEY_ID
    if S3_SECRET_ACCESS_KEY:
        kwargs["aws_secret_access_key"] = S3_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def _read_s3_object(s3_key: str, max_length: int | None = None) -> str | None:
    """Read a text file from S3 by its key."""
    if not S3_BUCKET_NAME:
        logger.error("AWS_STORAGE_BUCKET_NAME is not configured")
        return None
    try:
        client = _get_s3_client()
        response = client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        content = response["Body"].read().decode("utf-8", errors="replace")
        if max_length:
            content = content[:max_length]
        return content
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.warning("S3 error reading '%s': %s", s3_key, error_code)
        return None
    except Exception:
        logger.exception("Unexpected error reading S3 object '%s'", s3_key)
        return None


def _list_s3_attachments(conversation_id: str) -> list[dict]:
    """List text/* attachments in S3 for a conversation, ordered by last modified."""
    if not S3_BUCKET_NAME:
        return []
    try:
        client = _get_s3_client()
        prefix = f"{conversation_id}/attachments/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        objects = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            name = key.rsplit("/", 1)[-1] if "/" in key else key
            objects.append(
                {
                    "name": name,
                    "s3_key": key,
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                }
            )
        # Order by last modified (oldest first, like backend orders by created_at)
        objects.sort(key=lambda x: x["last_modified"])
        for idx, obj in enumerate(objects):
            obj["index"] = idx + 1
            del obj["last_modified"]
        return objects
    except Exception:
        logger.exception("Error listing S3 objects for conversation '%s'", conversation_id)
        return []


def _find_attachment_by_name(
    conversation_id: str, document_name: str
) -> dict | None:
    """Find a text attachment by partial name match (case-insensitive)."""
    attachments = _list_s3_attachments(conversation_id)
    # Exact match first
    for att in attachments:
        if att["name"] == document_name:
            return att
    # Partial match
    for att in attachments:
        if document_name.lower() in att["name"].lower():
            return att
    return None


def _search_albert_rag(collection_id: str, query: str, results_count: int = 4) -> dict:
    """Search using the Albert RAG API — mirrors AlbertRagBackend.search()."""
    import httpx  # noqa: PLC0415

    if not ALBERT_API_KEY:
        return {"error": "ALBERT_API_KEY is not configured. RAG search unavailable."}

    search_url = f"{ALBERT_API_URL.rstrip('/')}/v1/search"
    headers = {"Authorization": f"Bearer {ALBERT_API_KEY}"}

    try:
        response = httpx.post(
            search_url,
            headers=headers,
            json={
                "collections": [int(collection_id)],
                "prompt": query,
                "score_threshold": 0.6,
                "k": results_count,
            },
            timeout=ALBERT_API_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("data", []):
            chunk = item.get("chunk", {})
            results.append({
                "document_name": chunk.get("metadata", {}).get("document_name", ""),
                "content": chunk.get("content", ""),
                "score": item.get("score", 0),
            })

        usage = data.get("usage", {})
        return {
            "results": results,
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        }
    except httpx.HTTPStatusError as e:
        logger.warning("Albert RAG search error: %s %s", e.response.status_code, e.response.text)
        return {"error": f"Albert RAG search failed: HTTP {e.response.status_code}"}
    except Exception:
        logger.exception("Unexpected error during Albert RAG search")
        return {"error": "Unexpected error during RAG search."}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def document_list(conversation_id: str) -> list[dict]:
        """List all documents available in this conversation.
        Use this tool when you need to know which documents are available,
        their exact names, or when the user asks about their uploaded documents.

        Returns a list of documents with their names, types and sizes, ordered by upload date.
        The first document in the list is the oldest, the last is the most recent.

        Args:
            conversation_id: The conversation ID (UUID).

        Examples of when to use this tool:
        - "What documents do I have?" -> call document_list first
        - "Summarize the last document" -> call document_list to find the most recent one
        - "Summarize document number 3" -> call document_list to get the ordered list
        """
        docs = _list_s3_attachments(conversation_id)
        if not docs:
            return [{"documents": [], "message": "No documents found in this conversation."}]
        return [{"documents": docs, "total": len(docs)}]

    @mcp.tool()
    def document_get_content(
        conversation_id: str,
        document_name: str,
        max_length: int | None = None,
    ) -> dict:
        """Retrieve the full text content of a document by its name.
        Use this tool when the user wants to extract, read, or see the full text
        of a document (not just search for specific passages).

        For searching specific passages, use document_search_rag instead.
        For summarizing, use document_summarize instead.

        Args:
            conversation_id: The conversation ID (UUID).
            document_name: The name (or partial name) of the document to retrieve.
            max_length: Optional maximum number of characters to return.
                If the document is longer, it will be truncated with a note.

        Examples:
            - "Extract the text from this file" -> document_get_content(document_name="file.pdf")
            - "Show me the content of report.pdf" -> document_get_content(document_name="report.pdf")
            - "Read this document" -> document_get_content(document_name="document.pdf")
        """
        att = _find_attachment_by_name(conversation_id, document_name)
        if att is None:
            available = _list_s3_attachments(conversation_id)
            available_names = [a["name"] for a in available]
            return {
                "error": (
                    f"No text content found for document '{document_name}'. "
                    f"Available documents: {', '.join(available_names) if available_names else 'none'}. "
                    "If this is an image, use image_ocr instead."
                )
            }

        # Check size against threshold before reading
        if att["size"] and att["size"] > DOCUMENT_CONTENT_MAX_SIZE:
            return {
                "error": (
                    f"Document '{att['name']}' is too large "
                    f"({att['size']:,} bytes, limit is {DOCUMENT_CONTENT_MAX_SIZE:,} bytes). "
                    "Use document_search_rag to search for specific passages instead, "
                    "or use document_summarize to get a summary."
                )
            }

        content = _read_s3_object(att["s3_key"], max_length)
        if content is None:
            return {"error": f"Failed to read document '{att['name']}' from storage."}

        if max_length and len(content) >= max_length:
            content += f"\n\n[... truncated at {max_length} characters]"

        return {"content": content, "document_name": att["name"]}

    @mcp.tool()
    def document_analyze(
        conversation_id: str,
        document_names: list[str],
        analysis_type: str = "compare",
        instructions: str | None = None,
    ) -> dict:
        """Analyze multiple documents together to compare, match, or cross-reference them.
        Use this tool when the user wants to analyze relationships between documents.

        This tool is designed for tasks like:
        - Comparing a CV with a job posting to evaluate candidate fit
        - Comparing multiple contracts or quotes to find differences
        - Checking if a document complies with a reference/specification
        - Extracting and comparing specific information across documents
        - Cross-referencing information between related documents

        Args:
            conversation_id: The conversation ID (UUID).
            document_names: List of document names to analyze (at least 2 required).
                Use document_list tool first to get exact document names.
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
        # Validate analysis type
        try:
            analysis_type_enum = AnalysisType(analysis_type.lower())
        except ValueError:
            valid_types = [t.value for t in AnalysisType]
            return {
                "error": (
                    f"Invalid analysis_type '{analysis_type}'. "
                    f"Valid types are: {', '.join(valid_types)}."
                )
            }

        if not document_names or len(document_names) < 2:
            return {
                "error": (
                    "At least 2 documents are required for analysis. "
                    "Use document_list tool to see available documents."
                )
            }

        # Find and read documents
        attachments = []
        for name in document_names:
            att = _find_attachment_by_name(conversation_id, name)
            if att is None:
                available = _list_s3_attachments(conversation_id)
                available_names = [a["name"] for a in available]
                return {
                    "error": (
                        f"Could not find document matching '{name}'. "
                        f"Available documents: {', '.join(available_names) if available_names else 'none'}. "
                        "Use document_list to see available documents."
                    )
                }
            attachments.append(att)

        if len(attachments) < 2:
            return {
                "error": (
                    f"Could not find enough documents matching {document_names}. "
                    "Use document_list to see available documents."
                )
            }

        # Check cumulative size
        cumulative_size = sum(att["size"] or 0 for att in attachments)
        if cumulative_size > DOCUMENT_CONTENT_MAX_SIZE:
            doc_sizes = [f"{att['name']} ({att['size'] or 0:,} bytes)" for att in attachments]
            return {
                "error": (
                    f"The cumulative size of the selected documents ({cumulative_size:,} bytes) "
                    f"exceeds the limit ({DOCUMENT_CONTENT_MAX_SIZE:,} bytes). "
                    f"Documents: {', '.join(doc_sizes)}. "
                    "Use document_search_rag to search for specific passages in each document, "
                    "or use document_summarize to get summaries first, then analyze the summaries."
                )
            }

        # Read document contents
        documents = []
        for att in attachments:
            content = _read_s3_object(att["s3_key"])
            if content is None:
                return {"error": f"Failed to read document '{att['name']}' from storage."}
            documents.append((att["name"], content))

        # Build the analysis prompt and context for the calling LLM
        base_prompt = ANALYSIS_PROMPTS.get(analysis_type_enum, ANALYSIS_PROMPTS[AnalysisType.COMPARE])
        documents_context = "\n\n---\n\n".join(
            f"## Document: {doc_name}\n\n{doc_content}"
            for doc_name, doc_content in documents
        )

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

        return {
            "analysis_prompt": analysis_prompt,
            "analysis_type": analysis_type_enum.value,
            "documents_analyzed": [doc[0] for doc in documents],
        }

    @mcp.tool()
    def document_summarize(
        conversation_id: str,
        instructions: str | None = None,
    ) -> dict:
        """Generate a complete, ready-to-use summary of the documents in context
        (do not request the documents to the user).
        Return this summary directly to the user WITHOUT any modification,
        or additional summarization.
        The summary is already optimized and MUST be presented as-is in the final response
        or translated preserving the information.

        Instructions are optional but should reflect the user's request.

        Examples:
        "Summarize this doc in 2 paragraphs" -> instructions = "summary in 2 paragraphs"
        "Summarize this doc in English" -> instructions = "In English"
        "Summarize this doc" -> instructions = "" (default)

        Args:
            conversation_id: The conversation ID (UUID).
            instructions: The instructions the user gave to use for the summarization.
        """
        docs = _list_s3_attachments(conversation_id)
        if not docs:
            return {
                "error": (
                    "No text documents found in the conversation. "
                    "You must explain this to the user and ask them to provide documents."
                )
            }

        instructions_hint = (
            instructions.strip() if instructions else "The summary should contain 2 or 3 parts."
        )

        # Read all document contents
        documents = []
        for doc in docs:
            content = _read_s3_object(doc["s3_key"])
            if content:
                documents.append((doc["name"], content[:DOCUMENT_CONTENT_MAX_SIZE]))

        if not documents:
            return {"error": "Could not read any documents from storage."}

        # Build summarization context for the calling LLM
        documents_context = "\n\n".join(
            f"{doc_name}\n\n{doc_content}"
            for doc_name, doc_content in documents
        )

        summarization_prompt = (
            "Produce a coherent synthesis from the documents below.\n\n"
            f"'''\n{documents_context}\n'''\n\n"
            "Constraints:\n"
            "- Summarize without repetition.\n"
            "- Harmonize style and terminology.\n"
            "- The final summary must be well-structured and formatted in markdown.\n"
            f"- Follow the instructions: {instructions_hint}\n"
            "Respond directly with the final summary."
        )

        return {
            "summarization_prompt": summarization_prompt,
            "documents_summarized": [doc[0] for doc in documents],
        }

    @mcp.tool()
    def document_search_rag(
        conversation_id: str,
        query: str,
        collection_id: str | None = None,
    ) -> dict:
        """Perform a search in the documents provided by the user.
        Must be used whenever the user asks for information that
        is not in the model's knowledge base and most of the time.
        The query must contain all information to find accurate results.

        Uses the Albert RAG API for semantic search when available,
        falls back to simple text search otherwise.

        Args:
            conversation_id: The conversation ID (UUID).
            query: The query to search the documents for.
            collection_id: The RAG collection ID for the conversation (if available).
        """
        # Try Albert RAG search first if collection_id is provided
        if collection_id and ALBERT_API_KEY:
            result = _search_albert_rag(collection_id, query)
            if "error" not in result:
                return {
                    "query": query,
                    "method": "rag_semantic",
                    "results": result["results"],
                    "usage": result["usage"],
                }
            logger.warning("Albert RAG search failed, falling back to text search: %s", result["error"])

        # Fallback: simple text search across S3 documents
        docs = _list_s3_attachments(conversation_id)
        results = []
        for doc in docs:
            text = _read_s3_object(doc["s3_key"])
            if text and query.lower() in text.lower():
                idx = text.lower().index(query.lower())
                start = max(0, idx - 200)
                end = min(len(text), idx + len(query) + 200)
                results.append(
                    {
                        "document_name": doc["name"],
                        "content": text[start:end],
                        "score": 1.0,
                    }
                )
        if not results:
            return {"message": f"No passages matching '{query}' found in documents."}
        return {
            "query": query,
            "method": "text_search",
            "results": results,
        }
