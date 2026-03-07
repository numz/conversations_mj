"""Fake weather tool — replica of get_current_weather."""

from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_current_weather(location: str, unit: str = "celsius") -> dict:
        """Get the current weather in a given location.

        Args:
            location: The city and state, e.g. San Francisco, CA
            unit: The temperature unit — "celsius" or "fahrenheit"
        """
        if unit == "fahrenheit":
            return {"location": location, "temperature": "72", "unit": "fahrenheit"}
        return {"location": location, "temperature": "22", "unit": "celsius"}
