# Generated by Django 5.0.4 on 2024-04-18 18:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feeds", "0026_readinglist_articles_reading_time_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="readinglist",
            name="enable_reading_on_scroll",
            field=models.BooleanField(default=False),
        ),
    ]
