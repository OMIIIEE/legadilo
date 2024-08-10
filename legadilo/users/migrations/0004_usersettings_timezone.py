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

# Generated by Django 5.1 on 2024-08-10 10:30

import django.db.models.deletion
from django.db import migrations, models


def set_default_tz(apps, schema_editor):
    UserSettings = apps.get_model("users", "UserSettings")
    Timezone = apps.get_model("core", "Timezone")
    utc_tz = Timezone.objects.get(name="UTC")

    UserSettings.objects.filter(timezone__isnull=True).update(timezone=utc_tz)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_initial"),
        ("users", "0003_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersettings",
            name="timezone",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_settings",
                to="core.timezone",
            ),
        ),
        migrations.RunPython(set_default_tz, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usersettings",
            name="timezone",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_settings",
                to="core.timezone",
            ),
        ),
    ]
