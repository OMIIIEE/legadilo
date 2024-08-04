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

from collections.abc import Iterable
from typing import Self

from django.db import models

from legadilo.utils.time_utils import utcnow

from .user import User


class NotificationQuerySet(models.QuerySet["Notification"]):
    def for_user(self, user: User) -> Self:
        return self.filter(user=user)

    def for_ids(self, ids: Iterable[int]) -> Self:
        return self.filter(id__in=ids)

    def only_unread(self):
        return self.filter(is_read=False)


class NotificationManager(models.Manager["Notification"]):
    _hints: dict

    def get_queryset(self) -> NotificationQuerySet:
        return NotificationQuerySet(model=self.model, using=self._db, hints=self._hints)

    def has_unread(self, user: User) -> bool:
        return self.get_queryset().for_user(user).only_unread().exists()

    def list_all_for_user(self, user: User) -> Iterable[Notification]:
        return self.get_queryset().for_user(user).all()

    def mark_as_read(self, user: User, notification_id: int | None = None) -> None:
        qs = self.get_queryset().for_user(user)
        if notification_id:
            qs = qs.for_ids([notification_id])

        qs.update(read_at=utcnow())

    def mark_as_unread(self, user: User, notification_id: int | None = None) -> None:
        qs = self.get_queryset().for_user(user)
        if notification_id:
            qs = qs.for_ids([notification_id])

        qs.update(read_at=None)


class Notification(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_read = models.GeneratedField(
        expression=models.Case(
            models.When(read_at__isnull=True, then=False),
            default=True,
        ),
        output_field=models.BooleanField(),
        db_persist=True,
    )
    user = models.ForeignKey("users.User", related_name="notifications", on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = NotificationManager()

    def __str__(self):
        return f"Notification(title={self.title}, is_read={self.is_read})"
