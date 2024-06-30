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

import contextlib
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile


@contextlib.contextmanager
def ensure_file_on_disk(django_file: TemporaryUploadedFile | InMemoryUploadedFile):
    if hasattr(django_file, "temporary_file_path"):
        yield django_file.temporary_file_path()
        return

    with NamedTemporaryFile() as f:
        f.write(django_file.read())
        f.flush()
        yield f.name
