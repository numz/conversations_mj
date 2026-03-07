"""Conversations MCP Server — standalone replica of all tools.

Run with:
    python server.py                          # StreamableHTTP on port 8080
    python server.py --transport sse          # SSE transport
    python server.py --port 9090              # Custom port
    MCP_TRANSPORT=sse MCP_PORT=9090 python server.py  # Via env vars
"""

import argparse
import logging
import os

from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "DEBUG").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp-server")


def parse_args():
    parser = argparse.ArgumentParser(description="Conversations MCP Server")
    parser.add_argument(
        "--transport",
        default=os.environ.get("MCP_TRANSPORT", "streamable-http"),
        choices=["streamable-http", "sse", "stdio"],
        help="MCP transport type (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8080")),
        help="Port to listen on (default: 8080)",
    )
    return parser.parse_args()


args = parse_args()

mcp = FastMCP(
    "conversations-tools",
    instructions=(
        "MCP server providing all Conversations tools: "
        "weather, web search (Brave, Tavily), document management, "
        "Legifrance legal search, and Judilibre jurisprudence."
    ),
    host=args.host,
    port=args.port,
)

# Register tool modules based on MCP_ENABLED_MODULES (default: all)
_enabled = os.environ.get("MCP_ENABLED_MODULES", "").strip()
_enabled_modules = {m.strip() for m in _enabled.split(",") if m.strip()} if _enabled else None

_all_modules = {
    "weather": lambda: __import__("tools.weather", fromlist=["register"]).register(mcp),
    "web_search": lambda: __import__("tools.web_search", fromlist=["register"]).register(mcp),
    "documents": lambda: __import__("tools.documents", fromlist=["register"]).register(mcp),
    "legifrance": lambda: __import__("tools.legifrance", fromlist=["register"]).register(mcp),
}

for name, register_fn in _all_modules.items():
    if _enabled_modules is None or name in _enabled_modules:
        register_fn()
        logger.info("Registered module: %s", name)
    else:
        logger.info("Skipped module: %s", name)


def main():
    logger.info(
        "Starting MCP server on %s:%d (transport: %s)",
        args.host,
        args.port,
        args.transport,
    )
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
