"""Tests for Message Architecture Overhaul (Feature 22)."""

import hashlib
import json

from django.test import override_settings

import pytest
from pydantic import TypeAdapter
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from chat import factories
from chat.ai_sdk_types import (
    CarbonMetrics,
    CarbonRange,
    ExtendedUsage,
    TextUIPart,
    UIMessage,
)

pytestmark = pytest.mark.django_db()

ModelMessagesTypeAdapter = TypeAdapter(list[ModelRequest | ModelResponse])


def _make_pydantic_json(pairs):
    """Build pydantic_messages JSON from (role, text) pairs."""
    msgs = []
    for role, text in pairs:
        if role == "user":
            msgs.append(
                ModelRequest(parts=[UserPromptPart(content=text)], kind="request")
            )
        else:
            msgs.append(
                ModelResponse(parts=[TextPart(content=text)], kind="response")
            )
    return json.loads(ModelMessagesTypeAdapter.dump_json(msgs).decode("utf-8"))


def _stable_id(pk, idx):
    """Compute stable message ID like the model does."""
    return f"msg-{hashlib.md5(f'{pk}-{idx}'.encode()).hexdigest()[:8]}"


class TestGetComputedMessages:
    """Tests for ChatConversation.get_computed_messages()."""

    def test_empty_pydantic_messages(self):
        conv = factories.ChatConversationFactory(pydantic_messages=[])
        assert conv.get_computed_messages() == []

    def test_stable_id_generation(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assert len(result) == 2
        assert result[0].id == _stable_id(conv.pk, 0)
        assert result[1].id == _stable_id(conv.pk, 1)

    def test_stable_id_is_deterministic(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        r1 = conv.get_computed_messages()
        r2 = conv.get_computed_messages()
        assert [m.id for m in r1] == [m.id for m in r2]

    def test_feedback_enrichment(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_feedbacks = {msg_id: {"value": "positive"}}
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        assert assistant_msg.feedback == "positive"

    def test_feedback_legacy_format(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_feedbacks = {msg_id: "negative"}
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        assert assistant_msg.feedback == "negative"

    def test_usage_enrichment(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_usages = {
            msg_id: {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "latency_ms": 1234.5,
            }
        }
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        assert assistant_msg.usage is not None
        assert assistant_msg.usage.prompt_tokens == 100
        assert assistant_msg.usage.completion_tokens == 50
        assert assistant_msg.usage.latency_ms == 1234.5

    def test_usage_with_carbon(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_usages = {
            msg_id: {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "carbon": {
                    "kWh": {"min": 0.001, "max": 0.005},
                    "kgCO2eq": {"min": 0.0001, "max": 0.0005},
                },
            }
        }
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        assert assistant_msg.usage.carbon is not None
        assert assistant_msg.usage.carbon.kWh.min == 0.001

    def test_sources_enrichment(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_sources = {
            msg_id: [
                {
                    "source": {
                        "sourceType": "url",
                        "id": "src-1",
                        "url": "https://example.com",
                        "title": "Example",
                        "providerMetadata": {},
                    }
                }
            ]
        }
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        source_parts = [p for p in assistant_msg.parts if p.type == "source"]
        assert len(source_parts) == 1
        assert source_parts[0].source.url == "https://example.com"

    def test_no_feedback_no_usage_no_sources(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        assert assistant_msg.feedback is None
        assert assistant_msg.usage is None
        source_parts = [p for p in assistant_msg.parts if p.type == "source"]
        assert len(source_parts) == 0


class TestSerializerConditional:
    """Tests for ChatConversationSerializer conditional messages."""

    @override_settings(MESSAGE_ARCHITECTURE_ENABLED=False)
    def test_flag_off_returns_stored_messages(self):
        conv = factories.ChatConversationFactory()
        from chat.serializers import ChatConversationSerializer  # noqa: PLC0415

        serializer = ChatConversationSerializer(conv)
        assert isinstance(serializer.data["messages"], list)

    @override_settings(MESSAGE_ARCHITECTURE_ENABLED=True)
    def test_flag_on_returns_computed_messages_with_stable_ids(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        from chat.serializers import ChatConversationSerializer  # noqa: PLC0415

        serializer = ChatConversationSerializer(conv)
        messages = serializer.data["messages"]
        assert len(messages) == 2
        assert messages[0]["id"].startswith("msg-")
        assert messages[1]["id"].startswith("msg-")

    @override_settings(MESSAGE_ARCHITECTURE_ENABLED=True)
    def test_flag_on_includes_feedback_in_messages(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        msg_id = _stable_id(conv.pk, 1)
        conv.message_feedbacks = {msg_id: {"value": "positive"}}
        conv.save()

        from chat.serializers import ChatConversationSerializer  # noqa: PLC0415

        serializer = ChatConversationSerializer(conv)
        messages = serializer.data["messages"]
        assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
        assert assistant_msg["feedback"] == "positive"


class TestExtendedUsageTypes:
    """Tests for new type definitions."""

    def test_carbon_range(self):
        cr = CarbonRange(min=0.001, max=0.005)
        assert cr.min == 0.001
        assert cr.max == 0.005

    def test_carbon_metrics(self):
        cm = CarbonMetrics(
            kWh=CarbonRange(min=0.001, max=0.005),
            kgCO2eq=CarbonRange(min=0.0001, max=0.0005),
        )
        assert cm.kWh.min == 0.001
        assert cm.kgCO2eq.max == 0.0005

    def test_extended_usage(self):
        eu = ExtendedUsage(
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.003,
            carbon=CarbonMetrics(kWh=CarbonRange(min=0.001, max=0.005)),
            latency_ms=1234.5,
        )
        assert eu.prompt_tokens == 100
        assert eu.cost == 0.003

    def test_ui_message_with_usage(self):
        msg = UIMessage(
            id="test-1",
            role="assistant",
            content="Hello",
            parts=[TextUIPart(type="text", text="Hello")],
            usage=ExtendedUsage(prompt_tokens=10, completion_tokens=5),
        )
        assert msg.usage.prompt_tokens == 10

    def test_ui_message_with_feedback(self):
        msg = UIMessage(
            id="test-1",
            role="assistant",
            content="Hello",
            parts=[TextUIPart(type="text", text="Hello")],
            feedback="positive",
        )
        assert msg.feedback == "positive"
