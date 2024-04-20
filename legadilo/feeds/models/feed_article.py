from django.db import models
from django_stubs_ext.db.models import TypedModelMeta


class FeedArticle(models.Model):
    feed = models.ForeignKey("feeds.Feed", related_name="articles", on_delete=models.CASCADE)
    article = models.ForeignKey(
        "feeds.Article", related_name="feed_articles", on_delete=models.CASCADE
    )

    class Meta(TypedModelMeta):
        constraints = [
            models.UniqueConstraint(
                "feed", "article", name="%(app_label)s_%(class)s_article_linked_once_per_feed"
            ),
        ]

    def __str__(self):
        return f"FeedArticle(feed={self.feed}, article={self.article})"
