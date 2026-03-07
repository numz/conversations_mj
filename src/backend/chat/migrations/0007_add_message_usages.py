"""Migration to add message_usages field for extended metrics (Feature 17)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0006_add_message_architecture_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatconversation",
            name="message_usages",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Usage metrics per message ID: {message_id: {promptTokens, completionTokens, ...}}",
            ),
        ),
    ]
