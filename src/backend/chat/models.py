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

    message_feedbacks = models.JSONField(
        default=dict,
        blank=True,
        help_text="User feedback per message ID: "
        "{message_id: {value: 'positive'|'negative', comment?: string}}",
    )

    message_usages = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extended usage metrics per message ID (tokens, cost, carbon, latency)",
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
        4. Enrich with feedback, usage, and sources from normalized fields
        """
        from pydantic import TypeAdapter  # noqa: PLC0415
        from pydantic_ai.messages import ModelMessage  # noqa: PLC0415

        from chat.ai_sdk_types import (  # noqa: PLC0415
            CarbonMetrics,
            CarbonRange,
            ExtendedUsage,
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
            parsed_messages = ModelMessagesTypeAdapter.validate_python(
                self.pydantic_messages
            )
        except Exception:
            logger.exception(
                "Failed to parse pydantic_messages for conversation %s",
                self.pk,
            )
            return []

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

                    # Apply stored feedback
                    feedback = self.message_feedbacks.get(ui_msg.id)
                    if feedback is not None:
                        if isinstance(feedback, dict):
                            ui_msg.feedback = feedback.get("value")
                        else:
                            ui_msg.feedback = feedback

                    # Apply stored usage metrics
                    usage_data = self.message_usages.get(ui_msg.id)
                    if usage_data:
                        carbon = None
                        if usage_data.get("carbon"):
                            carbon_raw = usage_data["carbon"]
                            carbon = CarbonMetrics(
                                kWh=CarbonRange(**carbon_raw["kWh"])
                                if carbon_raw.get("kWh")
                                else None,
                                kgCO2eq=CarbonRange(**carbon_raw["kgCO2eq"])
                                if carbon_raw.get("kgCO2eq")
                                else None,
                            )

                        ui_msg.usage = ExtendedUsage(
                            prompt_tokens=usage_data.get("prompt_tokens", 0),
                            completion_tokens=usage_data.get(
                                "completion_tokens", 0
                            ),
                            cost=usage_data.get("cost"),
                            carbon=carbon,
                            latency_ms=usage_data.get("latency_ms"),
                        )

                    # Apply stored sources
                    sources_data = self.message_sources.get(ui_msg.id)
                    if sources_data:
                        for source_item in sources_data:
                            source_obj = SourceUIPart(
                                type="source",
                                source=LanguageModelV1Source(
                                    **source_item["source"]
                                ),
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

        return result


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
