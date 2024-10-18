#  NanoVNASaver
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
import logging
import re
import typing

logger = logging.getLogger(__name__)


_RXP = re.compile(
    r"""^
    \D*
    (?P<major>\d+)\.
    (?P<minor>\d+)\.?
    (?P<revision>\d+)?
    (?P<note>.*)
    $""",
    re.VERBOSE,
)


class _Version(typing.NamedTuple):
    major: int
    minor: int
    revision: int
    note: str

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}" f".{self.revision}{self.note}"


def Version(vstring: str = "0.0.0") -> "_Version":
    if (match := _RXP.search(vstring)) is None:
        logger.error("Unable to parse version: %s", vstring)
        return _Version(0, 0, 0, "")

    return _Version(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("revision") or "0"),
        match.group("note"),
    )
