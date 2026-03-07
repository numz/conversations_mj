"""Document tools — replicas of document_list, document_get_content, document_analyze,
document_summarize, and document_search_rag.

These tools operate on a local document directory (MCP_DOCUMENTS_DIR) instead of
the Django database. Place files in the configured directory to make them available.
"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DOCUMENTS_DIR = Path(os.environ.get("MCP_DOCUMENTS_DIR", "/data/documents"))
DOCUMENT_CONTENT_MAX_SIZE = int(
    os.environ.get("DOCUMENT_CONTENT_MAX_SIZE", "200000")
)


def _list_documents() -> list[dict]:
    """List all text files in the documents directory."""
    if not DOCUMENTS_DIR.exists():
        return []
    docs = []
    for i, path in enumerate(sorted(DOCUMENTS_DIR.iterdir())):
        if path.is_file():
            docs.append(
                {
                    "index": i,
                    "name": path.name,
                    "size": path.stat().st_size,
                    "type": _guess_content_type(path),
                }
            )
    return docs


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "text/xml",
        ".html": "text/html",
        ".htm": "text/html",
        ".pdf": "application/pdf",
    }.get(suffix, "text/plain")


def _read_document(name: str, max_length: int | None = None) -> str | None:
    """Read a document by exact or partial name match."""
    if not DOCUMENTS_DIR.exists():
        return None
    # Exact match first
    exact = DOCUMENTS_DIR / name
    if exact.is_file():
        text = exact.read_text(encoding="utf-8", errors="replace")
        if max_length:
            text = text[:max_length]
        return text
    # Partial match
    for path in DOCUMENTS_DIR.iterdir():
        if path.is_file() and name.lower() in path.name.lower():
            text = path.read_text(encoding="utf-8", errors="replace")
            if max_length:
                text = text[:max_length]
            return text
    return None


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def document_list() -> list[dict]:
        """List all documents available in the conversation.

        Returns a list of documents with their name, type, size, and index.
        """
        docs = _list_documents()
        if not docs:
            return [{"message": "No documents available."}]
        return docs

    @mcp.tool()
    def document_get_content(
        document_name: str, max_length: int | None = None
    ) -> dict:
        """Retrieve the full text content of a document by name.

        Args:
            document_name: Document name or partial name to match.
            max_length: Maximum number of characters to return.
        """
        text = _read_document(document_name, max_length)
        if text is None:
            return {"error": f"Document '{document_name}' not found."}
        return {"name": document_name, "content": text, "length": len(text)}

    @mcp.tool()
    def document_analyze(
        document_names: list[str],
        analysis_type: str = "compare",
        instructions: str | None = None,
    ) -> dict:
        """Analyze and compare multiple documents together.

        Args:
            document_names: List of document names to analyze (minimum 2).
            analysis_type: Type of analysis — "compare", "match", "compliance", "extract", or "cross_reference".
            instructions: Optional custom analysis instructions.
        """
        if len(document_names) < 2:
            return {"error": "At least 2 document names are required."}

        contents = {}
        cumulative_size = 0
        for name in document_names:
            text = _read_document(name)
            if text is None:
                return {"error": f"Document '{name}' not found."}
            cumulative_size += len(text.encode("utf-8"))
            if cumulative_size > DOCUMENT_CONTENT_MAX_SIZE:
                return {
                    "error": f"Cumulative document size exceeds limit of {DOCUMENT_CONTENT_MAX_SIZE} bytes."
                }
            contents[name] = text

        return {
            "analysis_type": analysis_type,
            "instructions": instructions,
            "documents": {
                name: {"length": len(text), "preview": text[:500]}
                for name, text in contents.items()
            },
            "note": "Full analysis requires an LLM. This MCP tool returns document content for the model to analyze.",
        }

    @mcp.tool()
    def document_summarize(instructions: str | None = None) -> dict:
        """Generate a complete summary of all documents in the conversation.

        Args:
            instructions: Optional specific summarization instructions.
        """
        docs = _list_documents()
        if not docs:
            return {"error": "No documents available to summarize."}

        contents = {}
        for doc in docs:
            text = _read_document(doc["name"])
            if text:
                contents[doc["name"]] = text[:DOCUMENT_CONTENT_MAX_SIZE]

        return {
            "instructions": instructions,
            "documents": {
                name: {"length": len(text), "preview": text[:500]}
                for name, text in contents.items()
            },
            "note": "Full summarization requires an LLM. This MCP tool returns document content for the model to summarize.",
        }

    @mcp.tool()
    def document_search_rag(query: str) -> dict:
        """Search for specific passages in user-provided documents using RAG.

        Args:
            query: The search query to find relevant passages.
        """
        # Without a RAG backend, do simple text search across documents.
        docs = _list_documents()
        results = []
        for doc in docs:
            text = _read_document(doc["name"])
            if text and query.lower() in text.lower():
                # Find the passage around the match
                idx = text.lower().index(query.lower())
                start = max(0, idx - 200)
                end = min(len(text), idx + len(query) + 200)
                results.append(
                    {
                        "document": doc["name"],
                        "passage": text[start:end],
                        "position": idx,
                    }
                )
        if not results:
            return {"message": f"No passages matching '{query}' found in documents."}
        return {"query": query, "results": results}
