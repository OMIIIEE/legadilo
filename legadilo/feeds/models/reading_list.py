from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from legadilo.feeds import constants
from legadilo.users.models import User


class ReadingListManager(models.Manager["ReadingList"]):
    @transaction.atomic()
    def create_default_lists(self, user: User):
        self.create(
            name=str(_("All articles")),
            slug=slugify(str(_("All articles"))),
            order=0,
            user=user,
        )
        self.create(
            name=str(_("Unread")),
            slug=slugify(str(_("Unread"))),
            is_default=True,
            read_status=constants.ReadStatus.ONLY_UNREAD,
            order=10,
            user=user,
        )
        self.create(
            name=str(_("Recent")),
            slug=slugify(str(_("Recent"))),
            articles_max_age_value=2,
            articles_max_age_unit=constants.ArticlesMaxAgeUnit.DAYS,
            order=20,
            user=user,
        )
        self.create(
            name=str(_("Favorite")),
            slug=slugify(str(_("Favorite"))),
            favorite_status=constants.FavoriteStatus.ONLY_FAVORITE,
            order=30,
            user=user,
        )
        self.create(
            name=str(_("Archive")),
            slug=slugify(str(_("Archive"))),
            read_status=constants.ReadStatus.ONLY_READ,
            order=40,
            user=user,
        )

    def get_reading_list(self, user: User, reading_list_slug: str | None) -> ReadingList:
        qs = self.get_queryset().select_related("user")
        if reading_list_slug is None:
            return qs.get(user=user, is_default=True)

        return qs.get(user=user, slug=reading_list_slug)

    def get_all_for_user(self, user: User) -> list[ReadingList]:
        return list(self.filter(user=user))


class ReadingList(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    is_default = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    read_status = models.CharField(
        choices=constants.ReadStatus.choices, default=constants.ReadStatus.ALL
    )
    favorite_status = models.CharField(
        choices=constants.FavoriteStatus.choices, default=constants.FavoriteStatus.ALL
    )
    articles_max_age_value = models.PositiveIntegerField(
        default=0,
        help_text=_(
            "Articles published before today minus this number will be excluded from the reading list."  # noqa: E501
        ),
    )
    articles_max_age_unit = models.CharField(
        choices=constants.ArticlesMaxAgeUnit.choices,
        default=constants.ArticlesMaxAgeUnit.UNSET,
        help_text=_(
            "Define the unit for the previous number. Leave to unset to not use this feature."
        ),
    )

    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="reading_lists")

    objects = ReadingListManager()

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                "is_default",
                "user",
                name="%(app_label)s_%(class)s_enforce_one_default_reading_list",
                condition=models.Q(is_default=True),
            ),
            models.UniqueConstraint(
                "slug", "user", name="%(app_label)s_%(class)s_enforce_slug_unicity"
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_articles_max_age_unit_valid",
                check=models.Q(
                    articles_max_age_unit__in=["UNSET", "HOURS", "DAYS", "WEEKS", "MONTHS"]
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_favorite_status_valid",
                check=models.Q(favorite_status__in=["ALL", "ONLY_FAVORITE", "ONLY_NON_FAVORITE"]),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_read_status_valid",
                check=models.Q(read_status__in=["ALL", "ONLY_UNREAD", "ONLY_READ"]),
            ),
        ]

    def __str__(self):
        return f"ReadingList(id={self.id}, name={self.name}, user={self.user}, order={self.order})"

    def delete(self, *args, **kwargs):
        if self.is_default:
            raise ValidationError("Cannot delete default list")

        return super().delete(*args, **kwargs)
