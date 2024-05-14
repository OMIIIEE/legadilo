# Generated by Django 5.0.6 on 2024-05-09 09:32

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import legadilo.utils.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("feeds", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Article",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255)),
                ("summary", models.TextField()),
                ("content", models.TextField(blank=True)),
                (
                    "reading_time",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="How much time in minutes is needed to read this article. If not specified, it will be calculated automatically from content length. If we don't have content, we will use 0.",
                    ),
                ),
                (
                    "authors",
                    models.JSONField(
                        blank=True,
                        default=list,
                        validators=[
                            legadilo.utils.validators.JsonSchemaValidator({
                                "items": {"type": "string"},
                                "type": "array",
                            })
                        ],
                    ),
                ),
                (
                    "contributors",
                    models.JSONField(
                        blank=True,
                        default=list,
                        validators=[
                            legadilo.utils.validators.JsonSchemaValidator({
                                "items": {"type": "string"},
                                "type": "array",
                            })
                        ],
                    ),
                ),
                ("link", models.URLField(max_length=1024)),
                ("preview_picture_url", models.URLField(blank=True)),
                ("preview_picture_alt", models.TextField(blank=True)),
                (
                    "external_tags",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Tags of the article from the its source",
                        validators=[
                            legadilo.utils.validators.JsonSchemaValidator({
                                "items": {"type": "string"},
                                "type": "array",
                            })
                        ],
                    ),
                ),
                (
                    "external_article_id",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="The id of the article in the its source.",
                        max_length=512,
                    ),
                ),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                (
                    "is_read",
                    models.GeneratedField(
                        db_persist=True,
                        expression=models.Case(
                            models.When(models.Q(("read_at__isnull", True)), then=False),
                            default=True,
                        ),
                        output_field=models.BooleanField(),
                    ),
                ),
                ("opened_at", models.DateTimeField(blank=True, null=True)),
                (
                    "was_opened",
                    models.GeneratedField(
                        db_persist=True,
                        expression=models.Case(
                            models.When(models.Q(("opened_at__isnull", True)), then=False),
                            default=True,
                        ),
                        output_field=models.BooleanField(),
                    ),
                ),
                ("is_favorite", models.BooleanField(default=False)),
                ("is_for_later", models.BooleanField(default=False)),
                (
                    "initial_source_type",
                    models.CharField(
                        choices=[("FEED", "Feed"), ("MANUAL", "Manual")],
                        default="FEED",
                        max_length=100,
                    ),
                ),
                ("initial_source_title", models.CharField(max_length=255)),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True, help_text="The date of publication of the article.", null=True
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        blank=True, help_text="The last time the article was updated.", null=True
                    ),
                ),
                (
                    "obj_created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Technical date for the creation of the article in our database.",
                    ),
                ),
                (
                    "obj_updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Technical date for the last update of the article in our database.",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="articles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ArticleTag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "tagging_reason",
                    models.CharField(
                        choices=[
                            ("ADDED_MANUALLY", "Added manually"),
                            ("FROM_FEED", "From feed"),
                            ("DELETED", "Deleted"),
                        ],
                        default="ADDED_MANUALLY",
                        max_length=100,
                    ),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="article_tags",
                        to="reading.article",
                    ),
                ),
            ],
            options={
                "ordering": ["article_id", "tag__name", "tag_id"],
            },
        ),
        migrations.CreateModel(
            name="ReadingList",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, max_length=255)),
                ("is_default", models.BooleanField(default=False)),
                ("enable_reading_on_scroll", models.BooleanField(default=False)),
                (
                    "auto_refresh_interval",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Time in seconds after which to refresh reading lists automatically. It must be at least 5 minutes. Any values lower that that will disable the feature for this reading list.",
                    ),
                ),
                ("order", models.IntegerField(default=0)),
                (
                    "read_status",
                    models.CharField(
                        choices=[
                            ("ALL", "All"),
                            ("ONLY_UNREAD", "Only unread"),
                            ("ONLY_READ", "Only read"),
                        ],
                        default="ALL",
                        max_length=100,
                    ),
                ),
                (
                    "favorite_status",
                    models.CharField(
                        choices=[
                            ("ALL", "All"),
                            ("ONLY_FAVORITE", "Only favorite"),
                            ("ONLY_NON_FAVORITE", "Only non favorite"),
                        ],
                        default="ALL",
                        max_length=100,
                    ),
                ),
                (
                    "for_later_status",
                    models.CharField(
                        choices=[
                            ("ALL", "All"),
                            ("ONLY_FOR_LATER", "Only for later"),
                            ("ONLY_NOT_FOR_LATER", "Only for not later"),
                        ],
                        default="ALL",
                        max_length=100,
                    ),
                ),
                (
                    "articles_max_age_value",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Articles published before today minus this number will be excluded from the reading list.",
                    ),
                ),
                (
                    "articles_max_age_unit",
                    models.CharField(
                        choices=[
                            ("UNSET", "Unset"),
                            ("HOURS", "Hour(s)"),
                            ("DAYS", "Day(s)"),
                            ("WEEKS", "Week(s)"),
                            ("MONTHS", "Month(s)"),
                        ],
                        default="UNSET",
                        help_text="Define the unit for the previous number. Leave to unset to not use this feature.",
                        max_length=100,
                    ),
                ),
                (
                    "articles_reading_time",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Include only articles that take more or less than this time to read.",
                    ),
                ),
                (
                    "articles_reading_time_operator",
                    models.CharField(
                        choices=[
                            ("UNSET", "Unset"),
                            ("MORE_THAN", "More than than"),
                            ("LESS_THAN", "Less than than"),
                        ],
                        default="UNSET",
                        help_text="Whether the reading must be more or less that the supplied value.",
                        max_length=100,
                    ),
                ),
                (
                    "include_tag_operator",
                    models.CharField(
                        choices=[("ALL", "All"), ("ANY", "Any")],
                        default="ALL",
                        help_text="Defines whether the articles must have all or any of the tags to be included in the reading list.",
                        max_length=100,
                    ),
                ),
                (
                    "exclude_tag_operator",
                    models.CharField(
                        choices=[("ALL", "All"), ("ANY", "Any")],
                        default="ALL",
                        help_text="Defines whether the articles must have all or any of the tags to be excluded from the reading list.",
                        max_length=100,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_lists",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
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
                    "filter_type",
                    models.CharField(
                        choices=[("INCLUDE", "Include"), ("EXCLUDE", "Exclude")],
                        default="INCLUDE",
                        max_length=100,
                    ),
                ),
                (
                    "reading_list",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reading_list_tags",
                        to="reading.readinglist",
                    ),
                ),
            ],
            options={
                "ordering": ["tag__name", "tag_id"],
            },
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("slug", models.SlugField(blank=True)),
                (
                    "articles",
                    models.ManyToManyField(
                        related_name="tags", through="reading.ArticleTag", to="reading.article"
                    ),
                ),
                (
                    "feeds",
                    models.ManyToManyField(
                        related_name="tags", through="feeds.FeedTag", to="feeds.feed"
                    ),
                ),
                (
                    "reading_lists",
                    models.ManyToManyField(
                        related_name="tags",
                        through="reading.ReadingListTag",
                        to="reading.readinglist",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["name", "id"],
            },
        ),
        migrations.AddField(
            model_name="readinglisttag",
            name="tag",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reading_list_tags",
                to="reading.tag",
            ),
        ),
        migrations.AddField(
            model_name="articletag",
            name="tag",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="article_tags",
                to="reading.tag",
            ),
        ),
        migrations.AddConstraint(
            model_name="article",
            constraint=models.UniqueConstraint(
                models.F("user"), models.F("link"), name="reading_article_article_unique_for_user"
            ),
        ),
        migrations.AddConstraint(
            model_name="article",
            constraint=models.CheckConstraint(
                check=models.Q(("initial_source_type__in", ["FEED", "MANUAL"])),
                name="reading_article_initial_source_type_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.UniqueConstraint(
                models.F("is_default"),
                models.F("user"),
                condition=models.Q(("is_default", True)),
                name="reading_readinglist_enforce_one_default_reading_list",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.UniqueConstraint(
                models.F("slug"), models.F("user"), name="reading_readinglist_enforce_slug_unicity"
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q((
                    "articles_max_age_unit__in",
                    ["UNSET", "HOURS", "DAYS", "WEEKS", "MONTHS"],
                )),
                name="reading_readinglist_articles_max_age_unit_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q((
                    "articles_reading_time_operator__in",
                    ["UNSET", "MORE_THAN", "LESS_THAN"],
                )),
                name="reading_readinglist_articles_reading_time_operator_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q((
                    "favorite_status__in",
                    ["ALL", "ONLY_FAVORITE", "ONLY_NON_FAVORITE"],
                )),
                name="reading_readinglist_favorite_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q(("read_status__in", ["ALL", "ONLY_UNREAD", "ONLY_READ"])),
                name="reading_readinglist_read_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q((
                    "for_later_status__in",
                    ["ALL", "ONLY_FOR_LATER", "ONLY_NOT_FOR_LATER"],
                )),
                name="reading_readinglist_for_later_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q(("exclude_tag_operator__in", ["ALL", "ANY"])),
                name="reading_readinglist_exclude_tag_operator_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglist",
            constraint=models.CheckConstraint(
                check=models.Q(("include_tag_operator__in", ["ALL", "ANY"])),
                name="reading_readinglist_include_tag_operator_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="tag",
            constraint=models.UniqueConstraint(
                models.F("slug"), models.F("user_id"), name="reading_tag_tag_slug_unique_for_user"
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglisttag",
            constraint=models.UniqueConstraint(
                models.F("reading_list"),
                models.F("tag"),
                name="reading_readinglisttag_tagged_once_per_reading_list",
            ),
        ),
        migrations.AddConstraint(
            model_name="readinglisttag",
            constraint=models.CheckConstraint(
                check=models.Q(("filter_type__in", ["INCLUDE", "EXCLUDE"])),
                name="reading_readinglisttag_filter_type_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="articletag",
            constraint=models.CheckConstraint(
                check=models.Q(("tagging_reason__in", ["ADDED_MANUALLY", "FROM_FEED", "DELETED"])),
                name="reading_articletag_tagging_reason_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="articletag",
            constraint=models.UniqueConstraint(
                models.F("article"),
                models.F("tag"),
                name="reading_articletag_tagged_once_per_article",
            ),
        ),
    ]
