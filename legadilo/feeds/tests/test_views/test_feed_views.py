from http import HTTPStatus

import httpx
import pytest
from asgiref.sync import sync_to_async
from django.contrib.messages import DEFAULT_LEVELS, get_messages
from django.contrib.messages.storage.base import Message
from django.urls import reverse

from legadilo.feeds.models import Article, Feed
from legadilo.feeds.tests.factories import FeedFactory

from ..fixtures import SAMPLE_HTML_TEMPLATE, SAMPLE_RSS_FEED


@pytest.mark.django_db(transaction=True)
class TestCreateFeedView:
    def setup_method(self):
        self.url = reverse("feeds:create_feed")
        self.feed_url = "https://example.com/feeds/atom.xml"
        self.sample_payload = {"url": self.feed_url}
        self.page_url = "https://example.com"
        self.sample_page_payload = {"url": self.page_url}

    @pytest.mark.asyncio()
    async def test_not_logged_in(self, async_client):
        response = await async_client.get(self.url)

        assert response.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio()
    async def test_get_form(self, logged_in_async_client):
        response = await logged_in_async_client.get(self.url)

        assert response.status_code == HTTPStatus.OK

    @pytest.mark.asyncio()
    async def test_create_feed(self, logged_in_async_client, httpx_mock):
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = await logged_in_async_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Feed 'Sample Feed' added",
            )
        ]
        assert await Feed.objects.acount() == 1
        assert await Article.objects.acount() > 0

    @pytest.mark.asyncio()
    async def test_create_feed_from_feed_choices(self, logged_in_async_client, httpx_mock):
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = await logged_in_async_client.post(
            self.url,
            {
                "url": self.page_url,
                "proposed_feed_choices": f'[["{self.feed_url}", "Cat 1 feed"], '
                '["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]',
                "feed_choices": self.feed_url,
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["SUCCESS"],
                message="Feed 'Sample Feed' added",
            )
        ]
        assert await Feed.objects.acount() == 1

    @pytest.mark.asyncio()
    async def test_invalid_form(self, logged_in_async_client):
        response = await logged_in_async_client.post(self.url, {"url": "toto"})

        assert response.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.asyncio()
    async def test_fetch_failure(self, logged_in_async_client, httpx_mock):
        httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))

        response = await logged_in_async_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.NOT_ACCEPTABLE
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to fetch the feed. Please check that the URL you entered is correct, that the feed "
                "exists and is accessible.",
            )
        ]

    @pytest.mark.asyncio()
    async def test_duplicated_feed(self, user, logged_in_async_client, httpx_mock):
        await sync_to_async(FeedFactory)(feed_url=self.feed_url, user=user)
        httpx_mock.add_response(text=SAMPLE_RSS_FEED, url=self.feed_url)

        response = await logged_in_async_client.post(self.url, self.sample_payload)

        assert response.status_code == HTTPStatus.CONFLICT
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="You are already subscribed to this feed.",
            )
        ]

    @pytest.mark.asyncio()
    async def test_cannot_find_feed_url(self, logged_in_async_client, httpx_mock):
        httpx_mock.add_response(text=SAMPLE_HTML_TEMPLATE.replace("{{PLACEHOLDER}}", ""), url=self.page_url)

        response = await logged_in_async_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["ERROR"],
                message="Failed to find a feed URL on the supplied page.",
            )
        ]

    @pytest.mark.asyncio()
    async def test_multiple_feed_urls_found(self, logged_in_async_client, httpx_mock):
        httpx_mock.add_response(
            text=SAMPLE_HTML_TEMPLATE.replace(
                "{{PLACEHOLDER}}",
                """<link href="//www.jujens.eu/feeds/all.rss.xml" type="application/rss+xml" rel="alternate" title="Full feed">
                    <link href="//www.jujens.eu/feeds/cat1.atom.xml" type="application/atom+xml" rel="alternate" title="Cat 1 feed">""",  # noqa: E501
            ),
            url=self.page_url,
        )

        response = await logged_in_async_client.post(self.url, self.sample_page_payload)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        messages = list(get_messages(response.asgi_request))
        assert messages == [
            Message(
                level=DEFAULT_LEVELS["WARNING"],
                message="Multiple feeds were found at this location, please select the proper one.",
            )
        ]
        form = response.context_data["form"]
        assert form.fields["url"].widget.attrs["readonly"] == "true"
        assert form.initial == {
            "proposed_feed_choices": '[["https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"], '
            '["https://www.jujens.eu/feeds/all.rss.xml", "Full feed"]]'
        }
        assert form.fields["feed_choices"].required
        assert form.fields["feed_choices"].choices == [
            ("https://www.jujens.eu/feeds/cat1.atom.xml", "Cat 1 feed"),
            ("https://www.jujens.eu/feeds/all.rss.xml", "Full feed"),
        ]
