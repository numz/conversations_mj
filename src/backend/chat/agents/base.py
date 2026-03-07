"""Base module for PydanticAI agents."""

import dataclasses
import json
import logging
from contextvars import ContextVar
from typing import Any, AsyncIterator, Optional

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import httpx
from pydantic_ai import Agent
from pydantic_ai.models import get_user_agent
from pydantic_ai.profiles import ModelProfile

from chat.tools import get_pydantic_tools_by_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extended Metrics — capture usage data from LLM SSE responses
# ---------------------------------------------------------------------------


class ExtendedMetrics:
    """Dynamic container for extended metrics captured from LLM responses."""

    def __init__(self):
        self._data: dict[str, Any] = {}

    def set(self, name: str, value: Any) -> None:
        self._data[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self._data.get(name, default)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name)

    def __repr__(self) -> str:
        return f"ExtendedMetrics({self._data})"

    def has_metrics(self) -> bool:
        return bool(self._data)

    def to_dict(self) -> dict[str, Any]:
        return self._data.copy()


_current_metrics: ContextVar[Optional[ExtendedMetrics]] = ContextVar(
    "extended_metrics", default=None
)


def get_current_metrics() -> Optional[ExtendedMetrics]:
    return _current_metrics.get()


def clear_current_metrics() -> None:
    _current_metrics.set(None)


def _get_nested_value(data: dict, path: str) -> Any:
    """Extract a value from a nested dict using dot notation (e.g. 'carbon.kWh.min')."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def set_metrics_from_usage(usage_data: dict) -> None:
    """Set extended metrics from a usage dict based on EXTENDED_METRICS_MAPPING."""
    if not usage_data:
        return
    if not getattr(settings, "EXTENDED_METRICS_ENABLED", False):
        return

    mapping = getattr(settings, "EXTENDED_METRICS_MAPPING", {})
    if not mapping:
        return

    metrics = ExtendedMetrics()
    for metric_name, json_path in mapping.items():
        value = _get_nested_value(usage_data, json_path)
        if value is not None:
            metrics.set(metric_name, value)

    if metrics.has_metrics():
        _current_metrics.set(metrics)
        logger.info("Extended metrics captured: %s", metrics)


class SSEInterceptorStream(httpx.AsyncByteStream):
    """Wraps an async byte stream to intercept SSE chunks and capture usage metrics."""

    def __init__(self, original_stream: httpx.AsyncByteStream):
        self._original_stream = original_stream
        self._buffer = b""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._original_stream:
            self._buffer += chunk
            yield chunk
            self._process_buffer()

    async def aclose(self) -> None:
        await self._original_stream.aclose()

    def _process_buffer(self) -> None:
        while b"\n\n" in self._buffer or b"\r\n\r\n" in self._buffer:
            sep = b"\n\n" if b"\n\n" in self._buffer else b"\r\n\r\n"
            event_end = self._buffer.find(sep)
            if event_end == -1:
                break
            event_data = self._buffer[:event_end]
            self._buffer = self._buffer[event_end + len(sep):]
            self._parse_sse_event(event_data)

    def _parse_sse_event(self, event_data: bytes) -> None:
        try:
            text = event_data.decode("utf-8")
            for line in text.split("\n"):
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        continue
                    try:
                        data = json.loads(data_str)
                        if "usage" in data and data["usage"]:
                            usage = data["usage"]
                            mapping = getattr(settings, "EXTENDED_METRICS_MAPPING", {})
                            root_keys = {path.split(".")[0] for path in mapping.values()}
                            if any(key in usage for key in root_keys):
                                set_metrics_from_usage(usage)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:  # pylint: disable=broad-except
            logger.debug("Error parsing SSE event: %s", e)


class SSEMetricsInterceptor(httpx.AsyncBaseTransport):
    """Async transport wrapper that intercepts SSE responses to capture usage metrics."""

    def __init__(self, transport: httpx.AsyncBaseTransport):
        self._transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._transport.handle_async_request(request)
        if b"chat/completions" in request.url.raw_path:
            response.stream = SSEInterceptorStream(response.stream)
        return response


def create_opengatellm_http_client() -> httpx.AsyncClient:
    """Create an httpx AsyncClient with SSE metrics interception for OpenGateLLM."""
    return httpx.AsyncClient(
        transport=SSEMetricsInterceptor(httpx.AsyncHTTPTransport()),
        timeout=httpx.Timeout(timeout=600, connect=5),
        headers={"User-Agent": get_user_agent()},
    )


def prepare_custom_model(configuration: "chat.llm_configuration.LLModel"):
    """
    Prepare a custom model instance based on the provided configuration.

    Only few providers are supported at the moment, according to our needs.
    We define custom models/providers to be able to keep specific configuration
    when needed.
    """
    # pylint: disable=import-outside-toplevel

    match configuration.provider.kind:
        case "mistral":
            import pydantic_ai.models.mistral as mistral_models  # noqa: PLC0415
            from mistralai import TextChunk as MistralTextChunk  # noqa: PLC0415
            from mistralai import ThinkChunk as MistralThinkChunk  # noqa: PLC0415
            from mistralai.types.basemodel import Unset as MistralUnset  # noqa: PLC0415
            from pydantic_ai.providers.mistral import MistralProvider  # noqa: PLC0415

            # --- Monkey patch for pydantic_ai.models.mistral._map_content ---
            # pylint: disable=protected-access

            # ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠
            # |  This workaround is fragile and only works because we are in streaming mode.  |
            # ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠ WARNING ⚠

            # The original _map_content raises exceptions for some when responses
            # contains citation/reference data, which is the case anytime we use
            # web search or other RAG tool (https://docs.mistral.ai/capabilities/citations/).
            # We make the patch idempotent using a sentinel attribute so repeated calls
            # to prepare_custom_model do not re-wrap and do not cause recursive calls.
            if not getattr(mistral_models, "__safe_map_patched__", False):
                _original_map_content = mistral_models._map_content  # noqa: SLF001

                def _safe_map_content(content):
                    """
                    A safe version of _map_content that ignores unsupported data types.

                    WARNING: this is a monkey patch and may break if the original
                    function changes in future versions of pydantic_ai.
                    Current version: pydantic_ai v1.0.18
                    """
                    text: str | None = None
                    thinking: list[str] = []

                    if isinstance(content, MistralUnset) or not content:
                        return None, []

                    if isinstance(content, list):
                        for chunk in content:
                            if isinstance(chunk, MistralTextChunk):
                                text = (text or "") + chunk.text
                            elif isinstance(chunk, MistralThinkChunk):
                                for thought in chunk.thinking:
                                    if thought.type == "text":  # pragma: no branch
                                        thinking.append(thought.text)
                            else:
                                logger.info(  # pragma: no cover
                                    "Other data types like (Image, Reference) are not yet "
                                    "supported,  got %s",
                                    type(chunk),
                                )
                    elif isinstance(content, str):
                        text = content

                    # Note: Check len to handle potential mismatch between function calls and
                    # responses from the API.
                    # (`msg: not the same number of function class and responses`)
                    if text == "":  # pragma: no cover
                        text = None

                    return text, thinking

                # Replace the original module-level function
                mistral_models._map_content = _safe_map_content  # noqa: SLF001
                mistral_models.__safe_map_patched__ = True
            # pylint: enable=protected-access
            # --- End monkey patch ---

            return mistral_models.MistralModel(
                model_name=configuration.model_name,
                profile=(
                    ModelProfile(**configuration.profile.dict(exclude_unset=True))
                    if configuration.profile
                    else None
                ),
                provider=MistralProvider(
                    api_key=configuration.provider.api_key,
                    base_url=configuration.provider.base_url,
                    # Disable the use of cached client
                    http_client=httpx.AsyncClient(
                        timeout=httpx.Timeout(timeout=600, connect=5),
                        headers={"User-Agent": get_user_agent()},
                    ),
                ),
            )
        case "openai":
            from pydantic_ai.models.openai import OpenAIChatModel  # noqa: PLC0415
            from pydantic_ai.profiles.openai import OpenAIModelProfile  # noqa: PLC0415
            from pydantic_ai.providers.openai import OpenAIProvider  # noqa: PLC0415

            if configuration.profile and (
                _config_profile := configuration.profile.dict(exclude_unset=True)
            ):
                # set some defaults if not provided, see openai_model_profile which
                # defines them for known models
                _model_profile_params = {
                    "supports_json_schema_output": True,
                    "supports_json_object_output": True,
                }
                _model_profile_params.update(_config_profile)
                profile = OpenAIModelProfile(**_model_profile_params)
            else:
                profile = None

            return OpenAIChatModel(
                model_name=configuration.model_name,
                profile=profile,
                provider=OpenAIProvider(
                    base_url=configuration.provider.base_url,
                    api_key=configuration.provider.api_key,
                    http_client=create_opengatellm_http_client(),
                ),
            )
        case _:
            raise ImproperlyConfigured(
                f"Unsupported provider kind '{configuration.provider.kind}' for custom model."
            )


@dataclasses.dataclass(init=False)
class BaseAgent(Agent):
    """
    Base class for PydanticAI agents.

    This class initializes the agent with model from configuration.
    """

    def __init__(self, *, model_hrid, **kwargs):
        """Initialize the agent with model configuration from settings."""
        _ignored_kwargs = {"model", "system_prompt", "tools", "toolsets"}
        if set(kwargs).intersection(_ignored_kwargs):
            raise ValueError(f"{_ignored_kwargs} arguments must not be provided.")

        try:
            self.configuration = settings.LLM_CONFIGURATIONS[model_hrid]
        except KeyError as exc:
            raise ImproperlyConfigured(
                f"LLM model configuration '{model_hrid}' not found."
            ) from exc

        if self.configuration.is_custom:
            _model_instance = prepare_custom_model(self.configuration)
        else:
            # In this case, we rely on PydanticAI's built-in model registry
            # and configuration: check pydantic_ai.models.KnownModelName
            # and pydantic_ai.models.infer_model()
            _model_instance = self.configuration.model_name

        _system_prompt = self.get_system_prompt()

        _tools = self.get_tools()

        super().__init__(model=_model_instance, instructions=_system_prompt, tools=_tools, **kwargs)

    def get_system_prompt(self) -> str | None:
        """Override this method to customize the system prompt."""
        return self.configuration.system_prompt

    def get_tools(self) -> list | None:
        """Override this method to customize tools."""
        if not self.configuration.tools:
            return []
        return [get_pydantic_tools_by_name(tool_name) for tool_name in self.configuration.tools]
