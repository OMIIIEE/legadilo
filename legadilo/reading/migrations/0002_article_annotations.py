# Generated by Django 5.0.6 on 2024-05-14 20:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="annotations",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Annotations made to the article. Currently only used for data imports to prevent data loss.",
            ),
        ),
    ]
