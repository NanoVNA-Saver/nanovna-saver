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

# This launcher is ignored by setuptools.  Its only purpose is direct
# execution from a source tree.

import os.path
import sys

# Ignore the current working directory.
src = os.path.join(os.path.dirname(__file__), "src")

if os.path.exists(src):
    sys.path.insert(0, src)

# pylint: disable-next=wrong-import-position
import NanoVNASaver.__main__

# The traditional test does not make sense here.
assert __name__ == "__main__"

NanoVNASaver.__main__.main()
