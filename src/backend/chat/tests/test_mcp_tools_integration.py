"""Tests for MCP tools integration feature."""

from unittest.mock import patch

import pytest
from pydantic_ai.models.openai import OpenAIChatModel

from chat.agents.base import BaseAgent
from chat.llm_configuration import LLModel, LLMProvider
from chat.mcp_servers import get_mcp_servers


@pytest.fixture()
def _openai_model_config(settings):
    """Configure a minimal OpenAI model for testing."""
    settings.LLM_CONFIGURATIONS = {
        "test-model": LLModel(
            hrid="test-model",
            model_name="test-model-v1",
            human_readable_name="Test Model",
            provider=LLMProvider(
                hrid="openai",
                kind="openai",
                base_url="https://test.vllm/v1",
                api_key="testkey",
            ),
            is_active=True,
            system_prompt="You are a test assistant.",
            tools=["get_current_weather"],
        ),
    }


class TestMCPToolsBypass:
    """Test that MCP_TOOLS_ENABLED bypasses local tool registration."""

    @pytest.mark.usefixtures("_openai_model_config")
    def test_local_tools_loaded_when_mcp_disabled(self, settings):
        """When MCP is off, local tools are loaded normally."""
        settings.MCP_TOOLS_ENABLED = False
        agent = BaseAgent(model_hrid="test-model")
        assert isinstance(agent._model, OpenAIChatModel)
        # Should have the get_current_weather tool
        tool_names = [t.name for t in agent._tool_defs]
        assert "get_current_weather" in tool_names

    @pytest.mark.usefixtures("_openai_model_config")
    def test_no_local_tools_when_mcp_enabled(self, settings):
        """When MCP is on, no local tools are loaded."""
        settings.MCP_TOOLS_ENABLED = True
        agent = BaseAgent(model_hrid="test-model")
        assert agent._tool_defs == []

    @pytest.mark.usefixtures("_openai_model_config")
    def test_no_local_tools_when_mcp_enabled_even_with_config(self, settings):
        """Even if the model config lists tools, MCP mode skips them all."""
        settings.MCP_TOOLS_ENABLED = True
        settings.LLM_CONFIGURATIONS["test-model"].tools = [
            "get_current_weather",
        ]
        agent = BaseAgent(model_hrid="test-model")
        assert agent._tool_defs == []


class TestMCPServersConfig:
    """Test MCP server configuration loading."""

    def test_no_servers_when_config_empty(self, settings):
        """No servers returned when MCP_SERVERS_CONFIG is empty."""
        settings.MCP_SERVERS_CONFIG = {}
        servers = get_mcp_servers()
        assert servers == []

    def test_servers_created_from_config(self, settings):
        """Servers are created from MCP_SERVERS_CONFIG dict."""
        settings.MCP_SERVERS_CONFIG = {
            "test-server": {
                "url": "http://localhost:8080/mcp",
            },
        }
        servers = get_mcp_servers()
        assert len(servers) == 1

    def test_invalid_config_skipped(self, settings):
        """Invalid configs (missing url) are skipped with warning."""
        settings.MCP_SERVERS_CONFIG = {
            "bad-server": {"headers": {"Authorization": "Bearer xxx"}},
            "good-server": {"url": "http://localhost:8080/mcp"},
        }
        servers = get_mcp_servers()
        assert len(servers) == 1

    def test_multiple_servers(self, settings):
        """Multiple servers can be configured."""
        settings.MCP_SERVERS_CONFIG = {
            "server-1": {"url": "http://host1:8080/mcp"},
            "server-2": {"url": "http://host2:9090/mcp"},
        }
        servers = get_mcp_servers()
        assert len(servers) == 2
