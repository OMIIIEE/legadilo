import pytest
from django.urls import reverse

from legadilo.feeds import constants
from legadilo.feeds.templatetags import favorite_action_url, read_action_url
from legadilo.feeds.tests.factories import ArticleFactory


@pytest.mark.parametrize(
    ("is_read", "update_action"),
    [
        pytest.param(
            True, constants.UpdateArticleActions.MARK_AS_UNREAD.name, id="article-is-read"
        ),
        pytest.param(
            False, constants.UpdateArticleActions.MARK_AS_READ.name, id="article-is-not-read"
        ),
    ],
)
def test_read_action_url(is_read, update_action):
    article = ArticleFactory.build(id=1, is_read=is_read)

    url = read_action_url(article)

    assert url == reverse(
        "feeds:update_article", kwargs={"article_id": 1, "update_action": update_action}
    )


@pytest.mark.parametrize(
    ("is_favorite", "update_action"),
    [
        pytest.param(
            True, constants.UpdateArticleActions.UNMARK_AS_FAVORITE.name, id="article-is-favorite"
        ),
        pytest.param(
            False,
            constants.UpdateArticleActions.MARK_AS_FAVORITE.name,
            id="article-is-not-favorite",
        ),
    ],
)
def test_favorite_action_url(is_favorite, update_action):
    article = ArticleFactory.build(id=1, is_favorite=is_favorite)

    url = favorite_action_url(article)

    assert url == reverse(
        "feeds:update_article", kwargs={"article_id": 1, "update_action": update_action}
    )
