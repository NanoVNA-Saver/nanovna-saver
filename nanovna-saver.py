#! /usr/bin/env python3
#  NanoVNASaver - a python program to view and export Touchstone data from a
#  NanoVNA
#  Copyright (C) 2019. Rune B. Broberg
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

from contextlib import suppress
import os

# noinspection PyUnresolvedReferences
with suppress(ImportError):
    # pylint: disable=no-name-in-module,import-error,unused-import
    # pyright: reportMissingImports=false
    import pkg_resources.py2_warn

try:
    from NanoVNASaver.__main__ import main
except ModuleNotFoundError:
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    from NanoVNASaver.__main__ import main


if __name__ == "__main__":
    main()
