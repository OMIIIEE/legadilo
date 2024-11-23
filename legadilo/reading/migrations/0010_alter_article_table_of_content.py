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

# Generated by Django 5.1.3 on 2024-11-23 16:49

from django.db import migrations, models

import legadilo.utils.collections_utils
import legadilo.utils.validators


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0009_comment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="table_of_content",
            field=models.JSONField(
                blank=True,
                default=list,
                encoder=legadilo.utils.collections_utils.CustomJsonEncoder,
                help_text="The table of content of the article.",
                validators=[legadilo.utils.validators.table_of_content_validator],
            ),
        ),
    ]
