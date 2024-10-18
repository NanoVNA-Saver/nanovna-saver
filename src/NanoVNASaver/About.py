#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020ff NanoVNA-Saver Authors
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

from setuptools_scm import get_version

try:
    version = get_version(root="../..", relative_to=__file__)
except LookupError:
    from NanoVNASaver._version import version

INFO_URL = "https://github.com/NanoVNA-Saver/nanovna-saver"
INFO = f"""NanoVNASaver {version}

Copyright (C) 2019, 2020 Rune B. Broberg
Copyright (C) 2020ff NanoVNA-Saver Authors

This program comes with ABSOLUTELY NO WARRANTY
This program is licensed under the GNU General Public License version 3

See {INFO_URL} for further details.
"""

TAGS_URL = "https://github.com/NanoVNA-Saver/nanovna-saver/tags"
TAGS_KEY = "/NanoVNA-Saver/nanovna-saver/releases/tag/v"

LATEST_URL = "https://github.com/NanoVNA-Saver/nanovna-saver/releases/latest"
