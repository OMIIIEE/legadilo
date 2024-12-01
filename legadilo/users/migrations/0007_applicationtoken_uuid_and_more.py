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

# Generated by Django 5.1.3 on 2024-12-01 14:11

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_applicationtoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicationtoken",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AlterField(
            model_name="applicationtoken",
            name="last_used_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When this token was last used to create an access token.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="applicationtoken",
            name="title",
            field=models.CharField(
                help_text="Give the token a nice name to identify its usage more easily.",
                max_length=255,
            ),
        ),
        migrations.AddConstraint(
            model_name="applicationtoken",
            constraint=models.UniqueConstraint(
                fields=("uuid",), name="users_applicationtoken_uuid_unique"
            ),
        ),
    ]
