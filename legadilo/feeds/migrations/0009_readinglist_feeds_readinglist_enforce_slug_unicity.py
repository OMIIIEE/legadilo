# Generated by Django 5.0.3 on 2024-03-17 18:35

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0008_readinglist_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.UniqueConstraint(
                models.F("slug"), models.F("user"), name="feeds_readinglist_enforce_slug_unicity"
            ),
        ),
    ]
