# Legifrance & Judilibre Tools

## Overview

The Legifrance tool suite provides the conversation agent with access to the official French legal database
([Legifrance](https://www.legifrance.gouv.fr/)) and the Court of Cassation open data platform
([Judilibre](https://www.courdecassation.fr/acces-rapide-judilibre)).

These tools allow the agent to search and retrieve:
- **Codes and Laws** (Code civil, Code du travail, etc.)
- **Jurisprudence** (judicial, administrative, constitutional, and financial court decisions)
- **Collective Agreements** (conventions collectives, accords d'entreprise)
- **Administrative documents** (JORF, circulaires, CNIL deliberations)
- **Court of Cassation decisions** via Judilibre

## Feature Flag

All Legifrance tools are controlled by a single feature flag:

```
LEGIFRANCE_TOOLS_ENABLED=True
```

When enabled, the tools are **automatically injected** into every agent — no need to add them to the
`tools` list in the LLM configuration or `AI_AGENT_TOOLS`. This is handled by `get_legifrance_tools()`
in `chat/tools/__init__.py`, called from `BaseAgent.get_tools()`.

When disabled (default), no Legifrance tools are loaded and the package is not even imported.

## Configuration

### Required Environment Variables

| Variable                     | Description                                  | Default |
|------------------------------|----------------------------------------------|---------|
| `LEGIFRANCE_TOOLS_ENABLED`   | Enable the tool suite                        | `false` |
| `LEGIFRANCE_CLIENT_ID`       | OAuth client ID (from PISTE portal)          |         |
| `LEGIFRANCE_CLIENT_SECRET`   | OAuth client secret (from PISTE portal)      |         |

### Optional Environment Variables

| Variable                     | Description                                  | Default |
|------------------------------|----------------------------------------------|---------|
| `LEGIFRANCE_API_BASE_URL`    | Legifrance API base URL                      | `https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app` |
| `LEGIFRANCE_OAUTH_URL`       | OAuth token endpoint                         | `https://sandbox-oauth.piste.gouv.fr/api/oauth/token` |
| `LEGIFRANCE_API_TOKEN`       | Static API token (alternative to OAuth)      |         |
| `LEGIFRANCE_OAUTH_HOST`      | OAuth host override                          |         |
| `LEGIFRANCE_API_HOST`        | API host override                            |         |
| `LEGIFRANCE_SSL_VERIFY`      | Enable SSL verification                      | `true`  |

### Getting API Credentials

Register on the [PISTE portal](https://developer.aife.economie.gouv.fr/) to obtain OAuth credentials
for the Legifrance API. The sandbox environment is available for testing.

## Tools Reference

### Legifrance Search Tools

#### `legifrance_search_codes_lois`

Search in French Codes and Laws (CODE and LODA fonds).

**Parameters:**
- `query` (str): Search query text
- `code_name` (str, optional): Filter by code name (e.g. "Code civil")
- `date_start` / `date_end` (str, optional): Date range filter
- `legal_status` (str, optional): Filter by legal status (e.g. "VIGUEUR" for in force)
- `page_size` (int, optional): Number of results

**Use case:** The user asks about a specific law, article, or legal provision.

---

#### `legifrance_search_jurisprudence`

Search in French Jurisprudence across all jurisdictions.

**Parameters:**
- `query` (str): Search query text
- `jurisdiction` (str, optional): Filter by jurisdiction type (judiciaire, administratif, constitutionnel, financier)
- `date_start` / `date_end` (str, optional): Date range filter
- `decision_number` (str, optional): Filter by decision number
- `page_size` (int, optional): Number of results

**Use case:** The user asks about court decisions, case law, or legal precedents.

---

#### `legifrance_search_conventions`

Search in Collective Bargaining Agreements (conventions collectives) and Company Agreements (accords d'entreprise).

**Parameters:**
- `query` (str): Search query text
- `idcc` (str, optional): Filter by IDCC number
- `date_start` / `date_end` (str, optional): Date range filter
- `page_size` (int, optional): Number of results

**Use case:** The user asks about collective agreements, labor conventions, or IDCC codes.

---

#### `legifrance_search_admin`

Search in JORF (Journal Officiel), circulaires, and CNIL deliberations.

**Parameters:**
- `query` (str): Search query text
- `source` (str, optional): Filter by source type (jorf, circ, cnil)
- `date_start` / `date_end` (str, optional): Date range filter
- `page_size` (int, optional): Number of results

**Use case:** The user asks about official publications, administrative circulars, or CNIL decisions.

---

#### `legifrance_search_code_article_by_number`

Search for a specific article number within a specific legal code. Uses an exact match strategy.

**Parameters:**
- `code_name` (str): The name of the Code (e.g. "Code civil", "Code du travail")
- `article_num` (str): The article number (e.g. "1240", "L1234-5")

**Use case:** The user asks for "Article 1240 du Code civil" or similar precise references.

---

#### `legifrance_get_document`

Retrieve the full text of a legal document from Legifrance by its identifier.

**Parameters:**
- `article_id` (str): The unique document identifier (e.g. "LEGIARTI...", "JORFTEXT...", "KALITEXT...", "JURITEXT...")

**Use case:** The agent found a document ID via search and needs to read its full content.

---

#### `legifrance_list_codes`

List available French legal codes, optionally filtered by name.

**Parameters:**
- `code_name` (str, optional): Filter by code name (e.g. "urbanisme" to find "Code de l'urbanisme"). Leave empty to list all codes.

**Use case:** The agent needs to find the exact name of a legal code before searching in it.

---

### Judilibre Tools

#### `judilibre_search`

Search in Judilibre, the Court of Cassation's open data platform.

**Parameters:**
- `query` (str): Search query text
- `jurisdiction` (str, optional): Filter by jurisdiction (cc, ca, tj)
- `chamber` (str, optional): Filter by chamber
- `date_start` / `date_end` (str, optional): Date range filter
- `solution` (str, optional): Filter by solution type (cassation, rejet, annulation, irrecevabilite)
- `publication` (str, optional): Filter by publication level (b=bulletin, r=rapport, l=lettre)

**Use case:** The user asks about Court of Cassation decisions or wants to search in Judilibre specifically.

---

#### `judilibre_get_decision`

Get the full text of a Court of Cassation decision from Judilibre.

**Parameters:**
- `decision_id` (str): The Judilibre decision ID

**Use case:** The agent found a decision ID via `judilibre_search` and needs to read the full text.

## Architecture

```
chat/tools/legifrance/
    __init__.py          # Package exports
    api.py               # HTTP client for Legifrance API (OAuth, requests)
    judilibre_api.py     # HTTP client for Judilibre API
    cache.py             # Caching utilities
    constants.py         # API constants (fonds, facets, sort options)
    exceptions.py        # Exception hierarchy (LegifranceError, etc.)
    logging_utils.py     # Logging utilities
    core/                # Shared models, criteria builders, parsers, schemas
    tools/               # Individual tool functions (one per file)
```

### Error Handling

All tools use the `@last_model_retry_soft_fail` decorator which:
- Raises `ModelRetry` for transient errors (rate limits, timeouts, server errors) so the LLM can retry
- Converts unexpected errors to a string message returned to the LLM (soft fail)

### Caching

The API client caches OAuth tokens to avoid unnecessary authentication requests.
Search results are not cached by default.

## See Also

- [Tools Overview](../tools.md)
- [Environment Variables](../env.md)
- [LLM Configuration](../llm-configuration.md)
