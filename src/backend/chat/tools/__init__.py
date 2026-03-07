"""Tools for the chat agent."""

from pydantic_ai import Tool, ToolDefinition

from .fake_current_weather import get_current_weather
from .web_seach_albert_rag import web_search_albert_rag
from .web_search_brave import web_search_brave, web_search_brave_with_document_backend
from .web_search_tavily import web_search_tavily


async def only_if_web_search_enabled(ctx, tool_def: ToolDefinition) -> ToolDefinition | None:
    """Prepare function to include a tool only if web search is enabled in the context."""
    return tool_def if ctx.deps.web_search_enabled else None


def get_legifrance_tools() -> list[Tool]:
    """Return Légifrance tools when the feature flag is enabled, empty list otherwise."""
    from django.conf import settings  # noqa: PLC0415

    if not getattr(settings, "LEGIFRANCE_TOOLS_ENABLED", False):
        return []

    from .legifrance import (  # noqa: PLC0415
        judilibre_get_decision,
        judilibre_search,
        legifrance_get_document,
        legifrance_list_codes,
        legifrance_search_admin,
        legifrance_search_code_article_by_number,
        legifrance_search_codes_lois,
        legifrance_search_conventions,
        legifrance_search_jurisprudence,
    )

    return [
        Tool(legifrance_search_codes_lois, takes_ctx=True, max_retries=5),
        Tool(legifrance_search_jurisprudence, takes_ctx=True, max_retries=5),
        Tool(legifrance_search_conventions, takes_ctx=True, max_retries=5),
        Tool(legifrance_search_admin, takes_ctx=True, max_retries=5),
        Tool(legifrance_get_document, takes_ctx=True, max_retries=5),
        Tool(legifrance_list_codes, takes_ctx=True, max_retries=5),
        Tool(legifrance_search_code_article_by_number, takes_ctx=True, max_retries=5),
        Tool(judilibre_search, takes_ctx=True, max_retries=5),
        Tool(judilibre_get_decision, takes_ctx=True, max_retries=5),
    ]


def get_pydantic_tools_by_name(name: str) -> Tool:
    """Get a tool by its name."""
    tool_dict = {
        "get_current_weather": Tool(get_current_weather, takes_ctx=False),
        "web_search_brave": Tool(
            web_search_brave,
            takes_ctx=True,
            prepare=only_if_web_search_enabled,
            max_retries=2,
        ),
        "web_search_brave_with_document_backend": Tool(
            web_search_brave_with_document_backend,
            takes_ctx=True,
            prepare=only_if_web_search_enabled,
            max_retries=2,
        ),
        "web_search_tavily": Tool(
            web_search_tavily,
            takes_ctx=False,
            prepare=only_if_web_search_enabled,
            max_retries=2,
        ),
        "web_search_albert_rag": Tool(
            web_search_albert_rag,
            takes_ctx=True,
            prepare=only_if_web_search_enabled,
            max_retries=2,
        ),
        **_get_legifrance_tools(),
    }

    return tool_dict[name]  # will raise on purpose if name is not found
