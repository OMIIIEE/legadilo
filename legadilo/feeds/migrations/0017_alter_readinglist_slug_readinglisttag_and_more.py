# Generated by Django 5.0.3 on 2024-03-30 11:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0016_articletag_feeds_articletag_tagged_once_per_article"),
    ]

    operations = [
        migrations.AlterField(
            model_name="readinglist",
            name="slug",
            field=models.SlugField(blank=True),
        ),
        migrations.CreateModel(
            name="ReadingListTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "reading_list",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_list_tags",
                        to="feeds.readinglist",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_lists",
                        to="feeds.tag",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="tag",
            name="reading_list_tags",
            field=models.ManyToManyField(
                related_name="tags", through="feeds.ReadingListTag", to="feeds.readinglist"
            ),
        ),
    ]
