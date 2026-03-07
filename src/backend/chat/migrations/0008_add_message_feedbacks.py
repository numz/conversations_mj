"""Migration to add message_feedbacks field for local feedback (Feature 21)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0007_add_message_usages"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatconversation",
            name="message_feedbacks",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="User feedback per message ID: {message_id: {value: 'positive'|'negative', comment?: string}}",
            ),
        ),
    ]
