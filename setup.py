#  NanoVNASaver
#
#  A python program to view and export Touchstone data from a NanoVNA
#  Copyright (C) 2019, 2020  Rune B. Broberg
#  Copyright (C) 2020,2021 NanoVNA-Saver Authors
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

from setuptools import setup


data_files=[
    ( "share/doc/nanovnasaver/", [ "CHANGELOG.md", "LICENSE", "README.md" ] ),
    ( "share/applications/", [ "NanoVNASaver.desktop" ] ),
    ( "share/icons/hicolor/48x48/apps/", [ "NanoVNASaver_48x48.png" ] ),
]


setup(
author="NanoVNA-Saver organization",
author_email="NanoVNA-Saver@users.noreply.github.com",
url="https://github.com/NanoVNA-Saver/nanovna-saver",
description="GUI for the NanoVNA and derivates",
long_description="""A multiplatform tool to save Touchstone files from the NanoVNA,
sweep frequency spans in segments to gain more data points,
and generally display and analyze the resulting data.
""",
license="GPLv3",
platforms=[ "all" ],
data_files=data_files,
)
