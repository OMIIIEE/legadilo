from http import HTTPStatus

import httpx
import pytest
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.feeds.models import Article, Feed, FeedUpdate
from legadilo.feeds.tests.factories import FeedFactory, TagFactory

from ... import constants
from ..fixtures import SAMPLE_HTML_TEMPLATE, SAMPLE_RSS_FEED


@pytest.mark.django_db()
class TestCreateFeedView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.url = reverse("feeds:subscribe_to_feed")
        self.feed_url = "https://example.com/feeds/atom.xml"
        self.sample_payload = {"url": self.feed_url}
        self.existing_tag = TagFactory(user=user)
        self.sample_payload_with_tags = {
            "url": self.feed_url,
            "tags": [self.existing_tag.slug, "New"],
        }
        self.page_url = "https://example.com"
        self.sample_page_payload = {"url": self.page_url}

    def test_not_logged_in(self, client):
        response = client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_get_form(self, logged_in_sync_client):
        response = logged_in_sync_client.get(self.url)

        assert response.status_code == HTTPStatus.OK

    def test_subscribe_to_feed(self, logged_in_sync_client, httpx_mock, django_assert_num_queries):
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        with django_assert_num_queries(19):
            response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Feed 'Sample Feed' added",
            )
        ]
        assert Feed.objects.count() == 1
        feed = Feed.objects.get()
        assert feed.tags.count() == 0
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert article.tags.count() == 0
        assert FeedUpdate.objects.count() == 1

    def test_subscribe_to_feed_with_tags(
        self, logged_in_sync_client, httpx_mock, django_assert_num_queries
    ):
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        with django_assert_num_queries(23):
            response = logged_in_sync_client.post(self.url, self.sample_payload_with_tags)

        assert response.status_code == HTTPStatus.CREATED, response.context["form"].errors
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Feed 'Sample Feed' added",
            )
        ]
        assert Feed.objects.count() == 1
        feed = Feed.objects.get()
        assert list(feed.tags.values_list("slug", flat=True)) == ["new", self.existing_tag.slug]
        assert Article.objects.count() > 0
        article = Article.objects.first()
        assert article is not None
        assert list(article.article_tags.values_list("tag__slug", "tagging_reason")) == [
            ("new", constants.TaggingReason.FROM_FEED),
            (self.existing_tag.slug, constants.TaggingReason.FROM_FEED),
        ]
        assert FeedUpdate.objects.count() == 1

    def test_subscribe_to_feed_from_feed_choices(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = logged_in_sync_client.post(
            self.url,
            {
                "url": self.page_url,
                "proposed_feed_choices": f'[["{self.feed_url}", "Cat 1 feed"], '
                '["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]',
                "feed_choices": self.feed_url,
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Feed 'Sample Feed' added",
            )
        ]
        assert Feed.objects.count() == 1
        assert FeedUpdate.objects.count() == 1

    def test_invalid_form(self, logged_in_sync_client):
        response = logged_in_sync_client.post(self.url, {"url": "toto"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_fetch_failure(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to fetch the feed. Please check that the URL you entered is "
                "correct, that the feed exists and is accessible.",
            )
        ]

    def test_fetched_file_too_big(self, logged_in_sync_client, httpx_mock, mocker):
        mocker.patch("legadilo.feeds.utils.feed_parsing.sys.getsizeof", return_value=2048 * 1024)
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="The feed file is too big, we won't parse it. "
                "Try to find a more lightweight feed.",
            )
        ]

    def test_fetched_file_invalid_feed(self, logged_in_sync_client, httpx_mock, mocker):
        httpx_mock.add_response(
            text=SAMPLE_RSS_FEED.replace(
                "<link>http://example.org/entry/3</link>", "<link>Just trash</link>"
            ),
            url=self.feed_url,
        )

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="We failed to parse the feed you supplied. Please check it is supported "
                "and matches the sync of a feed file.",
            )
        ]

    def test_duplicated_feed(self, user, logged_in_sync_client, httpx_mock):
        FeedFactory(feed_url=self.feed_url, user=user)
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = logged_in_sync_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CONFLICT
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="You are already subscribed to this feed.",
            )
        ]

    def test_cannot_find_feed_url(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(
            text=SAMPLE_HTML_TEMPLATE.replace("{{PLACEHOLDER}}", ""), url=self.page_url
        )

        response = logged_in_sync_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to find a feed URL on the supplied page.",
            )
        ]

    def test_multiple_feed_urls_found(self, logged_in_sync_client, httpx_mock):
        httpx_mock.add_response(
            text=SAMPLE_HTML_TEMPLATE.replace(
                "{{PLACEHOLDER}}",
                """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
            ),
            url=self.page_url,
        )

        response = logged_in_sync_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.wsgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="Multiple feeds were found at this location, please select the proper one.",
            )
        ]
        form = response.context_data["form"]
        assert form.fields["url"].widget.attrs["readonly"] == "true"
        assert form.initial == {
            "proposed_feed_choices": '[["https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"],'
            ' ["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]'
        }
        assert form.fields["feed_choices"].required
        assert form.fields["feed_choices"].choices == [
            ("https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"),
            ("https://www.jujens.eu/feeds/all.rss.xml", "Full feed"),
        ]
