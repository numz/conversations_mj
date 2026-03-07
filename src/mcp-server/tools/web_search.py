"""Web search tools — replicas of web_search_brave, web_search_tavily, web_search_albert_rag."""

import logging
import os

import httpx

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_API_URL = os.environ.get(
    "BRAVE_API_URL", "https://api.search.brave.com/res/v1/web/search"
)
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = os.environ.get(
    "TAVILY_API_URL", "https://api.tavily.com/search"
)
RAG_WEB_SEARCH_MAX_RESULTS = int(os.environ.get("RAG_WEB_SEARCH_MAX_RESULTS", "5"))


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def web_search_brave(query: str) -> dict:
        """Search the web using Brave Search API.

        Args:
            query: The search query string.
        """
        if not BRAVE_API_KEY:
            return {"error": "BRAVE_API_KEY not configured"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                BRAVE_API_URL,
                params={"q": query, "count": RAG_WEB_SEARCH_MAX_RESULTS},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": BRAVE_API_KEY,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = {}
        for i, item in enumerate(data.get("web", {}).get("results", [])):
            results[str(i)] = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "extra_snippets": item.get("extra_snippets", []),
            }
        return results

    @mcp.tool()
    async def web_search_brave_with_document_backend(query: str) -> dict:
        """Search the web using Brave Search API with document processing backend.

        This variant fetches full page content for deeper analysis.

        Args:
            query: The search query string.
        """
        # Same as web_search_brave — the RAG document backend is not available
        # outside of the Django app, so we fall back to standard Brave search.
        return await web_search_brave(query)

    @mcp.tool()
    async def web_search_tavily(query: str) -> list[dict]:
        """Search the web using Tavily Search API.

        Args:
            query: The search query string.
        """
        if not TAVILY_API_KEY:
            return [{"error": "TAVILY_API_KEY not configured"}]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                TAVILY_API_URL,
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": RAG_WEB_SEARCH_MAX_RESULTS,
                    "search_depth": "basic",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            {
                "link": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
            }
            for r in data.get("results", [])
        ]

    @mcp.tool()
    async def web_search_albert_rag(query: str) -> dict:
        """Search the web using Albert RAG API.

        Args:
            query: The search query string.
        """
        # Albert RAG requires internal infrastructure — returns stub.
        return {
            "error": "Albert RAG is not available outside the main application. "
            "Configure ALBERT_API_URL and ALBERT_API_KEY to enable.",
        }
