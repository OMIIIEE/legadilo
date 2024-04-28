from __future__ import annotations

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from legadilo.users.models import User

from .. import constants
from ..constants import SupportedFeedType
from ..utils.feed_parsing import FeedData
from .article import Article
from .feed_article import FeedArticle
from .feed_update import FeedUpdate
from .tag import FeedTag, Tag


class FeedQuerySet(models.QuerySet["Feed"]):
    def only_feeds_to_update(self, feed_ids: list[int] | None = None):
        feeds_to_update = self.filter(enabled=True)
        if feed_ids:
            feeds_to_update = feeds_to_update.filter(id__in=feed_ids)

        return feeds_to_update


class FeedManager(models.Manager["Feed"]):
    _hints: dict

    def get_queryset(self) -> FeedQuerySet:
        return FeedQuerySet(model=self.model, using=self._db, hints=self._hints)

    @transaction.atomic()
    def create_from_metadata(self, feed_metadata: FeedData, user: User, tags: list[Tag]) -> Feed:
        feed = self.create(
            feed_url=feed_metadata.feed_url,
            site_url=feed_metadata.site_url,
            title=feed_metadata.title,
            description=feed_metadata.description,
            feed_type=feed_metadata.feed_type,
            user=user,
        )
        FeedTag.objects.associate_feed_with_tags(feed, tags)
        self.update_feed(feed, feed_metadata)
        return feed

    @transaction.atomic()
    def update_feed(self, feed: Feed, feed_metadata: FeedData):
        created_articles = Article.objects.update_or_create_from_articles_list(
            feed.user,
            feed_metadata.articles,
            feed.tags.all(),
            source_type=constants.ArticleSourceType.FEED,
        )
        FeedUpdate.objects.create(
            status=constants.FeedUpdateStatus.SUCCESS,
            feed_etag=feed_metadata.etag,
            feed_last_modified=feed_metadata.last_modified,
            feed=feed,
        )
        FeedArticle.objects.bulk_create(
            [FeedArticle(article=article, feed=feed) for article in created_articles],
            ignore_conflicts=True,
        )

    @transaction.atomic()
    def log_error(self, feed: Feed, error_message: str):
        FeedUpdate.objects.create(
            status=constants.FeedUpdateStatus.FAILURE,
            error_message=error_message,
            feed=feed,
        )
        if FeedUpdate.objects.must_disable_feed(feed):
            feed.disable(_("We failed too many times to fetch the feed"))
            feed.save()

    def log_not_modified(self, feed: Feed):
        FeedUpdate.objects.create(
            status=constants.FeedUpdateStatus.NOT_MODIFIED,
            feed=feed,
        )


class Feed(models.Model):
    feed_url = models.URLField()
    site_url = models.URLField()
    enabled = models.BooleanField(default=True)
    disabled_reason = models.CharField(blank=True)

    # We store some feeds metadata, so we don't have to fetch when we need it.
    title = models.CharField()
    description = models.TextField(blank=True)
    feed_type = models.CharField(choices=SupportedFeedType)

    user = models.ForeignKey("users.User", related_name="feeds", on_delete=models.CASCADE)
    feed_articles = models.ManyToManyField(
        "feeds.Article",
        related_name="feeds",
        through="feeds.FeedArticle",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    objects = FeedManager()

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint("feed_url", "user", name="feeds_Feed_feed_url_unique"),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_feed_type_valid",
                check=models.Q(
                    feed_type__in=SupportedFeedType.names,
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_disabled_reason_empty_when_enabled",
                check=models.Q(
                    disabled_reason="",
                    enabled=True,
                )
                | models.Q(enabled=False),
            ),
        ]

    def __str__(self):
        return f"Feed(title={self.title}, feed_type={self.feed_type})"

    def disable(self, reason=""):
        self.disabled_reason = reason
        self.enabled = False
