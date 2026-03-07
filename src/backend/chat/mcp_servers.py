"""MCP servers configuration.

When MCP_TOOLS_ENABLED is True, servers are loaded from MCP_SERVERS_CONFIG setting.
Format: {"server-name": {"url": "http://host:port/mcp", "headers": {...}}, ...}
"""

import logging

from django.conf import settings

from pydantic_ai.mcp import MCPServerStreamableHTTP

logger = logging.getLogger(__name__)


def get_mcp_servers():
    """Retrieve MCP server instances from configuration.

    Returns a list of MCPServerStreamableHTTP instances ready to be used
    as toolsets in agent.iter().
    """
    servers_config = getattr(settings, "MCP_SERVERS_CONFIG", {})
    if not servers_config:
        return []

    servers = []
    for name, config in servers_config.items():
        if not isinstance(config, dict) or "url" not in config:
            logger.warning("Invalid MCP server config for '%s': missing 'url'", name)
            continue
        logger.info("Registering MCP server '%s' at %s", name, config["url"])
        servers.append(MCPServerStreamableHTTP(**config))
    return servers
