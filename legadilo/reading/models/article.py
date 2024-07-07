# Legadilo
# Copyright (C) 2023-2024 by Legadilo contributors.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

import json
import logging
import math
from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal, Self, assert_never, cast

from dateutil.relativedelta import relativedelta
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models, transaction
from django.db.models.functions import Cast, Coalesce
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from legadilo.reading import constants
from legadilo.reading.models.tag import ArticleTag
from legadilo.utils.collections import max_or_none, min_or_none
from legadilo.utils.security import full_sanitize
from legadilo.utils.text import get_nb_words_from_html
from legadilo.utils.time import utcnow
from legadilo.utils.validators import language_code_validator, list_of_strings_json_schema_validator

from .article_fetch_error import ArticleFetchError

if TYPE_CHECKING:
    from django_stubs_ext.db.models import TypedModelMeta

    from legadilo.reading.models.reading_list import ReadingList
    from legadilo.reading.models.tag import Tag
    from legadilo.reading.services.article_fetching import ArticleData
    from legadilo.users.models import User
else:
    TypedModelMeta = object

logger = logging.getLogger(__name__)


def _build_filters_from_reading_list(reading_list: ReadingList) -> models.Q:  # noqa: C901 too complex
    filters = models.Q()

    if reading_list.read_status == constants.ReadStatus.ONLY_READ:
        filters &= models.Q(is_read=True)
    elif reading_list.read_status == constants.ReadStatus.ONLY_UNREAD:
        filters &= models.Q(is_read=False)

    if reading_list.favorite_status == constants.FavoriteStatus.ONLY_FAVORITE:
        filters &= models.Q(is_favorite=True)
    elif reading_list.favorite_status == constants.FavoriteStatus.ONLY_NON_FAVORITE:
        filters &= models.Q(is_favorite=False)

    if reading_list.for_later_status == constants.ForLaterStatus.ONLY_FOR_LATER:
        filters &= models.Q(is_for_later=True)
    elif reading_list.for_later_status == constants.ForLaterStatus.ONLY_NOT_FOR_LATER:
        filters &= models.Q(is_for_later=False)

    if reading_list.articles_max_age_unit != constants.ArticlesMaxAgeUnit.UNSET:
        filters &= models.Q(
            published_at__gt=utcnow()
            - relativedelta(**{  # type: ignore[arg-type]
                reading_list.articles_max_age_unit.lower(): reading_list.articles_max_age_value
            })
        )

    articles_reading_time_operator = cast(
        constants.ArticlesReadingTimeOperator, reading_list.articles_reading_time_operator
    )
    match articles_reading_time_operator:
        case constants.ArticlesReadingTimeOperator.UNSET:
            pass
        case constants.ArticlesReadingTimeOperator.MORE_THAN:
            filters &= models.Q(reading_time__gte=reading_list.articles_reading_time)
        case constants.ArticlesReadingTimeOperator.LESS_THAN:
            filters &= models.Q(reading_time__lte=reading_list.articles_reading_time)
        case _:
            assert_never(reading_list.articles_reading_time_operator)

    filters &= _get_tags_filters(reading_list)

    return filters


def _get_tags_filters(reading_list: ReadingList) -> models.Q:
    filters = models.Q()
    tags_to_include = []
    tags_to_exclude = []
    for reading_list_tag in reading_list.reading_list_tags.all():
        filter_type = cast(constants.ReadingListTagFilterType, reading_list_tag.filter_type)
        match filter_type:
            case constants.ReadingListTagFilterType.INCLUDE:
                tags_to_include.append(reading_list_tag.tag_id)
            case constants.ReadingListTagFilterType.EXCLUDE:
                tags_to_exclude.append(reading_list_tag.tag_id)
            case _:
                assert_never(reading_list_tag.filter_type)

    if tags_to_include:
        operator = _get_reading_list_tags_sql_operator(
            constants.ReadingListTagOperator(reading_list.include_tag_operator)
        )
        filters &= models.Q(**{f"alias_tag_ids_for_article__{operator}": tags_to_include})
    if tags_to_exclude:
        operator = _get_reading_list_tags_sql_operator(
            constants.ReadingListTagOperator(reading_list.exclude_tag_operator)
        )
        filters &= ~models.Q(**{f"alias_tag_ids_for_article__{operator}": tags_to_exclude})
    return filters


def _get_reading_list_tags_sql_operator(
    reading_list_operator: constants.ReadingListTagOperator,
) -> Literal["contains", "overlap"]:
    match reading_list_operator:
        case constants.ReadingListTagOperator.ALL:
            return "contains"
        case constants.ReadingListTagOperator.ANY:
            return "overlap"


def _build_prefetch_article_tags():
    return models.Prefetch(
        "article_tags",
        queryset=ArticleTag.objects.get_queryset().for_reading_list(),
        to_attr="tags_to_display",
    )


class ArticleQuerySet(models.QuerySet["Article"]):
    def for_user(self, user: User):
        return self.filter(user=user)

    def only_unread(self):
        return self.filter(is_read=False)

    def for_current_tag_filtering(self) -> Self:
        return self.alias(
            alias_tag_ids_for_article=ArrayAgg(
                "article_tags__tag_id",
                filter=~models.Q(article_tags__tagging_reason=constants.TaggingReason.DELETED),
                default=models.Value([]),
            ),
        )

    def for_feed_links(self) -> Self:
        return self.alias(
            feed_ids=ArrayAgg("feeds__id", order="feeds__id"),
            feed_slugs=ArrayAgg("feeds__slug", ordering="feeds__id"),
            feed_open_original_link_by_default=ArrayAgg(
                "feeds__open_original_link_by_default", ordering="feeds__id"
            ),
        ).annotate(
            annot_feed_id=models.F("feed_ids__0"),
            annot_feed_slug=models.F("feed_slugs__0"),
            annot_open_original_by_default=models.F("feed_open_original_link_by_default__0"),
        )

    def for_reading_list(self, reading_list: ReadingList) -> Self:
        return (
            self.for_user(reading_list.user)
            .for_current_tag_filtering()
            .for_feed_links()
            .filter(_build_filters_from_reading_list(reading_list))
            .prefetch_related(_build_prefetch_article_tags())
            .default_order_by(reading_list.order_direction)
        )

    def for_tag(self, tag: Tag) -> Self:
        return (
            self.for_current_tag_filtering()
            .for_feed_links()
            .filter(alias_tag_ids_for_article__contains=[tag.id])
            .prefetch_related(_build_prefetch_article_tags())
            .default_order_by()
        )

    def for_external_tag(self, user: User, tag: str) -> Self:
        return (
            self.for_user(user)
            .for_feed_links()
            .filter(external_tags__icontains=tag)
            .prefetch_related(_build_prefetch_article_tags())
            .default_order_by()
        )

    def for_feed(self) -> Self:
        return (
            self.prefetch_related(_build_prefetch_article_tags())
            .for_feed_links()
            .default_order_by()
        )

    def for_details(self) -> Self:
        return self.prefetch_related(_build_prefetch_article_tags()).for_feed_links()

    def for_export(self, user: User) -> Self:
        return (
            self.for_user(user)
            .alias(
                feed_category_ids=ArrayAgg("feeds__category__id", order="feeds__id"),
                feed_category_titles=ArrayAgg("feeds__category__title", order="feeds__id"),
                feed_ids=ArrayAgg("feeds__id", order="feeds__id"),
                feed_titles=ArrayAgg("feeds__title", order="feeds__id"),
                feed_urls=ArrayAgg("feeds__feed_url", order="feeds__id"),
                feed_site_urls=ArrayAgg("feeds__site_url", order="feeds__id"),
            )
            .annotate(
                annot_feed_category_id=Coalesce(
                    Cast(models.F("feed_category_ids__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
                annot_feed_cateory_title=Coalesce(
                    Cast(models.F("feed_category_titles__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
                annot_feed_id=Coalesce(
                    Cast(models.F("feed_ids__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
                annot_feed_title=Coalesce(
                    Cast(models.F("feed_titles__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
                annot_feed_url=Coalesce(
                    Cast(models.F("feed_urls__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
                annot_feed_site_url=Coalesce(
                    Cast(models.F("feed_site_urls__0"), output_field=models.TextField()),
                    models.Value(""),
                    output_field=models.TextField(),
                ),
            )
            .prefetch_related(_build_prefetch_article_tags())
            .order_by("id")
        )

    def update_articles_from_action(self, action: constants.UpdateArticleActions):  # noqa: PLR0911 Too many return statements
        # Remove order bys to allow UPDATE to work. Otherwise, Django will fail because it can't
        # resolve the alias_date_field_order field.
        update_qs = self.order_by()

        match action:
            case constants.UpdateArticleActions.DO_NOTHING:
                return 0
            case constants.UpdateArticleActions.MARK_AS_READ:
                return update_qs.filter(read_at__isnull=True).update(read_at=utcnow())
            case constants.UpdateArticleActions.MARK_AS_UNREAD:
                return update_qs.update(read_at=None)
            case constants.UpdateArticleActions.MARK_AS_FAVORITE:
                return update_qs.update(is_favorite=True)
            case constants.UpdateArticleActions.UNMARK_AS_FAVORITE:
                return update_qs.update(is_favorite=False)
            case constants.UpdateArticleActions.MARK_AS_FOR_LATER:
                return update_qs.update(is_for_later=True)
            case constants.UpdateArticleActions.UNMARK_AS_FOR_LATER:
                return update_qs.update(is_for_later=False)
            case constants.UpdateArticleActions.MARK_AS_OPENED:
                return update_qs.filter(opened_at__isnull=True).update(opened_at=utcnow())
            case _:
                assert_never(action)

    def default_order_by(
        self,
        order_direction: constants.ReadingListOrderDirection = constants.ReadingListOrderDirection.DESC,  # noqa: E501
    ) -> Self:
        order_expression = models.F("alias_date_field_order")
        match order_direction:
            case constants.ReadingListOrderDirection.ASC:
                order = order_expression.asc(nulls_last=True)
            case constants.ReadingListOrderDirection.DESC:
                order = order_expression.desc(nulls_last=True)
            case _:
                assert_never(order_direction)

        return self.alias(
            alias_date_field_order=Coalesce(models.F("updated_at"), models.F("published_at"))
        ).order_by(order)


class ArticleManager(models.Manager["Article"]):
    _hints: dict

    def get_queryset(self) -> ArticleQuerySet:
        return ArticleQuerySet(model=self.model, using=self._db, hints=self._hints)

    @transaction.atomic()
    def update_or_create_from_articles_list(
        self,
        user: User,
        articles_data: list[ArticleData],
        tags: Iterable[Tag],
        *,
        source_type: constants.ArticleSourceType,
        force_update: bool = False,
    ) -> list[Article]:
        if len(articles_data) == 0:
            return []

        existing_links_to_articles = {
            article.link: article
            for article in self.get_queryset()
            .filter(user=user, link__in=[article_data.link for article_data in articles_data])
            .select_related("user", "user__settings")
        }
        articles_to_create = []
        articles_to_update = []
        seen_links = set()
        for article_data in articles_data:
            if article_data.link in seen_links:
                continue

            seen_links.add(article_data.link)
            if article_data.link in existing_links_to_articles:
                article_to_update = existing_links_to_articles[article_data.link]
                was_updated = article_to_update.update_article_from_data(
                    article_data, force_update=force_update
                )
                if source_type == constants.ArticleSourceType.MANUAL:
                    if article_to_update.main_source_type == constants.ArticleSourceType.FEED:
                        # We force the source type to manual if we manually add it so prevent any
                        # cleanup later one.
                        article_to_update.main_source_type = constants.ArticleSourceType.MANUAL
                    article_to_update.read_at = None
                    was_updated = True
                    article_to_update.obj_updated_at = utcnow()
                if was_updated:
                    articles_to_update.append(article_to_update)
            else:
                articles_to_create.append(
                    self.model(
                        user=user,
                        external_article_id=article_data.external_article_id,
                        title=article_data.title,
                        slug=slugify(article_data.title),
                        summary=article_data.summary,
                        content=article_data.content,
                        reading_time=get_nb_words_from_html(article_data.content)
                        // user.settings.default_reading_time,
                        authors=article_data.authors,
                        contributors=article_data.contributors,
                        external_tags=article_data.tags,
                        link=article_data.link,
                        preview_picture_url=article_data.preview_picture_url,
                        preview_picture_alt=article_data.preview_picture_alt,
                        published_at=article_data.published_at,
                        updated_at=article_data.updated_at,
                        main_source_type=source_type,
                        main_source_title=article_data.source_title,
                        language=article_data.language,
                        annotations=article_data.annotations,
                        read_at=article_data.read_at,
                        is_favorite=article_data.is_favorite,
                    )
                )

        self.bulk_create(articles_to_create, unique_fields=["user", "link"])

        self.bulk_update(
            articles_to_update,
            fields=[
                "title",
                "slug",
                "summary",
                "content",
                "reading_time",
                "authors",
                "preview_picture_url",
                "preview_picture_alt",
                "contributors",
                "external_tags",
                "updated_at",
                "read_at",
                "main_source_type",
                "obj_updated_at",
            ],
        )

        all_articles = [*articles_to_create, *existing_links_to_articles.values()]
        ArticleTag.objects.associate_articles_with_tags(
            all_articles,
            tags,
            tagging_reason=constants.TaggingReason.FROM_FEED
            if source_type == constants.ArticleSourceType.FEED
            else constants.TaggingReason.ADDED_MANUALLY,
        )

        return all_articles

    @transaction.atomic()
    def create_invalid_article(
        self,
        user: User,
        article_link: str,
        tags: Iterable[Tag],
        *,
        error_message="",
        technical_debug_data: dict | None = None,
    ) -> tuple[Article, bool]:
        try:
            article = self.get(user=user, link=article_link)
            created = False
        except self.model.DoesNotExist:
            created = True
            article = Article.objects.create(
                user=user, link=article_link, title=full_sanitize(article_link)
            )
            ArticleTag.objects.associate_articles_with_tags(
                [article], tags, tagging_reason=constants.TaggingReason.ADDED_MANUALLY
            )

        ArticleFetchError.objects.create(
            article=article, message=error_message, technical_debug_data=technical_debug_data
        )
        return article, created

    def get_articles_of_reading_list(self, reading_list: ReadingList) -> ArticleQuerySet:
        return self.get_queryset().for_reading_list(reading_list)

    def count_unread_articles_of_reading_lists(
        self, user: User, reading_lists: list[ReadingList]
    ) -> dict[str, int]:
        aggregation = {
            reading_list.slug: models.Count(
                "id",
                filter=_build_filters_from_reading_list(reading_list),
            )
            for reading_list in reading_lists
        }
        # We only count unread articles in the reading list. Not all article. I think it's more
        # relevant.
        return (
            self.get_queryset()
            .for_user(user)
            .only_unread()
            .for_current_tag_filtering()
            .aggregate(**aggregation)
        )

    def get_articles_of_tag(self, tag: Tag) -> ArticleQuerySet:
        return self.get_queryset().for_tag(tag)

    def get_articles_with_external_tag(self, user: User, tag: str) -> ArticleQuerySet:
        return self.get_queryset().for_external_tag(user, tag)

    async def export(self, user: User):
        articles_qs = self.get_queryset().for_export(user)
        nb_pages = math.ceil(await articles_qs.acount() / constants.MAX_EXPORT_ARTICLES_PER_PAGE)
        for page in range(nb_pages):
            articles = []
            start_index = page * constants.MAX_EXPORT_ARTICLES_PER_PAGE
            end_index = (
                page * constants.MAX_EXPORT_ARTICLES_PER_PAGE
                + constants.MAX_EXPORT_ARTICLES_PER_PAGE
            )
            async for article in articles_qs[start_index:end_index]:
                articles.append({
                    "category_id": article.annot_feed_category_id,  # type: ignore[attr-defined]
                    "category_title": article.annot_feed_cateory_title,  # type: ignore[attr-defined]
                    "feed_id": article.annot_feed_id,  # type: ignore[attr-defined]
                    "feed_title": article.annot_feed_title,  # type: ignore[attr-defined]
                    "feed_url": article.annot_feed_url,  # type: ignore[attr-defined]
                    "feed_site_url": article.annot_feed_site_url,  # type: ignore[attr-defined]
                    "article_id": article.id,
                    "article_title": article.title,
                    "article_link": article.link,
                    "article_content": article.content,
                    "article_date_published": article.published_at.isoformat()
                    if article.published_at
                    else "",
                    "article_date_updated": article.updated_at.isoformat()
                    if article.updated_at
                    else "",
                    "article_authors": json.dumps(article.authors) if article.authors else "",
                    "article_tags": json.dumps([tag.title for tag in article.tags_to_display])  # type: ignore[attr-defined]
                    if article.tags_to_display  # type: ignore[attr-defined]
                    else "",
                    "article_read_at": article.read_at.isoformat() if article.read_at else "",
                    "article_is_favorite": article.is_favorite,
                    "article_lang": article.language,
                })

            yield articles


class Article(models.Model):
    title = models.CharField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH)
    slug = models.SlugField(max_length=constants.ARTICLE_TITLE_MAX_LENGTH)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    reading_time = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "How much time in minutes is needed to read this article. If not specified, "
            "it will be calculated automatically from content length. If we don't have content, "
            "we will use 0."
        ),
    )
    authors = models.JSONField(
        validators=[list_of_strings_json_schema_validator], blank=True, default=list
    )
    contributors = models.JSONField(
        validators=[list_of_strings_json_schema_validator], blank=True, default=list
    )
    link = models.URLField(max_length=1_024)
    preview_picture_url = models.URLField(blank=True, max_length=1_024)
    preview_picture_alt = models.TextField(blank=True)
    external_tags = models.JSONField(
        validators=[list_of_strings_json_schema_validator],
        blank=True,
        default=list,
        help_text=_("Tags of the article from the its source"),
    )
    external_article_id = models.CharField(
        default="",
        blank=True,
        max_length=constants.EXTERNAL_ARTICLE_ID_MAX_LENGTH,
        help_text=_("The id of the article in the its source."),
    )
    annotations = models.JSONField(
        blank=True,
        default=list,
        help_text=_(
            "Annotations made to the article. Currently only used for data imports to prevent data "
            "loss."
        ),
    )
    language = models.CharField(
        default="",
        blank=True,
        max_length=constants.LANGUAGE_CODE_MAX_LENGTH,
        help_text=_("The language code for this article"),
        validators=[language_code_validator],
    )

    read_at = models.DateTimeField(null=True, blank=True)
    is_read = models.GeneratedField(
        expression=models.Case(
            models.When(models.Q(read_at__isnull=True), then=False),
            default=True,
        ),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    was_opened = models.GeneratedField(
        expression=models.Case(
            models.When(models.Q(opened_at__isnull=True), then=False),
            default=True,
        ),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    is_favorite = models.BooleanField(default=False)
    is_for_later = models.BooleanField(default=False)

    user = models.ForeignKey("users.User", related_name="articles", on_delete=models.CASCADE)

    main_source_type = models.CharField(
        default=constants.ArticleSourceType.FEED,
        choices=constants.ArticleSourceType.choices,
        max_length=100,
    )
    main_source_title = models.CharField(max_length=constants.ARTICLE_SOURCE_TITLE_MAX_LENGTH)

    published_at = models.DateTimeField(
        null=True, blank=True, help_text=_("The date of publication of the article.")
    )
    updated_at = models.DateTimeField(
        null=True, blank=True, help_text=_("The last time the article was updated.")
    )
    obj_created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Technical date for the creation of the article in our database."),
    )
    obj_updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Technical date for the last update of the article in our database."),
    )

    objects = ArticleManager()

    class Meta(TypedModelMeta):
        ordering = ["-updated_at", "-published_at", "id"]
        constraints = [
            models.UniqueConstraint(
                "user", "link", name="%(app_label)s_%(class)s_article_unique_for_user"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_main_source_type_valid",
                check=models.Q(
                    main_source_type__in=constants.ArticleSourceType.names,
                ),
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "is_read", "is_favorite", "is_for_later"],
            ),
        ]

    def __str__(self):
        return (
            f"Article(title={self.title}, main_source_type={self.main_source_type}, "
            f"main_source_title={self.main_source_title}, published_at={self.published_at})"
        )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        return super().save(*args, **kwargs)

    def update_article_from_data(
        self, article_data: ArticleData, *, force_update: bool = False
    ) -> bool:
        is_more_recent = (
            self.updated_at is None
            or article_data.updated_at is None
            or article_data.updated_at > self.updated_at
        )
        has_content_unlike_saved = bool(article_data.content) and not bool(self.content)
        if not is_more_recent and not has_content_unlike_saved and not force_update:
            return False

        if is_more_recent or force_update:
            self.title = article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH] or self.title
            self.slug = (
                slugify(article_data.title[: constants.ARTICLE_TITLE_MAX_LENGTH]) or self.slug
            )
            self.summary = article_data.summary or self.summary
            self.content = article_data.content or self.content
            self.reading_time = (
                get_nb_words_from_html(self.content) // self.user.settings.default_reading_time
            ) or self.reading_time
            self.preview_picture_url = article_data.preview_picture_url or self.preview_picture_alt
            self.preview_picture_alt = article_data.preview_picture_alt or self.preview_picture_alt
            self.authors = list(dict.fromkeys(self.authors + article_data.authors))
            self.contributors = list(dict.fromkeys(self.contributors + article_data.contributors))
            self.external_tags = list(dict.fromkeys(self.external_tags + article_data.tags))
            self.updated_at = max_or_none([article_data.updated_at, self.updated_at])
            self.published_at = min_or_none([article_data.published_at, self.published_at])
        elif has_content_unlike_saved:
            self.content = article_data.content

        self.article_to_update = utcnow()

        return True

    def update_from_details(self, *, title: str, reading_time: int):
        self.title = title
        self.reading_time = reading_time

    @property
    def is_from_feed(self):
        return self.main_source_type == constants.ArticleSourceType.FEED
