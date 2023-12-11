from io import StringIO

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from legadilo.users.models import User


@pytest.mark.django_db()
class TestUserManager:
    def test_create_user(self):
        user = User.objects.create_user(
            email="john@example.com",
            password="something-r@nd0m!",
        )
        assert user.email == "john@example.com"
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password("something-r@nd0m!")
        assert user.username is None

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="something-r@nd0m!",
        )
        assert user.email == "admin@example.com"
        assert user.is_staff
        assert user.is_superuser
        assert user.username is None

    def test_create_superuser_username_ignored(self):
        user = User.objects.create_superuser(
            email="test@example.com",
            password="something-r@nd0m!",
        )
        assert user.username is None

    def test_create_user_invalid_email(self):
        with pytest.raises(ValidationError):
            User.objects.create_user(email="test", password="something-R@nd0m!")

    def test_email_case_insensitive_search(self):
        user = User.objects.create(email="Hacker@example.com")
        user2 = User.objects.get(email="hacker@example.com")
        assert user == user2

    def test_email_case_insensitive_unique(self):
        User.objects.create(email="Hacker@example.com")
        msg = 'duplicate key value violates unique constraint "users_user_email_key"'
        with pytest.raises(IntegrityError, match=msg):
            User.objects.create(email="hacker@example.com")


@pytest.mark.django_db()
def test_createsuperuser_command():
    """Ensure createsuperuser command works with our custom manager."""
    out = StringIO()
    command_result = call_command(
        "createsuperuser",
        "--email",
        "henry@example.com",
        interactive=False,
        stdout=out,
    )

    assert command_result is None
    assert out.getvalue() == "Superuser created successfully.\n"
    user = User.objects.get(email="henry@example.com")
    assert not user.has_usable_password()
