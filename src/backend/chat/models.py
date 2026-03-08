"""Models for chat conversations."""

import hashlib
import logging
from typing import Sequence

from django.contrib.auth import get_user_model
from django.db import models

from django_pydantic_field import SchemaField

from core.file_upload.enums import AttachmentStatus
from core.models import BaseModel

from chat.ai_sdk_types import UIMessage

User = get_user_model()

logger = logging.getLogger(__name__)


class ChatConversation(BaseModel):
    """
    Model representing a chat conversation.

    This model stores the details of a chat conversation:
    - `owner`: The user who owns the conversation.
    - `title`: An optional title for the conversation, provided by frontend,
      the 100 first characters of the first user input message.
    - `ui_messages`: A JSON field of UI messages sent by the frontend, all content is
      overridden at each new request from the frontend.
    - `pydantic_messages`: A JSON field of PydanticAI messages, used to store conversation history.
    - `messages`: A JSON field of stored messages for the conversation, sent to frontend
       when loading the conversation.
    - `agent_usage`: A JSON field of agent usage statistics for the conversation,
    """

    owner = models.ForeignKey(
        User,
        related_name="conversations",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Title of the chat conversation",
    )
    title_set_by_user_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when the user manually set the title. If set, prevent automatic "
        "title generation.",
    )
    ui_messages = models.JSONField(
        default=list,
        blank=True,
        help_text="UI messages for the chat conversation, sent by frontend, not used",
    )
    pydantic_messages = models.JSONField(
        default=list,
        blank=True,
        help_text="Pydantic messages for the chat conversation, used for history",
    )
    messages: Sequence[UIMessage] = SchemaField(
        schema=list[UIMessage],
        default=list,
        blank=True,
        help_text="Stored messages for the chat conversation, sent to frontend",
    )

    agent_usage = models.JSONField(
        default=dict,
        blank=True,
        help_text="Agent usage for the chat conversation, provided by OpenAI API",
    )

    message_sources = models.JSONField(
        default=dict,
        blank=True,
        help_text="Sources per message ID: "
        "{message_id: [{sourceType, id, url, title, providerMetadata}]}",
    )

    collection_id = models.CharField(
        blank=True,
        null=True,
        help_text="Collection ID for the conversation, used for RAG document search",
    )

    def get_computed_messages(self):
        """Compute UIMessages from pydantic_messages on the fly.

        1. Parse pydantic_messages into ModelMessage objects
        2. Convert each to UIMessage via model_message_to_ui_message
        3. Assign stable IDs: msg-{md5(pk-index)[:8]}
        4. Enrich with sources from message_sources
        """
        from pydantic import TypeAdapter  # noqa: PLC0415
        from pydantic_ai.messages import ModelMessage  # noqa: PLC0415

        from chat.ai_sdk_types import (  # noqa: PLC0415
            LanguageModelV1Source,
            SourceUIPart,
        )
        from chat.clients.pydantic_ui_message_converter import (  # noqa: PLC0415
            model_message_to_ui_message,
        )

        if not self.pydantic_messages:
            return []

        ModelMessagesTypeAdapter = TypeAdapter(list[ModelMessage])
        try:
            parsed_messages = ModelMessagesTypeAdapter.validate_python(self.pydantic_messages)
        except Exception:
            logger.exception(
                "Failed to parse pydantic_messages for conversation %s",
                self.pk,
            )
            return []

        from chat.ai_sdk_types import ReasoningUIPart as ReasoningUIPartType  # noqa: PLC0415

        result = []
        for idx, msg in enumerate(parsed_messages):
            try:
                ui_msg = model_message_to_ui_message(msg)
                if ui_msg:
                    # Generate stable ID based on conversation + index
                    stable_id = hashlib.md5(  # noqa: S324
                        f"{self.pk}-{idx}".encode()
                    ).hexdigest()[:8]
                    ui_msg.id = f"msg-{stable_id}"

                    # Apply stored sources
                    sources_data = self.message_sources.get(ui_msg.id)
                    if sources_data:
                        for source_item in sources_data:
                            source_obj = SourceUIPart(
                                type="source",
                                source=LanguageModelV1Source(**source_item["source"]),
                            )
                            ui_msg.parts.append(source_obj)

                    result.append(ui_msg)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to convert message %d in conversation %s",
                    idx,
                    self.pk,
                    exc_info=True,
                )
                continue

        # Merge consecutive assistant messages: multi-step tool calling produces
        # multiple ModelResponse entries (reasoning + tool call, then reasoning + text).
        # We merge all reasoning parts into the last assistant message that has text content.
        merged = []
        pending_reasoning_parts = []
        for msg in result:
            if msg.role == "assistant":
                reasoning_parts = [p for p in msg.parts if isinstance(p, ReasoningUIPartType)]
                non_reasoning_parts = [p for p in msg.parts if not isinstance(p, ReasoningUIPartType)]
                has_text = bool(msg.content)

                if has_text:
                    # Final assistant message with content — prepend accumulated reasoning
                    msg.parts = pending_reasoning_parts + reasoning_parts + non_reasoning_parts
                    pending_reasoning_parts = []
                    merged.append(msg)
                else:
                    # Intermediate assistant message (no text) — collect its reasoning
                    pending_reasoning_parts.extend(reasoning_parts)
            else:
                # Flush any orphan reasoning into a standalone message if no text follows
                if pending_reasoning_parts:
                    pending_reasoning_parts = []
                merged.append(msg)

        return merged


class ChatConversationAttachment(BaseModel):
    """
    Model representing an attachment associated with a chat conversation.

    This model stores the details of an attachment:
    - `conversation`: The conversation this attachment belongs to.
    - `uploaded_by`: The user who uploaded the attachment.
    - `key`: The file path of the attachment in the object storage.
    - `file_name`: The original name of the attachment file.
    - `content_type`: The MIME type of the attachment file.

    """

    conversation = models.ForeignKey(
        ChatConversation,
        related_name="attachments",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    uploaded_by = models.ForeignKey(
        User,
        related_name="uploaded_attachments",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        help_text="User who uploaded the attachment",
    )
    upload_state = models.CharField(
        max_length=40,
        choices=AttachmentStatus.choices,
        default=AttachmentStatus.PENDING,
    )
    key = models.CharField(
        blank=False,
        null=False,
        help_text="File path of the attachment in the object storage",
    )
    file_name = models.CharField(
        blank=False,
        null=False,
        help_text="Original name of the attachment file",
    )
    content_type = models.CharField(
        max_length=100,
        blank=False,
        null=False,
        help_text="MIME type of the attachment file",
    )
    size = models.PositiveBigIntegerField(null=True, blank=True)

    conversion_from = models.CharField(
        blank=True,
        null=True,
        help_text="Original file key if the Markdown from another file",
    )
