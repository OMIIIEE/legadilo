from http import HTTPStatus

import pytest
from django.urls import reverse

from legadilo.reading import constants
from legadilo.reading.models import Article
from legadilo.reading.tests.factories import ArticleFactory, ReadingListFactory


@pytest.mark.django_db()
class TestUpdateArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.article = ArticleFactory(is_read=False, user=user)
        self.mark_as_read_url = reverse(
            "reading:update_article",
            kwargs={
                "article_id": self.article.id,
                "update_action": constants.UpdateArticleActions.MARK_AS_READ.name,
            },
        )
        self.mark_as_favorite_url = reverse(
            "reading:update_article",
            kwargs={
                "article_id": self.article.id,
                "update_action": constants.UpdateArticleActions.MARK_AS_FAVORITE.name,
            },
        )

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.mark_as_read_url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_update_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.mark_as_read_url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_update_article_view(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_read_url, HTTP_REFERER="http://testserver/reading/"
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response.headers["Location"] == "http://testserver/reading/"
        self.article.refresh_from_db()
        assert self.article.is_read

    def test_update_article_view_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(9):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"displayed_reading_list_id": str(self.reading_list.id)},
                HTTP_REFERER="http://testserver/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.template_name == "reading/update_article_action.html"
        assert response.context["article"] == self.article
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_articles_of_reading_lists"] == {self.reading_list.slug: 1}
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": False,
            "auto_refresh_interval": 0,
            "articles_list_min_refresh_timeout": 300,
        }
        assert response["HX-Reswap"] == "outerHTML show:none"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        self.article.refresh_from_db()
        assert self.article.is_read

    def test_update_article_view_for_article_details_read_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_read_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://example.com/reading/",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        location_url = reverse("reading:default_reading_list")
        assert response["Location"] == f"{location_url}?full_reload=true"

    def test_update_article_view_for_article_details_favorite_status_action(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(5):
            response = logged_in_sync_client.post(
                self.mark_as_favorite_url,
                data={"for_article_details": "True"},
                HTTP_REFERER="http://testserver/reading/articles/1",
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == "http://testserver/reading/articles/1"


@pytest.mark.django_db()
class TestDeleteArticleView:
    @pytest.fixture(autouse=True)
    def _setup_data(self, user):
        self.reading_list = ReadingListFactory(user=user)
        self.reading_list_url = reverse(
            "reading:reading_list", kwargs={"reading_list_slug": self.reading_list.slug}
        )
        self.article = ArticleFactory(user=user)
        self.url = reverse(
            "reading:delete_article",
            kwargs={
                "article_id": self.article.id,
            },
        )

    def test_cannot_access_if_not_logged_in(self, client):
        response = client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert reverse("account_login") in response["Location"]

    def test_cannot_delete_article_as_other_user(self, logged_in_other_user_sync_client):
        response = logged_in_other_user_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.post(self.url)

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("reading:default_reading_list")
        assert Article.objects.count() == 0

    def test_delete_with_from_url(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.post(self.url, {"from_url": self.reading_list_url})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == self.reading_list_url
        assert Article.objects.count() == 0

    def test_delete_with_htmx(self, logged_in_sync_client, django_assert_num_queries):
        with django_assert_num_queries(10):
            response = logged_in_sync_client.post(
                self.url,
                {
                    "from_url": self.reading_list_url,
                    "displayed_reading_list_id": str(self.reading_list.id),
                },
                HTTP_HX_Request="true",
            )

        assert response.status_code == HTTPStatus.OK
        assert response.context["article"].pk is None
        assert response.context["reading_lists"] == [self.reading_list]
        assert response.context["count_articles_of_reading_lists"] == {self.reading_list.slug: 0}
        assert response.context["displayed_reading_list_id"] == self.reading_list.id
        assert response.context["js_cfg"] == {
            "is_reading_on_scroll_enabled": False,
            "auto_refresh_interval": 0,
            "articles_list_min_refresh_timeout": 300,
        }
        assert response["HX-Reswap"] == "outerHTML show:none swap:1s"
        assert response["HX-Retarget"] == f"#article-card-{self.article.id}"
        assert Article.objects.count() == 0

    def test_delete_article_for_article_details(
        self, logged_in_sync_client, django_assert_num_queries
    ):
        with django_assert_num_queries(6):
            response = logged_in_sync_client.post(
                self.url, {"from_url": self.reading_list_url, "for_article_details": "True"}
            )

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == f"{self.reading_list_url}?full_reload=true"
        assert Article.objects.count() == 0
