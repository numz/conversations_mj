"""Tests for Message Architecture Overhaul (Feature 22).

Feature 22 is a pure architecture foundation:
- Computed messages from pydantic_messages with stable IDs
- Sources enrichment from message_sources
- No knowledge of feedback (#21) or usage metrics (#17)
"""

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

pytestmark = pytest.mark.django_db()

ModelMessagesTypeAdapter = TypeAdapter(list[ModelRequest | ModelResponse])


def _make_pydantic_json(pairs):
    """Build pydantic_messages JSON from (role, text) pairs."""
    msgs = []
    for role, text in pairs:
        if role == "user":
            msgs.append(ModelRequest(parts=[UserPromptPart(content=text)], kind="request"))
        else:
            msgs.append(ModelResponse(parts=[TextPart(content=text)], kind="response"))
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

    def test_message_roles(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assert result[0].role == "user"
        assert result[1].role == "assistant"

    def test_message_content(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assert result[0].content == "Hello"
        assert result[1].content == "Hi!"

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

    def test_multiple_sources(self):
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
                        "title": "Example 1",
                        "providerMetadata": {},
                    }
                },
                {
                    "source": {
                        "sourceType": "url",
                        "id": "src-2",
                        "url": "https://example.org",
                        "title": "Example 2",
                        "providerMetadata": {},
                    }
                },
            ]
        }
        conv.save()

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        source_parts = [p for p in assistant_msg.parts if p.type == "source"]
        assert len(source_parts) == 2

    def test_no_sources(self):
        pydantic_json = _make_pydantic_json([("user", "Hello"), ("assistant", "Hi!")])
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assistant_msg = [m for m in result if m.role == "assistant"][0]
        source_parts = [p for p in assistant_msg.parts if p.type == "source"]
        assert len(source_parts) == 0

    def test_invalid_pydantic_messages_returns_empty(self):
        conv = factories.ChatConversationFactory(pydantic_messages=[{"invalid": "data"}])
        result = conv.get_computed_messages()
        assert result == []

    def test_multi_turn_conversation(self):
        pydantic_json = _make_pydantic_json(
            [
                ("user", "Hello"),
                ("assistant", "Hi!"),
                ("user", "How are you?"),
                ("assistant", "I'm good!"),
            ]
        )
        conv = factories.ChatConversationFactory(pydantic_messages=pydantic_json)

        result = conv.get_computed_messages()
        assert len(result) == 4
        for i, msg in enumerate(result):
            assert msg.id == _stable_id(conv.pk, i)


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
    def test_flag_on_with_sources(self):
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

        from chat.serializers import ChatConversationSerializer  # noqa: PLC0415

        serializer = ChatConversationSerializer(conv)
        messages = serializer.data["messages"]
        assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
        source_parts = [p for p in assistant_msg["parts"] if p["type"] == "source"]
        assert len(source_parts) == 1

    @override_settings(MESSAGE_ARCHITECTURE_ENABLED=False)
    def test_flag_off_empty_conversation(self):
        conv = factories.ChatConversationFactory()
        from chat.serializers import ChatConversationSerializer  # noqa: PLC0415

        serializer = ChatConversationSerializer(conv)
        assert serializer.data["messages"] == []
