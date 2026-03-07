"""Legifrance & Judilibre tools — standalone replicas for MCP server.

These tools call the Legifrance/Judilibre APIs directly via httpx,
without requiring Django or the full backend stack.
"""

import asyncio
import datetime
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# --- Configuration from environment ---
API_BASE_URL = os.environ.get(
    "LEGIFRANCE_API_BASE_URL",
    "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app",
)
OAUTH_URL = os.environ.get(
    "LEGIFRANCE_OAUTH_URL",
    "https://oauth.piste.gouv.fr/api/oauth/token",
)
CLIENT_ID = os.environ.get("LEGIFRANCE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "")
API_TOKEN = os.environ.get("LEGIFRANCE_API_TOKEN", "")
SSL_VERIFY = os.environ.get("LEGIFRANCE_SSL_VERIFY", "true").lower() == "true"
OAUTH_HOST = os.environ.get("LEGIFRANCE_OAUTH_HOST", "")
API_HOST = os.environ.get("LEGIFRANCE_API_HOST", "")

# Judilibre
JUDILIBRE_API_URL = os.environ.get(
    "JUDILIBRE_API_URL", "https://api.piste.gouv.fr/cassation/judilibre/v1.0"
)
JUDILIBRE_KEY_NAME = os.environ.get("JUDILIBRE_KEY_NAME", "KeyId")
JUDILIBRE_KEY_VALUE = os.environ.get("JUDILIBRE_KEY_VALUE", "")

LEGIFRANCE_UI_BASE = "https://www.legifrance.gouv.fr"
JUDILIBRE_UI_BASE = "https://www.courdecassation.fr/decision"

TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0)
MAX_RETRIES = 3

# --- In-memory token cache ---
_token_cache: dict[str, Any] = {"token": "", "expires_at": 0}


def _clean_html(text: Any) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _authenticate() -> str:
    """Get or refresh OAuth token."""
    import time

    # Use static token if available
    if API_TOKEN:
        return API_TOKEN

    # Check in-memory cache
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("LEGIFRANCE_CLIENT_ID and LEGIFRANCE_CLIENT_SECRET required")

    headers = {}
    if OAUTH_URL:
        headers["Host"] = urlparse(OAUTH_URL).hostname

    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=TIMEOUT) as client:
        resp = await client.post(
            OAUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "openid",
            },
            headers=headers or None,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        _token_cache["token"] = token
        _token_cache["expires_at"] = time.time() + expires_in - 100
        return token


async def _api_request(method: str, path: str, payload: dict) -> dict | None:
    """Execute a Legifrance API request with auth and retry."""
    url = f"{API_BASE_URL}{path}"
    token = await _authenticate()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if API_HOST:
        headers["Host"] = API_HOST

    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=TIMEOUT) as client:
        for attempt in range(MAX_RETRIES):
            try:
                if method == "post":
                    resp = await client.post(url, json=payload, headers=headers)
                else:
                    resp = await client.get(url, headers=headers)

                if resp.status_code == 401 and attempt == 0:
                    _token_cache["token"] = ""
                    token = await _authenticate()
                    headers["Authorization"] = f"Bearer {token}"
                    continue

                if resp.status_code == 421:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                resp.raise_for_status()
                return resp.json()

            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise
    return None


async def _judilibre_request(path: str, params: dict) -> dict | None:
    """Execute a Judilibre API request."""
    token = await _authenticate()
    url = f"{JUDILIBRE_API_URL}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if JUDILIBRE_KEY_VALUE:
        headers[JUDILIBRE_KEY_NAME] = JUDILIBRE_KEY_VALUE

    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


def _build_source_url(article_id: str) -> str:
    """Build a Legifrance URL from an article/text ID."""
    prefix_to_path = {
        "LEGIARTI": "codes/article_lc",
        "LEGITEXT": "loda/id",
        "JURITEXT": "juri/id",
        "CETATEXT": "ceta/id",
        "CONSTEXT": "cons/id",
        "JUFITEXT": "jufi/id",
        "CNILTEXT": "cnil/id",
        "ACCOTEXT": "acco/id",
        "JORFTEXT": "jorf/id",
        "KALITEXT": "conv_coll/id",
        "KALIARTI": "conv_coll/article",
    }
    for prefix, path in prefix_to_path.items():
        if article_id.startswith(prefix):
            return f"{LEGIFRANCE_UI_BASE}/{path}/{article_id}"
    return f"{LEGIFRANCE_UI_BASE}/search/{article_id}"


def _build_source_with_title(article_id: str, title: str = "") -> tuple[str, str]:
    """Return (url, title) tuple for source metadata."""
    url = _build_source_url(article_id)
    return url, title or article_id


def register(mcp: FastMCP) -> None:
    # -----------------------------------------------------------------------
    # LEGIFRANCE TOOLS
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def legifrance_search_codes_lois(
        query: str,
        type_source: str = "CODE",
        code_name: str = "Code pénal",
        date: str | None = None,
    ) -> dict:
        """Search French Codes and Laws via Legifrance API.

        Args:
            query: Keywords or article number to search for.
            type_source: "CODE" for in-force codes, "LODA" for laws and decrees.
            code_name: Name of the code to search in (e.g. "Code civil", "Code pénal").
            date: Optional validity date in YYYY-MM-DD format.
        """
        fond = "CODE_DATE" if type_source == "CODE" else "LODA_DATE"
        criteres = [
            {
                "typeChamp": "ALL",
                "criteres": [
                    {"typeRecherche": "UN_DES_MOTS", "valeur": query, "operateur": "ET"}
                ],
                "operateur": "ET",
            }
        ]
        filtres = []
        if type_source == "CODE" and code_name:
            filtres.append({"facette": "NOM_CODE", "valeurs": [code_name]})
        if date:
            filtres.append({"facette": "DATE_VERSION", "valeurs": [date]})

        payload = {
            "fond": fond,
            "recherche": {
                "champs": criteres,
                "filtres": filtres,
                "pageNumber": 1,
                "pageSize": 5,
                "operateur": "ET",
                "sort": "PERTINENCE",
                "typePagination": "DEFAUT",
            },
        }
        data = await _api_request("post", "/search", payload)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", [])
        sources = {}
        formatted = []
        for r in results:
            titles = r.get("titles", [])
            title = titles[0].get("title", "") if titles else ""
            article_id = titles[0].get("id", "") if titles else ""
            if article_id:
                url, src_title = _build_source_with_title(article_id, _clean_html(title))
                sources[url] = src_title
            formatted.append(
                {
                    "id": article_id,
                    "title": _clean_html(title),
                    "sections": [_clean_html(t.get("title", "")) for t in titles[1:]],
                }
            )
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def legifrance_search_jurisprudence(
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
            juridiction: Court type — "JUDICIAIRE", "ADMINISTRATIF", "CONSTITUTIONNEL", or "FINANCIER".
            numero_decision: Optional specific decision number.
            sort: Sort order — "PERTINENCE", "DATE_DESC", or "DATE_ASC".
        """
        fond_map = {
            "JUDICIAIRE": "JURI",
            "ADMINISTRATIF": "CETAT",
            "CONSTITUTIONNEL": "CONSTIT",
            "FINANCIER": "JUFI",
        }
        fond = fond_map.get(juridiction, "JURI")
        criteres = [
            {
                "typeChamp": "ALL",
                "criteres": [
                    {"typeRecherche": "UN_DES_MOTS", "valeur": query, "operateur": "ET"}
                ],
                "operateur": "ET",
            }
        ]
        filtres = []
        if date:
            filtres.append({"facette": "DATE_DECISION", "valeurs": [date]})
        if numero_decision:
            filtres.append({"facette": "NUMERO_DECISION", "valeurs": [numero_decision]})

        payload = {
            "fond": fond,
            "recherche": {
                "champs": criteres,
                "filtres": filtres,
                "pageNumber": 1,
                "pageSize": 5,
                "operateur": "ET",
                "sort": sort or "PERTINENCE",
                "typePagination": "DEFAUT",
            },
        }
        data = await _api_request("post", "/search", payload)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", [])
        sources = {}
        formatted = []
        for r in results:
            titles = r.get("titles", [])
            title = _clean_html(titles[0].get("title", "")) if titles else ""
            article_id = titles[0].get("id", "") if titles else ""
            if article_id:
                url, src_title = _build_source_with_title(article_id, title)
                sources[url] = src_title
            formatted.append({"id": article_id, "title": title})
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def legifrance_search_conventions(
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
        fond = type_source
        criteres = [
            {
                "typeChamp": "ALL",
                "criteres": [
                    {"typeRecherche": "UN_DES_MOTS", "valeur": query, "operateur": "ET"}
                ],
                "operateur": "ET",
            }
        ]
        filtres = []
        if idcc:
            filtres.append({"facette": "IDCC", "valeurs": [idcc]})
        if date:
            filtres.append({"facette": "DATE_SIGNATURE", "valeurs": [date]})
        if etat_texte:
            filtres.append({"facette": "LEGAL_STATUS", "valeurs": [etat_texte]})

        sort = "SIGNATURE_DATE_DESC" if type_source == "KALI" else "PERTINENCE"
        payload = {
            "fond": fond,
            "recherche": {
                "champs": criteres,
                "filtres": filtres,
                "pageNumber": 1,
                "pageSize": 5,
                "operateur": "ET",
                "sort": sort,
                "typePagination": "DEFAUT",
            },
        }
        data = await _api_request("post", "/search", payload)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", [])
        sources = {}
        formatted = []
        for r in results:
            titles = r.get("titles", [])
            title = _clean_html(titles[0].get("title", "")) if titles else ""
            article_id = titles[0].get("id", "") if titles else ""
            if article_id:
                url, src_title = _build_source_with_title(article_id, title)
                sources[url] = src_title
            formatted.append({"id": article_id, "title": title})
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def legifrance_search_admin(
        query: str,
        source: str = "JORF",
        date: str | None = None,
        nor: str | None = None,
        nature_delib: str | None = None,
    ) -> dict:
        """Search French official publications (JORF, Circulars, CNIL).

        Args:
            query: Search keywords.
            source: Publication source — "JORF" (Official Journal), "CIRC" (Circulars), or "CNIL".
            date: Optional publication/deliberation date in YYYY-MM-DD format.
            nor: Optional NOR number.
            nature_delib: Optional deliberation nature (for CNIL source only).
        """
        fond = source
        criteres = [
            {
                "typeChamp": "ALL",
                "criteres": [
                    {"typeRecherche": "UN_DES_MOTS", "valeur": query, "operateur": "ET"}
                ],
                "operateur": "ET",
            }
        ]
        filtres = []
        if nor:
            filtres.append({"facette": "NOR", "valeurs": [nor]})
        if source == "CNIL":
            if date:
                filtres.append({"facette": "DATE_DELIB", "valeurs": [date]})
            if nature_delib:
                filtres.append({"facette": "NATURE_DELIB", "valeurs": [nature_delib]})
        else:
            if date:
                date_facet = "DATE_SIGNATURE" if source == "JORF" else "DATE_SIGNATURE"
                filtres.append({"facette": date_facet, "valeurs": [date]})

        sort_map = {"JORF": "PUBLICATION_DATE_DESC", "CIRC": "SIGNATURE_DATE_DESC", "CNIL": "PERTINENCE"}
        payload = {
            "fond": fond,
            "recherche": {
                "champs": criteres,
                "filtres": filtres,
                "pageNumber": 1,
                "pageSize": 5,
                "operateur": "ET",
                "sort": sort_map.get(source, "PERTINENCE"),
                "typePagination": "DEFAUT",
            },
        }
        data = await _api_request("post", "/search", payload)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", [])
        sources = {}
        formatted = []
        for r in results:
            titles = r.get("titles", [])
            title = _clean_html(titles[0].get("title", "")) if titles else ""
            article_id = titles[0].get("id", "") if titles else ""
            if article_id:
                url, src_title = _build_source_with_title(article_id, title)
                sources[url] = src_title
            formatted.append({"id": article_id, "title": title})
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def legifrance_get_document(article_id: str) -> dict:
        """Retrieve the full text of a legal document from Legifrance by its ID.

        Args:
            article_id: The document identifier (e.g. "LEGIARTI000...", "JORFTEXT000...", "KALITEXT000...").
        """
        if not article_id or len(article_id) < 8:
            return {"error": "Invalid article_id — must be a valid Legifrance identifier."}

        # Dispatch to the right endpoint based on prefix
        endpoints = {
            "ACCOTEXT": ("/consult/acco", {"id": article_id}),
            "CNILTEXT": ("/consult/cnil", {"textId": article_id}),
            "JORFTEXT": ("/consult/jorf", {"textCid": article_id}),
            "JORFARTI": ("/consult/getArticle", {"id": article_id}),
            "JURITEXT": ("/consult/juri", {"textId": article_id}),
            "CETATEXT": ("/consult/juri", {"textId": article_id}),
            "CONSTEXT": ("/consult/juri", {"textId": article_id}),
            "JUFITEXT": ("/consult/juri", {"textId": article_id}),
            "KALITEXT": ("/consult/kaliText", {"id": article_id}),
            "KALIARTI": ("/consult/kaliArticle", {"id": article_id}),
            "LEGIARTI": ("/consult/getArticle", {"id": article_id}),
            "LEGITEXT": ("/consult/lawDecree", {"textId": article_id, "date": datetime.date.today().isoformat()}),
        }
        path, payload = None, None
        for prefix, (p, pl) in endpoints.items():
            if article_id.startswith(prefix):
                path, payload = p, pl
                break
        if not path:
            path = "/consult/getArticle"
            payload = {"id": article_id}

        data = await _api_request("post", path, payload)
        if not data:
            return {"error": f"Document '{article_id}' not found."}

        # Extract text content
        article = data.get("article", data)
        text_content = _clean_html(
            article.get("texte", article.get("texteHtml", article.get("text", "")))
        )
        title = _clean_html(article.get("titre", article.get("title", article_id)))

        url = _build_source_url(article_id)
        return {
            "id": article_id,
            "title": title,
            "content": text_content[:8000] if text_content else "No content available.",
            "url": url,
            "sources": {url: title},
        }

    @mcp.tool()
    async def legifrance_search_code_article_by_number(
        code_name: str, article_num: str
    ) -> dict:
        """Search for a specific article number within a specific French legal code.

        Args:
            code_name: Name of the code (e.g. "Code pénal", "Code civil").
            article_num: Article number (e.g. "1240", "123-1").
        """
        payload = {
            "fond": "CODE_DATE",
            "recherche": {
                "champs": [
                    {
                        "typeChamp": "ALL",
                        "criteres": [
                            {"typeRecherche": "EXACTE", "valeur": article_num, "operateur": "ET"}
                        ],
                        "operateur": "ET",
                    }
                ],
                "filtres": [{"facette": "NOM_CODE", "valeurs": [code_name]}],
                "pageNumber": 1,
                "pageSize": 5,
                "operateur": "ET",
                "sort": "PERTINENCE",
                "typePagination": "ARTICLE",
            },
        }
        data = await _api_request("post", "/search", payload)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", [])
        sources = {}
        formatted = []
        for r in results:
            titles = r.get("titles", [])
            title = _clean_html(titles[0].get("title", "")) if titles else ""
            article_id = titles[0].get("id", "") if titles else ""
            values = r.get("values", {})
            etat = values.get("etatArticle", values.get("etat", ""))
            if article_id:
                url, src_title = _build_source_with_title(article_id, title)
                sources[url] = src_title
            formatted.append(
                {"id": article_id, "title": title, "status": etat}
            )
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def legifrance_list_codes(code_name: str = "") -> dict:
        """List all available French legal codes, optionally filtered by name.

        Args:
            code_name: Optional filter — partial or full code name to search for.
        """
        payload = {
            "codeName": code_name,
            "pageNumber": 1,
            "pageSize": 150,
            "states": ["VIGUEUR"],
            "sort": "TITLE_ASC",
        }
        data = await _api_request("post", "/list/code", payload)
        if not data:
            return {"results": []}

        results = data.get("results", [])
        formatted = []
        for r in results:
            formatted.append(
                {
                    "title": r.get("title", ""),
                    "cid": r.get("cid", ""),
                    "id": r.get("id", ""),
                    "etat": r.get("etat", ""),
                }
            )
        return {"results": formatted}

    # -----------------------------------------------------------------------
    # JUDILIBRE TOOLS
    # -----------------------------------------------------------------------

    @mcp.tool()
    async def judilibre_search(
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
            jurisdiction: Court — "cc" (Cour de cassation), "ca" (Cours d'appel), "tj" (Tribunaux).
            date_start: Optional start date in YYYY-MM-DD format.
            date_end: Optional end date in YYYY-MM-DD format.
            solution: Optional — "cassation", "rejet", "annulation", "irrecevabilite".
            publication: Optional — "b" (Bulletin), "r" (Rapport), "l" (Lettre).
        """
        if len(query) < 2:
            return {"error": "Query must be at least 2 characters."}

        params: dict[str, str] = {"query": query}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        if solution:
            params["solution"] = solution
        if publication:
            params["publication"] = publication

        data = await _judilibre_request("/search", params)
        if not data:
            return {"results": [], "sources": {}}

        results = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            results = []

        sources = {}
        formatted = []
        for r in results[:10]:
            decision_id = r.get("id", "")
            number = r.get("number", "")
            decision_date = r.get("decision_date", "")
            ecli = r.get("ecli", "")
            sol = r.get("solution", "")
            themes = r.get("themes", [])
            if decision_id:
                url = f"{JUDILIBRE_UI_BASE}/{decision_id}"
                title = f"Decision {number} ({decision_date})"
                sources[url] = title
            formatted.append(
                {
                    "id": decision_id,
                    "number": number,
                    "date": decision_date,
                    "ecli": ecli,
                    "solution": sol,
                    "themes": themes[:5] if themes else [],
                }
            )
        return {"results": formatted, "sources": sources}

    @mcp.tool()
    async def judilibre_get_decision(decision_id: str) -> dict:
        """Retrieve the full content of a Judilibre decision by its ID.

        Args:
            decision_id: The Judilibre decision identifier (minimum 10 characters).
        """
        if len(decision_id) < 10:
            return {"error": "decision_id must be at least 10 characters."}

        data = await _judilibre_request(f"/decision/{decision_id}", {"resolve_references": "true"})
        if not data:
            return {"error": f"Decision '{decision_id}' not found."}

        text = data.get("text", "")
        if len(text) > 8000:
            text = text[:8000] + "\n\n[... truncated ...]"

        url = f"{JUDILIBRE_UI_BASE}/{decision_id}"
        return {
            "id": decision_id,
            "number": data.get("number", ""),
            "date": data.get("decision_date", ""),
            "jurisdiction": data.get("jurisdiction", ""),
            "chamber": data.get("chamber", ""),
            "ecli": data.get("ecli", ""),
            "solution": data.get("solution", ""),
            "themes": data.get("themes", []),
            "text": text,
            "url": url,
            "sources": {url: f"Decision {data.get('number', decision_id)}"},
        }
