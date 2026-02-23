"""Test the post_score_message view with LOCAL_FEEDBACK_ENABLED."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status

from core.factories import UserFactory

from chat import factories

pytestmark = pytest.mark.django_db()


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_positive_persists_in_db(api_client):
    """Test that positive feedback is persisted in database when flag is on."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    message_id = "msg-123"

    with patch("langfuse.get_client"):
        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "positive",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    chat_conversation.refresh_from_db()
    assert message_id in chat_conversation.message_feedbacks
    assert chat_conversation.message_feedbacks[message_id]["value"] == "positive"


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_negative_with_comment(api_client):
    """Test that negative feedback with comment is persisted."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    message_id = "msg-456"

    with patch("langfuse.get_client"):
        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "negative",
                "comment": "Response was inaccurate",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    chat_conversation.refresh_from_db()
    feedback = chat_conversation.message_feedbacks[message_id]
    assert feedback["value"] == "negative"
    assert feedback["comment"] == "Response was inaccurate"


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_without_comment_no_comment_key(api_client):
    """Test that feedback without comment doesn't store empty comment."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    message_id = "msg-789"

    with patch("langfuse.get_client"):
        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "positive",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    chat_conversation.refresh_from_db()
    feedback = chat_conversation.message_feedbacks[message_id]
    assert "comment" not in feedback


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_without_trace_prefix_succeeds(api_client):
    """Test that feedback works without trace- prefix when flag is on."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    with patch("langfuse.get_client"):
        response = api_client.post(
            url,
            data={
                "message_id": "non-trace-message",
                "value": "positive",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_with_trace_prefix_sends_to_langfuse(api_client):
    """Test that feedback with trace- prefix also sends to Langfuse."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    trace_id = "test-trace-123"
    message_id = f"trace-{trace_id}"

    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "positive",
            },
            format="json",
        )

        mock_client.create_score.assert_called_once_with(
            name="sentiment",
            value="positive",
            trace_id=trace_id,
            score_id=f"{trace_id}-{chat_conversation.owner.pk}",
            data_type="CATEGORICAL",
        )

    assert response.status_code == status.HTTP_200_OK
    # Also persisted in DB
    chat_conversation.refresh_from_db()
    assert chat_conversation.message_feedbacks[message_id]["value"] == "positive"


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_langfuse_error_does_not_fail(api_client):
    """Test that Langfuse error doesn't prevent local persistence."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    trace_id = "test-trace-err"
    message_id = f"trace-{trace_id}"

    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.create_score.side_effect = ConnectionError("Langfuse down")
        mock_get_client.return_value = mock_client

        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "negative",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    chat_conversation.refresh_from_db()
    assert chat_conversation.message_feedbacks[message_id]["value"] == "negative"


@override_settings(LOCAL_FEEDBACK_ENABLED=True)
def test_local_feedback_overwrites_previous(api_client):
    """Test that sending feedback again overwrites the previous value."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    message_id = "msg-overwrite"

    with patch("langfuse.get_client"):
        api_client.post(
            url,
            data={"message_id": message_id, "value": "positive"},
            format="json",
        )
        api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "negative",
                "comment": "Changed my mind",
            },
            format="json",
        )

    chat_conversation.refresh_from_db()
    feedback = chat_conversation.message_feedbacks[message_id]
    assert feedback["value"] == "negative"
    assert feedback["comment"] == "Changed my mind"


@override_settings(LOCAL_FEEDBACK_ENABLED=False)
def test_flag_off_requires_trace_prefix(api_client):
    """Test that with flag off, trace- prefix is still required."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response = api_client.post(
            url,
            data={
                "message_id": "non-trace-message",
                "value": "positive",
            },
            format="json",
        )

        mock_client.create_score.assert_not_called()

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@override_settings(LOCAL_FEEDBACK_ENABLED=False)
def test_flag_off_does_not_persist_in_db(api_client):
    """Test that with flag off, feedback is not persisted in DB."""
    chat_conversation = factories.ChatConversationFactory()
    api_client.force_login(chat_conversation.owner)
    url = f"/api/v1.0/chats/{chat_conversation.pk}/score-message/"

    trace_id = "test-trace-nodb"
    message_id = f"trace-{trace_id}"

    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response = api_client.post(
            url,
            data={
                "message_id": message_id,
                "value": "positive",
            },
            format="json",
        )

    assert response.status_code == status.HTTP_200_OK
    chat_conversation.refresh_from_db()
    assert chat_conversation.message_feedbacks == {}
