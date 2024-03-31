# Generated by Django 5.0.3 on 2024-03-30 12:05

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0017_alter_readinglist_slug_readinglisttag_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="feedtag",
            constraint=models.UniqueConstraint(
                models.F("feed"), models.F("tag"), name="feeds_feedtag_tagged_once_per_feed"
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglisttag",
            constraint=models.UniqueConstraint(
                models.F("reading_list"),
                models.F("tag"),
                name="feeds_readinglisttag_tagged_once_per_reading_list",
            ),
        ),
    ]
