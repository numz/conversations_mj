"""Legifrance & Judilibre MCP tool registration wrapper.

This module registers all Legifrance and Judilibre tools with the MCP server.
It imports the standalone tool functions from the legifrance package and
wraps them as MCP tools.
"""

import logging

from mcp.server.fastmcp import FastMCP

from .legifrance.tools.search_codes_lois import legifrance_search_codes_lois
from .legifrance.tools.search_jurisprudence import legifrance_search_jurisprudence
from .legifrance.tools.search_conventions import legifrance_search_conventions
from .legifrance.tools.search_admin import legifrance_search_admin
from .legifrance.tools.get_document import legifrance_get_document
from .legifrance.tools.search_code_article_by_number import legifrance_search_code_article_by_number
from .legifrance.tools.list_codes import legifrance_list_codes
from .legifrance.tools.judilibre_search import judilibre_search
from .legifrance.tools.judilibre_get_decision import judilibre_get_decision

logger = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register all Legifrance and Judilibre tools with the MCP server."""

    # -----------------------------------------------------------------------
    # LEGIFRANCE TOOLS
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def mcp_legifrance_search_codes_lois(
        query: str,
        type_source: str = "CODE",
        code_name: str = "Code penal",
        date: str | None = None,
    ) -> dict:
        """Search French Codes and Laws via Legifrance API.

        Args:
            query: Keywords or article number to search for.
            type_source: "CODE" for in-force codes, "LODA" for laws and decrees.
            code_name: Name of the code to search in (e.g. "Code civil", "Code penal").
            date: Optional validity date in YYYY-MM-DD format.
        """
        logger.info("[MCP] legifrance_search_codes_lois(query=%r, type_source=%r, code_name=%r)", query, type_source, code_name)
        return await legifrance_search_codes_lois(query=query, type_source=type_source, code_name=code_name, date=date)

    @mcp.tool()
    async def mcp_legifrance_search_jurisprudence(
        query: str,
        date: str | None = None,
        juridiction: str = "JUDICIAIRE",
        numero_decision: str | None = None,
        sort: str | None = "PERTINENCE",
    ) -> dict:
        """Search French jurisprudence across all courts via Legifrance.

        Args:
            query: Search keywords.
            date: Optional decision date in YYYY-MM-DD format.
            juridiction: Court type -- "JUDICIAIRE", "ADMINISTRATIF", "CONSTITUTIONNEL", or "FINANCIER".
            numero_decision: Optional specific decision number.
            sort: Sort order -- "PERTINENCE", "DATE_DESC", or "DATE_ASC".
        """
        logger.info("[MCP] legifrance_search_jurisprudence(query=%r, juridiction=%r)", query, juridiction)
        return await legifrance_search_jurisprudence(query=query, date=date, juridiction=juridiction, numero_decision=numero_decision, sort=sort)

    @mcp.tool()
    async def mcp_legifrance_search_conventions(
        query: str,
        type_source: str = "KALI",
        idcc: str | None = None,
        date: str | None = None,
        etat_texte: str | None = "VIGUEUR",
    ) -> dict:
        """Search French collective bargaining agreements and company agreements.

        Args:
            query: Search keywords.
            type_source: "KALI" for collective agreements, "ACCO" for company agreements.
            idcc: Optional IDCC number to filter by.
            date: Optional signature date in YYYY-MM-DD format.
            etat_texte: Legal status filter (default "VIGUEUR" = currently in force).
        """
        logger.info("[MCP] legifrance_search_conventions(query=%r, type_source=%r)", query, type_source)
        return await legifrance_search_conventions(query=query, type_source=type_source, idcc=idcc, date=date, etat_texte=etat_texte)

    @mcp.tool()
    async def mcp_legifrance_search_admin(
        query: str,
        source: str = "JORF",
        date: str | None = None,
        nor: str | None = None,
        nature_delib: str | None = None,
    ) -> dict:
        """Search French official publications (JORF, Circulars, CNIL).

        Args:
            query: Search keywords.
            source: Publication source -- "JORF" (Official Journal), "CIRC" (Circulars), or "CNIL".
            date: Optional publication/deliberation date in YYYY-MM-DD format.
            nor: Optional NOR number.
            nature_delib: Optional deliberation nature (for CNIL source only).
        """
        logger.info("[MCP] legifrance_search_admin(query=%r, source=%r)", query, source)
        return await legifrance_search_admin(query=query, source=source, date=date, nor=nor, nature_delib=nature_delib)

    @mcp.tool()
    async def mcp_legifrance_get_document(article_id: str) -> dict:
        """Retrieve the full text of a legal document from Legifrance by its ID.

        Args:
            article_id: The document identifier (e.g. "LEGIARTI000...", "JORFTEXT000...", "KALITEXT000...").
        """
        logger.info("[MCP] legifrance_get_document(article_id=%r)", article_id)
        return await legifrance_get_document(article_id=article_id)

    @mcp.tool()
    async def mcp_legifrance_search_code_article_by_number(
        code_name: str, article_num: str
    ) -> dict:
        """Search for a specific article number within a specific French legal code.

        Args:
            code_name: Name of the code (e.g. "Code penal", "Code civil").
            article_num: Article number (e.g. "1240", "123-1").
        """
        logger.info("[MCP] legifrance_search_code_article_by_number(code_name=%r, article_num=%r)", code_name, article_num)
        return await legifrance_search_code_article_by_number(code_name=code_name, article_num=article_num)

    @mcp.tool()
    async def mcp_legifrance_list_codes(code_name: str = "") -> dict:
        """List all available French legal codes, optionally filtered by name.

        Args:
            code_name: Optional filter -- partial or full code name to search for.
        """
        logger.info("[MCP] legifrance_list_codes(code_name=%r)", code_name)
        return await legifrance_list_codes(code_name=code_name)

    # -----------------------------------------------------------------------
    # JUDILIBRE TOOLS
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def mcp_judilibre_search(
        query: str,
        jurisdiction: str | None = "cc",
        date_start: str | None = None,
        date_end: str | None = None,
        solution: str | None = None,
        publication: str | None = None,
    ) -> dict:
        """Search French Court of Cassation open data via Judilibre.

        Args:
            query: Search keywords (minimum 2 characters).
            jurisdiction: Court -- "cc" (Cour de cassation), "ca" (Cours d'appel), "tj" (Tribunaux).
            date_start: Optional start date in YYYY-MM-DD format.
            date_end: Optional end date in YYYY-MM-DD format.
            solution: Optional -- "cassation", "rejet", "annulation", "irrecevabilite".
            publication: Optional -- "b" (Bulletin), "r" (Rapport), "l" (Lettre).
        """
        logger.info("[MCP] judilibre_search(query=%r, jurisdiction=%r)", query, jurisdiction)
        return await judilibre_search(query=query, jurisdiction=jurisdiction, date_start=date_start, date_end=date_end, solution=solution, publication=publication)

    @mcp.tool()
    async def mcp_judilibre_get_decision(decision_id: str) -> dict:
        """Retrieve the full content of a Judilibre decision by its ID.

        Args:
            decision_id: The Judilibre decision identifier (minimum 10 characters).
        """
        logger.info("[MCP] judilibre_get_decision(decision_id=%r)", decision_id)
        return await judilibre_get_decision(decision_id=decision_id)
